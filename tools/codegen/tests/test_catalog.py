"""D-066: candidate signal catalog checks and the generated Python/Dart catalog."""

import copy
import importlib.util

import pytest

from vehicle_codegen import config, gen_catalog
from vehicle_codegen.cli import render_all
from vehicle_codegen.yaml_checks import load_yaml

# D-068 polls every committed candidate, so the list is empty; the checks run against
# two standard PIDs that are not in the table (test data, never generated).
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
    return copy.deepcopy(load_yaml(config.CANDIDATES_YAML))


@pytest.fixture
def cand(committed):
    committed["candidates"] = copy.deepcopy(SAMPLE)
    return committed


def _errors(cand, vehicle):
    return gen_catalog.check_catalog(cand, vehicle)


def test_committed_catalog_is_clean(committed, vehicle):
    assert _errors(committed, vehicle) == []
    assert committed["candidates"] == []  # D-068: every candidate is polled


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
    for e in load_yaml(config.CANDIDATES_YAML)["candidates"]:
        assert e["name"] not in c_text
    assert "vehicle_cl250_candidates" not in c_text


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
