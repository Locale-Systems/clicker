"""Source grouping and ignoring - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_sources.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core import edit  # noqa: E402
from core.models import ClickerData, ModelError  # noqa: E402
from core.receive import analyze  # noqa: E402
from core.sources import IgnoredSource, Shape, SourceTracker, shape_of  # noqa: E402

F433 = 433_920_000
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


# --- Shapes -------------------------------------------------------------------

tx141 = [shape_of(t) for t in corpus.TX141_BURSTS]
minute = [shape_of(t) for t in corpus.MINUTE_SOURCE_BURSTS]
check(all(tx141) and all(minute), "real bursts should have shapes")
tx = [s for s in tx141 if s is not None]
mn = [s for s in minute if s is not None]
same = [a.similarity(b) for group in (tx, mn) for i, a in enumerate(group) for b in group[i + 1 :]]
different = [a.similarity(b) for a in tx for b in mn]
check(min(same) >= 0.7, f"bursts of one source should overlap: {min(same):.2f}")
check(max(different) <= 0.5, f"different sources should not: {max(different):.2f}")
check(shape_of([400, -1200, 400, -1200]) is None, "too short to have a shape")
check(Shape.from_dict(tx[0].to_dict()).similarity(tx[0]) > 0.999, "shape doesn't survive storage")
check(tx[0].describe() == "pulses 220/450/810 µs, gaps 270/520/870 µs", tx[0].describe())

# --- Tracking -------------------------------------------------------------------

tracker = SourceTracker()


def hear(timings: list[int], at: float, radio: str = "rx") -> str | None:
    source = tracker.observe(radio, F433, analyze(timings), timings, at)
    return source.label if source else None


# The sensor every 50 s and the other source every 60 s, interleaved.
labels = []
for n in range(6):
    labels.append(hear(corpus.TX141_BURSTS[n % 3], 50.0 * n))
    labels.append(hear(corpus.MINUTE_SOURCE_BURSTS[n % 3], 60.0 * n + 7))
check(labels == ["Source A", "Source B"] * 6, f"grouping: {labels}")
sensor, other = sorted(tracker.sources, key=lambda s: s.number)
check(sensor.count == 6 and sensor.shape is not None, "sensor count")
check(round(sensor.period_s() or 0) == 50, f"sensor period {sensor.period_s()}")
check(round(other.period_s() or 0) == 60, f"other period {other.period_s()}")
check(sensor.describe().startswith("~"), sensor.describe())

# A burst caught in two receptions is one transmission, not two.
hear(corpus.TX141_BURSTS[0], 300.0)
hear(corpus.TX141_BURSTS[1], 300.5)
check(len(sensor.bursts) == 7 and sensor.count == 8, "a burst split in two counted twice")
# Too short to tell: no source. Another radio: its own sources.
check(hear([400, -1200, 400, -1200], 301) is None, "short noise got a source")
check(hear(corpus.TX141_BURSTS[1], 302, radio="rx2") == "Source C", "other radio shared a source")

# Unknown codes group by code; a weak frame one bit off joins its code.
check(hear(corpus.CANOPY_OPEN_FRAME, 400) == "Source D", "first code")
check(hear(corpus.CANOPY_OPEN_FRAME, 400.06) == "Source D", "same code")
check(hear(corpus.CANOPY_STOP_FRAME, 401) == "Source E", "another code")
check(tracker.get(tracker.sources[0].id) is tracker.sources[0], "get by id")
code = next(s for s in tracker.sources if s.label == "Source D")
check(code.describe() == "40-bit pwm …00110011", code.describe())
check(code.period_s() is None, "a button press has no period")

# Only the most recent sources are kept.
small = SourceTracker(max_sources=2)
for n, timings in enumerate([corpus.CANOPY_OPEN_FRAME, corpus.CANOPY_STOP_FRAME, corpus.EV1527_A]):
    small.observe("rx", F433, analyze(timings), timings, float(n))
check([s.number for s in small.sources] == [3, 2], "oldest source not dropped")

# --- Ignoring -----------------------------------------------------------------

data = ClickerData()
entry = edit.ignore_source(data, sensor.ignore_entry(" Neighbour's sensor "))
check(entry.name == "Neighbour's sensor" and entry.fingerprint is None, "ignore entry")
check(sensor.ignored_by(data.ignored) is entry, "sensor not ignored")
check(other.ignored_by(data.ignored) is None, "ignoring the sensor hid the other source")
# A sensor heard after a restart is still ignored: compared by shape, on its frequency.
restored = ClickerData.from_dict(data.to_dict())
later = shape_of(corpus.TX141_BURSTS[2])
check(restored.ignored[0].covers(F433, None, later), "ignored shape lost in storage")
check(not restored.ignored[0].covers(315_000_000, None, later), "ignored on another frequency")
code_entry = edit.ignore_source(data, code.ignore_entry())
check(code_entry.fingerprint == code.fingerprint and code_entry.shape is None, "code entry")
check(code_entry.covers(F433, code.fingerprint, None), "code not ignored")
check(not code_entry.covers(F433, "40b:other", None), "other code ignored")
check(IgnoredSource.from_dict(code_entry.to_dict()) == code_entry, "code entry storage")
edit.unignore_source(data, entry.id)
check(data.ignored == [code_entry], "unignore")
try:
    edit.unignore_source(data, entry.id)
    failures.append("unignoring twice: not refused")
except ModelError:
    pass
check("ignored" in ClickerData().to_dict(), "ignored list not stored")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all source tests passed")
