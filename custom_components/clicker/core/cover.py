"""Cover remotes (awnings, shades, garage doors): what to send, and what presses mean.

A cover needs ``open`` and ``close`` buttons; ``stop`` is optional. Clicker
knows a cover only as open or closed, not its position: Open and Close are
always sent (motors ignore a repeat, and it resyncs one that drifted) and set
the assumed state at once, while Stop leaves it as it was, since where the
cover stopped isn't known.
"""

from __future__ import annotations

from .fan import Step
from .models import ModelError

OPEN, CLOSE, STOP = "open", "close", "stop"

# Home Assistant's cover device classes, offered as the cover's type.
DEVICE_CLASSES = (
    "awning",
    "blind",
    "curtain",
    "damper",
    "door",
    "garage",
    "gate",
    "shade",
    "shutter",
    "window",
)


class CoverRemote:
    """A cover's buttons, by role."""

    def __init__(self, roles: set[str] | list[str] | dict[str, str]) -> None:
        roles = set(roles)
        if not {OPEN, CLOSE} <= roles:
            raise ModelError("needs both open and close buttons")
        self.can_stop = STOP in roles

    def open(self) -> list[Step]:
        """Open the cover."""
        return [Step(OPEN)]

    def close(self) -> list[Step]:
        """Close the cover."""
        return [Step(CLOSE)]

    def stop(self) -> list[Step]:
        """Stop the cover where it is."""
        if not self.can_stop:
            raise ModelError("has no stop button")
        return [Step(STOP)]

    def pressed(self, closed: bool | None, role: str) -> bool | None:
        """Return whether the cover is closed after the remote's ``role`` button."""
        if role == OPEN:
            return False
        if role == CLOSE:
            return True
        return closed


def check_options(options: dict[str, str]) -> None:
    """Raise ``ModelError`` unless these are valid cover options."""
    unknown = set(options) - {"device_class"}
    if unknown:
        raise ModelError(f"covers have no option {', '.join(sorted(unknown))}")
    device_class = options.get("device_class")
    if device_class is not None and device_class not in DEVICE_CLASSES:
        raise ModelError(
            f"unknown cover type {device_class!r}; use one of {', '.join(DEVICE_CLASSES)}"
        )
