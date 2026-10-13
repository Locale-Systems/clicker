"""Preview importing rf_device_manager's storage file into Clicker.

Usage:
    python3 -I tools/import_rfdm.py FILE              # print what would be imported
    python3 -I tools/import_rfdm.py FILE --out OUT    # also write Clicker's data as JSON
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "clicker"))

from core.importer import import_rf_device_manager  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("storage", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()

    result = import_rf_device_manager(json.loads(args.storage.read_text()), now=time.time())
    for radio in result.data.radios:
        print(f"radio   {radio.name}  transmitter={radio.transmitter}")
    for device in result.data.devices:
        print(f"device  {device.name}: {len(device.commands)} commands")
        for binding in device.bindings:
            print(f"        {binding.platform} {binding.name!r} roles: {', '.join(binding.roles)}")
    print()
    for note in result.notes:
        print(f"- {note}")
    if problems := result.data.problems():
        print("\nPROBLEMS:")
        print("\n".join(problems))
    if args.out:
        args.out.write_text(json.dumps(result.data.to_dict(), indent=2))
        print(f"\nwrote {args.out}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
