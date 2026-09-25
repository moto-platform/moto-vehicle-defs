from __future__ import annotations

import random

from moto_defs import e2e, platform, vehicle_cl250

S = e2e.E2EStatus


def _frames(data_id: int, n: int, length: int = 4) -> list[bytearray]:
    tx = e2e.TxState()
    out = []
    for i in range(n):
        f = bytearray(length)
        f[2] = i & 0xFF
        e2e.protect(data_id, f, tx)
        out.append(f)
    return out


def test_crc8_sae_j1850_check_value():
    # Standard check value: CRC-8/SAE-J1850 over "123456789" = 0x4B. DataID supplies the
    # first two bytes ("1", "2"); data[0] is the CRC slot and is skipped.
    assert e2e.crc8(0x3231, b"\x00" + b"3456789") == 0x4B


def test_protect_then_check_sequence_and_counter_wrap():
    data_id = platform.MESSAGES["VehicleSpeed"]["e2e_data_id"]
    rx = e2e.RxState(timeout_ms=300)
    statuses = [
        e2e.check(data_id, f, rx, now_ms=t * 100) for t, f in enumerate(_frames(data_id, 40))
    ]
    assert statuses[0] is S.INITIAL
    assert all(s is S.OK for s in statuses[1:])  # includes several 15 -> 0 wraps
    assert e2e.check_timeout(rx, now_ms=3900 + 300) is S.OK
    assert e2e.check_timeout(rx, now_ms=3900 + 301) is S.TIMEOUT


def test_check_detects_faults():
    data_id = 48
    frames = _frames(data_id, 4)
    rx = e2e.RxState(timeout_ms=300)
    assert e2e.check_timeout(rx, 0) is S.TIMEOUT
    assert e2e.check(data_id, frames[0], rx, 0) is S.INITIAL
    assert e2e.check_timeout(rx, 0) is S.TIMEOUT
    assert e2e.check(data_id, frames[1], rx, 1) is S.OK
    assert e2e.check(data_id, frames[1], rx, 2) is S.REPEATED
    assert e2e.check(data_id, frames[3], rx, 3) is S.WRONG_SEQUENCE
    corrupted = bytearray(frames[3])
    corrupted[2] ^= 0x01
    assert e2e.check(data_id, corrupted, rx, 4) is S.CRC_ERROR
    assert e2e.check(data_id, frames[0][:1], rx, 5) is S.BAD_LENGTH
    assert e2e.check(data_id, frames[0] + bytes(5), rx, 5) is S.BAD_LENGTH


def test_wrong_data_id_is_crc_error():
    lean = _frames(platform.MESSAGES["LeanEstimate"]["e2e_data_id"], 1, length=8)[0]
    other = platform.MESSAGES["CorneringParamEstimate"]["e2e_data_id"]
    assert e2e.check(other, lean, e2e.RxState(timeout_ms=300), 0) is S.CRC_ERROR


def test_sixteen_lost_frames_are_not_accepted_as_plus_one():
    frames = _frames(32, 20)
    rx = e2e.RxState(timeout_ms=60)
    assert e2e.check(32, frames[0], rx, 0) is S.INITIAL
    assert e2e.check(32, frames[1], rx, 20) is S.OK
    # Frames 2..17 lost (16 frames): frame 18 has counter 2 = last + 1 after the wrap.
    assert e2e.check(32, frames[18], rx, 20 * 17) is S.INITIAL
    assert e2e.check(32, frames[19], rx, 20 * 18) is S.OK


def test_frozen_sender_resuming_after_timeout_is_initial():
    frames = _frames(129, 3)
    rx = e2e.RxState(timeout_ms=300)
    assert e2e.check(129, frames[0], rx, 0) is S.INITIAL
    assert e2e.check(129, frames[1], rx, 100) is S.OK
    for t in range(200, 5000, 100):  # frozen: the same frame is repeated for 5 s
        assert e2e.check(129, frames[1], rx, t) in (S.REPEATED, S.INITIAL)
    assert e2e.check_timeout(rx, 5000) is S.TIMEOUT
    rx2 = e2e.RxState(timeout_ms=300)
    e2e.check(129, frames[0], rx2, 0)
    e2e.check(129, frames[1], rx2, 100)
    assert e2e.check(129, frames[2], rx2, 5100) is S.INITIAL  # silent for 5 s, then resumes


def test_timeout_wraps_at_32_bits():
    frames = _frames(48, 2)
    rx = e2e.RxState(timeout_ms=300)
    e2e.check(48, frames[0], rx, 0xFFFFFF00)
    assert e2e.check(48, frames[1], rx, 0x10) is S.OK
    assert e2e.check_timeout(rx, 0x20) is S.OK


def test_vehicle_decode_matches_d019_formulas():
    rng = random.Random(1)
    for _ in range(100):
        a, b = rng.randrange(256), rng.randrange(256)
        assert vehicle_cl250.decode(0xF40C, bytes([a, b])) == (a * 256 + b) / 4
        assert vehicle_cl250.decode(0xF40D, bytes([a])) == a
        assert vehicle_cl250.decode(0xF405, bytes([a])) == a - 40
        assert vehicle_cl250.decode(0xF411, bytes([a])) == a * 100 / 255
        assert vehicle_cl250.decode(0xF442, bytes([a, b])) == (a * 256 + b) / 1000


ALLOWED = [
    b"\x10\x01",
    b"\x10\x03",
    b"\x3e\x80",
    b"\x3e\x00",
    b"\x22\xf4\x0c",
    b"\x19\x02\xff",
    b"\x01\x0c",
    b"\x09\x02",
]
FORBIDDEN = [
    b"\x10\x02",
    b"\x10\x81",
    b"\x10\x82",
    b"\x10\x83",
    b"\x11\x01",
    b"\x14\xff\xff\xff",
    b"\x27\x01",
    b"\x2e\xf1\x90",
    b"\x2f\x00",
    b"\x31\x01",
    b"\x34\x00",
    b"\x36\x01",
    b"\x37",
    b"\x04",
    b"\x04\x00",
    b"\x10",
    b"\x3e",
    b"\x22\xf4",
    b"\x01",
    b"\x09",
    b"",
]


def test_request_rules_are_d020():
    assert all(vehicle_cl250._request_allowed(r) for r in ALLOWED)
    assert not any(vehicle_cl250._request_allowed(r) for r in FORBIDDEN)


def test_frame_guard():
    req, fb = 0x18DA10F1, 0x7E0

    def frame(payload: bytes) -> bytes:
        return (bytes([len(payload)]) + payload).ljust(8, b"\xaa")

    for r in ALLOWED:
        assert vehicle_cl250.frame_allowed(req, True, frame(r))
        assert vehicle_cl250.frame_allowed(fb, False, frame(r))
    for r in FORBIDDEN:
        assert not vehicle_cl250.frame_allowed(req, True, frame(r))
    ok = frame(b"\x22\xf4\x0c")
    assert not vehicle_cl250.frame_allowed(req, False, ok)  # wrong ID type
    assert not vehicle_cl250.frame_allowed(0x7DF, False, ok)  # functional ID not allowed
    assert not vehicle_cl250.frame_allowed(0x18DAF110, True, ok)  # response ID
    # A raw payload passed as a frame: 0x01 looks like SF_DL=1 carrying OBD 0x04 (clear DTC).
    assert not vehicle_cl250.frame_allowed(req, True, b"\x01\x04\xaa\xaa\xaa\xaa\xaa\xaa")
    assert not vehicle_cl250.frame_allowed(req, True, b"\x10\x14\x22\xf4\x0c\xaa\xaa\xaa")  # FF
    assert not vehicle_cl250.frame_allowed(req, True, b"\x05\x22\xf4\x0c")  # SF_DL > DLC-1
    assert not vehicle_cl250.frame_allowed(req, True, b"\x00\x22")  # SF_DL 0
