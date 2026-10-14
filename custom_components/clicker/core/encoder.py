"""Decode -> encode round trip for sub-GHz OOK captures.

A learned capture is replaced by a clean frame *encoded from its decoded
bits* whenever that frame provably reproduces the capture; otherwise the raw
capture is kept.

Pipeline for one capture:

1. ``canonical_unit``: normalize, drop broken edge frames, and find one
   complete repeating frame - starts with a mark, ends with its inter-frame
   gap - so frames can be concatenated back to back.
2. ``extract_spec``: decode that frame and measure its timings per symbol
   (median ``(mark, space)`` for a 0 bit and a 1 bit, the sync pair, or the
   Manchester half period).
3. ``encode``: rebuild the frame from bits + timings only.
4. Verify (``roundtrip``):
   - frame:  the encoded frame matches the captured one pulse by pulse;
   - decode: the encoded frame decodes to the same bits;
   - stream: 8 encoded frames back to back decode as 8 identical frames
     (what a transmitter actually sends).

Anything that fails a step keeps the raw capture, with the reason recorded.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from statistics import median
from typing import Any

from . import rf_analysis as ra
from .decoders import FrameContext, decode_frame

PAIR_ENCODINGS = {"space_distance", "mark_width", "pwm"}
STREAM_FRAMES = 8

# Bump whenever canonical_unit / extract_spec / encode change their output, so
# stored codes made by an older encoder can be re-encoded from their captures.
ENCODER_VERSION = 1


def _pair(value: Any) -> tuple[int, int] | None:
    """Return a stored ``[mark, space]`` pair as a tuple (JSON has no tuples)."""
    if value is None:
        return None
    mark, space = value
    return int(mark), int(space)


@dataclass(frozen=True)
class CodeSpec:
    """Everything needed to synthesize one frame of a code."""

    encoding: str
    bits: str
    zero: tuple[int, int] | None = None  # (mark, space) of a 0 bit
    one: tuple[int, int] | None = None  # (mark, space) of a 1 bit
    sync: tuple[int, int] = (0, 0)  # (mark, gap) closing the frame
    header: tuple[int, int] | None = None  # (mark, space) opening the frame
    tail_bit: bool = False  # the last bit's mark closes the frame; only sync's gap is used
    half: int = 0  # Manchester half period
    lead_half: bool = False  # Manchester: extra leading mark half
    gap: int = 0  # Manchester inter-frame gap

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        data = asdict(self)
        for key in ("zero", "one", "sync", "header"):
            if data[key] is not None:
                data[key] = list(data[key])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeSpec:
        """Load from ``to_dict`` output; unknown keys are ignored."""
        return cls(
            encoding=str(data["encoding"]),
            bits=str(data["bits"]),
            zero=_pair(data.get("zero")),
            one=_pair(data.get("one")),
            sync=_pair(data.get("sync")) or (0, 0),
            header=_pair(data.get("header")),
            tail_bit=bool(data.get("tail_bit", False)),
            half=int(data.get("half", 0)),
            lead_half=bool(data.get("lead_half", False)),
            gap=int(data.get("gap", 0)),
        )


@dataclass
class Report:
    """Outcome of one capture's round trip."""

    name: str
    status: str = "raw"  # "encoded" when every check passed
    reason: str = ""
    unit_source: str = ""
    encoding: str | None = None
    bits: str | None = None
    integration_bits: str | None = None  # what analyze() reports today
    frame_match: bool = False
    max_pulse_dev_pct: float | None = None
    gap_dev_pct: float | None = None
    redecode_ok: bool = False
    stream_frames_ok: int = 0
    fingerprint_same: bool | None = None
    spec: dict[str, Any] | None = field(default=None)


# ---------------------------------------------------------------------------
# 1. Find one complete repeating frame
# ---------------------------------------------------------------------------


def gap_threshold(timings: list[int]) -> float:
    """Mirror rf_analysis.split_frames' adaptive inter-frame gap threshold."""
    absolutes = sorted(abs(value) for value in timings)
    p95 = absolutes[int(0.95 * (len(absolutes) - 1))]
    return max(ra._FRAME_GAP_MIN_US, ra._FRAME_GAP_FACTOR * p95)


def _strip_leading_space(frame: list[int]) -> list[int]:
    return frame[1:] if frame and frame[0] < 0 else frame


@dataclass(frozen=True)
class UnitSearch:
    """Result of looking for one complete repeating frame in a capture."""

    unit: list[int] | None  # mark first, gap last; None when none was found
    source: str  # how the unit was found, or why not
    complete_frames: int = 0  # frames that end on their gap
    agreeing_frames: int = 0  # complete frames carrying the winning bits


def find_unit(timings: list[int]) -> UnitSearch:
    """Find one complete frame (mark first, gap last) and how it was found."""
    stream = _strip_leading_space(ra.trim_partial_frames(ra.normalize(timings)))
    if not stream:
        return UnitSearch(None, "empty capture")
    threshold = gap_threshold(stream)
    frames = [_strip_leading_space(frame) for frame in ra.split_frames(stream)]
    complete = [
        frame
        for frame in frames
        if len(frame) >= 10 and frame[-1] < 0 and abs(frame[-1]) >= threshold
    ]
    if complete:
        # Majority vote on the decoded bits so one frame with a reception bit
        # error cannot become the stored code; then the most typical frame
        # carrying the winning bits supplies the timings.
        decoded = [decode_frame(frame).get("bits") for frame in complete]
        votes = Counter(bits for bits in decoded if bits)
        if votes:
            winner, count = votes.most_common(1)[0]
            voters = [f for f, bits in zip(complete, decoded, strict=True) if bits == winner]
            return UnitSearch(
                ra.dominant_frame(voters),
                f"{len(complete)} complete frame(s), {count} agree on the bits",
                len(complete),
                count,
            )
        return UnitSearch(
            ra.dominant_frame(complete), f"{len(complete)} complete frame(s)", len(complete)
        )
    # One receiver event of a single frame: [sync mark, sync gap] + data
    # ending on a mark (the gap preceding the data closes the previous frame).
    # Rotating the leading gap to the end yields the repeating unit.
    if (
        len(frames) == 2
        and len(frames[0]) == 2
        and frames[0][0] > 0
        and len(frames[1]) >= 9
        and frames[1][-1] > 0
    ):
        unit = [*frames[1], frames[0][1]]
        agreeing = 1 if decode_frame(unit).get("bits") else 0
        return UnitSearch(unit, "rotated: leading sync gap moved to end", 1, agreeing)
    return UnitSearch(None, "no complete frame (no closing gap)")


def canonical_unit(timings: list[int]) -> tuple[list[int] | None, str]:
    """Return one complete frame (mark first, gap last) and how it was found."""
    search = find_unit(timings)
    return search.unit, search.source


# ---------------------------------------------------------------------------
# 2. Measure the timings of a decoded frame
# ---------------------------------------------------------------------------


def _median_pair(pairs: list[tuple[int, int]]) -> tuple[int, int] | None:
    if not pairs:
        return None
    return round(median(m for m, _ in pairs)), round(median(s for _, s in pairs))


def extract_spec(unit: list[int]) -> tuple[CodeSpec | None, str]:
    """Decode a frame and capture the timings needed to re-encode it."""
    decoded = decode_frame(unit)
    encoding, bits = decoded.get("encoding"), decoded.get("bits")
    if not encoding or not bits:
        return None, "does not decode (raw-only signal)"

    if encoding in PAIR_ENCODINGS:
        context = FrameContext.from_frame(unit)
        tail_bit = bool(decoded.get("tail_bit"))
        if context is None or len(context.bit_pairs) + tail_bit != len(bits):
            return None, "decoder pairs do not cover the bits"
        header_pairs = 0 if context.header_pair is None else 1
        if len(unit) != 2 * (header_pairs + len(context.bit_pairs) + 1):
            return None, "frame has structure beyond header + bits + sync (preamble?)"
        pairs = list(zip(context.bit_pairs, bits, strict=False))
        return (
            CodeSpec(
                encoding=encoding,
                bits=bits,
                zero=_median_pair([p for p, b in pairs if b == "0"]),
                one=_median_pair([p for p, b in pairs if b == "1"]),
                sync=context.sync_pair,
                header=context.header_pair,
                tail_bit=tail_bit,
            ),
            "",
        )

    if encoding == "manchester":
        base = CodeSpec(encoding=encoding, bits=bits, half=decoded["pulse_length"], gap=-unit[-1])
        for lead_half in (False, True):
            spec = CodeSpec(**{**asdict(base), "lead_half": lead_half})
            if ra.frames_similar(encode(spec), unit):
                return spec, ""
        return None, "Manchester phase could not be reproduced"

    return None, f"no encoder for {encoding}"


# ---------------------------------------------------------------------------
# 3. Encode
# ---------------------------------------------------------------------------


def encode(spec: CodeSpec) -> list[int]:
    """Synthesize one frame (mark first, inter-frame gap last)."""
    if spec.encoding in PAIR_ENCODINGS:
        out: list[int] = []
        if spec.header is not None:
            out += [spec.header[0], -spec.header[1]]
        for bit in spec.bits:
            symbol = spec.one if bit == "1" else spec.zero
            if symbol is None:
                raise ValueError(f"no timing measured for a {bit} bit")
            out += [symbol[0], -symbol[1]]
        if spec.tail_bit:
            out[-1] = -spec.sync[1]  # the last bit's space is the inter-frame gap
            return out
        return out + [spec.sync[0], -spec.sync[1]]

    if spec.encoding == "manchester":
        halves = [True] if spec.lead_half else []
        for bit in spec.bits:
            halves += [True, False] if bit == "1" else [False, True]
        while halves and not halves[0]:
            halves.pop(0)  # a leading space half merges into the previous gap
        out = []
        for level in halves:
            duration = spec.half if level else -spec.half
            if out and (out[-1] > 0) == level:
                out[-1] += duration
            else:
                out.append(duration)
        if out[-1] > 0:
            out.append(-spec.gap)
        else:
            out[-1] = -spec.gap  # the trailing space half merges into the gap
        return out

    raise ValueError(f"no encoder for {spec.encoding}")


# ---------------------------------------------------------------------------
# 4. Verify
# ---------------------------------------------------------------------------


def _deviation_pct(encoded: list[int], unit: list[int]) -> tuple[float, float]:
    """Max per-pulse deviation (excluding the gap) and the gap deviation, in %."""
    pulse = max(
        abs(abs(a) - abs(b)) / abs(b) * 100 for a, b in zip(encoded[:-1], unit[:-1], strict=True)
    )
    gap = abs(abs(encoded[-1]) - abs(unit[-1])) / abs(unit[-1]) * 100
    return round(pulse, 1), round(gap, 1)


def roundtrip(name: str, timings: list[int]) -> Report:
    """Run the full decode -> encode -> verify pipeline on one capture."""
    report = Report(name=name)
    report.integration_bits = ra.analyze(timings).get("bits")
    unit, report.unit_source = canonical_unit(timings)
    if unit is None:
        report.reason = report.unit_source
        return report
    spec, why = extract_spec(unit)
    if spec is None:
        report.reason = why
        return report
    report.encoding, report.bits, report.spec = spec.encoding, spec.bits, asdict(spec)

    encoded = encode(spec)
    report.frame_match = len(encoded) == len(unit) and ra.frames_similar(encoded, unit)
    if len(encoded) == len(unit):
        report.max_pulse_dev_pct, report.gap_dev_pct = _deviation_pct(encoded, unit)
    report.redecode_ok = decode_frame(encoded).get("bits") == spec.bits

    stream = encoded * STREAM_FRAMES
    report.stream_frames_ok = sum(
        decode_frame(frame).get("bits") == spec.bits for frame in ra.split_frames(stream)
    )
    report.fingerprint_same = ra.fingerprint(timings) == ra.fingerprint(stream)

    failed = [
        label
        for label, ok in (
            ("frame mismatch", report.frame_match),
            ("re-decode mismatch", report.redecode_ok),
            ("stream decode", report.stream_frames_ok == STREAM_FRAMES),
        )
        if not ok
    ]
    report.status = "raw" if failed else "encoded"
    report.reason = ", ".join(failed)
    return report
