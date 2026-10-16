"""derived/cl250_derived.yaml (D-070 item 3): checks and the helpers codegen needs.

Definitions only: every input must resolve to something defs already defines
(invariant 2), class rules follow D-070 item 1 and the ride-summary DIDs stay in the
rt-core block reserved by uds/dids.yaml (item 4).
"""

from __future__ import annotations

import math
import re
from typing import Any

from cantools.database.can import Database

from . import config

DERIVED_CLASSES = ("A", "B", "C", "D")
# Class -> the only allowed `output` list (D-070 item 4: no CAN or VSS without a consumer).
DERIVED_OUTPUT = {"A": ["log"], "B": ["log", "ride_summary"], "C": ["server"], "D": ["server"]}
# Derived inputs each class may use: live values never wait for a ride to close.
DERIVED_INPUT_CLASSES = {"A": ("A",), "B": ("A", "B"), "C": ("B", "C"), "D": ("A", "B", "C", "D")}
RECORD_DID_MIN = 0xFD40  # uds/dids.yaml: rt-core block for the class-B ride summaries
RECORD_DID_MAX = 0xFD5F
MIN_PERIOD_MS = 20  # 50 Hz at most (D-070 item 1)
U16_MAX = 0xFFFF  # period_ms, stale_after_ms and the element count are uint16_t in C
AXIS_MAX = 2  # bins: at most a 2-D map (operating points, trim cells)
DERIVED_UNITS = frozenset({
    "", "enum", "flag", "count", "%", "ratio",
    "s", "ms", "min", "h", "day",
    "m", "km", "m/s", "km/h", "m/s2", "m/s3", "deg", "deg/s", "1/s", "1/m", "1/km",
    "rpm", "Nm", "kW", "N", "kg/m", "m2",
    "degC", "degC/s", "degC/min", "kPa", "kg/m3", "V", "V/day",
    "g/s", "L/h", "L", "L/100km", "km/L", "mg", "g/kWh", "count/krev",
})  # fmt: skip

SIGNAL_REQUIRED = (
    "class",
    "description",
    "catalog",
    "unit",
    "range",
    "resolution",
    "inputs",
    "output",
)
SIGNAL_OPTIONAL = (
    "pending_inputs",
    "period_ms",
    "event",
    "window_ms",
    "stale_after_ms",
    "bins",
    "per_gear",
    "record",
)
SENSOR_KEYS = {"description", "unit", "sample_period_ms", "stale_after_ms", "phase0", "rt_core"}
RECORD_KEYS = {"did", "description"}
BLE_GROUPS = ("telemetry", "imuBlock", "gpsBlock")

_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
_UPPER = re.compile(r"^[A-Z][A-Z0-9_]*$")


# --------------------------------------------------------------------------- resolvers


def ble_fields(ble: dict[str, Any]) -> set[str]:
    """`<group>.<field>` names a sensor's phase0 source may use."""
    out = {f"telemetry.{f['name']}" for f in ble["fields"]}
    out |= {f"imuBlock.{f['name']}" for f in ble["imuBlock"]["sampleFields"]}
    out |= {f"gpsBlock.{f['name']}" for f in ble["gpsBlock"]["fields"]}
    return out


def rt_core_did_fields(dids_doc: dict[str, Any]) -> set[str]:
    """`<DID>` and `<DID>.<FIELD>` of rt-core's own UDS DIDs (uds/dids.yaml)."""
    out: set[str] = set()
    for d in dids_doc["nodes"]["RT_CORE"]["dids"]:
        out.add(d["name"])
        out |= {f"{d['name']}.{f['name']}" for f in d.get("fields", [])}
    return out


def rt_core_dids(dids_doc: dict[str, Any]) -> set[int]:
    return {d["did"] for d in dids_doc["nodes"]["RT_CORE"]["dids"]}


def catalog_rows() -> set[str]:
    """First cells of the catalog section 5 tables (docs/vehicle-data-catalog.md)."""
    rows: set[str] = set()
    inside = False
    for line in config.CATALOG_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.startswith("## 5.")
        elif inside and line.startswith("| ") and not line.startswith("| ---"):
            rows.add(line.split("|")[1].strip())
    return rows


def split_ref(ref: str) -> tuple[str, str]:
    kind, _, name = ref.partition(".")
    return kind, name


def input_period_ms(ref: str, doc: dict[str, Any], vehicle: dict[str, Any]) -> int | None:
    """Sample period of an input, None if it has none (constant, event, per ride)."""
    kind, name = split_ref(ref)
    if kind == "did":
        return next(d["poll_period_ms"] for d in vehicle["dids"] if d["name"] == name)
    if kind == "sensor":
        return doc["sensors"][name]["sample_period_ms"]
    if kind == "derived":
        return doc["signals"][name].get("period_ms")
    return None


def ready(doc: dict[str, Any], name: str, where: str) -> bool:
    """True if every input of signal `name` is defined for `where` (phase0 | rt_core)."""
    sig = doc["signals"][name]
    if sig.get("pending_inputs"):
        return False
    if where == "rt_core" and sig["class"] not in ("A", "B"):
        return False
    for ref in sig["inputs"]:
        kind, ref_name = split_ref(ref)
        if kind == "sensor" and doc["sensors"][ref_name][where] is None:
            return False
        if kind == "derived" and not ready(doc, ref_name, where):
            return False
    return True


def rt_core_signals(doc: dict[str, Any]) -> list[str]:
    """Classes A and B in file order: the rt-core table (C/D are server-side)."""
    return [n for n, s in doc["signals"].items() if s["class"] in ("A", "B")]


def element_count(sig: dict[str, Any], constants: dict[str, Any]) -> int:
    """Values one signal holds: bins per axis x gears (1 = a scalar)."""
    n = math.prod(b["count"] for b in sig.get("bins", []))
    if sig.get("per_gear"):
        n *= constants["constants"]["gear_count"]["value"]
    return n


# --------------------------------------------------------------------------- checks


def _is_real(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _is_pos_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _check_sensors(
    doc: dict[str, Any], ble: set[str], db: Database, rt_dids: set[str]
) -> list[str]:
    errors: list[str] = []
    sensors = doc.get("sensors")
    if not isinstance(sensors, dict) or not sensors:
        return ["derived: `sensors` must be a non-empty mapping"]
    for key, s in sensors.items():
        where = f"derived sensor {key}"
        if not isinstance(key, str) or not _SNAKE.match(key):
            errors.append(f"{where}: key must be snake_case")
        if not isinstance(s, dict) or set(s) != SENSOR_KEYS:
            errors.append(f"{where}: needs exactly {sorted(SENSOR_KEYS)}")
            continue
        if s["unit"] not in DERIVED_UNITS:
            errors.append(f"{where}: unit {s['unit']!r} not in DERIVED_UNITS")
        period, stale = s["sample_period_ms"], s["stale_after_ms"]
        if not _is_pos_int(period) or not _is_pos_int(stale) or stale > U16_MAX:
            errors.append(f"{where}: sample_period_ms and stale_after_ms must be integers > 0")
        elif stale < period:
            errors.append(f"{where}: stale_after_ms < sample_period_ms (never valid)")
        src0, src_rt = s["phase0"], s["rt_core"]
        if src0 is None and src_rt is None:
            errors.append(f"{where}: defined nowhere (phase0 and rt_core are both null)")
        if src0 is not None:
            kind, name = split_ref(str(src0))
            if kind != "ble" or name not in ble:
                errors.append(f"{where}: phase0 {src0!r} is not a ble/ble_schema.json field")
        if src_rt is not None:
            kind, name = split_ref(str(src_rt))
            if kind == "can":
                msg, _, sig = name.partition(".")
                try:
                    db.get_message_by_name(msg).get_signal_by_name(sig)
                except KeyError:
                    errors.append(f"{where}: rt_core {src_rt!r} is not a platform.dbc signal")
            elif kind != "uds" or name not in rt_dids:
                errors.append(
                    f"{where}: rt_core {src_rt!r} must be can.<Msg>.<SIG> or uds.<DID>.<FIELD>"
                )
    return errors


def _check_records(doc: dict[str, Any], used_dids: set[int]) -> list[str]:
    errors: list[str] = []
    records = doc.get("ride_summary_records")
    if not isinstance(records, dict) or not records:
        return ["derived: `ride_summary_records` must be a non-empty mapping"]
    seen: dict[int, str] = {}
    for key, r in records.items():
        where = f"derived record {key}"
        if not isinstance(key, str) or not _UPPER.match(key):
            errors.append(f"{where}: key must be UPPER_SNAKE_CASE")
        if not isinstance(r, dict) or set(r) != RECORD_KEYS:
            errors.append(f"{where}: needs exactly {sorted(RECORD_KEYS)}")
            continue
        did = r["did"]
        if not _is_pos_int(did) or not RECORD_DID_MIN <= did <= RECORD_DID_MAX:
            errors.append(f"{where}: did must be in 0x{RECORD_DID_MIN:04X}-0x{RECORD_DID_MAX:04X}")
        elif did in seen:
            errors.append(f"{where}: did 0x{did:04X} also used by {seen[did]}")
        elif did in used_dids:
            errors.append(f"{where}: did 0x{did:04X} is already an rt-core DID in uds/dids.yaml")
        else:
            seen[did] = key
    return errors


def _check_signal(
    name: str,
    sig: dict[str, Any],
    doc: dict[str, Any],
    earlier: dict[str, str],
    known: dict[str, set[str]],
    vehicle: dict[str, Any],
    catalog: set[str],
) -> list[str]:
    where = f"derived {name}"
    errors: list[str] = []
    missing = [k for k in SIGNAL_REQUIRED if k not in sig]
    extra = sorted(set(sig) - set(SIGNAL_REQUIRED) - set(SIGNAL_OPTIONAL))
    if missing or extra:
        return [f"{where}: missing {missing}, unknown {extra}"]
    cls = sig["class"]
    if cls not in DERIVED_CLASSES:
        return [f"{where}: class must be one of {DERIVED_CLASSES}"]
    if not isinstance(sig["description"], str) or not sig["description"].strip():
        errors.append(f"{where}: description must be text")
    if sig["catalog"] not in catalog:
        errors.append(f"{where}: catalog {sig['catalog']!r} is not a row of catalog section 5")
    if sig["unit"] not in DERIVED_UNITS:
        errors.append(f"{where}: unit {sig['unit']!r} not in DERIVED_UNITS")
    rng, res = sig["range"], sig["resolution"]
    if (
        not (isinstance(rng, list) and len(rng) == 2 and all(_is_real(v) for v in rng))
        or rng[0] >= rng[1]
    ):
        errors.append(f"{where}: range must be [min, max] with min < max")
    elif not _is_real(res) or res <= 0 or res > rng[1] - rng[0]:
        errors.append(f"{where}: resolution must be > 0 and within the range")
    if sig["output"] != DERIVED_OUTPUT[cls]:
        errors.append(f"{where}: class {cls} output must be {DERIVED_OUTPUT[cls]}")

    pending = sig.get("pending_inputs", [])
    if not isinstance(pending, list) or not all(isinstance(p, str) and p.strip() for p in pending):
        errors.append(f"{where}: pending_inputs must be a list of text")
        pending = []
    inputs = sig["inputs"]
    if not isinstance(inputs, list) or not all(isinstance(i, str) for i in inputs):
        return errors + [f"{where}: inputs must be a list of references"]
    if not inputs and not pending:
        errors.append(f"{where}: no inputs and no pending_inputs")
    if len(set(inputs)) != len(inputs):
        errors.append(f"{where}: duplicate inputs")
    for ref in inputs:
        kind, ref_name = split_ref(ref)
        if kind == "derived":
            if ref_name == name or ref_name not in earlier:
                errors.append(f"{where}: input {ref} must be a signal defined above it")
            elif earlier[ref_name] not in DERIVED_INPUT_CLASSES[cls]:
                errors.append(f"{where}: class {cls} cannot use class-{earlier[ref_name]} {ref}")
        elif kind not in known or ref_name not in known[kind]:
            errors.append(f"{where}: input {ref} is not defined in moto-vehicle-defs")
        elif cls == "C" and kind != "const":
            errors.append(f"{where}: class C uses class-B/C signals only, not {ref}")
    if cls == "D" and not pending:
        errors.append(f"{where}: class D names its off-vehicle inputs in pending_inputs")
    if errors:
        return errors

    errors += _check_timing(where, sig, doc, vehicle)
    for i, b in enumerate(sig.get("bins", [])):
        if not isinstance(b, dict) or set(b) != {"input", "min", "max", "count"}:
            errors.append(f"{where}: bins[{i}] needs exactly input, min, max, count")
        elif b["input"] not in inputs or not _is_pos_int(b["count"]):
            errors.append(f"{where}: bins[{i}] input must be one of inputs, count > 0")
        elif not (_is_real(b["min"]) and _is_real(b["max"]) and b["min"] < b["max"]):
            errors.append(f"{where}: bins[{i}] needs min < max")
    if "bins" in sig and not 1 <= len(sig["bins"]) <= AXIS_MAX:
        errors.append(f"{where}: bins has 1 to {AXIS_MAX} axes")
    if "per_gear" in sig and sig["per_gear"] is not True:
        errors.append(f"{where}: per_gear is true or absent")
    if cls == "B":
        if sig.get("record") not in doc.get("ride_summary_records", {}):
            errors.append(f"{where}: class B needs a record of ride_summary_records")
    elif "record" in sig:
        errors.append(f"{where}: only class B has a record")
    return errors


def _check_timing(
    where: str, sig: dict[str, Any], doc: dict[str, Any], vehicle: dict[str, Any]
) -> list[str]:
    cls, period, event = sig["class"], sig.get("period_ms"), sig.get("event")
    stale, window = sig.get("stale_after_ms"), sig.get("window_ms")
    if window is not None and (not _is_pos_int(window) or window > U16_MAX):
        return [f"{where}: window_ms must be an integer in 1..{U16_MAX}"]
    if cls != "A":
        if period is not None or event is not None or stale is not None:
            return [f"{where}: period_ms, event and stale_after_ms are class A only"]
        return []
    if event is not None and event is not True:
        return [f"{where}: event is true or absent"]
    if (period is None) == (event is None):
        return [f"{where}: class A needs exactly one of period_ms and event"]
    if event:
        if stale is not None:
            return [f"{where}: an event has no stale_after_ms"]
        return []
    if not _is_pos_int(period) or not MIN_PERIOD_MS <= period <= U16_MAX:
        return [f"{where}: period_ms must be an integer in {MIN_PERIOD_MS}..{U16_MAX}"]
    if not _is_pos_int(stale) or not period <= stale <= U16_MAX:
        return [f"{where}: stale_after_ms must be an integer in period_ms..{U16_MAX}"]
    periods = [p for ref in sig["inputs"] if (p := input_period_ms(ref, doc, vehicle)) is not None]
    if periods and period < min(periods):
        return [f"{where}: period_ms {period} is faster than its fastest input ({min(periods)} ms)"]
    # The output is only as fresh as its slowest input: a stale_after_ms below that
    # input's period would call an output fresh while it carries an older sample.
    if periods and stale < max(periods):
        slowest = max(periods)
        return [
            f"{where}: stale_after_ms {stale} is below its slowest input's period ({slowest} ms)"
        ]
    return []


def check_derived(
    doc: dict[str, Any],
    vehicle: dict[str, Any],
    constants: dict[str, Any],
    ble: dict[str, Any],
    platform_db: Database,
    dids_doc: dict[str, Any],
) -> list[str]:
    """derived/cl250_derived.yaml against the files its references point into."""
    if doc.get("schema_version") != 1:
        return ["derived: schema_version must be 1"]
    errors = _check_sensors(doc, ble_fields(ble), platform_db, rt_core_did_fields(dids_doc))
    errors += _check_records(doc, rt_core_dids(dids_doc))
    signals = doc.get("signals")
    if not isinstance(signals, dict) or not signals:
        return errors + ["derived: `signals` must be a non-empty mapping"]
    if errors:
        return errors
    known = {
        "did": {d["name"] for d in vehicle["dids"]},
        "sensor": set(doc["sensors"]),
        "const": set(constants["constants"]),
    }
    catalog = catalog_rows()
    earlier: dict[str, str] = {}
    used_records: set[str] = set()
    for name, sig in signals.items():
        if not isinstance(name, str) or not _SNAKE.match(name):
            errors.append(f"derived {name}: key must be snake_case")
        if not isinstance(sig, dict):
            errors.append(f"derived {name}: must be a mapping")
            continue
        errors += _check_signal(name, sig, doc, earlier, known, vehicle, catalog)
        if sig.get("class") in DERIVED_CLASSES:
            earlier[name] = sig["class"]
        if isinstance(sig.get("record"), str):
            used_records.add(sig["record"])
    for key in doc["ride_summary_records"]:
        if key not in used_records:
            errors.append(f"derived record {key}: no class-B signal reports in it")
    if errors:
        return errors
    for name in rt_core_signals(doc):
        n = element_count(signals[name], constants)
        if n > U16_MAX:
            errors.append(f"derived {name}: {n} elements do not fit uint16_t")
        if len(signals[name]["inputs"]) > 255:
            errors.append(f"derived {name}: more than 255 inputs")
    return errors
