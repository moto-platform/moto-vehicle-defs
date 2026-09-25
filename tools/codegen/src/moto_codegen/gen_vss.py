"""VSS output: gen/vss/vss.json (COVESA VSS + overlay with dbc2vss mappings for Kuksa)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

VSS_REPO = "https://github.com/COVESA/vehicle_signal_specification.git"
VSS_TAG = "v6.1"
VSS_COMMIT = "2817646d1808fc7c470c0432fc7f4ed685e5c9e3"


def fetch_spec(cache_dir: Path) -> Path:
    """Clone the pinned VSS release into cache_dir (once) and verify its commit."""
    dest = cache_dir / f"vss-{VSS_TAG}"
    if not (dest / "spec").is_dir():
        cache_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "-c",
                "advice.detachedHead=false",
                "clone",
                "--quiet",
                "--depth",
                "1",
                "--branch",
                VSS_TAG,
                VSS_REPO,
                str(dest),
            ],
            check=True,
        )
    head = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if head != VSS_COMMIT:
        raise RuntimeError(f"VSS {VSS_TAG} at {head}, expected {VSS_COMMIT}; delete {dest}")
    return dest / "spec"


def generate(root: Path, out_dir: Path, cache_dir: Path) -> dict[Path, str]:
    spec = fetch_spec(cache_dir)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "vss.json"
        subprocess.run(
            [
                "vspec",
                "--log-level",
                "WARNING",
                "export",
                "json",
                "--vspec",
                str(spec / "VehicleSignalSpecification.vspec"),
                "--include-dirs",
                str(spec),
                "--units",
                str(spec / "units.yaml"),
                "--quantities",
                str(spec / "quantities.yaml"),
                "--overlays",
                str(root / "vss/overlay.vspec"),
                "--extended-attributes",
                "dbc2vss",
                "--pretty",
                "--output",
                str(out),
            ],
            check=True,
        )
        text = out.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    return {out_dir / "vss" / "vss.json": text}
