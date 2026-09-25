"""Consistency rules that `make gen` / `make check` enforce before anything is generated."""

from __future__ import annotations

from typing import Any

from .sources import NODE_IDS, Sources, is_e2e, msg_attr

# D-020: the only services the vehicle-bus tester may send. Anything else is refused here,
# so a forbidden service can never reach generated code. `None` = any sub-function.
ALLOWED_VEHICLE_SERVICES: dict[int, frozenset[int] | None] = {
    0x10: frozenset({0x01, 0x03}),  # DiagnosticSessionControl: default / extended only
    0x3E: None,  # TesterPresent
    0x22: None,  # ReadDataByIdentifier
    0x19: None,  # ReadDTCInformation
    0x01: None,  # OBD show current data
    0x09: None,  # OBD request vehicle information
}
# Named explicitly so the error message is unambiguous (D-020).
FORBIDDEN_VEHICLE_SERVICES = frozenset({0x11, 0x14, 0x27, 0x2E, 0x2F, 0x31, 0x34, 0x36, 0x37})

# Platform ID classes (ARCHITECTURE section 4).
RESERVED = range(0x000, 0x010)
SAFETY_CRITICAL = range(0x010, 0x080)
HEARTBEAT = range(0x080, 0x090)
UDS = range(0x700, 0x800)

MAX_SINGLE_FRAME_DID_LEN = 4  # SF payload 7 = 0x62 + DID(2) + data(<=4)


class CheckError(Exception):
    pass


def _check_platform(src: Sources, errors: list[str]) -> None:
    db = src.platform
    names = {n.name for n in db.nodes}
    if names != set(NODE_IDS):
        errors.append(f"platform.dbc nodes {sorted(names)} != {sorted(NODE_IDS)}")
    for node in db.nodes:
        nid = node.dbc.attributes["NodeId"].value if node.dbc else None
        if nid != NODE_IDS.get(node.name):
            errors.append(f"node {node.name}: NodeId {nid} != {NODE_IDS.get(node.name)}")

    data_ids: dict[int, str] = {}
    for m in db.messages:
        where = f"{m.name} (0x{m.frame_id:03X})"
        if m.is_extended_frame:
            errors.append(f"{where}: platform bus uses 11-bit IDs only")
        if len(m.senders) != 1 or m.senders[0] not in NODE_IDS:
            errors.append(f"{where}: needs exactly one known sender, got {m.senders}")
        if m.frame_id in RESERVED:
            errors.append(f"{where}: 0x000-0x00F is reserved")
        if m.frame_id in UDS:
            errors.append(f"{where}: 0x700-0x7FF is UDS; do not define it in the DBC")
        cycle = msg_attr(m, "GenMsgCycleTime", 0)
        if not cycle or cycle <= 0:
            errors.append(f"{where}: GenMsgCycleTime must be > 0")
        for s in m.signals:
            if not s.receivers:
                errors.append(f"{where}.{s.name}: signal has no receiver")

        must_e2e = m.frame_id in SAFETY_CRITICAL or m.frame_id in HEARTBEAT
        if must_e2e and not is_e2e(m):
            errors.append(f"{where}: safety/heartbeat range requires E2E_Protected=Yes")
        if m.frame_id in HEARTBEAT:
            sender = m.senders[0] if m.senders else ""
            if m.frame_id != 0x080 + NODE_IDS.get(sender, -0x100):
                errors.append(f"{where}: heartbeat ID must be 0x080 + NodeId of {sender}")

        if is_e2e(m):
            crc = next((s for s in m.signals if s.name == "E2E_CRC"), None)
            ctr = next((s for s in m.signals if s.name == "E2E_COUNTER"), None)
            if crc is None or (crc.start, crc.length, crc.byte_order, crc.is_signed) != (
                0,
                8,
                "little_endian",
                False,
            ):
                errors.append(f"{where}: E2E_CRC must be byte 0 (0|8@1+)")
            if ctr is None or (ctr.start, ctr.length, ctr.byte_order, ctr.is_signed) != (
                8,
                4,
                "little_endian",
                False,
            ):
                errors.append(f"{where}: E2E_COUNTER must be byte 1 bits 0-3 (8|4@1+)")
            did = msg_attr(m, "E2E_DataID", 0)
            if not did:
                errors.append(f"{where}: E2E_DataID must be non-zero")
            elif did in data_ids:
                errors.append(f"{where}: E2E_DataID {did} already used by {data_ids[did]}")
            else:
                data_ids[did] = m.name


def _check_vehicle(src: Sources, errors: list[str]) -> None:
    v = src.vehicle
    for node in v.get("c_nodes", []):
        if node not in NODE_IDS:
            errors.append(f"vehicle_cl250.yaml: unknown c_node {node}")

    for svc in v.get("allowed_services", []):
        sid = svc["sid"]
        if sid in FORBIDDEN_VEHICLE_SERVICES:
            errors.append(f"vehicle_cl250.yaml: service 0x{sid:02X} is forbidden (D-020)")
            continue
        if sid not in ALLOWED_VEHICLE_SERVICES:
            errors.append(f"vehicle_cl250.yaml: service 0x{sid:02X} is not in D-020")
            continue
        min_len = svc.get("min_length")
        if not isinstance(min_len, int) or not 1 <= min_len <= 7:
            errors.append(f"vehicle_cl250.yaml: service 0x{sid:02X} needs min_length 1..7")
        elif svc.get("subfunctions") and min_len < 2:
            errors.append(
                f"vehicle_cl250.yaml: service 0x{sid:02X} min_length must cover the sub-function"
            )
        allowed_sub = ALLOWED_VEHICLE_SERVICES[sid]
        subs = svc.get("subfunctions")
        if allowed_sub is not None:
            if not subs or not set(subs) <= allowed_sub:
                errors.append(
                    f"vehicle_cl250.yaml: service 0x{sid:02X} sub-functions {subs} must be "
                    f"a subset of {sorted(allowed_sub)} (D-020)"
                )

    listed = {s["sid"]: s.get("subfunctions") for s in v.get("allowed_services", [])}
    session = v["session"]
    if session["request_subfunction"] not in (listed.get(0x10) or []):
        errors.append("vehicle_cl250.yaml: session.request_subfunction not allowed")
    tp_subs = listed.get(0x3E)
    if 0x3E not in listed or (tp_subs and session["tester_present_subfunction"] not in tp_subs):
        errors.append("vehicle_cl250.yaml: tester_present_subfunction not allowed")
    if 0x22 not in listed:
        errors.append("vehicle_cl250.yaml: 0x22 must be allowed to read DIDs")

    seen: set[int] = set()
    names: set[str] = set()
    for d in v["dids"]:
        if d["did"] in seen or d["name"] in names:
            errors.append(f"vehicle_cl250.yaml: duplicate DID {d['name']}")
        seen.add(d["did"])
        names.add(d["name"])
        if not 1 <= d["length"] <= MAX_SINGLE_FRAME_DID_LEN:
            errors.append(f"vehicle_cl250.yaml: {d['name']} length must be 1..4 (single frame)")
        if d["factor_den"] <= 0 or d["poll_period_ms"] <= 0:
            errors.append(f"vehicle_cl250.yaml: {d['name']} factor_den/poll_period must be > 0")
        if not isinstance(d.get("verified"), bool) or not d.get("evidence"):
            errors.append(f"vehicle_cl250.yaml: {d['name']} needs verified + evidence")


def _check_overlay(src: Sources, errors: list[str]) -> None:
    signals: dict[str, Any] = {}
    counts: dict[str, int] = {}
    for m in src.platform.messages:
        for s in m.signals:
            signals.setdefault(s.name, s)
            counts[s.name] = counts.get(s.name, 0) + 1
    for path, node in src.overlay.items():
        mapping = (node or {}).get("dbc2vss")
        if not mapping:
            continue
        sig = signals.get(mapping.get("signal"))
        if sig is not None and counts[sig.name] > 1:
            errors.append(f"overlay {path}: {sig.name} is not unique in platform.dbc")
        if sig is None:
            errors.append(f"overlay {path}: signal {mapping.get('signal')} not in platform.dbc")
        elif "LINUX" not in sig.receivers:
            errors.append(f"overlay {path}: {sig.name} is not received by LINUX")


def run(src: Sources) -> None:
    errors: list[str] = []
    _check_platform(src, errors)
    _check_vehicle(src, errors)
    _check_overlay(src, errors)
    if errors:
        raise CheckError("\n".join(errors))
