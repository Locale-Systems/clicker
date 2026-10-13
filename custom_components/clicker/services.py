"""Clicker's actions (services)."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util.json import load_json

from .const import DOMAIN
from .core.importer import import_rf_device_manager, merge_import
from .core.models import ModelError
from .runtime import ClickerConfigEntry

_LOGGER = logging.getLogger(__name__)

SERVICE_IMPORT_RF_DEVICE_MANAGER = "import_rf_device_manager"
RF_DEVICE_MANAGER_STORAGE = ("rf_device_manager",)  # under .storage


def _loaded_entry(hass: HomeAssistant) -> ClickerConfigEntry:
    entries: list[ClickerConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise ServiceValidationError("Clicker is not loaded")
    return entries[0]


async def async_import_rf_device_manager(
    hass: HomeAssistant, entry: ClickerConfigEntry
) -> dict[str, Any]:
    """Import rf_device_manager's devices into Clicker and save them.

    Devices whose names Clicker already has are skipped, so this can be run
    again safely. Returns the notes and any problems left in the data.
    """
    path = Path(hass.config.path(".storage", *RF_DEVICE_MANAGER_STORAGE))
    raw: Any = await hass.async_add_executor_job(load_json, path, None)
    if raw is None:
        raise ServiceValidationError(f"No rf_device_manager data found at {path}")
    try:
        result = import_rf_device_manager(raw, now=time.time())
    except (ModelError, AttributeError, TypeError, KeyError, ValueError) as err:
        raise HomeAssistantError(f"Could not read {path}: {err}") from err

    # Stored references are registry ids where the entity exists here.
    ent_reg = er.async_get(hass)
    for radio in result.data.radios:
        if radio.transmitter and (reg := ent_reg.async_get(radio.transmitter)) is not None:
            radio.transmitter = reg.id

    runtime = entry.runtime_data
    async with runtime.lock:
        notes = result.notes + merge_import(runtime.data, result.data)
        await runtime.async_save()
    await runtime.async_refresh_radios(hass)
    for note in notes:
        _LOGGER.info("Import: %s", note)
    return {"notes": notes, "problems": runtime.data.problems()}


def async_setup_services(hass: HomeAssistant) -> None:
    """Register Clicker's actions."""

    async def _import(call: ServiceCall) -> ServiceResponse:
        response = await async_import_rf_device_manager(hass, _loaded_entry(hass))
        return response if call.return_response else None

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_RF_DEVICE_MANAGER,
        _import,
        supports_response=SupportsResponse.OPTIONAL,
    )
