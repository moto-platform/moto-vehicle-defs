from __future__ import annotations

import copy
import dataclasses

import pytest

from moto_codegen import checks
from moto_codegen.sources import load


def test_sources_pass(root):
    checks.run(load(root))


@pytest.mark.parametrize("sid", [0x11, 0x14, 0x27, 0x2E, 0x2F, 0x31, 0x34, 0x36, 0x37, 0x85])
def test_forbidden_service_is_rejected(root, sid):
    src = load(root)
    vehicle = copy.deepcopy(src.vehicle)
    vehicle["allowed_services"].append({"sid": sid, "name": "Bad"})
    with pytest.raises(checks.CheckError, match=f"0x{sid:02X}"):
        checks.run(dataclasses.replace(src, vehicle=vehicle))


def test_programming_session_is_rejected(root):
    src = load(root)
    vehicle = copy.deepcopy(src.vehicle)
    vehicle["allowed_services"][0]["subfunctions"] = [0x01, 0x02, 0x03]
    with pytest.raises(checks.CheckError, match="D-020"):
        checks.run(dataclasses.replace(src, vehicle=vehicle))


def test_safety_range_requires_e2e(root):
    src = load(root)
    msg = src.platform.get_message_by_name("VehicleSpeed")
    msg.dbc.attributes["E2E_Protected"].value = 0
    with pytest.raises(checks.CheckError, match="requires E2E_Protected"):
        checks.run(src)


def test_duplicate_data_id_is_rejected(root):
    src = load(root)
    msg = src.platform.get_message_by_name("LeanEstimate")
    msg.dbc.attributes["E2E_DataID"].value = 33
    with pytest.raises(checks.CheckError, match="already used"):
        checks.run(src)


def test_overlay_signal_must_exist(root):
    src = load(root)
    overlay = copy.deepcopy(src.overlay)
    overlay["Vehicle.Speed"]["dbc2vss"]["signal"] = "NO_SUCH_SIGNAL"
    with pytest.raises(checks.CheckError, match="NO_SUCH_SIGNAL"):
        checks.run(dataclasses.replace(src, overlay=overlay))
