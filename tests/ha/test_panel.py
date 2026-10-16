"""The sidebar panel: served, registered for admins, removed on unload."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.clicker import panel
from custom_components.clicker.panel import PANEL_ELEMENT, _build_hash

from .test_init import setup_clicker

pytestmark = pytest.mark.usefixtures("found_radios")


@pytest.fixture
def built(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A stand-in for the panel build, which source checkouts don't carry."""
    (tmp_path / f"{PANEL_ELEMENT}.js").write_text(
        "customElements.define('clicker-panel', class {});"
    )
    monkeypatch.setattr(panel, "FRONTEND_DIR", tmp_path)
    return tmp_path


async def test_panel_registered_for_admins(hass: HomeAssistant, built: Path) -> None:
    """With a frontend, the panel module is served and added to the sidebar."""
    hass.config.components.add("frontend")
    with (
        patch("homeassistant.components.panel_custom.async_register_panel") as register,
        patch("homeassistant.components.frontend.async_remove_panel") as remove,
        patch(
            "homeassistant.components.http.HomeAssistantHTTP.async_register_static_paths",
            AsyncMock(),
        ) as static,
    ):
        entry = await setup_clicker(hass)
        kwargs: dict[str, Any] = register.call_args.kwargs
        assert kwargs["frontend_url_path"] == "clicker"
        assert kwargs["webcomponent_name"] == PANEL_ELEMENT
        assert kwargs["require_admin"] is True
        assert kwargs["module_url"] == f"/clicker_static/clicker-panel.js?v={_build_hash()}"
        (config,) = static.call_args.args[0]
        assert config.url_path == "/clicker_static" and config.path == str(built)

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        remove.assert_called_once_with(hass, "clicker")
        assert register.call_count == 2 and static.call_count == 1  # static paths once


async def test_no_frontend_no_panel(hass: HomeAssistant) -> None:
    """Without a frontend (tests, headless installs) setup still works."""
    with patch("homeassistant.components.panel_custom.async_register_panel") as register:
        await setup_clicker(hass)
    register.assert_not_called()


async def test_unbuilt_panel(
    hass: HomeAssistant,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A source checkout without a panel build still sets up, without the panel."""
    hass.config.components.add("frontend")
    monkeypatch.setattr(panel, "FRONTEND_DIR", tmp_path)
    with patch("homeassistant.components.panel_custom.async_register_panel") as register:
        await setup_clicker(hass)
    register.assert_not_called()
    assert "panel isn't built" in caplog.text
