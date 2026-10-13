"""Stream builder tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_stream.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core import rf_analysis as ra  # noqa: E402
from core.decoders import decode_frame  # noqa: E402
from core.encoder import encode  # noqa: E402
from core.models import (  # noqa: E402
    Command,
    CommandKind,
    EncodedFrame,
    RawFrame,
    SendPolicy,
    frame_from_capture,
)
from core.stream import DEFAULT_CLOSING_GAP_US, Transmission, plan_command, plan_frame  # noqa: E402

HELD_BITS = "000001111000101100000011"
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def alternates(timings: list[int]) -> bool:
    """Return whether marks and spaces strictly alternate."""
    return all((a > 0) != (b > 0) for a, b in zip(timings, timings[1:], strict=False))


def joinable(plan: Transmission) -> bool:
    """A unit must start with a mark, end with a gap and repeat cleanly."""
    return plan.unit[0] > 0 and plan.unit[-1] < 0 and alternates(plan.stream())


# --- Encoded code: one frame per unit ---------------------------------------

held = frame_from_capture(corpus.HELD_CAPTURE)
assert isinstance(held, EncodedFrame)
plan = plan_frame(held, SendPolicy())
print(f"encoded: {len(plan.unit)} timings x {plan.sends} sends, {plan.airtime_s:.2f} s on air")
check(list(plan.unit) == encode(held.spec), "encoded: unit is not the encoded frame")
check((plan.repeat_count, plan.frames_on_air) == (7, 8), "encoded: default is not 8 frames")
check(joinable(plan), "encoded: unit does not join cleanly")
frames = ra.split_frames(plan.stream())
check(len(frames) == 8, f"encoded: stream splits into {len(frames)} frames")
check(all(decode_frame(f).get("bits") == HELD_BITS for f in frames), "encoded: stream bits")
check(abs(plan.airtime_s - 8 * sum(abs(v) for v in plan.unit) / 1e6) < 1e-9, "encoded: airtime")
check(plan_frame(held, SendPolicy(frames_on_air=1)).repeat_count == 0, "encoded: send once")

# --- Raw capture of several frames: replayed whole ---------------------------

trimmed = ra.trim_partial_frames(ra.normalize(corpus.HELD_CAPTURE))
raw_multi = RawFrame(timings=tuple(trimmed), reason="test")
plan = plan_frame(raw_multi, SendPolicy())
print(f"raw, {raw_multi.frames_per_unit} frames: {plan.sends} sends, {plan.frames_on_air} frames")
check(raw_multi.frames_per_unit == 6, "raw: expected 6 frames in the capture")
check((plan.repeat_count, plan.frames_on_air) == (1, 12), "raw: 8 frames needs 2 replays")
check(list(plan.unit) == trimmed, "raw: an already-joinable capture was changed")
check(joinable(plan), "raw: unit does not join cleanly")
once = plan_frame(raw_multi, SendPolicy(frames_on_air=1))
check((once.repeat_count, once.frames_on_air) == (0, 6), "raw: send once replays the capture once")

# --- Raw capture ending on a mark: closed with its own frame gap -------------

ev1527 = ra.normalize(corpus.EV1527_A)  # [mark, 2.8 ms gap, data..., final mark]
check(ev1527[-1] > 0, "fixture: EV1527_A should end on a mark")
plan = plan_frame(RawFrame(timings=tuple(ev1527), reason="test"), SendPolicy())
check(plan.unit[-1] == ev1527[1], f"raw ending on a mark: closing gap {plan.unit[-1]}")
check(list(plan.unit[:-1]) == ev1527, "raw ending on a mark: other timings changed")
check(joinable(plan), "raw ending on a mark: stream does not alternate")

# --- Raw capture with no frame gap and a leading space -----------------------

plan = plan_frame(RawFrame(timings=(-500, 400, -1200, 400), reason="test"), SendPolicy())
check(plan.unit == (400, -1200, 400, -DEFAULT_CLOSING_GAP_US), f"no frame gap: unit {plan.unit}")
check(joinable(plan), "no frame gap: stream does not alternate")
try:
    plan_frame(RawFrame(timings=(-500,), reason="test"), SendPolicy())
    check(False, "a code with only a space was not refused")
except ValueError:
    pass

# --- Commands: their own policy, or a per-call override ----------------------

command = Command(
    name="Power", kind=CommandKind.TOGGLE, frame=held, policy=SendPolicy(frames_on_air=4)
)
check(plan_command(command).frames_on_air == 4, "command: its policy was ignored")
check(
    plan_command(command, SendPolicy(frames_on_air=2)).frames_on_air == 2,
    "command: override was ignored",
)

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all stream tests passed")
