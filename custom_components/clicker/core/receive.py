"""One analysis path for everything received and everything stored.

:func:`analyze` turns a raw capture into a :class:`Reception`: its canonical
frame, decoded bits and fingerprint. Learning, remote-press matching and the
live signal view all use it, and stored codes are analyzed by running their
own unit back through it (:func:`analyze_code`). So a code and the captures
of its button always reach the same bits and fingerprint, however the
analysis evolves.

The canonical frame comes from the encoder's frame search (majority vote on
bits across complete frames; a single frame that starts with its sync gap
has the gap moved to the end), so a single-frame event decodes to all its
bits rather than losing the last one to the sync.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from . import rf_analysis as ra
from .const import MIN_SIGNAL_PULSES
from .decoders import decode_frame
from .encoder import find_unit
from .models import Frame


@dataclass(frozen=True)
class Reception:
    """What one capture carries, as far as it can be told."""

    unit: tuple[int, ...] | None  # canonical frame; None when no complete frame
    bits: str | None
    encoding: str | None
    fingerprint: str | None  # matching key; None for captures too short to use
    complete_frames: int  # frames that end on their gap
    agreeing_frames: int  # complete frames carrying these bits
    how: str  # how the frame was found, or why not

    @property
    def decoded(self) -> bool:
        """Return whether the capture decoded to bits."""
        return self.bits is not None


def frame_fingerprint(frame: list[int]) -> str | None:
    """Return the matching key of one frame.

    Decodable frames hash their bits (immune to timing jitter; the same
    ``"<n>b:<sha>"`` scheme rf_device_manager uses, so imported codes keep
    their keys). Others hash the frame quantized to its own base unit.
    """
    if bits := decode_frame(frame).get("bits"):
        return f"{len(bits)}b:{hashlib.sha1(bits.encode()).hexdigest()[:12]}"
    symbols = ra.quantize_frame(frame, ra.estimate_base_unit(frame))
    if not symbols:
        return None
    digest = hashlib.sha1(",".join(map(str, symbols)).encode()).hexdigest()[:12]
    return f"{len(symbols)}:{digest}"


def analyze(timings: list[int]) -> Reception:
    """Analyze a raw capture (any sign convention, untrimmed)."""
    normalized = ra.normalize(timings)
    if len(normalized) < MIN_SIGNAL_PULSES:
        return Reception(None, None, None, None, 0, 0, "too short")
    search = find_unit(normalized)
    if search.unit is not None:
        frame = search.unit
        how = search.source
    else:
        # No complete frame: fall back to the most typical frame as captured.
        frame = ra.dominant_frame(ra.split_frames(ra.trim_partial_frames(normalized)))
        how = f"{search.source}; using the dominant frame as captured"
    decoded = decode_frame(frame)
    bits = decoded.get("bits")
    return Reception(
        unit=tuple(search.unit) if search.unit is not None else None,
        bits=str(bits) if bits else None,
        encoding=str(decoded["encoding"]) if bits else None,
        fingerprint=frame_fingerprint(frame),
        complete_frames=search.complete_frames,
        agreeing_frames=search.agreeing_frames,
        how=how,
    )


def analyze_code(frame: Frame) -> Reception:
    """Analyze a stored code exactly as its button's captures are analyzed."""
    return analyze(frame.unit())
