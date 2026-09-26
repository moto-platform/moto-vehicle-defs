"""limits/platform_limits.yaml and provisional poll periods (D-029)."""

import copy

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


def test_friction_default_inside_clamp_range(limits, vehicle, platform_db):
    limits["cornering"]["friction_coeff_default"]["value"] = 1.5
    assert any("outside the clamp range" in e for e in check_limits(limits, vehicle, platform_db))


def test_speed_age_consistent_with_poll_period(limits, vehicle, platform_db):
    limits["vehicle_speed"]["vehicle_speed_max_age_ms"]["value"] = 300  # == stale_after_ms
    assert any("vehicle_speed_max_age_ms" in e for e in check_limits(limits, vehicle, platform_db))


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
