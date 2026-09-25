from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "gen" / "python"))


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT
