"""Receive analysis tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_receive.py

The core promise: a stored code and the captures of its button reach the
same bits and fingerprint, because both go through ``analyze``.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core import rf_analysis as ra  # noqa: E402
from core.models import SendPolicy, frame_from_capture  # noqa: E402
from core.receive import FrameChain, analyze, analyze_code  # noqa: E402
from core.stream import plan_frame  # noqa: E402

HELD_BITS = "000001111000101100000011"
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


# --- A code and its own capture always agree --------------------------------

for name, timings in corpus.builtin_cases():
    heard = analyze(timings)
    stored = analyze_code(frame_from_capture(timings))
    print(f"{heard.fingerprint or '-':<20} {heard.how[:48]:<48} {name}")
    check(heard.fingerprint is not None, f"{name}: no fingerprint")
    check(heard.fingerprint == stored.fingerprint, f"{name}: code and capture disagree")
    check(heard.bits == stored.bits, f"{name}: code and capture decode differently")

# --- The 63 vs 64 bit fix ------------------------------------------------------

events = [analyze(t) for t in (corpus.EV1527_A, corpus.EV1527_B, corpus.EV1527_C)]
check(all(len(e.bits or "") == 64 for e in events), "EV1527: not all 64 bits")
check(len({e.fingerprint for e in events}) == 1, "EV1527: repeats have different fingerprints")
check(
    events[0].fingerprint != ra.fingerprint(corpus.EV1527_A),
    "EV1527: should differ from rf_device_manager's 63-bit fingerprint",
)

# --- One button, however it was heard ------------------------------------------

held = analyze(corpus.HELD_CAPTURE)
check(held.bits == HELD_BITS and held.encoding == "pwm", "held: wrong decode")
check((held.complete_frames, held.agreeing_frames) == (6, 6), "held: frame counts")
for name, timings in corpus.stress_cases():
    heard = analyze(timings)
    check(heard.fingerprint == held.fingerprint, f"{name}: fingerprint differs from clean press")
bit_error = analyze(corpus.stress_cases()[0][1])
check((bit_error.complete_frames, bit_error.agreeing_frames) == (6, 5), "bit error: vote counts")

# What a receiver hears from Clicker's own 8-frame send is the same button.
stream = plan_frame(frame_from_capture(corpus.HELD_CAPTURE), SendPolicy()).stream()
own = analyze(stream)
check(own.fingerprint == held.fingerprint, "own transmission: fingerprint differs")
check(own.complete_frames == 8, f"own transmission: {own.complete_frames} complete frames")

# --- Captures without a usable frame ------------------------------------------

noise = analyze(corpus.NOISE)
check(not noise.decoded and noise.unit is None, "noise: should not decode")
check(analyze([400, -1200, 400]).fingerprint is None, "too short: should have no fingerprint")
check(analyze([400, -1200, 400]).how == "too short", "too short: reason")

# A single frame cut off before its gap falls back to the frame as captured.
cut = analyze(ra.split_frames(ra.trim_partial_frames(ra.normalize(corpus.HELD_CAPTURE)))[0][:-1])
check(cut.unit is None and "dominant frame" in cut.how, "cut frame: should fall back")


# --- Frames that arrive one per reception ---------------------------------------

# The canopy remote's frames open with a header and arrive one at a time.
open_frame = analyze(corpus.CANOPY_OPEN_FRAME)
check(open_frame.bits == corpus.CANOPY_OPEN, f"canopy: decoded {open_frame.bits}")
check(not open_frame.reliable, "canopy: one frame on its own should not be reliable")
check(analyze(corpus.CANOPY_STOP_FRAME).bits == corpus.CANOPY_STOP, "canopy: Stop decode")
check(analyze(corpus.CANOPY_RELEASE_FRAME).bits == corpus.CANOPY_RELEASE, "canopy: release decode")
check(len(analyze(corpus.CANOPY_STOP_DROPPED).bits or "") == 39, "canopy: dropped pulse fixture")

chain = FrameChain()
first = chain.add("rx", open_frame, 0.0)
second = chain.add("rx", analyze(corpus.CANOPY_OPEN_FRAME), 0.06)
third = chain.add("rx", analyze(corpus.CANOPY_OPEN_FRAME), 0.12)
check(first == open_frame, "chain: the first frame should pass through unchanged")
check(second.reliable and second.agreeing_frames == 2, "chain: two frames should agree")
check(third.agreeing_frames == 3 and third.complete_frames == 3, "chain: frames should add up")
check(third.fingerprint == open_frame.fingerprint, "chain: fingerprint changed")
# Other bits, another receiver, a pause or an undecoded frame start over.
release = analyze(corpus.CANOPY_RELEASE_FRAME)
check(chain.add("rx", release, 0.2).agreeing_frames == 1, "chain: other bits")
check(chain.add("rx", release, 0.6).agreeing_frames == 1, "chain: after a pause")
check(chain.add("rx2", release, 0.65).agreeing_frames == 1, "chain: other receiver")
chain.add("rx", analyze(corpus.NOISE), 0.7)
check(chain.add("rx", release, 0.75).agreeing_frames == 1, "chain: across noise")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all receive tests passed")
