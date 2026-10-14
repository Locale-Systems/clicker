"""The websocket API the panel uses.

Reading (any user):

- ``clicker/data`` returns radios, devices and their commands;
  ``clicker/data/subscribe`` sends the same at once and again on every change.
- ``clicker/receptions/subscribe`` sends the recent receptions, then each new
  one as it arrives, with each radio's counts over the last 10 minutes (the
  live signal view).
- ``clicker/command/send`` sends a stored command (the Test button).

Changing (admin): ``clicker/device/{create,update,delete}``,
``clicker/command/{update,delete}``, ``clicker/radio/{update,delete}`` and
``clicker/binding/{validate,create,update,delete}`` (entities), with the
rules in :mod:`core.edit`; ``clicker/import/{status,run}`` imports
rf_device_manager's data.

Learning (admin): ``clicker/learn/subscribe`` opens a learn session for a
device and sends its ranked candidates every time a capture changes them;
``clicker/learn/test`` sends a candidate, and ``clicker/learn/save`` stores
one as a new command or as the new code of an existing command. A session
lives as long as its subscription.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_DATA_UPDATED
from .core import edit
from .core.learn import Candidate, LearnSession
from .core.models import (
    Capture,
    Command,
    CommandKind,
    Device,
    EncodedFrame,
    Frame,
    ModelError,
    Radio,
    SendPolicy,
    new_id,
)
from .core.receive import Reception
from .hub import STATS_WINDOW_S, Heard
from .runtime import ClickerConfigEntry, ClickerRuntime
from .sender import describe
from .services import async_import_rf_device_manager, rf_device_manager_path

type Connection = websocket_api.ActiveConnection
type Message = dict[str, Any]
type Handler = Callable[[HomeAssistant, Connection, Message], Awaitable[None]]

FRAMES_ON_AIR = vol.All(vol.Coerce(int), vol.Range(min=1, max=64))
KIND = vol.In([kind.value for kind in CommandKind])


def _runtime(hass: HomeAssistant) -> ClickerRuntime:
    entries: list[ClickerConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("Clicker is not loaded")
    return entries[0].runtime_data


def _errors(handler: Handler) -> Handler:
    """Report model errors as websocket errors instead of crashes."""

    @wraps(handler)
    async def wrapper(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
        try:
            await handler(hass, connection, msg)
        except edit.NotFoundError as err:
            connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, str(err))
        except ModelError as err:
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))

    return wrapper


# --- What the panel sees ------------------------------------------------------


def _frame(frame: Frame) -> dict[str, Any]:
    if isinstance(frame, EncodedFrame):
        return {"encoded": True, "encoding": frame.spec.encoding, "bits": frame.bits}
    return {"encoded": False, "reason": frame.reason, "bits": frame.bits}


def _command(command: Command) -> dict[str, Any]:
    return {
        "id": command.id,
        "name": command.name,
        "kind": command.kind.value,
        "frames_on_air": command.policy.frames_on_air,
        "captures": len(command.captures),
        **_frame(command.frame),
    }


def _device(runtime: ClickerRuntime, device: Device) -> dict[str, Any]:
    ha_device = dr.async_get(runtime.hass).async_get_device_by_identifier(
        (DOMAIN, device.id), runtime.entry_id
    )
    entities: dict[str, list[str]] = {}  # binding id -> its entity ids
    for entry in er.async_entries_for_config_entry(er.async_get(runtime.hass), runtime.entry_id):
        entities.setdefault(entry.unique_id.split(":", 1)[0], []).append(entry.entity_id)
    return {
        "id": device.id,
        "name": device.name,
        "radio_id": device.radio_id,
        "frequency_hz": device.frequency_hz,
        "area_id": device.area_id,
        "ha_device_id": ha_device.id if ha_device is not None else None,
        "commands": [_command(c) for c in device.commands],
        "bindings": [
            {
                "id": b.id,
                "platform": b.platform,
                "name": b.name,
                "roles": b.roles,
                "entity_ids": sorted(entities.get(b.id, [])),
            }
            for b in device.bindings
        ],
    }


def _radio(runtime: ClickerRuntime, radio: Radio) -> dict[str, Any]:
    found = runtime.links.get(radio.id)
    return {
        "id": radio.id,
        "name": radio.name,
        "frequency_hz": radio.frequency_hz,
        "online": found is not None,
        "node": found.title if found is not None else None,
        "can_send": radio.transmitter is not None,
        "can_receive": radio.receiver is not None,
    }


def _data(runtime: ClickerRuntime) -> dict[str, Any]:
    data = runtime.data
    return {
        "radios": [_radio(runtime, r) for r in data.radios],
        "devices": [_device(runtime, d) for d in data.devices],
        "problems": data.problems(),
    }


def _heard(heard: Heard) -> dict[str, Any]:
    return {
        "at": heard.at,
        "radio_id": heard.radio_id,
        "pulses": heard.pulses,
        "bits": heard.bits,
        "encoding": heard.encoding,
        "fingerprint": heard.fingerprint,
        "how": heard.how,
        "matches": list(heard.matches),
    }


@websocket_api.websocket_command({vol.Required("type"): "clicker/data"})
@websocket_api.async_response
async def ws_data(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Return everything the panel shows."""
    connection.send_result(msg["id"], _data(_runtime(hass)))


@websocket_api.websocket_command({vol.Required("type"): "clicker/data/subscribe"})
@websocket_api.async_response
async def ws_subscribe_data(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Send the data now and after every change."""
    runtime = _runtime(hass)

    @callback
    def _changed() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], _data(runtime)))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_DATA_UPDATED, _changed
    )
    connection.send_result(msg["id"])
    _changed()


@websocket_api.websocket_command({vol.Required("type"): "clicker/receptions/subscribe"})
@websocket_api.async_response
async def ws_subscribe_receptions(
    hass: HomeAssistant, connection: Connection, msg: Message
) -> None:
    """Send the recent receptions, then each new one, with per-radio counts."""
    hub = _runtime(hass).hub
    assert hub is not None

    def _event(heard: list[dict[str, Any]]) -> dict[str, Any]:
        return websocket_api.event_message(
            msg["id"], {"heard": heard, "stats": hub.stats(), "window_s": STATS_WINDOW_S}
        )

    @callback
    def _heard_one(heard: Heard, _reception: Reception, _radio: Radio) -> None:
        connection.send_message(_event([_heard(heard)]))

    connection.subscriptions[msg["id"]] = hub.async_add_listener(_heard_one)
    connection.send_result(msg["id"])
    connection.send_message(_event([_heard(heard) for heard in hub.recent]))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/command/send",
        vol.Required("device_id"): str,
        vol.Required("command_id"): str,
        vol.Optional("frames_on_air"): FRAMES_ON_AIR,
    }
)
@websocket_api.async_response
@_errors
async def ws_send(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Send a stored command."""
    runtime = _runtime(hass)
    assert runtime.sender is not None
    device = edit.get_device(runtime.data, msg["device_id"])
    command = edit.get_command(device, msg["command_id"])
    policy = SendPolicy(msg["frames_on_air"]) if "frames_on_air" in msg else None
    sent = await runtime.sender.async_send(
        runtime.sender.radio_of(device), command, policy=policy, context=connection.context(msg)
    )
    connection.send_result(msg["id"], describe(sent))


# --- Changes --------------------------------------------------------------------


async def _change[T](runtime: ClickerRuntime, change: Callable[[], T]) -> T:
    """Apply a change under the lock, then save (and notify)."""
    async with runtime.lock:
        result = change()
        await runtime.async_save()
    return result


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/device/create",
        vol.Required("name"): str,
        vol.Required("radio_id"): str,
        vol.Optional("area_id"): vol.Any(str, None),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_device_create(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Add a device on a radio."""
    runtime = _runtime(hass)
    device = await _change(
        runtime,
        lambda: edit.add_device(
            runtime.data, msg["name"], msg["radio_id"], area_id=msg.get("area_id")
        ),
    )
    connection.send_result(msg["id"], _device(runtime, device))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/device/update",
        vol.Required("device_id"): str,
        vol.Optional("name"): str,
        vol.Optional("area_id"): vol.Any(str, None),
        vol.Optional("radio_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_device_update(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Rename a device, set or clear (null) its area, or move it to another radio."""
    runtime = _runtime(hass)
    device = await _change(
        runtime,
        lambda: edit.update_device(
            runtime.data,
            msg["device_id"],
            name=msg.get("name"),
            area_id=msg.get("area_id"),
            clear_area="area_id" in msg and msg["area_id"] is None,
            radio_id=msg.get("radio_id"),
        ),
    )
    connection.send_result(msg["id"], _device(runtime, device))


@websocket_api.websocket_command(
    {vol.Required("type"): "clicker/device/delete", vol.Required("device_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_device_delete(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Remove a device."""
    runtime = _runtime(hass)
    await _change(runtime, lambda: edit.delete_device(runtime.data, msg["device_id"]))
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/command/update",
        vol.Required("device_id"): str,
        vol.Required("command_id"): str,
        vol.Optional("name"): str,
        vol.Optional("kind"): KIND,
        vol.Optional("frames_on_air"): FRAMES_ON_AIR,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_command_update(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Rename a command, change its kind or its frames on air."""
    runtime = _runtime(hass)
    command = await _change(
        runtime,
        lambda: edit.update_command(
            runtime.data,
            msg["device_id"],
            msg["command_id"],
            name=msg.get("name"),
            kind=CommandKind(msg["kind"]) if "kind" in msg else None,
            frames_on_air=msg.get("frames_on_air"),
        ),
    )
    connection.send_result(msg["id"], _command(command))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/command/delete",
        vol.Required("device_id"): str,
        vol.Required("command_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_command_delete(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Remove a command (and the binding roles that used it)."""
    runtime = _runtime(hass)
    await _change(
        runtime, lambda: edit.delete_command(runtime.data, msg["device_id"], msg["command_id"])
    )
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/radio/update",
        vol.Required("radio_id"): str,
        vol.Required("name"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_radio_update(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Rename a radio."""
    runtime = _runtime(hass)
    radio = await _change(
        runtime, lambda: edit.rename_radio(runtime.data, msg["radio_id"], msg["name"])
    )
    connection.send_result(msg["id"], _radio(runtime, radio))


@websocket_api.websocket_command(
    {vol.Required("type"): "clicker/radio/delete", vol.Required("radio_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_radio_delete(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Remove a radio no device uses."""
    runtime = _runtime(hass)
    await _change(runtime, lambda: edit.delete_radio(runtime.data, msg["radio_id"]))
    connection.send_result(msg["id"])


ROLES = vol.Schema({str: str})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/binding/validate",
        vol.Required("device_id"): str,
        vol.Required("platform"): str,
        vol.Required("roles"): ROLES,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_binding_validate(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Say whether these roles would make a working entity, and if not, why."""
    device = edit.get_device(_runtime(hass).data, msg["device_id"])
    try:
        edit.check_binding(device, msg["platform"], msg["roles"])
    except ModelError as err:
        connection.send_result(msg["id"], {"ok": False, "error": str(err)})
        return
    connection.send_result(msg["id"], {"ok": True, "error": None})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/binding/create",
        vol.Required("device_id"): str,
        vol.Required("platform"): str,
        vol.Required("name"): str,
        vol.Required("roles"): ROLES,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_binding_create(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Add an entity built from some of a device's commands."""
    runtime = _runtime(hass)
    binding = await _change(
        runtime,
        lambda: edit.add_binding(
            runtime.data, msg["device_id"], msg["platform"], msg["name"], msg["roles"]
        ),
    )
    connection.send_result(msg["id"], {"id": binding.id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/binding/update",
        vol.Required("device_id"): str,
        vol.Required("binding_id"): str,
        vol.Optional("name"): str,
        vol.Optional("roles"): ROLES,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_binding_update(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Rename an entity or change which commands drive it."""
    runtime = _runtime(hass)
    binding = await _change(
        runtime,
        lambda: edit.update_binding(
            runtime.data,
            msg["device_id"],
            msg["binding_id"],
            name=msg.get("name"),
            roles=msg.get("roles"),
        ),
    )
    connection.send_result(msg["id"], {"id": binding.id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/binding/delete",
        vol.Required("device_id"): str,
        vol.Required("binding_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_binding_delete(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Remove an entity; its commands stay."""
    runtime = _runtime(hass)
    await _change(
        runtime, lambda: edit.delete_binding(runtime.data, msg["device_id"], msg["binding_id"])
    )
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): "clicker/import/status"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_import_status(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Say whether rf_device_manager data exists to import."""
    path = rf_device_manager_path(hass)
    available = await hass.async_add_executor_job(path.is_file)
    connection.send_result(msg["id"], {"available": available})


@websocket_api.websocket_command({vol.Required("type"): "clicker/import/run"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_import_run(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Import rf_device_manager's devices (skipping names Clicker has); return the notes."""
    entries: list[ClickerConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("Clicker is not loaded")
    connection.send_result(msg["id"], await async_import_rf_device_manager(hass, entries[0]))


# --- Learning -------------------------------------------------------------------


@dataclass
class _Learning:
    """A learn session and what it needs to test and save candidates."""

    session: LearnSession
    device_id: str
    radio: Radio
    codes: dict[str, tuple[tuple[int, ...], Frame | None]] = field(default_factory=dict)

    def code(self, candidate: Candidate) -> Frame | None:
        """Return the candidate's code (None if unusable), built once per capture."""
        key = candidate.fingerprint or ""
        cached = self.codes.get(key)
        if cached is None or cached[0] != candidate.capture:
            try:
                frame: Frame | None = candidate.code()
            except ModelError:
                frame = None
            cached = self.codes[key] = (candidate.capture, frame)
        return cached[1]

    def candidate(self, runtime: ClickerRuntime, fingerprint: str) -> Candidate:
        for candidate in self.session.candidates(runtime.matcher):
            if candidate.fingerprint == fingerprint:
                return candidate
        raise edit.NotFoundError(f"no candidate {fingerprint!r} in this session")


def _learning(runtime: ClickerRuntime, session_id: str) -> _Learning:
    learning = runtime.learn_sessions.get(session_id)
    if not isinstance(learning, _Learning):
        raise edit.NotFoundError(f"no learn session {session_id!r}")
    return learning


def _candidate(runtime: ClickerRuntime, learning: _Learning, c: Candidate) -> dict[str, Any]:
    code = learning.code(c)
    known = []
    for match in c.known_as:
        device = runtime.data.device(match.device_id)
        command = device.command(match.command_id) if device is not None else None
        if device is not None and command is not None:
            known.append(
                {"device": device.name, "command": command.name, "distance": match.distance}
            )
    return {
        "fingerprint": c.fingerprint,
        "bits": c.bits,
        "encoding": c.reception.encoding,
        "how": c.reception.how,
        "sightings": c.sightings,
        "variants": c.variants,
        "first_at": c.first_at,
        "last_at": c.last_at,
        "usable": code is not None,
        "encoded": isinstance(code, EncodedFrame),
        "known_as": known,
    }


@websocket_api.websocket_command(
    {vol.Required("type"): "clicker/learn/subscribe", vol.Required("device_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_learn_subscribe(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Open a learn session for a device; send candidates as they change."""
    runtime = _runtime(hass)
    assert runtime.hub is not None and runtime.sender is not None
    device = edit.get_device(runtime.data, msg["device_id"])
    radio = runtime.sender.radio_of(device)
    session_id = new_id()
    learning = _Learning(LearnSession(device.frequency_hz), device.id, radio)
    runtime.learn_sessions[session_id] = learning

    @callback
    def _send() -> None:
        candidates = learning.session.candidates(runtime.matcher)
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {
                    "session_id": session_id,
                    "frequency_hz": learning.session.frequency_hz,
                    "candidates": [_candidate(runtime, learning, c) for c in candidates],
                },
            )
        )

    @callback
    def _heard(heard: Heard, reception: Reception, heard_on: Radio) -> None:
        if learning.session.add(
            list(heard.timings), heard_on.frequency_hz, heard.at, reception=reception
        ):
            _send()

    unsub = runtime.hub.async_add_listener(_heard)

    @callback
    def _close() -> None:
        unsub()
        runtime.learn_sessions.pop(session_id, None)

    connection.subscriptions[msg["id"]] = _close
    connection.send_result(msg["id"])
    _send()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/learn/test",
        vol.Required("session_id"): str,
        vol.Required("fingerprint"): str,
        vol.Optional("frames_on_air"): FRAMES_ON_AIR,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_learn_test(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Send a candidate through the session's radio, before saving it."""
    runtime = _runtime(hass)
    assert runtime.sender is not None
    learning = _learning(runtime, msg["session_id"])
    frame = learning.code(learning.candidate(runtime, msg["fingerprint"]))
    if frame is None:
        raise ModelError("this candidate has too few timings to send")
    trial = Command(name="Test", kind=CommandKind.BUTTON, frame=frame)
    policy = SendPolicy(msg["frames_on_air"]) if "frames_on_air" in msg else None
    sent = await runtime.sender.async_send(
        learning.radio, trial, policy=policy, context=connection.context(msg)
    )
    connection.send_result(msg["id"], describe(sent))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "clicker/learn/save",
        vol.Required("session_id"): str,
        vol.Required("fingerprint"): str,
        vol.Exclusive("command_id", "target"): str,
        vol.Exclusive("name", "target"): str,
        vol.Optional("kind"): KIND,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_errors
async def ws_learn_save(hass: HomeAssistant, connection: Connection, msg: Message) -> None:
    """Store a candidate as a new command (``name``) or the code of ``command_id``."""
    runtime = _runtime(hass)
    learning = _learning(runtime, msg["session_id"])
    candidate = learning.candidate(runtime, msg["fingerprint"])
    frame = learning.code(candidate)
    if frame is None:
        raise ModelError("this candidate has too few timings to store")
    capture = Capture(
        candidate.capture, learning.radio.id, learning.session.frequency_hz, time.time()
    )
    kind = CommandKind(msg["kind"]) if "kind" in msg else None

    def _save() -> Command:
        device = edit.get_device(runtime.data, learning.device_id)
        if "command_id" in msg:
            command = edit.get_command(device, msg["command_id"])
            command.frame = frame
            command.kind = kind or command.kind
        elif "name" in msg:
            command = edit.add_command(
                device, Command(name=msg["name"], kind=kind or CommandKind.BUTTON, frame=frame)
            )
        else:
            raise ModelError("give a name for a new command, or the command_id to relearn")
        command.add_capture(capture)
        return command

    command = await _change(runtime, _save)
    connection.send_result(msg["id"], _command(command))


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the panel's websocket commands."""
    for handler in (
        ws_data,
        ws_subscribe_data,
        ws_subscribe_receptions,
        ws_send,
        ws_device_create,
        ws_device_update,
        ws_device_delete,
        ws_command_update,
        ws_command_delete,
        ws_radio_update,
        ws_radio_delete,
        ws_binding_validate,
        ws_binding_create,
        ws_binding_update,
        ws_binding_delete,
        ws_import_status,
        ws_import_run,
        ws_learn_subscribe,
        ws_learn_test,
        ws_learn_save,
    ):
        websocket_api.async_register_command(hass, handler)
