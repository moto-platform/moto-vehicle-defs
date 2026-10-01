"""Loaders and checks for uds/vehicle_cl250.yaml and limits (uds/dids.yaml: gen_uds)."""

from __future__ import annotations

import math
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
    # The polling budget and the D-043 sample-gap bound need it; without it both would
    # be skipped silently.
    "assumed_round_trip_ms",
    # The D-053 poll period floor needs it.
    "client_step_max_ms",
)
DID_REQUIRED = (
    "did", "name", "length", "factor_num", "factor_den", "offset", "unit",
    "min", "max", "poll_period_ms", "stale_after_ms", "priority", "verified", "evidence",
)  # fmt: skip
# D-043: poll priority classes, most urgent first. Order only, never content.
DID_PRIORITIES = ("high", "normal")


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


def did_sample_gap_bounds(dids: list[dict[str, Any]], rtt: int) -> dict[str, int | None]:
    """Worst-case gap between two samples of each DID under the rt-core poller (D-043).

    The poller is non-preemptive fixed-priority scheduling with one request in flight:
    of the due DIDs, the lowest DID_PRIORITIES rank goes first, then table order, and a
    DID is due poll_period_ms after its last request. Every request holds the slot for
    the assumed round trip C. For DID i:
      w_i = C + sum over higher-ordered j of (floor(w_i / P_j) + 1) * C
    (one request already in flight, then every higher one released up to the start),
    and the gap between its samples is at most P_i + w_i + C. None means w_i did not
    converge below the DID's stale_after_ms. C must cover the ECU's answer plus the
    poll step of the firmware loop.
    """
    order = sorted(range(len(dids)), key=lambda i: (DID_PRIORITIES.index(dids[i]["priority"]), i))
    bounds: dict[str, int | None] = {}
    for pos, i in enumerate(order):
        higher = [dids[j]["poll_period_ms"] for j in order[:pos]]
        limit = dids[i]["stale_after_ms"]
        w = rtt
        while True:
            nxt = rtt + sum((w // p + 1) * rtt for p in higher)
            if nxt == w or nxt > limit:
                break
            w = nxt
        bounds[dids[i]["name"]] = dids[i]["poll_period_ms"] + w + rtt if nxt == w else None
    return bounds


def did_fault_gap_bounds(
    dids: list[dict[str, Any]], rtt: int, base: int, max_timeouts: int, step: int
) -> dict[str, int | None]:
    """Worst-case request gap of each DID while another DID is faulty (D-050..D-053).

    A faulty DID f (its last read timed out, or its last answer came later than its poll
    period after its sample stamp) competes in the normal class at its table position and
    gets no NRC 0x78 extension, so its read ends at the base response timeout B. The tester
    sees that timeout only at its next step, so the read holds the slot for H = B + S per
    read, S = client_step_max_ms (safety review MINOR-1 on D-053; rx_busy false, i.e. no
    segmented reception pausing the base timeout, D-050 item 3).
    After a timeout its period restarts at the timeout, so its next read starts at least P_f
    + B after the last one; after an answer the next read starts at least P_f after it. With
    P_f >= B + client_step_max_ms (D-052, D-053, checked separately) an answer within B, seen
    at most one step later, is within P_f of its own stamp and ends the fault state before
    f is due again, so only an answer stamped with an earlier timed-out read keeps
    f faulty: the densest chain alternates timeouts and such answers, at least P_f and P_f +
    B apart in turn. Slow answers do not reset the skip count (D-052), so at most 2 *
    max_timeouts - 1 faulty reads follow f's first failing attempt before the skip: one
    fewer when that attempt timed out, this many when it was a slow answer (safety review
    MINOR-1 on D-052). The fresh attempt itself is not covered (D-050 item 3). The plain
    timed-out chain is sparser and is covered too. For every other DID i, with a faulty read
    of f just started when i becomes due, one faulty DID at a time, and every other read
    holding the slot for the assumed round trip C:
      w_i = H + sum over j != f ordered before i of (floor(w_i / P_j) + 1) * C
              + (if f is ordered before i) min(n_f(w_i), 2 * max_timeouts - 2) * H
      n_f(w) = 2 * floor(w / (2 * P_f + B)) + (1 if w mod (2 * P_f + B) >= P_f else 0)
    and i's request gap is at most P_i + w_i. The sample age adds one round trip and the
    poll step on top (D-050 item 2). Each DID gets the worst bound over every other DID
    as f. None means w_i did not converge below the DID's stale_after_ms.
    """
    normal = DID_PRIORITIES.index("normal")
    cap = max(2 * max_timeouts - 2, 0)
    hold = base + step
    bounds: dict[str, int | None] = {}
    for i, d in enumerate(dids):
        worst: int | None = 0
        for f in range(len(dids)):
            if f == i:
                continue

            def key(j: int, f: int = f) -> tuple[int, int]:
                return (normal if j == f else DID_PRIORITIES.index(dids[j]["priority"]), j)

            ahead = [j for j in range(len(dids)) if j != i and key(j) < key(i)]
            p_f = dids[f]["poll_period_ms"]
            cycle = 2 * p_f + base  # spacing lower bound: a later timeout only spreads reads
            blocking = max(hold, rtt)
            w = blocking
            while True:
                nxt = blocking
                for j in ahead:
                    if j == f:
                        reads = 2 * (w // cycle) + (1 if w % cycle >= p_f else 0)
                        nxt += min(reads, cap) * hold
                    else:
                        nxt += (w // dids[j]["poll_period_ms"] + 1) * rtt
                if nxt == w or nxt > d["stale_after_ms"]:
                    break
                w = nxt
            if nxt != w:
                worst = None
                break
            worst = max(worst, d["poll_period_ms"] + w)
        bounds[d["name"]] = worst
    return bounds


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
        if not _is_pos_int(value):
            errors.append(f"vehicle: timing.{key} must be a positive integer")
    rtt = data["timing"].get("assumed_round_trip_ms")
    periods = [d.get("poll_period_ms") for d in data["dids"]]
    if _is_pos_int(rtt) and all(_is_pos_int(p) for p in periods):
        load = sum(rtt / p for p in periods)
        if load > 0.8:
            errors.append(
                f"vehicle: polling budget {load:.2f} > 0.8 at assumed_round_trip_ms={rtt} "
                "(single request in flight)"
            )
    if not _is_pos_int(data["timing"].get("requests_in_flight")) or (
        data["timing"]["requests_in_flight"] != 1
    ):
        errors.append("vehicle: requests_in_flight must be 1 (strict request/response)")
    complete = all(
        _is_pos_int(d.get(k)) for d in data["dids"] for k in ("poll_period_ms", "stale_after_ms")
    ) and all(d.get("priority") in DID_PRIORITIES and "name" in d for d in data["dids"])
    if _is_pos_int(rtt) and complete:
        # D-043: priority changes the order only; no DID may starve (safety-reviewer m3).
        bounds = did_sample_gap_bounds(data["dids"], rtt)
        for d in data["dids"]:
            gap = bounds[d["name"]]
            if gap is None or gap > d["stale_after_ms"]:
                errors.append(
                    f"vehicle: DID {d['name']}: worst-case sample gap "
                    f"{'unbounded' if gap is None else f'{gap} ms'} > stale_after_ms "
                    f"{d['stale_after_ms']} at assumed_round_trip_ms={rtt} (D-043 starvation)"
                )
    base = data["timing"].get("response_timeout_base_ms")
    max_timeouts = data["timing"].get("max_consecutive_timeouts")
    step = data["timing"].get("client_step_max_ms")
    period_rule = _is_pos_int(base) and _is_pos_int(step) and complete
    if period_rule:
        # D-052 (ISSUES E-8 (1)): a read answered within the base timeout without NRC
        # 0x78 must end before its DID is due again, or a slow DID starves the others.
        # D-053 (ISSUES E-9): the tester sees the answer only at its next step, up to
        # client_step_max_ms later. Seen at the period or later, its DID is due again at
        # once (and the answer is slow past the period) with no timeout and no skip, so
        # it can hold the slot back to back.
        for d in data["dids"]:
            if d["poll_period_ms"] < base + step:
                period_rule = False
                errors.append(
                    f"vehicle: DID {d['name']}: poll_period_ms {d['poll_period_ms']} < "
                    f"response_timeout_base_ms {base} + client_step_max_ms {step} "
                    "(D-052, D-053)"
                )
    if _is_pos_int(rtt) and _is_pos_int(step) and rtt <= step:
        # D-053: the assumed round trip covers the ECU's answer plus one step.
        errors.append(
            f"vehicle: timing.assumed_round_trip_ms {rtt} must exceed client_step_max_ms "
            f"{step} (the round trip includes one step, D-053)"
        )
    if _is_pos_int(rtt) and _is_pos_int(max_timeouts) and period_rule:
        # D-050..D-053: any one faulty DID (normal class, base timeout + one step per read,
        # skipped after max_consecutive_timeouts) must not starve the others (E-7, E-8).
        fault = did_fault_gap_bounds(data["dids"], rtt, base, max_timeouts, step)
        for d in data["dids"]:
            gap = fault[d["name"]]
            if gap is None or gap > d["stale_after_ms"]:
                errors.append(
                    f"vehicle: DID {d['name']}: fault-mode request gap "
                    f"{'unbounded' if gap is None else f'{gap} ms'} > stale_after_ms "
                    f"{d['stale_after_ms']} with another DID faulty at "
                    f"response_timeout_base_ms={base} + client_step_max_ms={step} "
                    "(D-050..D-053 starvation)"
                )

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
        if not _is_pos_int(item["poll_period_ms"]) or not _is_pos_int(item["stale_after_ms"]):
            errors.append(f"{label}: poll_period_ms and stale_after_ms must be positive integers")
        elif not item["poll_period_ms"] < item["stale_after_ms"] <= 0xFFFF:
            errors.append(f"{label}: stale_after_ms must be > poll_period_ms and <= 65535")
        if item.get("poll_period_verified", True) is False and not _is_pos_int(
            item.get("legacy_poll_period_ms")
        ):
            errors.append(f"{label}: provisional poll period needs legacy_poll_period_ms")
        if item["priority"] not in DID_PRIORITIES:
            errors.append(f"{label}: priority must be one of {DID_PRIORITIES} (D-043)")
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
        "k_yellow",
        "k_red",
    ),
    "vehicle_speed": ("vehicle_speed_max_age_ms", "vehicle_speed_accel_margin_mps2"),
}


# Sections whose values safety-node must never get (D-041 item 4: speed is rt-core's).
LIMIT_SECTIONS_NOT_FOR_SAFETY = ("vehicle_speed",)
# D-041 item 3: until Q-022 (combined braking in a curve) k_red leaves a longitudinal
# reserve of sqrt(1 - k_red^2) of mu, i.e. at least 0.6 mu.
K_RED_MAX_UNTIL_Q022 = 0.8


def limit_scope(data: dict[str, Any], node: str) -> tuple[str, ...]:
    """Sections of platform_limits.yaml generated for `node` (a DBC node name)."""
    return tuple(s for s in LIMIT_KEYS if node in (data.get("scope") or {}).get(s, ()))


def _check_scope(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scope = data.get("scope")
    if not isinstance(scope, dict) or set(scope) != set(LIMIT_KEYS):
        return [f"limits: scope must list exactly the sections {sorted(LIMIT_KEYS)}"]
    limit_nodes = {t.node for t in config.C_TARGETS if t.limits}
    for section, nodes in scope.items():
        if not isinstance(nodes, list) or not nodes:
            errors.append(f"limits: scope.{section} must be a non-empty list of nodes")
            continue
        unknown = set(nodes) - limit_nodes
        if unknown:
            errors.append(f"limits: scope.{section} names {sorted(unknown)}, not nodes with limits")
        if section in LIMIT_SECTIONS_NOT_FOR_SAFETY and "SAFETY" in nodes:
            errors.append(f"limits: scope.{section} must not include SAFETY (D-041)")
    for node in sorted(limit_nodes):
        if not any(node in (nodes or ()) for nodes in scope.values()):
            errors.append(f"limits: node {node} gets platform_limits.h but no section")
    return errors


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
    errors += _check_scope(data)
    if errors:
        return errors
    v = limit_values(data)
    mu = _signal(platform_db, "EkfFrictionMass", "FRICTION_COEFF")
    mass = _signal(platform_db, "EkfFrictionMass", "TOTAL_MASS")
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
    k_yellow, k_red = v["k_yellow"], v["k_red"]
    if not all(_is_real(k) for k in (k_yellow, k_red)) or not 0 < k_yellow < k_red < 1:
        errors.append("limits: need 0 < k_yellow < k_red < 1 (D-041)")
    elif k_red > K_RED_MAX_UNTIL_Q022:
        errors.append(
            f"limits: k_red must be <= {K_RED_MAX_UNTIL_Q022} until Q-022 "
            "(longitudinal reserve, D-041 item 3)"
        )
    speed = next((d for d in vehicle.get("dids", []) if d.get("name") == "VEHICLE_SPEED"), None)
    age = v["vehicle_speed_max_age_ms"]
    rtt = vehicle.get("timing", {}).get("assumed_round_trip_ms", 0)
    if speed is None:
        errors.append("limits: vehicle_cl250.yaml has no VEHICLE_SPEED DID")
    elif (
        not isinstance(age, int)
        or isinstance(age, bool)
        or not speed["poll_period_ms"] + rtt < age <= speed["stale_after_ms"]
    ):
        errors.append(
            "limits: vehicle_speed_max_age_ms must be an integer with poll_period_ms + "
            "assumed_round_trip_ms < value <= stale_after_ms of VEHICLE_SPEED (one late "
            "response must not drop the lean; rt-core cannot use an older sample anyway)"
        )
    margin = v["vehicle_speed_accel_margin_mps2"]
    if not _is_real(margin) or not 0 < margin <= 20:
        errors.append("limits: vehicle_speed_accel_margin_mps2 must be in (0, 20]")
    return errors


def _is_pos_int(value: Any) -> bool:
    """A positive int that is not a bool (YAML `true` would pass as 1, E-6 n3)."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_real(value: Any) -> bool:
    """A finite int/float that is not a bool (YAML `true` would pass as 1)."""
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)
