"""Load the moto-vehicle-defs source files (DBC, UDS YAML, VSS overlay)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cantools
import yaml
from cantools.database.can import Database

# MCU nodes that get C output under gen/c/<dir>/. LINUX and TESTER use gen/python and the
# DBC at runtime instead (ARCHITECTURE section 5: only the host side parses DBC/VSS).
C_NODES: dict[str, str] = {
    "RT_CORE": "rt_core",
    "SAFETY": "safety",
    "IO": "io",
    "CONN": "conn",
    "HIL_SIM": "hil_sim",
}

# Platform node IDs (ARCHITECTURE section 4). platform.dbc must carry the same values.
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
class Sources:
    root: Path
    platform: Database
    cl250: Database
    vehicle: dict[str, Any]
    dids: dict[str, Any]
    overlay: dict[str, Any]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at top level")
    return data


def load(root: Path) -> Sources:
    return Sources(
        root=root,
        platform=cantools.database.load_file(root / "dbc/platform.dbc", strict=True),
        cl250=cantools.database.load_file(root / "dbc/cl250.dbc", strict=True),
        vehicle=_load_yaml(root / "uds/vehicle_cl250.yaml"),
        dids=_load_yaml(root / "uds/dids.yaml"),
        overlay=_load_yaml(root / "vss/overlay.vspec"),
    )


def msg_attr(message: Any, name: str, default: Any = None) -> Any:
    """Return a DBC message attribute value, falling back to the definition default."""
    attrs = message.dbc.attributes if message.dbc else {}
    if name in attrs:
        return attrs[name].value
    return default


def is_e2e(message: Any) -> bool:
    return msg_attr(message, "E2E_Protected", 0) in (1, "Yes")


def node_messages(db: Database, node: str) -> list[Any]:
    """Messages a node sends or receives, in frame-ID order."""
    out = []
    for m in db.messages:
        receivers = {r for s in m.signals for r in s.receivers}
        if node in m.senders or node in receivers:
            out.append(m)
    return sorted(out, key=lambda m: m.frame_id)
