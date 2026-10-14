"""Buttons: one per role of a ``button`` binding, each sending its command."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .core.fan import Step
from .core.models import Binding, ModelError
from .entity import ClickerEntity, async_track_bindings, unsupported
from .runtime import ClickerConfigEntry

PARALLEL_UPDATES = 0  # sends are queued per radio by Clicker itself


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClickerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one button entity per role of every button binding."""
    async_track_bindings(hass, entry, "button", ClickerButton, async_add_entities)


class ClickerButton(ClickerEntity[str], ButtonEntity):
    """Sends one command; a button has no state to follow."""

    @staticmethod
    def remote_for(binding: Binding) -> str:
        raise NotImplementedError  # buttons split by role

    @classmethod
    def split(cls, binding: Binding) -> dict[str | None, str]:
        if not binding.roles:
            raise ModelError("a button binding needs at least one command")
        return {role: role for role in binding.roles}

    def _set_name(self) -> None:
        # Named after its command, which is unique within the device.
        command = self.device.command(self.binding.roles.get(self.remote, ""))
        name = command.name if command is not None else self.remote
        self._attr_name = None if name.casefold() == self.device.name.casefold() else name

    def pressed(self, role: str) -> bool:
        return False

    async def async_press(self) -> None:
        await self.async_send_steps([Step(self.remote)])

    async def async_set_assumed_state(self, **fields: Any) -> None:
        unsupported(self, fields)
