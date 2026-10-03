# ble/: BLE packet schema (D-061)

`ble_schema.json` is the single source for the BLE notifications that moto-connectivity-node sends to moto-mobile: the telemetry packet (versions 2, 3 and 4), the IMU block and the GATT service and characteristic UUIDs. It moved here from moto-connectivity-node's `docs/` (Q-017 resolved by D-061), so the three parties that touch the bytes read one definition instead of keeping verbatim copies with drift tests:

| Consumer | Uses | Generated file |
|---|---|---|
| moto-connectivity-node (C/C++) | offset/size macros, UUID strings, flag bits; its packed structs `static_assert` against them (gen/c stays MISRA-clean, so no packed structs are generated) | `gen/c/conn/ble_schema.h` |
| moto-server (Python) | `SCHEMA` (the whole JSON) plus `CURRENT_VERSION`, `ACCEPTED_VERSIONS`, `TOTAL_BYTES_BY_VERSION`, `telemetry_fields(version)` | `gen/python/moto_defs/ble.py` |
| moto-mobile (Dart) | `const` ints and strings in `abstract final class`es (`BleTelemetryV4Offsets`, `BleImuFlagBits`, ...) | `gen/dart/moto_defs/` (package `moto_defs`, used by path from the submodule) |

## Layout rules

- Telemetry `fields` hold the current version (4). A field without `sinceVersion` exists since version 3; `sinceVersion: 4` marks the fields appended in D-058. Fields only ever get appended, so every older version is a prefix of the next: `totalBytesByVersion` gives the size of each (3: 37, 4: 57). Version 2 is the low-MTU fallback (`lowMtuFallback`), a separate layout.
- All multi-byte fields are little-endian. Offsets and sizes are explicit; `moto-codegen check` refuses a file whose fields overlap, leave a gap, disagree with their type size, or with `totalBytes`, `totalBytesByVersion`, the IMU `headerBytes`/`sampleBytes`/`totalBytesMax`, or that reuses a flag bit or a UUID.
- Version 4's tester fields (step gap, one rotating per-DID ECU round-trip record) are TEMPORARY, like the lean fields (D-023): rt-core's health DID 0xFD02 (D-055) replaces them.

## Changing a layout

1. Edit `ble_schema.json`. Any change to field order, size or meaning bumps `version` (and `versioning.currentVersion`, `acceptedVersions`, `history`, `totalBytes`, `totalBytesByVersion`); the IMU block has its own `imuBlock.version`.
2. `make check` and `make gen`; commit the schema and `gen/` together. `make drift` (CI) fails if they differ.
3. Add a `CHANGELOG.md` entry and tag a defs release (MINOR while defs is `v0.x`; say in the entry which consumers must change).
4. conn, moto-mobile and moto-server bump their `external/moto-vehicle-defs` pin **together**; none of them may keep its own copy of the layout.

Not part of this schema: the phone telematics text written to `telematicsRx`, and the GPS block characteristic of D-060 (added here when its layout is decided).
