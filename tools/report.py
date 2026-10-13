"""Report which captures can be sent as encoded frames.

Usage:
    python3 -I tools/report.py                       # built-in corpus
    python3 -I tools/report.py --storage FILE        # every learned command in
                                                     # rf_device_manager's
                                                     # .storage/rf_device_manager
    python3 -I tools/report.py --capture FILE ...    # timings files (ESPHome raw
                                                     # dump or comma/space separated)
    add --json for machine-readable output
    add --emit TRANSMITTER to print a Home Assistant action per encoded
    command (rf_device_manager.send_raw) for testing encoded frames on air
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "custom_components" / "clicker"), str(ROOT / "tests")]

import corpus  # noqa: E402
from core import rf_analysis as ra  # noqa: E402
from core.encoder import CodeSpec, Report, encode, roundtrip  # noqa: E402


def storage_cases(path: pathlib.Path) -> list[tuple[str, list[int]]]:
    data = json.loads(path.read_text()).get("data", {})
    devices = {d.get("id"): d.get("name") for d in (data.get("devices") or {}).values()}
    cases = []
    for code in (data.get("codes") or {}).values():
        commands = (code.get("rf_data") or {}).get("commands") or {}
        for slot, command in commands.items():
            if command.get("data"):
                label = f"{devices.get(code.get('device_id'), '?')} / {code.get('name')} / {slot}"
                cases.append((label, command["data"]))
    return cases


def capture_cases(paths: list[pathlib.Path]) -> list[tuple[str, list[int]]]:
    return [(p.name, ra.parse_timings_text(p.read_text())) for p in paths]


def _cell(value: object) -> str:
    return "-" if value is None else str(value)


def print_table(reports: list[Report]) -> None:
    width = max(len(r.name) for r in reports)
    header = "result   encoding        bits  frame  pulse%  gap%  stream  fp  detail"
    print(f"{'capture':<{width}}  {header}")
    for r in reports:
        bits = len(r.bits) if r.bits else "-"
        note = r.reason or r.unit_source
        if r.integration_bits and r.bits and r.integration_bits != r.bits:
            note += f"; integration decodes {len(r.integration_bits)} bits"
        fp = {True: "=", False: "≠", None: "-"}[r.fingerprint_same]
        frame = "ok" if r.frame_match else "-"
        print(
            f"{r.name:<{width}}  {r.status:<7}  {r.encoding or '-':<14}  {bits!s:>4}  "
            f"{frame:>5}  {_cell(r.max_pulse_dev_pct):>6}  {_cell(r.gap_dev_pct):>4}  "
            f"{r.stream_frames_ok:>3}/8  {fp:>2}  {note}"
        )
    encoded = sum(r.status == "encoded" for r in reports)
    print(f"\n{encoded}/{len(reports)} captures can be sent as encoded frames")


def print_actions(reports: list[Report], transmitter: str, frequency: int) -> None:
    """Print one send_raw action per encoded command (paste into Developer Tools)."""
    for r in reports:
        if r.status != "encoded" or r.spec is None:
            continue
        frame = encode(CodeSpec(**r.spec))
        print(f"# {r.name} - {r.encoding}, {len(r.bits or '')} bits: {r.bits}")
        print("action: rf_device_manager.send_raw")
        print("data:")
        print(f"  transmitter: {transmitter}")
        print(f"  frequency: {frequency}")
        print(f'  timings: "{", ".join(map(str, frame))}"')
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--storage", type=pathlib.Path)
    parser.add_argument("--capture", type=pathlib.Path, nargs="*", default=[])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--emit", metavar="TRANSMITTER", help="radio_frequency entity id")
    parser.add_argument("--frequency", type=int, default=433_920_000)
    args = parser.parse_args()

    cases = corpus.builtin_cases() if not (args.storage or args.capture) else []
    if args.storage:
        cases += storage_cases(args.storage)
    cases += capture_cases(args.capture)
    reports = [roundtrip(name, timings) for name, timings in cases]
    if args.emit:
        print_actions(reports, args.emit, args.frequency)
    elif args.json:
        print(json.dumps([r.__dict__ for r in reports], indent=2))
    else:
        print_table(reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
