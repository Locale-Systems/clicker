# Derived from rf_device_manager's tests/test_decoders.py
# (https://github.com/Gifford47/rf_device_manager)
# Copyright (c) 2026 Gifford47 - MIT License, see
# custom_components/clicker/core/LICENSE-rf_device_manager.
"""Standalone decoder and analysis tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_decoders.py

``decoders.py`` and ``rf_analysis.py`` are deliberately pure Python, so the
whole detection pipeline (normalizing, frame splitting, the decoder chain,
fingerprints and clustering) is testable in isolation. When you add or
change a decoder in ``decoders.py``, add a case here - ideally from a real
ESPHome ``remote_receiver`` log line like the built-in EV1527 capture
below.
"""

from __future__ import annotations

import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "clicker"))

from core import rf_analysis  # noqa: E402
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def parse(text: str) -> list[int]:
    """Parse comma separated timings as logged by ESPHome remote_receiver."""
    return [int(v.strip()) for v in text.replace("\n", " ").split(",") if v.strip()]


# ---------------------------------------------------------------------------
# 1. Real EV1527-style capture (three receiver events of one button press,
#    logged by an ESPHome remote_receiver at 433.92 MHz) + real noise event.
#    Expectation: identical bits/fingerprints, one cluster, noise separate.
# ---------------------------------------------------------------------------

EV1527_A = parse("""
324, -2791, 321, -240, 323, -1333, 328, -1327, 316, -252, 330, -249, 320,
-1335, 317, -1323, 327, -252, 321, -252, 322, -1334, 319, -1325, 319, -262,
318, -252, 319, -1340, 318, -248, 315, -1362, 310, -253, 316, -1339, 311,
-260, 312, -1338, 318, -258, 310, -1345, 309, -263, 311, -1342, 313, -258,
311, -1344, 312, -259, 311, -1341, 318, -255, 312, -1354, 298, -1341, 303,
-285, 309, -1334, 315, -268, 308, -264, 312, -1344, 308, -1337, 306, -273,
311, -1333, 311, -267, 313, -269, 299, -1344, 310, -269, 301, -1349, 310,
-260, 309, -1347, 306, -265, 307, -1361, 309, -1333, 309, -273, 306, -267,
307, -1347, 307, -265, 307, -1349, 304, -1339, 308, -271, 308, -262, 306,
-1350, 307, -267, 304, -1349, 306, -262, 309, -1346, 309, -260, 310, -1338,
307
""")

EV1527_B = parse("""
328, -2778, 329, -241, 332, -1323, 330, -1313, 333, -249, 329, -245, 325,
-1326, 328, -1316, 332, -249, 329, -246, 326, -1325, 327, -1316, 331, -254,
326, -245, 324, -1328, 326, -243, 327, -1344, 324, -247, 325, -1334, 318,
-249, 322, -1331, 323, -246, 325, -1331, 323, -249, 322, -1330, 326, -252,
316, -1330, 327, -246, 322, -1334, 322, -249, 319, -1334, 321, -1330, 318,
-268, 322, -1325, 321, -261, 319, -259, 310, -1337, 318, -1324, 320, -263,
316, -1329, 315, -274, 308, -257, 312, -1344, 310, -258, 313, -1339, 316,
-258, 311, -1350, 303, -262, 305, -1363, 308, -1334, 309, -271, 309, -264,
304, -1349, 307, -262, 306, -1352, 304, -1338, 308, -277, 299, -271, 302,
-1351, 303, -275, 292, -1359, 298, -274, 295, -1362, 293, -273, 298, -1349,
294
""")

EV1527_C = parse("""
321, -2781, 330, -244, 321, -1329, 328, -1319, 325, -255, 324, -250, 318,
-1339, 316, -1323, 322, -257, 322, -257, 314, -1339, 315, -1327, 319, -261,
317, -256, 315, -1336, 318, -257, 313, -1356, 312, -258, 309, -1343, 315,
-254, 315, -1345, 310, -259, 310, -1344, 312, -258, 313, -1338, 314, -265,
305, -1345, 313, -256, 313, -1349, 307, -263, 306, -1345, 310, -1334, 310,
-284, 308, -1334, 312, -268, 310, -268, 302, -1347, 311, -1338, 306, -280,
300, -1336, 307, -272, 308, -270, 300, -1353, 300, -270, 303, -1347, 307,
-268, 301, -1353, 303, -270, 299, -1369, 300, -1341, 303, -285, 296, -274,
296, -1352, 304, -269, 299, -1355, 301, -1347, 299, -280, 299, -274, 294,
-1362, 295, -273, 296, -1358, 297, -277, 294, -1359, 296, -274, 297, -1352,
292
""")

NOISE = parse("""
117, -3666, 493, -952, 539, -925, 385, -1063, 493, -1870, 876, -656, 604,
-129, 201, -309, 767, -396, 2941, -128, 572, -113, 793, -181
""")

ev_results = {name: rf_analysis.analyze(t) for name, t in
              (("A", EV1527_A), ("B", EV1527_B), ("C", EV1527_C))}
noise_result = rf_analysis.analyze(NOISE)

for name, result in ev_results.items():
    print(
        f"EV1527 {name}: encoding={result.get('encoding')} "
        f"bits={result.get('bit_count')} hex={result.get('hex')} "
        f"fp={result.get('fingerprint')}"
    )
    check(result.get("encoding") == "space_distance",
          f"EV1527 {name}: expected space_distance")

check(
    ev_results["A"].get("bits")
    == ev_results["B"].get("bits")
    == ev_results["C"].get("bits")
    is not None,
    "EV1527: bits differ between repeats",
)
check(
    ev_results["A"]["fingerprint"]
    == ev_results["B"]["fingerprint"]
    == ev_results["C"]["fingerprint"],
    "EV1527: fingerprints differ between repeats",
)
check(rf_analysis.same_code(ev_results["A"], ev_results["B"]),
      "EV1527: same_code(A,B) is False")
check(not rf_analysis.same_code(ev_results["A"], noise_result),
      "EV1527: noise matched the code")

# ---------------------------------------------------------------------------
# 2. Manchester coding: jittered synthetic frames must decode to identical
#    bits and fingerprints (including the trailing half swallowed by the
#    inter-frame gap).
# ---------------------------------------------------------------------------


def build_manchester(bits: str, half_us: int, jitter: float, seed: int) -> list[int]:
    """Encode bits as Manchester (mark→space = 1) with timing jitter."""
    rng = random.Random(seed)
    halves: list[bool] = []
    for bit in bits:
        halves.extend((True, False) if bit == "1" else (False, True))
    timings: list[int] = []
    for level in halves:
        duration = round(half_us * (1 + rng.uniform(-jitter, jitter)))
        signed = duration if level else -duration
        if timings and (timings[-1] > 0) == (signed > 0):
            timings[-1] += signed
        else:
            timings.append(signed)
    if timings[-1] > 0:
        timings.append(-8000)  # inter-frame gap
    else:
        timings[-1] = -8000
    return timings


MANCHESTER_BITS = "101100111000101101001101"
manchester_a = rf_analysis.analyze(build_manchester(MANCHESTER_BITS, 500, 0.08, 1))
manchester_b = rf_analysis.analyze(build_manchester(MANCHESTER_BITS, 500, 0.08, 2))
print(
    f"Manchester: encoding={manchester_a.get('encoding')} "
    f"bits={manchester_a.get('bits')} hex={manchester_a.get('hex')}"
)
check(manchester_a.get("encoding") == "manchester", "Manchester: wrong encoding")
check(manchester_a.get("bits") == MANCHESTER_BITS, "Manchester: bits mismatch")
check(
    manchester_a["fingerprint"] == manchester_b["fingerprint"],
    "Manchester: jittered fingerprints differ",
)

# ---------------------------------------------------------------------------
# 3. rc-switch PWM regression: encoding our own binary output must decode
#    back to the same bits including the protocol guess.
# ---------------------------------------------------------------------------

RC_BITS = "100110100101"
rc_result = rf_analysis.analyze(rf_analysis.encode_binary(RC_BITS, protocol=1))
print(
    f"rc-switch: encoding={rc_result.get('encoding')} bits={rc_result.get('bits')} "
    f"protocol_guess={rc_result.get('protocol_guess')}"
)
check(rc_result.get("encoding") == "pwm", "rc-switch: wrong encoding")
check(rc_result.get("bits") == RC_BITS, "rc-switch: bits mismatch")
check(rc_result.get("protocol_guess") == 1, "rc-switch: wrong protocol guess")

# ---------------------------------------------------------------------------
# 4. Tri-state round trip.
# ---------------------------------------------------------------------------

TRISTATE = "0FF0F0FF0001"
tri_result = rf_analysis.analyze(rf_analysis.encode_tristate(TRISTATE, protocol=1))
print(f"tri-state: decoded={tri_result.get('tristate')}")
check(tri_result.get("tristate") == TRISTATE, "tri-state: round trip failed")

# ---------------------------------------------------------------------------
# 5. Tasmota RfRaw B0: a real working code from a Sonoff RF Bridge must
#    decode to raw timings that analyze as the same space-distance code.
# ---------------------------------------------------------------------------

B0 = (
    "AA B0 4C 04 08 0136 0AD2 0528 29EA "
    "381808282808082828080828280808280828082808280828082808280828082828"
    "082808082828082808082808280828082828080828082808280828082808282808 55"
)
b0_timings = rf_analysis.parse_tasmota_rfraw(B0)
b0_analysis = rf_analysis.analyze(b0_timings)
print(
    f"RfRaw B0: {len(b0_timings)} pulses, encoding={b0_analysis.get('encoding')} "
    f"bits={b0_analysis.get('bit_count')} hex={b0_analysis.get('hex')}"
)
check(len(b0_timings) >= 120, "B0: too few pulses decoded")
marks = {v for v in b0_timings if v > 0}
check(len(marks) == 1, f"B0: marks not constant ({sorted(marks)})")
check(b0_analysis.get("encoding") == "space_distance", "B0: wrong encoding")
check(
    (b0_analysis.get("hex") or "").startswith("0x3332AAAB4D2AC"),
    f"B0: unexpected code {b0_analysis.get('hex')}",
)
# Compact form without spaces must parse identically.
check(
    rf_analysis.parse_tasmota_rfraw(B0.replace(" ", ""))
    == b0_timings,
    "B0: compact (no-space) form parsed differently",
)

# ---------------------------------------------------------------------------
# Edge-frame trimming on the send path: a real ESPHome + CC1101 capture of a
# held EV1527-style button (remote_receiver idle: 15ms). The first frame was
# caught while the AGC settled (2.2 ms first mark), the last one is cut off
# after 5 bits; the 6 frames in between are clean.

HELD_CAPTURE = parse("""
-125, 2227, -1212, 364, -1264, 336, -1262, 361, -1233, 359, -1254, 1159, -427, 1208, -403,
1186, -427, 1182, -425, 380, -1226, 405, -1202, 405, -1206, 1205, -402, 405, -1180, 1229,
-402, 1208, -401, 405, -1206, 377, -1205, 403, -1227, 403, -1204, 378, -1205, 403, -1204,
1229, -401, 1209, -375, 402, -12179, 409, -1191, 415, -1188, 419, -1196, 401, -1200, 427,
-1204, 1210, -375, 1233, -400, 1207, -400, 1209, -401, 405, -1201, 404, -1183, 427, -1182,
1206, -424, 403, -1205, 1205, -399, 1205, -401, 406, -1207, 403, -1202, 404, -1202, 406,
-1183, 427, -1181, 428, -1181, 1228, -400, 1207, -376, 428, -12136, 422, -1222, 369, -1248,
366, -1214, 391, -1219, 399, -1203, 1204, -399, 1207, -425, 1208, -401, 1206, -400, 404,
-1205, 404, -1206, 402, -1202, 1203, -402, 405, -1206, 1208, -401, 1206, -402, 404, -1203,
404, -1205, 403, -1203, 405, -1182, 402, -1204, 426, -1202, 1203, -402, 1206, -402, 405,
-12152, 415, -1191, 417, -1198, 399, -1201, 428, -1178, 427, -1204, 1207, -401, 1209, -375,
1232, -401, 1207, -403, 406, -1180, 427, -1184, 401, -1224, 1208, -401, 404, -1180, 1231,
-402, 1208, -401, 404, -1205, 403, -1204, 404, -1203, 403, -1182, 427, -1204, 404, -1182,
1228, -400, 1208, -402, 404, -12125, 441, -1217, 365, -1242, 368, -1221, 397, -1224, 378,
-1226, 1204, -403, 1208, -402, 1205, -402, 1205, -402, 405, -1205, 406, -1201, 404, -1200,
1208, -403, 405, -1205, 1205, -403, 1207, -402, 405, -1202, 403, -1202, 404, -1202, 405,
-1206, 403, -1204, 404, -1203, 1207, -401, 1206, -403, 380, -12181, 409, -1193, 419, -1198,
399, -1198, 428, -1179, 402, -1202, 1229, -400, 1207, -404, 1211, -400, 1205, -401, 403,
-1202, 406, -1184, 428, -1204, 1206, -401, 403, -1181, 1232, -400, 1209, -401, 405, -1180,
427, -1201, 405, -1200, 404, -1182, 427, -1182, 427, -1201, 1203, -404, 1208, -403, 405,
-12134, 440, -1222, 375, -1224, 376, -1223, 378, -1232, 377, -1228, 1180, -426, 1208, -402,
1205, -402, 1210, -401, 404, -1201, 405, -1201, 406, -1205, 1206, -401, 405, -1206, 1205,
-401, 1204, -403, 405, -1204, 405, -1207, 403, -1182, 402, -1202, 403, -1204, 402, -1203,
1232, -399, 1208, -403, 377, -12174, 419, -1198, 413, -1192, 416, -1192, 398, -1222, 403,
-15000,
""")
held = rf_analysis.normalize(HELD_CAPTURE)
held_frames = rf_analysis.split_frames(held)
trimmed = rf_analysis.trim_partial_frames(held)
trimmed_frames = rf_analysis.split_frames(trimmed)
print(
    f"held capture: {len(held_frames)} frames -> {len(trimmed_frames)} after trim"
)
check(len(held_frames) == 8, f"held: expected 8 frames, got {len(held_frames)}")
check(len(trimmed_frames) == 6, f"held: expected 6 clean frames, got {len(trimmed_frames)}")
check(trimmed == [v for f in held_frames[1:7] for v in f], "held: interior frames altered")
check(trimmed[0] > 0 and trimmed[-1] < -10000, "held: trimmed capture must start with a mark and end on a sync gap")
check(
    all(
        rf_analysis.analyze(frame).get("bits") == "000001111000101100000011"
        for frame in trimmed_frames
    ),
    "held: a kept frame does not decode to the expected code",
)
# Single-frame and already-clean captures pass through untouched.
check(rf_analysis.trim_partial_frames(trimmed) == trimmed, "held: clean capture changed")
check(rf_analysis.trim_partial_frames(EV1527_A) == EV1527_A, "EV1527_A: changed by trim")
check(rf_analysis.trim_partial_frames(NOISE) == NOISE, "noise: changed by trim")
# Learn candidate pruning: fold reception bit errors into their button and
# drop one-off undecodable noise next to a clearly real press.

REAL = "000001111000101100000011"
BIT_ERR = "000001111000101100000111"  # one corrupted bit
OTHER = "110100101010010111001010"  # a different button/remote
check(rf_analysis.bit_distance(REAL, BIT_ERR) == 1, "bit_distance: wrong value")
check(rf_analysis.bit_distance(REAL, REAL[:20]) is None, "bit_distance: length mismatch")
check(rf_analysis.bits_within_tolerance(REAL, BIT_ERR), "tolerance: 1-bit error rejected")
check(not rf_analysis.bits_within_tolerance(REAL, OTHER), "tolerance: other code accepted")


def candidates() -> list[dict]:
    return [
        {"bits": REAL, "times_seen": 1, "frame_count": 6, "frame_length": 50},
        {"bits": None, "times_seen": 1, "frame_count": 1, "frame_length": 51},  # AGC frame
        {"bits": BIT_ERR, "times_seen": 1, "frame_count": 1, "frame_length": 50},
        {"bits": None, "times_seen": 1, "frame_count": 2, "frame_length": 30},  # noise
        {"bits": OTHER, "times_seen": 1, "frame_count": 1, "frame_length": 50},
    ]


ranked = sorted(candidates(), key=rf_analysis.learn_rank, reverse=True)
check(ranked[0]["bits"] == REAL, "rank: decoded multi-frame press not first")
keep = rf_analysis.prune_learn_candidates(ranked)
kept = [ranked[i] for i in keep]
print(f"learn pruning: {len(ranked)} candidates -> {len(kept)} shown")
check([c["bits"] for c in kept] == [REAL, OTHER], f"prune: unexpected result {kept}")
check(kept[0]["times_seen"] == 2 and kept[0]["variants"] == 2, "prune: bit error not folded")

# Weak top candidate (single one-frame raw capture): nothing is dropped, so
# remotes that do not decode still show all their captures.
weak = [
    {"bits": None, "times_seen": 1, "frame_count": 1, "frame_length": 60},
    {"bits": None, "times_seen": 1, "frame_count": 1, "frame_length": 40},
]
check(rf_analysis.prune_learn_candidates(weak) == [0, 1], "prune: weak top dropped raw entries")
# A raw-only remote seen repeatedly keeps its entry and still sheds one-offs.
raw_remote = [
    {"bits": None, "times_seen": 4, "frame_count": 1, "frame_length": 60},
    {"bits": None, "times_seen": 1, "frame_count": 1, "frame_length": 40},
]
check(rf_analysis.prune_learn_candidates(raw_remote) == [0], "prune: raw remote not kept alone")

# ---------------------------------------------------------------------------


# --- Header frames ---------------------------------------------------------------
from core.decoders import decode_frame  # noqa: E402


def header_frame(bits, zero, one, header, close):
    """Header pair, one pair per bit, then ``close`` (a stop mark + gap, or a gap)."""
    out = [header[0], -header[1]]
    for bit in bits:
        mark, space = one if bit == "1" else zero
        out += [mark, -space]
    if isinstance(close, int):
        out[-1] = -close  # the last bit's space is the inter-frame gap
    else:
        out += [close[0], -close[1]]
    return out


# Dooya style: PWM bits after a header; the last bit's mark closes the frame.
for last in "01":
    bits = "000111100011000001000111011100010011001" + last
    decoded = decode_frame(header_frame(bits, (260, 610), (560, 310), (3900, 1300), 15000))
    check(decoded.get("bits") == bits, f"header PWM ending {last}: {decoded.get('bits')}")
    check(decoded.get("tail_bit") is True, "header PWM: tail bit not flagged")
# NEC style: space-distance bits after a header, then a stop mark that is no bit.
nec = "00100000110111110001000011101111"
decoded = decode_frame(header_frame(nec, (560, 560), (560, 1690), (9000, 4500), (560, 40000)))
check(decoded.get("bits") == nec, f"header space distance: {decoded.get('bits')}")
check("tail_bit" not in decoded, "header space distance: stop mark taken as a bit")

if failures:
    print("\nFAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("\nOK: all decoder tests passed")
