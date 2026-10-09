"""limits/platform_limits.yaml and provisional poll periods (D-029)."""

import copy
import math

import pytest

from moto_codegen import config
from moto_codegen.yaml_checks import check_limits, check_vehicle, limit_values, load_yaml


@pytest.fixture
def limits():
    return copy.deepcopy(load_yaml(config.LIMITS_YAML))


def test_committed_limits_are_consistent(limits, vehicle, platform_db):
    assert check_limits(limits, vehicle, platform_db) == []


def test_there_is_no_default_lean_angle(limits, vehicle, platform_db):
    assert limit_values(limits)["lean_angle_default"] is None
    limits["cornering"]["lean_angle_default"]["value"] = 0.0
    assert any(
        "lean_angle_default must be null" in e for e in check_limits(limits, vehicle, platform_db)
    )


def test_lean_clamp_is_55_deg_above_the_friction_ceiling(limits):
    v = limit_values(limits)
    assert v["lean_angle_clamp_max_deg"] == 55.0  # D-065 item 3, user 2026-10-09
    assert v["lean_angle_clamp_max_deg"] > math.degrees(math.atan(v["friction_coeff_clamp_max"]))


@pytest.mark.parametrize(
    "clamp", [50.19, 45.0, 0.0, -55.0, 90.0, 95.0, float("nan"), float("inf"), True, "55", None]
)  # atan(1.2) = 50.194 deg; DBC LEAN_ANGLE max 90
def test_lean_clamp_range(limits, vehicle, platform_db, clamp):
    limits["cornering"]["lean_angle_clamp_max_deg"]["value"] = clamp
    assert any("lean_angle_clamp_max_deg" in e for e in check_limits(limits, vehicle, platform_db))


def test_lean_clamp_follows_the_friction_ceiling(limits, vehicle, platform_db):
    # Raising the mu ceiling raises the steepest reachable lean: atan(1.5) = 56.3 deg > 55.
    limits["cornering"]["friction_coeff_clamp_max"]["value"] = 1.5
    assert any(
        "atan(friction_coeff_clamp_max)" in e for e in check_limits(limits, vehicle, platform_db)
    )
    limits["cornering"]["lean_angle_clamp_max_deg"]["value"] = 57.0
    assert check_limits(limits, vehicle, platform_db) == []


def test_lean_clamp_on_the_dbc_scale(limits, vehicle, platform_db):
    limits["cornering"]["lean_angle_clamp_max_deg"]["value"] = 55.004  # LEAN_ANGLE is 0.01 deg
    assert any(
        "not representable in LEAN_ANGLE" in e for e in check_limits(limits, vehicle, platform_db)
    )


@pytest.mark.parametrize(("clamp", "reads_red"), [(43.8, False), (43.9, True), (55.0, True)])
def test_a_clamped_lean_reads_red_at_the_friction_ceiling(
    limits, vehicle, platform_db, clamp, reads_red
):
    # safety-reviewer MINOR-4: checked directly, tan(clamp) > k_red * mu_max = 0.8 * 1.2
    # (atan 0.96 = 43.83 deg), not only through the stricter atan(mu_max) floor.
    limits["cornering"]["lean_angle_clamp_max_deg"]["value"] = clamp
    errors = check_limits(limits, vehicle, platform_db)
    assert any("must read RED" in e for e in errors) is not reads_red


def test_friction_default_inside_clamp_range(limits, vehicle, platform_db):
    limits["cornering"]["friction_coeff_default"]["value"] = 1.5
    assert any("outside the clamp range" in e for e in check_limits(limits, vehicle, platform_db))


@pytest.mark.parametrize("age", [100, 120, 301, 400, 300.0, True])  # poll 100 + rtt 20, stale 300
def test_speed_age_within_poll_period_and_stale(limits, vehicle, platform_db, age):
    limits["vehicle_speed"]["vehicle_speed_max_age_ms"]["value"] = age
    assert any("vehicle_speed_max_age_ms" in e for e in check_limits(limits, vehicle, platform_db))


def test_speed_age_equals_stale_after(limits, vehicle):
    # D-041 item 4 re-scope: rt-core cannot use a sample older than stale_after_ms anyway.
    speed = next(d for d in vehicle["dids"] if d["name"] == "VEHICLE_SPEED")
    assert limit_values(limits)["vehicle_speed_max_age_ms"] == speed["stale_after_ms"]


@pytest.mark.parametrize(
    ("k_yellow", "k_red"),
    [(0.8, 0.6), (0.6, 0.6), (0.0, 0.8), (0.6, 1.0), (0.6, 1.2), (-0.1, 0.8),
     (float("nan"), 0.8), (0.6, float("inf")), (True, 0.8), ("0.6", 0.8), (None, 0.8)],
)  # fmt: skip
def test_k_thresholds_ordered_inside_unit_interval(limits, vehicle, platform_db, k_yellow, k_red):
    limits["cornering"]["k_yellow"]["value"] = k_yellow
    limits["cornering"]["k_red"]["value"] = k_red
    assert any("0 < k_yellow < k_red < 1" in e for e in check_limits(limits, vehicle, platform_db))


def test_k_red_leaves_the_d041_longitudinal_reserve(limits, vehicle, platform_db):
    # D-041 item 3: until Q-022, sqrt(1 - k_red^2) of mu stays for braking (0.6 at 0.8).
    limits["cornering"]["k_red"]["value"] = 0.81
    assert any("until Q-022" in e for e in check_limits(limits, vehicle, platform_db))


def test_speed_rules_never_reach_safety(limits, vehicle, platform_db):
    limits["scope"]["vehicle_speed"].append("SAFETY")
    assert any("must not include SAFETY" in e for e in check_limits(limits, vehicle, platform_db))


@pytest.mark.parametrize(
    ("mutate", "needle"),
    [
        (lambda s: s.pop("vehicle_speed"), "scope must list exactly"),
        (lambda s: s.update(extra=["RT_CORE"]), "scope must list exactly"),
        (lambda s: s["cornering"].append("IO"), "not nodes with limits"),
        (lambda s: s.update(cornering=[]), "non-empty list"),
        (lambda s: s["cornering"].remove("SAFETY"), "node SAFETY gets platform_limits.h"),
    ],
)
def test_scope_rejects(limits, vehicle, platform_db, mutate, needle):
    mutate(limits["scope"])
    assert any(needle in e for e in check_limits(limits, vehicle, platform_db))


@pytest.mark.parametrize(
    ("directory", "has_speed"), [("rt_core", True), ("safety", False), ("hil_sim", True)]
)
def test_limits_header_follows_scope(directory, has_speed):
    text = (config.GEN_DIR / "c" / directory / "platform_limits.h").read_text()
    assert "#define PLATFORM_LIMIT_K_YELLOW (0.6f)" in text
    assert "#define PLATFORM_LIMIT_K_RED (0.8f)" in text
    assert ("PLATFORM_LIMIT_VEHICLE_SPEED" in text) is has_speed


def test_every_limit_needs_a_rule_and_status(limits, vehicle, platform_db):
    del limits["cornering"]["total_mass_default_kg"]["rule"]
    limits["vehicle_speed"]["vehicle_speed_max_age_ms"]["status"] = "guess"
    errs = check_limits(limits, vehicle, platform_db)
    assert any("needs value + rule" in e for e in errs)
    assert any("status must be" in e for e in errs)


def test_provisional_poll_period_keeps_legacy_value(vehicle, platform_db):
    speed = next(d for d in vehicle["dids"] if d["name"] == "VEHICLE_SPEED")
    assert speed["poll_period_verified"] is False and speed["legacy_poll_period_ms"] == 800
    del speed["legacy_poll_period_ms"]
    assert any("legacy_poll_period_ms" in e for e in check_vehicle(vehicle, platform_db))


def test_limits_header_only_for_cornering_nodes():
    for target in config.C_TARGETS:
        path = config.GEN_DIR / "c" / target.directory / "platform_limits.h"
        assert path.exists() is target.limits, target.directory


def test_limits_fit_the_dbc_scale(limits, vehicle, platform_db):
    limits["cornering"]["friction_coeff_default"]["value"] = 0.5004  # FRICTION_COEFF is 0.001
    assert any("not representable" in e for e in check_limits(limits, vehicle, platform_db))


def test_polling_budget(vehicle, platform_db):
    vehicle["timing"]["assumed_round_trip_ms"] = 40
    assert any("polling budget" in e for e in check_vehicle(vehicle, platform_db))


def _effective_mu(state, received):
    """Reference of the friction rule in limits/platform_limits.yaml."""
    v = limit_values(load_yaml(config.LIMITS_YAML))
    lo, hi, default = (
        v["friction_coeff_clamp_min"],
        v["friction_coeff_clamp_max"],
        v["friction_coeff_default"],
    )
    if state in (0, 1):  # ESTIMATED, CLAMPED
        return min(max(received, lo), hi)
    if state == 2:  # DEFAULT
        return max(lo, min(received, default))
    return default  # INVALID, RESERVED, unknown: received value ignored


@pytest.mark.parametrize("state", [0, 1, 2, 3, 4, 255])
@pytest.mark.parametrize("received", [0.0, 0.099, 0.1, 0.5, 1.2, 1.201, 2.0])
def test_friction_rule_is_always_finite_and_bounded(state, received):
    import math

    mu = _effective_mu(state, received)
    assert math.isfinite(mu) and 0.1 <= mu <= 1.2
    if state == 2:
        assert mu <= 0.5  # a DEFAULT can only make warnings earlier


def test_generated_state_helper_is_an_allow_list(tmp_path):
    import shutil
    import subprocess

    cc = shutil.which("gcc")
    if cc is None:
        pytest.skip("no C compiler")
    src = tmp_path / "t.c"
    src.write_text(
        '#include "platform_limits.h"\n#include <stdio.h>\n'
        "int main(void){for(unsigned s=0;s<256;s++)putchar(platform_estimate_state_usable"
        "((uint8_t)s)?'1':'0');return 0;}\n"
    )
    exe = tmp_path / "t"
    subprocess.run(
        [cc, "-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-I", str(config.GEN_DIR / "c" / "safety"), str(src), "-o", str(exe)],
        check=True,
    )  # fmt: skip
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
    assert out == "11" + "0" * 254
