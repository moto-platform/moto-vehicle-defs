# Vehicle-agnostic anomaly reasoning and generalisation (idea note)

Idea note (Claude, 2026-10-27), **not a decision until D-xxx below is recorded in `DECISIONS.md`**. User choices from the 2026-10-27 session: hybrid relationship graph; anomalies need not be tagged to be reasoned about; the system validates its hypotheses with the rider; the design must scale beyond the CL250 to other motorcycles and to cars.

Known conflicts with recorded decisions:
- **D-084 item 3** says the LLM never diagnoses outside the catalog and answers "unidentified anomaly" when nothing matches. This note replaces that answer with evidence-bound hypotheses and a validation dialogue (D-xxx item 3). The catalog stays the first knowledge source.
- None with invariants 2, 3, 4 and 7: graph edges use defs signals only, nothing here feeds the safety partition, critical warnings still bypass the LLM (D-085 item 4), and every number comes from a tool.

## 1. Pipeline

| Layer | Job | Needs labels? | Where |
|---|---|---|---|
| 1. Detect | Flag "something is not normal": statistical distance (the "Jev" fast gate: Mahalanobis on residual features), physics residuals (D-083 level 1), broken correlations between related signals | No | Edge screen on the Raspi/server (D-083 item 4: no MCU inference); server for ride-level analysis |
| 2. Localise | Find which relationships broke, using the relationship graph (§2) | No | vehicle-mcp tool, computed |
| 3. Reason | Rank hypotheses from the broken edges, the context (ride window, temperature, load, history) and the fault catalog used as a knowledge base | No | LLM over vehicle-mcp tool results |
| 4. Validate | Ask discriminating questions to the rider and request targeted data (extra DID reads within the tester policy, freeze frames) to separate the hypotheses | — | Rider layer (Q-037) + vehicle-mcp |
| 5. Learn | A validated case becomes a labelled record: a new catalog entry or new evidence for an existing one, a HIL scenario and a vehicle-ml label | Labels are produced here | defs catalog (via `/signal-change`), vehicle-ml |

The loop in layer 5 is the main contribution: the system creates its own labelled fault data while it is used, which removes the "no labelled faults" problem that blocks a data-only model.

## 2. Relationship graph (hybrid)

- **Nodes:** defs signals and derived signals only (invariant 2).
- **Static edges (start here):** relationships known from physics and the D-083 level-1 models, e.g. RPM ↔ vehicle speed per gear (ratio table), RPM ↔ charging voltage (regulated plateau above cut-in), load/MAP ↔ coolant temperature (thermal model), MAP/IAT/RPM ↔ fuel trims (speed-density). Each edge carries its model, its expected band and its source.
- **Learned candidate edges:** dependencies found in recorded data (correlation, mutual information, lagged dependence). They enter as `candidate` and never drive an explanation on their own.
- **Promotion rule:** a candidate edge becomes `confirmed` only after a validated case uses it or a cited source supports it.
- **Output of the localise tool:** the broken edges with their evidence (window, expected band, observed value, residual), never free text.

## 3. Guardrails

1. A hypothesis must name graph nodes and cite the broken edges and windows that support it; no evidence, no hypothesis.
2. Hypotheses are labelled as hypotheses with a confidence rank, never as a diagnosis.
3. No dialogue while riding: only short warnings; questions wait for a stop.
4. Never state that riding on is safe; high-severity subsystems (brakes, steering, tyres, fuel leak, overheating) always advise stopping and an inspection (D-084 item 4).
5. A rider answer alone never closes a case; closing needs data evidence or a service result.
6. Targeted data requests stay inside the tester policy (invariant 1, D-020).

## 4. Evaluation (thesis metrics)

Faults are injected (software injection on recorded rides first, then the HIL bench, then safe reversible faults on a parked bike: fan unplugged at idle, a series resistor on the battery lead, extra electrical load; never brakes, steering or fuel). The system does not see the ground truth.

- Localisation: is the injected relationship among the broken edges?
- Reasoning: is the true cause in the top-3 hypotheses?
- Dialogue: number of questions to reach the true cause.
- Detection: false alarms per riding hour, detection delay.
- D-083 item 3 comparison: physics-informed vs data-only detector on the same features.

## 5. Reference problem on a single, possibly faulty vehicle

- "Healthy" is defined by physics and the manufacturer's values (service manual bands, ratios), not by the CL250's own data, so a fault already present shows up as a parameter outside its band instead of being learned as normal.
- Known-state baseline: a full service, a DTC read and a battery test first; the rides right after it are marked as the verified-healthy baseline.
- Robust statistics (median, trimmed estimates, an assumed contamination share) so occasional abnormal moments do not move the baseline.

## 6. Generalisation to other vehicles

| Layer | Content | Frequency | Source |
|---|---|---|---|
| 1. Physics | Energy balance, heat transfer, charging circuit, gear kinematics, vehicle dynamics | Never changes | Physics |
| 2. Class template | Graph topology and model set per powertrain class: single-cylinder liquid-cooled EFI motorcycle, multi-cylinder petrol car, EV, ... | A few, written once | Engineering knowledge |
| 3. Model profile | Parameters (gear ratios, thermostat temperature, charging band, mass, wheelbase, tyre size) and the signal mapping (which CAN ID / DID / OBD PID carries which VSS path) | Once per vehicle model | Service manual, spec sheet, DBC |
| 4. Unit baseline | The individual vehicle's own parameters (battery, warm-up curve, wear) | Per vehicle, automatic | First N rides |

- Layer 2 gives absolute health ("weak against the model's band"), layer 4 gives change over time ("degrading against its own past").
- Adding a vehicle model = writing a layer-3 profile, not training a new model. VSS already gives the vehicle-independent signal names; `uds/obd_catalog.yaml` (D-078) already gives the standard OBD-II signals most cars share.
- The CL250 files (`vehicle/cl250_constants.yaml`, `uds/vehicle_cl250.yaml`, `derived/cl250_derived.yaml`) are the first layer-3 profile and stay vehicle-specific (D-078); the missing piece is a layer-2 class template beside them.
- Chassis: IMU-based, needs an automatic mounting-orientation calibration on the first ride.
- Cross-vehicle learning: confirmed edges and validated cases from one model are offered to models of the same class as candidates.
- Business note (not a technical decision): with an OEM the DBC and specs come from the OEM, so a model profile is cheap; aftermarket means reverse-engineering each model, so it should stay on standard OBD-II signals for cars and a few chosen motorcycle models.
- Thesis evidence for generality: one short demo on a second vehicle (a car over OBD-II) that changes only the profile.

## 7. Proposed decision text (move into `DECISIONS.md` after the user's approval)

**D-xxx — Untagged anomalies are localised on a hybrid relationship graph, reasoned about by the LLM as evidence-bound hypotheses and validated with the rider; validated cases feed the catalog; the design is layered for other vehicles** (2026-10-27, user: wants an anomaly that is not tagged to be noticed in vehicle-mcp through its related data structures, interpreted from those relations, explained to the rider and validated by interacting with the rider; chose the hybrid graph; wants the system to scale to other vehicle types; D-078, D-083, D-084, D-085, invariants 2, 3, 4 and 7)
1. **Graph.** A relationship graph over defs signals: static edges from physics and the D-083 level-1 models, learned edges as candidates, promoted only by a validated case or a cited source.
2. **Tools.** vehicle-mcp computes detection scores and broken edges with their evidence; the LLM gets tool results only (invariant 7).
3. **Amends D-084 item 3.** With no catalog match the LLM returns ranked hypotheses bound to broken edges and their evidence, labelled as hypotheses, plus a validation dialogue, instead of only "unidentified anomaly". The catalog remains the first knowledge source.
4. **Learning loop.** A case closed by data evidence or a service result becomes a catalog entry or evidence (via `/signal-change`), a HIL scenario and a vehicle-ml label.
5. **Layers.** Physics, class template, model profile, unit baseline (§6); vehicle facts stay in per-vehicle files (D-078).
6. **Limits.** QM advice only, never a safety-partition input (invariant 3); critical warnings never wait for the LLM (D-085 item 4); no dialogue while riding.
- Not chosen: tag-only detection (cannot see unknown faults, no difference from a scan tool with an LLM); a free LLM diagnosis from raw data (unverifiable); one model trained per vehicle (does not scale).
- Why: it detects what nobody tagged, keeps every claim tied to computed evidence, produces its own labelled data, and makes a new vehicle model a profile instead of a project.
