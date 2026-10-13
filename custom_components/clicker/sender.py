"""The send queue: put commands on air one at a time per radio.

Home Assistant's ``radio_frequency`` send returns as soon as the request is
handed to ESPHome, so pacing is Clicker's job. Each radio sends one
transmission at a time; the next waits for the previous one's airtime plus
:data:`SETTLE_GAP_S`, so a receiver sees two quick presses as two presses.

Every send is announced to the matcher first, so Clicker's own
transmission, heard by any receiver on that frequency, isn't taken for a
remote press.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.radio_frequency import async_send_command
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util.json import JsonValueType
from rf_protocols.commands.ook import OOKCommand

from .core.models import Command, Device, EncodedFrame, Radio, SendPolicy
from .core.stream import Transmission, plan_command

if TYPE_CHECKING:
    from .runtime import ClickerRuntime

# Quiet time between two transmissions on one radio.
SETTLE_GAP_S = 0.25


@dataclass(frozen=True)
class Sent:
    """What a send put on air."""

    command: Command
    radio: Radio
    transmission: Transmission
    waited_s: float  # spent queued behind earlier sends


class SendQueue:
    """Serializes and paces transmissions per radio."""

    def __init__(
        self,
        hass: HomeAssistant,
        runtime: ClickerRuntime,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._hass = hass
        self._runtime = runtime
        self._clock = clock
        self._sleep = sleep
        self._locks: dict[str, asyncio.Lock] = {}
        self._busy_until: dict[str, float] = {}  # radio id -> clock time

    def _transmitter(self, radio: Radio) -> str:
        if radio.id not in self._runtime.links:
            raise HomeAssistantError(f"Radio {radio.name} is offline")
        if radio.transmitter is None:
            raise ServiceValidationError(f"Radio {radio.name} has no transmitter")
        return radio.transmitter

    def radio_of(self, device: Device) -> Radio:
        """Return the radio a device sends through."""
        if (radio := self._runtime.data.radio(device.radio_id)) is None:
            raise ServiceValidationError(f"{device.name} has no radio")
        return radio

    async def async_send(
        self,
        radio: Radio,
        command: Command,
        *,
        policy: SendPolicy | None = None,
        context: Context | None = None,
    ) -> Sent:
        """Send a command on a radio, after any sends already queued there.

        The command needn't be stored: learn candidates are tested this way.
        """
        transmitter = self._transmitter(radio)
        try:
            plan = plan_command(command, policy)
        except ValueError as err:
            raise ServiceValidationError(f"{command.name}: {err}") from err

        queued_at = self._clock()
        async with self._locks.setdefault(radio.id, asyncio.Lock()):
            if (wait := self._busy_until.get(radio.id, 0.0) - self._clock()) > 0:
                await self._sleep(wait)
            started = self._clock()
            self._runtime.matcher.note_transmission(radio.frequency_hz, started, plan.airtime_s)
            self._busy_until[radio.id] = started + plan.airtime_s + SETTLE_GAP_S
            await async_send_command(
                self._hass,
                transmitter,
                OOKCommand(
                    frequency=radio.frequency_hz,
                    timings=list(plan.unit),
                    repeat_count=plan.repeat_count,
                ),
                context=context,
            )
        return Sent(command, radio, plan, waited_s=started - queued_at)


def describe(sent: Sent) -> dict[str, JsonValueType]:
    """Summarize a send for a response."""
    plan = sent.transmission
    return {
        "command": sent.command.name,
        "radio": sent.radio.name,
        "encoded": isinstance(sent.command.frame, EncodedFrame),
        "frames_on_air": plan.frames_on_air,
        "sends": plan.sends,
        "airtime_ms": round(plan.airtime_s * 1000),
        "waited_ms": round(sent.waited_s * 1000),
    }
