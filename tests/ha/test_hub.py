"""The receive hub: subscriptions on ESPHome nodes, matching, events."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable, Generator
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core.importer import import_rf_device_manager
from custom_components.clicker.core.radios import FoundRadio
from custom_components.clicker.hub import EVENT_COMMAND_RECEIVED

from .conftest import FoundRadios, corpus, rf_device_manager_store
from .test_init import setup_clicker

NODE_ENTRY = "esphome-node-entry"
RX_KEY = 7


class FakeClient:
    """The parts of aioesphomeapi's client the hub uses."""

    def __init__(self) -> None:
        self.receivers: list[Callable[[Any], None]] = []
        self.subscribe_calls = 0

    def subscribe_infrared_rf_receive(self, cb: Callable[[Any], None]) -> Callable[[], None]:
        self.subscribe_calls += 1
        self.receivers.append(cb)
        return lambda: self.receivers.remove(cb)

    def send(self, timings: list[int], *, key: int = RX_KEY, device_id: int = 0) -> None:
        """Deliver a reception, as the node would."""
        event = SimpleNamespace(device_id=device_id, key=key, timings=timings)
        for cb in list(self.receivers):
            cb(event)


class FakeNode:
    """The parts of ESPHome's RuntimeEntryData the hub uses."""

    def __init__(self) -> None:
        self.available = True
        self.client = FakeClient()
        self.device_callbacks: set[Callable[[], None]] = set()

    def async_subscribe_device_updated(self, cb: Callable[[], None]) -> Callable[[], None]:
        self.device_callbacks.add(cb)
        return lambda: self.device_callbacks.discard(cb)

    def set_available(self, available: bool) -> None:
        if not available:
            self.client.receivers.clear()  # the connection takes its callbacks along
        self.available = available
        for cb in list(self.device_callbacks):
            cb()


@pytest.fixture
def node(hass: HomeAssistant, found_radios: list[FoundRadio]) -> Generator[FakeNode]:
    """A loaded ESPHome entry whose receiver feeds the discovered radio."""
    fake = FakeNode()
    entry = MockConfigEntry(domain="esphome", entry_id=NODE_ENTRY, title="wESP32")
    entry.add_to_hass(hass)
    entry.runtime_data = fake
    entry.mock_state(hass, ConfigEntryState.LOADED)
    found_radios[0] = dataclasses.replace(found_radios[0], receiver_handle=(NODE_ENTRY, 0, RX_KEY))
    yield fake
    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)  # so teardown doesn't load ESPHome


@pytest.fixture
def patio_fan(hass_storage: dict[str, Any], found_radios: list[FoundRadio]) -> None:
    """Stored data: the imported patio fan on the discovered radio."""
    data = import_rf_device_manager(json.loads(json.dumps(rf_device_manager_store())), now=0).data
    data.radios[0].transmitter = found_radios[0].transmitter
    hass_storage[DOMAIN] = {"version": 1, "key": DOMAIN, "data": data.to_dict()}


@pytest.mark.usefixtures("patio_fan")
async def test_press_fires_once(hass: HomeAssistant, node: FakeNode) -> None:
    """A press fires one event; its repeats within the release gap don't."""
    events = async_capture_events(hass, EVENT_COMMAND_RECEIVED)
    entry = await setup_clicker(hass)
    assert node.client.subscribe_calls == 1

    node.client.send(corpus.HELD_CAPTURE)
    node.client.send(corpus.HELD_CAPTURE)
    await hass.async_block_till_done()
    assert [(e.data["device"], e.data["command"], e.data["kind"]) for e in events] == [
        ("Patio fan", "Power", "toggle")
    ]
    hub = entry.runtime_data.hub
    assert hub is not None
    assert [h.matches for h in hub.recent] == [("Patio fan / Power",), ()]
    assert hub.recent[0].bits is not None and len(hub.recent[0].bits) == 24


@pytest.mark.usefixtures("patio_fan")
async def test_other_receptions(hass: HomeAssistant, node: FakeNode) -> None:
    """Other endpoints are ignored; unknown codes are kept but fire nothing."""
    events = async_capture_events(hass, EVENT_COMMAND_RECEIVED)
    entry = await setup_clicker(hass)
    hub = entry.runtime_data.hub
    assert hub is not None

    node.client.send(corpus.HELD_CAPTURE, key=RX_KEY + 1)
    assert not hub.recent
    node.client.send(corpus.NOISE)
    await hass.async_block_till_done()
    assert events == [] and [h.matches for h in hub.recent] == [()]


@pytest.mark.usefixtures("patio_fan")
async def test_reconnect_resubscribes(
    hass: HomeAssistant, node: FakeNode, found_radios: FoundRadios
) -> None:
    """After a reconnect the hub listens again and re-discovers radios."""
    events = async_capture_events(hass, EVENT_COMMAND_RECEIVED)
    entry = await setup_clicker(hass)
    hub = entry.runtime_data.hub
    assert hub is not None and hub.listening == {NODE_ENTRY: True}

    node.set_available(False)
    assert hub.listening == {NODE_ENTRY: False}
    discoveries = found_radios.discoveries
    node.set_available(True)
    await hass.async_block_till_done()
    assert hub.listening == {NODE_ENTRY: True} and node.client.subscribe_calls == 2
    assert found_radios.discoveries == discoveries + 1

    node.client.send(corpus.EV1527_A)
    await hass.async_block_till_done()
    assert [e.data["command"] for e in events] == ["Oscillate"]


@pytest.mark.usefixtures("patio_fan")
async def test_unload_stops_listening(hass: HomeAssistant, node: FakeNode) -> None:
    """Unloading Clicker removes every callback it left on the node."""
    entry = await setup_clicker(hass)
    assert node.client.receivers and node.device_callbacks
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert not node.client.receivers and not node.device_callbacks


async def test_import_is_matched(
    hass: HomeAssistant, node: FakeNode, tmp_path: Any, found_radios: list[FoundRadio]
) -> None:
    """Codes imported while running are matched straight away."""
    (tmp_path / ".storage").mkdir()
    (tmp_path / ".storage" / "rf_device_manager").write_text(json.dumps(rf_device_manager_store()))
    hass.config.config_dir = str(tmp_path)
    events = async_capture_events(hass, EVENT_COMMAND_RECEIVED)
    await setup_clicker(hass)
    await hass.services.async_call(DOMAIN, "import_rf_device_manager", blocking=True)

    node.client.send(corpus.HELD_CAPTURE)
    await hass.async_block_till_done()
    assert [e.data["command"] for e in events] == ["Power"]
