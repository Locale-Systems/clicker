"""Learn-candidate grouping tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_learn.py
"""

from __future__ import annotations

import dataclasses
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core import rf_analysis as ra  # noqa: E402
from core.encoder import encode  # noqa: E402
from core.learn import LearnSession  # noqa: E402
from core.matcher import Matcher  # noqa: E402
from core.models import (  # noqa: E402
    ClickerData,
    Command,
    CommandKind,
    Device,
    EncodedFrame,
    Radio,
    RawFrame,
    frame_from_capture,
)

F433, F303 = 433_920_000, 303_870_000
HELD_BITS = "000001111000101100000011"
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


held = frame_from_capture(corpus.HELD_CAPTURE)
assert isinstance(held, EncodedFrame)


def press(bits: str, frames: int = 3) -> list[int]:
    """A held press of a button with these bits (the fan's timings)."""
    return encode(dataclasses.replace(held.spec, bits=bits)) * frames


BIT_ERROR = "000101111000101100000011"  # one bit off the real press
AGC_FRAME = ra.split_frames(ra.normalize(corpus.HELD_CAPTURE))[0]  # gain still settling
RAW_FRAME = [300, -700, 1100, -300, 500, -1500, 300, -300, 900, -600, 300, -1100, 400, -9000]


def raw_press(seed: int) -> list[int]:
    """A jittered press of a remote no decoder recognizes."""
    rng = random.Random(seed)
    return [round(v * (1 + rng.uniform(-0.05, 0.05))) for v in RAW_FRAME * 3]


# --- A typical session: one button, plus noise and a corrupted copy ----------

session = LearnSession(F433)
captures = [
    corpus.HELD_CAPTURE,  # the press, 6 good frames
    AGC_FRAME,  # the frame caught while the receiver's gain settled
    press(HELD_BITS, 2),  # the button still held
    corpus.NOISE,  # a noise burst
    press(BIT_ERROR, 1),  # a copy with a reception bit error
    press(HELD_BITS, 1),
]
for at, capture in enumerate(captures):
    session.add(capture, F433, float(at))
found = session.candidates()
for c in found:
    print(f"{c.fingerprint:<18} sightings={c.sightings} variants={c.variants} bits={c.bits}")
check(len(found) == 1, f"typical session: {len(found)} candidates, want 1")
top = found[0]
check(top.bits == HELD_BITS, "typical session: wrong top candidate")
check((top.sightings, top.variants) == (4, 2), "typical session: folding counts")
check((top.first_at, top.last_at) == (0.0, 5.0), "typical session: time span")
check(top.capture == tuple(corpus.HELD_CAPTURE), "best capture: not the one with most frames")
code = top.code()
check(isinstance(code, EncodedFrame) and code.bits == HELD_BITS, "code: not the encoded press")

# Arrival order doesn't matter: a corrupted copy first is still folded in.
session = LearnSession(F433)
for at, capture in enumerate([press(BIT_ERROR, 1), corpus.HELD_CAPTURE, press(HELD_BITS)]):
    session.add(capture, F433, float(at))
found = session.candidates()
check([c.bits for c in found] == [HELD_BITS], f"order: {[c.bits for c in found]}")

# Sibling buttons one or two bits apart, each pressed for real, stay apart.
POWER_BITS = "000001111000101100000001"  # the patio fan's Power; Nature is 2 bits away
session = LearnSession(F433)
for at, capture in enumerate(
    [press(POWER_BITS, 6), press(POWER_BITS, 6)] + [corpus.NATURE_CAPTURE] * 3
):
    session.add(capture, F433, float(at))
found = session.candidates()
check(
    sorted((c.bits, c.sightings, c.variants) for c in found)
    == sorted([(POWER_BITS, 2, 1), ("000001111000101100010000", 3, 1)]),
    f"siblings: {[(c.bits, c.sightings, c.variants) for c in found]}",
)

# --- What a session ignores --------------------------------------------------------

session = LearnSession(F433)
check(not session.add(corpus.HELD_CAPTURE, F303, 0.0), "other frequency: was used")
check(not session.add([400, -1200, 400], F433, 0.0), "too short: was used")
check(session.candidates() == [], "ignored captures produced candidates")

# --- Two different buttons both stay ----------------------------------------------

session = LearnSession(F433)
for at, capture in enumerate([corpus.HELD_CAPTURE, corpus.EV1527_A, corpus.EV1527_B]):
    session.add(capture, F433, float(at))
check(len(session.candidates()) == 2, "different buttons: one was lost")

# --- Remotes no decoder recognizes -------------------------------------------------

session = LearnSession(F433)
session.add(raw_press(1), F433, 0.0)
session.add(corpus.NOISE, F433, 1.0)
check(len(session.candidates()) == 2, "weak raw top: something was pruned")
for at in range(2, 5):
    session.add(raw_press(at), F433, float(at))
found = session.candidates()
check(len(found) == 1 and found[0].sightings == 4, "raw remote: jittered presses not grouped")
check(isinstance(found[0].code(), RawFrame), "raw remote: code should be raw")

# --- Already learned ------------------------------------------------------------------

radio = Radio(name="433", frequency_hz=F433)
power = Command(name="Power", kind=CommandKind.TOGGLE, frame=held)
fan = Device(name="Fan", radio_id=radio.id, frequency_hz=F433, commands=[power])
session = LearnSession(F433)
session.add(corpus.HELD_CAPTURE, F433, 0.0)
known = session.candidates(Matcher(ClickerData(radios=[radio], devices=[fan])))[0].known_as
check([m.command_id for m in known] == [power.id], "known: existing command not reported")
check(session.candidates()[0].known_as == (), "known: reported without a matcher")

# --- Cap --------------------------------------------------------------------------------

session = LearnSession(F433, max_candidates=3)
rng = random.Random(9)
for at in range(6):
    bits = "".join(rng.choice("01") for _ in range(24))
    session.add(press(bits), F433, float(at))
check(len(session.candidates()) == 3, "cap: not applied")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all learn tests passed")
