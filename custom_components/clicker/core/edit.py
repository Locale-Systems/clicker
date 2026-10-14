"""Changes to stored data, with the rules that keep it consistent.

Every function changes ``ClickerData`` in place or raises ``ModelError``
without changing anything. The rules:

- device names are unique (ignoring case), and so are command names within
  a device, because actions find them by name;
- a device's frequency is its radio's: a device moves only to a radio on the
  same frequency, since its codes were learned there;
- deleting a command removes it from the bindings that use it (and drops a
  binding left with no roles); a radio can be deleted only once no device
  uses it;
- a binding's roles point at its own device's commands, and its platform's
  rules must accept them (a fan needs a way to switch off, ...); binding
  names are unique per device and platform. Deleting a binding keeps its
  commands.
"""

from __future__ import annotations

from .fan import FanRemote
from .models import (
    Binding,
    ClickerData,
    Command,
    CommandKind,
    Device,
    ModelError,
    Radio,
    SendPolicy,
)
from .onoff import OnOffRemote

PLATFORMS = ("fan", "light", "switch", "button")


class NotFoundError(ModelError):
    """The device, command or radio asked for doesn't exist."""


def _name(name: str, what: str) -> str:
    name = name.strip()
    if not name:
        raise ModelError(f"{what} name can't be empty")
    return name


def _check_device_name(data: ClickerData, name: str, device: Device | None = None) -> str:
    name = _name(name, "device")
    if any(d is not device and d.name.casefold() == name.casefold() for d in data.devices):
        raise ModelError(f"a device named {name!r} already exists")
    return name


def _check_command_name(device: Device, name: str, command: Command | None = None) -> str:
    name = _name(name, "command")
    if any(c is not command and c.name.casefold() == name.casefold() for c in device.commands):
        raise ModelError(f"{device.name} already has a command named {name!r}")
    return name


def get_device(data: ClickerData, device_id: str) -> Device:
    """Return a device, or raise ``NotFoundError``."""
    if (device := data.device(device_id)) is None:
        raise NotFoundError(f"no device {device_id!r}")
    return device


def get_command(device: Device, command_id: str) -> Command:
    """Return a device's command, or raise ``NotFoundError``."""
    if (command := device.command(command_id)) is None:
        raise NotFoundError(f"{device.name} has no command {command_id!r}")
    return command


def get_radio(data: ClickerData, radio_id: str) -> Radio:
    """Return a radio, or raise ``NotFoundError``."""
    if (radio := data.radio(radio_id)) is None:
        raise NotFoundError(f"no radio {radio_id!r}")
    return radio


def add_device(
    data: ClickerData, name: str, radio_id: str, *, area_id: str | None = None
) -> Device:
    """Add a device on a radio (taking the radio's frequency)."""
    radio = get_radio(data, radio_id)
    device = Device(
        name=_check_device_name(data, name),
        radio_id=radio.id,
        frequency_hz=radio.frequency_hz,
        area_id=area_id,
    )
    data.devices.append(device)
    return device


def update_device(
    data: ClickerData,
    device_id: str,
    *,
    name: str | None = None,
    area_id: str | None = None,
    clear_area: bool = False,
    radio_id: str | None = None,
) -> Device:
    """Rename a device, set or clear its area, or move it to another radio.

    Bindings named after the device are renamed with it, so its main entity
    keeps showing just the device name.
    """
    device = get_device(data, device_id)
    new_name = _check_device_name(data, name, device) if name is not None else device.name
    radio = get_radio(data, radio_id) if radio_id is not None else None
    if radio is not None and radio.frequency_hz != device.frequency_hz:
        raise ModelError(
            f"{device.name} is on {device.frequency_hz} Hz; radio {radio.name!r} is on "
            f"{radio.frequency_hz} Hz"
        )
    for binding in device.bindings:
        # A binding named like its device is the device's main entity: keep it so.
        if binding.name.casefold() == device.name.casefold():
            binding.name = new_name
    device.name = new_name
    if clear_area:
        device.area_id = None
    elif area_id is not None:
        device.area_id = area_id
    if radio is not None:
        device.radio_id = radio.id
    return device


def delete_device(data: ClickerData, device_id: str) -> Device:
    """Remove a device with its commands and bindings."""
    device = get_device(data, device_id)
    data.devices.remove(device)
    return device


def add_command(device: Device, command: Command) -> Command:
    """Add a new command to a device (its name must be free)."""
    command.name = _check_command_name(device, command.name)
    device.commands.append(command)
    return command


def update_command(
    data: ClickerData,
    device_id: str,
    command_id: str,
    *,
    name: str | None = None,
    kind: CommandKind | None = None,
    frames_on_air: int | None = None,
) -> Command:
    """Rename a command, change its kind or how many frames it sends."""
    device = get_device(data, device_id)
    command = get_command(device, command_id)
    new_name = _check_command_name(device, name, command) if name is not None else command.name
    policy = SendPolicy(frames_on_air=frames_on_air) if frames_on_air is not None else None
    command.name = new_name
    if kind is not None:
        command.kind = kind
    if policy is not None:
        command.policy = policy
    return command


def delete_command(data: ClickerData, device_id: str, command_id: str) -> Command:
    """Remove a command and every binding role that used it."""
    device = get_device(data, device_id)
    command = get_command(device, command_id)
    device.commands.remove(command)
    for binding in device.bindings:
        binding.roles = {role: cid for role, cid in binding.roles.items() if cid != command.id}
    device.bindings = [b for b in device.bindings if b.roles]
    return command


def rename_radio(data: ClickerData, radio_id: str, name: str) -> Radio:
    """Rename a radio."""
    radio = get_radio(data, radio_id)
    radio.name = _name(name, "radio")
    return radio


def delete_radio(data: ClickerData, radio_id: str) -> Radio:
    """Remove a radio no device uses (re-discovery adds it back if it's still there)."""
    radio = get_radio(data, radio_id)
    if users := [d.name for d in data.devices if d.radio_id == radio.id]:
        raise ModelError(f"radio {radio.name!r} is used by {', '.join(users)}")
    data.radios.remove(radio)
    return radio


def check_binding(device: Device, platform: str, roles: dict[str, str]) -> None:
    """Raise ``ModelError`` unless these roles make a working entity of ``platform``."""
    if platform not in PLATFORMS:
        raise ModelError(f"unknown entity type {platform!r}; use one of {', '.join(PLATFORMS)}")
    if not roles:
        raise ModelError("pick at least one command")
    for role, command_id in roles.items():
        if not role.strip():
            raise ModelError("a role can't be empty")
        if device.command(command_id) is None:
            raise ModelError(f"{device.name} has no command {command_id!r} (for {role})")
    if platform == "fan":
        FanRemote(roles)
    elif platform in ("light", "switch"):
        OnOffRemote(roles)


def _check_binding_name(device: Device, platform: str, name: str, binding: Binding | None) -> str:
    name = _name(name, "entity")
    for other in device.bindings:
        if other is not binding and other.platform == platform:
            if other.name.casefold() == name.casefold():
                raise ModelError(f"{device.name} already has a {platform} named {name!r}")
    return name


def get_binding(device: Device, binding_id: str) -> Binding:
    """Return a device's binding, or raise ``NotFoundError``."""
    if (binding := next((b for b in device.bindings if b.id == binding_id), None)) is None:
        raise NotFoundError(f"{device.name} has no entity {binding_id!r}")
    return binding


def add_binding(
    data: ClickerData, device_id: str, platform: str, name: str, roles: dict[str, str]
) -> Binding:
    """Add an entity to a device, built from some of its commands."""
    device = get_device(data, device_id)
    check_binding(device, platform, roles)
    binding = Binding(
        platform=platform,
        name=_check_binding_name(device, platform, name, None),
        roles=dict(roles),
    )
    device.bindings.append(binding)
    return binding


def update_binding(
    data: ClickerData,
    device_id: str,
    binding_id: str,
    *,
    name: str | None = None,
    roles: dict[str, str] | None = None,
) -> Binding:
    """Rename an entity or change its commands (its type is fixed)."""
    device = get_device(data, device_id)
    binding = get_binding(device, binding_id)
    new_name = (
        _check_binding_name(device, binding.platform, name, binding)
        if name is not None
        else binding.name
    )
    if roles is not None:
        check_binding(device, binding.platform, roles)
        binding.roles = dict(roles)
    binding.name = new_name
    return binding


def delete_binding(data: ClickerData, device_id: str, binding_id: str) -> Binding:
    """Remove an entity; the commands it used stay on the device."""
    device = get_device(data, device_id)
    binding = get_binding(device, binding_id)
    device.bindings.remove(binding)
    return binding
