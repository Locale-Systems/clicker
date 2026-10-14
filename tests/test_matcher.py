"""Matcher tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_matcher.py
"""

from __future__ import annotations

import dataclasses
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core.encoder import encode  # noqa: E402
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
from core.receive import FrameChain, analyze  # noqa: E402

F433, F303 = 433_920_000, 303_870_000
POWER = "000001111000101100000011"  # the patio fan's real code
SPEED_1 = "000001111000101100000010"  # sibling buttons: 1-2 bits apart
SPEED_2 = "000001111000101100000111"
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


held = frame_from_capture(corpus.HELD_CAPTURE)
assert isinstance(held, EncodedFrame)


def code(bits: str) -> EncodedFrame:
    """The held fan code's timings carrying other bits."""
    return EncodedFrame(spec=dataclasses.replace(held.spec, bits=bits))


def press(frame: EncodedFrame, frames: int = 3) -> list[int]:
    """What a receiver hears when the button is held for a few frames."""
    return encode(frame.spec) * frames


RAW_FRAME = [300, -700, 1100, -300, 500, -1500, 300, -300, 900, -600, 300, -1100, 400, -9000]
OTHER_RAW_FRAME = [900, -600, 300, -1100, 300, -700, 1100, -300, 500, -1500, 300, -300, 400, -9000]


def raw_pattern(frame: list[int] = RAW_FRAME, scale: float = 1.0, seed: int = 0) -> list[int]:
    """Three frames of a code no decoder recognizes, optionally scaled or jittered."""
    rng = random.Random(seed)
    jitter = 0.0 if seed == 0 else 0.05
    return [round(v * scale * (1 + rng.uniform(-jitter, jitter))) for v in frame * 3]


radio_433 = Radio(name="433", frequency_hz=F433)
radio_303 = Radio(name="303", frequency_hz=F303)
power = Command(name="Power", kind=CommandKind.TOGGLE, frame=code(POWER))
speed_1 = Command(name="Speed 1", kind=CommandKind.STATE, frame=code(SPEED_1))
speed_2 = Command(name="Speed 2", kind=CommandKind.STATE, frame=code(SPEED_2))
patio = Device(
    name="Patio fan", radio_id=radio_433.id, frequency_hz=F433, commands=[power, speed_1, speed_2]
)
minka_power = Command(name="Power", kind=CommandKind.TOGGLE, frame=code(POWER))
minka = Device(name="Minka", radio_id=radio_303.id, frequency_hz=F303, commands=[minka_power])
mystery = frame_from_capture(raw_pattern())
check(isinstance(mystery, RawFrame), "fixture: raw pattern should not encode")
shade_cmd = Command(name="Up", kind=CommandKind.BUTTON, frame=mystery)
shade = Device(name="Shade", radio_id=radio_433.id, frequency_hz=F433, commands=[shade_cmd])
data = ClickerData(radios=[radio_433, radio_303], devices=[patio, minka, shade])
matcher = Matcher(data)


def heard(timings: list[int], frequency: int = F433) -> set[tuple[str, str]]:
    """Which (device, command) pairs a capture identifies, ignoring time."""
    return {(m.device_id, m.command_id) for m in matcher.candidates(analyze(timings), frequency)}


# --- Identification ------------------------------------------------------------

check(heard(corpus.HELD_CAPTURE) == {(patio.id, power.id)}, "real press: not the patio power")
check(heard(press(code(POWER)), F303) == {(minka.id, minka_power.id)}, "303 MHz: not the Minka")
check(heard(press(code(SPEED_1))) == {(patio.id, speed_1.id)}, "sibling: not exactly speed 1")
check(heard(press(code(SPEED_2))) == {(patio.id, speed_2.id)}, "sibling: not exactly speed 2")
one_bit_off = "000101111000101100000011"  # bit error far from the siblings' bits
# A single frame can carry a reception bit error: the nearest command matches.
check(heard(press(code(one_bit_off), 1)) == {(patio.id, power.id)}, "bit error: not the nearest")
# Frames that agree are certain: one bit off is another button, not an error.
check(heard(press(code(one_bit_off))) == set(), "reliable near miss: matched")
check(heard(corpus.EV1527_A) == set(), "unrelated 64-bit code matched something")
check(heard(raw_pattern(seed=3)) == {(shade.id, shade_cmd.id)}, "raw code: jittered press missed")
check(heard(raw_pattern(OTHER_RAW_FRAME)) == set(), "raw code: a different pattern matched")
# Matching is relative to a code's own base pulse, so the same pattern played
# slower is the same code (as decoded bits are, whatever the pulse length).
check(heard(raw_pattern(scale=1.6)) == {(shade.id, shade_cmd.id)}, "raw code: slower press missed")
nearest = matcher.candidates(analyze(press(code(one_bit_off), 1)), F433)[0]
check(nearest.distance == 1 and nearest.kind is CommandKind.TOGGLE, "match details")

# The real patio fan remote: its unlearned Nature button is one bit from Speed 4.
SPEED_4 = "000001111000101100010001"
fan_speed_4 = Command(name="Speed 4", kind=CommandKind.STATE, frame=code(SPEED_4))
fan = Device(name="Fan", radio_id=radio_433.id, frequency_hz=F433, commands=[fan_speed_4])
fan_matcher = Matcher(ClickerData(radios=[radio_433], devices=[fan]))
nature = analyze(corpus.NATURE_CAPTURE)
check(nature.reliable and nature.bits == SPEED_4[:-1] + "0", "fixture: Nature decode")
check(fan_matcher.candidates(nature, F433) == [], "Nature button matched Speed 4")
check(bool(fan_matcher.candidates(analyze(press(code(SPEED_4))), F433)), "Speed 4 missed")

# --- One press, one match ---------------------------------------------------------

reception = analyze(press(code(POWER)))
fired = [bool(matcher.match(reception, F433, at)) for at in (0.0, 0.3, 0.6, 0.9, 1.5)]
check(fired == [True, False, False, False, True], f"debounce: fired {fired}")
other = analyze(press(code(SPEED_1)))
check(bool(matcher.match(other, F433, 1.6)), "debounce: another button was blocked")

# --- Clicker's own transmission ------------------------------------------------------

matcher.note_transmission(F433, at=10.0, airtime_s=0.41)
check(matcher.match(reception, F433, 10.5) == [], "echo: own send matched")
check(bool(matcher.match(analyze(press(code(POWER))), F303, 10.5)), "echo: other band blocked")
check(bool(matcher.match(reception, F433, 11.0)), "echo: matching did not resume")

# --- Re-indexing ----------------------------------------------------------------------

speed_3 = Command(name="Speed 3", kind=CommandKind.STATE, frame=code("110100101010010111001010"))
patio.commands.append(speed_3)
check(heard(press(speed_3.frame)) == set(), "before rebuild: new command already matched")
matcher.rebuild(data)
check(heard(press(speed_3.frame)) == {(patio.id, speed_3.id)}, "after rebuild: not matched")


# --- Remotes that send one frame per reception ----------------------------------------

# The patio canopy remote: every frame arrives on its own. Open sends ...33
# then its release code ...3c, which is 4 bits from Open and from Stop alike.
canopy_open = Command(
    name="Open", kind=CommandKind.BUTTON, frame=frame_from_capture(corpus.CANOPY_OPEN_FRAME)
)
canopy_stop = Command(
    name="Stop", kind=CommandKind.BUTTON, frame=frame_from_capture(corpus.CANOPY_STOP_FRAME)
)
check(isinstance(canopy_open.frame, EncodedFrame), "canopy: Open should store encoded")
canopy = Device(
    name="Canopy", radio_id=radio_433.id, frequency_hz=F433, commands=[canopy_open, canopy_stop]
)
canopy_matcher = Matcher(ClickerData(radios=[radio_433], devices=[canopy]))
# A weak reception as near to two of a device's commands is ambiguous.
release = analyze(corpus.CANOPY_RELEASE_FRAME)
check(canopy_matcher.candidates(release, F433) == [], "canopy: release code matched a button")
chain = FrameChain()
fired_names: list[str] = []
names = {canopy_open.id: "Open", canopy_stop.id: "Stop"}
presses = [(corpus.CANOPY_OPEN_FRAME, 0.06 * n) for n in range(4)]
presses += [(corpus.CANOPY_RELEASE_FRAME, 0.27 + 0.06 * n) for n in range(4)]
presses += [(corpus.CANOPY_STOP_DROPPED, 2.0)]
presses += [(corpus.CANOPY_STOP_FRAME, 2.06 + 0.06 * n) for n in range(3)]
for timings, at in presses:
    for match in canopy_matcher.match(chain.add("rx", analyze(timings), at), F433, at):
        fired_names.append(names[match.command_id])
check(fired_names == ["Open", "Stop"], f"canopy: fired {fired_names}")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all matcher tests passed")
