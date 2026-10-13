"""Reconcile stored radios with the radios Home Assistant currently offers.

Discovery (done by the integration) reports :class:`FoundRadio` objects: one
per transmitter/receiver pair on an ESPHome node, grouped by frequency. This
module decides which stored :class:`~.models.Radio` each one is, without
touching Home Assistant, so the rules are testable on their own:

1. **Same hardware.** A stored radio matches a found one whose receiver
   reference, or transmitter (entity id or entity-registry id), it already
   holds.
2. **Re-link by frequency.** A stored radio still unmatched (typically an
   import, whose transmitter entity id differs on this Home Assistant) takes
   the only unclaimed found radio on its frequency. Each re-link is noted.
3. **New hardware.** Found radios nobody claimed become new stored radios.

Matched radios are updated to the transmitter's entity-registry id, which
survives entity renames. Stored radios with no hardware are kept (a node
may just be offline) and noted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Radio


@dataclass(frozen=True)
class FoundRadio:
    """A radio Home Assistant can use right now."""

    node: str  # ESPHome node name
    title: str  # the node's name as shown in Home Assistant
    frequency_hz: int  # 0 when the radio is tunable (not supported yet)
    frequency_range: tuple[int, int]
    transmitter_entity_id: str | None = None
    transmitter_registry_id: str | None = None
    receiver: str | None = None  # "<mac>:<sub-device id>:<object id>"
    available: bool = True
    # Where receptions arrive this session, opaque here: the integration uses
    # (ESPHome config entry id, sub-device id, entity key).
    receiver_handle: tuple[str, int, int] | None = None

    @property
    def transmitter(self) -> str | None:
        """Return the rename-proof transmitter reference to store."""
        return self.transmitter_registry_id or self.transmitter_entity_id

    def holds(self, radio: Radio) -> bool:
        """Return whether a stored radio already refers to this hardware."""
        if radio.receiver is not None and radio.receiver == self.receiver:
            return True
        return radio.transmitter is not None and radio.transmitter in (
            self.transmitter_entity_id,
            self.transmitter_registry_id,
        )


@dataclass
class Reconciled:
    """Stored radios after reconciliation, and what changed."""

    radios: list[Radio] = field(default_factory=list)
    links: dict[str, FoundRadio] = field(default_factory=dict)  # radio id -> hardware
    notes: list[str] = field(default_factory=list)


def _mhz(frequency_hz: int) -> str:
    return f"{frequency_hz / 1e6:.2f} MHz"


def reconcile(stored: list[Radio], found: list[FoundRadio]) -> Reconciled:
    """Match stored radios to found hardware; see the module docstring for the rules."""
    result = Reconciled(radios=list(stored))
    usable = [f for f in found if f.frequency_hz > 0]
    for tunable in (f for f in found if f.frequency_hz <= 0):
        low, high = tunable.frequency_range
        result.notes.append(
            f"{tunable.title}: tunable radio ({_mhz(low)} to {_mhz(high)}) is not supported yet"
        )
    unclaimed = list(usable)

    for radio in stored:
        hardware = next((f for f in unclaimed if f.holds(radio)), None)
        if hardware is not None:
            unclaimed.remove(hardware)
            result.links[radio.id] = hardware

    for radio in stored:
        if radio.id in result.links:
            continue
        same_band = [f for f in unclaimed if f.frequency_hz == radio.frequency_hz]
        if len(same_band) == 1:
            hardware = same_band[0]
            unclaimed.remove(hardware)
            result.links[radio.id] = hardware
            result.notes.append(
                f"{radio.name}: re-linked to {hardware.title} ({_mhz(hardware.frequency_hz)})"
            )
        else:
            result.notes.append(f"{radio.name}: no matching radio found")

    for hardware in unclaimed:
        radio = Radio(
            name=f"{hardware.title} {_mhz(hardware.frequency_hz)}",
            frequency_hz=hardware.frequency_hz,
        )
        result.radios.append(radio)
        result.links[radio.id] = hardware
        result.notes.append(f"{radio.name}: new radio")

    for radio in result.radios:
        if (hardware := result.links.get(radio.id)) is not None:
            radio.transmitter = hardware.transmitter
            radio.receiver = hardware.receiver
    return result
