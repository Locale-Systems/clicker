"""Group receptions that match no command into sources, and remember ignored ones.

A *source* is one transmitter Clicker keeps hearing without knowing it: a
neighbour's weather sensor, a doorbell, an unlearned remote. Receptions that
decode are grouped by their code (their fingerprint; a weak reception within
one bit of a code joins it, since a single frame can carry a bit error).
Receptions that don't decode are grouped by their *shape*: how their pulse
and gap widths are distributed, as log-scale histograms. A sensor's bursts
differ bit for bit from one another (its readings change, and the receiver
drops pulses), but their timings come from the same few widths, so their
histograms overlap; another transmitter's don't. On real captures, bursts of
one source overlap by 0.73 or more and different sources by 0.57 at most.

Sources live in memory (:class:`SourceTracker`). Ignoring one stores an
:class:`IgnoredSource` with its code or shape, which later receptions are
compared against, so it stays ignored across restarts.
"""

from __future__ import annotations

import math
import statistics
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from . import rf_analysis as ra

if TYPE_CHECKING:
    from .receive import Reception

# Histogram bins: 8 per octave (~9 % apart) from 64 µs up to 16 ms.
_BINS_PER_OCTAVE = 8
_LOWEST_US = 64
_BINS = _BINS_PER_OCTAVE * 8
# Durations this long are idle time around a transmission, not part of it.
_MAX_US = 10_000
# Peaks closer than this ratio are one cluster.
_SAME_PEAK = 1.2
# Fewer values than this say too little to tell a source by.
MIN_SHAPE_VALUES = 16
# Shapes overlapping at least this much are the same source.
SIMILAR = 0.65
# Receptions more than this far apart (seconds) are separate transmissions.
BURST_GAP_S = 2.0
MAX_SOURCES = 50
# Captures kept per source, for exporting.
SAMPLES = 3


def _histogram(values: list[int]) -> tuple[float, ...]:
    """A normalized log-scale histogram; each value is split between its two nearest bins."""
    bins = [0.0] * _BINS
    for value in values:
        x = math.log2(value / _LOWEST_US) * _BINS_PER_OCTAVE
        if 0 <= x < _BINS - 1:
            index = int(x)
            bins[index] += 1 - (x - index)
            bins[index + 1] += x - index
    total = sum(bins) or 1.0
    return tuple(b / total for b in bins)


def _peaks(bins: tuple[float, ...], min_mass: float = 0.08) -> list[int]:
    """The widths (µs, rounded to 10) the histogram clusters around."""
    found: list[tuple[float, float]] = []  # (width, mass)
    for i, value in enumerate(bins):
        left = bins[i - 1] if i else 0.0
        right = bins[i + 1] if i + 1 < len(bins) else 0.0
        mass = left + value + right
        if value > 0 and value >= left and value > right and mass >= min_mass:
            # Interpolate between the neighbours for a closer centre.
            offset = (right - left) / mass
            found.append((_LOWEST_US * 2 ** ((i + offset) / _BINS_PER_OCTAVE), mass))
    merged: list[tuple[float, float]] = []
    for width, mass in found:
        if merged and width < merged[-1][0] * _SAME_PEAK:
            if mass > merged[-1][1]:
                merged[-1] = (width, mass)  # one cluster split in two: keep its heavier half
            continue
        merged.append((width, mass))
    return [int(round(width, -1)) for width, _mass in merged]


@dataclass(frozen=True)
class Shape:
    """How a transmission's mark and gap widths are distributed."""

    marks: tuple[float, ...]
    gaps: tuple[float, ...]

    def similarity(self, other: Shape) -> float:
        """Return how much two shapes overlap: 1 for identical, 0 for disjoint."""
        marks = sum(map(min, self.marks, other.marks, strict=True))
        gaps = sum(map(min, self.gaps, other.gaps, strict=True))
        return (marks + gaps) / 2

    def blend(self, other: Shape, weight: float) -> Shape:
        """Move this shape towards ``other`` by ``weight`` (0..1)."""

        def mix(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
            return tuple(x + (y - x) * weight for x, y in zip(a, b, strict=True))

        return Shape(mix(self.marks, other.marks), mix(self.gaps, other.gaps))

    def describe(self) -> str:
        """Say which widths it is made of, e.g. "pulses 210/450/810 µs, gaps 270/520 µs"."""
        marks, gaps = _peaks(self.marks), _peaks(self.gaps)
        parts = []
        if marks:
            parts.append(f"pulses {'/'.join(map(str, marks))} µs")
        if gaps:
            parts.append(f"gaps {'/'.join(map(str, gaps))} µs")
        return ", ".join(parts) or "no clear timing"

    def to_dict(self) -> dict[str, Any]:
        """Serialize sparsely: only bins with weight, rounded."""

        def sparse(bins: tuple[float, ...]) -> dict[str, float]:
            return {str(i): round(v, 4) for i, v in enumerate(bins) if round(v, 4)}

        return {"marks": sparse(self.marks), "gaps": sparse(self.gaps)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Shape:
        """Load from ``to_dict`` output."""

        def dense(bins: dict[str, float]) -> tuple[float, ...]:
            values = [0.0] * _BINS
            for index, value in bins.items():
                if 0 <= int(index) < _BINS:
                    values[int(index)] = float(value)
            return tuple(values)

        return cls(dense(data.get("marks") or {}), dense(data.get("gaps") or {}))


def shape_of(timings: list[int] | tuple[int, ...]) -> Shape | None:
    """Return a capture's shape, or None when it is too short to tell."""
    normalized = ra.normalize(list(timings))
    marks = [v for v in normalized if 0 < v < _MAX_US]
    gaps = [-v for v in normalized if -_MAX_US < v < 0]
    if len(marks) + len(gaps) < MIN_SHAPE_VALUES:
        return None
    return Shape(_histogram(marks), _histogram(gaps))


@dataclass
class IgnoredSource:
    """A source the user doesn't want to see: a code, or a shape, on one frequency."""

    frequency_hz: int
    name: str = ""
    fingerprint: str | None = None
    shape: Shape | None = None
    description: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def covers(self, frequency_hz: int, fingerprint: str | None, shape: Shape | None) -> bool:
        """Return whether a source with this code or shape is this one."""
        if frequency_hz != self.frequency_hz:
            return False
        if self.fingerprint is not None:
            return fingerprint == self.fingerprint
        return (
            shape is not None and self.shape is not None and shape.similarity(self.shape) >= SIMILAR
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        data: dict[str, Any] = {
            "id": self.id,
            "frequency_hz": self.frequency_hz,
            "name": self.name,
            "description": self.description,
        }
        if self.fingerprint is not None:
            data["fingerprint"] = self.fingerprint
        if self.shape is not None:
            data["shape"] = self.shape.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IgnoredSource:
        """Load from ``to_dict`` output."""
        return cls(
            id=str(data["id"]),
            frequency_hz=int(data["frequency_hz"]),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            fingerprint=data.get("fingerprint"),
            shape=Shape.from_dict(data["shape"]) if data.get("shape") else None,
        )


@dataclass
class Source:
    """One transmitter heard repeatedly without matching any command."""

    number: int  # 1 for the first source heard, ...
    radio_id: str
    frequency_hz: int
    first_seen: float
    last_seen: float
    fingerprint: str | None = None  # set for a code
    bits: str | None = None
    encoding: str | None = None
    shape: Shape | None = None  # set for a shape
    pulses: int = 0  # timings in the latest reception
    count: int = 0
    samples: deque[tuple[int, ...]] = field(default_factory=lambda: deque(maxlen=SAMPLES))
    bursts: deque[float] = field(default_factory=lambda: deque(maxlen=20))
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @property
    def label(self) -> str:
        """ "Source A", "Source B", ... "Source AA", in the order they were first heard."""
        n, letters = self.number, ""
        while n > 0:
            n, rest = divmod(n - 1, 26)
            letters = chr(ord("A") + rest) + letters
        return f"Source {letters}"

    def describe(self) -> str:
        """What it sends, for a person: its code, or its timing."""
        if self.bits is not None:
            tail = self.bits[-8:]
            return f"{len(self.bits)}-bit {self.encoding or 'code'} …{tail}"
        assert self.shape is not None
        return f"~{self.pulses} pulses; {self.shape.describe()}"

    def period_s(self) -> float | None:
        """Return how often it transmits, when its transmissions are regular."""
        starts = list(self.bursts)
        if len(starts) < 3:
            return None
        intervals = [b - a for a, b in zip(starts, starts[1:], strict=False)]
        typical = statistics.median(intervals)
        regular = [i for i in intervals if abs(i - typical) <= 0.25 * typical]
        return typical if len(regular) >= 0.6 * len(intervals) else None

    def ignored_by(self, ignored: list[IgnoredSource]) -> IgnoredSource | None:
        """Return the ignore entry that covers this source, if any."""
        return next(
            (i for i in ignored if i.covers(self.frequency_hz, self.fingerprint, self.shape)),
            None,
        )

    def ignore_entry(self, name: str = "") -> IgnoredSource:
        """An entry that ignores this source and any later reception like it."""
        return IgnoredSource(
            frequency_hz=self.frequency_hz,
            name=name.strip(),
            fingerprint=self.fingerprint,
            shape=None if self.fingerprint is not None else self.shape,
            description=self.describe(),
        )


class SourceTracker:
    """Keeps the sources heard recently, up to ``max_sources``."""

    def __init__(self, max_sources: int = MAX_SOURCES) -> None:
        self._max = max_sources
        self._sources: list[Source] = []
        self._numbers = 0

    @property
    def sources(self) -> list[Source]:
        """The sources, most recently heard first."""
        return sorted(self._sources, key=lambda s: s.last_seen, reverse=True)

    def get(self, source_id: str) -> Source | None:
        """Return the source with this id, if it is still tracked."""
        return next((s for s in self._sources if s.id == source_id), None)

    def observe(
        self,
        radio_id: str,
        frequency_hz: int,
        reception: Reception,
        timings: list[int] | tuple[int, ...],
        at: float,
    ) -> Source | None:
        """File an unmatched reception under its source; None when it is too short to tell."""
        if reception.bits is not None:
            source = self._code_source(radio_id, reception)
            shape = None
        else:
            shape = shape_of(timings)
            if shape is None:
                return None
            source = self._shape_source(radio_id, shape)
        if source is None:
            self._numbers += 1
            source = Source(
                number=self._numbers,
                radio_id=radio_id,
                frequency_hz=frequency_hz,
                first_seen=at,
                last_seen=at,
                fingerprint=reception.fingerprint if reception.bits is not None else None,
                bits=reception.bits,
                encoding=reception.encoding,
                shape=shape,
            )
            self._sources.append(source)
            if len(self._sources) > self._max:
                self._sources.remove(min(self._sources, key=lambda s: s.last_seen))
        elif shape is not None and source.shape is not None:
            # Follow the source as it drifts; early receptions weigh more.
            source.shape = source.shape.blend(shape, 1 / min(source.count + 1, 10))
        if not source.bursts or at - source.last_seen > BURST_GAP_S:
            source.bursts.append(at)
        source.last_seen = at
        source.count += 1
        source.pulses = len(timings)
        source.samples.append(tuple(timings))
        return source

    def _code_source(self, radio_id: str, reception: Reception) -> Source | None:
        codes = [s for s in self._sources if s.radio_id == radio_id and s.bits is not None]
        exact = next((s for s in codes if s.fingerprint == reception.fingerprint), None)
        if exact is not None or reception.reliable:
            return exact
        return next((s for s in codes if ra.bit_distance(s.bits, reception.bits) == 1), None)

    def _shape_source(self, radio_id: str, shape: Shape) -> Source | None:
        best: tuple[float, Source] | None = None
        for source in self._sources:
            if source.radio_id != radio_id or source.shape is None or source.bits is not None:
                continue
            similarity = source.shape.similarity(shape)
            if similarity >= SIMILAR and (best is None or similarity > best[0]):
                best = (similarity, source)
        return best[1] if best else None
