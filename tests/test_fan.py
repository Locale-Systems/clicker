"""Fan remote rules - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_fan.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "clicker"))

from core.fan import POWER_UP_PAUSE_S, FanRemote, FanState, Step  # noqa: E402
from core.models import ModelError  # noqa: E402

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def roles(plan: tuple[list[Step], FanState]) -> list[str]:
    return [step.role for step in plan[0]]


def refused(action: object, message: str) -> None:
    try:
        action()  # type: ignore[operator]
    except ModelError:
        return
    failures.append(f"{message}: not refused")


OFF, ON = FanState(), FanState(on=True, speed=2)

# --- The patio fan: power toggle, 4 speeds, oscillation toggle ----------------

patio = FanRemote(["power", "speed_1", "speed_2", "speed_3", "speed_4", "oscillate"])
check(patio.speed_count == 4 and patio.can_oscillate and not patio.can_reverse, "features")

check(roles(patio.turn_on(OFF)) == ["power"], "on from off: power only (fan resumes)")
check(patio.turn_on(FanState(speed=3))[1] == FanState(on=True, speed=3), "resume keeps speed")
check(roles(patio.turn_on(ON)) == [], "on when on: a toggle must not be sent")
steps, state = patio.turn_on(OFF, 3)
check([s.role for s in steps] == ["power", "speed_3"], "on at speed from off: power, then speed")
check(steps[0].pause_after_s == POWER_UP_PAUSE_S, "no power-up pause before the speed")
check(state == FanState(on=True, speed=3), "on at speed: state")
check(roles(patio.set_speed(ON, 4)) == ["speed_4"], "speed when on: speed only")
check(roles(patio.turn_off(ON)) == ["power"], "off when on: power")
check(roles(patio.turn_off(OFF)) == [], "off when off: nothing")
check(roles(patio.set_speed(ON, 0)) == ["power"], "speed 0: off")
check(patio.turn_off(ON)[1] == FanState(on=False, speed=2), "off keeps the last speed")

check(roles(patio.oscillate(ON, True)) == ["oscillate"], "oscillate on")
check(roles(patio.oscillate(FanState(on=True, oscillating=True), True)) == [], "already on")
refused(lambda: patio.set_direction(ON, True), "direction without buttons")
refused(lambda: patio.set_speed(ON, 5), "speed above the top")

# Remote presses.
check(patio.pressed(OFF, "power") == FanState(on=True), "power press from off")
check(patio.pressed(ON, "power") == FanState(on=False, speed=2), "power press from on")
check(patio.pressed(OFF, "speed_3") == FanState(on=True, speed=3), "speed press")
check(patio.pressed(ON, "oscillate").oscillating, "oscillate press")
check(patio.pressed(ON, "unknown") == ON, "other roles change nothing")

# --- The Minka Aire: off + 6 speeds, a reverse toggle ----------------------------

minka = FanRemote(["off", "direction"] + [f"speed_{n}" for n in range(1, 7)])
check(minka.speed_count == 6 and minka.can_reverse and not minka.can_oscillate, "Minka features")
check(roles(minka.turn_on(OFF)) == ["speed_6"], "on, never run: the top speed")
check(roles(minka.turn_on(FanState(speed=2))) == ["speed_2"], "on resumes the last speed")
check(roles(minka.turn_on(OFF, 4)) == ["speed_4"], "speed buttons switch it on")
check(roles(minka.turn_off(OFF)) == ["off"], "an off button is always safe to send")
check(roles(minka.set_direction(ON, True)) == ["direction"], "reverse")
check(roles(minka.set_direction(FanState(reverse=True), True)) == [], "already reversed")
check(minka.pressed(ON, "direction").reverse, "reverse press")
check(minka.pressed(ON, "off") == FanState(on=False, speed=2), "off press")

# --- Explicit buttons everywhere ----------------------------------------------

explicit = FanRemote(
    ["on", "off", "oscillate_on", "oscillate_off", "direction_forward", "direction_reverse"]
)
check(explicit.speed_count == 0, "no speeds")
check(roles(explicit.turn_on(ON)) == ["on"], "explicit on is always sent")
check(roles(explicit.oscillate(FanState(oscillating=True), True)) == ["oscillate_on"], "osc on")
check(roles(explicit.set_direction(ON, False)) == ["direction_forward"], "forward")
check(not explicit.pressed(FanState(oscillating=True), "oscillate_off").oscillating, "osc off")

# --- Unusable sets of buttons -------------------------------------------------------

refused(lambda: FanRemote(["speed_1", "speed_2"]), "speeds without any way to switch off")
refused(lambda: FanRemote(["on"]), "on without off")
refused(lambda: FanRemote(["power", "speed_1", "speed_3"]), "a gap in the speeds")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all fan tests passed")
