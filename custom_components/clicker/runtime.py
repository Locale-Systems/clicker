"""What a loaded Clicker entry holds while Home Assistant runs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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

    store: ClickerStore
    data: ClickerData = field(default_factory=ClickerData)
    links: dict[str, FoundRadio] = field(default_factory=dict)  # radio id -> hardware
    reported: set[str] = field(default_factory=set)  # notes already logged
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # held while changing data
    hub: ReceiveHub | None = None
    sender: SendQueue | None = None
    matcher: Matcher = field(init=False)

    def __post_init__(self) -> None:
        self.matcher = Matcher(self.data)

    async def async_save(self) -> None:
        """Save the data and re-index codes; call with the lock held after a change."""
        await self.store.async_save(self.data)
        self.matcher.rebuild(self.data)

    async def async_refresh_radios(self, hass: HomeAssistant) -> None:
        """Re-discover radios, reconcile them with the stored ones, save changes."""
        found = await async_find_radios(hass)
        async with self.lock:
            before = [radio.to_dict() for radio in self.data.radios]
            result = reconcile(self.data.radios, found)
            self.data.radios = result.radios
            self.links = result.links
            if [radio.to_dict() for radio in self.data.radios] != before:
                await self.async_save()
        if self.hub is not None:
            self.hub.async_update()
        for note in result.notes:
            if note not in self.reported:
                self.reported.add(note)
                _LOGGER.info("Radio %s", note)


type ClickerConfigEntry = ConfigEntry[ClickerRuntime]
