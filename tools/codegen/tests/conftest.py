import copy

import cantools
import pytest

from moto_codegen import config
from moto_codegen.dbc_checks import load_dbc
from moto_codegen.yaml_checks import load_yaml


@pytest.fixture(scope="session")
def platform_db():
    return load_dbc(config.PLATFORM_DBC)


@pytest.fixture
def vehicle():
    return copy.deepcopy(load_yaml(config.VEHICLE_YAML))


@pytest.fixture
def platform_text():
    return config.PLATFORM_DBC.read_text(encoding="utf-8")


def parse_dbc(text: str):
    return cantools.database.load_string(text, database_format="dbc", strict=True)
