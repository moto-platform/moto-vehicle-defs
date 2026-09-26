"""The committed definitions pass every check."""

from moto_codegen import config, gen_vss
from moto_codegen.dbc_checks import check_cl250_dbc, check_platform_dbc, load_dbc
from moto_codegen.yaml_checks import check_dids, check_vehicle, load_yaml


def test_platform_dbc_is_consistent(platform_db):
    assert check_platform_dbc(platform_db) == []


def test_cl250_dbc_is_a_skeleton():
    db = load_dbc(config.CL250_DBC)
    assert check_cl250_dbc(db) == []
    assert db.messages == []  # Q-001: no passive broadcast known yet


def test_vehicle_yaml_is_consistent(platform_db, vehicle):
    assert check_vehicle(vehicle, platform_db) == []


def test_every_vehicle_did_is_verified(vehicle):
    assert all(d["verified"] for d in vehicle["dids"])


def test_dids_yaml_skeleton():
    assert check_dids(load_yaml(config.DIDS_YAML)) == []


def test_overlay_maps_existing_signals_only(platform_db):
    overlay = gen_vss.load_overlay()
    # Base paths are checked in test_gen_drift (needs the pinned VSS download).
    errors = [
        e for e in gen_vss.check_overlay(overlay, set(overlay), platform_db) if "COVESA" not in e
    ]
    assert errors == []
    extensions = {p for p in overlay if p.startswith("Vehicle.Motorcycle")}
    assert extensions == set(gen_vss.APPROVED_EXTENSIONS)  # only user-approved paths (D-028)


def test_overlay_rejects_ambiguous_and_unknown_choices(platform_db):
    bad = {
        "Vehicle.Speed": {"dbc2vss": {"signal": "NODE_MODE", "interval_ms": 100}},
        "Vehicle.Motorcycle.IsEcuPresent": {
            "dbc2vss": {
                "signal": "ECU_PRESENT",
                "interval_ms": 100,
                "transform": {"mapping": [{"from": "MAYBE", "to": True}]},
            }
        },
    }
    errors = gen_vss.check_overlay(bad, set(bad), platform_db)
    assert any("ambiguous" in e for e in errors)
    assert any("unknown choice MAYBE" in e for e in errors)
