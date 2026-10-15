"""derived/cl250_derived.yaml (D-070 item 3)."""

import copy

import pytest

from moto_codegen import config, derived, gen_ble, gen_c, gen_python
from moto_codegen.dbc_checks import load_dbc
from moto_codegen.derived import check_derived
from moto_codegen.yaml_checks import load_yaml


@pytest.fixture(scope="module")
def refs():
    return {
        "vehicle": load_yaml(config.VEHICLE_YAML),
        "constants": load_yaml(config.VEHICLE_CONSTANTS_YAML),
        "ble": gen_ble.load_schema(),
        "db": load_dbc(config.PLATFORM_DBC),
        "dids": load_yaml(config.DIDS_YAML),
    }


@pytest.fixture
def doc():
    return copy.deepcopy(load_yaml(config.DERIVED_YAML))


def _check(doc, refs, dids=None):
    return check_derived(
        doc, refs["vehicle"], refs["constants"], refs["ble"], refs["db"], dids or refs["dids"]
    )


def _has(errors, *parts):
    return any(all(p in e for p in parts) for e in errors)


def _add(doc, name, **fields):
    base = {
        "class": "A",
        "description": "test signal",
        "catalog": "Longitudinal acceleration, jerk",
        "unit": "m/s2",
        "range": [-10.0, 10.0],
        "resolution": 0.01,
        "inputs": ["did.VEHICLE_SPEED"],
        "period_ms": 110,
        "stale_after_ms": 330,
        "output": ["log"],
    }
    doc["signals"][name] = {k: v for k, v in {**base, **fields}.items() if v is not None}


def test_committed_definitions_are_consistent(doc, refs):
    assert _check(doc, refs) == []


@pytest.mark.parametrize(
    "ref", ["did.NOT_A_DID", "sensor.not_a_sensor", "const.not_a_constant", "can.EkfLean"]
)
def test_an_input_must_be_defined_in_defs(doc, refs, ref):
    _add(doc, "t_sig", inputs=["did.VEHICLE_SPEED", ref])
    assert _has(_check(doc, refs), "t_sig", ref, "not defined")


def test_a_derived_input_must_be_defined_above(doc, refs):
    first = next(iter(doc["signals"]))
    doc["signals"][first]["inputs"].append("derived.trip_distance")
    _add(doc, "t_self", inputs=["derived.t_self"])
    errors = _check(doc, refs)
    assert _has(errors, first, "derived.trip_distance", "defined above")
    assert _has(errors, "t_self", "defined above")


def test_class_rules(doc, refs):
    _add(doc, "t_live_from_ride", inputs=["derived.ride_distance"])
    _add(
        doc,
        "t_trend_from_did",
        **{"class": "C", "output": ["server"], "period_ms": None, "stale_after_ms": None},
    )
    _add(doc, "t_bad_output", output=["log", "can"])
    _add(
        doc,
        "t_d_without_pending",
        **{"class": "D", "output": ["server"], "period_ms": None, "stale_after_ms": None},
    )
    errors = _check(doc, refs)
    assert _has(errors, "t_live_from_ride", "class A cannot use class-B")
    assert _has(errors, "t_trend_from_did", "class C uses class-B/C signals only")
    assert _has(errors, "t_bad_output", "output must be ['log']")
    assert _has(errors, "t_d_without_pending", "pending_inputs")


@pytest.mark.parametrize(
    "fields, message",
    [
        ({"period_ms": 50, "stale_after_ms": 150}, "faster than its fastest input (110 ms)"),
        (
            {"inputs": ["sensor.imu_accel_x"], "period_ms": 10, "stale_after_ms": 30},
            "period_ms must be",
        ),  # fmt: skip
        ({"stale_after_ms": 100}, "stale_after_ms must be"),
        ({"period_ms": None}, "exactly one of period_ms and event"),
        ({"period_ms": None, "event": True}, "an event has no stale_after_ms"),
        ({"window_ms": 0}, "window_ms"),
        ({"window_ms": 65536}, "window_ms"),
    ],
)
def test_live_timing(doc, refs, fields, message):
    _add(doc, "t_timing", **fields)
    assert _has(_check(doc, refs), "t_timing", message)


def test_ride_summary_records(doc, refs):
    ride = doc["signals"]["ride_distance"]
    del ride["record"]
    assert _has(_check(doc, refs), "ride_distance", "needs a record")
    ride["record"] = "RIDE_USAGE"
    doc["ride_summary_records"]["RIDE_USAGE"]["did"] = 0xFD3F
    assert _has(_check(doc, refs), "RIDE_USAGE", "0xFD40-0xFD5F")
    doc["ride_summary_records"]["RIDE_USAGE"]["did"] = 0xFD40
    doc["ride_summary_records"]["RIDE_EXTRA"] = {"did": 0xFD40, "description": "x"}
    assert _has(_check(doc, refs), "RIDE_EXTRA", "also used by RIDE_USAGE")
    doc["ride_summary_records"]["RIDE_EXTRA"]["did"] = 0xFD5F
    assert _has(_check(doc, refs), "RIDE_EXTRA", "no class-B signal")


def test_a_record_did_never_reuses_an_rt_core_did(doc, refs):
    dids = copy.deepcopy(refs["dids"])
    did = doc["ride_summary_records"]["RIDE_USAGE"]["did"]
    dids["nodes"]["RT_CORE"]["dids"].append({"did": did, "name": "TAKEN"})
    assert _has(_check(doc, refs, dids), "RIDE_USAGE", "already an rt-core DID")


def test_sensor_sources_resolve(doc, refs):
    s = doc["sensors"]
    s["imu_accel_x"]["phase0"] = "ble.imuBlock.bx"
    s["lean_angle"]["rt_core"] = "can.EkfLean.NOT_A_SIGNAL"
    s["can_bus_off_count"]["rt_core"] = "uds.RT_CORE_HEALTH.NOT_A_FIELD"
    s["gps_heading"]["phase0"] = None
    errors = _check(doc, refs)
    assert _has(errors, "imu_accel_x", "not a ble/ble_schema.json field")
    assert _has(errors, "lean_angle", "not a platform.dbc signal")
    assert _has(errors, "can_bus_off_count", "uds.<DID>.<FIELD>")
    assert _has(errors, "gps_heading", "defined nowhere")


def test_units_ranges_and_catalog(doc, refs):
    _add(doc, "t_unit", unit="furlong")
    _add(doc, "t_range", range=[5.0, 5.0])
    _add(doc, "t_res", resolution=50.0)
    _add(doc, "t_catalog", catalog="Not a catalog row")
    errors = _check(doc, refs)
    assert _has(errors, "t_unit", "furlong")
    assert _has(errors, "t_range", "min < max")
    assert _has(errors, "t_res", "resolution")
    assert _has(errors, "t_catalog", "not a row of catalog section 5")


def test_bins(doc, refs):
    _add(doc, "t_bins", bins=[{"input": "did.ENGINE_SPEED", "min": 0.0, "max": 1.0, "count": 4}])
    assert _has(_check(doc, refs), "t_bins", "input must be one of inputs")


def test_readiness_follows_sensor_sources_and_pending_inputs(doc, refs):
    _add(doc, "t_imu", inputs=["sensor.imu_accel_x"], period_ms=20, stale_after_ms=60)
    _add(doc, "t_lean", inputs=["sensor.lean_angle"], period_ms=100, stale_after_ms=300)
    _add(doc, "t_pending", pending_inputs=["0xA6 odometer (catalog 2.1, not defined)"])
    _add(doc, "t_chain", inputs=["derived.t_imu"], period_ms=20, stale_after_ms=60)
    assert _check(doc, refs) == []
    assert derived.ready(doc, "t_imu", "phase0") and not derived.ready(doc, "t_imu", "rt_core")
    assert derived.ready(doc, "t_lean", "phase0") and derived.ready(doc, "t_lean", "rt_core")
    assert not derived.ready(doc, "t_pending", "phase0")
    assert not derived.ready(doc, "t_chain", "rt_core")


def test_generated_c_holds_classes_a_and_b_only(doc, refs):
    files = gen_c.generate_derived_c(doc, refs["constants"])
    h, c = files["vehicle_cl250_derived.h"], files["vehicle_cl250_derived.c"]
    names = derived.rt_core_signals(doc)
    assert f"#define VEHICLE_CL250_DERIVED_COUNT ({len(names)}u)" in h
    for name, sig in doc["signals"].items():
        assert (f"VEHICLE_CL250_DERIVED_{name.upper()} (" in h) == (sig["class"] in "AB")
        assert (f"/* {name} [" in c) == (sig["class"] in "AB")
    for key, rec in doc["ride_summary_records"].items():
        assert f"({rec['did']:#06X}u)".replace("0X", "0x") in h, key
    assert "const." not in c


def test_histogram_element_count(doc, refs):
    sig = doc["signals"]["operating_point_time"]
    assert derived.element_count(sig, refs["constants"]) == 16 * 16
    sig["per_gear"] = True
    assert derived.element_count(sig, refs["constants"]) == 16 * 16 * 6


def test_python_module_carries_every_class_and_readiness(doc):
    py = gen_python.generate_derived_py(doc)
    ns: dict = {}
    exec(compile(py, "vehicle_derived.py", "exec"), ns)
    assert set(ns["SIGNALS"]) == set(doc["signals"])
    assert set(ns["SENSORS"]) == set(doc["sensors"])
    for name, sig in ns["SIGNALS"].items():
        assert sig["ready_phase0"] == derived.ready(doc, name, "phase0")
        assert sig["ready_rt_core"] == derived.ready(doc, name, "rt_core")


def test_only_rt_core_gets_the_derived_table():
    assert [t.node for t in config.C_TARGETS if t.vehicle_constants] == ["RT_CORE"]
