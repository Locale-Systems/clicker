# Clicker

<img src="custom_components/clicker/brand/icon.png" alt="" width="96" align="right">

Control sub-GHz RF remote devices (ceiling fans, lights, awnings, shades, outlets) from Home Assistant through an ESPHome radio, and keep Home Assistant in step when someone uses the physical remote.

- **Learn by pressing.** Open a device, press a button on its remote, test what was heard, save it.
- **Clean frames, not recordings.** Learned codes are decoded and sent as frames rebuilt from the bits and measured timings. A raw recording is replayed only when a rebuilt frame can't be shown to reproduce it.
- **The physical remote updates Home Assistant.** Presses on the real remote are heard, matched to their device and command, and move the entity's state, the logbook and your automations.
- **Real entities.** Fans with speeds, oscillation and direction, lights, switches, covers and buttons, built from whatever buttons the remote has. Toggles are only sent when the state has to change.
- **Several radios.** Each radio has a frequency, so a 433.92 MHz radio and a 303.87 MHz radio work side by side.
- **See what's on the air.** Live signals shows everything the radios hear and groups unknown transmitters (a neighbour's weather sensor, a doorbell) into sources you can ignore.

## Requirements

- Home Assistant 2026.10 or later.
- An ESPHome node with an RF transceiver (for example a CC1101) set up as a radio-frequency transmitter, and ideally a receiver, on your remote's frequency. See [Setting up an ESPHome radio](docs/esphome.md).
- Remotes that use OOK/ASK modulation with fixed codes: most fan, light, outlet and shade remotes. Rolling-code remotes (garage door openers, car keys) can't be replayed.

## Installation

### HACS

1. In HACS, open the menu (⋮) and choose **Custom repositories**.
2. Add `https://github.com/Locale-Systems/clicker` with the type **Integration**.
3. Find **Clicker** in HACS, download it, and restart Home Assistant.

### By hand

Download `clicker.zip` from the [latest release](https://github.com/Locale-Systems/clicker/releases/latest), unzip it into a `custom_components/clicker` folder in your Home Assistant configuration, and restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration** and choose **Clicker**.
2. Clicker finds the radios on your ESPHome nodes by itself. They appear on the **Radios** tab of the Clicker panel, with what each can do.
3. Open **Clicker** in the sidebar (administrators only) and add your first device.

## Using Clicker

The panel has three tabs.

- **Devices** lists your devices by area. **New device** asks for a name and a radio, then opens straight into learning: press each button on the remote two or three times, **Test** what was heard, and **Save** it as a command. A device's page lists its commands (test, rename, change kind or how many frames go on air, relearn, delete) and its entities, built from templates: fans with a power toggle or an Off button, lights and switches with a toggle or On and Off buttons, covers with Open, Close and an optional Stop, and buttons. Click an entity to open its controls. **Import** brings in devices from RF Device Manager.
- **Live signals** shows everything the radios hear, what it decoded to and which command it matched, with each radio's counts over the last 10 minutes. Transmitters that match nothing but keep being heard are grouped into **unknown sources**, with how often they transmit. **Ignore** one, optionally naming it, to hide it and anything like it; ignored sources stay ignored across restarts and can be shown again.
- **Radios** shows each radio's state, what it can do and advice. Rename a radio, or delete one no device uses.

Commands are kept separately from the entities that use them, so you can delete or rebuild an entity without losing what you learned.

## Entities

### Fans

A fan entity is built from the buttons the remote has, since fan remotes differ:

| Feature | Toggle | Explicit buttons |
| --- | --- | --- |
| Power | `power` | `off`, plus `on` and/or speeds |
| Speed | | `speed_1` … `speed_<n>` |
| Oscillation | `oscillate` | `oscillate_on`, `oscillate_off` |
| Direction | `direction` (reverse) | `direction_forward`, `direction_reverse` |

Toggles are sent only when the state has to change. On a power-toggle fan, choosing a speed while it's off sends power first; on a fan with explicit buttons, the speed buttons switch it on. Turning the fan on resumes its last speed.

### Lights and switches

Power is a `toggle` (or `power`) button, or `on` and `off` buttons. A fan remote's light button is a light on the same device. Brightness up/down buttons can't set an absolute brightness, so they become buttons.

### Covers

`open` and `close` buttons, and optionally `stop`. Pick the kind of cover (awning, blind, curtain, damper, door, garage, gate, shade, shutter or window) for the right icon and voice-assistant wording. Clicker knows a cover as open or closed, not its position: Open and Close set the state as they're sent, and Stop leaves it as it was.

### Buttons

Each chosen command becomes a button entity named after it; pressing it sends the command.

### Assumed state

RF devices don't report back, so every Clicker entity's state is assumed: set by what Clicker sends and by presses heard on the physical remote, and restored after a restart. If they disagree (a press was missed), **Clicker: Set assumed state** (`clicker.set_assumed_state`) corrects any Clicker fan, light, switch or cover without sending anything.

## Actions

| Action | What it does |
| --- | --- |
| **Clicker: Send command** (`clicker.send_command`) | Sends a device's command by name or id, for example `device: Patio Fan`, `command: Power`. `frames_on_air` overrides how many frames go out. Returns what went on air. |
| **Clicker: Set assumed state** (`clicker.set_assumed_state`) | Corrects entities' assumed state without sending anything (`is_on`, `percentage`, `oscillating`, `direction`, `is_closed`). |
| **Clicker: Import from RF Device Manager** (`clicker.import_rf_device_manager`) | Imports RF Device Manager's devices and codes (administrators only). |

Sends on one radio go out one at a time, each after the previous one's airtime plus a short gap.

## Automations: remote presses

Every press on a physical remote that matches a stored command fires a `clicker_remote_pressed` event and shows in the logbook ("Patio Fan: Power pressed on the remote"). Holding a button counts as one press. The event has `device` and `command` (names), `kind`, `device_id` (the Home Assistant device), `clicker_device_id`, `command_id`, `radio_id` and `distance` (0 for an exact match).

```yaml
triggers:
  - trigger: event
    event_type: clicker_remote_pressed
    event_data:
      device: Patio Fan
      command: Power
actions:
  - action: light.toggle
    target:
      entity_id: light.patio_string_lights
```

Every Clicker device has a Home Assistant device, so presses also appear on its device page, with or without entities.

## Identifying unknown signals

Every recent reception and every unknown source on the Live signals tab has a download button. It saves the capture as an [rtl_433](https://github.com/merbanan/rtl_433) pulse file (`.ook`): the source's last three captures as received, plus a cleaned copy when Clicker can decode the signal (Clicker's best reading of the frame, repeated so that every repeat agrees, which many rtl_433 decoders need).

```bash
rtl_433 -r capture.ook       # try rtl_433's decoders
rtl_433 -A -r capture.ook    # analyze the modulation and suggest a flex decoder
```

The file is plain text, so you can also paste it into an AI chat and ask what the signal is likely to be. Treat a decode without a checksum as a guess.

## Importing from RF Device Manager

Run **Clicker: Import from RF Device Manager**, or use **Import** on the Devices tab. Clicker reads RF Device Manager's stored devices, re-encodes each code and joins each device to the matching Clicker radio: the same transmitter, or else the only radio on that frequency. Devices whose names Clicker already has are skipped, so importing again is safe. RF Device Manager itself is left untouched.

## Troubleshooting

- **A radio is offline.** Check that its ESPHome node is on and connected to Home Assistant. Clicker picks it up again by itself when it reconnects.
- **Nothing shows in Live signals when you press a remote.** The radio needs a receiver on the remote's frequency. Check the node's ESPHome logs; if a receiver that used to work hears only garbage, rebooting the node often fixes it.
- **Presses show but don't match.** Compare the code in Live signals with the stored command, and relearn the command if the remote has changed.
- **A command does nothing.** Use **Test** on the device page while watching the device, try more frames on air, and check that the radio's transmitter works.
- **Logs.** Turn on debug logging for Clicker (`custom_components.clicker`) to see every reception as it arrives. The integration's diagnostics include the last 25 receptions.

## Development

See [docs/development.md](docs/development.md).

## Credits

The decoders, the analysis pipeline and their tests are derived from [rf_device_manager](https://github.com/Gifford47/rf_device_manager) by Gifford47 (MIT). See `custom_components/clicker/core/LICENSE-rf_device_manager`.

## License

[MIT](LICENSE)
