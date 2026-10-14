"""Clicker's actions (services)."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import probatio as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_extract_entity_ids, async_register_admin_service
from homeassistant.util.json import load_json

from .const import DOMAIN
from .core.importer import import_rf_device_manager, merge_import
from .core.models import Command, Device, ModelError, SendPolicy
from .runtime import ClickerConfigEntry
from .sender import describe

_LOGGER = logging.getLogger(__name__)

SERVICE_IMPORT_RF_DEVICE_MANAGER = "import_rf_device_manager"
SERVICE_SEND_COMMAND = "send_command"
SERVICE_SET_ASSUMED_STATE = "set_assumed_state"
ATTR_DEVICE = "device"
ATTR_COMMAND = "command"
ATTR_FRAMES_ON_AIR = "frames_on_air"

SET_ASSUMED_STATE_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Optional("is_on"): cv.boolean,
        vol.Optional("is_closed"): cv.boolean,
        vol.Optional("percentage"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("oscillating"): cv.boolean,
        vol.Optional("direction"): vol.In(["forward", "reverse"]),
    }
)

SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE): cv.string,
        vol.Required(ATTR_COMMAND): cv.string,
        vol.Optional(ATTR_FRAMES_ON_AIR): vol.All(vol.Coerce(int), vol.Range(min=1, max=64)),
    }
)
RF_DEVICE_MANAGER_STORAGE = ("rf_device_manager",)  # under .storage


def _loaded_entry(hass: HomeAssistant) -> ClickerConfigEntry:
    entries: list[ClickerConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise ServiceValidationError("Clicker is not loaded")
    return entries[0]


def _by_name_or_id[T: (Device, Command)](items: list[T], wanted: str, what: str) -> T:
    """Find an item by id, or else by its name ignoring case."""
    for item in items:
        if item.id == wanted:
            return item
    named = [item for item in items if item.name.casefold() == wanted.casefold()]
    if len(named) != 1:
        problem = "No" if not named else "More than one"
        raise ServiceValidationError(f"{problem} {what} named {wanted!r}")
    return named[0]


def rf_device_manager_path(hass: HomeAssistant) -> Path:
    """Where rf_device_manager keeps its data."""
    return Path(hass.config.path(".storage", *RF_DEVICE_MANAGER_STORAGE))


async def async_import_rf_device_manager(
    hass: HomeAssistant, entry: ClickerConfigEntry
) -> dict[str, Any]:
    """Import rf_device_manager's devices into Clicker and save them.

    Devices whose names Clicker already has are skipped, so this can be run
    again safely. Returns the notes and any problems left in the data.
    """
    path = rf_device_manager_path(hass)
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

    async def _send(call: ServiceCall) -> ServiceResponse:
        runtime = _loaded_entry(hass).runtime_data
        device = _by_name_or_id(runtime.data.devices, call.data[ATTR_DEVICE], "device")
        command = _by_name_or_id(device.commands, call.data[ATTR_COMMAND], "command")
        policy = None
        if (frames := call.data.get(ATTR_FRAMES_ON_AIR)) is not None:
            policy = SendPolicy(frames_on_air=frames)
        assert runtime.sender is not None
        sent = await runtime.sender.async_send(
            runtime.sender.radio_of(device), command, policy=policy, context=call.context
        )
        return {"device": device.name, **describe(sent)} if call.return_response else None

    async def _set_assumed_state(call: ServiceCall) -> None:
        # One action for every Clicker entity: each takes the fields it has.
        runtime = _loaded_entry(hass).runtime_data
        targets = [
            runtime.entities[entity_id]
            for entity_id in sorted(await async_extract_entity_ids(call))
            if entity_id in runtime.entities
        ]
        if not targets:
            raise ServiceValidationError("No Clicker entities were targeted")
        fields = {k: v for k, v in call.data.items() if k not in cv.ENTITY_SERVICE_FIELDS}
        for entity in targets:
            await entity.async_set_assumed_state(**fields)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_ASSUMED_STATE, _set_assumed_state, schema=SET_ASSUMED_STATE_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        _send,
        schema=SEND_COMMAND_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def _import(call: ServiceCall) -> ServiceResponse:
        response = await async_import_rf_device_manager(hass, _loaded_entry(hass))
        return response if call.return_response else None

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_IMPORT_RF_DEVICE_MANAGER,
        _import,
        supports_response=SupportsResponse.OPTIONAL,
    )
