"""Button and switch entities."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core import edit
from custom_components.clicker.core.models import (
    Binding,
    ClickerData,
    Command,
    CommandKind,
    Device,
    Radio,
)
from custom_components.clicker.core.radios import FoundRadio

from .conftest import F433, FakeNode
from .test_fan import frame, press, sent, setup

OUTLET = {"toggle": ("Outlet", CommandKind.TOGGLE, "0110")}
SCENES = {
    "nature": ("Nature", CommandKind.BUTTON, "0000"),
    "sleep": ("Sleep", CommandKind.BUTTON, "0010"),
}


def store(hass_storage: dict[str, Any], transmitter: str | None) -> None:
    """A remote with an outlet toggle and two scene buttons."""
    radio = Radio(name="Gateway", frequency_hz=F433, transmitter=transmitter)
    device = Device(name="Porch", radio_id=radio.id, frequency_hz=F433)
    for platform, name, buttons in (("switch", "Outlet", OUTLET), ("button", "Scenes", SCENES)):
        binding = Binding(platform=platform, name=name)
        for role, (command_name, kind, tail) in buttons.items():
            command = Command(name=command_name, kind=kind, frame=frame(tail))
            device.commands.append(command)
            binding.roles[role] = command.id
        device.bindings.append(binding)
    data = ClickerData(radios=[radio], devices=[device])
    hass_storage[DOMAIN] = {"version": 1, "key": DOMAIN, "data": data.to_dict()}


@pytest.fixture(autouse=True)
def porch(hass_storage: dict[str, Any], found_radios: list[FoundRadio]) -> None:
    store(hass_storage, found_radios[0].transmitter)


def state_of(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


async def test_switch(hass: HomeAssistant, node: FakeNode, transmit: AsyncMock) -> None:
    """A toggled outlet: it follows the remote, and toggles only to change state."""
    await setup(hass)
    # The remote first: right after Clicker sends, its frequency is muted as an echo.
    node.client.send(press(OUTLET["toggle"][2]))
    await hass.async_block_till_done()
    assert state_of(hass, "switch.porch_outlet") == STATE_ON
    for service in (SERVICE_TURN_ON, SERVICE_TURN_OFF, SERVICE_TURN_OFF, SERVICE_TURN_ON):
        await hass.services.async_call(
            SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: "switch.porch_outlet"}, blocking=True
        )
    assert sent(transmit, OUTLET) == ["Outlet", "Outlet"]


async def test_buttons(hass: HomeAssistant, node: FakeNode, transmit: AsyncMock) -> None:
    """One button per command of a button binding, each sending its own."""
    await setup(hass)
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: "button.porch_sleep"}, blocking=True
    )
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: "button.porch_nature"}, blocking=True
    )
    assert sent(transmit, SCENES) == ["Sleep", "Nature"]

    # A remote press of a button changes no state.
    before = state_of(hass, "button.porch_nature")
    node.client.send(press(SCENES["nature"][2]))
    await hass.async_block_till_done()
    assert state_of(hass, "button.porch_nature") == before

    with pytest.raises(ServiceValidationError, match="has no is_on"):
        await hass.services.async_call(
            DOMAIN,
            "set_assumed_state",
            {ATTR_ENTITY_ID: "button.porch_nature", "is_on": True},
            blocking=True,
        )


async def test_buttons_follow_commands(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, transmit: AsyncMock
) -> None:
    """Deleting a command removes just its button; renaming renames it."""
    entry = await setup(hass)
    runtime = entry.runtime_data
    device = runtime.data.devices[0]
    nature, sleep = (device.command(device.bindings[1].roles[r]) for r in ("nature", "sleep"))
    assert nature is not None and sleep is not None
    async with runtime.lock:
        edit.delete_command(runtime.data, device.id, sleep.id)
        edit.update_command(runtime.data, device.id, nature.id, name="Breeze")
        await runtime.async_save()
    await hass.async_block_till_done()
    assert entity_registry.async_get("button.porch_sleep") is None
    state = hass.states.get("button.porch_nature")  # the entity id stays; the name follows
    assert state is not None and state.attributes["friendly_name"] == "Porch Breeze"
    assert state_of(hass, "switch.porch_outlet") == STATE_OFF
