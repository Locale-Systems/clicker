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
| `custom_components/clicker/core/` | Pure-Python core with no Home Assistant imports: normalization, decoders, encoder and round-trip checks, the data model (`models.py`), the stream builder (`stream.py`), the shared receive analysis (`receive.py`), the matcher (`matcher.py`), learn-candidate grouping (`learn.py`) and the rf_device_manager importer (`importer.py`) |
| `custom_components/clicker/` | The Home Assistant integration: setup, config flow, radio discovery (`discovery.py`) and diagnostics |
| `tests/` | One suite per core module, plus the capture corpus |
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
python3 -I tools/report.py                      # built-in corpus
python3 -I tools/report.py --storage FILE       # every code in rf_device_manager's .storage/rf_device_manager
python3 -I tools/report.py --storage FILE --emit radio_frequency.TRANSMITTER
```

Python 3.14 or later, matching Home Assistant's own minimum. The core uses only the standard library; Every module except the two derived from rf_device_manager is checked with `mypy --strict`.

## Credits

The decoders, the analysis pipeline and their tests are derived from [rf_device_manager](https://github.com/Gifford47/rf_device_manager) by Gifford47 (MIT). See `custom_components/clicker/core/LICENSE-rf_device_manager`.
