"""UDS sources (iso14229.yaml, dids.yaml), Q-021 watch IDs and the generated code (D-040)."""

import copy
import ctypes
import re
import shutil
import subprocess

import pytest

from moto_codegen import config, gen_uds
from moto_codegen.yaml_checks import check_vehicle, load_yaml

CC = shutil.which("gcc") or shutil.which("cc")
FLAGS = ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wshadow", "-Wconversion"]
C_DIR = config.GEN_DIR / "c"


@pytest.fixture
def iso():
    return load_yaml(config.ISO14229_YAML)


@pytest.fixture
def dids():
    return copy.deepcopy(load_yaml(config.DIDS_YAML))


def _errors(dids, iso, vehicle):
    return gen_uds.check_dids(dids, iso, vehicle)


# --------------------------------------------------------------------------- sources


@pytest.mark.parametrize(
    ("code", "dtc"),
    [
        ("U0100-00", 0xC10000),
        ("U3000-00", 0xF00000),
        ("P0301-1F", 0x03011F),
        ("C1234-56", 0x523456),
        ("B0000-00", 0x800000),
    ],  # fmt: skip
)
def test_j2012_encoding(code, dtc):
    assert gen_uds.j2012_to_dtc(code) == dtc


@pytest.mark.parametrize("code", ["U0100", "X0100-00", "U4100-00", "u0100-00", "U0100-0"])
def test_j2012_rejects_malformed(code):
    assert gen_uds.j2012_to_dtc(code) is None


def test_iso_duplicate_rejected(iso):
    iso["nrcs"].append({"nrc": 0x31, "name": "AGAIN"})
    assert any("duplicate" in e for e in gen_uds.check_iso(iso))


def test_iso_positive_sid_rejected(iso):
    iso["services"].append({"sid": 0x62, "name": "NOT_A_REQUEST", "clause": "x"})
    assert any("not a request SID" in e for e in gen_uds.check_iso(iso))


def _rt(dids):
    return dids["nodes"]["RT_CORE"]


@pytest.mark.parametrize(
    ("mutate", "needle"),
    [
        (lambda d: _rt(d)["server"].update(physical_request_id=0x720), "0x710"),
        (lambda d: _rt(d)["server"].update(physical_response_id=0x719), "0x718"),
        (lambda d: _rt(d)["server"].update(p2_server_max_ms=6000), "P2 < P2*"),
        (lambda d: _rt(d)["server"].update(p2_star_server_max_ms=5005), "multiple"),
        (lambda d: _rt(d)["server"].update(max_read_dids=40), "rx_buffer"),
        (lambda d: _rt(d)["server"].update(sessions=["EXTENDED"]), "DEFAULT"),
        (
            lambda d: _rt(d)["server"]["services"].append(
                {"service": "CLEAR_DIAGNOSTIC_INFORMATION", "sessions": ["EXTENDED"]}
            ),
            "duplicate",
        ),
        (
            lambda d: _rt(d)["server"]["services"][4].update(sessions=["PROGRAMMING"]),
            "served sessions",
        ),
        (lambda d: _rt(d)["server"]["services"][1].update(subfunctions=["NOPE"]), "sub-functions"),
        (lambda d: _rt(d)["dids"][0].update(access="write"), "only read"),
        (lambda d: _rt(d)["dids"][0].update(did=0xF200), "outside"),
        (lambda d: _rt(d)["dids"][1].update(did=0xF186), "duplicate DID"),
        (lambda d: _rt(d)["dids"][3].update(length=5), "uint length"),
        (lambda d: _rt(d)["dids"][2]["fields"][1].update(mask=0x01), "overlaps"),
        (lambda d: _rt(d)["dids"][4].update(vehicle_did="NOPE"), "not in vehicle_cl250"),
        (lambda d: _rt(d)["dids"][4].update(length=3), "length must be 5"),
        (lambda d: _rt(d)["dtcs"][0].update(code="U0101-00"), "does not encode"),
        (lambda d: _rt(d)["dtcs"][1].update(dtc=0xC10000, code="U0100-00"), "unique"),
        (lambda d: _rt(d)["dtcs"][0].update(dtc=0xFFFFFF), "unique"),
        (lambda d: d["transport"].update(functional_request_id=0x7DE), "0x7DF"),
        (lambda d: d["nodes"]["IO"].update(dids=[{"did": 0xF189}]), "no server"),
        (
            lambda d: d["nodes"]["IO"].update(server=_rt(d)["server"], dids=[_rt(d)["dids"][4]]),
            "0x730",
        ),
    ],
)
def test_dids_rejects(dids, iso, vehicle, mutate, needle):
    mutate(dids)
    errors = _errors(dids, iso, vehicle)
    assert any(needle in e for e in errors), errors


def test_vehicle_sample_needs_vehicle_node(dids, iso, vehicle):
    io = dids["nodes"]["IO"]
    io["server"] = copy.deepcopy(_rt(dids)["server"])
    io["server"].update(physical_request_id=0x730, physical_response_id=0x738)
    io["dids"] = [copy.deepcopy(_rt(dids)["dids"][4])]
    assert any("vehicle_sample needs" in e for e in _errors(dids, iso, vehicle))


def test_platform_uds_ids_are_not_in_the_dbc(platform_db, dids):
    ids = {m.frame_id for m in platform_db.messages}
    srv = _rt(dids)["server"]
    assert {srv["physical_request_id"], srv["physical_response_id"], 0x7DF}.isdisjoint(ids)


# --------------------------------------------------------------------------- Q-021 watch


def test_functional_watch_must_be_watch_only(vehicle, platform_db):
    vehicle["addressing"]["functional_watch"]["watch_only"] = False
    assert any("watch_only" in e for e in check_vehicle(vehicle, platform_db))


def test_functional_watch_is_required(vehicle, platform_db):
    del vehicle["addressing"]["functional_watch"]
    assert any("functional_watch missing" in e for e in check_vehicle(vehicle, platform_db))


def test_functional_watch_cannot_alias_the_request_id(vehicle, platform_db):
    vehicle["addressing"]["functional_watch"]["ids"].append(
        {"id_type": "extended_29bit", "id": vehicle["addressing"]["primary"]["request_id"]}
    )
    assert any("duplicates" in e for e in check_vehicle(vehicle, platform_db))


def test_functional_watch_ids_are_the_obd_ones(vehicle):
    ids = {(w["id"], w["id_type"]) for w in vehicle["addressing"]["functional_watch"]["ids"]}
    assert ids == {(0x7DF, "standard_11bit"), (0x18DB33F1, "extended_29bit")}


def test_functional_watch_is_generated(vehicle):
    text = (C_DIR / "rt_core" / "vehicle_cl250.c").read_text()
    assert "{ 0x7DFu, false }" in text and "{ 0x18DB33F1u, true }" in text


# --------------------------------------------------------------------------- ISO header


def _defines(text: str) -> dict[str, int]:
    return {
        m.group(1): int(m.group(2), 16)
        for m in re.finditer(r"#define (UDS_\w+) \((0x[0-9A-F]+)u\)", text)
    }


def test_full_iso_header_is_identical_on_every_full_node():
    texts = {t.directory: (C_DIR / t.directory / "uds_iso14229.h").read_text()
             for t in config.C_TARGETS if t.uds_iso == "full"}  # fmt: skip
    assert len(set(texts.values())) == 1


def test_client_subset_names_nothing_outside_d020():
    """CONN is a vehicle-bus tester only: no name for 0x14, 0x10 02 or server NRCs."""
    defs = _defines((C_DIR / "conn" / "uds_iso14229.h").read_text())
    sids = {
        v for k, v in defs.items() if k.startswith("UDS_SID_") and k != "UDS_SID_NEGATIVE_RESPONSE"
    }
    assert sids <= set(config.ALLOWED_VEHICLE_SERVICES)
    assert "UDS_SID_CLEAR_DIAGNOSTIC_INFORMATION" not in defs
    assert "UDS_SESSION_PROGRAMMING" not in defs
    assert "UDS_GROUP_OF_DTC_ALL" not in defs
    assert {k for k in defs if k.startswith("UDS_NRC_")} == {
        "UDS_NRC_RESPONSE_PENDING",
        "UDS_NRC_SUBFUNCTION_NOT_SUPPORTED_IN_ACTIVE_SESSION",
        "UDS_NRC_SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION",
    }


def test_iso_header_keeps_the_client_names():
    """The names rt-core's client used from its temporary header (D-039 item 1)."""
    for d in ("rt_core", "conn"):
        defs = _defines((C_DIR / d / "uds_iso14229.h").read_text())
        assert defs["UDS_SID_READ_DATA_BY_IDENTIFIER"] == 0x22
        assert defs["UDS_SID_NEGATIVE_RESPONSE"] == 0x7F
        assert defs["UDS_NRC_RESPONSE_PENDING"] == 0x78
        assert defs["UDS_NRC_SUBFUNCTION_NOT_SUPPORTED_IN_ACTIVE_SESSION"] == 0x7E
        assert defs["UDS_NRC_SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION"] == 0x7F


# --------------------------------------------------------------------------- generated C


@pytest.fixture(scope="module")
def lib(tmp_path_factory):
    if CC is None:
        pytest.skip("no C compiler")
    out = tmp_path_factory.mktemp("uds") / "libuds.so"
    d = C_DIR / "rt_core"
    srcs = [str(d / "platform_uds.c"), str(d / "vehicle_cl250.c")]
    subprocess.run([CC, *FLAGS, "-shared", "-fPIC", "-o", str(out), *srcs], check=True)
    so = ctypes.CDLL(str(out))
    for fn in ("platform_uds_service_supported", "platform_uds_session_supported",
               "platform_uds_nrc_suppressed_functional"):  # fmt: skip
        getattr(so, fn).argtypes = [ctypes.c_uint8]
        getattr(so, fn).restype = ctypes.c_bool
    for fn in ("platform_uds_service_allowed_in_session", "platform_uds_subfunction_supported"):
        getattr(so, fn).argtypes = [ctypes.c_uint8, ctypes.c_uint8]
        getattr(so, fn).restype = ctypes.c_bool
    so.platform_uds_find_did.argtypes = [ctypes.c_uint16]
    so.platform_uds_find_did.restype = ctypes.POINTER(DidEntry)
    so.vehicle_cl250_request_allowed.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    so.vehicle_cl250_request_allowed.restype = ctypes.c_bool
    return so


class DidEntry(ctypes.Structure):
    _fields_ = [
        ("did", ctypes.c_uint16),
        ("length", ctypes.c_uint8),
        ("encoding", ctypes.c_uint8),
        ("vehicle_idx", ctypes.c_uint8),
    ]


def test_service_session_matrix_matches_yaml(lib, iso, dids):
    tables = gen_uds.iso_tables(iso)
    srv = _rt(dids)["server"]
    offered = {tables["services"][e["service"]]: e for e in srv["services"]}
    served = {tables["sessions"][s] for s in srv["sessions"]}
    for sid in range(256):
        assert lib.platform_uds_service_supported(sid) == (sid in offered)
        for session in range(256):
            want = sid in offered and session in {
                tables["sessions"][s] for s in offered[sid]["sessions"]
            }
            assert lib.platform_uds_service_allowed_in_session(sid, session) == want
    for session in range(256):
        assert lib.platform_uds_session_supported(session) == (session in served)
    assert not lib.platform_uds_session_supported(0x02)  # no bootloader yet
    assert lib.platform_uds_service_allowed_in_session(0x14, 0x03)
    assert not lib.platform_uds_service_allowed_in_session(0x14, 0x01)  # extended only


def test_subfunctions_match_yaml(lib):
    for sub in range(256):
        assert lib.platform_uds_subfunction_supported(0x3E, sub) == ((sub & 0x7F) == 0x00)
        assert lib.platform_uds_subfunction_supported(0x19, sub) == (
            (sub & 0x7F) in (0x01, 0x02, 0x0A)
        )
        assert not lib.platform_uds_subfunction_supported(0x22, sub)
        assert not lib.platform_uds_subfunction_supported(0x14, sub)


def test_functional_nrc_suppression(lib, iso):
    for nrc in range(256):
        assert lib.platform_uds_nrc_suppressed_functional(nrc) == (
            nrc in iso["functional_suppressed_nrcs"]
        )


def test_did_table_matches_yaml(lib, dids, vehicle):
    vidx = {d["name"]: i for i, d in enumerate(vehicle["dids"])}
    for item in _rt(dids)["dids"]:
        entry = lib.platform_uds_find_did(item["did"]).contents
        assert entry.length == gen_uds.did_length(item, vehicle)
        assert entry.encoding == gen_uds.ENCODINGS.index(item["encoding"])
        want = vidx[item["vehicle_did"]] if item["encoding"] == "vehicle_sample" else 0xFF
        assert entry.vehicle_idx == want
    assert not lib.platform_uds_find_did(0xF190)


@pytest.mark.parametrize(
    "payload",
    [b"\x14\xff\xff\xff", b"\x10\x02", b"\x10\x82", b"\x11\x01", b"\x27\x01", b"\x2e\xf1\x90"],
)
def test_vehicle_gate_still_refuses_server_services(lib, payload):
    """Naming 0x14 / 0x10 02 in uds_iso14229.h widens nothing on the vehicle bus (D-020)."""
    assert not lib.vehicle_cl250_request_allowed(payload, len(payload))


# --------------------------------------------------------------------------- Python


def test_python_module_matches(dids, vehicle):
    ns: dict = {}
    exec((config.GEN_DIR / "python" / "moto_defs" / "uds.py").read_text(), ns)  # noqa: S102
    rt = ns["SERVERS"]["RT_CORE"]
    assert rt["physical_request_id"] == 0x710 and rt["physical_response_id"] == 0x718
    assert ns["TRANSPORT"]["functional_request_id"] == 0x7DF
    assert rt["dids"]["VEHICLE_ENGINE_SPEED"] == (0xFD10, 5, "vehicle_sample")
    assert rt["dtcs"]["VEHICLE_ECU_COMM_LOST"] == (0xC10000, "U0100-00")
    assert ns["SID_CLEAR_DIAGNOSTIC_INFORMATION"] == 0x14
