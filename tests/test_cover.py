"""Cover remote rules (awnings, shades, garage doors) - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_cover.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "clicker"))

from core.cover import CoverRemote, check_options  # noqa: E402
from core.models import ModelError  # noqa: E402

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def refused(action: object, message: str) -> None:
    """Expect ``action()`` to raise ModelError."""
    try:
        action()  # type: ignore[operator]
        failures.append(f"{message}: not refused")
    except ModelError:
        pass


# The patio awning: Open, Close and Stop buttons.
awning = CoverRemote(["open", "close", "stop"])
check([s.role for s in awning.open()] == ["open"], "open")
check([s.role for s in awning.close()] == ["close"], "close")
check([s.role for s in awning.stop()] == ["stop"], "stop")
check(awning.can_stop, "awning should stop")

# Presses set the state; Stop leaves it, wherever the cover stopped.
check(awning.pressed(True, "open") is False, "open press")
check(awning.pressed(False, "close") is True, "close press")
check(awning.pressed(False, "stop") is False and awning.pressed(None, "stop") is None, "stop press")

# Stop is optional; open and close are not.
no_stop = CoverRemote({"open": "a", "close": "b"})
check(not no_stop.can_stop, "no stop button")
refused(no_stop.stop, "stop without a stop button")
for bad in (["open"], ["close", "stop"], ["toggle"]):
    refused(lambda bad=bad: CoverRemote(bad), f"{bad}")

# Options: only a known device class.
check_options({})
check_options({"device_class": "awning"})
refused(lambda: check_options({"device_class": "boat"}), "unknown device class")
refused(lambda: check_options({"travel_s": "20"}), "unknown option")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all cover tests passed")
