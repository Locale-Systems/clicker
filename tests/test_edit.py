"""Data editing tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_edit.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core import edit  # noqa: E402
from core.models import (  # noqa: E402
    Binding,
    ClickerData,
    Command,
    CommandKind,
    ModelError,
    Radio,
    frame_from_capture,
)

F433, F303 = 433_920_000, 303_870_000
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def refused(action: object, message: str) -> None:
    """Expect a callable to raise ModelError."""
    try:
        action()  # type: ignore[operator]
    except ModelError:
        return
    failures.append(f"{message}: not refused")


hall = Radio(name="Hall", frequency_hz=F433)
hall2 = Radio(name="Upstairs", frequency_hz=F433)
shed = Radio(name="Shed", frequency_hz=F303)
data = ClickerData(radios=[hall, hall2, shed])

# Devices: named uniquely, on a radio, at its frequency.
fan = edit.add_device(data, "  Patio fan ", hall.id, area_id="patio")
check(fan.name == "Patio fan" and fan.frequency_hz == F433 and fan.area_id == "patio", "add")
refused(lambda: edit.add_device(data, "patio FAN", hall.id), "duplicate device name")
refused(lambda: edit.add_device(data, " ", hall.id), "empty device name")
refused(lambda: edit.add_device(data, "Lamp", "nope"), "unknown radio")
lamp = edit.add_device(data, "Lamp", shed.id)

edit.update_device(data, fan.id, name="Patio Fan", radio_id=hall2.id)
check(fan.name == "Patio Fan" and fan.radio_id == hall2.id, "rename and move")
refused(lambda: edit.update_device(data, fan.id, radio_id=shed.id), "move across frequencies")
refused(lambda: edit.update_device(data, lamp.id, name="patio fan"), "rename onto a taken name")
check(lamp.name == "Lamp", "a refused rename changed the name")
fan.bindings = [Binding(platform="fan", name="patio fan"), Binding(platform="light", name="Light")]
edit.update_device(data, fan.id, name="Porch fan")
check([b.name for b in fan.bindings] == ["Porch fan", "Light"], "main binding not renamed")
fan.bindings = []
edit.update_device(data, fan.id, name="Patio Fan")
edit.update_device(data, fan.id, clear_area=True)
check(fan.area_id is None, "area not cleared")

# Commands: unique names per device; kind and frames editable.
power = edit.add_command(
    fan,
    Command(name="Power", kind=CommandKind.TOGGLE, frame=frame_from_capture(corpus.HELD_CAPTURE)),
)
speed = edit.add_command(
    fan, Command(name="Speed 1", kind=CommandKind.STATE, frame=frame_from_capture(corpus.EV1527_A))
)
refused(
    lambda: edit.add_command(
        fan, Command(name="power", kind=CommandKind.BUTTON, frame=power.frame)
    ),
    "duplicate command name",
)
edit.update_command(data, fan.id, speed.id, name="Low", kind=CommandKind.BUTTON, frames_on_air=1)
check(
    (speed.name, speed.kind, speed.policy.frames_on_air) == ("Low", CommandKind.BUTTON, 1), "edit"
)
refused(lambda: edit.update_command(data, fan.id, speed.id, frames_on_air=0), "zero frames")
refused(lambda: edit.update_command(data, fan.id, speed.id, name="POWER"), "rename onto taken")
check(speed.name == "Low" and speed.policy.frames_on_air == 1, "a refused edit changed things")
refused(lambda: edit.update_command(data, lamp.id, speed.id, name="x"), "command of another device")

# Deleting a command cleans the bindings that used it.
fan.bindings = [
    Binding(platform="fan", name="Fan", roles={"power": power.id, "speed_1": speed.id}),
    Binding(platform="button", name="Low", roles={"press": speed.id}),
]
edit.delete_command(data, fan.id, speed.id)
check([c.name for c in fan.commands] == ["Power"], "command not deleted")
check([(b.name, b.roles) for b in fan.bindings] == [("Fan", {"power": power.id})], "bindings")
check(data.problems() == [], f"problems after delete: {data.problems()}")

# Radios: renamed freely, deleted only when unused.
edit.rename_radio(data, hall.id, "Garage")
check(hall.name == "Garage", "radio rename")
refused(lambda: edit.delete_radio(data, shed.id), "deleting a radio in use")
edit.delete_device(data, lamp.id)
edit.delete_radio(data, shed.id)
check(shed not in data.radios and lamp not in data.devices, "delete")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all edit tests passed")
