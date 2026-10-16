"""Serve the panel's built JavaScript and add Clicker to the sidebar (admins only)."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL_PATH = DOMAIN
PANEL_ELEMENT = "clicker-panel"
STATIC_URL = f"/{DOMAIN}_static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
_STATIC_REGISTERED = f"{DOMAIN}_static_registered"

_LOGGER = logging.getLogger(__name__)


async def async_register_panel(hass: HomeAssistant) -> bool:
    """Add the panel; return False when Home Assistant has no frontend (tests)."""
    if "frontend" not in hass.config.components:
        return False
    # Imported here: panel_custom needs the frontend, which may not be loaded.
    from homeassistant.components import panel_custom

    # Versioned by content, so browsers fetch a rebuilt panel even when the
    # integration's version is unchanged (they cache the module by its URL).
    version = await hass.async_add_executor_job(_build_hash)
    if version is None:
        # Releases ship the build; a source checkout needs `npm run build` in panel/.
        _LOGGER.error("The Clicker panel isn't built: %s is missing", _build_path())
        return False
    if not hass.data.get(_STATIC_REGISTERED):
        # Static paths live as long as Home Assistant runs; register them once.
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        hass.data[_STATIC_REGISTERED] = True
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="Clicker",
        sidebar_icon="mdi:remote",
        module_url=f"{STATIC_URL}/{PANEL_ELEMENT}.js?v={version}",
        require_admin=True,
        config={},
    )
    return True


def _build_path() -> Path:
    return FRONTEND_DIR / f"{PANEL_ELEMENT}.js"


def _build_hash() -> str | None:
    try:
        return hashlib.sha1(_build_path().read_bytes()).hexdigest()[:12]
    except FileNotFoundError:
        return None


def async_remove_panel(hass: HomeAssistant) -> None:
    """Take the panel out of the sidebar."""
    from homeassistant.components import frontend

    frontend.async_remove_panel(hass, PANEL_URL_PATH)
