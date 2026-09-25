# Legacy telemetry notes (extracted per D-023)

Source: `moto-platform/HondaCl250_Telemetry` at tag `legacy-final` (commit `78e745e`), archived and read-only. Its CAN/UDS path was validated on the real CL250 (D-019). IMU, BLE and Wi-Fi were **not** verified on real hardware or phones (legacy README).

Machine-readable facts live in [`uds/vehicle_cl250.yaml`](../uds/vehicle_cl250.yaml) and are generated into `gen/`. This page keeps the context and the pitfalls, so nothing has to be rediscovered.

## Vehicle bus and addressing

- Diagnostic connector (DLC) CAN: classic CAN, 500 kbps, ESP32-S3 TWAI in normal mode, accept-all filter.
- Primary: 29-bit normal fixed addressing, request `0x18DA10F1` (ECU `0x10`, tester `0xF1`), response `0x18DAF110`.
- Fallback: 11-bit request `0x7E0`, response `0x7E8`. The legacy firmware sent **every** request on both IDs back to back (one logical request, two frames). A legacy code comment says the 11-bit request goes to `$7DF`; the code actually uses `0x7E0` (physical), which is what the YAML records.
- Requests are 8-byte frames padded with `0xAA`.

## DIDs (OBD-mapped, SAE J1979 scaling)

| DID | Signal | Formula | Poll period |
|---|---|---|---|
| `0xF40C` | Engine speed | (A·256+B)/4 rpm | 50 ms |
| `0xF40D` | Vehicle speed | A km/h | 800 ms |
| `0xF411` | Throttle position | A·100/255 % | 800 ms |
| `0xF405` | Coolant temperature | A−40 °C | 800 ms |
| `0xF442` | Control module (battery) voltage | (A·256+B)/1000 V | 800 ms |

- Polling is **priority ordered** (engine speed first), with **exactly one request in flight**: IDLE → WAITING → COMPLETE/TIMEOUT → IDLE. An earlier version fired independent timers and could not tell overlapping responses apart.
- Battery voltage: the legacy decoder also fell back to `A/10` when the response was shorter than 6 bytes or the 16-bit value was ≤ 500. That branch has no recorded evidence and contradicts the verified formula, so it was **not** carried over: a response shorter than the DID length is now dropped. If a real ECU ever returns one byte for `0xF442`, record the evidence here and in the YAML.

## Session, timing and error handling

- Session: `0x10 0x03` (extended) sent at start and **re-sent every 2 s until a positive `0x50`** arrives. The ECU is not assumed to accept it.
- Tester present: `0x3E 0x80` every 1000 ms (sent regardless of session state; harmless in the default session).
- Response timeout: 100 ms. NRC `0x78` (responsePending) restarts the wait and doubles it, capped at 2000 ms.
- Any other NRC resolves the request (it is neither a success nor a timeout).
- 5 consecutive timeouts on one DID → that DID is skipped for 5 s.
- ECU presence: any positive (`0x50`, `0x62`) **or negative** (`0x7F`) response within the last 3 s means the ECU is present. Consumers show an explicit "ECU not found" state instead of frozen values.
- Bus-off: recovery retried with exponential backoff 1 s → 2 s → … capped at 30 s; after recovery the driver lands in STOPPED and must be restarted.
- Staleness: every value carries its last-update time. Legacy threshold 500 ms (applied to all values in the Nextion and logger code, even the 800 ms DIDs, which therefore flicker to stale between polls; a per-DID threshold of about 2× the poll period is the fix).

## NRC names (ISO 14229-1 Annex A)

`0x10` generalReject · `0x11` serviceNotSupported · `0x12` subFunctionNotSupported · `0x13` incorrectMessageLengthOrInvalidFormat · `0x21` busyRepeatRequest · `0x22` conditionsNotCorrect · `0x24` requestSequenceError · `0x31` requestOutOfRange · `0x33` securityAccessDenied · `0x35` invalidKey · `0x78` responsePending · `0x7E` subFunctionNotSupportedInActiveSession · `0x7F` serviceNotSupportedInActiveSession

## ISO-TP first-frame pitfall

Every DID above fits in a single frame (PCI high nibble `0x0`). The legacy parser read `data[1]` as the SID directly. On a **first frame** (PCI `0x1X`), `data[1]` is the low byte of the multi-frame length, not a SID, so parsing it would silently corrupt values. The fix was to drop any response whose PCI type is not single frame. Full multi-frame ISO-TP (first frame + flow control + consecutive frames) is a rewrite item for moto-rt-core (D-023); until then, keep DIDs at ≤ 4 data bytes (the codegen enforces this).

## Pin map (ESP32-S3 DevKitC-1, legacy)

| Function | Pins | Notes |
|---|---|---|
| CAN (TWAI) | TX `GPIO4`, RX `GPIO5` | via a CAN transceiver to the DLC |
| Nextion display | UART2 TX `GPIO17`, RX `GPIO18` | 115200 8N1 |
| IMU (MPU6050) | SDA `GPIO1`, SCL `GPIO2` | I²C 400 kHz, address `0x68` (dropped, see below) |
| Loop-timing probe | `GPIO8` | high during one loop pass |
| Wi-Fi AP trigger | `GPIO0` (BOOT button) | held within 1 s of boot |

## Other lessons carried into the port

- Module pattern: producers (CAN, BLE) write the shared state first each pass, consumers (Nextion, Wi-Fi, logger) get it read-only; unhealthy modules are skipped; central scheduling via each module's declared period.
- Task watchdog (5 s) around the main loop; boot log prints the reset reason.
- BLE: the RX (write) characteristic requires an encrypted, bonded link ("Just Works", no MITM protection, because the board has no display/keypad). BLE stack callbacks only enqueue events; the main loop applies them (no data race on the shared state).
- Phone-supplied text is sanitised before it reaches the Nextion (quotes, backslash, control bytes, `0xFF` terminators) and the JSON endpoint.
- Wi-Fi AP is **off by default**; it starts only on the BOOT button at start-up or when no BLE client connects within 15 s. The AP password is a build-time secret, never committed.
- `WiFi.persistent(false)` to avoid NVS writes on every boot.

## Dropped (D-023)

- Web PWA (`mobile_app/*.html/js/css/py`).
- Complementary-filter lean angle (IMUModule): known to be wrong (D-023). Lean angle comes from the rt-core EKF (`LeanEstimate`, platform.dbc) instead.
