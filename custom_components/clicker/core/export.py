"""Write captures as rtl_433 pulse files, for working out unknown signals elsewhere.

The ``.ook`` format is rtl_433's text pulse format: per packet, a header of
``;``-prefixed lines, then one ``<pulse µs> <gap µs>`` line per pulse, then
``;end``. rtl_433 reads every packet in a file (``rtl_433 -r capture.ook`` to
decode, ``rtl_433 -A -r capture.ook`` to analyze the modulation), and since
it is plain text it can also be pasted into an AI chat.

Each export holds the captures as received and, when Clicker can decode the
signal, a *cleaned* packet: Clicker's majority-vote frame, rebuilt and
repeated. Receivers drop the odd short pulse, so the repeats of a raw
capture rarely agree bit for bit, and many rtl_433 decoders insist they do;
the cleaned packet gives them identical repeats.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import rf_analysis as ra
from .encoder import encode, extract_spec
from .receive import analyze

# The gap that ends a packet, long enough for every rtl_433 decoder to reset.
END_GAP_US = 20_000
CLEAN_REPEATS = 4


@dataclass(frozen=True)
class Packet:
    """One packet of a pulse file: a title and its pulse/gap pairs."""

    title: str
    pairs: tuple[tuple[int, int], ...]


def pulse_pairs(timings: list[int] | tuple[int, ...]) -> tuple[tuple[int, int], ...]:
    """Turn a capture into (pulse, gap) pairs: signed, de-glitched, starting with a pulse."""
    signed = ra.normalize(list(timings))
    while signed and signed[0] < 0:
        signed = signed[1:]
    pairs = []
    for index in range(0, len(signed), 2):
        gap = -signed[index + 1] if index + 1 < len(signed) else END_GAP_US
        pairs.append((signed[index], gap))
    if pairs:
        pairs[-1] = (pairs[-1][0], max(pairs[-1][1], END_GAP_US))
    return tuple(pairs)


def cleaned(timings: list[int] | tuple[int, ...]) -> tuple[list[int], str] | None:
    """Return Clicker's cleaned version of a capture and what it is, if it decodes."""
    reception = analyze(list(timings))
    if reception.unit is None or reception.bits is None:
        return None
    spec, _why = extract_spec(list(reception.unit))
    frame = encode(spec) if spec is not None else list(reception.unit)
    how = "rebuilt from the decoded bits" if spec is not None else "the frame as received"
    return frame * CLEAN_REPEATS, (
        f"{len(reception.bits)}-bit {reception.encoding}, {CLEAN_REPEATS} identical frames, {how}"
    )


def packets_for(captures: list[tuple[int, ...]]) -> list[Packet]:
    """The raw packets of some captures of one signal, then a cleaned one when it decodes."""
    packets = [
        Packet(f"capture {n} of {len(captures)}, as received", pulse_pairs(timings))
        for n, timings in enumerate(captures, 1)
    ]
    for timings in reversed(captures):  # the latest capture that decodes
        if (clean := cleaned(timings)) is not None:
            frame, what = clean
            packets.append(Packet(f"cleaned by Clicker: {what}", pulse_pairs(frame)))
            break
    return [p for p in packets if p.pairs]


def to_ook(packets: list[Packet], frequency_hz: int, notes: list[str]) -> str:
    """Write packets as an rtl_433 pulse file; ``notes`` head the first packet."""
    lines: list[str] = []
    for index, packet in enumerate(packets):
        lines += [";pulse data", ";version 1", ";timescale 1us"]
        if index == 0:
            lines += [f";clicker {note}" for note in notes]
        lines += [
            f";clicker {packet.title}",
            f";ook {len(packet.pairs)} pulses",
            f";freq1 {frequency_hz}",
        ]
        lines += [f"{pulse} {gap}" for pulse, gap in packet.pairs]
        lines.append(";end")
    return "\n".join(lines) + "\n"
