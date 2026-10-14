"""The receive hub: subscriptions on ESPHome nodes, matching, events."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core.radios import FoundRadio
from custom_components.clicker.hub import EVENT_REMOTE_PRESSED

from .conftest import NODE_ENTRY, RX_KEY, FakeNode, FoundRadios, corpus, rf_device_manager_store
from .test_init import setup_clicker


@pytest.mark.usefixtures("patio_fan")
async def test_press_fires_once(hass: HomeAssistant, node: FakeNode) -> None:
    """A press fires one event; its repeats within the release gap don't."""
    events = async_capture_events(hass, EVENT_REMOTE_PRESSED)
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
async def test_frames_follow_on(hass: HomeAssistant, node: FakeNode) -> None:
    """Frames that arrive one per reception agree with each other."""
    entry = await setup_clicker(hass)
    hub = entry.runtime_data.hub
    assert hub is not None
    agreeing: list[int] = []
    hub.async_add_listener(
        lambda _heard, reception, _radio: agreeing.append(reception.agreeing_frames)
    )

    for _ in range(3):
        node.client.send(corpus.CANOPY_OPEN_FRAME)
    node.client.send(corpus.CANOPY_OPEN_FRAME, key=RX_KEY + 1)  # not a radio of ours
    node.client.send(corpus.CANOPY_RELEASE_FRAME)
    assert agreeing == [1, 2, 3, 1]


@pytest.mark.usefixtures("patio_fan")
async def test_other_receptions(hass: HomeAssistant, node: FakeNode) -> None:
    """Other endpoints are ignored; unknown codes are kept but fire nothing."""
    events = async_capture_events(hass, EVENT_REMOTE_PRESSED)
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
    events = async_capture_events(hass, EVENT_REMOTE_PRESSED)
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
async def test_esphome_reload_relistens(
    hass: HomeAssistant, node: FakeNode, found_radios: FoundRadios
) -> None:
    """A reloaded ESPHome entry (new runtime data) is listened to straight away."""
    entry = await setup_clicker(hass)
    hub = entry.runtime_data.hub
    assert hub is not None
    esphome = hass.config_entries.async_get_entry(NODE_ENTRY)
    assert esphome is not None

    # Reloaded: new runtime data, loaded before the node reconnects, and
    # until then ESPHome only knows the transmitter.
    node.set_available(False)
    connected = found_radios[0]
    found_radios[0] = dataclasses.replace(connected, receiver=None, receiver_handle=None)
    reloaded = FakeNode()
    reloaded.available = False
    esphome.runtime_data = reloaded
    esphome.mock_state(hass, ConfigEntryState.LOADED)
    await hass.async_block_till_done()
    assert hub.listening == {NODE_ENTRY: False} and not node.device_callbacks
    assert entry.runtime_data.data.radios[0].receiver == connected.receiver

    found_radios[0] = connected
    reloaded.set_available(True)
    await hass.async_block_till_done()
    assert hub.listening == {NODE_ENTRY: True} and reloaded.client.subscribe_calls == 1
    events = async_capture_events(hass, EVENT_REMOTE_PRESSED)
    reloaded.client.send(corpus.HELD_CAPTURE)
    await hass.async_block_till_done()
    assert [e.data["command"] for e in events] == ["Power"]


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
    events = async_capture_events(hass, EVENT_REMOTE_PRESSED)
    await setup_clicker(hass)
    await hass.services.async_call(DOMAIN, "import_rf_device_manager", blocking=True)

    node.client.send(corpus.HELD_CAPTURE)
    await hass.async_block_till_done()
    assert [e.data["command"] for e in events] == ["Power"]
