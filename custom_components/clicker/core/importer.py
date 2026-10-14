"""Import rf_device_manager's storage file (``.storage/rf_device_manager``).

Mapping:

- each rf_device_manager **device** becomes a Clicker :class:`Device`, plus
  one :class:`Radio` per transmitter + frequency it uses;
- each rf_device_manager **code** (one entity) becomes a :class:`Binding`
  on that device, with its slots as roles; a light's brightness steps go to
  a separate button binding, since they can't set an absolute brightness;
- each **slot** becomes a :class:`Command`, re-encoded from its stored
  capture (which is kept as the command's source capture). Its kind follows
  the slot: toggles (power, oscillate, an on code with no off code) are
  ``TOGGLE``, momentary actions (press, stop, brightness steps) ``BUTTON``,
  everything else ``STATE``.

Not carried over, and said so in the notes: repeat settings (Clicker counts
frames on air instead, and encoded codes don't need the workaround repeats),
icons, and disabled codes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import (
    Binding,
    Capture,
    ClickerData,
    Command,
    CommandKind,
    Device,
    EncodedFrame,
    ModelError,
    Radio,
    frame_from_capture,
)
from .receive import analyze_code

_TOGGLE_SLOTS = {"power", "oscillate"}
_BUTTON_SLOTS = {"press", "stop", "brightness_up", "brightness_down"}
_BRIGHTNESS_SLOTS = ("brightness_up", "brightness_down")
_SLOT_NAMES = {
    "on": "On",
    "off": "Off",
    "power": "Power",
    "oscillate": "Oscillate",
    "direction_forward": "Forward",
    "direction_reverse": "Reverse",
    "open": "Open",
    "close": "Close",
    "stop": "Stop",
    "press": "Press",
    "brightness_up": "Brighter",
    "brightness_down": "Dimmer",
}


@dataclass
class ImportResult:
    """The imported data and one line per notable decision."""

    data: ClickerData = field(default_factory=ClickerData)
    notes: list[str] = field(default_factory=list)


def _slot_name(slot: str) -> str:
    if slot in _SLOT_NAMES:
        return _SLOT_NAMES[slot]
    if slot.startswith("speed_"):
        return f"Speed {slot.removeprefix('speed_')}"
    for prefix in ("option:", "value:"):
        if slot.startswith(prefix):
            return slot.removeprefix(prefix)
    return slot.replace("_", " ").capitalize()


def _slot_kind(slot: str, slots: set[str]) -> tuple[CommandKind, str]:
    """Return a slot's command kind and its binding role."""
    if slot in _TOGGLE_SLOTS:
        return CommandKind.TOGGLE, slot
    if slot == "on" and "off" not in slots:
        return CommandKind.TOGGLE, "toggle"  # one code switches both ways
    if slot in _BUTTON_SLOTS:
        return CommandKind.BUTTON, slot
    return CommandKind.STATE, slot


def _radio_name(transmitter: str | None, frequency_hz: int) -> str:
    base = (transmitter or "").split(".", 1)[-1].replace("_", " ").strip() or "Radio"
    return f"{base} ({frequency_hz / 1e6:.2f} MHz)"


def import_rf_device_manager(store: dict[str, Any], *, now: float) -> ImportResult:
    """Convert rf_device_manager storage (the whole file or its ``data``)."""
    data = store.get("data", store)
    if not isinstance(data, dict) or "devices" not in data:
        raise ModelError("not an rf_device_manager storage file: no devices")
    result = ImportResult()
    radios: dict[tuple[str | None, int], Radio] = {}
    devices: dict[str, Device] = {}

    for raw_device in (data.get("devices") or {}).values():
        settings = raw_device.get("settings") or {}
        frequency = int(settings.get("frequency") or 0)
        transmitter = raw_device.get("transmitter") or None
        key = (transmitter, frequency)
        if key not in radios:
            radios[key] = Radio(
                name=_radio_name(transmitter, frequency),
                frequency_hz=frequency,
                transmitter=transmitter,
            )
        name = settings.get("description") or raw_device.get("name") or "Device"
        devices[raw_device["id"]] = Device(
            name=str(name), radio_id=radios[key].id, frequency_hz=frequency
        )
        if settings.get("default_repeat"):
            result.notes.append(f"{name}: default repeat dropped (Clicker counts frames on air)")

    codes = list((data.get("codes") or {}).values())
    for code in codes:
        device = devices.get(code.get("device_id", ""))
        code_name = str(code.get("description") or code.get("name") or "Code")
        if device is None:
            result.notes.append(f"{code_name}: skipped, its device is missing")
            continue
        if code.get("enabled") is False:
            result.notes.append(f"{code_name}: skipped, it was disabled")
            continue
        commands = (code.get("rf_data") or {}).get("commands") or {}
        slots = set(commands)
        prefix = (
            ""
            if sum(c.get("device_id") == code.get("device_id") for c in codes) == 1
            else code_name
        )
        binding = Binding(platform=str(code.get("entity_type") or "button"), name=code_name)
        for slot, raw_command in commands.items():
            label = " ".join(part for part in (prefix, _slot_name(slot)) if part)
            timings = [int(v) for v in raw_command.get("data") or []]
            try:
                frame = frame_from_capture(timings)
            except ModelError:
                result.notes.append(f"{device.name} / {label}: skipped, no usable timings")
                continue
            kind, role = _slot_kind(slot, slots)
            command = Command(name=label, kind=kind, frame=frame)
            command.add_capture(Capture(tuple(timings), device.radio_id, device.frequency_hz, now))
            device.commands.append(command)
            binding.roles[role] = command.id

            how = "encoded" if isinstance(frame, EncodedFrame) else f"kept raw ({frame.reason})"
            old, new = raw_command.get("fingerprint"), analyze_code(frame).fingerprint
            fingerprint = "fingerprint kept" if old == new else f"fingerprint {old} -> {new}"
            if raw_command.get("repeat"):
                fingerprint += "; repeat dropped"
            result.notes.append(f"{device.name} / {label}: {kind.value}, {how}, {fingerprint}")
        if (code.get("settings") or {}).get("icon"):
            result.notes.append(f"{code_name}: icon not imported")
        # Brightness steps can't give a light an absolute brightness: they
        # become buttons beside it.
        steps = {r: binding.roles.pop(r) for r in _BRIGHTNESS_SLOTS if r in binding.roles}
        if binding.roles:
            device.bindings.append(binding)
        if steps:
            device.bindings.append(Binding(platform="button", name=code_name, roles=steps))
            result.notes.append(f"{code_name}: brightness steps imported as buttons")

    result.data = ClickerData(radios=list(radios.values()), devices=list(devices.values()))
    return result


def merge_import(target: ClickerData, imported: ClickerData) -> list[str]:
    """Add imported devices to ``target`` and return one note per decision.

    An imported radio joins a stored one with the same transmitter reference,
    or else the only stored radio on its frequency; otherwise it is added and
    radio reconciliation links it later. A device whose name is already taken
    is skipped, so importing the same file twice changes nothing.
    """
    notes: list[str] = []
    radio_ids: dict[str, str] = {}
    for radio in imported.radios:
        same = [
            r for r in target.radios if radio.transmitter and r.transmitter == radio.transmitter
        ]
        if not same:
            same = [r for r in target.radios if r.frequency_hz == radio.frequency_hz]
        if len(same) == 1:
            radio_ids[radio.id] = same[0].id
            notes.append(f"{radio.name}: uses radio {same[0].name}")
        else:
            target.radios.append(radio)
            radio_ids[radio.id] = radio.id
            notes.append(f"{radio.name}: added as a new radio")

    taken = {device.name.casefold() for device in target.devices}
    for device in imported.devices:
        if device.name.casefold() in taken:
            notes.append(f"{device.name}: skipped, a device with that name exists")
            continue
        device.radio_id = radio_ids.get(device.radio_id, device.radio_id)
        target.devices.append(device)
        taken.add(device.name.casefold())
        notes.append(f"{device.name}: imported with {len(device.commands)} commands")
    used = {device.radio_id for device in target.devices}
    unused = [r for r in imported.radios if r in target.radios and r.id not in used]
    for radio in unused:  # every device on it was skipped
        target.radios.remove(radio)
    return notes
