"""Cover entities: Open/Close/Stop sent, presses followed, the type from options."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
    STATE_CLOSED,
    STATE_OPEN,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import mock_restore_cache

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

from .conftest import F433, FakeNode, corpus
from .test_fan import setup

COVER = "cover.patio_awning"
# The real awning remote; Close isn't in the corpus, so it reuses the release code.
FRAMES = {
    "open": ("Open", corpus.CANOPY_OPEN_FRAME),
    "close": ("Close", corpus.CANOPY_RELEASE_FRAME),
    "stop": ("Stop", corpus.CANOPY_STOP_FRAME),
}


def store(
    hass_storage: dict[str, Any],
    transmitter: str | None,
    roles: tuple[str, ...] = ("open", "close", "stop"),
    options: dict[str, str] | None = None,
) -> dict[str, EncodedFrame]:
    """The patio awning; returns its frames by command name."""
    radio = Radio(name="Gateway", frequency_hz=F433, transmitter=transmitter)
    device = Device(name="Patio awning", radio_id=radio.id, frequency_hz=F433)
    binding = Binding(platform="cover", name="Patio awning", options=options or {})
    frames: dict[str, EncodedFrame] = {}
    for role in roles:
        name, timings = FRAMES[role]
        frame = frame_from_capture(timings)
        assert isinstance(frame, EncodedFrame)
        command = Command(name=name, kind=CommandKind.BUTTON, frame=frame)
        device.commands.append(command)
        binding.roles[role] = command.id
        frames[name] = frame
    device.bindings.append(binding)
    data = ClickerData(radios=[radio], devices=[device])
    hass_storage[DOMAIN] = {"version": 1, "key": DOMAIN, "data": data.to_dict()}
    return frames


def sent(transmit: AsyncMock, frames: dict[str, EncodedFrame]) -> list[str]:
    """The names of the commands sent so far."""
    names = {tuple(encode(frame.spec)): name for name, frame in frames.items()}
    return [names[tuple(c.args[2].timings)] for c in transmit.call_args_list]


async def call(hass: HomeAssistant, service: str) -> None:
    await hass.services.async_call(COVER_DOMAIN, service, {ATTR_ENTITY_ID: COVER}, blocking=True)


def state_of(hass: HomeAssistant) -> State:
    state = hass.states.get(COVER)
    assert state is not None
    return state


async def test_open_close_stop(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    found_radios: list[FoundRadio],
    transmit: AsyncMock,
) -> None:
    """Open and Close set the state as they're sent; Stop leaves it."""
    frames = store(hass_storage, found_radios[0].transmitter, options={"device_class": "awning"})
    await setup(hass)
    state = state_of(hass)
    assert state.state == STATE_UNKNOWN and state.attributes[ATTR_DEVICE_CLASS] == "awning"
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )
    await call(hass, SERVICE_OPEN_COVER)
    assert state_of(hass).state == STATE_OPEN
    await call(hass, SERVICE_STOP_COVER)
    assert state_of(hass).state == STATE_OPEN
    await call(hass, SERVICE_CLOSE_COVER)
    await call(hass, SERVICE_CLOSE_COVER)  # always sent: a motor ignores a repeat
    assert state_of(hass).state == STATE_CLOSED
    assert sent(transmit, frames) == ["Open", "Stop", "Close", "Close"]


async def test_without_stop(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    found_radios: list[FoundRadio],
    transmit: AsyncMock,
) -> None:
    """Without a Stop button the cover can't stop, and has no device class."""
    store(hass_storage, found_radios[0].transmitter, roles=("open", "close"))
    await setup(hass)
    state = state_of(hass)
    assert ATTR_DEVICE_CLASS not in state.attributes
    assert not state.attributes[ATTR_SUPPORTED_FEATURES] & CoverEntityFeature.STOP


async def test_remote_presses(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    found_radios: list[FoundRadio],
    node: FakeNode,
    transmit: AsyncMock,
) -> None:
    """The remote's frames arrive one per reception and still move the cover."""
    store(hass_storage, found_radios[0].transmitter)
    await setup(hass)
    for _ in range(4):
        node.client.send(corpus.CANOPY_OPEN_FRAME)
    await hass.async_block_till_done()
    assert state_of(hass).state == STATE_OPEN
    node.client.send(corpus.CANOPY_STOP_FRAME)
    await hass.async_block_till_done()
    assert state_of(hass).state == STATE_OPEN
    transmit.assert_not_called()


async def test_restore_and_assumed_state(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    found_radios: list[FoundRadio],
    transmit: AsyncMock,
) -> None:
    """The last state survives a restart; set_assumed_state corrects it."""
    mock_restore_cache(hass, [State(COVER, STATE_CLOSED)])
    store(hass_storage, found_radios[0].transmitter)
    await setup(hass)
    assert state_of(hass).state == STATE_CLOSED
    await hass.services.async_call(
        DOMAIN, "set_assumed_state", {ATTR_ENTITY_ID: COVER, "is_closed": False}, blocking=True
    )
    assert state_of(hass).state == STATE_OPEN
    with pytest.raises(ServiceValidationError, match="has no is_on"):
        await hass.services.async_call(
            DOMAIN, "set_assumed_state", {ATTR_ENTITY_ID: COVER, "is_on": True}, blocking=True
        )
    transmit.assert_not_called()
