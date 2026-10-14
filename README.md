# Clicker

A Home Assistant integration for learning, controlling and tracking sub-GHz RF remotes (ceiling fans, lights, shades) through ESPHome radios.

**Status:** phase 2 of 5, the integration backend. The core library is done; the integration installs and discovers ESPHome radios, but can't learn or send yet.

## What's different

- **Clean frames, not recordings.** Learned codes are decoded, then sent as frames encoded from the decoded bits and measured timings. The raw capture is replayed only when an encoded frame can't be verified to reproduce it.
- **The physical remote updates Home Assistant.** Presses on the real remote are received, decoded and matched to their device, so its state in Home Assistant follows what the remote did.
- **Several radios, one integration.** Every receiver and transmitter has a frequency, so a 433.92 MHz radio and a 303.87 MHz radio run side by side without crosstalk.
- **A panel instead of forms.** Learn a button by pressing it, watch signals arrive live, and lay devices out like their physical remotes.
- **Toggle-aware.** Power, oscillate and light toggles are only sent when the state actually has to change.

## Layout

| Path | What |
| --- | --- |
| `custom_components/clicker/core/` | Pure-Python core with no Home Assistant imports: normalization, decoders, encoder and round-trip checks, the data model (`models.py`), the stream builder (`stream.py`), the shared receive analysis (`receive.py`), the matcher (`matcher.py`), learn-candidate grouping (`learn.py`), the editing rules (`edit.py`), fan and on/off remote rules (`fan.py`, `onoff.py`) and the rf_device_manager importer (`importer.py`) |
| `custom_components/clicker/` | The Home Assistant integration: setup, config flow, radio discovery (`discovery.py`), storage (`storage.py`), the receive hub (`hub.py`), the send queue (`sender.py`), actions (`services.py`), the panel's websocket API (`websocket.py`), entities (`entity.py`, `fan.py`, `light.py`, `switch.py`, `cover.py`, `button.py`) and diagnostics |
| `tests/` | One suite per core module, plus the capture corpus |
| `tests/ha/` | Home Assistant tests (pytest-homeassistant-custom-component) |
| `panel/` | The sidebar panel (Lit + TypeScript); its build is committed to `custom_components/clicker/frontend/` |
| `tools/import_rfdm.py` | Previews importing rf_device_manager's storage file, and can write the result as Clicker data |
| `tools/report.py` | Reports which captures can be sent as encoded frames, and prints ready-to-run `send_raw` actions for testing on air |

## Development

```bash
python3 -I tests/test_decoders.py
python3 -I tests/test_encoder.py
python3 -I tests/test_models.py
python3 -I tests/test_stream.py
python3 -I tests/test_receive.py
python3 -I tests/test_matcher.py
python3 -I tests/test_importer.py
python3 -I tests/test_learn.py
python3 -I tests/test_radios.py
python3 -I tests/test_edit.py
python3 -I tests/test_fan.py
python3 -I tests/test_onoff.py
python3 -I tools/report.py                      # built-in corpus
python3 -I tools/report.py --storage FILE       # every code in rf_device_manager's .storage/rf_device_manager
python3 -I tools/report.py --storage FILE --emit radio_frequency.TRANSMITTER
```

The Home Assistant tests, lint and type checks run in their own environment:

```bash
uv venv --python 3.14 .venv-ha
uv pip install --python .venv-ha -r requirements_test.txt
.venv-ha/bin/pytest
.venv-ha/bin/ruff check . && .venv-ha/bin/ruff format --check .
.venv-ha/bin/mypy
```

The panel builds with Node:

```bash
cd panel && npm install
npm run typecheck && npm test
npm run build      # writes custom_components/clicker/frontend/clicker-panel.js; commit it
```

Python 3.14 or later, matching Home Assistant's own minimum. The core uses only the standard library. Every module except the two derived from rf_device_manager is checked with `mypy --strict`.

### The panel

Clicker adds a **Clicker** entry to the sidebar for admins, with three tabs:

- **Devices**: your devices by area. Add a device (it opens straight into learning) or import from RF Device Manager. A device's page lists its commands (test, rename, change kind or frames on air, delete), learns new ones from the remote (live candidates you can test, then save or use to relearn an existing command), and builds entities from templates: fans with a power toggle or an Off button, lights and switches with a toggle or On and Off buttons, covers with Open, Close and an optional Stop (and a kind: awning, shade, garage door, ...), and buttons.
- **Live signals**: everything the radios hear, with what it decoded to and which command it matched, and each radio's counts over the last 10 minutes.
- **Radios**: each radio's state, what it can do, and advice; rename, or delete one no device uses.

### Fans

A binding with platform `fan` becomes a fan entity, built from the roles it has, since fan remotes differ:

| Feature | Toggle | Explicit buttons |
| --- | --- | --- |
| Power | `power` | `off`, plus `on` and/or speeds |
| Speed | | `speed_1` … `speed_<n>` |
| Oscillation | `oscillate` | `oscillate_on`, `oscillate_off` |
| Direction | `direction` (reverse) | `direction_forward`, `direction_reverse` |

Toggles are sent only when the state has to change. On a power-toggle fan, a speed from off sends power first; on an explicit-power fan, the speed buttons switch it on. Remote presses move the assumed state the same way, with the context of their `clicker_remote_pressed` event.

### Lights and switches

A binding with platform `light` becomes an on/off light, and one with platform `switch` a switch: power is a `toggle` (or `power`) button, or `on` and `off` buttons. As with fans, a toggle is sent only when the light has to change, explicit buttons are always sent, and remote presses move the state. A fan remote's light button is a light binding on the same device. Brightness steps can't set an absolute brightness, so they're buttons.

### Covers

A binding with platform `cover` becomes a cover: `open` and `close` buttons, and optionally `stop`. Its `device_class` option (awning, blind, curtain, damper, door, garage, gate, shade, shutter or window) sets the icon and how voice assistants refer to it. Clicker knows a cover only as open or closed, not its position: Open and Close are always sent and set the state at once, Stop leaves it as it was, and remote presses move it the same way.

### Buttons

Every command of a binding with platform `button` becomes a button entity named after the command; pressing it sends that command. Buttons have no state to follow.

If a press is missed and a device and Home Assistant disagree, **Clicker: Set assumed state** (`clicker.set_assumed_state`) corrects any Clicker fan, light, switch or cover without sending anything; each takes the fields it has.

### Sending

**Clicker: Send command** (`clicker.send_command`) sends a device's command by name or id, for example `device: Patio Fan`, `command: Power`. `frames_on_air` overrides how many frames go out for this one send. Sends on one radio go out one at a time, each waiting for the previous one's airtime plus a 250 ms gap, and receptions of Clicker's own sends aren't taken for remote presses. With a response, it returns what went on air.

### Remote presses

Clicker listens to every receiver it has linked. A press that matches a stored command fires `clicker_remote_pressed` with `device` and `command` (names), `kind`, `device_id` (the Home Assistant device), `clicker_device_id`, `command_id`, `radio_id` and `distance` (0 for an identical code), and shows in the logbook as, for example, "Patio Fan: Power pressed on the remote". Every Clicker device has a Home Assistant device, with or without entities. Holding a button counts once. Some remotes (Dooya-style motor remotes, for one) pause so long between frames that each frame arrives as its own reception; identical frames from one receiver within 250 ms are counted together, as if they had arrived at once. The last 25 receptions, matched or not, are in the diagnostics; set `custom_components.clicker` to debug logging to see each one as it arrives.

### Importing from rf_device_manager

Run the **Clicker: Import from RF Device Manager** action (`clicker.import_rf_device_manager`). It reads `.storage/rf_device_manager`, re-encodes each code and joins each device to the matching Clicker radio: the same transmitter entity, or else the only radio on that frequency. Devices whose names Clicker already has are skipped, so running it again is safe. With a response, it returns one note per decision and any problems left.

## Credits

The decoders, the analysis pipeline and their tests are derived from [rf_device_manager](https://github.com/Gifford47/rf_device_manager) by Gifford47 (MIT). See `custom_components/clicker/core/LICENSE-rf_device_manager`.
