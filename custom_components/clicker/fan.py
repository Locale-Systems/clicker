"""Fans, built from bindings with platform ``fan`` (rules in :mod:`core.fan`)."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

import probatio as vol
from homeassistant.components.fan import (
    ATTR_DIRECTION,
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.const import STATE_ON
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import SIGNAL_DATA_UPDATED
from .core.fan import FanRemote, FanState, Plan
from .core.matcher import Match
from .core.models import Binding, Device, ModelError
from .entity import ClickerEntity
from .hub import SIGNAL_REMOTE_PRESSED
from .runtime import ClickerConfigEntry, ClickerRuntime

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0  # sends are queued per radio by Clicker itself
SERVICE_SET_ASSUMED_STATE = "set_assumed_state"
ATTR_IS_ON = "is_on"
ATTR_LAST_SPEED = "last_speed"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClickerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one fan entity per fan binding, following data changes."""
    runtime = entry.runtime_data
    fans: dict[str, ClickerFan] = {}
    refused: set[str] = set()  # bindings already reported as unusable

    @callback
    def _sync() -> None:
        usable: dict[str, tuple[Device, Binding, FanRemote]] = {}
        for device in runtime.data.devices:
            for binding in device.bindings:
                if binding.platform != "fan":
                    continue
                try:
                    usable[binding.id] = (device, binding, FanRemote(binding.roles))
                except ModelError as err:
                    if binding.id not in refused:
                        refused.add(binding.id)
                        _LOGGER.warning(
                            "%s / %s: not a usable fan: %s", device.name, binding.name, err
                        )
        refused.intersection_update(b.id for d in runtime.data.devices for b in d.bindings)
        refused.difference_update(usable)

        ent_reg = er.async_get(hass)
        for binding_id in set(fans) - set(usable):
            gone = fans.pop(binding_id)
            if gone.registry_entry is not None:
                ent_reg.async_remove(gone.entity_id)
            else:
                hass.async_create_task(gone.async_remove(force_remove=True))
        new: list[ClickerFan] = []
        for binding_id, (device, binding, remote) in usable.items():
            if (fan := fans.get(binding_id)) is not None:
                fan.update_fan(device, binding, remote)
            else:
                fans[binding_id] = fan = ClickerFan(runtime, device, binding, remote)
                new.append(fan)
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_DATA_UPDATED, _sync))

    entity_platform.async_get_current_platform().async_register_entity_service(
        SERVICE_SET_ASSUMED_STATE,
        {
            vol.Optional(ATTR_IS_ON): cv.boolean,
            vol.Optional(ATTR_PERCENTAGE): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
            vol.Optional(ATTR_OSCILLATING): cv.boolean,
            vol.Optional(ATTR_DIRECTION): vol.In([DIRECTION_FORWARD, DIRECTION_REVERSE]),
        },
        "async_set_assumed_state",
    )


class ClickerFan(ClickerEntity, FanEntity):
    """A fan driven by its remote's buttons; its state follows remote presses."""

    def __init__(
        self, runtime: ClickerRuntime, device: Device, binding: Binding, remote: FanRemote
    ) -> None:
        super().__init__(runtime, device, binding)
        self._remote = remote
        self._state = FanState()
        self._set_features()

    def _set_features(self) -> None:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self._remote.speed_count:
            features |= FanEntityFeature.SET_SPEED
        if self._remote.can_oscillate:
            features |= FanEntityFeature.OSCILLATE
        if self._remote.can_reverse:
            features |= FanEntityFeature.DIRECTION
        self._attr_supported_features = features

    def update_fan(self, device: Device, binding: Binding, remote: FanRemote) -> None:
        """Take changed data; the assumed state is kept."""
        self.update_binding(device, binding)
        self._remote = remote
        self._set_features()
        if self.hass is not None:
            self.async_write_ha_state()

    # --- State ---------------------------------------------------------------

    @property
    def _speeds(self) -> list[int]:
        return list(range(1, self._remote.speed_count + 1))

    def _speed_for(self, percentage: int) -> int:
        return percentage_to_ordered_list_item(self._speeds, percentage)

    @property
    def is_on(self) -> bool:
        return self._state.on

    @property
    def speed_count(self) -> int:
        return max(self._remote.speed_count, 1)

    @property
    def percentage(self) -> int | None:
        if not self._state.on:
            return 0
        if not self._remote.speed_count or self._state.speed is None:
            return None
        return ordered_list_item_to_percentage(self._speeds, self._state.speed)

    @property
    def oscillating(self) -> bool | None:
        return self._state.oscillating if self._remote.can_oscillate else None

    @property
    def current_direction(self) -> str | None:
        if not self._remote.can_reverse:
            return None
        return DIRECTION_REVERSE if self._state.reverse else DIRECTION_FORWARD

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # The speed a fan comes back on at, kept while it is off.
        return {ATTR_LAST_SPEED: self._state.speed}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            speed = last.attributes.get(ATTR_LAST_SPEED)
            self._state = FanState(
                on=last.state == STATE_ON,
                speed=speed if isinstance(speed, int) and speed in self._speeds else None,
                oscillating=bool(last.attributes.get(ATTR_OSCILLATING)),
                reverse=last.attributes.get(ATTR_DIRECTION) == DIRECTION_REVERSE,
            )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_REMOTE_PRESSED, self._on_press)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_DATA_UPDATED, self.async_write_ha_state)
        )

    @callback
    def _on_press(self, match: Match, _at: float, context: Context) -> None:
        if match.device_id != self.device.id or not (roles := self.roles_of(match.command_id)):
            return
        self._state = self._remote.pressed(self._state, roles[0])
        self.async_set_context(context)
        self.async_write_ha_state()

    # --- Requests ------------------------------------------------------------

    async def _run(self, plan: Plan) -> None:
        """Show the new state, send the plan's buttons; undo the state if sending fails."""
        steps, new = plan
        old, self._state = self._state, new
        self.async_write_ha_state()
        try:
            for step in steps:
                await self.async_send_role(
                    step.role, context=self._context, pause_after_s=step.pause_after_s
                )
        except Exception:
            self._state = old
            self.async_write_ha_state()
            raise

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        speed = self._speed_for(percentage) if percentage and self._remote.speed_count else None
        await self._run(self._remote.turn_on(self._state, speed))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._run(self._remote.turn_off(self._state))

    async def async_set_percentage(self, percentage: int) -> None:
        speed = self._speed_for(percentage) if percentage else 0
        await self._run(self._remote.set_speed(self._state, speed))

    async def async_oscillate(self, oscillating: bool) -> None:
        await self._run(self._remote.oscillate(self._state, oscillating))

    async def async_set_direction(self, direction: str) -> None:
        await self._run(self._remote.set_direction(self._state, direction == DIRECTION_REVERSE))

    async def async_set_assumed_state(
        self,
        is_on: bool | None = None,
        percentage: int | None = None,
        oscillating: bool | None = None,
        direction: str | None = None,
    ) -> None:
        """Correct the assumed state without sending anything (after a missed press)."""
        state = self._state
        if percentage is not None and self._remote.speed_count:
            speed = self._speed_for(percentage) if percentage else state.speed
            state = replace(state, on=percentage > 0, speed=speed)
        if is_on is not None:
            state = replace(state, on=is_on)
        if oscillating is not None:
            state = replace(state, oscillating=oscillating)
        if direction is not None:
            state = replace(state, reverse=direction == DIRECTION_REVERSE)
        self._state = state
        self.async_write_ha_state()
