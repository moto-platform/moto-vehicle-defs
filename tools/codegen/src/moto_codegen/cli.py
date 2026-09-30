"""`moto-codegen gen|check` entry point (called by the repo Makefile)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import config, gen_c, gen_python, gen_uds, gen_vss
from .dbc_checks import check_cl250_dbc, check_platform_dbc, load_dbc
from .yaml_checks import check_limits, check_vehicle, load_yaml


def run_checks(with_vss: bool = True) -> list[str]:
    errors: list[str] = []
    platform_db = load_dbc(config.PLATFORM_DBC)
    errors += check_platform_dbc(platform_db)
    errors += check_cl250_dbc(load_dbc(config.CL250_DBC))
    errors += check_vehicle(load_yaml(config.VEHICLE_YAML), platform_db)
    iso = load_yaml(config.ISO14229_YAML)
    iso_errors = gen_uds.check_iso(iso)
    errors += iso_errors
    if not iso_errors:
        errors += gen_uds.check_dids(
            load_yaml(config.DIDS_YAML), iso, load_yaml(config.VEHICLE_YAML)
        )
    errors += check_limits(
        load_yaml(config.LIMITS_YAML), load_yaml(config.VEHICLE_YAML), platform_db
    )
    if with_vss:
        base = gen_vss.fetch_base()
        errors += gen_vss.check_overlay(
            gen_vss.load_overlay(), gen_vss.base_paths(base), platform_db
        )
    return errors


def render_all(with_vss: bool = True) -> dict[Path, str]:
    """Every generated file, keyed by path relative to gen/."""
    db = load_dbc(config.PLATFORM_DBC)
    vehicle = load_yaml(config.VEHICLE_YAML)
    limits = load_yaml(config.LIMITS_YAML)
    iso = load_yaml(config.ISO14229_YAML)
    dids = load_yaml(config.DIDS_YAML)
    servers = gen_uds.servers(dids)
    files: dict[Path, str] = {}
    for target in config.C_TARGETS:
        out = Path("c") / target.directory
        parts = {**gen_c.generate_platform_c(db, target), **gen_c.generate_e2e_c(db, target)}
        if target.vehicle_dids:
            parts.update(gen_c.generate_vehicle_c(vehicle))
        if target.limits:
            parts.update(gen_c.generate_limits_c(limits, target.node))
        if target.uds_iso is not None:
            parts.update(gen_uds.generate_iso_c(iso, client_only=target.uds_iso == "client"))
        if target.node in servers:
            parts.update(
                gen_uds.generate_server_c(target.node, servers[target.node], dids, iso, vehicle)
            )
        for name, text in parts.items():
            files[out / name] = text
    py = Path("python") / "moto_defs"
    files[py / "__init__.py"] = gen_python.generate_init_py()
    files[py / "platform.py"] = gen_python.generate_platform_py(db)
    files[py / "vehicle_cl250.py"] = gen_python.generate_vehicle_py(vehicle)
    files[py / "e2e.py"] = gen_python.generate_e2e_py()
    files[py / "limits.py"] = gen_python.generate_limits_py(limits)
    files[py / "uds.py"] = gen_uds.generate_uds_py(iso, dids, vehicle)
    if with_vss:
        files[Path("vss") / "vss_dbc.json"] = gen_vss.export_json(gen_vss.fetch_base())
    return files


def write_all(files: dict[Path, str], gen_dir: Path = config.GEN_DIR) -> None:
    for sub in sorted({rel.parts[0] for rel in files}):  # only the parts being regenerated
        shutil.rmtree(gen_dir / sub, ignore_errors=True)
    for rel, text in files.items():
        path = gen_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="moto-codegen")
    parser.add_argument("command", choices=["check", "gen"])
    parser.add_argument("--no-vss", action="store_true", help="skip the VSS base download/export")
    args = parser.parse_args(argv)

    errors = run_checks(with_vss=not args.no_vss)
    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} error(s); nothing generated.", file=sys.stderr)
        return 1
    print("checks: OK")
    if args.command == "gen":
        files = render_all(with_vss=not args.no_vss)
        write_all(files)
        print(f"gen: wrote {len(files)} files to {config.GEN_DIR.relative_to(config.REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
