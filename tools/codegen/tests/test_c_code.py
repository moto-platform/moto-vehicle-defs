"""Generated C: builds warning-free per node and matches the Python reference."""

import ctypes
import random
import shutil
import subprocess

import pytest
from cantools.database.can.c_source import camel_to_snake_case

from moto_codegen import config, e2e
from moto_codegen.yaml_checks import request_allowed

CC = shutil.which("gcc") or shutil.which("cc")
pytestmark = pytest.mark.skipif(CC is None, reason="no C compiler")
FLAGS = ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wshadow", "-Wconversion"]
C_DIR = config.GEN_DIR / "c"


@pytest.mark.parametrize("target", [t.directory for t in config.C_TARGETS])
def test_node_code_compiles_strict(target, tmp_path):
    sources = sorted((C_DIR / target).glob("*.c"))
    assert sources, f"gen/c/{target} is empty; run make gen"
    for src in sources:
        subprocess.run(
            [CC, *FLAGS, "-c", str(src), "-o", str(tmp_path / (src.stem + ".o"))], check=True
        )


class RxState(ctypes.Structure):
    _fields_ = [
        ("last_rx_ms", ctypes.c_uint32),
        ("last_counter", ctypes.c_uint8),
        ("synced", ctypes.c_bool),
    ]


class TxState(ctypes.Structure):
    _fields_ = [("counter", ctypes.c_uint8)]


@pytest.fixture(scope="module")
def lib(tmp_path_factory):
    out = tmp_path_factory.mktemp("lib") / "libgen.so"
    d = C_DIR / "hil_sim"  # restbus target: contains every message and the DID table
    srcs = [str(d / n) for n in ("moto_e2e.c", "platform_e2e.c", "vehicle_cl250.c", "platform.c")]
    subprocess.run([CC, *FLAGS, "-shared", "-fPIC", "-o", str(out), *srcs], check=True)
    so = ctypes.CDLL(str(out))
    so.moto_e2e_crc.restype = ctypes.c_uint8
    so.moto_e2e_crc.argtypes = [ctypes.c_uint16, ctypes.c_char_p, ctypes.c_size_t]
    so.moto_e2e_protect.argtypes = [
        ctypes.c_uint16,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.POINTER(TxState),
    ]
    so.moto_e2e_check.argtypes = [
        ctypes.c_uint16,
        ctypes.c_uint8,
        ctypes.c_uint32,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.POINTER(RxState),
        ctypes.c_uint32,
    ]
    so.moto_e2e_check_timeout.argtypes = [ctypes.POINTER(RxState), ctypes.c_uint32, ctypes.c_uint32]
    so.vehicle_cl250_request_allowed.restype = ctypes.c_bool
    so.vehicle_cl250_request_allowed.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    so.vehicle_cl250_frame_allowed.restype = ctypes.c_bool
    so.vehicle_cl250_frame_allowed.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    so.vehicle_cl250_parse_response.restype = ctypes.c_bool
    so.vehicle_cl250_parse_response.argtypes = [
        ctypes.c_uint16,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_float),
    ]
    so.vehicle_cl250_decode.restype = ctypes.c_bool
    so.vehicle_cl250_find.restype = ctypes.c_void_p
    so.vehicle_cl250_decode.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_float),
    ]
    return so


def test_crc_matches_reference(lib):
    rng = random.Random(1234)
    for _ in range(2000):
        data_id = rng.randrange(0x10000)
        payload = bytes(rng.randrange(256) for _ in range(rng.randrange(2, 9)))
        assert lib.moto_e2e_crc(data_id, payload, len(payload)) == e2e.compute_crc(data_id, payload)


@pytest.mark.parametrize("max_delta", [1, 2])
def test_protect_and_check_match_reference(lib, max_delta):
    rng = random.Random(99 + max_delta)
    data_id = 0x1021
    c_tx, py_tx = TxState(), e2e.TxState()
    c_rx, py_rx = RxState(), e2e.RxState()
    now = 0xFFFFFF00  # exercises the uint32 wrap
    prev = bytearray(8)
    seen = set()
    for _ in range(3000):
        buf = bytearray(rng.randrange(256) for _ in range(8))
        cbuf = ctypes.create_string_buffer(bytes(buf), 8)
        lib.moto_e2e_protect(data_id, cbuf, 8, ctypes.byref(c_tx))
        e2e.protect(data_id, buf, py_tx)
        assert cbuf.raw == bytes(buf)
        action = rng.random()
        if action < 0.1:  # corrupt
            buf[rng.randrange(8)] ^= 1 << rng.randrange(8)
        elif action < 0.15:  # drop
            continue
        elif action < 0.25:  # repeat the previous frame (frozen sender)
            buf = bytearray(prev)
        prev = bytearray(buf)
        now = (now + rng.choice([10, 20, 20, 20, 90])) & 0xFFFFFFFF
        for fn in ("timeout", "check"):
            if fn == "timeout":
                c = lib.moto_e2e_check_timeout(ctypes.byref(c_rx), 60, now)
                p = e2e.check_timeout(py_rx, 60, now)
            else:
                c = lib.moto_e2e_check(
                    data_id, max_delta, 60, bytes(buf), 8, ctypes.byref(c_rx), now
                )
                p = e2e.check(data_id, max_delta, 60, bytes(buf), py_rx, now)
            assert c == p
            seen.add(e2e.E2EStatus(p))
        assert (c_rx.last_counter, c_rx.last_rx_ms, c_rx.synced) == (
            py_rx.last_counter,
            py_rx.last_rx_ms,
            py_rx.synced,
        )
    # every receiver outcome except BAD_ARGUMENT must have been exercised
    expected = set(e2e.E2EStatus) - {e2e.E2EStatus.BAD_ARGUMENT}
    if max_delta == 1:
        expected.discard(e2e.E2EStatus.OK_SOME_LOST)  # impossible with max delta 1
    assert seen == expected


def test_request_allow_list_matches_policy_exhaustively(lib, vehicle):
    policy = vehicle["tester_policy"]
    for sid in range(256):
        assert lib.vehicle_cl250_request_allowed(bytes([sid]), 1) == request_allowed(policy, [sid])
        for sub in range(256):
            payload = bytes([sid, sub])
            assert lib.vehicle_cl250_request_allowed(payload, 2) == request_allowed(policy, payload)
    assert not lib.vehicle_cl250_request_allowed(None, 0)
    for sid in config.FORBIDDEN_VEHICLE_SERVICES:
        assert not any(lib.vehicle_cl250_request_allowed(bytes([sid, s]), 2) for s in range(256))


@pytest.mark.parametrize(
    ("did", "data", "expected"),
    [
        (0xF40C, b"\x1a\xf8", 1726.0),  # (0x1A*256+0xF8)/4
        (0xF40C, b"\xff\xff", 16383.75),
        (0xF40D, b"\x3c", 60.0),
        (0xF405, b"\x00", -40.0),
        (0xF405, b"\x7d", 85.0),
        (0xF411, b"\xff", 100.0),
        (0xF442, b"\x30\xd4", 12.5),
    ],
)
def test_did_decode(lib, did, data, expected):
    entry = lib.vehicle_cl250_find(did)
    assert entry
    out = ctypes.c_float()
    assert lib.vehicle_cl250_decode(entry, data, len(data), ctypes.byref(out))
    assert out.value == pytest.approx(expected, rel=1e-6)


def test_did_decode_rejects_short_and_unknown(lib):
    out = ctypes.c_float()
    assert not lib.vehicle_cl250_decode(
        lib.vehicle_cl250_find(0xF40C), b"\x01", 1, ctypes.byref(out)
    )
    assert lib.vehicle_cl250_find(0x1234) is None


def test_request_allow_list_is_exactly_d020(lib):
    """Golden test, independent of the YAML: what C allows is D-020, nothing more."""
    for sid in range(256):
        for sub in range(256):
            golden = config.ALLOWED_VEHICLE_SERVICES.get(sid, "absent")
            if golden == "absent":
                expected = False
            elif golden is None:
                expected = True
            else:
                expected = (sub & 0x7F) in golden
            assert lib.vehicle_cl250_request_allowed(bytes([sid, sub]), 2) == expected, (sid, sub)


@pytest.mark.parametrize(
    ("frame", "allowed"),
    [
        (b"\x02\x10\x03" + b"\xaa" * 5, True),
        (b"\x02\x3e\x80" + b"\xaa" * 5, True),
        (b"\x03\x22\xf4\x0c" + b"\xaa" * 4, True),
        (b"\x01\x04" + b"\xaa" * 6, False),  # OBD mode 04 = clear DTCs
        (b"\x02\x10\x02" + b"\xaa" * 5, False),
        (b"\x02\x11\x01" + b"\xaa" * 5, False),
        (b"\x10\x08\x22\xf4\x0c\x00\x00\x00", False),  # First Frame
        (b"\x21\x22\xf4\x0c\x00\x00\x00\x00", False),  # Consecutive Frame
        (b"\x00\x22\xf4\x0c\x00\x00\x00\x00", False),  # SF length 0
        (b"\x08\x22\xf4\x0c\x00\x00\x00\x00", False),  # SF length > 7
        (b"\x07\x22\xf4", False),  # length beyond the buffer
    ],
)
def test_frame_allowed(lib, frame, allowed):
    assert lib.vehicle_cl250_frame_allowed(frame, len(frame)) is allowed


@pytest.mark.parametrize(
    ("did", "frame", "ok", "value"),
    [
        (0xF40D, b"\x04\x62\xf4\x0d\x3c\xaa\xaa\xaa", True, 60.0),
        (0xF40C, b"\x05\x62\xf4\x0c\x1a\xf8\xaa\xaa", True, 1726.0),
        (0xF40D, b"\x04\x62\xf4\x11\x3c\xaa\xaa\xaa", False, None),  # late TPS answer
        (0xF40D, b"\x03\x7f\x22\x31\xaa\xaa\xaa\xaa", False, None),  # NRC
        (0xF40D, b"\x04\x7f\xf4\x0d\x3c\xaa\xaa\xaa", False, None),  # wrong SID, echo ok
        (0xF40D, b"\x04\x22\xf4\x0d\x3c\xaa\xaa\xaa", False, None),  # own request echoed
        (0xF40C, b"\x04\x62\xf4\x0c\x1a\xaa\xaa\xaa", False, None),  # too short
        (0xF40D, b"\x10\x08\x62\xf4\x0d\x3c\x00\x00", False, None),  # First Frame
        (0x1234, b"\x04\x62\x12\x34\x00\xaa\xaa\xaa", False, None),  # unknown DID
    ],
)
def test_parse_response(lib, did, frame, ok, value):
    out = ctypes.c_float()
    assert lib.vehicle_cl250_parse_response(did, frame, len(frame), ctypes.byref(out)) is ok
    if ok:
        assert out.value == pytest.approx(value)


def test_e2e_wrapper_constants(platform_db):
    from moto_codegen.dbc_checks import cycle_time_ms, e2e_data_id, is_e2e_protected

    header = (C_DIR / "hil_sim" / "platform_e2e.h").read_text()
    source = (C_DIR / "hil_sim" / "platform_e2e.c").read_text()
    for m in platform_db.messages:
        if not is_e2e_protected(m, platform_db):
            continue
        up = "PLATFORM_" + camel_to_snake_case(m.name).upper()
        assert e2e_data_id(m, platform_db) == 0x1000 + m.frame_id
        assert f"#define {up}_E2E_DATA_ID (0x{0x1000 + m.frame_id:04X}u)" in header
        assert f"#define {up}_E2E_TIMEOUT_MS ({3 * cycle_time_ms(m)}u)" in header
        fn = "platform_" + camel_to_snake_case(m.name)
        body = source.split(f"{fn}_e2e_check(const")[1].split("}")[0]
        assert f"{up}_E2E_DATA_ID" in body and f"{up}_E2E_TIMEOUT_MS" in body
