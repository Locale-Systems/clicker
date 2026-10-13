"""Clicker: learn, send and track sub-GHz RF remotes through ESPHome radios."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .core.models import ClickerData
from .core.radios import FoundRadio, reconcile
from .discovery import async_find_radios

_LOGGER = logging.getLogger(__name__)

# ESPHome nodes connect and reconnect on their own schedule; look again regularly.
RADIO_REFRESH_INTERVAL = timedelta(seconds=60)


@dataclass
class ClickerRuntime:
    """What a loaded Clicker entry holds while Home Assistant runs."""

    data: ClickerData = field(default_factory=ClickerData)
    links: dict[str, FoundRadio] = field(default_factory=dict)  # radio id -> hardware
    reported: set[str] = field(default_factory=set)  # notes already logged

    async def async_refresh_radios(self, hass: HomeAssistant) -> None:
        """Re-discover radios and reconcile them with the stored ones."""
        result = reconcile(self.data.radios, await async_find_radios(hass))
        self.data.radios = result.radios
        self.links = result.links
        for note in result.notes:
            if note not in self.reported:
                self.reported.add(note)
                _LOGGER.info("Radio %s", note)


type ClickerConfigEntry = ConfigEntry[ClickerRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: ClickerConfigEntry) -> bool:
    """Set up Clicker from its config entry."""
    runtime = ClickerRuntime()
    entry.runtime_data = runtime

    @callback
    def _refresh(*_: object) -> None:
        entry.async_create_background_task(
            hass, runtime.async_refresh_radios(hass), "clicker radio refresh"
        )

    _refresh()
    entry.async_on_unload(async_track_time_interval(hass, _refresh, RADIO_REFRESH_INTERVAL))
    if not hass.is_running:

        @callback
        def _started(_event: Event) -> None:
            _refresh()

        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _started))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ClickerConfigEntry) -> bool:
    """Unload Clicker; listeners registered with async_on_unload are removed."""
    return True
