"""Decide which device commands a reception was: pure logic, clock passed in.

Rules:

- **Frequency first.** Only devices on the receiving radio's frequency are
  candidates. Matching is by frequency, not by radio, so several radios on
  one band all work.
- **Exact when certain, nearest otherwise.** An identical fingerprint is
  distance 0. Reliable bits (two or more frames agreeing, see
  ``Reception.reliable``) must be identical: a remote's sibling buttons often
  differ by a single bit, so a near miss is another button, not an error.
  Only a weak reception (one frame, or frames that disagree) may be within
  ``rf_analysis.BIT_TOLERANCE`` of a code (distance = differing bits), and
  undecodable codes need similar frame timing (distance 1). Both are relative
  to a code's own base pulse, so a remote whose timing drifts still matches.
- **Closest command per device.** Only the nearest command of each device
  fires; ties go to the command listed first. Different devices sharing a
  code all fire.
- **One press, one match.** A command that matched is ignored again until
  its button has been quiet for ``release_gap_s``. The window slides with
  every repeated frame, so holding a toggle still counts once.
- **Clicker's own sends don't count.** Receptions on a frequency are ignored
  while Clicker transmits on it, plus ``echo_margin_s``.

Stored codes are analyzed with :func:`receive.analyze_code`, the same path
as receptions, so a code and its button always compare like for like.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import rf_analysis as ra
from .models import ClickerData, Command, CommandKind
from .receive import Reception, analyze_code

DEFAULT_RELEASE_GAP_S = 0.5
DEFAULT_ECHO_MARGIN_S = 0.5


@dataclass(frozen=True)
class Match:
    """A reception identified as one device command."""

    device_id: str
    command_id: str
    kind: CommandKind
    distance: int  # 0 = identical code


@dataclass(frozen=True)
class _Code:
    device_id: str
    command: Command
    heard_as: Reception


def code_distance(heard: Reception, code: Reception) -> int | None:
    """Return how far a reception is from a stored code, or None if unrelated.

    Not symmetric: only ``heard``'s reliability decides whether near bits count.
    """
    if heard.fingerprint is not None and heard.fingerprint == code.fingerprint:
        return 0
    if heard.bits is not None or code.bits is not None:
        if heard.reliable:
            return None  # identical bits share the fingerprint, matched above
        if ra.bits_within_tolerance(heard.bits, code.bits):
            return ra.bit_distance(heard.bits, code.bits)
        return None
    if (
        heard.unit is not None
        and code.unit is not None
        and ra.frames_similar(list(heard.unit), list(code.unit))
    ):
        return 1
    return None


class Matcher:
    """Identifies receptions as device commands, with debounce and echo rules."""

    def __init__(
        self,
        data: ClickerData,
        *,
        release_gap_s: float = DEFAULT_RELEASE_GAP_S,
        echo_margin_s: float = DEFAULT_ECHO_MARGIN_S,
    ) -> None:
        self._release_gap_s = release_gap_s
        self._echo_margin_s = echo_margin_s
        self._codes: dict[int, list[_Code]] = {}
        self._last_heard: dict[tuple[str, str], float] = {}
        self._transmitting_until: dict[int, float] = {}
        self.rebuild(data)

    def rebuild(self, data: ClickerData) -> None:
        """Re-index the stored codes (call after devices or commands change)."""
        codes: dict[int, list[_Code]] = {}
        for device in data.devices:
            for command in device.commands:
                codes.setdefault(device.frequency_hz, []).append(
                    _Code(device.id, command, analyze_code(command.frame))
                )
        self._codes = codes
        known = {(c.device_id, c.command.id) for group in codes.values() for c in group}
        self._last_heard = {k: t for k, t in self._last_heard.items() if k in known}

    def note_transmission(self, frequency_hz: int, at: float, airtime_s: float) -> None:
        """Record that Clicker is sending on a frequency from ``at`` for ``airtime_s``."""
        until = at + airtime_s + self._echo_margin_s
        self._transmitting_until[frequency_hz] = max(
            until, self._transmitting_until.get(frequency_hz, until)
        )

    def candidates(self, reception: Reception, frequency_hz: int) -> list[Match]:
        """Return the closest command per device on this frequency, ignoring time."""
        best: dict[str, Match] = {}
        for code in self._codes.get(frequency_hz, []):
            distance = code_distance(reception, code.heard_as)
            if distance is None:
                continue
            current = best.get(code.device_id)
            if current is None or distance < current.distance:
                best[code.device_id] = Match(
                    code.device_id, code.command.id, code.command.kind, distance
                )
        return list(best.values())

    def match(self, reception: Reception, frequency_hz: int, at: float) -> list[Match]:
        """Return the presses this reception completes, applying debounce and echo rules."""
        if at < self._transmitting_until.get(frequency_hz, float("-inf")):
            return []
        fired: list[Match] = []
        for candidate in self.candidates(reception, frequency_hz):
            key = (candidate.device_id, candidate.command_id)
            last = self._last_heard.get(key)
            self._last_heard[key] = at
            if last is None or at - last >= self._release_gap_s:
                fired.append(candidate)
        return fired
