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
    """Halving rule still applies for non-small datasets.

    NOTE: this test used to use dataset=Cora and assert epochs_used==100, but
    scale_down.py now skips halving for SMALL_DATASETS (Cora/Citeseer/Pubmed)
    because they train in <5s on CPU at full epochs. Use ImageNet here to
    exercise the halving branch; see test_scale_down_keeps_small_dataset_epochs
    for the small-dataset path.
    """
    plan = {
        "schema_version": "1.0",
        "arxiv_id": "1512.03385",
        "method": {"epochs": 200, "dataset": "ImageNet"},
    }
    write_json(tmp_workspace / "repro_plan.json", plan)

    result = _run_scale_down(tmp_workspace)

    assert result.returncode == 0, result.stderr
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["epochs_used"] == 100
    assert out["scaled_hparams"]["data_subset_size"] == 10000


def test_scale_down_keeps_small_dataset_epochs(tmp_workspace, write_json):
    """SMALL_DATASETS (Cora/Citeseer/Pubmed) keep original epochs unscaled.

    Regression: scale-down used to always halve epochs regardless of dataset.
    For tiny graph datasets that train in seconds, halving just hurts
    convergence (e.g. GCN/Cora at 100 epochs got 77%, at 200 epochs got 83%)
    without saving any meaningful wall-clock budget.
    """
    for dataset in ("Cora", "Citeseer", "Pubmed"):
        plan = {"method": {"epochs": 200, "dataset": dataset}}
        write_json(tmp_workspace / "repro_plan.json", plan)

        result = _run_scale_down(tmp_workspace)

        assert result.returncode == 0, result.stderr
        out = json.loads((tmp_workspace / "repro_plan.json").read_text())
        assert out["scaled_hparams"]["epochs_used"] == 200, (
            f"{dataset}: expected epochs_used=200 (no halving for small datasets), "
            f"got {out['scaled_hparams']['epochs_used']}"
        )
        assert out["scaled_hparams"]["data_subset_size"] is None
        assert "no scaling needed" in out["scaled_hparams"]["rationale"].lower(), (
            f"{dataset}: rationale should say 'no scaling needed' when nothing was scaled, "
            f"got {out['scaled_hparams']['rationale']!r}"
        )


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
