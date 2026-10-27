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


def _platform_module(monkeypatch):
    monkeypatch.syspath_prepend(str(PKG_DIR))
    for name in [n for n in sys.modules if n == "vehicle_defs" or n.startswith("vehicle_defs.")]:
        monkeypatch.delitem(sys.modules, name)
    return importlib.import_module("vehicle_defs.platform")


def _pack(table, values):
    """Pack physical values with only the generated table (little-endian, as vehicle-server does)."""
    raw_frame = 0
    for sig in table:
        assert sig.byte_order == "little_endian"
        raw = round((values[sig.name] - sig.offset) / sig.factor)
        raw &= (1 << sig.length) - 1
        raw_frame |= raw << sig.start
    return raw_frame


def test_signal_table_matches_cantools(monkeypatch, platform_db):
    platform = _platform_module(monkeypatch)
    assert list(platform.SIGNALS) == [
        m.name for m in sorted(platform_db.messages, key=lambda m: m.frame_id)
    ]
    for msg in platform_db.messages:
        table = platform.SIGNALS[msg.name]
        assert [s.name for s in table] == [s.name for s in msg.signals]
        for t, s in zip(table, msg.signals, strict=True):
            assert (t.start, t.length, t.byte_order, t.is_signed) == (
                s.start,
                s.length,
                s.byte_order,
                s.is_signed,
            )
            assert (t.factor, t.offset, t.minimum, t.maximum) == (
                s.scale,
                s.offset,
                s.minimum,
                s.maximum,
            )
            assert t.unit == (s.unit or "")
            assert t.receivers == tuple(s.receivers)
            expect = {k: str(v) for k, v in s.choices.items()} if s.choices else None
            assert t.choices == expect
            assert (t.is_multiplexer, t.multiplexer_signal) == (
                s.is_multiplexer,
                s.multiplexer_signal,
            )


def test_signal_table_packs_like_cantools(monkeypatch, platform_db):
    platform = _platform_module(monkeypatch)
    for msg in platform_db.messages:
        table = platform.SIGNALS[msg.name]
        # skip protected E2E bytes: compare only the payload bits the table describes
        values = {}
        for t in table:
            lo = t.minimum if t.minimum is not None else 0
            hi = t.maximum if t.maximum is not None else lo
            values[t.name] = (lo + hi) / 2 if not t.choices else min(t.choices)
        expected = int.from_bytes(msg.encode(values, scaling=True, strict=False), "little")
        mask = 0
        for t in table:
            mask |= ((1 << t.length) - 1) << t.start
        got = _pack(table, values)
        assert got & mask == expected & mask, msg.name
