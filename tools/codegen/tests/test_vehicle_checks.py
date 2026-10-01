"""D-020 allow-list and evidence rules for uds/vehicle_cl250.yaml."""

import pytest

from moto_codegen import config
from moto_codegen.yaml_checks import (
    check_vehicle,
    did_fault_gap_bounds,
    did_sample_gap_bounds,
    request_allowed,
)


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


def _gap_bounds(vehicle):
    return did_sample_gap_bounds(vehicle["dids"], vehicle["timing"]["assumed_round_trip_ms"])


def test_sample_gap_bounds_of_the_table_are_within_stale_after(vehicle):
    # D-043 no starvation, worked by hand for the table at C = 20 ms (RPM and speed at
    # 110 ms, D-053): speed (high, P110): w = 20 -> 150; RPM (P110): w = 20 + 20 = 40 -> 170;
    # throttle (P200): w = 60 -> 280; coolant (P800): w = 80 -> 900;
    # battery (P800): w = 100 -> 920.
    assert vehicle["timing"]["assumed_round_trip_ms"] == 20
    assert _gap_bounds(vehicle) == {
        "VEHICLE_SPEED": 150,
        "ENGINE_SPEED": 170,
        "THROTTLE_POS": 280,
        "COOLANT_TEMP": 900,
        "BATTERY_VOLTAGE": 920,
    }
    for d in vehicle["dids"]:
        assert _gap_bounds(vehicle)[d["name"]] <= d["stale_after_ms"]


def test_a_stale_after_below_the_sample_gap_bound_fails(vehicle, platform_db):
    rpm = next(d for d in vehicle["dids"] if d["name"] == "ENGINE_SPEED")
    rpm["stale_after_ms"] = 169  # bound 170
    errs = check_vehicle(vehicle, platform_db)
    assert any("ENGINE_SPEED: worst-case sample gap 170 ms > stale_after_ms 169" in e for e in errs)
    rpm["stale_after_ms"] = 170
    assert not any("sample gap" in e for e in check_vehicle(vehicle, platform_db))


def test_the_bound_follows_the_priority_order(vehicle):
    # Making throttle high puts it ahead of RPM: RPM's interference grows.
    before = _gap_bounds(vehicle)
    next(d for d in vehicle["dids"] if d["name"] == "THROTTLE_POS")["priority"] = "high"
    after = _gap_bounds(vehicle)
    assert after["ENGINE_SPEED"] > before["ENGINE_SPEED"]
    assert after["THROTTLE_POS"] < before["THROTTLE_POS"]


def test_an_overloaded_table_is_unbounded_and_fails(vehicle, platform_db):
    for d in vehicle["dids"]:
        d["poll_period_ms"] = 30
        d["stale_after_ms"] = 60
    errs = check_vehicle(vehicle, platform_db)
    assert any("polling budget" in e for e in errs)
    assert any("worst-case sample gap unbounded" in e for e in errs)


def _fault_bounds(vehicle, step=None):
    t = vehicle["timing"]
    return did_fault_gap_bounds(
        vehicle["dids"],
        t["assumed_round_trip_ms"],
        t["response_timeout_base_ms"],
        t["max_consecutive_timeouts"],
        t["client_step_max_ms"] if step is None else step,
    )


def test_fault_gap_bounds_of_the_table_are_within_stale_after(vehicle):
    # D-050..D-053, worked by hand (B = 100, S = 10, so a faulty read holds the slot for
    # H = B + S = 110; C = 20; RPM and speed at P = 110; any one DID faulty, its reads
    # alternate P_f and P_f + B apart, at most 2 * 5 - 2 = 8 after the blocking one):
    # RPM: throttle, coolant or battery faulty (normal DIDs, E-8 (2)): w = H + 2 * C
    #   (speed) = 150 -> 260;
    # speed: only the blocking read is ahead of it: w = H = 110 -> 220;
    # throttle: RPM or speed faulty: w = H + 1 * H + 3 * C = 280 -> 480;
    # coolant: RPM or speed faulty: w = H + 5 * H + 14 * C = 940 -> 1740;
    # battery: RPM or speed faulty: w = H + 8 * H (the cap) + 24 * C = 1470 -> 2270.
    t = vehicle["timing"]
    assert (t["assumed_round_trip_ms"], t["response_timeout_base_ms"]) == (20, 100)
    assert (t["client_step_max_ms"], t["max_consecutive_timeouts"]) == (10, 5)
    assert _fault_bounds(vehicle) == {
        "ENGINE_SPEED": 260,
        "VEHICLE_SPEED": 220,
        "THROTTLE_POS": 480,
        "COOLANT_TEMP": 1740,
        "BATTERY_VOLTAGE": 2270,
    }
    assert not any("fault-mode" in e for e in check_vehicle(vehicle, None))


def test_a_faulty_read_holds_the_slot_until_the_step_that_sees_its_timeout(vehicle):
    # Safety review MINOR-1 on D-053: the tester ends a faulty read at the step that sees
    # its base timeout, up to one step after it, so the model holds B + S per faulty read.
    without, with_step = _fault_bounds(vehicle, step=0), _fault_bounds(vehicle)
    assert (without["VEHICLE_SPEED"], with_step["VEHICLE_SPEED"]) == (210, 220)
    assert all(with_step[n] >= without[n] for n in without)


def test_a_round_trip_not_above_the_step_is_refused(vehicle, platform_db):
    # assumed_round_trip_ms covers the ECU's answer plus one step (D-043, D-053).
    vehicle["timing"]["assumed_round_trip_ms"] = 10
    errs = check_vehicle(vehicle, platform_db)
    assert any(
        "timing.assumed_round_trip_ms 10 must exceed client_step_max_ms 10" in e for e in errs
    )


def test_a_poll_period_below_the_base_timeout_is_refused(vehicle, platform_db):
    # D-052 (ISSUES E-8 (1)): with the legacy 50 ms, an RPM answer at 51-99 ms (no NRC 0x78)
    # made RPM due again at once and starved the later normal DIDs.
    rpm = next(d for d in vehicle["dids"] if d["name"] == "ENGINE_SPEED")
    rpm["poll_period_ms"], rpm["stale_after_ms"] = 50, 150
    errs = check_vehicle(vehicle, platform_db)
    assert any(
        "ENGINE_SPEED: poll_period_ms 50 < response_timeout_base_ms 100 + client_step_max_ms 10"
        in e
        for e in errs
    )
    # The fault-mode model needs the rule, so it is not evaluated without it.
    assert not any("fault-mode" in e for e in errs)


def test_a_poll_period_equal_to_the_base_timeout_is_refused(vehicle, platform_db):
    # D-053 (ISSUES E-9): at P = B an answer just inside B, seen by a late step, makes its
    # DID due again at once with no timeout and no skip. One step more is required.
    for d in vehicle["dids"]:
        if d["name"] in ("ENGINE_SPEED", "VEHICLE_SPEED"):
            d["poll_period_ms"] = 100
    errs = check_vehicle(vehicle, platform_db)
    for name in ("ENGINE_SPEED", "VEHICLE_SPEED"):
        assert any(
            f"{name}: poll_period_ms 100 < response_timeout_base_ms 100 + client_step_max_ms 10"
            " (D-052, D-053)" in e
            for e in errs
        )
    for d in vehicle["dids"]:
        if d["name"] in ("ENGINE_SPEED", "VEHICLE_SPEED"):
            d["poll_period_ms"] = 110
    assert not any("D-053" in e for e in check_vehicle(vehicle, platform_db))


def test_a_base_timeout_plus_step_above_a_period_is_refused(vehicle, platform_db):
    for key, value in (("response_timeout_base_ms", 101), ("client_step_max_ms", 11)):
        saved = vehicle["timing"][key]
        vehicle["timing"][key] = value
        errs = check_vehicle(vehicle, platform_db)
        for name in ("ENGINE_SPEED", "VEHICLE_SPEED"):
            assert any(f"{name}: poll_period_ms 110 < response_timeout_base_ms" in e for e in errs)
        vehicle["timing"][key] = saved
    assert not any("D-053" in e for e in check_vehicle(vehicle, platform_db))


@pytest.mark.parametrize("value", [None, 0, -5, "10", True])
def test_client_step_max_is_required_for_the_period_rule(vehicle, platform_db, value):
    if value is None:
        del vehicle["timing"]["client_step_max_ms"]
    else:
        vehicle["timing"]["client_step_max_ms"] = value
    errs = check_vehicle(vehicle, platform_db)
    assert any("timing.client_step_max_ms must be a positive integer" in e for e in errs)
    # Without the step the period rule and the fault-mode model are not evaluated.
    assert not any("fault-mode" in e for e in errs)


def test_a_normal_did_ahead_of_rpm_breaks_the_fault_mode_bound(vehicle, platform_db):
    # RPM's 260 ms relies on no normal DID being ahead of it in table order.
    dids = vehicle["dids"]
    rpm = next(i for i, d in enumerate(dids) if d["name"] == "ENGINE_SPEED")
    tps = next(i for i, d in enumerate(dids) if d["name"] == "THROTTLE_POS")
    dids[rpm], dids[tps] = dids[tps], dids[rpm]
    errs = check_vehicle(vehicle, platform_db)
    assert not any("worst-case sample gap" in e for e in errs)  # the nominal bound holds
    assert any(
        "ENGINE_SPEED: fault-mode request gap 370 ms > stale_after_ms 330" in e for e in errs
    )


def test_a_faulty_normal_did_sets_the_rpm_fault_bound(vehicle, platform_db):
    # ISSUES E-8 (2): the worst case for RPM is a faulty normal DID behind it (its read
    # just started), which the D-051 check did not model: P + H + 2 * C (speed) = 260.
    next(d for d in vehicle["dids"] if d["name"] == "ENGINE_SPEED")["stale_after_ms"] = 259
    errs = check_vehicle(vehicle, platform_db)
    assert any(
        "ENGINE_SPEED: fault-mode request gap 260 ms > stale_after_ms 259" in e for e in errs
    )


def test_slow_answers_between_timeouts_count_toward_the_faulty_reads(vehicle):
    # D-052 (ISSUES E-8 (3)): a slow answer does not reset the skip count, so each
    # timeout before the skip may come with one slow answer, and the first failing read
    # may itself be a slow answer: 2 * max - 1 faulty reads after it, 2 * max - 2 after the
    # blocking one (safety review MINOR-1). Battery's window reaches the cap: 4 at max 3,
    # 8 at max 5.
    dids, t = vehicle["dids"], vehicle["timing"]
    rtt, base, step = (
        t["assumed_round_trip_ms"],
        t["response_timeout_base_ms"],
        t["client_step_max_ms"],
    )
    assert did_fault_gap_bounds(dids, rtt, base, 3, step)["BATTERY_VOLTAGE"] == 1650
    assert did_fault_gap_bounds(dids, rtt, base, 5, step)["BATTERY_VOLTAGE"] == 2270


def test_without_the_skip_a_faulty_did_starves_the_slow_dids(vehicle, platform_db):
    # The skip after max_consecutive_timeouts caps the faulty reads; without it a faulty
    # RPM or speed, with the others, fills battery's window.
    vehicle["timing"]["max_consecutive_timeouts"] = 100
    errs = check_vehicle(vehicle, platform_db)
    assert any(
        "BATTERY_VOLTAGE: fault-mode request gap unbounded > stale_after_ms 2400" in e for e in errs
    )


def test_without_a_high_priority_did_every_did_is_still_covered(vehicle, platform_db):
    # Since D-052 any one DID may be faulty, not only a demoted high one. Every DID gets a
    # finite bound; but with speed behind RPM in table order a faulty RPM read (H = 110)
    # pushes speed to 110 + 110 + 110 = 330 > 300, so speed needs its high priority.
    for d in vehicle["dids"]:
        d["priority"] = "normal"
    bounds = _fault_bounds(vehicle)
    assert set(bounds) == {d["name"] for d in vehicle["dids"]}
    assert all(b is not None for b in bounds.values())
    errs = [e for e in check_vehicle(vehicle, platform_db) if "fault-mode" in e]
    assert len(errs) == 1
    assert "VEHICLE_SPEED: fault-mode request gap 330 ms > stale_after_ms 300" in errs[0]


@pytest.mark.parametrize("value", [None, 0, -5, "20", True])
def test_assumed_round_trip_is_required_for_the_budget_and_gap_checks(vehicle, platform_db, value):
    if value is None:
        del vehicle["timing"]["assumed_round_trip_ms"]
    else:
        vehicle["timing"]["assumed_round_trip_ms"] = value
    errs = check_vehicle(vehicle, platform_db)
    assert any("timing.assumed_round_trip_ms must be a positive integer" in e for e in errs)


def test_budget_within_0_8_but_gap_bound_failing_is_refused(vehicle, platform_db):
    # Budget 0.0257 * 21 = 0.54 passes; RPM's bound at C = 21 is 110 + 42 + 21 = 173.
    vehicle["timing"]["assumed_round_trip_ms"] = 21
    next(d for d in vehicle["dids"] if d["name"] == "ENGINE_SPEED")["stale_after_ms"] = 172
    errs = check_vehicle(vehicle, platform_db)
    assert not any("polling budget" in e for e in errs)
    assert any("ENGINE_SPEED: worst-case sample gap 173 ms > stale_after_ms 172" in e for e in errs)


@pytest.mark.parametrize("key", ["response_timeout_base_ms", "did_skip_cooldown_ms"])
def test_a_bool_timing_value_is_refused(vehicle, platform_db, key):
    # YAML `true` is an int subclass in Python and would pass as 1 ms (E-6 n3).
    vehicle["timing"][key] = True
    errs = check_vehicle(vehicle, platform_db)
    assert any(f"timing.{key} must be a positive integer" in e for e in errs)


def test_requests_in_flight_true_is_not_one(vehicle, platform_db):
    vehicle["timing"]["requests_in_flight"] = True
    errs = check_vehicle(vehicle, platform_db)
    assert any("requests_in_flight must be 1" in e for e in errs)


@pytest.mark.parametrize("key", ["poll_period_ms", "stale_after_ms"])
def test_a_bool_did_period_is_refused(vehicle, platform_db, key):
    vehicle["dids"][0][key] = True
    errs = check_vehicle(vehicle, platform_db)
    assert any("poll_period_ms and stale_after_ms must be positive integers" in e for e in errs)
