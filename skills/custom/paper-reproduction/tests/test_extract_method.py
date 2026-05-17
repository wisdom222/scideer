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


def test_arch_defaults_fill_when_regex_misses_gcn(tmp_workspace):
    """When the paper text mentions GCN+Cora but no hparams are extractable,
    fall back to GCN's well-known reference defaults.

    Regression: a real production run on 2026-05-17 produced repro_plan.json
    with most hparams as None even though the paper is a GCN paper with
    long-established defaults. Empty hparams cascade into useless report
    tables ("| learning_rate | None | regex |") and force scripts to fall
    back to their own hardcoded defaults silently.

    Fix: extract_method.py should fill None hparams from KNOWN_ARCH_DEFAULTS
    when the architecture is identifiable (model_arch_hint).
    """
    # Paper text that mentions GCN + Cora + the target value, but NO hparam text.
    # All hparam regex patterns should miss; defaults should fill in.
    minimal_text = (
        "We propose a GCN model. We evaluate on the Cora citation dataset.\n"
        "Table 2 reports test accuracy of 81.5% on Cora.\n"
        "Code at https://github.com/tkipf/gcn for reproducibility.\n"
    )
    _setup_paper_txt(tmp_workspace, minimal_text)
    result = _run(tmp_workspace, "Table 2 GCN/Cora row, expected ~81.5%")
    assert result.returncode == 0, result.stderr

    plan = json.loads((tmp_workspace / "repro_plan.json").read_text())
    method = plan["method"]
    # Arch + dataset still extracted normally
    assert method["model_arch_hint"] == "GCN"
    assert method["dataset"] == "Cora"
    # These should all be filled from GCN reference defaults, not None
    assert method["epochs"] == 200, f"epochs default expected 200, got {method['epochs']}"
    assert method["learning_rate"] == 0.01
    assert method["hidden_dim"] == 16
    assert method["dropout"] == 0.5
    assert method["weight_decay"] == 5e-4
    # Warnings should note the defaults were applied
    warnings_blob = " ".join(plan["warnings"])
    assert "GCN" in warnings_blob and "default" in warnings_blob.lower(), (
        f"warnings should mention GCN reference defaults were applied; got: {plan['warnings']}"
    )


def test_arch_defaults_do_not_override_regex_extraction(tmp_workspace, gcn_paper_text):
    """When the paper text DOES contain hparams, regex values win over defaults.

    Belt-and-suspenders: ensure adding the fallback doesn't shadow successful
    extractions. Uses the full GCN paper fixture which has all hparams.
    """
    _setup_paper_txt(tmp_workspace, gcn_paper_text)
    result = _run(tmp_workspace, "Table 2 GCN/Cora row, expected ~81.5%")
    assert result.returncode == 0
    plan = json.loads((tmp_workspace / "repro_plan.json").read_text())
    method = plan["method"]
    # These match what test_extract_gcn_hparams expects (regex extraction);
    # if the defaults shadowed regex, these would still pass coincidentally
    # because the defaults match. But the warnings should be clean.
    assert method["epochs"] == 200
    assert method["learning_rate"] == 0.01
    # Warnings should NOT mention defaults being used (because regex found them)
    warnings_blob = " ".join(plan["warnings"]).lower()
    assert "reference default" not in warnings_blob, (
        f"defaults should not be applied when regex succeeded; got warnings: {plan['warnings']}"
    )


def test_arch_defaults_skipped_for_unknown_arch(tmp_workspace):
    """When the architecture is unknown (no model_arch_hint), don't fabricate defaults."""
    text = (
        "We propose a novel ZetaNet architecture on the MyCustomDataset.\n"
        "Result: 99.9% accuracy as shown in Table 1.\n"
    )
    _setup_paper_txt(tmp_workspace, text)
    result = _run(tmp_workspace, "Table 1 result, expected ~99.9%", arxiv_id="9999.99999")
    plan = json.loads((tmp_workspace / "repro_plan.json").read_text())
    method = plan["method"]
    # No arch match -> no defaults applied
    assert method["model_arch_hint"] is None
    assert method["epochs"] is None
    assert method["learning_rate"] is None
