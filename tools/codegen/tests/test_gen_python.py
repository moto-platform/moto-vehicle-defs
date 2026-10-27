"""Every generated Python module compiles and imports (safety-reviewer, D-072 item 7)."""

import importlib
import sys

import pytest

from vehicle_codegen import config, e2e

PKG_DIR = config.GEN_DIR / "python"
MODULES = sorted(p.stem for p in (PKG_DIR / "vehicle_defs").glob("*.py") if p.stem != "__init__")


@pytest.mark.parametrize("module", MODULES)
def test_generated_module_imports(module, monkeypatch):
    monkeypatch.syspath_prepend(str(PKG_DIR))
    for name in [n for n in sys.modules if n == "vehicle_defs" or n.startswith("vehicle_defs.")]:
        monkeypatch.delitem(sys.modules, name)
    importlib.import_module(f"vehicle_defs.{module}")


@pytest.mark.parametrize("data_id", [0x1023, 0x1120])
def test_all_zero_frame_fails_crc_for_every_counter(data_id):
    for counter in range(16):
        frame = bytes([0, counter]) + bytes(6)
        status = e2e.check(data_id, 1, 60, frame, e2e.RxState(), 0)
        assert status == e2e.E2EStatus.WRONG_CRC, (data_id, counter)


def test_heartbeat_payload_fails_as_warning_status():
    # Masquerade from the same sender: a protected 0x082 payload checked as 0x023.
    frame = bytearray(8)
    e2e.protect(0x1082, frame, e2e.TxState())
    status = e2e.check(0x1023, 1, 60, bytes(frame), e2e.RxState(), 0)
    assert status == e2e.E2EStatus.WRONG_CRC
