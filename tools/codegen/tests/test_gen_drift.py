"""gen/ must equal a fresh generation (CI also runs `git diff --exit-code gen/`)."""

import pytest

from moto_codegen import config, gen_vss
from moto_codegen.cli import render_all


def _compare(files):
    stale = [
        str(rel)
        for rel, text in files.items()
        if not (config.GEN_DIR / rel).exists()
        or (config.GEN_DIR / rel).read_text(encoding="utf-8") != text
    ]
    assert stale == [], f"gen/ is out of date, run `make gen`: {stale}"


def test_c_python_and_dart_are_up_to_date():
    files = render_all(with_vss=False)
    _compare(files)
    on_disk = {
        p.relative_to(config.GEN_DIR)
        for sub in ("c", "python", "dart")
        for p in (config.GEN_DIR / sub).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert on_disk == set(files), "unexpected extra files in gen/"


def test_vss_is_up_to_date(platform_db):
    try:
        base = gen_vss.fetch_base()
    except OSError as exc:  # offline
        pytest.skip(f"VSS base not available: {exc}")
    assert (
        gen_vss.check_overlay(gen_vss.load_overlay(), gen_vss.base_paths(base), platform_db) == []
    )
    assert gen_vss.check_overlay(
        {"Vehicle.Motorcycle.WheelieAngle": {}}, gen_vss.base_paths(base), platform_db
    ) == ["overlay: Vehicle.Motorcycle.WheelieAngle is an extension not yet approved by the user"]
    rel = "vss/vss_dbc.json"
    assert (config.GEN_DIR / rel).read_text(encoding="utf-8") == gen_vss.export_json(base)
