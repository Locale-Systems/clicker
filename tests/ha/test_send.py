"""The send queue and the send_command action."""

from __future__ import annotations

import dataclasses
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core.radios import FoundRadio
from custom_components.clicker.core.stream import plan_command
from custom_components.clicker.hub import EVENT_COMMAND_RECEIVED
from custom_components.clicker.sender import SETTLE_GAP_S, SendQueue

from .conftest import F433, FakeNode, corpus
from .test_init import setup_clicker

pytestmark = pytest.mark.usefixtures("patio_fan")


@pytest.fixture
def transmit() -> Generator[AsyncMock]:
    """Home Assistant's radio_frequency send, as Clicker calls it."""
    with patch("custom_components.clicker.sender.async_send_command") as send:
        yield send


async def send(hass: HomeAssistant, **data: Any) -> dict[str, Any]:
    response = await hass.services.async_call(
        DOMAIN, "send_command", data, blocking=True, return_response=True
    )
    assert response is not None
    return dict(response)


async def test_send_command(
    hass: HomeAssistant, transmit: AsyncMock, found_radios: list[FoundRadio]
) -> None:
    """Names resolve; the planned unit goes to the radio's transmitter."""
    entry = await setup_clicker(hass)
    response = await send(hass, device="patio FAN", command="power")
    assert response["device"] == "Patio fan" and response["command"] == "Power"
    assert response["encoded"] is True and response["frames_on_air"] >= 8

    device = entry.runtime_data.data.devices[0]
    power = next(c for c in device.commands if c.name == "Power")
    plan = plan_command(power)
    ((_hass, transmitter, command), kwargs) = transmit.call_args
    assert transmitter == found_radios[0].transmitter
    assert command.frequency == F433 and command.timings == list(plan.unit)
    assert command.repeat_count == plan.repeat_count and kwargs["context"] is not None

    # By id, and with a one-off frame count.
    response = await send(hass, device=device.id, command=power.id, frames_on_air=1)
    assert response["frames_on_air"] == 1 and transmit.call_args.args[2].repeat_count == 0


@pytest.mark.parametrize(
    ("data", "error"),
    [
        pytest.param({"device": "Garage", "command": "Power"}, "No device named", id="device"),
        pytest.param({"device": "Patio fan", "command": "Up"}, "No command named", id="command"),
    ],
)
@pytest.mark.usefixtures("transmit", "found_radios")
async def test_send_unknown(hass: HomeAssistant, data: dict[str, str], error: str) -> None:
    """Unknown names are a clear validation error."""
    await setup_clicker(hass)
    with pytest.raises(ServiceValidationError, match=error):
        await send(hass, **data)


async def test_send_offline_radio(
    hass: HomeAssistant, transmit: AsyncMock, found_radios: list[FoundRadio]
) -> None:
    """A radio with no hardware right now can't send."""
    found_radios.clear()
    await setup_clicker(hass)
    with pytest.raises(HomeAssistantError, match="is offline"):
        await send(hass, device="Patio fan", command="Power")
    transmit.assert_not_called()


async def test_sends_are_paced(
    hass: HomeAssistant, transmit: AsyncMock, found_radios: list[FoundRadio]
) -> None:
    """A second send on a radio waits for the first one's airtime and the gap."""
    entry = await setup_clicker(hass)
    now = [100.0]
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        now[0] += seconds

    queue = SendQueue(hass, entry.runtime_data, clock=lambda: now[0], sleep=sleep)
    device = entry.runtime_data.data.devices[0]
    power, oscillate = device.commands
    first = await queue.async_send(device, power)
    second = await queue.async_send(device, oscillate)
    assert first.waited_s == 0
    assert waits == [pytest.approx(first.transmission.airtime_s + SETTLE_GAP_S)]
    assert second.waited_s == pytest.approx(waits[0])
    assert transmit.call_count == 2

    # Once the radio has been quiet long enough, no wait.
    now[0] += 10
    assert (await queue.async_send(device, power)).waited_s == 0 and len(waits) == 1


async def test_own_send_is_not_a_press(
    hass: HomeAssistant, transmit: AsyncMock, node: FakeNode, found_radios: list[FoundRadio]
) -> None:
    """Hearing Clicker's own transmission doesn't fire a press."""
    events = async_capture_events(hass, EVENT_COMMAND_RECEIVED)
    entry = await setup_clicker(hass)
    await send(hass, device="Patio fan", command="Power")
    node.client.send(corpus.HELD_CAPTURE)
    await hass.async_block_till_done()
    assert events == []
    hub = entry.runtime_data.hub
    assert hub is not None and [h.matches for h in hub.recent] == [()]


async def test_receive_only_radio(
    hass: HomeAssistant, transmit: AsyncMock, found_radios: list[FoundRadio]
) -> None:
    """A radio without a transmitter is refused before anything is sent."""
    entry = await setup_clicker(hass)
    entry.runtime_data.data.radios[0].transmitter = None
    found_radios[0] = dataclasses.replace(
        found_radios[0], transmitter_entity_id=None, transmitter_registry_id=None
    )
    with pytest.raises(ServiceValidationError, match="has no transmitter"):
        await send(hass, device="Patio fan", command="Power")
    transmit.assert_not_called()
