from __future__ import annotations

import shutil
import subprocess

import pytest

from moto_codegen.sources import C_NODES

CFLAGS = ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wconversion", "-Wshadow"]
pytestmark = pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc not installed")


@pytest.mark.parametrize("node_dir", sorted(C_NODES.values()))
def test_generated_c_compiles_and_passes(root, tmp_path, node_dir):
    gen = root / "gen" / "c" / node_dir
    sources = sorted(str(p) for p in gen.glob("*.c"))
    if not (gen / "moto_e2e.h").exists():
        # No E2E messages for this node: compile only.
        for src in sources:
            subprocess.run(
                ["gcc", *CFLAGS, "-c", src, "-I", str(gen), "-o", str(tmp_path / "x.o")], check=True
            )
        return
    defines = ["-DHAVE_VEHICLE"] if (gen / "vehicle_cl250.h").exists() else []
    exe = tmp_path / "test_gen"
    harness = root / "tools" / "codegen" / "tests" / "c" / "test_gen.c"
    subprocess.run(
        ["gcc", *CFLAGS, *defines, "-I", str(gen), str(harness), *sources, "-o", str(exe)],
        check=True,
    )
    result = subprocess.run([str(exe)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
