"""What a loaded Clicker entry holds while Home Assistant runs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_DATA_UPDATED
from .core.matcher import Matcher
from .core.models import ClickerData
from .core.radios import FoundRadio, reconcile
from .discovery import async_find_radios
from .hub import ReceiveHub
from .sender import SendQueue
from .storage import ClickerStore

_LOGGER = logging.getLogger(__name__)


@dataclass
class ClickerRuntime:
    """Clicker's data, its store, the radios it is linked to and its matcher."""

    hass: HomeAssistant
    store: ClickerStore
    data: ClickerData = field(default_factory=ClickerData)
    links: dict[str, FoundRadio] = field(default_factory=dict)  # radio id -> hardware
    reported: set[str] = field(default_factory=set)  # notes already logged
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # held while changing data
    hub: ReceiveHub | None = None
    sender: SendQueue | None = None
    learn_sessions: dict[str, object] = field(default_factory=dict)  # see websocket.py
    entities: dict[str, Any] = field(default_factory=dict)  # entity id -> ClickerEntity
    matcher: Matcher = field(init=False)

    def __post_init__(self) -> None:
        self.matcher = Matcher(self.data)

    async def async_save(self) -> None:
        """Save the data, re-index codes and tell subscribers; call with the lock held."""
        await self.store.async_save(self.data)
        self.matcher.rebuild(self.data)
        async_dispatcher_send(self.hass, SIGNAL_DATA_UPDATED)

    async def async_refresh_radios(self, hass: HomeAssistant) -> None:
        """Re-discover radios, reconcile them with the stored ones, save changes."""
        found = await async_find_radios(hass)
        async with self.lock:
            before = [radio.to_dict() for radio in self.data.radios]
            linked = set(self.links)
            result = reconcile(self.data.radios, found)
            self.data.radios = result.radios
            self.links = result.links
            if [radio.to_dict() for radio in self.data.radios] != before:
                await self.async_save()
            elif set(self.links) != linked:
                async_dispatcher_send(hass, SIGNAL_DATA_UPDATED)
        if self.hub is not None:
            self.hub.async_update()
        for note in result.notes:
            if note not in self.reported:
                self.reported.add(note)
                _LOGGER.info("Radio %s", note)


type ClickerConfigEntry = ConfigEntry[ClickerRuntime]
