"""Fans, built from bindings with platform ``fan`` (rules in :mod:`core.fan`)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from homeassistant.components.fan import (
    ATTR_DIRECTION,
    ATTR_OSCILLATING,
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .core.fan import FanRemote, FanState, Plan
from .core.models import Binding
from .entity import ClickerEntity, async_track_bindings, unsupported
from .runtime import ClickerConfigEntry

PARALLEL_UPDATES = 0  # sends are queued per radio by Clicker itself
ATTR_LAST_SPEED = "last_speed"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClickerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one fan entity per fan binding, following data changes."""
    async_track_bindings(hass, entry, "fan", ClickerFan, async_add_entities)


class ClickerFan(ClickerEntity[FanRemote], FanEntity):
    """A fan driven by its remote's buttons; its state follows remote presses."""

    _state = FanState()

    @staticmethod
    def remote_for(binding: Binding) -> FanRemote:
        return FanRemote(binding.roles)

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self.remote.speed_count:
            features |= FanEntityFeature.SET_SPEED
        if self.remote.can_oscillate:
            features |= FanEntityFeature.OSCILLATE
        if self.remote.can_reverse:
            features |= FanEntityFeature.DIRECTION
        return features

    # --- State ---------------------------------------------------------------

    @property
    def _speeds(self) -> list[int]:
        return list(range(1, self.remote.speed_count + 1))

    def _speed_for(self, percentage: int) -> int:
        return percentage_to_ordered_list_item(self._speeds, percentage)

    @property
    def is_on(self) -> bool:
        return self._state.on

    @property
    def speed_count(self) -> int:
        return max(self.remote.speed_count, 1)

    @property
    def percentage(self) -> int | None:
        if not self._state.on:
            return 0
        if not self.remote.speed_count or self._state.speed is None:
            return None
        return ordered_list_item_to_percentage(self._speeds, self._state.speed)

    @property
    def oscillating(self) -> bool | None:
        return self._state.oscillating if self.remote.can_oscillate else None

    @property
    def current_direction(self) -> str | None:
        if not self.remote.can_reverse:
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

    def pressed(self, role: str) -> bool:
        old, self._state = self._state, self.remote.pressed(self._state, role)
        return self._state != old

    # --- Requests ------------------------------------------------------------

    async def _run(self, plan: Plan) -> None:
        """Show the new state, send the plan's buttons; undo the state if sending fails."""
        steps, new = plan
        old, self._state = self._state, new
        self.async_write_ha_state()
        try:
            await self.async_send_steps(steps)
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
        speed = self._speed_for(percentage) if percentage and self.remote.speed_count else None
        await self._run(self.remote.turn_on(self._state, speed))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._run(self.remote.turn_off(self._state))

    async def async_set_percentage(self, percentage: int) -> None:
        speed = self._speed_for(percentage) if percentage else 0
        await self._run(self.remote.set_speed(self._state, speed))

    async def async_oscillate(self, oscillating: bool) -> None:
        await self._run(self.remote.oscillate(self._state, oscillating))

    async def async_set_direction(self, direction: str) -> None:
        await self._run(self.remote.set_direction(self._state, direction == DIRECTION_REVERSE))

    async def async_set_assumed_state(
        self,
        is_on: bool | None = None,
        percentage: int | None = None,
        oscillating: bool | None = None,
        direction: str | None = None,
        **other: Any,
    ) -> None:
        """Correct the assumed state without sending anything (after a missed press)."""
        unsupported(self, other)
        state = self._state
        if percentage is not None and self.remote.speed_count:
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
