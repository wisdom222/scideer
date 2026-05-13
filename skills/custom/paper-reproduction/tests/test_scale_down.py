"""Unit tests for scale_down.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _run_scale_down(workspace: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "scale_down.py"), "--workspace", str(workspace)],
        capture_output=True, text=True, check=False,
    )


def test_scale_down_halves_epochs(tmp_workspace, write_json):
    plan = {
        "schema_version": "1.0",
        "arxiv_id": "1609.02907",
        "method": {"epochs": 200, "dataset": "Cora"},
    }
    write_json(tmp_workspace / "repro_plan.json", plan)

    result = _run_scale_down(tmp_workspace)

    assert result.returncode == 0, result.stderr
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["epochs_used"] == 100
    assert out["scaled_hparams"]["data_subset_size"] is None


def test_scale_down_floors_at_min(tmp_workspace, write_json):
    plan = {"method": {"epochs": 10, "dataset": "Cora"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    assert result.returncode == 0
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["epochs_used"] == 10


def test_scale_down_subsamples_large_dataset(tmp_workspace, write_json):
    plan = {"method": {"epochs": 10, "dataset": "MNIST"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    assert result.returncode == 0
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["data_subset_size"] == 10000


def test_scale_down_keeps_small_dataset(tmp_workspace, write_json):
    plan = {"method": {"epochs": 200, "dataset": "Cora"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["data_subset_size"] is None


def test_scale_down_handles_null_epochs(tmp_workspace, write_json):
    plan = {"method": {"epochs": None, "dataset": "Cora"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    assert result.returncode == 0
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["epochs_used"] is None


def test_scale_down_missing_workspace_file_errors(tmp_workspace):
    result = _run_scale_down(tmp_workspace)
    assert result.returncode != 0
    assert "missing" in result.stderr.lower()


def test_scale_down_is_idempotent(tmp_workspace, write_json):
    """Running scale_down twice on the same file produces identical output."""
    plan = {"method": {"epochs": 200, "dataset": "Cora"}}
    write_json(tmp_workspace / "repro_plan.json", plan)

    # First run
    result1 = _run_scale_down(tmp_workspace)
    assert result1.returncode == 0
    after_first = (tmp_workspace / "repro_plan.json").read_text()

    # Second run
    result2 = _run_scale_down(tmp_workspace)
    assert result2.returncode == 0
    after_second = (tmp_workspace / "repro_plan.json").read_text()

    assert after_first == after_second


def test_scale_down_handles_string_epochs_gracefully(tmp_workspace, write_json):
    """Defensive: if epochs is a string (from a malformed plan), epochs_used is null instead of crashing."""
    plan = {"method": {"epochs": "200", "dataset": "Cora"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    assert result.returncode == 0, result.stderr
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["epochs_used"] is None
