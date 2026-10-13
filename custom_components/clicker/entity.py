"""What every Clicker entity shares: its device, binding, radio and commands."""

from __future__ import annotations

from homeassistant.core import Context
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .core.models import Binding, Device
from .runtime import ClickerRuntime


class ClickerEntity(RestoreEntity):
    """An entity driven by one binding of a Clicker device.

    State is assumed (RF remotes don't report back) and restored across
    restarts; the device and binding objects are swapped in place when the
    data changes, so edits apply without reloading.
    """

    _attr_assumed_state = True
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, runtime: ClickerRuntime, device: Device, binding: Binding) -> None:
        self._runtime = runtime
        self.device = device
        self.binding = binding
        self._attr_unique_id = binding.id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)}, name=device.name, model="RF remote"
        )
        self._set_name()

    def _set_name(self) -> None:
        # The device's main entity takes the device name, as HA recommends.
        same = self.binding.name.casefold() == self.device.name.casefold()
        self._attr_name = None if same else self.binding.name

    def update_binding(self, device: Device, binding: Binding) -> None:
        """Take the latest stored device and binding."""
        self.device, self.binding = device, binding
        self._set_name()

    @property
    def available(self) -> bool:
        radio = self._runtime.data.radio(self.device.radio_id)
        return (
            radio is not None and radio.transmitter is not None and radio.id in self._runtime.links
        )

    async def async_send_role(
        self, role: str, *, context: Context | None, pause_after_s: float = 0.0
    ) -> None:
        """Send the command bound to a role, through the device's radio."""
        sender = self._runtime.sender
        assert sender is not None
        command = self.device.command(self.binding.roles[role])
        if command is None:
            raise KeyError(role)
        await sender.async_send(
            sender.radio_of(self.device), command, context=context, pause_after_s=pause_after_s
        )

    def roles_of(self, command_id: str) -> list[str]:
        """Return the roles a command has in this binding."""
        return [role for role, cid in self.binding.roles.items() if cid == command_id]
