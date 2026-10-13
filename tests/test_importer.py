"""rf_device_manager importer tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_importer.py

Uses a synthetic storage file in rf_device_manager's format (schema 1) built
from the corpus captures, so no personal data lives in the repository.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core import rf_analysis as ra  # noqa: E402
from core.importer import import_rf_device_manager  # noqa: E402
from core.models import ClickerData, CommandKind, EncodedFrame, ModelError, RawFrame  # noqa: E402

F433 = 433_920_000
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def command(timings: list[int], repeat: int = 0) -> dict[str, object]:
    """One stored slot, as rf_device_manager writes it."""
    return {
        "protocol": "raw",
        "frequency": F433,
        "data": timings,
        "repeat": repeat,
        "fingerprint": ra.fingerprint(timings),
        "extra": {},
    }


def code(code_id: str, device: str, entity: str, slots: dict[str, list[int]], **extra: object):
    """One stored code (entity), as rf_device_manager writes it."""
    return {
        "id": code_id,
        "device_id": device,
        "name": code_id,
        "entity_type": entity,
        "enabled": True,
        "settings": {},
        "rf_data": {"commands": {slot: command(t) for slot, t in slots.items()}},
        **extra,
    }


HELD = corpus.HELD_CAPTURE
EV = corpus.EV1527_A
STORE = {
    "version": 1,
    "minor_version": 1,
    "key": "rf_device_manager",
    "data": {
        "devices": {
            "d1": {
                "id": "d1",
                "name": "living",
                "transmitter": "radio_frequency.hall_rf",
                "settings": {"description": "Living room", "frequency": F433, "default_repeat": 3},
            },
            "d2": {
                "id": "d2",
                "name": "garage",
                "transmitter": "radio_frequency.hall_rf",
                "settings": {"frequency": F433},
            },
        },
        "codes": {
            "light": code(
                "light",
                "d1",
                "light",
                {"on": HELD, "brightness_up": EV, "brightness_down": corpus.NOISE},
                description="Ceiling light",
            ),
            "shade": code("shade", "d1", "cover", {"open": HELD, "close": EV, "stop": HELD}),
            "old": code("old", "d1", "switch", {"on": HELD}, enabled=False),
            "lost": code("lost", "missing", "switch", {"on": HELD}),
            "door": code("door", "d2", "button", {"press": EV, "broken": [-500]}),
        },
    },
}

result = import_rf_device_manager(json.loads(json.dumps(STORE)), now=1_760_000_000.0)
data = result.data
for note in result.notes:
    print(f"- {note}")

check(data.problems() == [], f"imported data has problems: {data.problems()}")
check(ClickerData.from_dict(json.loads(json.dumps(data.to_dict()))) == data, "round trip")

# One radio for the shared transmitter + frequency; devices named from descriptions.
check(len(data.radios) == 1 and data.radios[0].transmitter == "radio_frequency.hall_rf", "radios")
living, garage = data.devices
check((living.name, garage.name) == ("Living room", "garage"), "device names")
check(living.radio_id == garage.radio_id == data.radios[0].id, "devices share the radio")

# Several codes on one device: command names are prefixed with the code name.
names = {c.name: c for c in living.commands}
check(set(names) >= {"Ceiling light On", "shade Open", "shade Stop"}, f"names {sorted(names)}")
check([c.name for c in garage.commands] == ["Press"], "single code: names not prefixed")

# Kinds and roles follow the slots.
check(names["Ceiling light On"].kind is CommandKind.TOGGLE, "on without off: not a toggle")
check(names["Ceiling light Brighter"].kind is CommandKind.BUTTON, "brightness step: not a button")
check(names["shade Open"].kind is CommandKind.STATE, "open: not a state")
check(names["shade Stop"].kind is CommandKind.BUTTON, "stop: not a button")
light = next(b for b in living.bindings if b.name == "Ceiling light")
check(light.platform == "light" and "toggle" in light.roles, f"light roles {light.roles}")
check(light.roles["toggle"] == names["Ceiling light On"].id, "role points to the wrong command")

# Codes re-encoded where they round-trip; noise kept raw; sources kept.
check(isinstance(names["shade Open"].frame, EncodedFrame), "held capture: not encoded")
check(isinstance(names["Ceiling light Dimmer"].frame, RawFrame), "noise: not kept raw")
check(names["shade Open"].captures[0].timings == tuple(HELD), "source capture not kept")
check(names["shade Open"].captures[0].received_at == 1_760_000_000.0, "import time not used")

# Notes: dropped settings, skipped codes, changed fingerprints.
notes = "\n".join(result.notes)
check("Living room: default repeat dropped" in notes, "default repeat note")
check("old: skipped, it was disabled" in notes, "disabled code note")
check("lost: skipped, its device is missing" in notes, "orphaned code note")
check("Broken: skipped, no usable timings" in notes, "unusable timings note")
check("Press: button, encoded, fingerprint 63b:" in notes, "63 -> 64 bit fingerprint change note")
check("shade Open: state, encoded, fingerprint kept" in notes, "kept fingerprint note")

try:
    import_rf_device_manager({"data": {"codes": {}}}, now=0.0)
    check(False, "a file without devices was accepted")
except ModelError:
    pass

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all importer tests passed")
