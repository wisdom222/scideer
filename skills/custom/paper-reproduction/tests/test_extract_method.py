"""Unit tests for extract_method.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _setup_paper_txt(workspace: Path, text: str):
    (workspace / "paper.txt").write_text(text, encoding="utf-8")


def _run(workspace: Path, target: str, arxiv_id: str = "1609.02907"):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "extract_method.py"),
         "--workspace", str(workspace), "--target", target,
         "--arxiv-id", arxiv_id, "--paper-title", "Semi-Supervised Classification with GCNs"],
        capture_output=True, text=True, check=False,
    )


def test_extract_gcn_hparams(tmp_workspace, gcn_paper_text):
    _setup_paper_txt(tmp_workspace, gcn_paper_text)
    result = _run(tmp_workspace, "Table 2 GCN/Cora row, expected ~81.5%")
    assert result.returncode == 0, result.stderr
    plan = json.loads((tmp_workspace / "repro_plan.json").read_text())
    method = plan["method"]
    assert method["epochs"] == 200
    assert method["learning_rate"] == 0.01
    assert method["dropout"] == 0.5
    assert method["weight_decay"] == 5e-4
    assert method["hidden_dim"] == 16
    assert method["dataset"] == "Cora"
    assert method["model_arch_hint"] == "GCN"


def test_extract_target_verified(tmp_workspace, gcn_paper_text):
    _setup_paper_txt(tmp_workspace, gcn_paper_text)
    result = _run(tmp_workspace, "Table 2 GCN/Cora row, expected ~81.5%")
    plan = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert plan["target"]["expected_value"] == 81.5
    assert plan["target"]["verified_in_paper"] is True


def test_extract_target_not_in_paper_exits_2(tmp_workspace, gcn_paper_text):
    _setup_paper_txt(tmp_workspace, gcn_paper_text)
    result = _run(tmp_workspace, "Table 99 fake metric, expected ~99.9%")
    assert result.returncode == 2
    plan = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert plan["target"]["verified_in_paper"] is False


def test_extract_github_url(tmp_workspace, gcn_paper_text):
    _setup_paper_txt(tmp_workspace, gcn_paper_text)
    _run(tmp_workspace, "Table 2 GCN/Cora row, expected ~81.5%")
    plan = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert plan["code_repo_url"] == "https://github.com/tkipf/gcn"
    assert plan["code_repo_url_source"] == "pdf_grep"


def test_extract_no_github_url(tmp_workspace):
    _setup_paper_txt(tmp_workspace,
                     "Some paper. We trained for 50 epochs with lr 0.001 on MNIST. "
                     "Result: 98.5% accuracy.")
    _run(tmp_workspace, "MNIST result, expected ~98.5%", arxiv_id="9999.12345")
    plan = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert plan["code_repo_url"] is None


def test_extract_missing_paper_txt_errors(tmp_workspace):
    result = _run(tmp_workspace, "Some target, expected ~50%")
    assert result.returncode != 0
