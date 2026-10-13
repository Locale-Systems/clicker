"""Config flow for Clicker: installs the integration; everything else lives in its panel."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class ClickerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Install Clicker (one instance)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm and create the entry."""
        if user_input is not None:
            return self.async_create_entry(title="Clicker", data={})
        return self.async_show_form(step_id="user")
