"""Logbook entries for remote presses."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN
from .hub import EVENT_REMOTE_PRESSED


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe clicker_remote_pressed: "Patio Fan: Power pressed on the remote"."""

    @callback
    def _describe(event: Event) -> dict[str, str]:
        data = event.data
        return {
            LOGBOOK_ENTRY_NAME: str(data.get("device", "Clicker device")),
            LOGBOOK_ENTRY_MESSAGE: f"{data.get('command', 'a button')} pressed on the remote",
        }

    async_describe_event(DOMAIN, EVENT_REMOTE_PRESSED, _describe)
