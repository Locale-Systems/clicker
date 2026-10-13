"""Diagnostics for Clicker: the radios it found and how they map to stored ones."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from . import ClickerConfigEntry
from .discovery import async_find_radios


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ClickerConfigEntry
) -> dict[str, Any]:
    """Return what Clicker sees: hardware found, stored radios and their links."""
    runtime = entry.runtime_data
    return {
        "found_radios": [asdict(found) for found in await async_find_radios(hass)],
        "stored_radios": [radio.to_dict() for radio in runtime.data.radios],
        "links": {radio_id: found.node for radio_id, found in runtime.links.items()},
    }
