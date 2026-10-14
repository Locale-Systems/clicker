"""Switches, built from bindings with platform ``switch`` (rules in :mod:`core.onoff`)."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Keep one switch entity per switch binding, following data changes."""
    async_track_bindings(hass, entry, "switch", ClickerSwitch, async_add_entities)


class ClickerSwitch(OnOffEntity, SwitchEntity):
    """An RF-switched outlet or relay; it follows remote presses."""
