"""Fixtures for Clicker's Home Assistant tests."""

from __future__ import annotations

import pathlib
import sys
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

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


@pytest.fixture
def found_radios() -> Generator[list[FoundRadio]]:
    """What discovery finds; tests change the list to change the hardware."""
    found = [wesp32()]
    with (
        patch(
            "custom_components.clicker.runtime.async_find_radios",
            AsyncMock(side_effect=lambda hass: list(found)),
        ),
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
