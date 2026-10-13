"""Turn a code and its send policy into what goes on air.

A transmission is one *unit* plus a repeat count, which is what Home
Assistant's ``radio_frequency`` commands carry (``repeat_count`` = extra
sends after the first) and what ESPHome replays back to back. Sending one
unit keeps the ESPHome API message small, so the unit must join cleanly to
the next copy of itself:

- it starts with a mark (a leading space would only stretch the previous
  gap, so it is dropped);
- it ends with its inter-frame gap. Encoded frames always do. A raw capture
  that ends on a mark gets a closing gap: its own largest frame gap when it
  has one, otherwise :data:`DEFAULT_CLOSING_GAP_US`.

Nothing else about a raw capture is changed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .encoder import gap_threshold
from .models import Command, Frame, SendPolicy

DEFAULT_CLOSING_GAP_US = 10_000


@dataclass(frozen=True)
class Transmission:
    """One send: a unit, how often it repeats, and what that puts on air."""

    unit: tuple[int, ...]
    repeat_count: int  # extra sends after the first
    frames_on_air: int  # frames that actually go out (>= the policy's)

    @property
    def sends(self) -> int:
        """Return how many times the unit goes out."""
        return self.repeat_count + 1

    @property
    def airtime_s(self) -> float:
        """Return how long the transmitter is busy, in seconds."""
        return sum(abs(value) for value in self.unit) * self.sends / 1_000_000

    def stream(self) -> list[int]:
        """Return the full on-air timings (the unit repeated)."""
        return list(self.unit) * self.sends


def _joinable_unit(timings: list[int]) -> list[int]:
    """Return the unit trimmed to start on a mark and end on a gap."""
    unit = list(timings)
    while unit and unit[0] < 0:
        unit.pop(0)
    if not unit:
        return unit
    if unit[-1] > 0:
        spaces = [-value for value in unit if value < 0]
        threshold = gap_threshold(unit)
        frame_gaps = [space for space in spaces if space >= threshold]
        unit.append(-(max(frame_gaps) if frame_gaps else DEFAULT_CLOSING_GAP_US))
    return unit


def plan_frame(frame: Frame, policy: SendPolicy) -> Transmission:
    """Plan the transmission of a code under a send policy.

    The unit is sent often enough that at least ``policy.frames_on_air``
    frames go out: an encoded unit is one frame; a raw capture of *k* frames
    is replayed ``ceil(frames_on_air / k)`` times, so "send once" (1 frame)
    replays a multi-frame capture exactly once.
    """
    unit = _joinable_unit(frame.unit())
    if not unit:
        raise ValueError("code holds no timings to send")
    per_unit = frame.frames_per_unit
    sends = math.ceil(policy.frames_on_air / per_unit)
    return Transmission(unit=tuple(unit), repeat_count=sends - 1, frames_on_air=sends * per_unit)


def plan_command(command: Command, policy: SendPolicy | None = None) -> Transmission:
    """Plan a command's transmission, optionally overriding its send policy."""
    return plan_frame(command.frame, policy or command.policy)
