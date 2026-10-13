"""On/off remotes (lights, switches): what to send, and what presses mean.

Power comes as a toggle (``toggle``, or ``power``) or as ``on`` and ``off``
buttons; with both, the explicit buttons are used. As with fans, a toggle is
sent only to change the state, while explicit buttons are always sent (they
are safe to repeat, and resync a device that drifted).
"""

from __future__ import annotations

from .fan import Step
from .models import ModelError

TOGGLE, POWER, ON, OFF = "toggle", "power", "on", "off"

type OnOffPlan = tuple[list[Step], bool]


class OnOffRemote:
    """A device's power buttons, by role."""

    def __init__(self, roles: set[str] | list[str] | dict[str, str]) -> None:
        roles = set(roles)
        self.explicit = {ON, OFF} <= roles
        self.toggle = next((r for r in (TOGGLE, POWER) if r in roles), None)
        if not self.explicit and self.toggle is None:
            raise ModelError("needs a toggle, or both on and off buttons")

    def set(self, on: bool, want: bool) -> OnOffPlan:
        """Switch to ``want`` from the assumed state ``on``."""
        if self.explicit:
            return [Step(ON if want else OFF)], want
        assert self.toggle is not None
        return ([Step(self.toggle)] if on != want else []), want

    def pressed(self, on: bool, role: str) -> bool:
        """Return the state after the remote's button with this role was pressed."""
        if role in (TOGGLE, POWER):
            return not on
        if role in (ON, OFF):
            return role == ON
        return on
