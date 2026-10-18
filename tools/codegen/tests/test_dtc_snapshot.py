"""D-080: DTC freeze-frame constants and the four requests built from them."""

import pytest

from moto_codegen import config
from moto_codegen.yaml_checks import (
    check_dtc_snapshot,
    dtc_snapshot_requests,
    frame_allowed,
    load_yaml,
    request_allowed,
    single_frame,
)


@pytest.fixture
def iso():
    return load_yaml(config.ISO14229_YAML)


def test_committed_section_is_clean(vehicle, iso):
    assert check_dtc_snapshot(vehicle, iso) == []
    snap = vehicle["dtc_snapshot"]
    assert (snap["decision"], snap["provisional"]) == ("D-080", True)
    assert (snap["status_mask"], snap["max_dtcs_per_run"]) == (0x0C, 8)
    assert (snap["snapshot_record"], snap["ext_data_record"]) == (0xFF, 0xFF)


def test_the_four_requests_pass_both_gates(vehicle):
    reqs = dtc_snapshot_requests(vehicle["dtc_snapshot"])
    assert reqs == {
        "count": [0x19, 0x01, 0x0C],
        "list": [0x19, 0x02, 0x0C],
        "snapshot": [0x19, 0x04, 0, 0, 0, 0xFF],
        "ext_data": [0x19, 0x06, 0, 0, 0, 0xFF],
    }
    for req in reqs.values():
        assert request_allowed(vehicle["tester_policy"], req)
        assert frame_allowed(vehicle, single_frame(vehicle, req))


def test_iso_names_the_snapshot_subfunctions(iso):
    subs = {s["id"]: s["name"] for s in iso["read_dtc_subfunctions"]}
    assert subs[0x04] == "REPORT_DTC_SNAPSHOT_RECORD_BY_DTC_NUMBER"
    assert subs[0x06] == "REPORT_DTC_EXT_DATA_RECORD_BY_DTC_NUMBER"


def test_missing_section_is_reported(vehicle, iso):
    del vehicle["dtc_snapshot"]
    assert check_dtc_snapshot(vehicle, iso) == ["vehicle: dtc_snapshot missing (D-080)"]


@pytest.mark.parametrize("mask", [0, 0x100, -1, True, "0x0C"])
def test_bad_status_mask_is_refused(vehicle, iso, mask):
    vehicle["dtc_snapshot"]["status_mask"] = mask
    assert any("status_mask" in e for e in check_dtc_snapshot(vehicle, iso))


def test_status_mask_must_be_made_of_iso_status_bits(vehicle, iso):
    iso["dtc_status_bits"] = [b for b in iso["dtc_status_bits"] if b["mask"] != 0x08]
    assert any("not made of dtc_status_bits" in e for e in check_dtc_snapshot(vehicle, iso))


@pytest.mark.parametrize("count", [0, 9, -1, 8.0, True])
def test_dtcs_per_run_must_be_1_to_8(vehicle, iso, count):
    vehicle["dtc_snapshot"]["max_dtcs_per_run"] = count
    assert any("max_dtcs_per_run" in e for e in check_dtc_snapshot(vehicle, iso))


@pytest.mark.parametrize("key", ["snapshot_record", "ext_data_record"])
def test_record_numbers_are_bytes(vehicle, iso, key):
    vehicle["dtc_snapshot"][key] = 0x100
    assert any(key in e for e in check_dtc_snapshot(vehicle, iso))


def test_decision_and_provisional_flag_are_required(vehicle, iso):
    vehicle["dtc_snapshot"]["decision"] = "D-079"
    vehicle["dtc_snapshot"]["provisional"] = "yes"
    errs = check_dtc_snapshot(vehicle, iso)
    assert any("decision" in e for e in errs)
    assert any("provisional" in e for e in errs)


def test_missing_iso_subfunction_is_reported(vehicle, iso):
    iso["read_dtc_subfunctions"] = [s for s in iso["read_dtc_subfunctions"] if s["id"] != 0x06]
    assert any("lacks 0x06" in e for e in check_dtc_snapshot(vehicle, iso))


def test_requests_the_policy_refuses_are_reported(vehicle, iso):
    vehicle["tester_policy"]["allowed"] = [
        e for e in vehicle["tester_policy"]["allowed"] if e["sid"] != 0x19
    ]
    errs = check_dtc_snapshot(vehicle, iso)
    assert len([e for e in errs if "violates tester_policy" in e]) == 4


def test_a_request_the_frame_gate_refuses_is_reported(vehicle, iso, monkeypatch):
    # 0x19 0x04 plus a 3-byte DTC and a record fits one Single Frame; a longer padded
    # frame would not, so the gate twin is what refuses it.
    monkeypatch.setattr(
        "moto_codegen.yaml_checks.frame_allowed", lambda vehicle, frame: len(frame) == 0
    )
    errs = check_dtc_snapshot(vehicle, iso)
    assert len([e for e in errs if "frame gate" in e]) == 4


def test_generated_python_and_c_carry_the_constants(vehicle):
    snap = vehicle["dtc_snapshot"]
    py = (config.GEN_DIR / "python" / "moto_defs" / "vehicle_cl250.py").read_text()
    assert f"DTC_STATUS_MASK = 0x{snap['status_mask']:02X}" in py
    assert f"DTC_MAX_PER_RUN = {snap['max_dtcs_per_run']}" in py
    assert f"DTC_SNAPSHOT_RECORD = 0x{snap['snapshot_record']:02X}" in py
    assert f"DTC_EXT_DATA_RECORD = 0x{snap['ext_data_record']:02X}" in py
    for target in config.C_TARGETS:
        path = config.GEN_DIR / "c" / target.directory / "vehicle_cl250.h"
        if not target.vehicle_dids:
            assert not path.exists()
            continue
        header = path.read_text()
        assert "#define VEHICLE_CL250_DTC_STATUS_MASK (0x0Cu)" in header
        assert "#define VEHICLE_CL250_DTC_MAX_PER_RUN (8u)" in header
        assert "#define VEHICLE_CL250_DTC_SNAPSHOT_RECORD (0xFFu)" in header
        assert "#define VEHICLE_CL250_DTC_EXT_DATA_RECORD (0xFFu)" in header
