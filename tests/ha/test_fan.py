"""Fan entities: what they send, and how remote presses move their state."""

from __future__ import annotations

import dataclasses
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.fan import (
    ATTR_DIRECTION,
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    DIRECTION_REVERSE,
    SERVICE_OSCILLATE,
    SERVICE_SET_DIRECTION,
    SERVICE_SET_PERCENTAGE,
    FanEntityFeature,
)
from homeassistant.components.fan import (
    DOMAIN as FAN_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    mock_restore_cache,
)

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core.encoder import encode
from custom_components.clicker.core.models import (
    Binding,
    ClickerData,
    Command,
    CommandKind,
    Device,
    EncodedFrame,
    Radio,
    frame_from_capture,
)
from custom_components.clicker.core.radios import FoundRadio
from custom_components.clicker.hub import EVENT_REMOTE_PRESSED

from .conftest import F433, FakeNode, corpus
from .test_init import setup_clicker

PREFIX = "00000111100010110000"
PATIO = {  # role: (command name, kind, last 4 bits)
    "power": ("Power", CommandKind.TOGGLE, "0001"),
    "speed_1": ("Speed 1", CommandKind.STATE, "1001"),
    "speed_2": ("Speed 2", CommandKind.STATE, "0101"),
    "speed_3": ("Speed 3", CommandKind.STATE, "0111"),
    "oscillate": ("Oscillate", CommandKind.TOGGLE, "0011"),
}
MINKA = {
    "off": ("Off", CommandKind.STATE, "1000"),
    **{f"speed_{n}": (f"Speed {n}", CommandKind.STATE, f"{n:04b}") for n in range(1, 7)},
    "direction": ("Reverse", CommandKind.TOGGLE, "1111"),
}
HELD = frame_from_capture(corpus.HELD_CAPTURE)
assert isinstance(HELD, EncodedFrame)


def frame(tail: str) -> EncodedFrame:
    return EncodedFrame(spec=dataclasses.replace(HELD.spec, bits=PREFIX + tail))


def press(tail: str) -> list[int]:
    """A held press of the button: several agreeing frames."""
    return encode(frame(tail).spec) * 5


def store(hass_storage: dict[str, Any], transmitter: str | None, buttons: dict[str, Any]) -> None:
    radio = Radio(name="Gateway", frequency_hz=F433, transmitter=transmitter)
    device = Device(name="Ceiling fan", radio_id=radio.id, frequency_hz=F433)
    binding = Binding(platform="fan", name="Ceiling fan")
    for role, (name, kind, tail) in buttons.items():
        command = Command(name=name, kind=kind, frame=frame(tail))
        device.commands.append(command)
        binding.roles[role] = command.id
    device.bindings.append(binding)
    data = ClickerData(radios=[radio], devices=[device])
    hass_storage[DOMAIN] = {"version": 1, "key": DOMAIN, "data": data.to_dict()}


@pytest.fixture
def patio(hass_storage: dict[str, Any], found_radios: list[FoundRadio]) -> None:
    store(hass_storage, found_radios[0].transmitter, PATIO)


@pytest.fixture
def minka(hass_storage: dict[str, Any], found_radios: list[FoundRadio]) -> None:
    store(hass_storage, found_radios[0].transmitter, MINKA)


async def setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = await setup_clicker(hass)
    assert entry.runtime_data.sender is not None
    entry.runtime_data.sender._sleep = AsyncMock()  # don't wait out the airtime
    return entry


ENTITY = "fan.ceiling_fan"


async def call(hass: HomeAssistant, service: str, **data: Any) -> None:
    await hass.services.async_call(
        FAN_DOMAIN, service, {ATTR_ENTITY_ID: ENTITY, **data}, blocking=True
    )


def sent(transmit: AsyncMock, buttons: dict[str, Any]) -> list[str]:
    """The names of the buttons sent so far."""
    names = {tuple(encode(frame(tail).spec)): name for name, _kind, tail in buttons.values()}
    return [names[tuple(c.args[2].timings)] for c in transmit.call_args_list]


@pytest.mark.usefixtures("patio")
async def test_patio_fan_sends(hass: HomeAssistant, transmit: AsyncMock) -> None:
    """A power-toggle fan: toggles only when the state must change."""
    await setup(hass)
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == STATE_OFF
    features = state.attributes[ATTR_SUPPORTED_FEATURES]
    assert features & FanEntityFeature.SET_SPEED and features & FanEntityFeature.OSCILLATE
    assert not features & FanEntityFeature.DIRECTION

    await call(hass, SERVICE_TURN_ON)
    await call(hass, SERVICE_TURN_ON)  # already on: no second toggle
    await call(hass, SERVICE_SET_PERCENTAGE, **{ATTR_PERCENTAGE: 33})
    await call(hass, SERVICE_OSCILLATE, **{ATTR_OSCILLATING: True})
    await call(hass, SERVICE_OSCILLATE, **{ATTR_OSCILLATING: True})
    await call(hass, SERVICE_TURN_OFF)
    await call(hass, SERVICE_TURN_OFF)
    assert sent(transmit, PATIO) == ["Power", "Speed 1", "Oscillate", "Power"]

    transmit.reset_mock()
    await call(hass, SERVICE_TURN_ON, **{ATTR_PERCENTAGE: 100})  # from off: power, then speed
    assert sent(transmit, PATIO) == ["Power", "Speed 3"]
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == STATE_ON
    assert state.attributes[ATTR_PERCENTAGE] == 100 and state.attributes[ATTR_OSCILLATING]


@pytest.mark.usefixtures("minka")
async def test_minka_style_fan(hass: HomeAssistant, transmit: AsyncMock) -> None:
    """Off + 6 speeds + a reverse toggle: speeds switch it on."""
    await setup(hass)
    state = hass.states.get(ENTITY)
    assert state is not None
    assert state.attributes[ATTR_SUPPORTED_FEATURES] & FanEntityFeature.DIRECTION
    assert state.attributes["percentage_step"] == pytest.approx(100 / 6)

    await call(hass, SERVICE_TURN_ON)  # never run: the top speed
    await call(hass, SERVICE_SET_PERCENTAGE, **{ATTR_PERCENTAGE: 34})
    await call(hass, SERVICE_SET_DIRECTION, **{ATTR_DIRECTION: DIRECTION_REVERSE})
    await call(hass, SERVICE_SET_DIRECTION, **{ATTR_DIRECTION: DIRECTION_REVERSE})
    await call(hass, SERVICE_TURN_OFF)
    await call(hass, SERVICE_TURN_ON)  # resumes speed 3
    assert sent(transmit, MINKA) == ["Speed 6", "Speed 3", "Reverse", "Off", "Speed 3"]


@pytest.mark.usefixtures("patio")
async def test_remote_presses(hass: HomeAssistant, node: FakeNode, transmit: AsyncMock) -> None:
    """Presses move the state, carrying the press event's context; nothing is sent."""
    events = async_capture_events(hass, EVENT_REMOTE_PRESSED)
    await setup(hass)

    node.client.send(press(PATIO["speed_2"][2]))
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == STATE_ON
    assert state.attributes[ATTR_PERCENTAGE] == 66  # speed 2 of 3
    assert state.context.id == events[0].context.id

    node.client.send(press(PATIO["power"][2]))
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == STATE_OFF
    assert state.attributes["last_speed"] == 2
    transmit.assert_not_called()


@pytest.mark.usefixtures("patio")
async def test_failed_send_restores_state(hass: HomeAssistant, transmit: AsyncMock) -> None:
    """If the radio refuses, the assumed state goes back."""
    await setup(hass)
    transmit.side_effect = HomeAssistantError("transmitter unavailable")
    with pytest.raises(HomeAssistantError):
        await call(hass, SERVICE_TURN_ON)
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == STATE_OFF


@pytest.mark.usefixtures("patio")
async def test_set_assumed_state(hass: HomeAssistant, transmit: AsyncMock) -> None:
    """Resync sets the state without sending."""
    await setup(hass)
    await hass.services.async_call(
        DOMAIN,
        "set_assumed_state",
        {ATTR_ENTITY_ID: ENTITY, ATTR_PERCENTAGE: 66, ATTR_OSCILLATING: True},
        blocking=True,
    )
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == STATE_ON
    assert state.attributes[ATTR_PERCENTAGE] == 66 and state.attributes[ATTR_OSCILLATING]
    transmit.assert_not_called()

    await call(hass, SERVICE_TURN_OFF)  # the toggle now knows the fan is on
    assert sent(transmit, PATIO) == ["Power"]


@pytest.mark.usefixtures("patio")
async def test_restored_state(hass: HomeAssistant) -> None:
    """The assumed state survives a restart."""
    mock_restore_cache(hass, [State(ENTITY, STATE_OFF, {ATTR_OSCILLATING: True, "last_speed": 3})])
    await setup(hass)
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == STATE_OFF
    assert state.attributes[ATTR_OSCILLATING] and state.attributes["last_speed"] == 3


@pytest.mark.usefixtures("patio")
async def test_fan_follows_data_changes(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, found_radios: list[FoundRadio]
) -> None:
    """Losing the power button removes the fan; radios going offline make it unavailable."""
    entry = await setup(hass)
    runtime = entry.runtime_data
    assert entity_registry.async_get(ENTITY) is not None

    found_radios.clear()
    await runtime.async_refresh_radios(hass)
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == "unavailable"

    device = runtime.data.devices[0]
    power = device.command(device.bindings[0].roles["power"])
    assert power is not None
    async with runtime.lock:
        device.commands.remove(power)
        del device.bindings[0].roles["power"]
        await runtime.async_save()
    await hass.async_block_till_done()
    assert entity_registry.async_get(ENTITY) is None and hass.states.get(ENTITY) is None
