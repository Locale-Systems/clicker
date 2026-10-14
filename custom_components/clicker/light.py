"""Lights, built from bindings with platform ``light`` (rules in :mod:`core.onoff`)."""

from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import OnOffEntity, async_track_bindings
from .runtime import ClickerConfigEntry

PARALLEL_UPDATES = 0  # sends are queued per radio by Clicker itself


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClickerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one light entity per light binding, following data changes."""
    async_track_bindings(hass, entry, "light", ClickerLight, async_add_entities)


class ClickerLight(OnOffEntity, LightEntity):
    """An on/off light; it follows remote presses."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
