"""Lights, built from bindings with platform ``light`` (rules in :mod:`core.onoff`)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .core.models import Binding
from .core.onoff import OnOffPlan, OnOffRemote
from .entity import ClickerEntity, async_track_bindings, unsupported
from .runtime import ClickerConfigEntry

PARALLEL_UPDATES = 0  # sends are queued per radio by Clicker itself


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClickerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one light entity per light binding, following data changes."""
    async_track_bindings(hass, entry, "light", ClickerLight, async_add_entities)


class ClickerLight(ClickerEntity[OnOffRemote], LightEntity):
    """An on/off light driven by its remote's buttons; it follows remote presses."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _on = False

    @staticmethod
    def remote_for(binding: Binding) -> OnOffRemote:
        return OnOffRemote(binding.roles)

    @property
    def is_on(self) -> bool:
        return self._on

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._on = last.state == STATE_ON

    def pressed(self, role: str) -> bool:
        old, self._on = self._on, self.remote.pressed(self._on, role)
        return self._on != old

    async def _run(self, plan: OnOffPlan) -> None:
        """Show the new state, send; undo the state if sending fails."""
        steps, new = plan
        old, self._on = self._on, new
        self.async_write_ha_state()
        try:
            await self.async_send_steps(steps)
        except Exception:
            self._on = old
            self.async_write_ha_state()
            raise

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._run(self.remote.set(self._on, True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._run(self.remote.set(self._on, False))

    async def async_set_assumed_state(self, is_on: bool | None = None, **other: Any) -> None:
        """Correct the assumed state without sending anything (after a missed press)."""
        unsupported(self, other)
        if is_on is not None:
            self._on = is_on
        self.async_write_ha_state()
