"""Setup, config flow, storage and diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.clicker.const import DOMAIN
from custom_components.clicker.core.models import ClickerData, Device, Radio
from custom_components.clicker.core.radios import FoundRadio

from .conftest import F433, wesp32


async def setup_clicker(hass: HomeAssistant) -> MockConfigEntry:
    """Add and load a Clicker entry."""
    entry = MockConfigEntry(domain=DOMAIN, title="Clicker")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow_single_instance(hass: HomeAssistant, found_radios: Any) -> None:
    """The user step creates the entry; a second one is refused."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert again["type"] is FlowResultType.ABORT
    assert again["reason"] == "single_instance_allowed"


async def test_discovered_radio_is_saved(
    hass: HomeAssistant, hass_storage: dict[str, Any], found_radios: list[FoundRadio]
) -> None:
    """A radio found at startup is stored, and kept across a reload."""
    entry = await setup_clicker(hass)
    assert entry.state is ConfigEntryState.LOADED
    stored = ClickerData.from_dict(hass_storage[DOMAIN]["data"])
    assert [(r.frequency_hz, r.transmitter) for r in stored.radios] == [(F433, "reg-tx-433")]

    radio_id = stored.radios[0].id
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert [r.id for r in entry.runtime_data.data.radios] == [radio_id]
    assert radio_id in entry.runtime_data.links


async def test_unchanged_radios_are_not_rewritten(
    hass: HomeAssistant, hass_storage: dict[str, Any], found_radios: list[FoundRadio]
) -> None:
    """Rediscovering the same hardware doesn't write the file."""
    entry = await setup_clicker(hass)
    hass_storage[DOMAIN]["data"]["marker"] = True
    await entry.runtime_data.async_refresh_radios(hass)
    assert hass_storage[DOMAIN]["data"].get("marker") is True


async def test_stored_data_loads(
    hass: HomeAssistant, hass_storage: dict[str, Any], found_radios: list[FoundRadio]
) -> None:
    """Stored devices load; an offline radio is kept unlinked."""
    shed = Radio(name="Shed", frequency_hz=303_870_000, transmitter="radio_frequency.shed")
    fan = Device(name="Shed fan", radio_id=shed.id, frequency_hz=303_870_000)
    hass_storage[DOMAIN] = {
        "version": 1,
        "key": DOMAIN,
        "data": ClickerData(radios=[shed], devices=[fan]).to_dict(),
    }
    entry = await setup_clicker(hass)
    data = entry.runtime_data.data
    assert [d.name for d in data.devices] == ["Shed fan"]
    assert shed.id not in entry.runtime_data.links
    assert len(data.radios) == 2  # the shed radio plus the discovered wESP32


async def test_newer_schema_refuses_to_load(
    hass: HomeAssistant, hass_storage: dict[str, Any], found_radios: list[FoundRadio]
) -> None:
    """Data from a newer Clicker fails setup and is left untouched."""
    newer = {"version": 99, "radios": [], "devices": []}
    hass_storage[DOMAIN] = {"version": 1, "key": DOMAIN, "data": newer}
    entry = await setup_clicker(hass)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert hass_storage[DOMAIN]["data"] == newer


async def test_remove_entry_deletes_data(
    hass: HomeAssistant, hass_storage: dict[str, Any], found_radios: list[FoundRadio]
) -> None:
    """Removing the integration removes its file."""
    entry = await setup_clicker(hass)
    assert DOMAIN in hass_storage
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert DOMAIN not in hass_storage


async def test_diagnostics(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, found_radios: list[FoundRadio]
) -> None:
    """Diagnostics show found and stored radios and how they link."""
    entry = await setup_clicker(hass)
    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert diagnostics["found_radios"][0]["node"] == wesp32().node
    radio_id = diagnostics["stored_radios"][0]["id"]
    assert diagnostics["links"] == {radio_id: wesp32().node}
    assert diagnostics["devices"] == [] and diagnostics["problems"] == []
