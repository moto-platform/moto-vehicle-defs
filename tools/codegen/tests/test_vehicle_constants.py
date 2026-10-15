"""vehicle/cl250_constants.yaml (D-070 item 3)."""

import copy

import pytest

from moto_codegen import config, gen_c, gen_python
from moto_codegen.yaml_checks import check_vehicle_constants, load_yaml


@pytest.fixture
def constants():
    return copy.deepcopy(load_yaml(config.VEHICLE_CONSTANTS_YAML))


def test_committed_constants_are_consistent(constants):
    assert check_vehicle_constants(constants) == []


def test_only_rt_core_gets_the_constants_header():
    assert [t.node for t in config.C_TARGETS if t.vehicle_constants] == ["RT_CORE"]


@pytest.mark.parametrize("bad", [0, -1.0, float("nan"), float("inf"), True, "2.8", None])
def test_a_value_must_be_a_finite_positive_number(constants, bad):
    constants["constants"]["primary_reduction_ratio"]["value"] = bad
    assert any("primary_reduction_ratio" in e for e in check_vehicle_constants(constants))


def test_every_value_names_its_source_and_status(constants):
    constants["constants"]["stoichiometric_afr"]["source"] = " "
    constants["constants"]["fuel_density_kg_per_l"]["status"] = "guess"
    errors = check_vehicle_constants(constants)
    assert any("stoichiometric_afr: source" in e for e in errors)
    assert any("fuel_density_kg_per_l: status" in e for e in errors)


def test_a_missing_field_is_reported(constants):
    del constants["constants"]["gear_ratio_3"]["unit"]
    assert any("gear_ratio_3: needs exactly" in e for e in check_vehicle_constants(constants))


def test_gear_ratios_match_gear_count_and_decrease(constants):
    c = copy.deepcopy(constants)
    del c["constants"]["gear_ratio_6"]
    assert any("gear_ratio_6 missing" in e for e in check_vehicle_constants(c))
    c = copy.deepcopy(constants)
    c["constants"]["gear_ratio_7"] = dict(c["constants"]["gear_ratio_6"], value=0.9)
    assert any("gear_ratio_7 beyond" in e for e in check_vehicle_constants(c))
    c = copy.deepcopy(constants)
    c["constants"]["gear_ratio_4"]["value"] = 1.7
    assert any("strictly decrease" in e for e in check_vehicle_constants(c))


def test_generated_header_and_module_carry_every_value(constants):
    h = gen_c.generate_vehicle_constants_c(constants)["vehicle_cl250_constants.h"]
    py = gen_python.generate_vehicle_constants_py(constants)
    assert "#define VEHICLE_CL250_GEAR_COUNT (6u)" in h
    for key in constants["constants"]:
        assert f"VEHICLE_CL250_{key.upper()} (" in h
        assert f'"{key}": (' in py
