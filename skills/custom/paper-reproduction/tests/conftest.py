"""Shared pytest fixtures for paper-reproduction tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make scripts/ importable as a package for tests
SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

import pytest


@pytest.fixture
def gcn_paper_text() -> str:
    """Pre-extracted GCN paper text used by extract_method.py tests."""
    fixture_path = Path(__file__).parent / "fixtures" / "gcn_paper_text.txt"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """A clean per-test workspace directory with the right layout."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "code").mkdir()
    (ws / "logs").mkdir()
    (ws / "figures").mkdir()
    return ws


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@pytest.fixture
def write_json():
    return _write_json
