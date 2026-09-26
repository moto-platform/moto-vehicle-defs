# Legacy Telemetry Notes — HondaCl250_Telemetry

**Source**: `moto-platform/HondaCl250_Telemetry@16a4b26` (archived, read-only reference; never modify it).
**Purpose**: human-readable extraction of the legacy ESP32 prototype's UDS/CAN protocol knowledge, per D-023, so it is not rediscovered while building moto-rt-core. Relates to D-019 (verified CL250 bus parameters).
**Authority**: all machine-readable values (DIDs, formulas, addressing, timing constants) live in `uds/vehicle_cl250.yaml`. If this document and the YAML ever disagree, **the YAML wins** — fix this file to match, not the other way around.

Every fact below is cited as `path:line` inside the archived repo (not this repo).

## 1. UDS request/response state machine

Single request in flight: `IDLE → WAITING → COMPLETE/TIMEOUT → IDLE` (`src/HondaCANModule.h:51-59`, `src/HondaCANModule.cpp:170-199,201-214,312-315`). DID slots are priority-ordered, RPM checked first every cycle so a slow DID's wait can never starve it for more than one timeout window (`src/HondaCANModule.h:72-81`):

| DID | Signal | Cadence |
|---|---|---|
| `0xF40C` | Engine RPM | 50 ms |
| `0xF40D` | Vehicle Speed | 800 ms |
| `0xF411` | Throttle Position | 800 ms |
| `0xF405` | Coolant Temperature | 800 ms |
| `0xF442` | Battery Voltage | 800 ms |

Base timeout 100 ms (`src/HondaCANModule.h:89`). NRC `0x78` (responsePending) resets and doubles the timeout, capped at 2000 ms, without resolving the request (`src/HondaCANModule.h:90`, `src/HondaCANModule.cpp:290-298`). Any other NRC resolves the request as COMPLETE (`src/HondaCANModule.cpp:299-308`). 5 consecutive timeouts on a DID skip it for 5000 ms (`src/HondaCANModule.h:91-92`, `src/HondaCANModule.cpp:201-214`).

ECU is considered "present" if any positive response (`0x62` or `0x50`) or any NRC was seen within the last 3000 ms (`src/HondaCANModule.h:94-109`, `src/HondaCANModule.cpp:160-168,275,282,288`). Extended session (`0x10 0x03`) is retried every 2000 ms until a positive `0x50` confirms it (`src/HondaCANModule.h:103-105`, `src/HondaCANModule.cpp:37-42,151-158,276-282`). Tester-present (`0x3E 0x80`) is sent every 1000 ms, unconditionally, regardless of session state (`src/HondaCANModule.cpp:143-149`).

Frames are always 8 bytes, unused trailing bytes padded `0xAA` (`src/HondaCANModule.cpp:52-78`, padding loops at `:61` and `:75`). Every request is sent on **both** 29-bit `0x18DA10F1` and 11-bit `0x7E0` (`src/HondaCANModule.cpp:3-9,40-41,100-103,147-148,156-157`); responses are accepted from `0x18DAF110` and `0x7E8` (`src/HondaCANModule.h:21-22`, `src/HondaCANModule.cpp:220`).

## 2. NRC table (`nrcName()`, `src/HondaCANModule.cpp:80-97`)

| Code | Name | Handling |
|---|---|---|
| `0x10` | generalReject | logged, request resolved |
| `0x11` | serviceNotSupported | logged, request resolved |
| `0x12` | subFunctionNotSupported | logged, request resolved |
| `0x13` | incorrectMessageLengthOrInvalidFormat | logged, request resolved |
| `0x21` | busyRepeatRequest | logged, request resolved |
| `0x22` | conditionsNotCorrect | logged, request resolved |
| `0x24` | requestSequenceError | logged, request resolved |
| `0x31` | requestOutOfRange | logged, request resolved |
| `0x33` | securityAccessDenied | logged, request resolved |
| `0x35` | invalidKey | logged, request resolved |
| `0x78` | responsePending | **special**: reset + double timeout (capped 2000 ms), request stays WAITING |
| `0x7E` | subFunctionNotSupportedInActiveSession | logged, request resolved |
| `0x7F` | serviceNotSupportedInActiveSession | logged, request resolved |
| other | unknownNRC | logged, request resolved |

All non-`0x78` codes are counted (`_nrcCount`) and move the state machine `WAITING → COMPLETE` (`src/HondaCANModule.cpp:283-308`); any NRC also counts as proof the ECU is alive (`:288`).

## 3. Bus-off recovery

Exponential backoff: 1000 ms initial, doubling each attempt, capped at 30000 ms (`src/HondaCANModule.h:34-41`, `src/HondaCANModule.cpp:108-129`). On entering `BUS_OFF`: log once, reset backoff, attempt recovery immediately (`src/HondaCANModule.cpp:111-121`). `STOPPED` (where the driver lands after `initiateRecovery()` completes) triggers `_bus.start()` (`src/HondaCANModule.cpp:130-137`); `RUNNING` after a prior bus-off resets the backoff state (`:138-141`). TWAI alerts enabled: `BUS_OFF`, `BUS_RECOVERED`, `ERR_PASS`, `ABOVE_ERR_WARN`; filter is accept-all (`src/hal/TwaiCanBus.cpp:9-10`).

## 4. ISO-TP first-frame pitfall

Only Single Frames (PCI high nibble `0x0`) are handled. A First Frame (PCI `0x1X`) has `data[1]` as part of the multi-frame length field, **not** a SID — parsing it as one would corrupt `SystemState` (`src/HondaCANModule.cpp:222-238`). The legacy code drops any non-SF frame with a warning and continues (`:232-239`); this is exercised by a unit test (`test/test_can_protocol/test_main.cpp:149-164`). All DIDs used today fit in a Single Frame (≤7 bytes payload), so this only guards against a future response that grows past that. **Consequence for moto-rt-core**: full multi-frame ISO-TP (First Frame + Flow Control + Consecutive Frames) must be implemented from scratch — out of scope in the legacy code, in scope for the D-023 rewrite.

## 5. Pin map (ESP32-S3 DevKitC-1)

| Signal | Pin | Notes |
|---|---|---|
| CAN TX | `GPIO_NUM_4` | `src/main.cpp:23` |
| CAN RX | `GPIO_NUM_5` | `src/main.cpp:24`; 500 kbps (`src/hal/TwaiCanBus.cpp:7`) |
| I2C SDA | `GPIO_NUM_1` | `src/main.cpp:26` |
| I2C SCL | `GPIO_NUM_2` | `src/main.cpp:27`; MPU6050 @ `0x68`, 400 kHz (`CONTEXT.md:22`) |
| Nextion UART2 TX | `GPIO_NUM_17` | `src/main.cpp:29` |
| Nextion UART2 RX | `GPIO_NUM_18` | `src/main.cpp:30`; 115200 baud, SERIAL_8N1 (`CONTEXT.md:21`) |
| Debug loop probe | `GPIO_NUM_8` | `src/main.cpp:32-34`, not wired to any peripheral |
| USB serial | — | 115200 baud, debug log output (`CONTEXT.md:19`) |

## 6. Discrepancies / pitfalls found in the legacy code

- **(a) Slow-DID cadence.** `CONTEXT.md:55` documents the slow DIDs as "5Hz / 200ms"; the actual `DidSlot` cadence in code is 800 ms for all four (`src/HondaCANModule.h:77-80`). Code is authoritative — it is what ran on hardware and is what `test/test_can_protocol` exercises.
- **(b) Wrong ID comments.** `sendFrame11`'s doc comment claims it sends to "$7DF" (`src/HondaCANModule.h:116-118`), but the implementation targets `0x7E0` physical addressing (`src/HondaCANModule.cpp:9,66-78`). The `#define` comment at `src/HondaCANModule.cpp:8` also labels `0x7E8` as "Source Tool" — `0x7E8` is actually the ECU's *response* ID (`UDS_RESP_11BIT`, `src/HondaCANModule.h:22`), not a tester/source address.
- **(c) Battery voltage heuristic.** `0xF442` decode uses `rawVolt > 500 ? rawVolt/1000.0f : data[4]/10.0f` (DLC≥6), else `data[4]/10.0f` (`src/HondaCANModule.cpp:260-268`) — a heuristic, not the plain J1979 `(A*256+B)/1000` formula. `uds/vehicle_cl250.yaml` uses the plain J1979 formula only; the heuristic branch is **not** carried over.
- **(d) Staleness threshold.** A single 500 ms threshold applies uniformly to every signal (`src/SystemState.h:10-15`), tighter than the 800 ms cadence of four of the five DIDs.
- **(e) Tester-present timing.** Sent every 1000 ms unconditionally, even before the extended session is confirmed (`src/HondaCANModule.cpp:143-149`).
- **(f) Lean angle dropped.** The IMU complementary-filter lean angle (`DynamicsData.leanAngle`, `src/SystemState.h:41-46`; computed per `CONTEXT.md:9`) is not ported — replaced by rt-core's EKF fusion (D-023).

## 7. Accepted security risks (`SECURITY.md`)

| Risk | Legacy rationale | Platform status |
|---|---|---|
| No secure boot (`:22-30`) | eFuse burn irreversible; no OTA ⇒ no remote path | **Re-assess** — rt-core adds a UDS bootloader/OTA path, so "no remote path" no longer holds |
| No flash encryption (`:32-39`) | Same physical-access precondition as secure boot | **Re-assess** once OTA exists, same reasoning |
| No physical access protection (`:41-46`) | Matches OEM diagnostic-port trust model | Still applies, no new mitigation planned |
| No OTA (`:48-54`) | Removes remote-attack surface, zero cost for one hobby unit | **Does not carry over** — platform has OTA via UDS bootloader |
| BLE Just Works pairing (`:56-68`) | No display/keypad for passkey pairing | Still applies to the connectivity-node BLE port (same hardware) |
| HTTP no auth beyond WPA2 (`:70-77`) | Read-only data, WPA2 is the access boundary | Still applies to the ported Wi-Fi module |
| CAN/UDS no authentication (`:79-86`) | Matches vehicle's own UDS-over-CAN design | Still valid; platform adds the D-020 service allow-list on the tester side |

Hardened items carried forward (`SECURITY.md:9-18`, one line each):
- Wi-Fi SoftAP: WPA2-PSK, password out of source control, AP off by default.
- BLE telematics write: bonding + link encryption required; notify stream stays unauthenticated.
- BLE/HTTP → Nextion/JSON: input character-filtered / JSON-escaped.
- BLE packet integrity: versioned wire format, version mismatch rejected.
- CAN/UDS malformed responses: NRC, ISO-TP frame-type, and timeout handling.
- Flash/NVS: no runtime writes; `WiFi.persistent(false)`.

## 8. Test coverage in the legacy repo (`test/test_can_protocol/test_main.cpp`)

| Test | Line | Behaviour covered |
|---|---|---|
| `test_rpm_decode_updates_state_and_ecu_presence` | `:73` | RPM decode formula, one-cycle-delayed `ecuPresent` flip |
| `test_session_confirm_is_recognized` | `:100` | `0x50` stops the 2 s session retry |
| `test_nrc_other_than_pending_resolves_request_without_corrupting_state` | `:128` | non-`0x78` NRC resolves WAITING, state untouched |
| `test_multiframe_response_is_dropped_not_misparsed` | `:149` | First Frame dropped, not parsed as a SID |
| `test_bus_off_triggers_recovery_with_backoff` | `:166` | exponential backoff timing |
| `test_bus_recovery_complete_restarts_driver` | `:193` | `STOPPED → start()` call |
| `test_did_skipped_after_max_consecutive_timeouts_then_resumes` | `:209` | 5× timeout skip + cooldown resume |

`isStale()` and the BLE packet layout are covered separately in `test/test_native/test_main.cpp` (`platformio.ini:34-44`). Not covered by native tests: the NRC table's individual codes beyond `0x31`/`0x78`, the battery-voltage heuristic decode, tester-present cadence, and the HAL/pin config — `src/hal/TwaiCanBus.cpp` is excluded from the native build; only `HondaCANModule.cpp` is compiled against `MockCanBus` (`test/test_can_protocol/test_main.cpp:5-10`).
