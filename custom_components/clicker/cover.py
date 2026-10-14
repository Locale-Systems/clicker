"""Covers, built from bindings with platform ``cover`` (rules in :mod:`core.cover`)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverDeviceClass, CoverEntity, CoverEntityFeature
from homeassistant.const import STATE_CLOSED, STATE_OPEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .core.cover import CoverRemote
from .core.fan import Step
from .core.models import Binding
from .entity import ClickerEntity, async_track_bindings, unsupported
from .runtime import ClickerConfigEntry

PARALLEL_UPDATES = 0  # sends are queued per radio by Clicker itself


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClickerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one cover entity per cover binding, following data changes."""
    async_track_bindings(hass, entry, "cover", ClickerCover, async_add_entities)


class ClickerCover(ClickerEntity[CoverRemote], CoverEntity):
    """An RF-controlled awning, shade or door: open or closed, never a position.

    State is assumed: Open and Close set it as they are sent, Stop leaves it.
    """

    _closed: bool | None = None

    @staticmethod
    def remote_for(binding: Binding) -> CoverRemote:
        return CoverRemote(binding.roles)

    @property
    def device_class(self) -> CoverDeviceClass | None:
        device_class = self.binding.options.get("device_class")
        return CoverDeviceClass(device_class) if device_class else None

    @property
    def supported_features(self) -> CoverEntityFeature:
        features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        if self.remote.can_stop:
            features |= CoverEntityFeature.STOP
        return features

    @property
    def is_closed(self) -> bool | None:
        return self._closed

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._closed = {STATE_CLOSED: True, STATE_OPEN: False}.get(last.state)

    def pressed(self, role: str) -> bool:
        old, self._closed = self._closed, self.remote.pressed(self._closed, role)
        return self._closed != old

    async def _run(self, steps: list[Step], closed: bool | None) -> None:
        """Show the new state, send; undo the state if sending fails."""
        old, self._closed = self._closed, closed
        self.async_write_ha_state()
        try:
            await self.async_send_steps(steps)
        except Exception:
            self._closed = old
            self.async_write_ha_state()
            raise

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._run(self.remote.open(), False)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._run(self.remote.close(), True)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._run(self.remote.stop(), self._closed)

    async def async_set_assumed_state(self, is_closed: bool | None = None, **other: Any) -> None:
        """Correct the assumed state without sending anything (after a missed press)."""
        unsupported(self, other)
        if is_closed is not None:
            self._closed = is_closed
        self.async_write_ha_state()
