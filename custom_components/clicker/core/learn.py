"""Group the captures of a learn session into ranked candidates.

A session listens on one frequency while the user presses a button. Every
capture is analyzed (``receive.analyze``) and grouped by fingerprint; the
candidate list is rebuilt from the groups on every view, so it can be shown
live and never depends on arrival order:

1. **Rank** groups by sightings, then decoded before raw, then agreeing
   frames (a held button yields several identical frames per capture).
2. **Fold** a group into a stronger one when they are the same button by the
   matcher's own rule (``matcher.code_distance``): a weak reception whose
   bits are within the bit tolerance (a reception bit error), or similar raw
   frames. Two groups with reliable bits never fold, so sibling buttons a bit
   apart stay separate. Learning and matching agree on "the same button".
3. **Prune** undecodable groups seen once (noise, frames caught while the
   receiver's gain settled), but only when the top candidate is clearly a
   real press (seen twice, or decoded with two agreeing frames). Remotes no
   decoder recognizes still work: nothing is pruned next to a weak top.

Each group keeps its best capture (most agreeing frames) to build the code
from, and a candidate can say which existing commands it already matches,
so the same button isn't learned twice.
"""

from __future__ import annotations

from dataclasses import dataclass

from .matcher import Match, Matcher, code_distance
from .models import Frame, frame_from_capture
from .receive import Reception, analyze

DEFAULT_MAX_CANDIDATES = 8


@dataclass(frozen=True)
class Candidate:
    """One button the session may have heard, with the evidence for it."""

    reception: Reception  # analysis of the best capture
    capture: tuple[int, ...]  # the best capture, to build the code from
    sightings: int  # captures grouped here, folded copies included
    variants: int  # distinct codes folded together (1 = only its own)
    first_at: float
    last_at: float
    known_as: tuple[Match, ...] = ()  # existing commands it already matches

    @property
    def fingerprint(self) -> str | None:
        """Return the candidate's fingerprint."""
        return self.reception.fingerprint

    @property
    def bits(self) -> str | None:
        """Return the candidate's decoded bits, if any."""
        return self.reception.bits

    def code(self) -> Frame:
        """Build the code to store: encoded when it round-trips, else raw."""
        return frame_from_capture(list(self.capture))


@dataclass
class _Group:
    reception: Reception
    capture: tuple[int, ...]
    sightings: int
    first_at: float
    last_at: float


@dataclass
class _Folded:
    group: _Group
    sightings: int
    variants: int
    first_at: float
    last_at: float


def _rank(sightings: int, reception: Reception) -> tuple[int, int, int]:
    return sightings, int(reception.decoded), reception.agreeing_frames


def _confident(folded: _Folded) -> bool:
    return folded.sightings >= 2 or folded.group.reception.reliable


class LearnSession:
    """Collects captures on one frequency and ranks what they could be."""

    def __init__(self, frequency_hz: int, *, max_candidates: int = DEFAULT_MAX_CANDIDATES) -> None:
        self.frequency_hz = frequency_hz
        self._max_candidates = max_candidates
        self._groups: dict[str, _Group] = {}

    def add(
        self,
        timings: list[int],
        frequency_hz: int,
        at: float,
        reception: Reception | None = None,
    ) -> bool:
        """Take one capture; return whether it was used.

        Pass ``reception`` when the capture was already analyzed (the receive
        pipeline analyzes once for matching, the live view and learning).
        """
        if frequency_hz != self.frequency_hz:
            return False
        reception = reception or analyze(timings)
        if reception.fingerprint is None:
            return False
        group = self._groups.get(reception.fingerprint)
        if group is None:
            self._groups[reception.fingerprint] = _Group(reception, tuple(timings), 1, at, at)
            return True
        group.sightings += 1
        group.first_at, group.last_at = min(group.first_at, at), max(group.last_at, at)
        if reception.agreeing_frames > group.reception.agreeing_frames:
            group.reception, group.capture = reception, tuple(timings)
        return True

    def candidates(self, known: Matcher | None = None) -> list[Candidate]:
        """Return the ranked candidates, strongest first."""
        groups = sorted(
            self._groups.values(), key=lambda g: _rank(g.sightings, g.reception), reverse=True
        )
        folded: list[_Folded] = []
        for group in groups:
            target = next(
                (
                    f
                    for f in folded
                    if code_distance(group.reception, f.group.reception) is not None
                ),
                None,
            )
            if target is None:
                folded.append(_Folded(group, group.sightings, 1, group.first_at, group.last_at))
                continue
            target.sightings += group.sightings
            target.variants += 1
            target.first_at = min(target.first_at, group.first_at)
            target.last_at = max(target.last_at, group.last_at)
        folded.sort(key=lambda f: _rank(f.sightings, f.group.reception), reverse=True)
        if folded and _confident(folded[0]):
            folded = [folded[0]] + [
                f for f in folded[1:] if f.group.reception.decoded or f.sightings >= 2
            ]
        return [
            Candidate(
                reception=f.group.reception,
                capture=f.group.capture,
                sightings=f.sightings,
                variants=f.variants,
                first_at=f.first_at,
                last_at=f.last_at,
                known_as=tuple(known.candidates(f.group.reception, self.frequency_hz))
                if known is not None
                else (),
            )
            for f in folded[: self._max_candidates]
        ]
