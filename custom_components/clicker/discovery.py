"""Find the radios ESPHome nodes offer, as :class:`core.radios.FoundRadio` objects.

Every loaded ESPHome node reports its RF endpoints as ``RadioFrequencyInfo``
(transmitters and receivers, each with a frequency range). Home Assistant's
ESPHome integration only keeps the transmitters (the ones it makes entities
for), so the node is asked directly over its existing API connection.

Endpoints on the same sub-device and frequency range are paired into one
radio. A transmitter's entity is found through ESPHome's own unique id
scheme; receivers are referenced by object id, which unlike the entity key
survives firmware updates.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.radio_frequency import DOMAIN as RF_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import ESPHOME_DOMAIN
from .core.radios import FoundRadio

_LOGGER = logging.getLogger(__name__)

try:  # ESPHome is an after-dependency: without it there are simply no radios.
    from aioesphomeapi import RadioFrequencyCapability, RadioFrequencyInfo, build_device_unique_id
except ImportError:  # pragma: no cover - only without the ESPHome integration
    HAS_ESPHOME = False
else:
    HAS_ESPHOME = True


def receiver_reference(mac: str, info: RadioFrequencyInfo) -> str:
    """Return the stable reference stored for a receiver."""
    return f"{mac}:{info.device_id}:{info.object_id}"


async def _async_rf_infos(entry_data: Any) -> list[RadioFrequencyInfo]:
    """Ask the node for all its RF endpoints, receivers included.

    Home Assistant's ESPHome integration only keeps the RF infos its platform
    turns into entities (transmitters), so receivers must be listed live.
    Falls back to the kept infos when the node is offline.
    """
    kept = list(entry_data.info.get(RadioFrequencyInfo, {}).values())
    if not entry_data.available:
        return kept
    try:
        infos, _services = await entry_data.client.list_entities_services()
    except Exception as err:  # noqa: BLE001 - any API failure: use what we know
        _LOGGER.debug("Could not list entities of %s: %s", entry_data.title, err)
        return kept
    return [info for info in infos if isinstance(info, RadioFrequencyInfo)]


async def async_find_radios(hass: HomeAssistant) -> list[FoundRadio]:
    """Return every radio the loaded ESPHome nodes offer right now."""
    if not HAS_ESPHOME:
        return []
    entries = [
        entry
        for entry in hass.config_entries.async_entries(ESPHOME_DOMAIN)
        if entry.state is ConfigEntryState.LOADED and entry.runtime_data.device_info is not None
    ]
    infos_per_entry = await asyncio.gather(*(_async_rf_infos(e.runtime_data) for e in entries))
    ent_reg = er.async_get(hass)
    found: list[FoundRadio] = []
    for entry, infos in zip(entries, infos_per_entry, strict=True):
        entry_data: Any = entry.runtime_data
        device_info = entry_data.device_info
        groups: dict[tuple[int, int, int], dict[str, RadioFrequencyInfo]] = {}
        for info in infos:
            group = groups.setdefault((info.device_id, info.frequency_min, info.frequency_max), {})
            if info.capabilities & RadioFrequencyCapability.TRANSMITTER:
                group.setdefault("tx", info)
            if info.capabilities & RadioFrequencyCapability.RECEIVER:
                group.setdefault("rx", info)
        for (_device_id, low, high), group in groups.items():
            entity_id = registry_id = None
            if (tx := group.get("tx")) is not None:
                unique_id = build_device_unique_id(device_info.mac_address, tx)
                entity_id = ent_reg.async_get_entity_id(RF_DOMAIN, ESPHOME_DOMAIN, unique_id)
                if entity_id is not None and (reg := ent_reg.async_get(entity_id)) is not None:
                    registry_id = reg.id
            rx = group.get("rx")
            found.append(
                FoundRadio(
                    node=device_info.name,
                    title=entry.title or device_info.friendly_name or device_info.name,
                    frequency_hz=low if low == high else 0,
                    frequency_range=(low, high),
                    transmitter_entity_id=entity_id,
                    transmitter_registry_id=registry_id,
                    receiver=receiver_reference(device_info.mac_address, rx) if rx else None,
                    available=bool(entry_data.available),
                )
            )
    return found
