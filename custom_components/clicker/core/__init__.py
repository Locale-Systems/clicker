"""Clicker core: pure-Python RF analysis, decoding and encoding.

Nothing in this package imports Home Assistant, so it is tested on its own
(``tests/``) and reused by the integration.

- ``decoders`` / ``rf_analysis``: derived from rf_device_manager (MIT, see
  ``LICENSE-rf_device_manager``): normalization, frame splitting, structural
  decoders, fingerprints, input parsers.
- ``encoder``: canonical frame search, timing measurement, encoding and the
  round-trip checks that decide whether a code is sent encoded or raw.
"""
