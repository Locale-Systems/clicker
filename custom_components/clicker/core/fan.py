"""What a fan remote sends for each request, and what its presses mean.

Fan remotes vary, so a fan is built from the roles its binding has. Each
feature comes as a toggle or as explicit buttons:

==============  ==========================  =================================
Feature         Toggle                      Explicit buttons
==============  ==========================  =================================
Power           ``power``                   ``off``, plus ``on`` and/or speeds
Speed           (none)                      ``speed_1`` ... ``speed_<n>``
Oscillation     ``oscillate``               ``oscillate_on``, ``oscillate_off``
Direction       ``direction`` (reverse)     ``direction_forward``, ``direction_reverse``
==============  ==========================  =================================

The rules, matching rf_device_manager's fans where they overlap:

- **A toggle is sent only to change the state.** Turning a toggle fan off
  while it's already off sends nothing; so does oscillating when it already
  oscillates.
- **Toggle power, then speed.** On a power-toggle fan a speed button isn't
  assumed to switch it on: from off, power is sent first, with an extra
  pause so the fan sees two presses. Turning on without a speed resumes the
  fan's own last speed.
- **Speed buttons switch an explicit-power fan on**, so on such a fan "turn
  on at speed 3" is just speed 3, and plain "turn on" is the last speed (or
  the top one), or ``on`` when there are no speeds.
- **Presses update the state the same way:** power flips on/off, ``off``
  turns off, a speed button turns on at that speed, toggles flip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .models import ModelError

POWER, ON, OFF = "power", "on", "off"
OSCILLATE, OSCILLATE_ON, OSCILLATE_OFF = "oscillate", "oscillate_on", "oscillate_off"
DIRECTION, FORWARD, REVERSE = "direction", "direction_forward", "direction_reverse"
_SPEED = re.compile(r"^speed_(\d+)$")

# Extra quiet after a power toggle before a speed button follows, on top of
# the send queue's gap, so the fan has powered up and sees a separate press.
POWER_UP_PAUSE_S = 0.25


@dataclass(frozen=True)
class FanState:
    """What Home Assistant assumes the fan is doing."""

    on: bool = False
    speed: int | None = None  # 1..n; kept while off, so "on" can resume it
    oscillating: bool = False
    reverse: bool = False


@dataclass(frozen=True)
class Step:
    """One command to send, and any extra pause before the next one."""

    role: str
    pause_after_s: float = 0.0


type Plan = tuple[list[Step], FanState]


class FanRemote:
    """A fan's buttons, by role, and the rules for using them."""

    def __init__(self, roles: set[str] | list[str] | dict[str, str]) -> None:
        roles = set(roles)
        speeds = sorted(int(m.group(1)) for r in roles if (m := _SPEED.match(r)))
        if speeds != list(range(1, len(speeds) + 1)):
            raise ModelError(f"fan speeds must be speed_1 to speed_<n>, got {speeds}")
        self.speed_count = len(speeds)
        self.power_toggle = POWER in roles
        self.has_on, self.has_off = ON in roles, OFF in roles
        if not self.power_toggle and not (self.has_off and (self.has_on or speeds)):
            raise ModelError("a fan needs a power toggle, or off plus on or speed buttons")
        self.oscillate_toggle = OSCILLATE in roles
        self.oscillate_buttons = {OSCILLATE_ON, OSCILLATE_OFF} <= roles
        self.direction_toggle = DIRECTION in roles
        self.direction_buttons = {FORWARD, REVERSE} <= roles

    @property
    def can_oscillate(self) -> bool:
        return self.oscillate_toggle or self.oscillate_buttons

    @property
    def can_reverse(self) -> bool:
        return self.direction_toggle or self.direction_buttons

    def _check_speed(self, speed: int) -> None:
        if not 1 <= speed <= self.speed_count:
            raise ModelError(f"speed must be 1-{self.speed_count}, got {speed}")

    def turn_on(self, state: FanState, speed: int | None = None) -> Plan:
        """Switch on, at ``speed`` if given (else the fan's last speed)."""
        if speed is not None:
            self._check_speed(speed)
        on = replace(state, on=True, speed=speed or state.speed)
        if self.power_toggle:
            steps = [] if state.on else [Step(POWER, POWER_UP_PAUSE_S if speed else 0.0)]
            if speed is not None:
                steps.append(Step(f"speed_{speed}"))
            return steps, on
        if speed is None and self.speed_count:
            speed = state.speed or self.speed_count
            on = replace(on, speed=speed)
        if speed is not None:
            return [Step(f"speed_{speed}")], on
        return [Step(ON)], on

    def turn_off(self, state: FanState) -> Plan:
        """Switch off (the last speed is kept for the next turn on)."""
        if self.power_toggle:
            return ([Step(POWER)] if state.on else []), replace(state, on=False)
        return [Step(OFF)], replace(state, on=False)

    def set_speed(self, state: FanState, speed: int) -> Plan:
        """Run at a speed; 0 switches off."""
        return self.turn_off(state) if speed == 0 else self.turn_on(state, speed)

    def oscillate(self, state: FanState, oscillating: bool) -> Plan:
        """Start or stop oscillating."""
        if not self.can_oscillate:
            raise ModelError("this fan can't oscillate")
        new = replace(state, oscillating=oscillating)
        if self.oscillate_buttons:
            return [Step(OSCILLATE_ON if oscillating else OSCILLATE_OFF)], new
        return ([Step(OSCILLATE)] if state.oscillating != oscillating else []), new

    def set_direction(self, state: FanState, reverse: bool) -> Plan:
        """Run forward or in reverse."""
        if not self.can_reverse:
            raise ModelError("this fan can't change direction")
        new = replace(state, reverse=reverse)
        if self.direction_buttons:
            return [Step(REVERSE if reverse else FORWARD)], new
        return ([Step(DIRECTION)] if state.reverse != reverse else []), new

    def pressed(self, state: FanState, role: str) -> FanState:
        """Return the state after the remote's button with this role was pressed."""
        if role == POWER:
            return replace(state, on=not state.on)
        if role == ON:
            return replace(state, on=True)
        if role == OFF:
            return replace(state, on=False)
        if match := _SPEED.match(role):
            return replace(state, on=True, speed=int(match.group(1)))
        if role == OSCILLATE:
            return replace(state, oscillating=not state.oscillating)
        if role in (OSCILLATE_ON, OSCILLATE_OFF):
            return replace(state, oscillating=role == OSCILLATE_ON)
        if role == DIRECTION:
            return replace(state, reverse=not state.reverse)
        if role in (FORWARD, REVERSE):
            return replace(state, reverse=role == REVERSE)
        return state
