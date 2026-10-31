"""STM32H755 M7<->M4 mailbox layout (D-072 item 4c, D-093).

mailbox/h755_mailbox.yaml names the region, the slot order and one HSEM ID per slot.
Each slot is a platform.dbc message: frame ID and length come from the DBC. The slot
set is checked against the messages SAFETY receives and sends, so a new SAFETY message
cannot skip the mailbox. Generated: one identical C header for rt_core and safety, and
a Python module for host tools.
"""

from __future__ import annotations

import json
import zlib
from typing import Any, NamedTuple

from cantools.database.can import Database
from cantools.database.can.c_source import camel_to_snake_case

from . import config
from .c_e2e_templates import BANNER
from .dbc_checks import cycle_time_ms, e2e_data_id, is_e2e_protected
from .gen_python import BANNER as PY_BANNER

SOURCE = "mailbox/h755_mailbox.yaml"

HEADER_BYTES = 32  # m7_layout_id, m4_layout_id, 24 reserved bytes
SLOT_BYTES = 16  # write_seq u32, len u8, 3 reserved, data[8]
ALIGN_BYTES = 32
SRAM4_FIRST = 0x38000000  # STM32H755 SRAM4 (D3 domain), 64 KiB
SRAM4_LAST = 0x3800FFFF
MAX_DATA_BYTES = 8  # classic CAN payload
HSEM_IDS = range(1, 32)  # ID 0 stays free for vendor boot code (D-093 item 5)

DIRECTIONS = {"m7_to_m4": 1, "m4_to_m7": 2}  # integer codes used in the C header
CLASSES = {"safety": 1, "qm": 2}

REGION_KEYS = {"name", "base_address", "reserved_bytes", "verified", "note"}
SLOT_KEYS = {"message", "direction", "class", "hsem_id"}


class Slot(NamedTuple):
    index: int
    message: str
    frame_id: int
    length: int
    direction: str
    cls: str
    hsem_id: int
    offset: int  # from the region base


class Layout(NamedTuple):
    name: str
    base_address: int
    reserved_bytes: int
    verified: bool
    slots: tuple[Slot, ...]

    @property
    def used_bytes(self) -> int:
        return HEADER_BYTES + SLOT_BYTES * len(self.slots)


def _is_int(value: object) -> bool:
    return type(value) is int


def _dbc_sets(db: Database) -> tuple[set[str], set[str]]:
    """(messages SAFETY receives, messages SAFETY sends) as the DBC says."""
    received = {m.name for m in db.messages if any("SAFETY" in s.receivers for s in m.signals)}
    sent = {m.name for m in db.messages if "SAFETY" in m.senders}
    return received, sent


def check_mailbox(doc: dict[str, Any], db: Database) -> list[str]:
    errors: list[str] = []
    extra = set(doc) - {"region", "slots"}
    if extra:
        errors.append(f"mailbox: unknown top-level keys {sorted(extra)}")
    region = doc.get("region")
    slots = doc.get("slots")
    if not isinstance(region, dict) or not isinstance(slots, list) or not slots:
        return errors + ["mailbox: needs a region mapping and a non-empty slots list"]

    extra = set(region) - REGION_KEYS
    if extra:
        errors.append(f"mailbox: unknown region keys {sorted(extra)}")
    for key in ("name", "base_address", "reserved_bytes", "verified", "note"):
        if key not in region:
            errors.append(f"mailbox: region.{key} missing")
    if not isinstance(region.get("name"), str) or not region.get("name"):
        errors.append("mailbox: region.name must be a non-empty string")
    if not isinstance(region.get("verified"), bool):
        errors.append("mailbox: region.verified must be true or false")
    if not isinstance(region.get("note"), str) or not region.get("note"):
        errors.append("mailbox: region.note must be a non-empty string")
    base, reserved = region.get("base_address"), region.get("reserved_bytes")
    if not _is_int(base) or not _is_int(reserved):
        errors.append("mailbox: region.base_address and region.reserved_bytes must be integers")
    else:
        if base % ALIGN_BYTES:
            errors.append(
                f"mailbox: region.base_address 0x{base:08X} is not {ALIGN_BYTES}-byte aligned"
            )
        if reserved < ALIGN_BYTES or reserved & (reserved - 1):
            errors.append(
                f"mailbox: region.reserved_bytes {reserved} must be a power of two >= "
                f"{ALIGN_BYTES} (one MPU region)"
            )
        elif base % reserved:
            errors.append(
                f"mailbox: region.base_address 0x{base:08X} is not a multiple of "
                f"region.reserved_bytes {reserved} (MPU region rule)"
            )
        if not SRAM4_FIRST <= base or base + reserved - 1 > SRAM4_LAST:
            errors.append(
                f"mailbox: region 0x{base:08X}+{reserved} is outside SRAM4 "
                f"0x{SRAM4_FIRST:08X}..0x{SRAM4_LAST:08X}"
            )
        used = HEADER_BYTES + SLOT_BYTES * len(slots)
        if used > reserved:
            errors.append(f"mailbox: used size {used} B exceeds region.reserved_bytes {reserved}")

    received, sent = _dbc_sets(db)
    if received != config.SAFETY_RX_ALLOWED:
        errors.append(
            f"mailbox: the DBC says SAFETY receives {sorted(received)}, but "
            "SAFETY_RX_SAFETY_INPUTS | SAFETY_RX_QM_IMMOBILIZER is "
            f"{sorted(config.SAFETY_RX_ALLOWED)}"
        )
    by_name = {m.name: m for m in db.messages}
    seen: dict[str, int] = {}
    hsem_seen: dict[int, str] = {}
    dir_of: dict[str, str] = {}
    for i, slot in enumerate(slots):
        if not isinstance(slot, dict):
            errors.append(f"mailbox: slot {i} must be a mapping")
            continue
        name = slot.get("message")
        label = f"slot {i} ({name})"
        extra = set(slot) - SLOT_KEYS
        if extra:
            errors.append(f"mailbox: {label}: unknown keys {sorted(extra)}")
        for key in SLOT_KEYS:
            if key not in slot:
                errors.append(f"mailbox: {label}: {key} missing")
        if name in seen:
            errors.append(f"mailbox: {label}: message {name} is already slot {seen[name]}")
        seen.setdefault(name, i)
        msg = by_name.get(name)
        if msg is None:
            errors.append(f"mailbox: {label}: unknown message {name} (not in platform.dbc)")
        else:
            if msg.length > MAX_DATA_BYTES:
                errors.append(f"mailbox: {label}: DBC length {msg.length} exceeds {MAX_DATA_BYTES}")
            if not is_e2e_protected(msg, db) or not e2e_data_id(msg, db):
                errors.append(f"mailbox: {label}: message is not E2E-protected in platform.dbc")
        direction, cls = slot.get("direction"), slot.get("class")
        if direction not in DIRECTIONS:
            errors.append(f"mailbox: {label}: direction must be one of {sorted(DIRECTIONS)}")
        if cls not in CLASSES:
            errors.append(f"mailbox: {label}: class must be one of {sorted(CLASSES)}")
        if isinstance(name, str):
            dir_of[name] = direction
            want_dir = (
                "m7_to_m4"
                if name in config.SAFETY_RX_ALLOWED
                else "m4_to_m7"
                if name in sent
                else None
            )
            if want_dir is not None and direction in DIRECTIONS and direction != want_dir:
                errors.append(f"mailbox: {label}: direction must be {want_dir}")
            want_cls = (
                "qm"
                if name in config.SAFETY_RX_QM_IMMOBILIZER
                else "safety"
                if name in config.SAFETY_RX_SAFETY_INPUTS or name in sent
                else None
            )
            if want_cls is not None and cls in CLASSES and cls != want_cls:
                errors.append(f"mailbox: {label}: class must be {want_cls}")
        hsem = slot.get("hsem_id")
        if not _is_int(hsem) or hsem not in HSEM_IDS:
            errors.append(f"mailbox: {label}: hsem_id must be an integer 1..31")
        elif hsem in hsem_seen:
            errors.append(f"mailbox: {label}: hsem_id {hsem} is already used by {hsem_seen[hsem]}")
        else:
            hsem_seen[hsem] = str(name)

    names = {s.get("message") for s in slots if isinstance(s, dict)}
    for name in sorted(config.SAFETY_RX_ALLOWED - names):
        errors.append(f"mailbox: missing m7_to_m4 slot for {name} (SAFETY receives it)")
    for name in sorted(sent - names):
        errors.append(f"mailbox: missing m4_to_m7 slot for {name} (SAFETY sends it)")
    for name in sorted(n for n in names - config.SAFETY_RX_ALLOWED - sent if n in by_name):
        errors.append(f"mailbox: slot for {name}, which SAFETY neither receives nor sends")
    return errors


def resolve(doc: dict[str, Any], db: Database) -> Layout:
    """The layout of a checked YAML, with frame IDs and lengths taken from the DBC."""
    by_name = {m.name: m for m in db.messages}
    slots = tuple(
        Slot(
            index=i,
            message=s["message"],
            frame_id=by_name[s["message"]].frame_id,
            length=by_name[s["message"]].length,
            direction=s["direction"],
            cls=s["class"],
            hsem_id=s["hsem_id"],
            offset=HEADER_BYTES + SLOT_BYTES * i,
        )
        for i, s in enumerate(doc["slots"])
    )
    r = doc["region"]
    return Layout(r["name"], r["base_address"], r["reserved_bytes"], r["verified"], slots)


def _message_def(name: str, db: Database) -> dict[str, Any]:
    """The parts of a platform.dbc message that fix the payload bytes and their E2E use."""
    msg = next(m for m in db.messages if m.name == name)
    signals = [
        {
            "name": sig.name,
            "start": sig.start,
            "length": sig.length,
            "byte_order": sig.byte_order,
            "is_signed": bool(sig.is_signed),
            "factor": sig.scale,
            "offset": sig.offset,
            "minimum": sig.minimum,
            "maximum": sig.maximum,
            "choices": [[k, str(v)] for k, v in sorted((sig.choices or {}).items())],
        }
        for sig in sorted(msg.signals, key=lambda sg: (sg.start, sg.name))
    ]
    return {
        "e2e_data_id": e2e_data_id(msg, db),
        "e2e_protected": is_e2e_protected(msg, db),
        "cycle_time_ms": cycle_time_ms(msg),
        "signals": signals,
    }


def layout_id(layout: Layout, db: Database) -> int:
    """CRC-32 (zlib.crc32, IEEE 802.3, init/xorout 0xFFFFFFFF) of the canonical layout.

    Canonical serialisation: UTF-8 JSON with sorted keys and no whitespace
    (separators "," and ":", Python json.dumps defaults otherwise: ensure_ascii, floats as
    repr, null for no limit) of
    {"base_address", "header_bytes", "reserved_bytes", "slot_bytes",
     "slots": [{"class", "direction", "frame_id", "hsem_id", "index", "length",
                "message", "offset",
                "dbc": {"cycle_time_ms", "e2e_data_id", "e2e_protected",
                        "signals": [{"name", "start", "length", "byte_order",
                                     "is_signed", "factor", "offset", "minimum",
                                     "maximum", "choices": [[raw, name], ...]}, ...]}},
               ...]}
    in slot order; the signals are sorted by (start bit, name) and the choices by raw
    value; integers are decimal. "dbc" is the slot message's definition in
    dbc/platform.dbc, so a changed bit position, scale, value table, DataID or cycle time
    changes the ID. The region name, `verified` and `note` are not part of it.
    """
    canonical = {
        "base_address": layout.base_address,
        "reserved_bytes": layout.reserved_bytes,
        "header_bytes": HEADER_BYTES,
        "slot_bytes": SLOT_BYTES,
        "slots": [
            {
                "index": s.index,
                "message": s.message,
                "frame_id": s.frame_id,
                "length": s.length,
                "direction": s.direction,
                "class": s.cls,
                "hsem_id": s.hsem_id,
                "offset": s.offset,
                "dbc": _message_def(s.message, db),
            }
            for s in layout.slots
        ],
    }
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF


def generate_c(doc: dict[str, Any], db: Database) -> dict[str, str]:
    lay = resolve(doc, db)
    n = len(lay.slots)
    p = "PLATFORM_MAILBOX_"
    h = [
        BANNER.format(source=SOURCE),
        "#ifndef PLATFORM_MAILBOX_H",
        "#define PLATFORM_MAILBOX_H",
        "",
    ]
    h += ["#include <stddef.h>", "#include <stdint.h>", '#include "platform.h"', ""]
    h += [
        "/* STM32H755 M7<->M4 mailbox (D-072 item 4c, D-093). Little-endian, 4-byte aligned:",
        " * a 32 B header, then one 16 B slot per message. A slot carries the platform payload",
        " * verbatim (E2E CRC and counter included); frame ID and length come from platform.dbc.",
        " * Header-only: the image places the object itself (linker section).",
        " *",
        " * Access rules (D-093 item 5):",
        " * - Access only through a volatile platform_mailbox_t pointer.",
        " * - One-step HSEM take with IRQs masked, DMB after the take, DMB/DSB before the release.",
        " * - Copy the payload as two aligned 32-bit words, never memcpy.",
        " * - Writer: increment write_seq after the copy, behind a barrier. Reader: compare",
        " *   write_seq for inequality only (a wrap is harmless).",
        " * - Reader: len != SLOT_<X>_LENGTH is no frame; call the E2E check with the",
        " *   compile-time length, never with len.",
        " * - Each core writes only the fields it owns (its layout word and the slots of its",
        " *   direction) and never clears the region. */",
        f"#define {p}REGION_ADDR (0x{lay.base_address:08X}u) /* {lay.name}, SRAM4 (D3) */",
        "/* Release and bike images must refuse to build while ADDR_VERIFIED is 0: the check",
        " * lives in the consuming images. */",
        f"#define {p}ADDR_VERIFIED ({int(lay.verified)}) /* 0: not yet confirmed on the board */",
        f"#define {p}RESERVED_BYTES ({lay.reserved_bytes}u)",
        f"#define {p}USED_BYTES ({lay.used_bytes}u)",
        f"#define {p}HEADER_BYTES ({HEADER_BYTES}u)",
        f"#define {p}SLOT_BYTES ({SLOT_BYTES}u)",
        f"#define {p}SLOT_COUNT ({n}u)",
        "",
        "/* CRC-32 of the resolved layout (gen_mailbox.layout_id()): each core writes its own",
        " * header word at boot, and a reader takes no frame while the peer's word differs. */",
        f"#define {p}LAYOUT_ID (0x{layout_id(lay, db):08X}u)",
        "",
        "/* Direction and class codes of the slot macros below. */",
        f"#define {p}DIR_M7_TO_M4 ({DIRECTIONS['m7_to_m4']}u)",
        f"#define {p}DIR_M4_TO_M7 ({DIRECTIONS['m4_to_m7']}u)",
        f"#define {p}CLASS_SAFETY ({CLASSES['safety']}u)",
        f"#define {p}CLASS_QM ({CLASSES['qm']}u)",
        "",
        "/* Slots in order. OFFSET is from the region base; HSEM_ID is the slot's semaphore. */",
    ]
    for s in lay.slots:
        up = camel_to_snake_case(s.message).upper()
        sp = f"{p}SLOT_{up}_"
        h += [
            f"#define {sp}INDEX ({s.index}u) /* {s.message} */",
            f"#define {sp}FRAME_ID (PLATFORM_{up}_FRAME_ID)",
            f"#define {sp}LENGTH (PLATFORM_{up}_LENGTH)",
            f"#define {sp}HSEM_ID ({s.hsem_id}u)",
            f"#define {sp}DIRECTION ({p}DIR_{s.direction.upper()})",
            f"#define {sp}CLASS ({p}CLASS_{s.cls.upper()})",
            f"#define {sp}OFFSET ({s.offset}u)",
        ]
    h += [
        "",
        "typedef struct {",
        "    uint32_t m7_layout_id; /* written by the M7 at boot */",
        "    uint32_t m4_layout_id; /* written by the M4 at boot */",
        f"    uint8_t reserved[{HEADER_BYTES - 8}];",
        "} platform_mailbox_header_t;",
        "",
        "typedef struct {",
        "    uint32_t write_seq; /* incremented by the writer after the copy, under the HSEM */",
        "    uint8_t len; /* DBC length; a reader accepts only SLOT_<X>_LENGTH, never uses len */",
        "    uint8_t reserved[3];",
        f"    uint8_t data[{MAX_DATA_BYTES}];",
        "} platform_mailbox_slot_t;",
        "",
        "typedef struct {",
        "    platform_mailbox_header_t header;",
        f"    platform_mailbox_slot_t slot[{p}SLOT_COUNT];",
        "} platform_mailbox_t;",
        "",
        "/* Compile-time checks (C99): a negative array size fails the build. */",
        f"#if ({p}REGION_ADDR % {ALIGN_BYTES}u) != 0u",
        "#error platform mailbox base address is not 32-byte aligned",
        "#endif",
        f"#if ({p}USED_BYTES > {p}RESERVED_BYTES)",
        "#error platform mailbox is larger than its reserved region",
        "#endif",
    ]
    checks = [
        ("header_size", f"sizeof(platform_mailbox_header_t) == {p}HEADER_BYTES"),
        ("slot_size", f"sizeof(platform_mailbox_slot_t) == {p}SLOT_BYTES"),
        ("size", f"sizeof(platform_mailbox_t) == {p}USED_BYTES"),
        ("slot_offset", f"offsetof(platform_mailbox_t, slot) == {p}HEADER_BYTES"),
        ("m4_id_offset", "offsetof(platform_mailbox_header_t, m4_layout_id) == 4u"),
        ("len_offset", "offsetof(platform_mailbox_slot_t, len) == 4u"),
        ("data_offset", "offsetof(platform_mailbox_slot_t, data) == 8u"),
    ]
    for s in lay.slots:
        up = camel_to_snake_case(s.message).upper()
        sp = f"{p}SLOT_{up}_"
        checks += [
            (f"{up.lower()}_length", f"PLATFORM_{up}_LENGTH <= {MAX_DATA_BYTES}u"),
            (f"{up.lower()}_length_eq", f"PLATFORM_{up}_LENGTH == {sp}LENGTH"),
            (
                f"{up.lower()}_offset",
                f"{sp}OFFSET == offsetof(platform_mailbox_t, slot[{s.index}])",
            ),
        ]
    for name, cond in checks:
        h.append(f"typedef char platform_mailbox_assert_{name}[({cond}) ? 1 : -1];")
    h += ["", "#endif /* PLATFORM_MAILBOX_H */", ""]
    return {"platform_mailbox.h": "\n".join(h)}


def generate_python(doc: dict[str, Any], db: Database) -> str:
    lay = resolve(doc, db)
    lines = [PY_BANNER.format(source=SOURCE), ""]
    lines += [
        "from typing import NamedTuple",
        "",
        "",
        "class Slot(NamedTuple):",
        '    """One mailbox slot (D-093); offset is from the region base."""',
        "",
        "    index: int",
        "    message: str  # platform.dbc message name",
        "    frame_id: int",
        "    length: int",
        "    direction: str  # 'm7_to_m4' | 'm4_to_m7'",
        "    cls: str  # 'safety' | 'qm'",
        "    hsem_id: int",
        "    offset: int",
        "",
        "",
        f"BASE_ADDRESS = 0x{lay.base_address:08X}  # {lay.name}, SRAM4 (D3)",
        f"ADDR_VERIFIED = {lay.verified}",
        f"RESERVED_BYTES = {lay.reserved_bytes}",
        f"USED_BYTES = {lay.used_bytes}",
        f"HEADER_BYTES = {HEADER_BYTES}",
        f"SLOT_BYTES = {SLOT_BYTES}",
        f"LAYOUT_ID = 0x{layout_id(lay, db):08X}  # CRC-32 of the resolved layout",
        "",
        "SLOTS = (",
    ]
    for s in lay.slots:
        lines.append(
            f"    Slot({s.index}, {s.message!r}, 0x{s.frame_id:03X}, {s.length}, "
            f"{s.direction!r}, {s.cls!r}, {s.hsem_id}, {s.offset}),"
        )
    lines += [")", ""]
    return "\n".join(lines)
