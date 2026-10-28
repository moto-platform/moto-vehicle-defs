"""D-090: the 0x19 0x04 / 0x06 response framing and the generated host decoders."""

import copy
import importlib.util
from pathlib import Path

import pytest

from vehicle_codegen import config, gen_uds
from vehicle_codegen.yaml_checks import load_yaml

VECTORS = load_yaml(Path(__file__).parent / "vectors" / "dtc_records.yaml")


@pytest.fixture(scope="module")
def catalog():
    path = config.GEN_DIR / "python" / "vehicle_defs" / "vehicle_catalog.py"
    spec = importlib.util.spec_from_file_location("vehicle_catalog_dtc", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def iso():
    return copy.deepcopy(load_yaml(config.ISO14229_YAML))


def _hex(text: str) -> bytes:
    return bytes.fromhex(text.replace(" ", ""))


def _plain(decoded):
    """Decoder output with bytes as upper-case hex, as the vectors write them."""
    if isinstance(decoded, bytes):
        return decoded.hex().upper()
    if isinstance(decoded, dict):
        return {k: _plain(v) for k, v in decoded.items()}
    if isinstance(decoded, list):
        return [_plain(v) for v in decoded]
    return decoded


def test_committed_framing_is_the_standard(iso):
    assert gen_uds.check_iso(iso) == []


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("dtc_and_status_length",), 5),
        (("snapshot", "identifier_length"), 1),
        (("snapshot", "undefined_number_of_identifiers"), 0xFF),
        (("ext_data", "obd_records"), [0x90, 0xFE]),
    ],
)
def test_framing_differing_from_the_standard_is_refused(iso, path, value):
    node = iso["dtc_record_reports"]
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    assert any("Tables 274/276" in e for e in gen_uds.check_iso(iso))


def test_framing_needs_its_sub_functions_listed(iso):
    iso["read_dtc_subfunctions"] = [s for s in iso["read_dtc_subfunctions"] if s["id"] != 0x06]
    errors = gen_uds.check_iso(iso)
    assert "iso14229: dtc_record_reports.ext_data sub-function is not listed" in errors


def test_no_mcu_target_gets_the_framing():
    for path, text in config_rendered_c().items():
        assert "dtc_record" not in text.lower(), path


def config_rendered_c():
    from vehicle_codegen.cli import render_all

    return {p: t for p, t in render_all(with_vss=False).items() if p.parts[0] == "c"}


@pytest.mark.parametrize("vector", VECTORS["snapshot"], ids=lambda v: v["name"])
def test_snapshot_vectors(catalog, vector):
    assert _plain(catalog.decode_dtc_snapshot(_hex(vector["response"]))) == vector["expect"]


@pytest.mark.parametrize("vector", VECTORS["ext_data"], ids=lambda v: v["name"])
def test_ext_data_vectors(catalog, vector):
    assert _plain(catalog.decode_dtc_ext_data(_hex(vector["response"]))) == vector["expect"]


@pytest.mark.parametrize("vector", VECTORS["invalid"], ids=lambda v: v["response"])
def test_invalid_responses_raise(catalog, vector):
    decoder = {"snapshot": catalog.decode_dtc_snapshot, "ext_data": catalog.decode_dtc_ext_data}
    with pytest.raises(ValueError):
        decoder[vector["decoder"]](_hex(vector["response"]))


def test_vector_dids_come_from_the_catalog(catalog):
    for vector in VECTORS["snapshot"]:
        for record in vector["expect"]["records"]:
            for value in record["values"]:
                assert catalog.BY_DID[value["did"]] == value["name"]
