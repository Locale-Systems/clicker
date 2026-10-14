"""Clicker: learn, send and track sub-GHz RF remotes through ESPHome radios."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .core.models import ModelError
from .hub import ReceiveHub
from .runtime import ClickerConfigEntry, ClickerRuntime
from .sender import SendQueue
from .services import async_setup_services
from .storage import ClickerStore
from .websocket import async_setup_websocket

__all__ = ["ClickerConfigEntry", "ClickerRuntime"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.BUTTON, Platform.FAN, Platform.LIGHT, Platform.SWITCH]

# ESPHome nodes connect and reconnect on their own schedule; look again regularly.
RADIO_REFRESH_INTERVAL = timedelta(seconds=60)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register Clicker's actions."""
    async_setup_services(hass)
    async_setup_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ClickerConfigEntry) -> bool:
    """Set up Clicker from its config entry."""
    store = ClickerStore(hass)
    try:
        data = await store.async_load()
    except ModelError as err:
        # Leave the file alone: a newer Clicker wrote it.
        raise ConfigEntryError(f"Can't read Clicker's stored data: {err}") from err
    runtime = ClickerRuntime(hass=hass, store=store, data=data)
    entry.runtime_data = runtime

    @callback
    def _refresh(*_: object) -> None:
        entry.async_create_background_task(
            hass, runtime.async_refresh_radios(hass), "clicker radio refresh"
        )

    runtime.hub = ReceiveHub(hass, runtime, _refresh)
    runtime.sender = SendQueue(hass, runtime)
    entry.async_on_unload(runtime.hub.async_stop)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _refresh()
    entry.async_on_unload(async_track_time_interval(hass, _refresh, RADIO_REFRESH_INTERVAL))
    if not hass.is_running:

        @callback
        def _started(_event: Event) -> None:
            _refresh()

        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _started))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ClickerConfigEntry) -> bool:
    """Unload Clicker's entities; listeners registered with async_on_unload go too."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ClickerConfigEntry) -> None:
    """Delete Clicker's stored data when the integration is removed."""
    await ClickerStore(hass).async_remove()
