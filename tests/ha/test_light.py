"""Light entities: toggles sent only to change state, presses followed."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.clicker.const import DOMAIN
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
from .test_fan import MINKA, frame, press, sent, setup

LIGHT = "light.ceiling_fan_light"
FAN = "fan.ceiling_fan"
TOGGLE_LIGHT = {"toggle": ("Light", CommandKind.TOGGLE, "1100")}
EXPLICIT_LIGHT = {
    "on": ("Light on", CommandKind.STATE, "1101"),
    "off": ("Light off", CommandKind.STATE, "1110"),
}


def store(hass_storage: dict[str, Any], transmitter: str | None, light: dict[str, Any]) -> None:
    """A Minka-style fan with a light on the same remote."""
    radio = Radio(name="Gateway", frequency_hz=F433, transmitter=transmitter)
    device = Device(name="Ceiling fan", radio_id=radio.id, frequency_hz=F433)
    for platform, name, buttons in (("fan", "Ceiling fan", MINKA), ("light", "Light", light)):
        binding = Binding(platform=platform, name=name)
        for role, (command_name, kind, tail) in buttons.items():
            command = Command(name=command_name, kind=kind, frame=frame(tail))
            device.commands.append(command)
            binding.roles[role] = command.id
        device.bindings.append(binding)
    data = ClickerData(radios=[radio], devices=[device])
    hass_storage[DOMAIN] = {"version": 1, "key": DOMAIN, "data": data.to_dict()}


async def call(hass: HomeAssistant, service: str) -> None:
    await hass.services.async_call(LIGHT_DOMAIN, service, {ATTR_ENTITY_ID: LIGHT}, blocking=True)


def state_of(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


async def test_toggle_light(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    found_radios: list[FoundRadio],
    transmit: AsyncMock,
) -> None:
    """The Minka's light toggle: sent only when the light must change."""
    store(hass_storage, found_radios[0].transmitter, TOGGLE_LIGHT)
    await setup(hass)
    assert state_of(hass, LIGHT) == STATE_OFF
    await call(hass, SERVICE_TURN_ON)
    await call(hass, SERVICE_TURN_ON)
    await call(hass, SERVICE_TURN_OFF)
    await call(hass, SERVICE_TURN_OFF)
    assert sent(transmit, TOGGLE_LIGHT) == ["Light", "Light"]


async def test_explicit_light(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    found_radios: list[FoundRadio],
    transmit: AsyncMock,
) -> None:
    """On and off buttons are always sent."""
    store(hass_storage, found_radios[0].transmitter, EXPLICIT_LIGHT)
    await setup(hass)
    await call(hass, SERVICE_TURN_ON)
    await call(hass, SERVICE_TURN_ON)
    await call(hass, SERVICE_TURN_OFF)
    assert sent(transmit, EXPLICIT_LIGHT) == ["Light on", "Light on", "Light off"]


async def test_presses_reach_the_right_entity(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    found_radios: list[FoundRadio],
    node: FakeNode,
    transmit: AsyncMock,
) -> None:
    """The light button moves the light; a fan button moves only the fan."""
    store(hass_storage, found_radios[0].transmitter, TOGGLE_LIGHT)
    await setup(hass)
    node.client.send(press(TOGGLE_LIGHT["toggle"][2]))
    await hass.async_block_till_done()
    assert (state_of(hass, LIGHT), state_of(hass, FAN)) == (STATE_ON, STATE_OFF)

    node.client.send(press(MINKA["speed_2"][2]))
    await hass.async_block_till_done()
    assert (state_of(hass, LIGHT), state_of(hass, FAN)) == (STATE_ON, STATE_ON)
    transmit.assert_not_called()


async def test_set_assumed_state(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    found_radios: list[FoundRadio],
    transmit: AsyncMock,
) -> None:
    """One resync action for fans and lights; fields a light lacks are refused."""
    store(hass_storage, found_radios[0].transmitter, TOGGLE_LIGHT)
    await setup(hass)
    await hass.services.async_call(
        DOMAIN, "set_assumed_state", {ATTR_ENTITY_ID: [LIGHT, FAN], "is_on": True}, blocking=True
    )
    assert (state_of(hass, LIGHT), state_of(hass, FAN)) == (STATE_ON, STATE_ON)
    with pytest.raises(ServiceValidationError, match="has no percentage"):
        await hass.services.async_call(
            DOMAIN, "set_assumed_state", {ATTR_ENTITY_ID: LIGHT, "percentage": 50}, blocking=True
        )
    with pytest.raises(ServiceValidationError, match="No Clicker entities"):
        await hass.services.async_call(
            DOMAIN,
            "set_assumed_state",
            {ATTR_ENTITY_ID: "light.other", "is_on": True},
            blocking=True,
        )
    transmit.assert_not_called()
