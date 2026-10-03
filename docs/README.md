# Documentation Index — where to look for what

**Rule (for Claude):** start with `ARCHITECTURE.md` + `DECISIONS.md`. The raw docs below are large (~2,800 lines in total), so read only the needed section with `Read offset/limit`, or ask the `docs-researcher` agent. Line numbers are as of 2026-09-29. If a doc changes, refresh them with `grep -n '^#' <file>`.

Authority order: `DECISIONS.md` > `ARCHITECTURE.md` > other English docs. For vehicle facts, `uds/vehicle_cl250.yaml` beats `legacy-telemetry-notes.md`. `archive/` is not read by Claude (D-038).

| File | Status | Use for |
|---|---|---|
| `ARCHITECTURE.md` | **Authoritative (summary)** | Units, buses, CAN ID plan, E2E, codegen pipeline, layers, data flows, CI pyramid |
| `DECISIONS.md` | **Authoritative** | Decisions (ADR D-xxx) + open questions (Q-xxx) |
| `hardware-architecture.md` | Detail (rationale); **bus topology superseded** by ARCHITECTURE §3 | Subsystem rationale, references, Phase 2 list |
| `vehicle-work-plan.md` | On-vehicle plan (bus access per D-037) | CL250 data, mounting, field test protocols T0-T4, virtual dyno |
| `phase0-data-collection-plan.md` | Authoritative (data), superseded in part (D-032, D-045) | Recording format, metadata schema, work packages WP-1..WP-7 |
| `feature-pool.md` | Pool | All feature candidates (IDs F1.., K1.., ...), open-source references |
| `hardware-procurement-list.md` | Current | Hardware groups 1-12, items on hand |
| `hardware-integration.md` | Working guide (2026-10-03) | Phase 0 on-vehicle build: parts, wiring, mounting, bring-up gates, first measurements, open items |
| `e2e-profile.md` | **Authoritative (spec, short)** | E2E frame layout, CRC, counter, receiver statuses, timeouts (D-005, D-026) |
| `legacy-telemetry-notes.md` | Reference (short) | Legacy HondaCl250_Telemetry facts per D-023: UDS state machine, NRC table, bus-off backoff, ISO-TP first-frame pitfall, ESP32-S3 pin map, discrepancies, accepted security risks, legacy test coverage |
| `archive/tr/*` | Turkish originals + the two advisor documents (D-038) | **Not read by Claude.** Ç1-Ç8 are in `ARCHITECTURE.md` §9 |

## hardware-architecture.md (859 lines)

| Lines | Section |
|---|---|
| 13-95 | §1-5 philosophy, 5 units, chip choices, CAN rules, latency (bus topology: see ARCHITECTURE §3) |
| 96-191 | §5b.0-0c context classification, conditioning factors, context bus |
| 192-242 | §5b.1 blind spot monitoring (BSM) |
| 243-286 | §5b.2 cornering safety (3 layers) |
| 287-332 | §5b.3 io-node: immobilizer, park mode, power board |
| 333-378 | §5b.4 display / LED ring / profile pages |
| 379-451 | §5b.5 lane departure warning (LDW) |
| 452-470 | §5b.6 voice commands (ESP-SR) |
| 471-529 | §5b.7 moto-mcp, privacy |
| 530-581 | §5b.8 linux-node SDV layer, Raspi power/thermal |
| 582-629 | §5b.9 anomaly model + validation protocol |
| 630-649 | §5b.10-11 virtual dyno, comfort/energy/driver assistance |
| 650-685 | §6-7 module vs chip, staged rollout |
| 686-747 | §8-9 repo structure, dependency direction, setup order |
| 748-817 | §9b HIL bench |
| 818-859 | §10 Phase 2, eliminated items, open notes |

## vehicle-work-plan.md (672 lines)

| Lines | Section |
|---|---|
| 19-92 | §2 CL250 data, ratios, wheel radius, speed formula |
| 93-202 | §3 on-vehicle hardware (DUT, CAN + bus safety note 3.2, power, IMU, GPS, microphone) |
| 203-231 | §4 wiring, EMC, sleep current |
| 232-291 | §5 parameter measurement, **5.5 CAN signal map extraction (274)** |
| 292-349 | §6 data collection: signals, metadata, storage |
| 350-422 | §7 field test classes T0-T4 |
| 423-475 | §8 virtual dynamometer protocol |
| 476-548 | §9-11 assistant profiles, modification experiments, real dyno |
| 549-587 | §12 legal/safety framework |
| 588-672 | §13-16 BOM, schedule, risks, deliverables |

## phase0-data-collection-plan.md (278 lines)

Superseded-in-part note (D-032, D-045) at the top, line 5 · §1 work packages 27-40 · §3 data schema 76-124 (format decision 111) · §4-8 WP-3..WP-7 125-206 · §9 hardware 207-252 · §10-11 effort, next 253-278

## feature-pool.md (624 lines)

§1-13 categories 26-311 (vehicle functions §9 173, comfort/energy §9c 223, vision §10 254) · §14 top ten 312 · §15 out of pool 332 · §16 prioritization 345 · §17 hardware analysis 361-404 · §18 open-source ecosystem 405-624 (SDV §18.3 446, test/sim §18.5 479, data/ML §18.6 495, reference projects §18.7 510, costs §18.9 545)

## hardware-procurement-list.md (156 lines)

Groups 1-12: 12-142 · grand total 143 · on hand 149

## archive/tr/ (for the user; not read by Claude, D-038)

- `bitirme-projesi-kapsam.md`: thesis scope (§5 Ç1-Ç8 / G1-G5), validation, 14-week schedule, risks
- `bitirme-raporu-hoca-sunumu.md`: advisor report (methodology, MCU adequacy, HIL, scalability)
- the Turkish originals of the English docs (not maintained)
