"""Fixtures for Clicker's Home Assistant tests."""

from __future__ import annotations

import dataclasses
import json
import pathlib
import sys
from collections.abc import Callable, Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core.importer import import_rf_device_manager
from custom_components.clicker.core.radios import FoundRadio

# corpus.py (shared with the script suites) imports the core as top-level `core`.
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "custom_components" / "clicker")]
import corpus  # noqa: E402

F433 = 433_920_000


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load custom_components/clicker."""


def wesp32() -> FoundRadio:
    """The wESP32 gateway as discovery reports it."""
    return FoundRadio(
        node="wesp32-rf-gateway",
        title="wESP32 RF Gateway",
        frequency_hz=F433,
        frequency_range=(F433, F433),
        transmitter_entity_id="radio_frequency.wesp32_rf_gateway_rf_transmitter",
        transmitter_registry_id="reg-tx-433",
        receiver="AA:BB:CC:DD:EE:FF:0:rf_receiver",
    )


class FoundRadios(list[FoundRadio]):
    """What discovery finds, and how often Clicker looked."""

    discoveries = 0

    async def discover(self, hass: object) -> list[FoundRadio]:
        self.discoveries += 1
        return list(self)


@pytest.fixture
def found_radios() -> Generator[FoundRadios]:
    """What discovery finds; tests change the list to change the hardware."""
    found = FoundRadios([wesp32()])
    with (
        patch("custom_components.clicker.runtime.async_find_radios", found.discover),
        patch(
            "custom_components.clicker.diagnostics.async_find_radios",
            AsyncMock(side_effect=lambda hass: list(found)),
        ),
    ):
        yield found


def rf_device_manager_store(transmitter: str = "radio_frequency.hall_rf") -> dict[str, object]:
    """A small rf_device_manager storage file, built from corpus captures."""

    def slot(timings: list[int]) -> dict[str, object]:
        return {"protocol": "raw", "frequency": F433, "data": timings, "repeat": 0}

    return {
        "version": 1,
        "minor_version": 1,
        "key": "rf_device_manager",
        "data": {
            "devices": {
                "d1": {
                    "id": "d1",
                    "name": "patio",
                    "transmitter": transmitter,
                    "settings": {"description": "Patio fan", "frequency": F433},
                }
            },
            "codes": {
                "fan": {
                    "id": "fan",
                    "device_id": "d1",
                    "name": "fan",
                    "entity_type": "fan",
                    "enabled": True,
                    "settings": {},
                    "rf_data": {
                        "commands": {
                            "power": slot(corpus.HELD_CAPTURE),
                            "oscillate": slot(corpus.EV1527_A),
                        }
                    },
                }
            },
        },
    }


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


@pytest.fixture
def transmit() -> Generator[AsyncMock]:
    """Home Assistant's radio_frequency send, as Clicker calls it."""
    with patch("custom_components.clicker.sender.async_send_command") as send:
        yield send
