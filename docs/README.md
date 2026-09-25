# Documentation Index — where to look for what

**Rule (for Claude):** start with `ARCHITECTURE.md` + `DECISIONS.md`. The raw docs below are large (~3,400 lines, ~60k tokens in total), so read only the needed section with `Read offset/limit`, or ask the `docs-researcher` agent. Line numbers are as of 2026-09-25. If a doc changes, refresh them with `grep -n '^#' <file>`.

Authority order: `DECISIONS.md` > `ARCHITECTURE.md` > other English docs > `tr/` archive.

| File | Status | Use for |
|---|---|---|
| `ARCHITECTURE.md` | **Authoritative (summary)** | Units, buses, CAN ID plan, E2E, codegen pipeline, layers, data flows, CI pyramid |
| `DECISIONS.md` | **Authoritative** | Decisions (ADR D-xxx) + open questions (Q-xxx) |
| `hardware-architecture.md` | Authoritative (detail) | Subsystem rationale, references, Phase 2 list |
| `vehicle-work-plan.md` | Authoritative (on-vehicle) | CL250 data, mounting, field test protocols T0-T4, virtual dyno |
| `phase0-data-collection-plan.md` | Authoritative (data) | Recording format, metadata schema, work packages WP-1..WP-7 |
| `feature-pool.md` | Pool | All feature candidates (IDs F1.., K1.., ...), open-source references |
| `hardware-procurement-list.md` | Current | Hardware groups 1-12, items on hand |
| `tr/bitirme-projesi-kapsam.md` | Turkish, advisor-facing, **partly outdated** (ESP32 DUT, no Raspi — see D-001) | Thesis core/extended scope Ç1-Ç8 / G1-G5, 14-week schedule |
| `tr/bitirme-raporu-hoca-sunumu.md` | Turkish, advisor report | Methodology, MCU adequacy analysis, SDG |
| `tr/*` (others) | Turkish originals of the English docs | Not maintained. Use only if a translation looks wrong |

## hardware-architecture.md (854 lines)

| Lines | Section |
|---|---|
| 11-94 | §1-5 philosophy, 5 units, chip choices, CAN rules, latency |
| 97-190 | §5b.0-0c context classification, conditioning factors, context bus |
| 191-241 | §5b.1 blind spot monitoring (BSM) |
| 242-281 | §5b.2 cornering safety (3 layers) |
| 282-327 | §5b.3 io-node: immobilizer, park mode, power board |
| 328-373 | §5b.4 display / LED ring / profile pages |
| 374-446 | §5b.5 lane departure warning (LDW) |
| 447-465 | §5b.6 voice commands (ESP-SR) |
| 466-524 | §5b.7 moto-mcp, privacy |
| 525-576 | §5b.8 linux-node SDV layer, Raspi power/thermal |
| 577-624 | §5b.9 anomaly model + validation protocol |
| 625-644 | §5b.10-11 virtual dyno, comfort/energy/driver assistance |
| 645-680 | §6-7 module vs chip, staged rollout |
| 681-742 | §8-9 repo structure, dependency direction, setup order |
| 743-812 | §9b HIL bench |
| 813-854 | §10 Phase 2, eliminated items, open notes |

## vehicle-work-plan.md (669 lines)

| Lines | Section |
|---|---|
| 19-92 | §2 CL250 data, ratios, wheel radius, speed formula |
| 93-199 | §3 on-vehicle hardware (DUT, CAN, power, IMU, GPS, microphone) |
| 200-228 | §4 wiring, EMC, sleep current |
| 229-288 | §5 parameter measurement, **5.5 CAN signal map extraction (271)** |
| 289-346 | §6 data collection: signals, metadata, storage |
| 347-419 | §7 field test classes T0-T4 |
| 420-472 | §8 virtual dynamometer protocol |
| 473-545 | §9-11 assistant profiles, modification experiments, real dyno |
| 546-584 | §12 legal/safety framework |
| 585-669 | §13-16 BOM, schedule, risks, deliverables |

## phase0-data-collection-plan.md (272 lines)

§1 work packages 25-38 · §3 data schema 74-122 (format decision 109) · §4-8 WP-3..WP-7 123-200 · §9 hardware 201-246 · §10-11 effort, next 247-272

## feature-pool.md (624 lines)

§1-13 categories 26-311 (vehicle functions §9 173, comfort/energy §9c 223, vision §10 254) · §14 top ten 312 · §15 out of pool 332 · §16 prioritization 345 · §17 hardware analysis 361-404 · §18 open-source ecosystem 405-624 (SDV §18.3 446, test/sim §18.5 479, data/ML §18.6 495, reference projects §18.7 510, costs §18.9 545)

## hardware-procurement-list.md (156 lines)

Groups 1-12: 12-142 · grand total 143 · on hand 149

## tr/ advisor docs (Turkish)

- `tr/bitirme-projesi-kapsam.md` (221): §5 scope 69-108, §8 validation 144-170, §9 schedule 171-188, §11 risks 202-213
- `tr/bitirme-raporu-hoca-sunumu.md` (763): §1-2 goals/functions 28-94, §3 hardware 95-168, §4 repos 169-221, §5 methodology 222-353, §6 architecture 354-404, §7 MCU adequacy 405-485, §8 HIL 486-546, §9 scalability 547-
