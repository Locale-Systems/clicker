"""Diagnostics for Clicker: radios, how they map to hardware, and a device summary."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .discovery import async_find_radios
from .runtime import ClickerConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ClickerConfigEntry
) -> dict[str, Any]:
    """Return what Clicker sees and stores (codes summarized, not dumped)."""
    runtime = entry.runtime_data
    data = runtime.data
    return {
        "found_radios": [asdict(found) for found in await async_find_radios(hass)],
        "stored_radios": [radio.to_dict() for radio in data.radios],
        "links": {radio_id: found.node for radio_id, found in runtime.links.items()},
        "devices": [
            {
                "name": device.name,
                "radio_id": device.radio_id,
                "frequency_hz": device.frequency_hz,
                "commands": {
                    command.name: f"{command.kind.value}, {type(command.frame).__name__}"
                    for command in device.commands
                },
                "bindings": {b.name: sorted(b.roles) for b in device.bindings},
            }
            for device in data.devices
        ],
        "problems": data.problems(),
        "listening": runtime.hub.listening if runtime.hub else {},
        "recent_receptions": [asdict(heard) for heard in runtime.hub.recent] if runtime.hub else [],
    }
