"""On/off remote rules (lights, switches) - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_onoff.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "clicker"))

from core.models import ModelError  # noqa: E402
from core.onoff import OnOffRemote  # noqa: E402

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def roles(plan: tuple[list, bool]) -> list[str]:  # type: ignore[type-arg]
    return [step.role for step in plan[0]]


# A toggle (the Minka Aire's light): sent only to change the state.
toggle = OnOffRemote(["toggle"])
check(roles(toggle.set(False, True)) == ["toggle"] and toggle.set(False, True)[1], "on")
check(roles(toggle.set(True, True)) == [], "already on: a toggle must not be sent")
check(roles(toggle.set(True, False)) == ["toggle"], "off")
check(roles(toggle.set(False, False)) == [], "already off")
check(toggle.pressed(False, "toggle") and not toggle.pressed(True, "toggle"), "presses flip")
check(roles(OnOffRemote(["power"]).set(False, True)) == ["power"], "power is a toggle too")

# Explicit buttons: always sent, presses set the state.
explicit = OnOffRemote(["on", "off", "toggle"])
check(roles(explicit.set(True, True)) == ["on"], "explicit on is always sent")
check(roles(explicit.set(False, False)) == ["off"], "explicit off is always sent")
check(explicit.pressed(False, "on") and not explicit.pressed(True, "off"), "explicit presses")
check(explicit.pressed(True, "brightness_up"), "other roles change nothing")

for bad in (["on"], ["off"], ["brightness_up"]):
    try:
        OnOffRemote(bad)
        failures.append(f"{bad}: not refused")
    except ModelError:
        pass

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all on/off tests passed")
