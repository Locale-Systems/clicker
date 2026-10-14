"""Home Assistant devices for Clicker devices, and logbook entries for presses."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.clicker import async_remove_config_entry_device
from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core import edit
from custom_components.clicker.hub import EVENT_REMOTE_PRESSED
from custom_components.clicker.logbook import async_describe_events

from .conftest import FakeNode, corpus
from .test_init import setup_clicker

pytestmark = pytest.mark.usefixtures("patio_fan", "found_radios")


async def test_devices_follow_data(hass: HomeAssistant, device_registry: dr.DeviceRegistry) -> None:
    """Every Clicker device has a Home Assistant device, entities or not."""
    entry = await setup_clicker(hass)
    runtime = entry.runtime_data
    fan = runtime.data.devices[0]
    registered = device_registry.async_get_device_by_identifier((DOMAIN, fan.id), entry.entry_id)
    assert registered is not None and registered.name == "Patio fan"
    assert registered.model == "RF remote"

    async with runtime.lock:
        lamp = edit.add_device(runtime.data, "Lamp", fan.radio_id)
        edit.update_device(runtime.data, fan.id, name="Porch fan")
        await runtime.async_save()
    await hass.async_block_till_done()
    assert (
        device_registry.async_get_device_by_identifier((DOMAIN, lamp.id), entry.entry_id)
        is not None
    )
    renamed = device_registry.async_get_device_by_identifier((DOMAIN, fan.id), entry.entry_id)
    assert renamed is not None and renamed.name == "Porch fan"

    # Only a device Clicker no longer has can be deleted in the UI.
    assert not await async_remove_config_entry_device(hass, entry, renamed)
    async with runtime.lock:
        edit.delete_device(runtime.data, lamp.id)
        await runtime.async_save()
    await hass.async_block_till_done()
    assert device_registry.async_get_device_by_identifier((DOMAIN, lamp.id), entry.entry_id) is None


async def test_press_event_and_logbook(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry, node: FakeNode
) -> None:
    """The press event names Home Assistant's device; the logbook reads naturally."""
    events = async_capture_events(hass, EVENT_REMOTE_PRESSED)
    entry = await setup_clicker(hass)
    fan = entry.runtime_data.data.devices[0]
    node.client.send(corpus.HELD_CAPTURE)
    await hass.async_block_till_done()
    (event,) = events
    registered = device_registry.async_get_device_by_identifier((DOMAIN, fan.id), entry.entry_id)
    assert registered is not None
    assert event.data["device_id"] == registered.id and event.data["clicker_device_id"] == fan.id

    describers: dict[tuple[str, str], Callable[[Event], dict[str, str]]] = {}

    def describe_event(domain: str, event_type: str, func: Any) -> None:
        describers[domain, event_type] = func

    async_describe_events(hass, describe_event)
    entry_text = describers[DOMAIN, EVENT_REMOTE_PRESSED](event)
    assert entry_text == {
        LOGBOOK_ENTRY_NAME: "Patio fan",
        LOGBOOK_ENTRY_MESSAGE: "Power pressed on the remote",
    }
