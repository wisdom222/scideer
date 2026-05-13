"""Unit tests for comparator.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _make_metrics(workspace: Path, write_json, **overrides):
    metrics = {
        "schema_version": "1.0",
        "arxiv_id": "1609.02907",
        "code_source": "cache",
        "wall_time_seconds": 32.4,
        "exit_code": 0,
        "final_metrics": {
            "test_accuracy": 0.8023,
            "test_accuracy_unit": "fraction",
            "epochs_actually_run": 100,
        },
        "training_curve": [],
        "errors": [],
        "warnings": [],
    }
    metrics.update(overrides)
    write_json(workspace / "metrics.json", metrics)


def _make_plan(workspace: Path, write_json, **overrides):
    plan = {
        "schema_version": "1.0",
        "arxiv_id": "1609.02907",
        "paper_title": "Semi-Supervised Classification with GCNs",
        "target": {
            "description": "Table 2 GCN/Cora row, expected ~81.5%",
            "metric_name": "test_accuracy",
            "expected_value": 81.5,
            "expected_unit": "percent",
            "verified_in_paper": True,
        },
        "method": {"model_arch_hint": "GCN", "dataset": "Cora", "epochs": 200,
                   "learning_rate": 0.01},
        "code_repo_url": "https://github.com/tkipf/gcn",
        "scaled_hparams": {"epochs_used": 100, "data_subset_size": None,
                           "rationale": "halved epochs"},
        "warnings": [],
    }
    plan.update(overrides)
    write_json(workspace / "repro_plan.json", plan)


def _run(workspace: Path, output: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "comparator.py"),
         "--workspace", str(workspace), "--output", str(output)],
        capture_output=True, text=True, check=False,
    )


def test_comparator_within_tolerance_cache_scaled(tmp_workspace, write_json, tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    _make_plan(tmp_workspace, write_json)
    _make_metrics(tmp_workspace, write_json)

    result = _run(tmp_workspace, output)

    assert result.returncode == 0, result.stderr
    cmp = json.loads((output / "comparison.json").read_text())
    assert cmp["verdict"] == "within_tolerance"
    assert cmp["tolerance_used"] == 0.05  # cache + scale_down -> 5%
    assert cmp["paper_value"] == 81.5
    assert cmp["our_value"] == pytest.approx(80.23, abs=0.1)
    assert (output / "report.md").exists()


def test_comparator_deviated(tmp_workspace, write_json, tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    _make_plan(tmp_workspace, write_json)
    _make_metrics(tmp_workspace, write_json,
                  final_metrics={"test_accuracy": 0.65, "test_accuracy_unit": "fraction",
                                 "epochs_actually_run": 100})
    result = _run(tmp_workspace, output)
    assert result.returncode == 0
    cmp = json.loads((output / "comparison.json").read_text())
    assert cmp["verdict"] == "deviated"


def test_comparator_execution_failed(tmp_workspace, write_json, tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    _make_plan(tmp_workspace, write_json)
    _make_metrics(tmp_workspace, write_json,
                  exit_code=137, final_metrics=None,
                  errors=["oom: process killed at epoch 23"])
    result = _run(tmp_workspace, output)
    assert result.returncode == 0  # comparator itself succeeds even on exec failure
    cmp = json.loads((output / "comparison.json").read_text())
    assert cmp["verdict"] == "execution_failed"
    report = (output / "report.md").read_text()
    assert "OOM" in report or "oom" in report


def test_comparator_template_tolerance_widens(tmp_workspace, write_json, tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    _make_plan(tmp_workspace, write_json)
    _make_metrics(tmp_workspace, write_json, code_source="template",
                  final_metrics={"test_accuracy": 0.70, "test_accuracy_unit": "fraction",
                                 "epochs_actually_run": 100})
    result = _run(tmp_workspace, output)
    cmp = json.loads((output / "comparison.json").read_text())
    assert cmp["tolerance_used"] >= 0.15
    assert cmp["verdict"] == "within_tolerance"  # template tolerance covers 11.5pp gap


def test_comparator_subsample_tolerance(tmp_workspace, write_json, tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    _make_plan(tmp_workspace, write_json,
               scaled_hparams={"epochs_used": 5, "data_subset_size": 10000,
                               "rationale": "subsample MNIST"})
    _make_metrics(tmp_workspace, write_json,
                  final_metrics={"test_accuracy": 0.95, "test_accuracy_unit": "fraction",
                                 "epochs_actually_run": 5})
    result = _run(tmp_workspace, output)
    cmp = json.loads((output / "comparison.json").read_text())
    assert cmp["tolerance_used"] == 0.08  # cache + subsample
