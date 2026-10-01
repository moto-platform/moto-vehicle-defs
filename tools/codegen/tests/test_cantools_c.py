"""C-7: the generated cantools C (pack/unpack/init/decode) at runtime, against cantools Python.

Each node's `platform.c` is built as a shared library and driven through ctypes. The
structs are read from the node's `platform.h`, so the test follows the DBC without
naming a message or signal. `_MISRA_FIXUPS` is checked on a synthetic DBC that makes
cantools emit every pattern a fixup rewrites.
"""

import ctypes
import random
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

import pytest
from cantools.database.can import Message, Signal
from cantools.database.can.c_source import camel_to_snake_case, generate
from conftest import parse_dbc

from moto_codegen import config, gen_c

CC = shutil.which("gcc") or shutil.which("cc")
pytestmark = pytest.mark.skipif(CC is None, reason="no C compiler")
FLAGS = ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wshadow", "-Wconversion"]
C_DIR = config.GEN_DIR / "c"
RANDOM_PAYLOADS = 10_000

_CTYPES = {
    f"{s}int{w}_t": getattr(ctypes, f"c_{s}int{w}") for s in ("", "u") for w in (8, 16, 32, 64)
}
_STRUCT_RE = re.compile(r"^struct (\w+)_t \{$(.*?)^\};$", re.MULTILINE | re.DOTALL)
_MEMBER_RE = re.compile(r"^    (u?int(?:8|16|32|64)_t) (\w+);$", re.MULTILINE)


@dataclass
class CMessage:
    msg: Message
    struct: Any  # ctypes.Structure subclass built from the header
    signals: dict[str, Signal]  # struct member -> DBC signal
    init: Any
    pack: Any | None
    unpack: Any | None
    decode: dict[str, Any]  # struct member -> <msg>_<member>_decode()
    encode: dict[str, Any]  # struct member -> <msg>_<member>_encode()
    in_range: dict[str, Any]  # struct member -> <msg>_<member>_is_in_range()


def _build(sources: list, out, flags=FLAGS):
    subprocess.run([CC, *flags, "-shared", "-fPIC", "-o", str(out), *map(str, sources)], check=True)
    return ctypes.CDLL(str(out))


def load_api(so, header: str, prefix: str, db) -> dict[str, CMessage]:
    by_snake = {camel_to_snake_case(m.name): m for m in db.messages}
    api = {}
    for found in _STRUCT_RE.finditer(header):
        name = found[1].removeprefix(f"{prefix}_")
        msg = by_snake[name]
        fields = [(m[2], _CTYPES[m[1]]) for m in _MEMBER_RE.finditer(found[2])]
        signals = {camel_to_snake_case(s.name): s for s in msg.signals}
        assert {f for f, _ in fields} == set(signals), name
        struct = type(name, (ctypes.Structure,), {"_fields_": fields})
        fn = f"{prefix}_{name}"

        def bind(symbol, restype, argtypes):
            if not re.search(rf"^\w+ {symbol}\(", header, re.MULTILINE):
                return None
            f = getattr(so, symbol)
            f.restype, f.argtypes = restype, argtypes
            return f

        ptr = ctypes.POINTER(struct)
        api[name] = CMessage(
            msg=msg,
            struct=struct,
            signals=signals,
            init=bind(f"{fn}_init", ctypes.c_int, [ptr]),
            pack=bind(f"{fn}_pack", ctypes.c_int, [ctypes.c_char_p, ptr, ctypes.c_size_t]),
            unpack=bind(f"{fn}_unpack", ctypes.c_int, [ptr, ctypes.c_char_p, ctypes.c_size_t]),
            decode={
                member: f
                for member, ctype in fields
                if (f := bind(f"{fn}_{member}_decode", ctypes.c_float, [ctype])) is not None
            },
            encode={
                member: f
                for member, ctype in fields
                if (f := bind(f"{fn}_{member}_encode", ctype, [ctypes.c_float])) is not None
            },
            in_range={
                member: f
                for member, ctype in fields
                if (f := bind(f"{fn}_{member}_is_in_range", ctypes.c_bool, [ctype])) is not None
            },
        )
    return api


def _raw_range(sig: Signal) -> tuple[int, int]:
    if sig.is_signed:
        return -(1 << (sig.length - 1)), (1 << (sig.length - 1)) - 1
    return 0, (1 << sig.length) - 1


def _boundaries(sig: Signal) -> list[int]:
    lo, hi = _raw_range(sig)
    values = {lo, lo + 1, hi - 1, hi, 0, min(1, hi)}
    for limit in (sig.minimum, sig.maximum):
        if limit is not None:
            raw = round(sig.conversion.scaled_to_raw(limit))
            values |= {raw - 1, raw, raw + 1}
    return sorted(v for v in values if lo <= v <= hi)


def _c_unpack(cm: CMessage, data: bytes, extra: int = 0) -> dict[str, int]:
    """`extra` trailing bytes: a frame longer than the DBC length must decode the same."""
    s = cm.struct()
    assert cm.unpack(ctypes.byref(s), data + b"\x5a" * extra, len(data) + extra) == 0
    return {member: getattr(s, member) for member in cm.signals}


def _c_pack(cm: CMessage, raw: dict[str, int]) -> bytes:
    s = cm.struct(**raw)
    buf = ctypes.create_string_buffer(b"\xa5" * 16, 16)
    assert cm.pack(buf, ctypes.byref(s), 16) == cm.msg.length
    assert buf.raw[cm.msg.length :] == b"\xa5" * (16 - cm.msg.length)  # writes `length` bytes only
    return buf.raw[: cm.msg.length]


def _py_raw(cm: CMessage, data: bytes) -> dict[str, int]:
    decoded = cm.msg.decode(data, decode_choices=False, scaling=False)
    return {member: decoded[sig.name] for member, sig in cm.signals.items()}


def _py_pack(cm: CMessage, raw: dict[str, int]) -> bytes:
    by_name = {sig.name: raw[member] for member, sig in cm.signals.items()}
    return bytes(cm.msg.encode(by_name, scaling=False, padding=False, strict=False))


def check_round_trip(cm: CMessage, rng: random.Random, payloads: int) -> None:
    """unpack == cantools decode, pack == cantools encode, both ways, and the guards."""
    n = cm.msg.length
    datas = [bytes(rng.randrange(256) for _ in range(n)) for _ in range(payloads)]
    datas += [b"\x00" * n, b"\xff" * n]
    raws = [_py_raw(cm, d) for d in datas]
    for member, sig in cm.signals.items():  # one signal at a boundary, the others 0 or all ones
        for base in (0x00, 0xFF):
            for value in _boundaries(sig):
                raw = _py_raw(cm, bytes([base]) * n)
                raw[member] = value
                raws.append(raw)
                datas.append(_py_pack(cm, raw))
    for data, raw in zip(datas, raws, strict=True):
        if cm.unpack is not None:
            extra = rng.choice((0, 1, 8 - n, 56))
            assert _c_unpack(cm, data, extra) == raw, (cm.msg.name, data.hex(), extra)
        if cm.pack is not None:
            packed = _c_pack(cm, raw)
            assert packed == _py_pack(cm, raw), (cm.msg.name, raw)
            assert _py_raw(cm, packed) == raw, (cm.msg.name, raw)
    for member, fn in cm.decode.items():
        sig = cm.signals[member]
        for value in {r[member] for r in raws}:
            expected = sig.conversion.raw_to_scaled(value, decode_choices=False)
            assert fn(value) == pytest.approx(expected, rel=1e-6, abs=1e-6), (sig.name, value)
    for member in cm.signals:
        check_signal_helpers(cm, member)
    if cm.pack is not None:
        check_pack_masks_each_member(cm)
    check_guards(cm)


def _truncate(sig: Signal, value: int) -> int:
    """`value` cut to the signal's width, as the DBC layout stores it."""
    value &= (1 << sig.length) - 1
    if sig.is_signed and value >> (sig.length - 1):
        value -= 1 << sig.length
    return value


def check_pack_masks_each_member(cm: CMessage) -> None:
    """A member with bits set beyond its signal width must not leak into its neighbours
    (the E2E CRC and counter share bytes with other signals)."""
    zero = dict.fromkeys(cm.signals, 0)
    for member, sig in cm.signals.items():
        width = 8 * ctypes.sizeof(dict(cm.struct._fields_)[member])
        all_ones = -1 if sig.is_signed else (1 << width) - 1
        packed = _c_pack(cm, {**zero, member: all_ones})
        assert _py_raw(cm, packed) == {**zero, member: _truncate(sig, all_ones)}, (sig.name,)


def check_signal_helpers(cm: CMessage, member: str) -> None:
    """is_in_range() at the raw limits and one step outside; encode() back to raw."""
    sig = cm.signals[member]
    lo, hi = _raw_range(sig)
    in_range, encode, decode = cm.in_range.get(member), cm.encode.get(member), cm.decode.get(member)
    if in_range is not None:
        raw_min = lo if sig.minimum is None else round(sig.conversion.scaled_to_raw(sig.minimum))
        raw_max = hi if sig.maximum is None else round(sig.conversion.scaled_to_raw(sig.maximum))
        for raw, expected in ((raw_min - 1, False), (raw_min, True), (raw_max, True),
                              (raw_max + 1, False)):  # fmt: skip
            if lo <= raw <= hi:
                assert in_range(raw) is expected, (sig.name, raw)
    if encode is not None and decode is not None:
        # float holds every integer up to 2^24 exactly; past that, encode()'s float-to-int
        # conversion can overflow (undefined in C). No platform signal is wider than 16 bits.
        for raw in (r for r in _boundaries(sig) if abs(r) <= 1 << 24):
            # C truncates (value - offset) / scale in float toward zero: one step at most.
            assert abs(encode(decode(raw)) - raw) <= 1, (sig.name, raw)


def check_guards(cm: CMessage) -> None:
    n = cm.msg.length
    assert cm.init(None) < 0
    s = cm.struct()
    ctypes.memset(ctypes.byref(s), 0xFF, ctypes.sizeof(s))
    assert cm.init(ctypes.byref(s)) == 0
    assert bytes(s) == bytes(ctypes.sizeof(s))
    if cm.unpack is not None:
        for size in range(n):  # too short: rejected, destination untouched
            ctypes.memset(ctypes.byref(s), 0x5A, ctypes.sizeof(s))
            assert cm.unpack(ctypes.byref(s), b"\xff" * n, size) < 0
            assert bytes(s) == b"\x5a" * ctypes.sizeof(s)
    if cm.pack is not None:
        for size in range(n):
            buf = ctypes.create_string_buffer(b"\xa5" * n, n)
            assert cm.pack(buf, ctypes.byref(cm.struct()), size) < 0
            assert buf.raw == b"\xa5" * n


@pytest.mark.parametrize("target", config.C_TARGETS, ids=lambda t: t.directory)
def test_node_cantools_code_matches_cantools_python(target, platform_db, tmp_path):
    d = C_DIR / target.directory
    so = _build([d / "platform.c"], tmp_path / "libplatform.so")
    api = load_api(so, (d / "platform.h").read_text(), "platform", platform_db)
    # The node gets pack for what it sends and unpack for what it receives, nothing else.
    by_name = {cm.msg.name: cm for cm in api.values()}
    sends = {m.name for m in platform_db.messages if gen_c._sends(target, m)}
    receives = {m.name for m in platform_db.messages if gen_c._receives(target, m)}
    assert {n for n, cm in by_name.items() if cm.pack} == sends
    assert {n for n, cm in by_name.items() if cm.unpack} == receives
    assert set(by_name) == sends | receives
    rng = random.Random(f"c7-{target.directory}")
    for cm in api.values():
        check_round_trip(cm, rng, RANDOM_PAYLOADS)


# Every pattern _MISRA_FIXUPS rewrites: memset (pack), the one-line NULL guard (init),
# and the unpack shift helpers at 16, 32 and 64 bits, little- and big-endian, signed.
SYNTHETIC_DBC = """VERSION ""

NS_ :

BS_:

BU_: TX RX

BO_ 256 Mixed: 8 TX
 SG_ U4 : 0|4@1+ (1,0) [0|15] "" RX
 SG_ S12 : 4|12@1- (0.5,-3) [-1027|1020.5] "" RX
 SG_ U16 : 16|16@1+ (1,0) [0|65535] "" RX
 SG_ S32 : 32|32@1- (1,0) [0|0] "" RX

BO_ 257 Wide: 8 TX
 SG_ U64 : 0|64@1+ (1,0) [0|0] "" RX

BO_ 258 Motorola: 8 TX
 SG_ M13 : 7|13@0+ (1,0) [0|8191] "" RX
 SG_ MS7 : 30|7@0- (1,0) [-64|63] "" RX
 SG_ M20 : 34|20@0+ (0.25,100) [100|262243.75] "" RX
"""


def test_misra_fixups_rewrite_every_pattern_and_keep_behaviour(tmp_path):
    db = parse_dbc(SYNTHETIC_DBC)
    header, source, _, _ = generate(
        db, "synth", "synth.h", "synth.c", "synth_fuzzer.c",
        floating_point_numbers=True, use_float=True,
    )  # fmt: skip
    memset, guard, widen = (p for p, _ in gen_c._MISRA_FIXUPS)
    # cantools still emits each pattern (a silent format change would make a fixup dead) ...
    assert len(memset.findall(source)) == 2 * len(db.messages)  # *_pack() and *_init()
    assert len(guard.findall(source)) == len(db.messages)  # only the *_init() NULL guards
    assert {m[1] for m in widen.finditer(source)} == {"uint16_t", "uint32_t", "uint64_t"}
    # ... and none survives the rewrite.
    fixed = gen_c._misra_fixups(source)
    for pattern, _ in gen_c._MISRA_FIXUPS:
        assert not pattern.search(fixed), pattern.pattern
    assert fixed.count("(void)memset(") == 2 * len(db.messages)
    # Same behaviour: original and rewritten source both match cantools Python.
    for kind, text in (("orig", source), ("fixed", fixed)):
        d = tmp_path / kind
        d.mkdir()
        (d / "synth.h").write_text(header)
        (d / "synth.c").write_text(text)
        flags = FLAGS if kind == "fixed" else [f for f in FLAGS if f != "-Werror"]
        so = _build([d / "synth.c"], d / "libsynth.so", flags)
        api = load_api(so, header, "synth", db)
        assert len(api) == len(db.messages)
        rng = random.Random("c7-synthetic")
        for cm in api.values():
            check_round_trip(cm, rng, 2000)
