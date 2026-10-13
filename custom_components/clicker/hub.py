"""The receive hub: listen to every linked receiver and identify the presses.

ESPHome nodes push ``InfraredRFReceiveEvent`` messages over their API
connection; Home Assistant's ESPHome integration doesn't route RF receptions
anywhere, so Clicker listens on each node's client directly. A subscription
lives as long as the connection, so it is renewed whenever the node comes
back, and the radios are re-discovered then too (entity keys can change
with new firmware). A reloaded ESPHome entry gets new runtime data, so a
newly loaded entry triggers a re-discovery as well.

Each reception is analyzed (:func:`core.receive.analyze`) and matched
(:class:`core.matcher.Matcher`). A match fires ``clicker_remote_pressed``
on the event bus and :data:`SIGNAL_REMOTE_PRESSED` for Clicker's entities.
The last receptions, matched or not, are kept for diagnostics and learning.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import (
    SIGNAL_CONFIG_ENTRY_CHANGED,
    ConfigEntry,
    ConfigEntryChange,
    ConfigEntryState,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

from .const import DOMAIN, ESPHOME_DOMAIN
from .core.matcher import Match
from .core.models import Radio
from .core.receive import Reception, analyze

if TYPE_CHECKING:
    from .runtime import ClickerRuntime

_LOGGER = logging.getLogger(__name__)

EVENT_REMOTE_PRESSED = f"{DOMAIN}_remote_pressed"
SIGNAL_REMOTE_PRESSED = f"{DOMAIN}_remote_pressed"  # dispatcher: (Match, at)
# A held button can fill the receiver's buffer; the first frames are enough.
MAX_ANALYZED_TIMINGS = 2000
RECENT_RECEPTIONS = 25

type ReceptionListener = Callable[[Heard, Reception, Radio], None]


@dataclass(frozen=True)
class Heard:
    """One reception, as diagnostics and the panel show it."""

    at: float  # wall clock
    radio_id: str
    pulses: int
    bits: str | None
    encoding: str | None
    fingerprint: str | None
    how: str
    matches: tuple[str, ...]  # "Device / Command"
    timings: tuple[int, ...]  # as received, for learning


class _NodeListener:
    """Receive subscription on one ESPHome node, renewed on every reconnect."""

    def __init__(self, hub: ReceiveHub, entry_id: str, entry_data: Any) -> None:
        self.entry_id = entry_id
        self.entry_data = entry_data
        self._hub = hub
        self._unsub_receive: CALLBACK_TYPE | None = None
        self._was_available = bool(entry_data.available)
        self._unsub_device = entry_data.async_subscribe_device_updated(self._on_device_update)
        self._subscribe()

    @property
    def subscribed(self) -> bool:
        return self._unsub_receive is not None

    @callback
    def _subscribe(self) -> None:
        if self._unsub_receive is not None or not self.entry_data.available:
            return
        try:
            self._unsub_receive = self.entry_data.client.subscribe_infrared_rf_receive(
                self._on_receive
            )
        except Exception as err:  # noqa: BLE001 - not connected after all: retry on update
            _LOGGER.debug("Could not listen to %s yet: %s", self.entry_id, err)

    @callback
    def _on_device_update(self) -> None:
        available = bool(self.entry_data.available)
        if not available:
            self._unsub_receive = None  # it went with the connection
        else:
            self._subscribe()
            if not self._was_available:
                self._hub.request_refresh()  # keys may have changed
        self._was_available = available

    @callback
    def _on_receive(self, event: Any) -> None:
        self._hub.async_handle(
            (self.entry_id, event.device_id, event.key), list(event.timings), time.monotonic()
        )

    @callback
    def async_stop(self) -> None:
        self._unsub_device()
        if self._unsub_receive is not None and self.entry_data.available:
            self._unsub_receive()
        self._unsub_receive = None


class ReceiveHub:
    """Routes receptions from every linked receiver through the matcher."""

    def __init__(
        self,
        hass: HomeAssistant,
        runtime: ClickerRuntime,
        request_refresh: Callable[[], None],
    ) -> None:
        self._hass = hass
        self._runtime = runtime
        self.request_refresh = request_refresh
        self._listeners: dict[str, _NodeListener] = {}
        self._routes: dict[tuple[str, int, int], str] = {}  # receiver handle -> radio id
        self.recent: deque[Heard] = deque(maxlen=RECENT_RECEPTIONS)
        self._reception_listeners: list[ReceptionListener] = []
        self._unsub_entries = async_dispatcher_connect(
            hass, SIGNAL_CONFIG_ENTRY_CHANGED, self._on_entry_changed
        )

    @callback
    def _on_entry_changed(self, change: ConfigEntryChange, entry: ConfigEntry) -> None:
        if entry.domain == ESPHOME_DOMAIN and entry.state is ConfigEntryState.LOADED:
            self.request_refresh()

    @callback
    def async_add_listener(self, listener: ReceptionListener) -> CALLBACK_TYPE:
        """Call ``listener`` with every reception (learn sessions, the live view)."""
        self._reception_listeners.append(listener)
        return lambda: self._reception_listeners.remove(listener)

    @property
    def listening(self) -> dict[str, bool]:
        """ESPHome entry id -> whether its receive subscription is live."""
        return {entry_id: lst.subscribed for entry_id, lst in self._listeners.items()}

    @callback
    def async_update(self) -> None:
        """Follow the current radio links: listen to new nodes, drop gone ones."""
        self._routes = {
            found.receiver_handle: radio_id
            for radio_id, found in self._runtime.links.items()
            if found.receiver_handle is not None
        }
        # Every loaded node, routed or not: a node that is still connecting
        # lists no receivers yet, and its reconnect is what triggers discovery.
        wanted: dict[str, Any] = {
            entry.entry_id: entry.runtime_data
            for entry in self._hass.config_entries.async_loaded_entries(ESPHOME_DOMAIN)
        }
        for entry_id, listener in list(self._listeners.items()):
            if wanted.get(entry_id) is not listener.entry_data:  # gone or reloaded
                listener.async_stop()
                del self._listeners[entry_id]
        for entry_id, entry_data in wanted.items():
            if entry_id not in self._listeners:
                self._listeners[entry_id] = _NodeListener(self, entry_id, entry_data)

    @callback
    def async_stop(self) -> None:
        """Stop listening everywhere."""
        self._unsub_entries()
        for listener in self._listeners.values():
            listener.async_stop()
        self._listeners.clear()

    @callback
    def async_handle(self, handle: tuple[str, int, int], timings: list[int], at: float) -> None:
        """Analyze and match one reception from the receiver at ``handle``."""
        radio_id = self._routes.get(handle)
        data = self._runtime.data
        radio = data.radio(radio_id) if radio_id is not None else None
        if radio is None:
            return  # another endpoint on the node, or not linked (yet)
        reception = analyze(timings[:MAX_ANALYZED_TIMINGS])
        names: list[str] = []
        for match in self._runtime.matcher.match(reception, radio.frequency_hz, at):
            if (name := self._fire(match, radio.id, at)) is not None:
                names.append(name)
        heard = Heard(
            at=time.time(),
            radio_id=radio.id,
            pulses=len(timings),
            bits=reception.bits,
            encoding=reception.encoding,
            fingerprint=reception.fingerprint,
            how=reception.how,
            matches=tuple(names),
            timings=tuple(timings),
        )
        self.recent.append(heard)
        for listener in list(self._reception_listeners):
            listener(heard, reception, radio)
        _LOGGER.debug(
            "%s heard %s (%d pulses): %s",
            radio.name,
            reception.fingerprint or "an undecoded code",
            len(timings),
            ", ".join(names) or "no match",
        )

    def _fire(self, match: Match, radio_id: str, at: float) -> str | None:
        device = self._runtime.data.device(match.device_id)
        command = device.command(match.command_id) if device is not None else None
        if device is None or command is None:
            return None
        self._hass.bus.async_fire(
            EVENT_REMOTE_PRESSED,
            {
                "device_id": device.id,
                "device": device.name,
                "command_id": command.id,
                "command": command.name,
                "kind": match.kind.value,
                "radio_id": radio_id,
                "distance": match.distance,
            },
        )
        async_dispatcher_send(self._hass, SIGNAL_REMOTE_PRESSED, match, at)
        return f"{device.name} / {command.name}"
