"""VSS export: COVESA base release + vss/overlay.vspec -> gen/vss/vss_dbc.json."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import yaml
from cantools.database.can import Database

from . import config

VSS_VERSION = "6.0"
VSS_BASE_URL = (
    "https://github.com/COVESA/vehicle_signal_specification/releases/download/v" + VSS_VERSION
)
# Pinned release assets (sha256). Changing the VSS version is a decision (D-024).
VSS_BASE_FILES = {
    "vss.yaml": "87d137149eac92880ffc32b23c623b2f2cf2b93c8b0cce3281f37aeb682827fc",
    "units.yaml": "f43f6240011f2191d376c24a6ff21429ac7f776da661a1ebc7fb4dcd6a8f0497",
    "quantities.yaml": "442e8505cab7b94f5c74fb3d81ab2cd89098d31f79090c240c1f40f67d16b944",
}
CACHE_DIR = config.REPO_ROOT / "tools" / "codegen" / ".cache" / f"vss-{VSS_VERSION}"
EXTENSION_ROOT = "Vehicle.Motorcycle"
# Extensions the user approved (D-004 requires asking first). Empty until approved.
APPROVED_EXTENSIONS: frozenset[str] = frozenset()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_base() -> Path:
    """Download (once) and verify the pinned VSS release files; returns the cache dir."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for name, digest in VSS_BASE_FILES.items():
        path = CACHE_DIR / name
        if not path.exists() or _sha256(path) != digest:
            with urllib.request.urlopen(f"{VSS_BASE_URL}/{name}", timeout=60) as resp:
                path.write_bytes(resp.read())
        if _sha256(path) != digest:
            raise RuntimeError(f"{name}: sha256 mismatch for VSS {VSS_VERSION}")
    return CACHE_DIR


def load_overlay(path: Path = config.OVERLAY_VSPEC) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_overlay(overlay: dict, base_paths: set[str], platform_db: Database) -> list[str]:
    errors: list[str] = []
    signals = {s.name for m in platform_db.messages for s in m.signals}
    for path, node in overlay.items():
        if path not in base_paths:
            if path.startswith(EXTENSION_ROOT) and path in APPROVED_EXTENSIONS:
                pass
            elif path.startswith(EXTENSION_ROOT):
                errors.append(f"overlay: {path} is an extension not yet approved by the user")
            else:
                errors.append(f"overlay: {path} does not exist in COVESA VSS {VSS_VERSION}")
        mapping = (node or {}).get("dbc2vss")
        if mapping is None:
            continue
        sig = mapping.get("signal")
        if sig not in signals:
            errors.append(f"overlay: {path} maps unknown platform.dbc signal {sig}")
        if not isinstance(mapping.get("interval_ms"), int) or mapping["interval_ms"] <= 0:
            errors.append(f"overlay: {path} needs a positive dbc2vss.interval_ms")
    return errors


def base_paths(base_dir: Path) -> set[str]:
    with open(base_dir / "vss.yaml", encoding="utf-8") as f:
        return set((yaml.safe_load(f) or {}).keys())


def export_json(base_dir: Path) -> str:
    """Run vss-tools and return the pretty JSON text (with dbc2vss kept)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "vss_dbc.json"
        cmd = [
            "vspec", "export", "json",
            "-s", str(base_dir / "vss.yaml"),
            "-l", str(config.OVERLAY_VSPEC),
            "-u", str(base_dir / "units.yaml"),
            "-q", str(base_dir / "quantities.yaml"),
            "-e", "dbc2vss",
            "--pretty",
            "-o", str(out),
        ]  # fmt: skip
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        data = json.loads(out.read_text(encoding="utf-8"))
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
