"""Radio reconciliation tests - no Home Assistant required.

Run from the repository root::

    python3 -I tests/test_radios.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "clicker"))

from core.models import Radio  # noqa: E402
from core.radios import FoundRadio, reconcile  # noqa: E402

F433, F303 = 433_920_000, 303_870_000
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failed expectation."""
    if not condition:
        failures.append(message)


def wesp32(frequency: int = F433, *, receiver: bool = True) -> FoundRadio:
    """The dev Home Assistant's view of the wESP32 gateway."""
    return FoundRadio(
        node="wesp32-rf-gateway",
        title="wESP32 RF Gateway",
        frequency_hz=frequency,
        frequency_range=(frequency, frequency),
        transmitter_entity_id="radio_frequency.wesp32_rf_gateway_rf_transmitter",
        transmitter_registry_id="reg-tx-433",
        receiver="AA:BB:CC:DD:EE:FF:0:rf_receiver" if receiver else None,
    )


# --- Nothing stored: discovered radios become new ones ---------------------

result = reconcile([], [wesp32()])
check(len(result.radios) == 1, "new: radio not created")
radio = result.radios[0]
check(radio.name == "wESP32 RF Gateway 433.92 MHz" and radio.frequency_hz == F433, "new: details")
check(radio.transmitter == "reg-tx-433", "new: should store the registry id")
check(radio.receiver == "AA:BB:CC:DD:EE:FF:0:rf_receiver", "new: receiver reference")
check(result.links[radio.id].node == "wesp32-rf-gateway", "new: not linked")
check(result.notes == ["wESP32 RF Gateway 433.92 MHz: new radio"], f"new: notes {result.notes}")

# --- Same hardware again: matched, nothing new ------------------------------

again = reconcile(result.radios, [wesp32()])
check(again.radios == result.radios and again.notes == [], "rediscovery: changed something")
renamed = Radio(name="Garage", frequency_hz=F433, transmitter="reg-tx-433")
check(reconcile([renamed], [wesp32()]).notes == [], "registry id: not matched")
by_entity = Radio(
    name="Garage", frequency_hz=F433, transmitter="radio_frequency.wesp32_rf_gateway_rf_transmitter"
)
matched = reconcile([by_entity], [wesp32()])
check(matched.notes == [] and by_entity.transmitter == "reg-tx-433", "entity id: not upgraded")

# --- An import from another Home Assistant: re-linked by frequency ----------


def imported_radio() -> Radio:
    """A radio imported from production, whose transmitter id differs here."""
    return Radio(
        name="garage wesp32 (433.92 MHz)",
        frequency_hz=F433,
        transmitter="radio_frequency.garage_wesp32_rf_gateway_rf_transmitter",
    )


imported = imported_radio()
relinked = reconcile([imported], [wesp32()])
check(len(relinked.radios) == 1, "import: a duplicate radio was created")
check(imported.transmitter == "reg-tx-433", "import: transmitter not re-linked")
check(any("re-linked to wESP32 RF Gateway" in n for n in relinked.notes), "import: no note")

# Ambiguous: two radios on the band, so nothing is guessed.
two = [wesp32(), FoundRadio("attic", "Attic", F433, (F433, F433), "radio_frequency.attic", "reg-a")]
imported = imported_radio()
ambiguous = reconcile([imported], two)
check(imported.id not in ambiguous.links, "ambiguous: guessed a radio")
check(any("no matching radio found" in n for n in ambiguous.notes), "ambiguous: no note")
check(len(ambiguous.radios) == 3, "ambiguous: found radios should still be added")

# --- Offline, receiver-only, other bands, tunable ---------------------------

offline = Radio(name="Shed", frequency_hz=F303, transmitter="radio_frequency.shed")
kept = reconcile([offline], [wesp32()])
check(offline in kept.radios and offline.id not in kept.links, "offline: radio dropped or linked")
check(offline.transmitter == "radio_frequency.shed", "offline: references changed")

rx_only = reconcile(
    [], [FoundRadio("rx-node", "RX node", F433, (F433, F433), receiver="11:22:33:44:55:66:0:rx")]
)
check(rx_only.radios[0].transmitter is None, "receiver-only: invented a transmitter")

bands = reconcile([], [wesp32(F433), wesp32(F303, receiver=False)])
check(sorted(r.frequency_hz for r in bands.radios) == [F303, F433], "two bands: not both added")

tunable = FoundRadio("sx", "SX1276", 0, (300_000_000, 928_000_000), "radio_frequency.sx", "reg-sx")
skipped = reconcile([], [tunable])
check(skipped.radios == [] and "not supported yet" in skipped.notes[0], "tunable: not skipped")

if failures:
    print("FAILURES:")
    print("\n".join(failures))
    sys.exit(1)
print("OK: all radio tests passed")
