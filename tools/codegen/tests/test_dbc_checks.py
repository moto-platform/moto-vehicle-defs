"""Negative tests: each rule of the platform ID plan / E2E layout is enforced."""

import re

from conftest import parse_dbc

from moto_codegen.dbc_checks import check_platform_dbc


def errors_for(text: str) -> list[str]:
    return check_platform_dbc(parse_dbc(text))


def test_duplicate_data_id_is_rejected(platform_text):
    text = platform_text.replace('BA_ "E2E_DataID" BO_ 33 4129;', 'BA_ "E2E_DataID" BO_ 33 4128;')
    assert any("already used" in e for e in errors_for(text))


def test_safety_range_requires_e2e(platform_text):
    text = platform_text.replace('BA_ "E2E_Protected" BO_ 33 1;', 'BA_ "E2E_Protected" BO_ 33 0;')
    errs = errors_for(text)
    assert any("E2E is mandatory" in e for e in errs)
    assert any("E2E_DataID set but" in e for e in errs)


def test_missing_data_id_is_rejected(platform_text):
    text = platform_text.replace('BA_ "E2E_DataID" BO_ 34 4130;\n', "")
    assert any("E2E_DataID missing" in e for e in errors_for(text))


def test_e2e_layout_is_enforced(platform_text):
    text = platform_text.replace(
        ' SG_ E2E_COUNTER : 8|4@1+ (1,0) [0|15] "" SAFETY,LINUX\n SG_ LEAN_ANGLE_STATE',
        ' SG_ E2E_COUNTER : 8|3@1+ (1,0) [0|7] "" SAFETY,LINUX\n SG_ LEAN_ANGLE_STATE',
        1,
    )
    assert any("E2E_COUNTER must be 8|4" in e for e in errors_for(text))


def test_heartbeat_id_must_match_sender_node_id(platform_text):
    text = platform_text.replace("BO_ 131 HeartbeatIo: 8 IO", "BO_ 131 HeartbeatIo: 8 CONN")
    assert any("0x080 + NodeId" in e for e in errors_for(text))


def test_ids_outside_plan_are_rejected(platform_text):
    for bad_id in (0x005, 0x090, 0x7E0):
        text = re.sub(r"\b272\b", str(bad_id), platform_text)
        assert any("0x" in e and ("range" in e or "outside" in e) for e in errors_for(text)), bad_id


def test_naming_rules(platform_text):
    text = platform_text.replace("VehicleEngine", "vehicle_engine").replace(
        "ECU_PRESENT", "EcuPresent"
    )
    errs = errors_for(text)
    assert any("PascalCase" in e for e in errs)
    assert any("SNAKE_CASE" in e for e in errs)


def test_unknown_node_id_attribute(platform_text):
    text = platform_text.replace('BA_ "NodeId" BU_ SAFETY 2;', 'BA_ "NodeId" BU_ SAFETY 7;')
    assert any("NodeId 7 != 2" in e for e in errors_for(text))
