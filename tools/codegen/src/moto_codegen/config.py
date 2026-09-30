"""Static platform configuration: repo paths, node table and CAN ID plan.

The ID plan and node IDs mirror docs/ARCHITECTURE.md section 4. The DBC is the
source of truth for messages; this module only holds the rules they must obey.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PLATFORM_DBC = REPO_ROOT / "dbc" / "platform.dbc"
CL250_DBC = REPO_ROOT / "dbc" / "cl250.dbc"
VEHICLE_YAML = REPO_ROOT / "uds" / "vehicle_cl250.yaml"
DIDS_YAML = REPO_ROOT / "uds" / "dids.yaml"
ISO14229_YAML = REPO_ROOT / "uds" / "iso14229.yaml"
LIMITS_YAML = REPO_ROOT / "limits" / "platform_limits.yaml"
OVERLAY_VSPEC = REPO_ROOT / "vss" / "overlay.vspec"
GEN_DIR = REPO_ROOT / "gen"

# Node name -> node_id (ARCHITECTURE section 4).
NODE_IDS: dict[str, int] = {
    "RT_CORE": 1,
    "SAFETY": 2,
    "IO": 3,
    "CONN": 4,
    "LINUX": 5,
    "HIL_SIM": 0xE,
    "TESTER": 0xF,
}


@dataclass(frozen=True)
class CTarget:
    """A firmware node that gets generated C code under gen/c/<directory>/."""

    node: str
    directory: str
    all_messages: bool = False  # restbus simulator: every message, both directions
    vehicle_dids: bool = False  # gets the CL250 DID table (vehicle-bus tester or simulator)
    limits: bool = False  # gets platform_limits.h (producer/consumer of cornering values)
    # uds_iso14229.h: "full" (UDS server and/or client) or "client" (vehicle-bus tester
    # only: nothing outside the D-020 allow-list is named, D-040). None: no UDS.
    uds_iso: str | None = None


# LINUX and TESTER parse the DBC/VSS at runtime (Python), so they get no C code.
C_TARGETS: tuple[CTarget, ...] = (
    CTarget("RT_CORE", "rt_core", vehicle_dids=True, limits=True, uds_iso="full"),
    CTarget("SAFETY", "safety", limits=True),
    CTarget("IO", "io"),
    # Temporary sole vehicle-bus tester until rt-core polls (D-023).
    CTarget("CONN", "conn", vehicle_dids=True, uds_iso="client"),
    # Simulates the CL250 ECU and impersonates platform nodes on the HIL bench.
    CTarget(
        "HIL_SIM", "hil_sim", all_messages=True, vehicle_dids=True, limits=True, uds_iso="full"
    ),
)


@dataclass(frozen=True)
class IdRange:
    first: int
    last: int
    name: str
    e2e_mandatory: bool
    allowed_in_dbc: bool = True

    def contains(self, frame_id: int) -> bool:
        return self.first <= frame_id <= self.last


ID_RANGES: tuple[IdRange, ...] = (
    IdRange(0x000, 0x00F, "reserved", e2e_mandatory=False, allowed_in_dbc=False),
    IdRange(0x010, 0x07F, "safety", e2e_mandatory=True),
    IdRange(0x080, 0x08F, "heartbeat", e2e_mandatory=True),
    IdRange(0x100, 0x3FF, "state", e2e_mandatory=False),
    IdRange(0x400, 0x5FF, "telemetry", e2e_mandatory=False),
    IdRange(0x600, 0x6FF, "bridge", e2e_mandatory=False),
    # UDS frames are defined by ISO 15765 addressing, not as DBC messages.
    IdRange(0x700, 0x7FF, "uds", e2e_mandatory=False, allowed_in_dbc=False),
)

HEARTBEAT_BASE_ID = 0x080
HEARTBEAT_CYCLE_MS = 100
E2E_TIMEOUT_CYCLES = 3  # receiver timeout = 3 x cycle (ARCHITECTURE section 4)
E2E_MAX_DELTA_COUNTER = 1  # conservative: any lost frame is reported as WRONG_SEQUENCE

# D-041/D-042: the only platform messages safety-node may receive (lean, mu and the
# rt-core heartbeat for the fallback). Vehicle speed in particular is not a
# safety-node input; widening this list is a safety decision (safety-reviewer).
SAFETY_RX_ALLOWED = frozenset({"EkfLean", "EkfFrictionMass", "HeartbeatRtCore"})

# D-020 forbidden vehicle-bus services, repeated here as a second line of defence:
# the checker rejects vehicle_cl250.yaml if its policy ever allows one of them.
FORBIDDEN_VEHICLE_SERVICES = frozenset({0x11, 0x14, 0x27, 0x2E, 0x2F, 0x31, 0x34, 0x36, 0x37})
FORBIDDEN_VEHICLE_SUBFUNCTIONS = {0x10: frozenset({0x02})}
# D-020 allow-list, golden copy: sid -> allowed sub-functions (bit 7 masked), None = any.
# The YAML policy may be narrower, never wider; widening it needs a new decision.
ALLOWED_VEHICLE_SERVICES: dict[int, frozenset[int] | None] = {
    0x10: frozenset({0x01, 0x03}),  # DiagnosticSessionControl: default / extended only
    0x3E: frozenset({0x00}),  # TesterPresent
    0x22: None,  # ReadDataByIdentifier
    0x19: None,  # ReadDTCInformation
    0x01: None,  # OBD show current data
    0x09: None,  # OBD request vehicle information
}


def policy_d020_errors(policy: dict) -> list[str]:
    """Errors if the YAML tester policy allows anything outside the golden D-020 list."""
    errors = []
    for entry in policy.get("allowed", []):
        sid = entry.get("sid")
        if sid not in ALLOWED_VEHICLE_SERVICES:
            errors.append(f"tester_policy allows 0x{sid:02X}, not on the D-020 allow-list")
            continue
        golden = ALLOWED_VEHICLE_SERVICES[sid]
        subs = entry.get("subfunctions")
        if golden is not None and (subs is None or not set(subs) <= golden):
            errors.append(
                f"tester_policy 0x{sid:02X} sub-functions {subs} exceed D-020 {sorted(golden)}"
            )
    return errors


def assert_policy_within_d020(policy: dict) -> None:
    errors = policy_d020_errors(policy)
    if errors:
        raise ValueError("; ".join(errors))


def id_range_of(frame_id: int) -> IdRange | None:
    for r in ID_RANGES:
        if r.contains(frame_id):
            return r
    return None
