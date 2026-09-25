# CLAUDE.md — moto-vehicle-defs

## What this repo is

The **single source of truth for signals** in the motorcycle platform. The CAN message map, the VSS (COVESA Vehicle Signal Specification) semantic model, and the diagnostic (UDS) service definitions live here. **The other 10 repos read this repo; none of them invent their own signal definitions.**

## What this repo is NOT

- Executable code (firmware, services) does not live here — only schema/definitions. Exception: `tools/codegen` (a development tool) and the `gen/` output it produces (pack/unpack/E2E code derived from the definitions).
- There is no business logic. It defines *what* a signal *is*, not *how* it is used.

## File structure (D-003, D-004 — `docs/ARCHITECTURE.md` §5)

```
/dbc/cl250.dbc        → vehicle bus (OEM, reverse-engineered; unverified signals are flagged)
/dbc/platform.dbc     → platform bus (our nodes; ID plan in ARCHITECTURE §4; E2E attributes)
/vss/overlay.vspec    → Vehicle.Motorcycle.* extensions + dbc2vss mappings (kuksa-can-provider format)
/uds/dids.yaml        → per-node DID/DTC/routine definitions
/tools/codegen/       → Python: cantools + vss-tools; generates node-filtered C, Python, VSS JSON
/gen/                 → GENERATED output (no manual edits; `make gen` + commit before tagging)
/docs/                → all platform documentation (index: docs/README.md)
/CHANGELOG.md         → what changed in each release
```

Signal add/change flow: the `/signal-change` skill. CI must fail red if `gen/` is out of sync with the source.

## Versioning rule — THE MOST IMPORTANT RULE

This repo is **semantically versioned** (v1.0.0, v1.1.0...). Other repos pin to a specific version (git submodule + tag, or package version). Adding/changing/removing a signal:

1. Is done here first, a line is added to `CHANGELOG.md`
2. A new version is tagged
3. **Only after that** are dependent repos (`moto-rt-core`, `moto-linux-node`, etc.) updated to the new version — not automatic, a deliberate step

When Claude Code works in this repo: after changing a signal schema, **check which repos depend on this version and remind the user** — do not break them silently.

## Signal naming

Follow the VSS taxonomy (e.g. `Vehicle.Powertrain.CombustionEngine.Speed`). Do not invent your own arbitrary naming — check COVESA's VSS specification; if there is no VSS equivalent for a motorcycle-specific signal, propose a consistent extension under `Vehicle.Motorcycle.*` and **ask the user first**, do not add it silently.

## Context — project architecture

For the full hardware/repo architecture: `docs/ARCHITECTURE.md` (summary) and `docs/DECISIONS.md` · detail: `docs/hardware-architecture.md` §8-9 (section index in `docs/README.md`). You don't need to read this file every time — only check it when a signal/repo dependency is unclear.

## Vehicle: CL250 (first application)

Motorcycle: Honda CL250, classic CAN (not CAN-FD — work under this assumption until verified, Q-001). The platform bus is independent of it: classic CAN 500 kbps (D-009). `/dbc/cl250.dbc` is this vehicle's concrete definition; the schema under `/vss/` is vehicle-independent.
