"""The sidebar panel: served, registered for admins, removed on unload."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.clicker.panel import FRONTEND_DIR, PANEL_ELEMENT

from .test_init import setup_clicker

pytestmark = pytest.mark.usefixtures("found_radios")


async def test_panel_registered_for_admins(hass: HomeAssistant) -> None:
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
        assert kwargs["module_url"] == "/clicker_static/clicker-panel.js?v=0.1.0"
        (config,) = static.call_args.args[0]
        assert config.url_path == "/clicker_static" and config.path == str(FRONTEND_DIR)

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        remove.assert_called_once_with(hass, "clicker")
        assert register.call_count == 2 and static.call_count == 1  # static paths once


async def test_no_frontend_no_panel(hass: HomeAssistant) -> None:
    """Without a frontend (tests, headless installs) setup still works."""
    with patch("homeassistant.components.panel_custom.async_register_panel") as register:
        await setup_clicker(hass)
    register.assert_not_called()


def test_built_panel_is_committed() -> None:
    """The integration serves the committed build; there is no build step at install."""
    assert (FRONTEND_DIR / f"{PANEL_ELEMENT}.js").stat().st_size > 1000
