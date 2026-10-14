"""Encoder round-trip tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_encoder.py

Every decodable capture in the corpus must be sendable as an encoded frame
that matches the capture, decodes to the same bits and survives an 8-frame
stream; noise must stay raw. Add real captures to ``corpus.py`` whenever a
remote behaves unexpectedly.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core.encoder import STREAM_FRAMES, CodeSpec, encode, roundtrip  # noqa: E402

HELD_BITS = "000001111000101100000011"
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


reports = {name: roundtrip(name, timings) for name, timings in corpus.builtin_cases()}
for report in reports.values():
    print(f"{report.status:<7} {report.encoding or '-':<14} {report.name}")

# Everything decodable encodes and passes all three checks.
for name, report in reports.items():
    if name == "real: noise burst":
        continue
    check(report.status == "encoded", f"{name}: not encoded ({report.reason})")
    check(report.frame_match, f"{name}: frame mismatch")
    check(report.redecode_ok, f"{name}: re-decode mismatch")
    check(report.stream_frames_ok == STREAM_FRAMES, f"{name}: stream decode")

# Noise has no complete frame and must stay raw.
noise = reports["real: noise burst"]
check(noise.status == "raw", "noise: was encoded")

# The held fan button and all its degraded copies keep the same code.
for name, report in reports.items():
    if "held" in name or name.startswith("stress:"):
        check(report.bits == HELD_BITS, f"{name}: wrong bits {report.bits}")
        check(report.fingerprint_same is True, f"{name}: fingerprint changed")

# Single-frame events that start with their sync gap: the leading gap is
# moved to the end and all 64 bits are recovered (rf_device_manager's
# decoder reads 63 because it mistakes the last data bit for the sync).
for name in ("real: EV1527 event A", "real: EV1527 event B", "real: EV1527 event C"):
    report = reports[name]
    check(report.unit_source.startswith("rotated"), f"{name}: not rotated")
    check(len(report.bits or "") == 64, f"{name}: expected 64 bits")
    check(len(report.integration_bits or "") == 63, f"{name}: upstream no longer 63 bits")
check(
    reports["real: EV1527 event A"].bits
    == reports["real: EV1527 event B"].bits
    == reports["real: EV1527 event C"].bits,
    "EV1527: repeats decode to different codes",
)

# Majority vote: one frame with a bit error is outvoted.
check(
    "5 agree" in reports["stress: one frame with a bit error"].unit_source,
    "bit error: vote count unexpected",
)

# Manchester round trip keeps the bit order.
check(
    reports["synthetic: Manchester x3 (8% jitter)"].bits == "101100111000101101001101",
    "Manchester: bits mismatch",
)

# The encoder refuses a symbol it never measured instead of guessing.
try:
    encode(CodeSpec(encoding="pwm", bits="01", zero=(400, 1200), one=None, sync=(400, 12000)))
    check(False, "encode: missing 1-bit timing was not refused")
except ValueError:
    pass


# --- Frames that open with a header -----------------------------------------------

for name in ("CANOPY_OPEN_FRAME", "CANOPY_RELEASE_FRAME", "CANOPY_STOP_FRAME"):
    report = roundtrip(name, getattr(corpus, name))
    check(report.status == "encoded", f"{name}: {report.status} ({report.reason})")
    spec = CodeSpec.from_dict(report.spec or {})
    check(spec.header is not None and spec.header[0] > 3000, f"{name}: header not measured")
    check(spec.tail_bit and len(spec.bits) == 40, f"{name}: last bit not in the closing mark")
    check(CodeSpec.from_dict(spec.to_dict()) == spec, f"{name}: spec does not survive storage")
    frame = encode(spec)
    check(len(frame) == len(getattr(corpus, name)), f"{name}: encoded {len(frame)} timings")
    check(frame[0] == spec.header[0] and frame[-1] == -spec.sync[1], f"{name}: frame shape")

if failures:
    print("\nFAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("\nOK: all encoder tests passed")
