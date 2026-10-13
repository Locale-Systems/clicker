"""Persist Clicker's radios and devices in Home Assistant's ``.storage``.

The file is one :class:`core.models.ClickerData` document. Its schema has
its own version (handled by ``ClickerData.from_dict``), so the Home Assistant
store version stays at 1.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .core.models import ClickerData

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


class ClickerStore:
    """Loads and saves Clicker's data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Wrap the Home Assistant store for Clicker's file."""
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY, atomic_writes=True)

    async def async_load(self) -> ClickerData:
        """Return the stored data, or empty data on first run.

        Raises ``ModelError`` for a file this version can't read.
        """
        raw = await self._store.async_load()
        return ClickerData() if raw is None else ClickerData.from_dict(raw)

    async def async_save(self, data: ClickerData) -> None:
        """Write the data now."""
        await self._store.async_save(data.to_dict())

    async def async_remove(self) -> None:
        """Delete the file (the integration was removed)."""
        await self._store.async_remove()
