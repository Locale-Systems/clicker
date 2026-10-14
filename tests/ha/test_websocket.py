"""The panel's websocket API."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core.models import ClickerData
from custom_components.clicker.core.radios import FoundRadio

from .conftest import FakeNode, corpus
from .test_init import setup_clicker

pytestmark = pytest.mark.usefixtures("patio_fan", "found_radios")

# A button the patio fan doesn't have.
NEW_BUTTON = dict(corpus.builtin_cases())["synthetic: tri-state P1 x3"]


class Client:
    """A websocket client that numbers its own messages."""

    def __init__(self, ws: Any) -> None:
        self.ws = ws

    async def call(self, type_: str, **data: Any) -> dict[str, Any]:
        await self.ws.send_json_auto_id({"type": type_, **data})
        return dict(await self.ws.receive_json())

    async def ok(self, type_: str, **data: Any) -> Any:
        msg = await self.call(type_, **data)
        assert msg["success"], msg
        return msg["result"]

    async def error(self, type_: str, **data: Any) -> str:
        msg = await self.call(type_, **data)
        assert not msg["success"], msg
        return str(msg["error"]["code"])

    async def event(self) -> Any:
        msg = await self.ws.receive_json()
        assert msg["type"] == "event", msg
        return msg["event"]


@pytest.fixture
async def client(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> Client:
    await setup_clicker(hass)
    return Client(await hass_ws_client(hass))


def stored(hass_storage: dict[str, Any]) -> ClickerData:
    return ClickerData.from_dict(hass_storage[DOMAIN]["data"])


async def test_data(client: Client, found_radios: list[FoundRadio]) -> None:
    """Radios with their link state, devices with their commands."""
    data = await client.ok("clicker/data")
    (radio,) = data["radios"]
    assert radio["online"] and radio["can_send"] and radio["can_receive"]
    assert radio["node"] == found_radios[0].title
    (device,) = data["devices"]
    assert device["name"] == "Patio fan" and device["radio_id"] == radio["id"]
    assert device["ha_device_id"] is not None
    assert [b["entity_ids"] for b in device["bindings"]] == [["fan.patio_fan_fan"]]
    power = device["commands"][0]
    assert power["name"] == "Power" and power["kind"] == "toggle"
    assert power["encoded"] and len(power["bits"]) == 24 and power["captures"] == 1
    assert data["problems"] == []


async def test_subscribe_data(client: Client) -> None:
    """Subscribers get the data at once and after each change."""
    await client.ok("clicker/data/subscribe")
    device = (await client.event())["devices"][0]
    await client.ws.send_json_auto_id(
        {"type": "clicker/device/update", "device_id": device["id"], "name": "Porch fan"}
    )
    # The change is announced and answered; the order of the two doesn't matter.
    messages = [await client.ws.receive_json(), await client.ws.receive_json()]
    event = next(m for m in messages if m["type"] == "event")
    assert event["event"]["devices"][0]["name"] == "Porch fan"


async def test_devices(client: Client, hass_storage: dict[str, Any]) -> None:
    """Create, update and delete devices, with the editing rules enforced."""
    radio_id = (await client.ok("clicker/data"))["radios"][0]["id"]
    lamp = await client.ok("clicker/device/create", name="Lamp", radio_id=radio_id, area_id="den")
    assert lamp["frequency_hz"] == 433_920_000 and lamp["area_id"] == "den"
    assert "Lamp" in [d.name for d in stored(hass_storage).devices]

    assert await client.error("clicker/device/create", name="lamp", radio_id=radio_id) == (
        "invalid_format"
    )
    assert await client.error("clicker/device/create", name="X", radio_id="nope") == "not_found"

    lamp = await client.ok("clicker/device/update", device_id=lamp["id"], area_id=None)
    assert lamp["area_id"] is None
    await client.ok("clicker/device/delete", device_id=lamp["id"])
    assert [d.name for d in stored(hass_storage).devices] == ["Patio fan"]
    assert await client.error("clicker/device/delete", device_id=lamp["id"]) == "not_found"


async def test_commands_and_radios(client: Client, hass_storage: dict[str, Any]) -> None:
    """Edit and delete commands; rename radios; radios in use can't be deleted."""
    data = await client.ok("clicker/data")
    device, radio = data["devices"][0], data["radios"][0]
    power, oscillate = device["commands"]

    edited = await client.ok(
        "clicker/command/update",
        device_id=device["id"],
        command_id=oscillate["id"],
        name="Swing",
        kind="button",
        frames_on_air=4,
    )
    assert (edited["name"], edited["kind"], edited["frames_on_air"]) == ("Swing", "button", 4)
    assert await client.error(
        "clicker/command/update", device_id=device["id"], command_id=power["id"], name="swing"
    ) == ("invalid_format")
    await client.ok("clicker/command/delete", device_id=device["id"], command_id=power["id"])
    (kept,) = stored(hass_storage).devices[0].commands
    assert kept.name == "Swing" and stored(hass_storage).problems() == []

    renamed = await client.ok("clicker/radio/update", radio_id=radio["id"], name="Garage")
    assert renamed["name"] == "Garage"
    assert await client.error("clicker/radio/delete", radio_id=radio["id"]) == "invalid_format"


async def test_bindings(client: Client, hass: HomeAssistant, hass_storage: dict[str, Any]) -> None:
    """Entities are validated, created, changed and deleted; commands stay."""
    device = (await client.ok("clicker/data"))["devices"][0]
    power, oscillate = (c["id"] for c in device["commands"])
    checked = await client.ok(
        "clicker/binding/validate",
        device_id=device["id"],
        platform="fan",
        roles={"oscillate": oscillate},
    )
    assert checked == {"ok": False, "error": checked["error"]} and "power" in checked["error"]

    created = await client.ok(
        "clicker/binding/create",
        device_id=device["id"],
        platform="button",
        name="Extras",
        roles={"swing": oscillate},
    )
    await hass.async_block_till_done()
    assert hass.states.get("button.patio_fan_oscillate") is not None
    await client.ok(
        "clicker/binding/update",
        device_id=device["id"],
        binding_id=created["id"],
        roles={"swing": oscillate, "power": power},
    )
    await hass.async_block_till_done()
    assert hass.states.get("button.patio_fan_power") is not None
    assert await client.error(
        "clicker/binding/create", device_id=device["id"], platform="light", name="L", roles={}
    ) == ("invalid_format")
    await client.ok("clicker/binding/delete", device_id=device["id"], binding_id=created["id"])
    await hass.async_block_till_done()
    assert hass.states.get("button.patio_fan_power") is None
    assert len(stored(hass_storage).devices[0].commands) == 2


async def test_changes_need_admin(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """A non-admin can read and send, but not change anything or learn."""
    await setup_clicker(hass)
    client = Client(await hass_ws_client(hass, hass_read_only_access_token))
    data = await client.ok("clicker/data")
    device_id = data["devices"][0]["id"]
    assert await client.error("clicker/device/delete", device_id=device_id) == "unauthorized"
    assert await client.error("clicker/learn/subscribe", device_id=device_id) == "unauthorized"


async def test_send(client: Client, transmit: AsyncMock) -> None:
    """The Test button sends a stored command."""
    device = (await client.ok("clicker/data"))["devices"][0]
    power = device["commands"][0]
    sent = await client.ok(
        "clicker/command/send", device_id=device["id"], command_id=power["id"], frames_on_air=2
    )
    assert sent["command"] == "Power" and sent["frames_on_air"] == 2
    transmit.assert_called_once()


async def test_receptions(client: Client, node: FakeNode) -> None:
    """Live receptions: the recent ones first, then each as it arrives."""
    await client.ok("clicker/receptions/subscribe")
    assert (await client.event())["heard"] == []
    node.client.send(corpus.HELD_CAPTURE)
    (heard,) = (await client.event())["heard"]
    assert heard["matches"] == ["Patio fan / Power"] and len(heard["bits"]) == 24


async def test_learn(
    client: Client, node: FakeNode, transmit: AsyncMock, hass_storage: dict[str, Any]
) -> None:
    """Candidates arrive live, can be tested, and are saved as commands."""
    device = (await client.ok("clicker/data"))["devices"][0]
    await client.ok("clicker/learn/subscribe", device_id=device["id"])
    first = await client.event()
    session_id = first["session_id"]
    assert first["candidates"] == [] and first["frequency_hz"] == 433_920_000

    node.client.send(NEW_BUTTON)
    node.client.send(NEW_BUTTON)
    await client.event()
    (candidate,) = (await client.event())["candidates"]
    assert candidate["sightings"] == 2 and candidate["usable"] and candidate["encoded"]
    assert candidate["known_as"] == []

    node.client.send(corpus.HELD_CAPTURE)  # a button the fan already has
    candidates = (await client.event())["candidates"]
    assert {"device": "Patio fan", "command": "Power", "distance": 0} in [
        k for c in candidates for k in c["known_as"]
    ]

    fingerprint = candidate["fingerprint"]
    await client.ok("clicker/learn/test", session_id=session_id, fingerprint=fingerprint)
    transmit.assert_called_once()
    saved = await client.ok(
        "clicker/learn/save", session_id=session_id, fingerprint=fingerprint, name="Light"
    )
    assert saved["name"] == "Light" and saved["kind"] == "button" and saved["encoded"]
    names = [c.name for c in stored(hass_storage).devices[0].commands]
    assert names == ["Power", "Oscillate", "Light"]

    # Relearning an existing command replaces its code and keeps its id.
    power = device["commands"][0]
    relearned = await client.ok(
        "clicker/learn/save",
        session_id=session_id,
        fingerprint=fingerprint,
        command_id=power["id"],
    )
    assert relearned["id"] == power["id"] and relearned["bits"] == saved["bits"]
    assert relearned["captures"] == 2
    assert await client.error(
        "clicker/learn/save", session_id=session_id, fingerprint="nope", name="X"
    ) == ("not_found")


async def test_learn_session_ends_with_subscription(client: Client) -> None:
    """Unsubscribing closes the session."""
    device = (await client.ok("clicker/data"))["devices"][0]
    sub = await client.call("clicker/learn/subscribe", device_id=device["id"])
    session_id = (await client.event())["session_id"]
    await client.ok("unsubscribe_events", subscription=sub["id"])
    assert await client.error("clicker/learn/test", session_id=session_id, fingerprint="x") == (
        "not_found"
    )
