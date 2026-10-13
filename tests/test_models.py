"""Data model tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_models.py
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core import rf_analysis as ra  # noqa: E402
from core.encoder import ENCODER_VERSION, CodeSpec, encode  # noqa: E402
from core.models import (  # noqa: E402
    MAX_CAPTURES_PER_COMMAND,
    SCHEMA_VERSION,
    Binding,
    Capture,
    ClickerData,
    Command,
    CommandKind,
    Device,
    EncodedFrame,
    ModelError,
    Radio,
    RawFrame,
    SendPolicy,
    frame_from_capture,
)

HELD_BITS = "000001111000101100000011"
F433 = 433_920_000
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def raises(func: object, message: str) -> None:
    """Expect a ModelError from calling ``func``."""
    try:
        func()  # type: ignore[operator]
    except ModelError:
        return
    failures.append(message)


def sample_data() -> ClickerData:
    """A radio and a fan with an encoded, a raw and a bound command."""
    radio = Radio(name="wESP32 433", frequency_hz=F433, transmitter="radio_frequency.rf_tx")
    power = Command(
        name="Power",
        kind=CommandKind.TOGGLE,
        frame=frame_from_capture(corpus.HELD_CAPTURE),
        captures=[Capture(tuple(corpus.HELD_CAPTURE), radio.id, F433, 1_760_000_000.0)],
    )
    noise = Command(
        name="Mystery",
        kind=CommandKind.BUTTON,
        frame=frame_from_capture(corpus.NOISE),
        policy=SendPolicy(frames_on_air=1),
    )
    fan = Device(
        name="Patio fan",
        radio_id=radio.id,
        frequency_hz=F433,
        area_id="patio",
        commands=[power, noise],
        bindings=[Binding(platform="fan", name="Patio fan", roles={"power": power.id})],
    )
    return ClickerData(radios=[radio], devices=[fan])


# --- Frames built from captures --------------------------------------------

held = frame_from_capture(corpus.HELD_CAPTURE)
check(isinstance(held, EncodedFrame), "held capture: not encoded")
check(held.bits == HELD_BITS, f"held capture: bits {held.bits}")
check(held.frames_per_unit == 1, "encoded frame: unit is not one frame")
if isinstance(held, EncodedFrame):
    check(held.unit() == encode(held.spec), "encoded frame: unit differs from encode()")
    check(held.encoder_version == ENCODER_VERSION, "encoded frame: encoder version")
    check(len(held.unit()) == 50, f"encoded frame: {len(held.unit())} timings, want 50")

noise = frame_from_capture(corpus.NOISE)
check(isinstance(noise, RawFrame), "noise: not raw")
check(bool(getattr(noise, "reason", "")), "raw frame: no reason recorded")
check(
    noise.unit() == ra.trim_partial_frames(ra.normalize(corpus.NOISE)),
    "raw frame: timings changed",
)
raises(lambda: frame_from_capture([]), "empty capture: not refused")

# --- JSON round trip ---------------------------------------------------------

data = sample_data()
stored = json.loads(json.dumps(data.to_dict()))
check(stored["version"] == SCHEMA_VERSION, "to_dict: version missing")
check(ClickerData.from_dict(stored) == data, "round trip: loaded data differs")
spec = CodeSpec(encoding="pwm", bits="01", zero=(400, 1200), one=(1200, 400), sync=(400, 12000))
check(CodeSpec.from_dict(json.loads(json.dumps(spec.to_dict()))) == spec, "CodeSpec: round trip")

# Unknown keys are ignored; missing optional keys take defaults.
stored["future_field"] = True
stored["devices"][0]["future_field"] = {"x": 1}
check(ClickerData.from_dict(stored) == data, "unknown keys: not ignored")
minimal = {"devices": [{"id": "d1", "name": "Fan", "radio_id": "r1", "frequency_hz": F433}]}
loaded = ClickerData.from_dict(minimal)
check(loaded.devices[0].commands == [] and loaded.radios == [], "defaults: not applied")
power_dict = data.devices[0].commands[0].to_dict()
check(Command.from_dict({**power_dict, "policy": None}).policy == SendPolicy(), "policy default")

# Bad or newer data is refused, not misread.
raises(lambda: ClickerData.from_dict({"version": SCHEMA_VERSION + 1}), "newer schema: not refused")
raises(lambda: Device.from_dict({"name": "Fan"}), "missing id: not refused")
raises(lambda: Command.from_dict({**power_dict, "kind": "spin"}), "unknown kind: not refused")
raises(
    lambda: Command.from_dict({**power_dict, "frame": {"kind": "zip"}}),
    "unknown frame: not refused",
)

# --- Rules ---------------------------------------------------------------------

check(data.problems() == [], f"valid data reported problems: {data.problems()}")
raises(lambda: SendPolicy(frames_on_air=0), "frames_on_air 0: not refused")
raises(lambda: SendPolicy(frames_on_air=65), "frames_on_air 65: not refused")

broken = sample_data()
fan = broken.devices[0]
fan.commands.append(Command(name="power", kind=CommandKind.BUTTON, frame=held))
fan.bindings[0].roles["oscillate"] = "missing-id"
fan.frequency_hz = 303_870_000
issues = broken.problems()
check(any("more than one command named 'power'" in p for p in issues), "duplicate names not found")
check(
    any("'oscillate' points to a missing command" in p for p in issues),
    "dangling binding not found",
)
check(any("does not match radio" in p for p in issues), "frequency mismatch not found")
fan.radio_id = "gone"
check(any("unknown radio" in p for p in broken.problems()), "unknown radio not found")

# Captures are capped, oldest dropped first.
command = Command(name="Speed 1", kind=CommandKind.STATE, frame=held)
for n in range(MAX_CAPTURES_PER_COMMAND + 3):
    command.add_capture(Capture((400, -1200), "r1", F433, float(n)))
check(len(command.captures) == MAX_CAPTURES_PER_COMMAND, "captures: not capped")
check(command.captures[0].received_at == 3.0, "captures: wrong ones dropped")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all model tests passed")
