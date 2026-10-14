"""The import_rf_device_manager action."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core.models import ClickerData, CommandKind, EncodedFrame
from custom_components.clicker.core.radios import FoundRadio

from .conftest import rf_device_manager_store
from .test_init import setup_clicker


@pytest.fixture
def config_dir(hass: HomeAssistant, tmp_path: pathlib.Path) -> pathlib.Path:
    """Point Home Assistant's config directory at an empty folder."""
    (tmp_path / ".storage").mkdir()
    hass.config.config_dir = str(tmp_path)
    return tmp_path


def write_rfdm(config_dir: pathlib.Path, store: dict[str, Any]) -> None:
    """Put an rf_device_manager file where the action reads it."""
    (config_dir / ".storage" / "rf_device_manager").write_text(json.dumps(store))


async def run_import(hass: HomeAssistant) -> dict[str, Any]:
    response = await hass.services.async_call(
        DOMAIN, "import_rf_device_manager", blocking=True, return_response=True
    )
    assert response is not None
    return dict(response)


async def test_import_joins_discovered_radio(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_dir: pathlib.Path,
    found_radios: list[FoundRadio],
) -> None:
    """Imported devices land on the discovered radio and are saved."""
    write_rfdm(config_dir, rf_device_manager_store("radio_frequency.from_production"))
    entry = await setup_clicker(hass)
    radio_id = entry.runtime_data.data.radios[0].id

    response = await run_import(hass)
    assert response["problems"] == []
    assert "Patio fan: imported with 2 commands" in response["notes"]

    stored = ClickerData.from_dict(hass_storage[DOMAIN]["data"])
    assert [r.id for r in stored.radios] == [radio_id]
    (device,) = stored.devices
    assert device.radio_id == radio_id
    kinds = {c.name: c.kind for c in device.commands}
    assert kinds == {"Power": CommandKind.TOGGLE, "Oscillate": CommandKind.TOGGLE}
    assert all(isinstance(c.frame, EncodedFrame) for c in device.commands)

    # Again: nothing new.
    response = await run_import(hass)
    assert "Patio fan: skipped, a device with that name exists" in response["notes"]
    assert len(ClickerData.from_dict(hass_storage[DOMAIN]["data"]).devices) == 1


async def test_import_matches_transmitter_entity(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_dir: pathlib.Path,
    found_radios: list[FoundRadio],
) -> None:
    """A transmitter entity that exists here is matched by its registry id."""
    reg = entity_registry.async_get_or_create(
        "radio_frequency", "esphome", "hall-tx", suggested_object_id="hall_rf"
    )
    hall = FoundRadio(
        "hall",
        "Hall",
        found_radios[0].frequency_hz,
        found_radios[0].frequency_range,
        reg.entity_id,
        reg.id,
    )
    found_radios.append(hall)  # two radios on the band: the frequency alone won't do
    write_rfdm(config_dir, rf_device_manager_store(reg.entity_id))
    entry = await setup_clicker(hass)

    await run_import(hass)
    data = entry.runtime_data.data
    radio = data.radio(data.devices[0].radio_id)
    assert radio is not None and radio.transmitter == reg.id
    assert entry.runtime_data.links[radio.id].node == "hall"
    assert len(data.radios) == 2


async def test_import_without_file(
    hass: HomeAssistant, config_dir: pathlib.Path, found_radios: list[FoundRadio]
) -> None:
    """No rf_device_manager data: a clear error."""
    await setup_clicker(hass)
    with pytest.raises(ServiceValidationError, match="No rf_device_manager data"):
        await run_import(hass)


async def test_import_over_websocket(
    hass: HomeAssistant,
    hass_ws_client: Any,
    config_dir: pathlib.Path,
    found_radios: list[FoundRadio],
) -> None:
    """The panel checks for rf_device_manager data, then imports it."""
    await setup_clicker(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "clicker/import/status"})
    assert (await ws.receive_json())["result"] == {"available": False}

    write_rfdm(config_dir, rf_device_manager_store())
    await ws.send_json_auto_id({"type": "clicker/import/status"})
    assert (await ws.receive_json())["result"] == {"available": True}
    await ws.send_json_auto_id({"type": "clicker/import/run"})
    result = (await ws.receive_json())["result"]
    assert "Patio fan: imported with 2 commands" in result["notes"] and result["problems"] == []
