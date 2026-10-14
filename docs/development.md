# Developing Clicker

## Layout

| Path | What |
| --- | --- |
| `custom_components/clicker/core/` | Pure-Python core with no Home Assistant imports: normalization and decoders (`rf_analysis.py`, `decoders.py`), the encoder and its round-trip checks (`encoder.py`), the data model (`models.py`), the stream builder (`stream.py`), the shared receive analysis (`receive.py`), the matcher (`matcher.py`), learn-candidate grouping (`learn.py`), unknown sources (`sources.py`), the rtl_433 pulse-file export (`export.py`), the editing rules (`edit.py`), fan, on/off and cover rules (`fan.py`, `onoff.py`, `cover.py`) and the rf_device_manager importer (`importer.py`) |
| `custom_components/clicker/` | The Home Assistant integration: setup, config flow, radio discovery (`discovery.py`), storage (`storage.py`), the receive hub (`hub.py`), the send queue (`sender.py`), actions (`services.py`), the panel's websocket API (`websocket.py`), the panel (`panel.py`), entities (`entity.py`, `fan.py`, `light.py`, `switch.py`, `cover.py`, `button.py`), HA devices (`devices.py`), the logbook and diagnostics |
| `custom_components/clicker/frontend/` | The panel's build (committed, so HACS installs need no build step) |
| `custom_components/clicker/brand/` | The integration's icon |
| `panel/` | The sidebar panel's source (Lit + TypeScript) |
| `tests/` | One suite per core module, plus the capture corpus (`corpus.py`, real captures) |
| `tests/ha/` | Home Assistant tests (pytest-homeassistant-custom-component) |
| `tools/import_rfdm.py` | Previews importing rf_device_manager's storage file, and can write the result as Clicker data |
| `tools/report.py` | Reports which captures can be sent as encoded frames, and prints ready-to-run actions for testing on air |

## Core tests

The core uses only the standard library, and each suite runs on its own:

```bash
for t in tests/test_*.py; do python3 -I "$t" || break; done
python3 -I tools/report.py                      # built-in corpus
python3 -I tools/report.py --storage FILE       # every code in rf_device_manager's .storage/rf_device_manager
python3 -I tools/report.py --capture FILE ...   # timings files (ESPHome raw dump, or comma/space separated)
```

When you change a decoder or the receive path, add the real capture that prompted it to `tests/corpus.py`.

## Home Assistant tests, lint and types

```bash
uv venv --python 3.14 .venv-ha
uv pip install --python .venv-ha -r requirements_test.txt
.venv-ha/bin/pytest
.venv-ha/bin/ruff check . && .venv-ha/bin/ruff format --check .
.venv-ha/bin/mypy
```

Python 3.14 or later, matching Home Assistant's own minimum. Every module except the two derived from rf_device_manager is checked with `mypy --strict`.

## Panel

```bash
cd panel && npm install
npm run typecheck && npm test
npm run build      # writes custom_components/clicker/frontend/clicker-panel.js; commit it
```

CI fails if the committed build isn't current. The panel is served as `/clicker_static/clicker-panel.js?v=<hash of the build>`, so browsers pick up a new build after Home Assistant restarts.

## Validation

GitHub Actions run the tests above, Home Assistant's `hassfest`, and the HACS checks. To run hassfest locally from a Home Assistant core checkout:

```bash
python -m script.hassfest --integration-path /path/to/clicker/custom_components/clicker
```

## Releasing

1. Update `version` in `custom_components/clicker/manifest.json`.
2. Commit, tag `v<version>`, push, and publish a GitHub release for the tag. HACS offers releases as updates.
