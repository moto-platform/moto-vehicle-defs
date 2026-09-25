"""moto-codegen: validate the sources and (re)generate gen/.

moto-codegen check [--root .]          validate sources only
moto-codegen gen [--root .] [--no-vss] validate, then rewrite gen/ from scratch
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import checks, gen_c, gen_python, gen_vss
from .sources import load


def _write(out_dir: Path, files: dict[Path, str], keep_vss: bool) -> None:
    for sub in ("c", "python"):
        shutil.rmtree(out_dir / sub, ignore_errors=True)
    if not keep_vss:
        shutil.rmtree(out_dir / "vss", ignore_errors=True)
    for path, text in sorted(files.items()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="moto-codegen")
    parser.add_argument("command", choices=["check", "gen"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--no-vss", action="store_true", help="keep gen/vss as is (offline)")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    src = load(root)
    try:
        checks.run(src)
    except checks.CheckError as exc:
        print(f"moto-codegen: source check failed:\n{exc}", file=sys.stderr)
        return 1
    if args.command == "check":
        print("moto-codegen: sources OK")
        return 0

    out_dir = root / "gen"
    files = {**gen_c.generate(src, out_dir), **gen_python.generate(src, out_dir)}
    if not args.no_vss:
        files.update(gen_vss.generate(root, out_dir, root / ".cache"))
    _write(out_dir, files, keep_vss=args.no_vss)
    print(f"moto-codegen: wrote {len(files)} files under {out_dir.relative_to(root)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
