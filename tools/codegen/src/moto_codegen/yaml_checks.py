"""Loaders and checks for uds/vehicle_cl250.yaml and uds/dids.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from cantools.database.can import Database

from . import config

VEHICLE_REQUIRED_TIMING = (
    "requests_in_flight",
    "response_timeout_base_ms",
    "response_timeout_max_ms",
    "max_consecutive_timeouts",
    "did_skip_cooldown_ms",
    "ecu_absent_timeout_ms",
    "bus_off_backoff_initial_ms",
    "bus_off_backoff_max_ms",
)
DID_REQUIRED = (
    "did", "name", "length", "factor_num", "factor_den", "offset", "unit",
    "min", "max", "poll_period_ms", "stale_after_ms", "verified", "evidence",
)  # fmt: skip


def load_yaml(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return data


def request_allowed(policy: dict[str, Any], payload: list[int] | bytes) -> bool:
    """Python twin of the generated vehicle_cl250_request_allowed() (D-020)."""
    if not payload:
        return False
    sid = payload[0]
    if sid in config.FORBIDDEN_VEHICLE_SERVICES:
        return False
    for entry in policy["allowed"]:
        if entry["sid"] != sid:
            continue
        subs = entry.get("subfunctions")
        if subs is None:
            return True
        if len(payload) < 2:
            return False
        sub = payload[1] & 0x7F
        return sub in subs and sub not in config.FORBIDDEN_VEHICLE_SUBFUNCTIONS.get(sid, ())
    return False


def _evidence_ok(item: dict[str, Any]) -> bool:
    ev = item.get("evidence")
    return isinstance(ev, list) and len(ev) > 0 and all(":" in str(e) for e in ev)


def check_vehicle(data: dict[str, Any], platform_db: Database | None) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "source", "bus", "addressing", "transport",
                "tester_policy", "session", "timing", "dids"):  # fmt: skip
        if key not in data:
            errors.append(f"vehicle: missing top-level key '{key}'")
    if errors:
        return errors

    for key in ("repo", "commit"):
        if not data["source"].get(key):
            errors.append(f"vehicle: source.{key} missing")

    # --- D-020 policy: must never allow a forbidden service ---
    policy = data["tester_policy"]
    for entry in policy.get("allowed", []):
        sid = entry.get("sid")
        if sid in config.FORBIDDEN_VEHICLE_SERVICES:
            errors.append(f"vehicle: tester_policy allows forbidden service 0x{sid:02X} (D-020)")
        forbidden_subs = config.FORBIDDEN_VEHICLE_SUBFUNCTIONS.get(sid, frozenset())
        for sub in entry.get("subfunctions") or []:
            if sub in forbidden_subs:
                errors.append(
                    f"vehicle: tester_policy allows 0x{sid:02X} 0x{sub:02X} (forbidden, D-020)"
                )
    errors += [f"vehicle: {e}" for e in config.policy_d020_errors(policy)]
    listed_forbidden = set(policy.get("forbidden", []))
    if listed_forbidden != set(config.FORBIDDEN_VEHICLE_SERVICES):
        errors.append("vehicle: tester_policy.forbidden differs from the D-020 list")

    # --- every request the tester is told to send must pass the policy ---
    requests = {
        "session.start": data["session"]["start"]["request"],
        "session.tester_present": data["session"]["tester_present"]["request"],
    }
    for did in data["dids"]:
        if "did" in did:
            requests[f"did 0x{did['did']:04X}"] = [0x22, did["did"] >> 8, did["did"] & 0xFF]
    for label, payload in requests.items():
        if not request_allowed(policy, payload):
            errors.append(f"vehicle: {label} request {payload} violates tester_policy (D-020)")

    for key in VEHICLE_REQUIRED_TIMING:
        value = data["timing"].get(key)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"vehicle: timing.{key} must be a positive integer")
    if data["timing"].get("requests_in_flight") != 1:
        errors.append("vehicle: requests_in_flight must be 1 (strict request/response)")

    for section in ("bus", "transport"):
        if data[section].get("verified") and not _evidence_ok(data[section]):
            errors.append(f"vehicle: {section} verified without file:line evidence")
    for name, addr in data["addressing"].items():
        if addr.get("verified") and not _evidence_ok(addr):
            errors.append(f"vehicle: addressing.{name} verified without evidence")

    seen_dids: set[int] = set()
    seen_names: set[str] = set()
    for item in data["dids"]:
        label = f"vehicle: DID {item.get('name', '?')}"
        missing = [k for k in DID_REQUIRED if k not in item]
        if missing:
            errors.append(f"{label}: missing {missing}")
            continue
        did = item["did"]
        if not 0 <= did <= 0xFFFF or did in seen_dids:
            errors.append(f"{label}: DID 0x{did:04X} invalid or duplicate")
        seen_dids.add(did)
        if item["name"] in seen_names:
            errors.append(f"{label}: duplicate name")
        seen_names.add(item["name"])
        # Single Frame: PCI + 0x62 + DID(2) + data must fit in 8 bytes.
        if not 1 <= item["length"] <= 4:
            errors.append(f"{label}: length must be 1..4 bytes (Single Frame, uint32 raw)")
        if item["factor_den"] == 0 or item["factor_num"] == 0:
            errors.append(f"{label}: factor_num/factor_den must be non-zero")
        if item["min"] > item["max"]:
            errors.append(f"{label}: min > max")
        if item["poll_period_ms"] <= 0:
            errors.append(f"{label}: poll_period_ms must be > 0")
        if not item["poll_period_ms"] < item["stale_after_ms"] <= 0xFFFF:
            errors.append(f"{label}: stale_after_ms must be > poll_period_ms and <= 65535")
        if item["verified"] and not _evidence_ok(item):
            errors.append(f"{label}: verified without file:line evidence")
        ref = item.get("platform_signal")
        if ref and platform_db is not None:
            msg_name, _, sig_name = ref.partition(".")
            try:
                platform_db.get_message_by_name(msg_name).get_signal_by_name(sig_name)
            except KeyError:
                errors.append(f"{label}: platform_signal {ref} not found in platform.dbc")
    return errors


def check_dids(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = data.get("nodes")
    if not isinstance(nodes, dict):
        return ["dids: 'nodes' mapping missing"]
    for node, content in nodes.items():
        if node not in config.NODE_IDS:
            errors.append(f"dids: unknown node {node}")
            continue
        seen: set[int] = set()
        for item in (content or {}).get("dids", []) or []:
            did = item.get("did")
            if not isinstance(did, int) or not (0xF100 <= did <= 0xF1FF or 0xFD00 <= did <= 0xFDFF):
                errors.append(f"dids: {node} DID {did} outside 0xF1xx/0xFDxx")
            elif did in seen:
                errors.append(f"dids: {node} duplicate DID 0x{did:04X}")
            else:
                seen.add(did)
            if item.get("access", "read") != "read":
                errors.append(f"dids: {node} DID {did}: only read access without user approval")
    return errors
