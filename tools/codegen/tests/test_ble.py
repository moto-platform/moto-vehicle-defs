"""ble/ble_schema.json (D-061): checks, and C, Python and Dart outputs agree with it."""

import copy
import re
import shutil
import subprocess

import pytest

from moto_codegen import config, gen_ble

# Telemetry version 3 as it was in moto-connectivity-node's schema (D-032): name, offset, size.
V3_LAYOUT = [
    ("version", 0, 1), ("seq", 1, 1), ("deviceTimeMs", 2, 4), ("rpm", 6, 2), ("speed", 8, 1),
    ("coolantTemp", 9, 1), ("throttlePos", 10, 1), ("batteryVolt", 11, 2), ("leanAngle", 13, 2),
    ("maxLeanRight", 15, 2), ("maxLeanLeft", 17, 2), ("flags", 19, 1), ("rpmAgeMs", 20, 2),
    ("speedAgeMs", 22, 2), ("coolantTempAgeMs", 24, 2), ("throttlePosAgeMs", 26, 2),
    ("batteryVoltAgeMs", 28, 2), ("canBusState", 30, 1), ("canTxErrorCount", 31, 1),
    ("canRxErrorCount", 32, 1), ("canBusOffCount", 33, 1), ("unansweredDidCount", 34, 2),
    ("canFlags", 36, 1),
]  # fmt: skip
# The v4 fields appended in D-058: name, offset, size.
V4_APPENDED = [
    ("stepGapMaxMs", 37, 2), ("stepGapOverCount", 39, 2), ("rttDid", 41, 2), ("rttMinMs", 43, 2),
    ("rttMaxMs", 45, 2), ("rttSumMs", 47, 4), ("rttCount", 51, 4), ("rttNrc78Count", 55, 2),
]  # fmt: skip


@pytest.fixture(scope="module")
def real():
    return gen_ble.load_schema()


@pytest.fixture
def schema(real):
    return copy.deepcopy(real)


def _errors(schema):
    return gen_ble.check_schema(schema)


def test_checks_pass_on_the_real_file(real):
    assert _errors(real) == []


def _field(schema, name):
    return next(f for f in schema["fields"] if f["name"] == name)


def _mutate_overlap(s):
    _field(s, "rpm")["offset"] -= 1


def _mutate_gap(s):
    _field(s, "speed")["offset"] += 1


def _mutate_size(s):
    _field(s, "rpm")["size"] = 3


def _mutate_unknown_type(s):
    _field(s, "rpm")["type"] = "float"


def _mutate_total(s):
    s["totalBytes"] = 58


def _mutate_total_by_version_v3(s):
    s["totalBytesByVersion"]["3"] = 38


def _mutate_total_by_version_current(s):
    s["totalBytesByVersion"]["4"] = 56


def _mutate_since_version_order(s):
    _field(s, "speed")["sinceVersion"] = 4  # later v3 fields would go back to 3


def _mutate_since_version_range(s):
    _field(s, "rttDid")["sinceVersion"] = 5


def _mutate_fallback_gap(s):
    s["lowMtuFallback"]["fields"][4]["offset"] += 1


def _mutate_fallback_total(s):
    s["lowMtuFallback"]["totalBytes"] = 17


def _mutate_imu_header_gap(s):
    s["imuBlock"]["headerFields"][3]["offset"] += 1


def _mutate_imu_header_bytes(s):
    s["imuBlock"]["headerBytes"] = 13


def _mutate_imu_sample_overlap(s):
    s["imuBlock"]["sampleFields"][2]["offset"] = 3


def _mutate_imu_sample_bytes(s):
    s["imuBlock"]["sampleBytes"] = 14


def _mutate_imu_total_max(s):
    s["imuBlock"]["totalBytesMax"] = 133


def _mutate_flag_duplicate(s):
    s["flags"]["bits"][3]["bit"] = 2


def _mutate_flag_out_of_range(s):
    s["flags"]["bits"][3]["bit"] = 8


def _mutate_can_flag_duplicate(s):
    s["canHealth"]["canFlags"]["bits"][1]["bit"] = 0


def _mutate_imu_flag_duplicate(s):
    s["imuBlock"]["flags"]["bits"][1]["bit"] = 0


def _mutate_uuid(s):
    s["gatt"]["serviceUuid"] = "4fafc201-1fb5-459e-8fcc-c5c9c331914"


def _mutate_uuid_duplicate(s):
    s["gatt"]["characteristics"]["imu"]["uuid"] = s["gatt"]["serviceUuid"]


def _mutate_current_version(s):
    s["versioning"]["currentVersion"] = 3


def _mutate_accepted_versions(s):
    s["versioning"]["acceptedVersions"] = [2, 4]


def _mutate_duplicate_name(s):
    _field(s, "rttCount")["name"] = "rttSumMs"


def _mutate_bad_name(s):
    _field(s, "rttCount")["name"] = "rtt_count"


def _mutate_bus_state_duplicate(s):
    s["canHealth"]["busState"]["values"][1]["value"] = 0


def _gps_field(s, name):
    return next(f for f in s["gpsBlock"]["fields"] if f["name"] == name)


def _mutate_gps_gap(s):
    _gps_field(s, "groundSpeed")["offset"] += 1


def _mutate_gps_total(s):
    s["gpsBlock"]["totalBytes"] = 27


def _mutate_gps_latitude(s):
    _gps_field(s, "reserved").update(name="latitude", size=4, type="int32")
    s["gpsBlock"]["totalBytes"] = 29


def _mutate_gps_height(s):
    _gps_field(s, "reserved")["name"] = "hMsl"


def _mutate_gps_fix_type_duplicate(s):
    s["gpsBlock"]["fixType"]["values"][1]["value"] = 0


def _mutate_gps_flag_duplicate(s):
    s["gpsBlock"]["flags"]["bits"][2]["bit"] = 1


def _mutate_gps_unit(s):
    s["gpsBlock"]["scale"]["speed"]["unit"] = "km/h"


def _mutate_gps_characteristic(s):
    del s["gatt"]["characteristics"]["gps"]


def _mutate_gps_uuid_duplicate(s):
    s["gatt"]["characteristics"]["gps"]["uuid"] = s["gatt"]["characteristics"]["imu"]["uuid"]


MUTATIONS = [
    (_mutate_gps_gap, "gpsBlock.fields"),
    (_mutate_gps_total, "gpsBlock.fields: fields end at 26, but the declared total is 27"),
    (_mutate_gps_latitude, "'latitude' looks like a position"),
    (_mutate_gps_height, "'hMsl' looks like a position"),
    (_mutate_gps_fix_type_duplicate, "gpsBlock.fixType.values"),
    (_mutate_gps_flag_duplicate, "gpsBlock.flags.bits: bit 1"),
    (_mutate_gps_unit, "gpsBlock.scale.speed.unit 'km/h' unknown"),
    (_mutate_gps_characteristic, "gatt.characteristics.gps.uuid"),
    (_mutate_gps_uuid_duplicate, "UUIDs must be unique"),
    (_mutate_overlap, "overlaps"),
    (_mutate_gap, "leaves a gap"),
    (_mutate_size, "does not match type"),
    (_mutate_unknown_type, "unknown type"),
    (_mutate_total, "declared total is 58"),
    (_mutate_total, "totalBytes 58 != totalBytesByVersion[4]"),
    (_mutate_total_by_version_v3, "fields as of version 3"),
    (_mutate_total_by_version_current, "totalBytes 57 != totalBytesByVersion[4]"),
    (_mutate_since_version_order, "sinceVersion goes back"),
    (_mutate_since_version_range, "sinceVersion 5 out of range"),
    (_mutate_fallback_gap, "lowMtuFallback.fields"),
    (_mutate_fallback_total, "lowMtuFallback.fields: fields end at 16"),
    (_mutate_imu_header_gap, "imuBlock.headerFields"),
    (_mutate_imu_header_bytes, "imuBlock.headerFields: fields end at 12"),
    (_mutate_imu_sample_overlap, "imuBlock.sampleFields"),
    (_mutate_imu_sample_bytes, "imuBlock.sampleFields: fields end at 12"),
    (_mutate_imu_total_max, "imuBlock.totalBytesMax 133"),
    (_mutate_flag_duplicate, "flags.bits: bit 2"),
    (_mutate_flag_out_of_range, "bit position must be an integer 0..7"),
    (_mutate_can_flag_duplicate, "canHealth.canFlags.bits: bit 0"),
    (_mutate_imu_flag_duplicate, "imuBlock.flags.bits: bit 0"),
    (_mutate_uuid, "is not a lowercase 128-bit UUID"),
    (_mutate_uuid_duplicate, "UUIDs must be unique"),
    (_mutate_current_version, "currentVersion 3 != version"),
    (_mutate_accepted_versions, "acceptedVersions"),
    (_mutate_duplicate_name, "duplicate name"),
    (_mutate_bad_name, "name must be lowerCamel"),
    (_mutate_bus_state_duplicate, "busState.values"),
]


@pytest.mark.parametrize(("mutate", "expected"), MUTATIONS, ids=lambda x: getattr(x, "__name__", x))
def test_each_check_fails_on_a_mutated_copy(schema, mutate, expected):
    mutate(schema)
    errors = _errors(schema)
    assert any(expected in e for e in errors), (expected, errors)


def test_malformed_schema_is_an_error_not_a_crash(schema):
    del schema["lowMtuFallback"]
    assert _errors(schema)


# --- layouts ---------------------------------------------------------------------------


def _layout(schema, version):
    fields = gen_ble.fields_for_version(schema, version)
    return [(f["name"], f["offset"], f["size"]) for f in fields]


def test_v3_is_the_old_layout_and_a_prefix_of_v4(real):
    assert real["version"] == 4 and real["totalBytes"] == 57
    assert real["totalBytesByVersion"] == {"3": 37, "4": 57}
    assert real["versioning"]["acceptedVersions"] == [2, 3, 4]
    assert _layout(real, 3) == V3_LAYOUT
    assert _layout(real, 4) == V3_LAYOUT + V4_APPENDED
    assert sum(size for _, _, size in V3_LAYOUT) == 37


def test_only_the_appended_fields_have_since_version(real):
    since = {f["name"]: f["sinceVersion"] for f in real["fields"] if "sinceVersion" in f}
    assert since == {name: 4 for name, _, _ in V4_APPENDED}


# --- C, Python and Dart agree ----------------------------------------------------------


def _c_macros(text):
    return {m[1]: int(m[2]) for m in re.finditer(r"^#define (\w+) \((\d+)u\)", text, flags=re.M)}


def _dart_class(text, name):
    """int members of a Dart class; `1 << n` values are evaluated."""
    body = re.search(rf"abstract final class {name} \{{(.*?)\n\}}", text, flags=re.S)
    assert body, f"{name} missing in the Dart output"
    members = re.finditer(r"static const int (\w+) = (\d+|1 << \d+);", body[1])
    return {m[1]: eval(m[2]) for m in members}  # noqa: S307 - generated, digits and `<<` only


@pytest.fixture(scope="module")
def outputs(real):
    c = gen_ble.generate_c(real)["ble_schema.h"]
    dart = gen_ble.generate_dart(real)["lib/ble_schema.dart"]
    py: dict = {}
    exec(compile(gen_ble.generate_python(real), "ble.py", "exec"), py)  # noqa: S102
    return c, dart, py


def test_v4_offsets_agree_in_c_python_and_dart(real, outputs):
    c, dart, py = outputs
    macros = _c_macros(c)
    dart_off = _dart_class(dart, "BleTelemetryV4Offsets")
    dart_size = _dart_class(dart, "BleTelemetryV4Sizes")
    py_fields = py["telemetry_fields"](4)
    assert [f["name"] for f in py_fields] == [n for n, _, _ in V3_LAYOUT + V4_APPENDED]
    for f in py_fields:
        snake = gen_ble._upper_snake(f["name"])
        assert macros[f"BLE_TELEMETRY_V4_{snake}_OFFSET"] == f["offset"], f["name"]
        assert macros[f"BLE_TELEMETRY_V4_{snake}_SIZE"] == f["size"], f["name"]
        assert dart_off[f["name"]] == f["offset"], f["name"]
        assert dart_size[f["name"]] == f["size"], f["name"]
    assert len(dart_off) == len(py_fields)
    assert macros["BLE_TELEMETRY_V4_TOTAL_BYTES"] == py["TOTAL_BYTES"] == 57
    assert _dart_class(dart, "BleTelemetry")["totalBytesV4"] == 57


def test_totals_and_versions_agree(real, outputs):
    c, dart, py = outputs
    macros = _c_macros(c)
    assert macros["BLE_TELEMETRY_CURRENT_VERSION"] == py["CURRENT_VERSION"] == 4
    assert macros["BLE_TELEMETRY_LEGACY_VERSION"] == py["FALLBACK_VERSION"] == 2
    assert py["ACCEPTED_VERSIONS"] == (2, 3, 4)
    assert py["TOTAL_BYTES_BY_VERSION"] == {3: 37, 4: 57}
    assert macros["BLE_TELEMETRY_V3_TOTAL_BYTES"] == 37
    assert macros["BLE_TELEMETRY_V2_TOTAL_BYTES"] == py["FALLBACK_TOTAL_BYTES"] == 16
    assert py["SCHEMA"] == real
    for v, fields in ((2, py["telemetry_fields"](2)), (3, py["telemetry_fields"](3))):
        end = max(f["offset"] + f["size"] for f in fields)
        assert end == {2: 16, 3: 37}[v]
    with pytest.raises(ValueError):
        py["telemetry_fields"](5)


def test_v3_and_v2_offsets_agree_in_dart_and_c(real, outputs):
    c, dart, _ = outputs
    macros = _c_macros(c)
    v3 = _dart_class(dart, "BleTelemetryV3Offsets")
    assert list(v3.items()) == [(n, o) for n, o, _ in V3_LAYOUT]
    v2 = _dart_class(dart, "BleTelemetryV2Offsets")
    for f in real["lowMtuFallback"]["fields"]:
        assert v2[f["name"]] == f["offset"]
        assert macros[f"BLE_TELEMETRY_V2_{gen_ble._upper_snake(f['name'])}_OFFSET"] == f["offset"]


def test_imu_flags_gatt_and_sentinels_agree(real, outputs):
    c, dart, _ = outputs
    macros = _c_macros(c)
    imu = real["imuBlock"]
    block = _dart_class(dart, "BleImuBlock")
    assert block["totalBytesMax"] == macros["BLE_IMU_TOTAL_BYTES_MAX"] == 132
    assert block["headerBytes"] == macros["BLE_IMU_HEADER_BYTES"] == imu["headerBytes"]
    assert macros["BLE_IMU_ACCEL_LSB_PER_G"] == 4096
    assert macros["BLE_IMU_GYRO_LSB_PER_DPS_X10"] == 655
    assert "static const double gyroLsbPerDps = 65.5;" in dart
    assert _dart_class(dart, "BleTelemetryFlagBits")["imuActive"] == 1 << 7
    assert re.search(r"BLE_TELEMETRY_FLAG_IMU_ACTIVE \(1u << 7u\)", c)
    assert re.search(r"BLE_CAN_FLAG_POLLER_ENABLED \(1u << 0u\)", c)
    assert _dart_class(dart, "BleImuFlagBits") == {
        "deviceOverflow": 1,
        "readError": 2,
        "sensorReconfigured": 4,
    }
    assert _dart_class(dart, "BleCanBusState")["busOff"] == 3
    assert macros["BLE_GATT_REQUESTED_MTU"] == _dart_class(dart, "BleGatt")["requestedMtu"] == 185
    assert f'BLE_GATT_SERVICE_UUID "{real["gatt"]["serviceUuid"]}"' in c
    assert f"'{real['gatt']['serviceUuid']}'" in dart


# D-060 item 3: the GPS block as decided, and nothing that locates the rider.
GPS_LAYOUT = [
    ("version", 0, 1), ("seq", 1, 1), ("deviceTimeMs", 2, 4), ("groundSpeed", 6, 4),
    ("headingOfMotion", 10, 4), ("speedAccuracy", 14, 4), ("headingAccuracy", 18, 4),
    ("fixType", 22, 1), ("numSv", 23, 1), ("flags", 24, 1), ("reserved", 25, 1),
]  # fmt: skip


def test_gps_block_agrees_in_c_python_and_dart(real, outputs):
    c, dart, py = outputs
    macros = _c_macros(c)
    fields = py["gps_fields"]()
    assert [(f["name"], f["offset"], f["size"]) for f in fields] == GPS_LAYOUT
    dart_off = _dart_class(dart, "BleGpsOffsets")
    dart_size = _dart_class(dart, "BleGpsSizes")
    for f in fields:
        snake = gen_ble._upper_snake(f["name"])
        assert macros[f"BLE_GPS_{snake}_OFFSET"] == dart_off[f["name"]] == f["offset"]
        assert macros[f"BLE_GPS_{snake}_SIZE"] == dart_size[f["name"]] == f["size"]
    assert macros["BLE_GPS_TOTAL_BYTES"] == py["GPS_TOTAL_BYTES"] == 26
    assert _dart_class(dart, "BleGpsBlock")["totalBytes"] == 26
    assert macros["BLE_GPS_BLOCK_VERSION"] == py["GPS_BLOCK_VERSION"] == 1
    assert macros["BLE_GPS_SPEED_LSB_PER_MPS"] == 1000
    assert macros["BLE_GPS_HEADING_LSB_PER_DEG"] == 100000
    assert _dart_class(dart, "BleGpsScale") == {"speedLsbPerMps": 1000, "headingLsbPerDeg": 100000}
    assert macros["BLE_GPS_FIX_TYPE_FIX3D"] == _dart_class(dart, "BleGpsFixType")["fix3d"] == 3
    assert _dart_class(dart, "BleGpsFlagBits") == {
        "gnssFixOk": 1,
        "parseError": 2,
        "uartOverflow": 4,
    }
    gps_uuid = real["gatt"]["characteristics"]["gps"]["uuid"]
    assert f'"{gps_uuid}"' in c and f"'{gps_uuid}'" in dart


def test_no_position_anywhere_in_the_gps_block(real):
    """D-060 item 3 / invariant 7: latitude, longitude and height never leave conn."""
    names = [f["name"] for f in real["gpsBlock"]["fields"]]
    assert not [n for n in names if gen_ble._POSITION_NAME.search(n)]
    assert real["gpsBlock"]["totalBytes"] == 26


def test_dart_package_files(real):
    files = gen_ble.generate_dart(real)
    assert set(files) == {"pubspec.yaml", "lib/ble_schema.dart", "lib/moto_defs.dart"}
    assert "name: moto_defs" in files["pubspec.yaml"]
    assert "publish_to: none" in files["pubspec.yaml"]
    assert "export 'ble_schema.dart';" in files["lib/moto_defs.dart"]
    for text in files.values():
        assert "GENERATED" in text and "DO NOT EDIT" in text


CC = shutil.which("gcc") or shutil.which("cc")


@pytest.mark.skipif(CC is None, reason="no C compiler")
def test_header_compiles_strict_and_values_hold(tmp_path):
    src = tmp_path / "t.c"
    src.write_text(
        '#include "ble_schema.h"\n'
        "int main(void)\n{\n"
        "    unsigned int ok = 1u;\n"
        "    ok &= (BLE_TELEMETRY_V4_STEP_GAP_MAX_MS_OFFSET == 37u) ? 1u : 0u;\n"
        "    ok &= (BLE_TELEMETRY_V4_RTT_NRC78_COUNT_OFFSET\n"
        "           + BLE_TELEMETRY_V4_RTT_NRC78_COUNT_SIZE\n"
        "           == BLE_TELEMETRY_V4_TOTAL_BYTES) ? 1u : 0u;\n"
        "    ok &= ((BLE_TELEMETRY_FLAG_IMU_ACTIVE\n"
        "            & BLE_TELEMETRY_FLAG_RPM_VALID) == 0u) ? 1u : 0u;\n"
        "    ok &= (BLE_GPS_RESERVED_OFFSET + BLE_GPS_RESERVED_SIZE\n"
        "           == BLE_GPS_TOTAL_BYTES) ? 1u : 0u;\n"
        "    ok &= (BLE_GPS_HEADING_LSB_PER_DEG == 100000u) ? 1u : 0u;\n"
        "    return (ok == 1u) ? 0 : 1;\n}\n",
        encoding="utf-8",
    )
    flags = ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wshadow", "-Wconversion"]
    exe = tmp_path / "t"
    header_dir = config.GEN_DIR / "c" / "conn"
    subprocess.run([CC, *flags, "-I", str(header_dir), str(src), "-o", str(exe)], check=True)
    assert subprocess.run([str(exe)], check=False).returncode == 0
