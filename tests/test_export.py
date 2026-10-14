"""rtl_433 pulse-file export - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_export.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core.export import END_GAP_US, packets_for, pulse_pairs, to_ook  # noqa: E402
from core.receive import analyze  # noqa: E402

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def read_ook(text: str) -> list[list[tuple[int, int]]]:
    """Parse a pulse file back into its packets, as rtl_433 reads it."""
    packets: list[list[tuple[int, int]]] = []
    current: list[tuple[int, int]] | None = None
    for line in text.splitlines():
        if line == ";pulse data":
            current = []
        elif line == ";end":
            assert current is not None
            packets.append(current)
            current = None
        elif not line.startswith(";"):
            assert current is not None, "pulse outside a packet"
            pulse, gap = line.split()
            current.append((int(pulse), int(gap)))
    check(current is None, "unterminated packet")
    return packets


def timings(pairs: list[tuple[int, int]]) -> list[int]:
    return [v for pulse, gap in pairs for v in (pulse, -gap)]


# Pulse pairs start with a pulse and end on a gap long enough to end a packet.
pairs = pulse_pairs([-5000, 400, -1200, 1200, -400, 400])
check(pairs == ((400, 1200), (1200, 400), (400, END_GAP_US)), f"pairs {pairs}")
check(pulse_pairs([400, 1200, 1200, 400]) == ((400, 1200), (1200, END_GAP_US)), "unsigned input")
check(pulse_pairs([]) == (), "empty capture")

# A remote Clicker decodes: the capture as received, then a cleaned packet.
awning = packets_for([tuple(corpus.CANOPY_OPEN_FRAME)])
check(
    [p.title.split(",")[0] for p in awning] == ["capture 1 of 1", "cleaned by Clicker: 40-bit pwm"],
    f"{[p.title for p in awning]}",
)
text = to_ook(awning, 433_920_000, ["export of the awning", "decode: rtl_433 -r FILE"])
raw, clean = read_ook(text)
check(analyze(timings(raw)).bits == corpus.CANOPY_OPEN, "raw packet lost the code")
cleaned = analyze(timings(clean))
check(cleaned.bits == corpus.CANOPY_OPEN, "cleaned packet decodes to another code")
check(cleaned.agreeing_frames == cleaned.complete_frames == 4, "cleaned repeats should all agree")
check(text.count(";clicker export of the awning") == 1, "notes head the file once")
check(text.count(";freq1 433920000") == 2 and text.count(";end") == 2, "packet headers")
check(text.startswith(";pulse data\n;version 1\n;timescale 1us\n"), "file header")

# A source Clicker can't decode: only its captures, as received.
sensor = packets_for([tuple(t) for t in corpus.TX141_BURSTS])
check(len(sensor) == 3 and all("as received" in p.title for p in sensor), "undecodable source")
check(
    [timings(list(p)) for p in read_ook(to_ook(sensor, 433_920_000, []))]
    == [timings(list(p.pairs)) for p in sensor],
    "pulse file does not round-trip",
)

# The cleaned packet comes from the latest capture that decodes.
mixed = packets_for([tuple(corpus.CANOPY_OPEN_FRAME), tuple(corpus.NOISE)])
check(len(mixed) == 3 and mixed[-1].title.startswith("cleaned"), "cleaned from an earlier capture")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all export tests passed")
