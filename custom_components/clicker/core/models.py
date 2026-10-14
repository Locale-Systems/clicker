"""Clicker's data model: radios, devices, commands, frames and captures.

Pure Python (no Home Assistant). Every type round-trips through plain JSON
via ``to_dict`` / ``from_dict``, so the whole model can live in Home
Assistant's Store. Loading ignores unknown keys and fills missing optional
ones with defaults, so files written by older and newer versions both load;
a file with a newer *schema* version is refused rather than misread.

A command's code is a :data:`Frame`: an :class:`EncodedFrame` (decoded bits
plus measured symbol timings, sent as clean frames) when the capture
round-trips through the encoder, otherwise a :class:`RawFrame` (the trimmed
capture, replayed as received). The source captures are kept with the
command so codes can be re-encoded when the encoder improves.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from . import rf_analysis as ra
from .const import MIN_SIGNAL_PULSES
from .encoder import ENCODER_VERSION, CodeSpec, encode, roundtrip

SCHEMA_VERSION = 1
DEFAULT_FRAMES_ON_AIR = 8  # about a short button press
MAX_FRAMES_ON_AIR = 64
MAX_CAPTURES_PER_COMMAND = 5


class ModelError(ValueError):
    """Stored data that cannot be loaded, or a value that breaks the model."""


def new_id() -> str:
    """Return a new random object id."""
    return uuid.uuid4().hex


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    try:
        return data[key]
    except KeyError:
        raise ModelError(f"{where}: missing {key!r}") from None


# ---------------------------------------------------------------------------
# Commands and their codes
# ---------------------------------------------------------------------------


class CommandKind(StrEnum):
    """How a command is sent, and what a remote press of it means."""

    BUTTON = "button"  # always sent; a remote press only fires an event
    TOGGLE = "toggle"  # sent only when the assumed state must change; a press flips it
    STATE = "state"  # sets one state (speed 2, light on); safe to resend


@dataclass(frozen=True)
class Capture:
    """One raw reception, kept as the source of a learned code."""

    timings: tuple[int, ...]
    radio_id: str
    frequency_hz: int
    received_at: float  # Unix time

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        return {
            "timings": list(self.timings),
            "radio_id": self.radio_id,
            "frequency_hz": self.frequency_hz,
            "received_at": self.received_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Capture:
        """Load from ``to_dict`` output."""
        return cls(
            timings=tuple(int(v) for v in _require(data, "timings", "capture")),
            radio_id=str(_require(data, "radio_id", "capture")),
            frequency_hz=int(_require(data, "frequency_hz", "capture")),
            received_at=float(_require(data, "received_at", "capture")),
        )


@dataclass(frozen=True)
class EncodedFrame:
    """A code sent as frames synthesized from its decoded bits and timings."""

    spec: CodeSpec
    encoder_version: int = ENCODER_VERSION

    @property
    def bits(self) -> str:
        """Return the decoded bits."""
        return self.spec.bits

    def unit(self) -> list[int]:
        """Return one repeating unit: a single frame ending in its gap."""
        return encode(self.spec)

    @property
    def frames_per_unit(self) -> int:
        """Return how many frames one unit holds."""
        return 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        return {
            "kind": "encoded",
            "spec": self.spec.to_dict(),
            "encoder_version": self.encoder_version,
        }


@dataclass(frozen=True)
class RawFrame:
    """A code replayed from its (normalized, edge-trimmed) capture."""

    timings: tuple[int, ...]
    reason: str  # why it could not be encoded

    @property
    def bits(self) -> str | None:
        """Return the decoded bits of the dominant frame, if any."""
        bits = ra.analyze(list(self.timings)).get("bits")
        return str(bits) if bits else None

    def unit(self) -> list[int]:
        """Return one repeating unit: the whole stored capture."""
        return list(self.timings)

    @property
    def frames_per_unit(self) -> int:
        """Return how many frames one unit holds."""
        return max(1, len(ra.split_frames(list(self.timings))))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        return {"kind": "raw", "timings": list(self.timings), "reason": self.reason}


Frame = EncodedFrame | RawFrame


def frame_from_dict(data: dict[str, Any]) -> Frame:
    """Load either frame type from its ``to_dict`` output."""
    kind = _require(data, "kind", "frame")
    if kind == "encoded":
        return EncodedFrame(
            spec=CodeSpec.from_dict(_require(data, "spec", "frame")),
            encoder_version=int(data.get("encoder_version", 1)),
        )
    if kind == "raw":
        return RawFrame(
            timings=tuple(int(v) for v in _require(data, "timings", "frame")),
            reason=str(data.get("reason", "")),
        )
    raise ModelError(f"frame: unknown kind {kind!r}")


def frame_from_capture(timings: list[int]) -> Frame:
    """Build the code for a capture: encoded when it round-trips, else raw."""
    report = roundtrip("capture", timings)
    if report.status == "encoded" and report.spec is not None:
        return EncodedFrame(spec=CodeSpec.from_dict(report.spec))
    trimmed = ra.trim_partial_frames(ra.normalize(timings))
    if len(trimmed) < MIN_SIGNAL_PULSES:
        raise ModelError(
            f"capture holds {len(trimmed)} usable timings; a code needs {MIN_SIGNAL_PULSES}"
        )
    return RawFrame(timings=tuple(trimmed), reason=report.reason)


@dataclass(frozen=True)
class SendPolicy:
    """How much goes on air per send.

    ``frames_on_air`` counts frames, not repeats: an encoded code sends that
    many frames; a raw capture holding several frames is replayed until at
    least that many have gone out. ``1`` means send once.
    """

    frames_on_air: int = DEFAULT_FRAMES_ON_AIR

    def __post_init__(self) -> None:
        if not 1 <= self.frames_on_air <= MAX_FRAMES_ON_AIR:
            raise ModelError(
                f"frames_on_air must be 1-{MAX_FRAMES_ON_AIR}, got {self.frames_on_air}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        return {"frames_on_air": self.frames_on_air}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendPolicy:
        """Load from ``to_dict`` output."""
        return cls(frames_on_air=int(data.get("frames_on_air", DEFAULT_FRAMES_ON_AIR)))


@dataclass
class Command:
    """One button of a remote."""

    name: str
    kind: CommandKind
    frame: Frame
    policy: SendPolicy = field(default_factory=SendPolicy)
    captures: list[Capture] = field(default_factory=list)
    id: str = field(default_factory=new_id)

    def add_capture(self, capture: Capture) -> None:
        """Keep a source capture, dropping the oldest beyond the limit."""
        self.captures.append(capture)
        del self.captures[:-MAX_CAPTURES_PER_COMMAND]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind.value,
            "frame": self.frame.to_dict(),
            "policy": self.policy.to_dict(),
            "captures": [capture.to_dict() for capture in self.captures],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Command:
        """Load from ``to_dict`` output."""
        kind = _require(data, "kind", "command")
        try:
            command_kind = CommandKind(kind)
        except ValueError:
            raise ModelError(f"command: unknown kind {kind!r}") from None
        return cls(
            id=str(_require(data, "id", "command")),
            name=str(_require(data, "name", "command")),
            kind=command_kind,
            frame=frame_from_dict(_require(data, "frame", "command")),
            policy=SendPolicy.from_dict(data.get("policy") or {}),
            captures=[Capture.from_dict(c) for c in data.get("captures") or []],
        )


# ---------------------------------------------------------------------------
# Devices and radios
# ---------------------------------------------------------------------------


@dataclass
class Binding:
    """Ties commands to one Home Assistant entity.

    ``roles`` maps a platform role to a command id, e.g. for a fan
    ``{"power": ..., "speed_1": ..., "speed_2": ..., "oscillate": ...}``.
    Which roles a platform accepts is checked by the entity layer.
    ``options`` holds platform settings, e.g. a cover's ``device_class``.
    """

    platform: str
    name: str
    roles: dict[str, str] = field(default_factory=dict)
    id: str = field(default_factory=new_id)
    options: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        data: dict[str, Any] = {
            "id": self.id,
            "platform": self.platform,
            "name": self.name,
            "roles": dict(self.roles),
        }
        if self.options:
            data["options"] = dict(self.options)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Binding:
        """Load from ``to_dict`` output."""
        return cls(
            id=str(_require(data, "id", "binding")),
            platform=str(_require(data, "platform", "binding")),
            name=str(_require(data, "name", "binding")),
            roles={str(k): str(v) for k, v in (data.get("roles") or {}).items()},
            options={str(k): str(v) for k, v in (data.get("options") or {}).items()},
        )


@dataclass
class Device:
    """A remote-controlled device (a fan, a light) and its remote's commands."""

    name: str
    radio_id: str
    frequency_hz: int
    area_id: str | None = None
    commands: list[Command] = field(default_factory=list)
    bindings: list[Binding] = field(default_factory=list)
    id: str = field(default_factory=new_id)

    def command(self, command_id: str) -> Command | None:
        """Return the command with this id, if any."""
        return next((c for c in self.commands if c.id == command_id), None)

    def problems(self) -> list[str]:
        """Return everything inconsistent inside this device."""
        found: list[str] = []
        if self.frequency_hz <= 0:
            found.append(f"device {self.name!r}: frequency must be positive")
        names = [c.name.casefold() for c in self.commands]
        for name in sorted({n for n in names if names.count(n) > 1}):
            found.append(f"device {self.name!r}: more than one command named {name!r}")
        ids = {c.id for c in self.commands}
        for binding in self.bindings:
            for role, command_id in sorted(binding.roles.items()):
                if command_id not in ids:
                    found.append(
                        f"device {self.name!r}: binding {binding.name!r} role "
                        f"{role!r} points to a missing command"
                    )
        return found

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        return {
            "id": self.id,
            "name": self.name,
            "radio_id": self.radio_id,
            "frequency_hz": self.frequency_hz,
            "area_id": self.area_id,
            "commands": [c.to_dict() for c in self.commands],
            "bindings": [b.to_dict() for b in self.bindings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        """Load from ``to_dict`` output."""
        area_id = data.get("area_id")
        return cls(
            id=str(_require(data, "id", "device")),
            name=str(_require(data, "name", "device")),
            radio_id=str(_require(data, "radio_id", "device")),
            frequency_hz=int(_require(data, "frequency_hz", "device")),
            area_id=str(area_id) if area_id else None,
            commands=[Command.from_dict(c) for c in data.get("commands") or []],
            bindings=[Binding.from_dict(b) for b in data.get("bindings") or []],
        )


@dataclass
class Radio:
    """One physical radio (a CC1101 on an ESPHome node) on one frequency.

    The receiver and transmitter references are opaque here; the integration
    fills them from what it discovers in Home Assistant and ESPHome.
    """

    name: str
    frequency_hz: int
    transmitter: str | None = None  # radio_frequency entity id
    receiver: str | None = None  # ESPHome receiver reference
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values."""
        return {
            "id": self.id,
            "name": self.name,
            "frequency_hz": self.frequency_hz,
            "transmitter": self.transmitter,
            "receiver": self.receiver,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Radio:
        """Load from ``to_dict`` output."""
        transmitter, receiver = data.get("transmitter"), data.get("receiver")
        return cls(
            id=str(_require(data, "id", "radio")),
            name=str(_require(data, "name", "radio")),
            frequency_hz=int(_require(data, "frequency_hz", "radio")),
            transmitter=str(transmitter) if transmitter else None,
            receiver=str(receiver) if receiver else None,
        )


# ---------------------------------------------------------------------------
# The stored document
# ---------------------------------------------------------------------------


@dataclass
class ClickerData:
    """Everything Clicker stores: radios and devices."""

    radios: list[Radio] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)

    def radio(self, radio_id: str) -> Radio | None:
        """Return the radio with this id, if any."""
        return next((r for r in self.radios if r.id == radio_id), None)

    def device(self, device_id: str) -> Device | None:
        """Return the device with this id, if any."""
        return next((d for d in self.devices if d.id == device_id), None)

    def problems(self) -> list[str]:
        """Return everything inconsistent, across devices and radios."""
        found: list[str] = []
        for device in self.devices:
            found += device.problems()
            radio = self.radio(device.radio_id)
            if radio is None:
                found.append(f"device {device.name!r}: unknown radio")
            elif radio.frequency_hz != device.frequency_hz:
                found.append(
                    f"device {device.name!r}: {device.frequency_hz} Hz does not match "
                    f"radio {radio.name!r} at {radio.frequency_hz} Hz"
                )
        return found

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe values, tagged with the schema version."""
        return {
            "version": SCHEMA_VERSION,
            "radios": [r.to_dict() for r in self.radios],
            "devices": [d.to_dict() for d in self.devices],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClickerData:
        """Load stored data, refusing files from a newer schema version."""
        version = int(data.get("version", SCHEMA_VERSION))
        if version > SCHEMA_VERSION:
            raise ModelError(
                f"stored data is schema version {version}; this Clicker reads "
                f"up to {SCHEMA_VERSION}"
            )
        # Migrations from older schema versions go here, oldest first.
        return cls(
            radios=[Radio.from_dict(r) for r in data.get("radios") or []],
            devices=[Device.from_dict(d) for d in data.get("devices") or []],
        )
