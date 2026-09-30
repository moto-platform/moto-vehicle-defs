"""Loaders and checks for uds/vehicle_cl250.yaml and limits (uds/dids.yaml: gen_uds)."""

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


def _check_functional_watch(addressing: dict[str, Any]) -> list[str]:
    """Q-021/D-040: OBD functional request IDs the tester watches and never sends."""
    watch = addressing.get("functional_watch")
    if not isinstance(watch, dict):
        return ["vehicle: addressing.functional_watch missing (D-040)"]
    if watch.get("watch_only") is not True:
        return ["vehicle: addressing.functional_watch must be watch_only: true (D-020)"]
    errors: list[str] = []
    used = {
        (a[k], a.get("id_type") == "extended_29bit")
        for n, a in addressing.items()
        if n != "functional_watch"
        for k in ("request_id", "response_id")
    }
    seen: set[tuple[int, bool]] = set()
    for item in watch.get("ids") or []:
        ext = item.get("id_type") == "extended_29bit"
        ident = item.get("id")
        limit = 0x1FFFFFFF if ext else 0x7FF
        if item.get("id_type") not in ("standard_11bit", "extended_29bit") or not (
            isinstance(ident, int) and 0 <= ident <= limit
        ):
            errors.append(f"vehicle: functional_watch id {ident} invalid for its id_type")
        elif (ident, ext) in used or (ident, ext) in seen:
            errors.append(f"vehicle: functional_watch id 0x{ident:X} duplicates another ID")
        seen.add((ident, ext))
    if not seen:
        errors.append("vehicle: functional_watch.ids is empty")
    return errors


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
    rtt = data["timing"].get("assumed_round_trip_ms")
    periods = [d.get("poll_period_ms") for d in data["dids"]]
    if isinstance(rtt, int) and all(isinstance(p, int) and p > 0 for p in periods):
        load = sum(rtt / p for p in periods)
        if load > 0.8:
            errors.append(
                f"vehicle: polling budget {load:.2f} > 0.8 at assumed_round_trip_ms={rtt} "
                "(single request in flight)"
            )
    if data["timing"].get("requests_in_flight") != 1:
        errors.append("vehicle: requests_in_flight must be 1 (strict request/response)")

    for section in ("bus", "transport"):
        if data[section].get("verified") and not _evidence_ok(data[section]):
            errors.append(f"vehicle: {section} verified without file:line evidence")
    for name, addr in data["addressing"].items():
        if addr.get("verified") and not _evidence_ok(addr):
            errors.append(f"vehicle: addressing.{name} verified without evidence")
    errors += _check_functional_watch(data["addressing"])

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
        if item.get("poll_period_verified", True) is False and not isinstance(
            item.get("legacy_poll_period_ms"), int
        ):
            errors.append(f"{label}: provisional poll period needs legacy_poll_period_ms")
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


LIMIT_KEYS = {
    "cornering": (
        "friction_coeff_default",
        "friction_coeff_clamp_min",
        "friction_coeff_clamp_max",
        "lean_angle_default",
        "total_mass_default_kg",
    ),
    "vehicle_speed": ("vehicle_speed_max_age_ms", "vehicle_speed_accel_margin_mps2"),
}


def limit_values(data: dict[str, Any]) -> dict[str, Any]:
    """Flat {name: value} of platform_limits.yaml."""
    return {k: v["value"] for section in LIMIT_KEYS for k, v in data[section].items()}


def _signal(platform_db: Database, message: str, signal: str):
    return platform_db.get_message_by_name(message).get_signal_by_name(signal)


def _fits(sig, value: float) -> bool:
    """Value inside the DBC range and representable on the signal's scale."""
    raw = (value - sig.offset) / sig.scale
    return sig.minimum <= value <= sig.maximum and abs(raw - round(raw)) < 1e-6


def check_limits(data: dict[str, Any], vehicle: dict[str, Any], platform_db: Database) -> list[str]:
    errors: list[str] = []
    for section, keys in LIMIT_KEYS.items():
        entries = data.get(section) or {}
        for key in keys:
            entry = entries.get(key)
            if not isinstance(entry, dict) or "value" not in entry or not entry.get("rule"):
                errors.append(f"limits: {section}.{key} needs value + rule")
            elif entry.get("status") not in ("provisional", "measured", "approved"):
                errors.append(
                    f"limits: {section}.{key} status must be provisional|measured|approved"
                )
        extra = set(entries) - set(keys)
        if extra:
            errors.append(f"limits: unknown keys {sorted(extra)} in {section}")
    if errors:
        return errors
    v = limit_values(data)
    mu = _signal(platform_db, "EkfFrictionMass", "FRICTION_COEFF")
    mass = _signal(platform_db, "EkfFrictionMass", "TOTAL_MASS")
    age_sig = _signal(platform_db, "VehicleSpeed", "VEHICLE_SPEED_AGE")
    lo, hi, default = (
        v["friction_coeff_clamp_min"],
        v["friction_coeff_clamp_max"],
        v["friction_coeff_default"],
    )
    if not lo <= default <= hi:
        errors.append("limits: friction_coeff_default outside the clamp range")
    if not 0 < lo < hi:
        errors.append("limits: friction clamp range must be 0 < min < max")
    for name in ("friction_coeff_default", "friction_coeff_clamp_min", "friction_coeff_clamp_max"):
        if not _fits(mu, v[name]):
            errors.append(f"limits: {name} not representable in FRICTION_COEFF")
    if not _fits(mass, v["total_mass_default_kg"]) or v["total_mass_default_kg"] <= 0:
        errors.append("limits: total_mass_default_kg not representable in TOTAL_MASS")
    if v["lean_angle_default"] is not None:
        errors.append("limits: lean_angle_default must be null (no safe default lean, D-029)")
    speed = next((d for d in vehicle.get("dids", []) if d.get("name") == "VEHICLE_SPEED"), None)
    age = v["vehicle_speed_max_age_ms"]
    if speed is None:
        errors.append("limits: vehicle_cl250.yaml has no VEHICLE_SPEED DID")
    elif not speed["stale_after_ms"] < age <= age_sig.maximum:
        errors.append(
            "limits: vehicle_speed_max_age_ms must exceed stale_after_ms of VEHICLE_SPEED "
            "(else it adds nothing) and fit VEHICLE_SPEED_AGE"
        )
    if not 0 < v["vehicle_speed_accel_margin_mps2"] <= 20:
        errors.append("limits: vehicle_speed_accel_margin_mps2 must be in (0, 20]")
    return errors
