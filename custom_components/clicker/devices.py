"""Keep one Home Assistant device per Clicker device.

Devices exist even without entities, so remote presses (logbook entries,
device triggers later) always have a device to belong to. Entities attach to
the same device through its ``(clicker, <device id>)`` identifier.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_DATA_UPDATED

if TYPE_CHECKING:
    from .runtime import ClickerConfigEntry

MODEL = "RF remote"


@callback
def async_track_devices(hass: HomeAssistant, entry: ClickerConfigEntry) -> None:
    """Create, rename and remove devices as Clicker's devices change."""
    runtime = entry.runtime_data
    dev_reg = dr.async_get(hass)

    @callback
    def _sync() -> None:
        wanted = {device.id: device for device in runtime.data.devices}
        for device in wanted.values():
            dev_reg.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, device.id)},
                name=device.name,
                model=MODEL,
            )
        for registered in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
            if not any(i[0] == DOMAIN and i[1] in wanted for i in registered.identifiers):
                dev_reg.async_remove_device(registered.id)

    _sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_DATA_UPDATED, _sync))


def ha_device_id(hass: HomeAssistant, entry_id: str, device_id: str) -> str | None:
    """Return the Home Assistant device id of a Clicker device, if registered."""
    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, device_id), entry_id)
    return device.id if device is not None else None
