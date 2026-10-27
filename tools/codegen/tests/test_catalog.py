"""D-066, D-078 item 2: OBD/UDS catalog checks and the generated Python/Dart catalog."""

import copy
import importlib.util
import re

import pytest

from vehicle_codegen import config, gen_catalog
from vehicle_codegen.cli import render_all
from vehicle_codegen.yaml_checks import load_yaml

# Two scalar entries for the schema checks, in place of the committed list (test data,
# never generated).
SAMPLE = [
    {"obd_pid": 0x2C, "did": 0xF42C, "name": "COMMANDED_EGR", "label": "EGR", "group": "air",
     "length": 1, "factor_num": 100, "factor_den": 255, "offset": 0, "unit": "%", "min": 0,
     "max": 100, "description": "Commanded EGR."},
    {"obd_pid": 0x2D, "did": 0xF42D, "name": "EGR_ERROR", "label": "EGR error", "group": "air",
     "length": 1, "factor_num": 100, "factor_den": 128, "offset": -100, "unit": "%",
     "min": -100, "max": 99.21875, "description": "EGR error."},
]  # fmt: skip


@pytest.fixture
def committed():
    return copy.deepcopy(load_yaml(config.OBD_CATALOG_YAML))


@pytest.fixture
def cand(committed):
    committed["candidates"] = copy.deepcopy(SAMPLE)
    return committed


def _errors(cand, vehicle):
    return gen_catalog.check_catalog(cand, vehicle)


def test_committed_catalog_is_clean(committed, vehicle):
    assert _errors(committed, vehicle) == []
    polled = {d["name"] for d in vehicle["dids"]}
    assert polled.isdisjoint(e["name"] for e in committed["candidates"])  # D-078 item 2


def test_sample_catalog_is_clean(cand, vehicle):
    assert _errors(cand, vehicle) == []


def test_candidates_must_be_a_list(committed, vehicle):
    del committed["candidates"]
    assert any("must be a list" in e for e in _errors(committed, vehicle))


def test_every_candidate_is_an_allowed_0x22_read(cand, vehicle):
    for e in cand["candidates"]:
        assert e["did"] == 0xF400 | e["obd_pid"]


@pytest.mark.parametrize("key", ["poll_period_ms", "stale_after_ms", "priority"])
def test_poll_settings_are_refused(cand, vehicle, key):
    cand["candidates"][0][key] = 1000
    assert any("never polled" in e for e in _errors(cand, vehicle))


def test_wrong_did_is_refused(cand, vehicle):
    cand["candidates"][0]["did"] = 0xF4FF
    assert any("0xF400 | obd_pid" in e for e in _errors(cand, vehicle))


def test_support_pid_is_refused(cand, vehicle):
    cand["candidates"][0].update(obd_pid=0x20, did=0xF420)
    assert any("support PID" in e for e in _errors(cand, vehicle))


def test_polled_did_cannot_be_a_candidate(cand, vehicle):
    cand["candidates"][0].update(obd_pid=0x0C, did=0xF40C)
    assert any("already listed" in e for e in _errors(cand, vehicle))


def test_duplicate_name_is_refused(cand, vehicle):
    cand["candidates"][1]["name"] = cand["candidates"][0]["name"]
    assert any("name already used" in e for e in _errors(cand, vehicle))


def test_range_must_follow_the_formula(cand, vehicle):
    cand["candidates"][0]["max"] = cand["candidates"][0]["max"] + 1
    assert any("max" in e and "formula" in e for e in _errors(cand, vehicle))
    cand["candidates"] = copy.deepcopy(SAMPLE)
    cand["candidates"][0]["min"] = 1
    assert any("min" in e and "formula" in e for e in _errors(cand, vehicle))


def test_unknown_group_is_refused(cand, vehicle):
    cand["candidates"][0]["group"] = "nope"
    assert any("group 'nope'" in e for e in _errors(cand, vehicle))


def test_polled_metadata_must_match_the_did_table(cand, vehicle):
    del cand["polled"]["ENGINE_SPEED"]
    assert any("`polled` keys" in e for e in _errors(cand, vehicle))


def test_a_read_the_policy_refuses_is_reported(cand, vehicle):
    vehicle["tester_policy"]["allowed"] = [
        e for e in vehicle["tester_policy"]["allowed"] if e["sid"] != 0x22
    ]
    assert any("tester_policy" in e for e in _errors(cand, vehicle))


def test_catalog_has_polled_first_then_candidates(cand, vehicle):
    cat = gen_catalog.catalog(cand, vehicle)
    polled = [e["name"] for e in cat if e["status"] == "polled"]
    assert polled == [d["name"] for d in vehicle["dids"]]
    assert all(e["status"] == "candidate" for e in cat[len(polled) :])
    assert all(e["poll_period_ms"] is None and e["priority"] is None for e in cat[len(polled) :])
    assert len(cat) == len(vehicle["dids"]) + len(cand["candidates"])


def test_no_c_target_gets_the_catalog():
    files = render_all(with_vss=False)
    c_text = "".join(t for rel, t in files.items() if rel.parts[0] == "c")
    for e in load_yaml(config.OBD_CATALOG_YAML)["candidates"]:
        # a whole identifier: derived names such as RIDE_ODOMETER_MISMATCH contain others
        assert not re.search(rf"\b{e['name']}\b", c_text), e["name"]
    assert "obd_catalog" not in c_text


def test_generated_python_decodes(tmp_path):
    path = config.GEN_DIR / "python" / "vehicle_defs" / "vehicle_catalog.py"
    spec = importlib.util.spec_from_file_location("vehicle_catalog", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.decode("ENGINE_SPEED", bytes([0x0F, 0xA0])) == 1000.0
    assert mod.decode("SHORT_TERM_FUEL_TRIM_B1", bytes([128])) == 0.0
    assert mod.decode("TIMING_ADVANCE", bytes([128])) == 0.0
    assert mod.decode("INTAKE_AIR_TEMP", bytes([60])) == 20.0
    assert mod.SIGNALS["INTAKE_MAP"]["status"] == mod.STATUS_POLLED  # D-068
    assert mod.SIGNALS["INTAKE_MAP"]["poll_period_ms"] == 2000
    assert mod.SIGNALS["VEHICLE_SPEED"]["status"] == mod.STATUS_POLLED
    assert mod.BY_DID[0xF40B] == "INTAKE_MAP"


def test_generated_dart_lists_every_signal(committed, vehicle):
    text = (config.GEN_DIR / "dart" / "vehicle_defs" / "lib" / "vehicle_signals.dart").read_text()
    for e in gen_catalog.catalog(committed, vehicle):
        assert f"name: '{e['name']}'" in text
        assert f"did: 0x{e['did']:04X}" in text
    barrel = (config.GEN_DIR / "dart" / "vehicle_defs" / "lib" / "vehicle_defs.dart").read_text()
    assert "export 'vehicle_signals.dart';" in barrel


# --- D-068 multi-value entries (`fields`) ---

MULTI = (
    "MONITOR_STATUS FUEL_SYSTEM_STATUS SECONDARY_AIR_STATUS O2_SENSORS_PRESENT_2B "
    "O2_SENSORS_PRESENT_4B OBD_STANDARD AUX_INPUT_STATUS FUEL_TYPE"
).split() + [f"O2_S{i}{kind}" for kind in ("", "_WR_VOLTAGE", "_WR_CURRENT") for i in range(1, 9)]


def _entry(cand, name):
    return next(e for e in cand["candidates"] if e["name"] == name)


def _field(cand, name, field):
    return next(f for f in _entry(cand, name)["fields"] if f["name"] == field)


@pytest.fixture(scope="module")
def mod():
    path = config.GEN_DIR / "python" / "vehicle_defs" / "vehicle_catalog.py"
    spec = importlib.util.spec_from_file_location("vehicle_catalog_multi", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_multi_value_pid_of_d068_is_defined(committed):
    by_name = {e["name"]: e for e in committed["candidates"]}
    assert all("fields" in by_name[n] for n in MULTI)
    assert {by_name[n]["obd_pid"] for n in MULTI} == (
        {0x01, 0x03, 0x12, 0x13, 0x1C, 0x1D, 0x1E, 0x51}
        | set(range(0x14, 0x1C))
        | set(range(0x24, 0x2C))
        | set(range(0x34, 0x3C))
    )


def test_fields_may_not_share_a_bit(committed, vehicle):
    _field(committed, "FUEL_SYSTEM_STATUS", "FUEL_SYSTEM_2")["byte"] = 0
    assert any("shares a bit" in e for e in _errors(committed, vehicle))
    committed = copy.deepcopy(load_yaml(config.OBD_CATALOG_YAML))
    _field(committed, "MONITOR_STATUS", "READINESS_B_LOW")["bits"] = 4  # runs into bit 3
    assert any("shares a bit" in e for e in _errors(committed, vehicle))


def test_fields_must_lie_inside_length(committed, vehicle):
    _field(committed, "FUEL_SYSTEM_STATUS", "FUEL_SYSTEM_2")["byte"] = 2
    assert any("leaves length 2" in e for e in _errors(committed, vehicle))


def test_sub_byte_field_must_stay_in_its_byte(committed, vehicle):
    _field(committed, "AUX_INPUT_STATUS", "PTO_ACTIVE")["bits"] = 9
    assert any("leaves the byte" in e for e in _errors(committed, vehicle))


def test_field_needs_size_or_bit_and_bits(committed, vehicle):
    del _field(committed, "AUX_INPUT_STATUS", "PTO_ACTIVE")["bits"]
    assert any("either size, or bit and bits" in e for e in _errors(committed, vehicle))


def test_field_range_must_follow_the_formula(committed, vehicle):
    _field(committed, "O2_SENSORS_PRESENT_2B", "PRESENT")["max"] = 254
    assert any("max 254" in e and "formula" in e for e in _errors(committed, vehicle))
    committed = copy.deepcopy(load_yaml(config.OBD_CATALOG_YAML))
    _field(committed, "O2_S1", "VOLTAGE")["min"] = 0.5
    assert any("min 0.5" in e and "formula" in e for e in _errors(committed, vehicle))


def test_enum_keys_must_be_inside_the_raw_range(committed, vehicle):
    _field(committed, "MONITOR_STATUS", "IGNITION_TYPE")["enum"][2] = "OTHER"
    assert any("enum keys" in e for e in _errors(committed, vehicle))


def test_enum_names_must_be_unique_upper_snake(committed, vehicle):
    _field(committed, "MONITOR_STATUS", "IGNITION_TYPE")["enum"][1] = "SPARK"
    assert any("enum names must be unique" in e for e in _errors(committed, vehicle))
    committed = copy.deepcopy(load_yaml(config.OBD_CATALOG_YAML))
    _field(committed, "MONITOR_STATUS", "IGNITION_TYPE")["enum"][1] = "diesel"
    assert any("enum names must be UPPER_SNAKE" in e for e in _errors(committed, vehicle))


def test_not_used_raw_must_be_a_raw_value(committed, vehicle):
    _field(committed, "O2_S1", "SHORT_TERM_TRIM")["not_used_raw"] = 256
    assert any("not_used_raw" in e for e in _errors(committed, vehicle))


def test_field_names_are_unique_upper_snake_per_entry(committed, vehicle):
    _field(committed, "MONITOR_STATUS", "DTC_COUNT")["name"] = "MIL_ON"
    assert any("name already used in this entry" in e for e in _errors(committed, vehicle))
    committed = copy.deepcopy(load_yaml(config.OBD_CATALOG_YAML))
    _field(committed, "MONITOR_STATUS", "DTC_COUNT")["name"] = "dtc_count"
    assert any("name must be UPPER_SNAKE" in e for e in _errors(committed, vehicle))


def test_scalar_columns_are_refused_next_to_fields(committed, vehicle):
    _entry(committed, "O2_S1")["unit"] = "V"
    assert any("not allowed next to fields" in e for e in _errors(committed, vehicle))


def test_fields_must_be_a_non_empty_list(committed, vehicle):
    _entry(committed, "O2_S1")["fields"] = []
    assert any("fields must be a non-empty list" in e for e in _errors(committed, vehicle))


def test_multi_value_entry_may_not_be_polled(committed, vehicle):
    _entry(committed, "O2_S1")["priority"] = "normal"
    assert any("never polled" in e for e in _errors(committed, vehicle))


def test_scalar_entry_needs_its_formula(cand, vehicle):
    del cand["candidates"][0]["factor_num"]
    assert any("missing factor_num" in e for e in _errors(cand, vehicle))


def test_multi_value_view_in_the_catalog_is_raw(committed, vehicle):
    cat = {e["name"]: e for e in gen_catalog.catalog(committed, vehicle)}
    e = cat["O2_S1_WR_CURRENT"]
    assert (e["factor_num"], e["factor_den"], e["offset"], e["unit"]) == (1, 1, 0, "")
    assert (e["min"], e["max"], e["status"]) == (0, 2**32 - 1, "candidate")
    assert [f["name"] for f in e["fields"]] == ["LAMBDA", "CURRENT"]
    assert cat["ENGINE_SPEED"]["fields"] is None


def test_decode_fields_monitor_status(mod):
    out = mod.decode_fields("MONITOR_STATUS", bytes([0x83, 0x1B, 0x07, 0xFF]))
    assert out == {
        "MIL_ON": 1,
        "DTC_COUNT": 3,
        "READINESS_B_LOW": 3,
        "IGNITION_TYPE": "COMPRESSION",
        "READINESS_B_HIGH": 1,
        "READINESS_C": 7,
        "READINESS_D": 255,
    }
    assert mod.decode_fields("MONITOR_STATUS", bytes(4))["IGNITION_TYPE"] == "SPARK"


def test_decode_fields_fuel_system_status(mod):
    assert mod.decode_fields("FUEL_SYSTEM_STATUS", bytes([2, 4])) == {
        "FUEL_SYSTEM_1": "CLOSED_LOOP",
        "FUEL_SYSTEM_2": "OPEN_LOOP_LOAD_OR_DECEL",
    }
    assert mod.decode_fields("FUEL_SYSTEM_STATUS", bytes([32, 0]))["FUEL_SYSTEM_1"] == 32


def test_decode_fields_o2_sensor_with_not_used_trim(mod):
    assert mod.decode_fields("O2_S1", bytes([90, 128])) == {"VOLTAGE": 0.45, "SHORT_TERM_TRIM": 0.0}
    assert mod.decode_fields("O2_S1", bytes([90, 0xFF])) == {
        "VOLTAGE": 0.45,
        "SHORT_TERM_TRIM": None,
    }
    assert mod.decode_fields("O2_S8", bytes([255, 0]))["SHORT_TERM_TRIM"] == -100.0


def test_decode_fields_o2_wide_range(mod):
    out = mod.decode_fields("O2_S1_WR_CURRENT", bytes([0x80, 0x00, 0x80, 0x00]))
    assert out == {"LAMBDA": 1.0, "CURRENT": 0.0}
    out = mod.decode_fields("O2_S3_WR_CURRENT", bytes([0, 0, 0xFF, 0xFF]))
    assert out == {"LAMBDA": 0.0, "CURRENT": 127.99609375}
    out = mod.decode_fields("O2_S2_WR_VOLTAGE", bytes([0x40, 0x00, 0x20, 0x00]))
    assert out == {"LAMBDA": 0.5, "VOLTAGE": 1.0}


def test_decode_and_decode_fields_refuse_the_other_kind(mod):
    with pytest.raises(ValueError, match="decode_fields"):
        mod.decode("O2_S1", bytes(2))
    with pytest.raises(ValueError, match="use decode"):
        mod.decode_fields("ENGINE_SPEED", bytes(2))
    with pytest.raises(ValueError, match="need 4 bytes"):
        mod.decode_fields("MONITOR_STATUS", bytes(3))


def test_generated_scalar_catalog_entries_decode(mod):
    assert mod.decode("ODOMETER", bytes([0, 0, 0x27, 0x10])) == 1000.0
    assert mod.decode("EGR_ERROR", bytes([128])) == 0.0
    assert mod.decode("CYLINDER_FUEL_RATE", bytes([0, 32])) == 1.0
    assert mod.SIGNALS["ODOMETER"]["status"] == mod.STATUS_CANDIDATE
    assert mod.SIGNALS["ODOMETER"]["poll_period_ms"] is None
    assert mod.BY_DID[0xF4A6] == "ODOMETER"


def test_generated_dart_has_the_fields(committed, vehicle):
    text = (config.GEN_DIR / "dart" / "vehicle_defs" / "lib" / "vehicle_signals.dart").read_text()
    assert "final class VehicleSignalField" in text
    assert "enumNames: <int, String>{0: 'SPARK', 1: 'COMPRESSION'}," in text
    assert "notUsedRaw: 255," in text
    assert "Map<String, Object?> decodeFields(List<int> data)" in text


# --- ISO 14229-1 identification DIDs ---

IDENT = {
    0xF187: "SPARE_PART_NUMBER",
    0xF188: "ECU_SOFTWARE_NUMBER",
    0xF189: "ECU_SOFTWARE_VERSION",
    0xF18A: "SYSTEM_SUPPLIER_ID",
    0xF191: "ECU_HARDWARE_NUMBER",
    0xF192: "SUPPLIER_HARDWARE_NUMBER",
    0xF193: "SUPPLIER_HARDWARE_VERSION",
    0xF194: "SUPPLIER_SOFTWARE_NUMBER",
    0xF195: "SUPPLIER_SOFTWARE_VERSION",
    0xF197: "SYSTEM_NAME",
}


def test_identification_list_is_the_iso_set_without_personal_data(committed):
    assert {e["did"]: e["name"] for e in committed["identification"]} == IDENT
    assert 0xF18C not in IDENT and 0xF190 not in IDENT  # serial number, VIN (D-033, D-059)


@pytest.mark.parametrize("did", [0xF18C, 0xF190])
def test_personal_identification_dids_are_refused(committed, vehicle, did):
    committed["identification"][0]["did"] = did
    assert any("personal data" in e for e in _errors(committed, vehicle))


def test_identification_did_outside_the_iso_range_is_refused(committed, vehicle):
    committed["identification"][0]["did"] = 0xF40C
    assert any("identification range" in e for e in _errors(committed, vehicle))


def test_identification_did_cannot_repeat_or_reuse_a_name(committed, vehicle):
    committed["identification"][1]["did"] = committed["identification"][0]["did"]
    committed["identification"][2]["name"] = committed["identification"][0]["name"]
    errs = _errors(committed, vehicle)
    assert any("already listed" in e for e in errs)
    assert any("name already used" in e for e in errs)


def test_identification_did_has_no_length_and_is_ascii(committed, vehicle):
    committed["identification"][0]["length"] = 8
    committed["identification"][1]["encoding"] = "hex"
    errs = _errors(committed, vehicle)
    assert any("variable" in e for e in errs)
    assert any("encoding must be ascii" in e for e in errs)


def test_identification_read_the_gate_refuses_is_reported(committed, vehicle):
    vehicle["tester_policy"]["allowed"] = [
        e for e in vehicle["tester_policy"]["allowed"] if e["sid"] != 0x22
    ]
    errs = [e for e in _errors(committed, vehicle) if e.startswith("identification[")]
    assert len(errs) == len(IDENT)
    assert all("tester_policy" in e for e in errs)


def test_identification_must_be_a_list(committed, vehicle):
    del committed["identification"]
    assert any("identification: must be a list" in e for e in _errors(committed, vehicle))


def test_decode_ascii_strips_padding(mod):
    assert mod.decode_ascii(b"HONDA-CL250\xff\xff \x00") == "HONDA-CL250"
    assert mod.decode_ascii(b"\x00\x00AB 12\xff") == "AB 12"
    assert mod.decode_ascii(b"") == ""
    assert mod.IDENTIFICATION["SYSTEM_NAME"]["did"] == 0xF197
    assert mod.IDENTIFICATION_BY_DID[0xF187] == "SPARE_PART_NUMBER"


def test_generated_dart_has_the_identification_table(committed):
    text = (config.GEN_DIR / "dart" / "vehicle_defs" / "lib" / "vehicle_signals.dart").read_text()
    for did, name in IDENT.items():
        assert f"did: 0x{did:04X}," in text
        assert f"name: '{name}'," in text
    assert "String decodeIdentificationAscii(List<int> data)" in text
