"""D-020 allow-list and evidence rules for uds/vehicle_cl250.yaml."""

import pytest

from moto_codegen import config
from moto_codegen.yaml_checks import check_vehicle, request_allowed


def test_policy_allowing_a_forbidden_service_fails(vehicle, platform_db):
    vehicle["tester_policy"]["allowed"].append({"sid": 0x2E, "name": "WriteDataByIdentifier"})
    assert any("forbidden service 0x2E" in e for e in check_vehicle(vehicle, platform_db))


def test_programming_session_is_never_allowed(vehicle, platform_db):
    vehicle["tester_policy"]["allowed"][0]["subfunctions"].append(0x02)
    vehicle["session"]["start"]["request"] = [0x10, 0x02]
    errs = check_vehicle(vehicle, platform_db)
    assert any("0x10 0x02" in e for e in errs)
    assert any("session.start" in e for e in errs)


def test_forbidden_list_must_match_d020(vehicle, platform_db):
    vehicle["tester_policy"]["forbidden"].remove(0x14)
    assert any("differs from the D-020" in e for e in check_vehicle(vehicle, platform_db))


def test_verified_needs_evidence(vehicle, platform_db):
    vehicle["dids"][0]["evidence"] = []
    assert any("without file:line evidence" in e for e in check_vehicle(vehicle, platform_db))


def test_platform_signal_must_exist(vehicle, platform_db):
    vehicle["dids"][0]["platform_signal"] = "VehicleEngine.NOPE"
    assert any("not found in platform.dbc" in e for e in check_vehicle(vehicle, platform_db))


@pytest.mark.parametrize("prio", ["safety", "HIGH", 1, None])
def test_priority_must_be_a_known_class(vehicle, platform_db, prio):
    vehicle["dids"][0]["priority"] = prio
    assert any("priority must be one of" in e for e in check_vehicle(vehicle, platform_db))


def test_priority_is_required(vehicle, platform_db):
    del vehicle["dids"][0]["priority"]
    assert any("missing ['priority']" in e for e in check_vehicle(vehicle, platform_db))


def test_vehicle_speed_is_the_only_high_priority_did(vehicle):
    # D-043 item 2: 0xF40D feeds the rt-core EKF lean estimate.
    high = [d["did"] for d in vehicle["dids"] if d["priority"] == "high"]
    assert high == [0xF40D]


def test_python_vehicle_module_decodes(vehicle):
    ns: dict = {}
    exec((config.GEN_DIR / "python" / "moto_defs" / "vehicle_cl250.py").read_text(), ns)  # noqa: S102
    assert ns["decode"]("VEHICLE_SPEED", b"\x3c") == 60.0
    assert ns["decode"]("ENGINE_SPEED", b"\x1a\xf8") == 1726.0
    assert ns["PRIORITIES"] == ("high", "normal")
    assert {n: t[9] for n, t in ns["DIDS"].items()} == {
        d["name"]: d["priority"] for d in vehicle["dids"]
    }


def test_duplicate_did(vehicle, platform_db):
    vehicle["dids"][1]["did"] = vehicle["dids"][0]["did"]
    assert any("duplicate" in e for e in check_vehicle(vehicle, platform_db))


@pytest.mark.parametrize(
    ("payload", "allowed"),
    [
        ([0x10, 0x03], True),
        ([0x10, 0x83], True),  # suppressPosRsp bit is ignored
        ([0x10, 0x01], True),
        ([0x10, 0x02], False),
        ([0x10, 0x82], False),
        ([0x10], False),
        ([0x3E, 0x80], True),
        ([0x3E, 0x01], False),
        ([0x22, 0xF4, 0x0C], True),
        ([0x19, 0x02, 0xFF], True),
        ([0x01, 0x0C], True),
        ([0x09, 0x02], True),
        ([], False),
        *[([sid, 0x00], False) for sid in sorted(config.FORBIDDEN_VEHICLE_SERVICES)],
        ([0x85, 0x02], False),  # ControlDTCSetting: not on the allow-list
    ],
)
def test_request_allowed(vehicle, payload, allowed):
    assert request_allowed(vehicle["tester_policy"], payload) is allowed


@pytest.mark.parametrize("sid", [0x28, 0x85, 0x3D, 0x04, 0x2A])
def test_policy_wider_than_d020_fails(vehicle, platform_db, sid):
    vehicle["tester_policy"]["allowed"].append({"sid": sid, "name": "not allowed"})
    assert any("not on the D-020 allow-list" in e for e in check_vehicle(vehicle, platform_db))
    with pytest.raises(ValueError):
        config.assert_policy_within_d020(vehicle["tester_policy"])


def test_tester_present_any_subfunction_fails(vehicle, platform_db):
    tp = next(e for e in vehicle["tester_policy"]["allowed"] if e["sid"] == 0x3E)
    del tp["subfunctions"]
    assert any("exceed D-020" in e for e in check_vehicle(vehicle, platform_db))


def test_stale_after_must_exceed_poll_period(vehicle, platform_db):
    vehicle["dids"][0]["stale_after_ms"] = vehicle["dids"][0]["poll_period_ms"]
    assert any("stale_after_ms" in e for e in check_vehicle(vehicle, platform_db))
