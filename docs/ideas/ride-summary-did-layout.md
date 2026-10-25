# Ride-summary DID layout (C3 part 2b) — proposal, awaiting the user

Status: **proposal**, nothing implemented. 2026-10-26, Claude. Decisions it builds on: D-070 item 4 (class-B ride summaries are rt-core UDS DIDs 0xFD40-0xFD5F), D-087 item 2 (a ride = one D-075 stop epoch), D-055/D-067 (the existing `record` DID encoding). On approval it becomes a decision (D-0xx) and a `/signal-change`.

## Problem

`derived/cl250_derived.yaml` reserves one DID per ride-summary record (0xFD40-0xFD49 summaries, 0xFD4A-0xFD4E health windows) and gives every class-B signal its record, `range` and `resolution`, but no byte layout. rt-core computes 12 of these signals since rt-core#54 and cannot serve them without a layout, and a hand-written layout would break invariant 2.

## Proposal

1. **Generated, not hand-written.** Codegen builds each record's layout from `cl250_derived.yaml` (the class-B signals of that `record`, in YAML order) and emits it into the rt-core `platform_uds` tables as an ordinary `record` DID (the same encoding as 0xFD02/0xFD03: big-endian unsigned fields of 1, 2 or 4 bytes that saturate, never wrap). No layout is typed into `uds/dids.yaml` by hand.
2. **Field encoding.** `raw = round((value - range.min) / resolution)`, unsigned, big-endian. Width = the smallest of 1, 2 or 4 bytes whose all-ones value is above the largest raw value: the all-ones value is reserved as **NOT_AVAILABLE** (not computed on rt-core yet, not valid, or no ride closed). A value outside the range is NOT_AVAILABLE too (D-070: never clamped). Offsetting by `range.min` makes signed signals unsigned, so the existing encoder needs no signed field type.
3. **Header (4 bytes, every record).** Byte 0: layout version (1). Bytes 1-2: the ride's stop-epoch counter (uint16, from `services/tester_epoch`; lets a reader match records of the same ride and see a new ride). Byte 3: flags — bit 0 `RIDE_CLOSED` (1 = the last closed ride, 0 = no ride closed since boot, all fields NOT_AVAILABLE); bits 1-7 reserved 0.
4. **Which ride.** The DIDs serve the **last closed ride** (the previous-ride record of rt-core#54). The running ride is not served in v1 (it changes during the read, and the log covers it); a "current ride" mirror at 0xFD50-0xFD5E stays possible later inside the reserved block.
5. **Multi-element signals are left out of v1.** `operating_point_time` (RPM × load histogram), `fuel_trim_map`, `ride_coolant_time_at_temp`, `ride_oil_time_at_temp` and the per-gear `ride_final_drive_ratio` get their own layout later (a histogram does not fit a small record; ISO-TP allows it, but the server buffer and the D-070 item 6 cost need a separate look). Their records carry only the scalar fields; `RIDE_OPERATING_POINTS` (only a histogram) is not served in v1.
6. **Serving.** The platform UDS server (comms task) answers 0x22 for these DIDs from a comms-side copy of the closed-ride record, which the derived task hands over through one `services/snapshot` (derived → comms, single producer and consumer, the 0xFD03 pattern: the server never reads the derived state itself). Read-only, platform bus only, never the vehicle bus.

## Resulting sizes (scalar fields + 4 B header, computed from the current YAML)

| DID | Record | Scalar fields | Bytes |
|---|---|---|---|
| 0xFD40 | RIDE_USAGE | distance 4 B, time 4 B, idle time 4 B, stop count 2 B | 18 |
| 0xFD41 | RIDE_FUELING | fuel used, consumption, LTFT mean, STFT std (2 B each) | 12 |
| 0xFD42 | RIDE_OPERATING_POINTS | — (histogram only) | not served in v1 |
| 0xFD43 | RIDE_THERMAL | 8 fields (1-2 B) | 14 |
| 0xFD44 | RIDE_ELECTRICAL | cranking dip, rest voltage | 8 |
| 0xFD45 | RIDE_ENGINE_STRESS | 6 fields | 22 |
| 0xFD46 | RIDE_DRIVETRAIN | 4 fields | 12 |
| 0xFD47 | RIDE_CALIBRATION | 4 fields | 14 |
| 0xFD48 | RIDE_RIDER_STYLE | 2 fields | 8 |
| 0xFD49 | RIDE_ECU_HEALTH | 7 fields | 21 |
| 0xFD4A-0xFD4E | health windows W1-W5 | 4-8 fields | 12-20 |

Today rt-core computes 12 of the scalar fields; the others read NOT_AVAILABLE until their formula exists, so the layout is stable while signals are added.

## Open points for the user

- Approve the encoding (offset by `range.min`, all-ones = NOT_AVAILABLE, 4-byte header with the epoch counter) and "last closed ride only" for v1.
- Approve leaving the histogram / per-gear signals for a later layout.
- A defs MINOR release follows (new generated DIDs), then rt-core serves them (QM, D-070 item 5).
