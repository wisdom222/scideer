"""Unit tests for run_experiment.py."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _make_plan(workspace: Path, **overrides):
    plan = {
        "schema_version": "1.0",
        "arxiv_id": "1609.02907",
        "method": {"dataset": "Cora", "model_arch_hint": "GCN",
                   "epochs": 200, "learning_rate": 0.01,
                   "hidden_dim": 16, "dropout": 0.5},
        "code_repo_url": "https://github.com/tkipf/gcn",
        "scaled_hparams": {"epochs_used": 5, "data_subset_size": None,
                           "rationale": "test"},
    }
    plan.update(overrides)
    (workspace / "repro_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")


def _run(workspace: Path, cache_dir: Path | None = None, timeout: int = 60):
    env = os.environ.copy()
    if cache_dir:
        env["SCIDEER_CACHE_DIR"] = str(cache_dir)
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "run_experiment.py"),
         "--workspace", str(workspace), "--timeout", str(timeout)],
        capture_output=True, text=True, check=False, env=env,
    )


def test_tier1_cache_hit(tmp_workspace, tmp_path):
    """Fake cache contains pygcn/train.py; run_experiment.py copies + runs it."""
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    shutil.copytree(FIXTURES_DIR / "fake_cache" / "pygcn", cache_root / "pygcn")
    _make_plan(tmp_workspace)
    result = _run(tmp_workspace, cache_dir=cache_root)
    assert result.returncode == 0, result.stderr
    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    assert metrics["code_source"] == "cache"
    assert metrics["exit_code"] == 0
    assert metrics["final_metrics"]["test_accuracy"] == pytest.approx(0.8023)


def test_tier3_template_when_no_cache_no_repo(tmp_workspace, tmp_path):
    """No cache + no repo URL -> falls through to Tier 3 template skeleton."""
    cache_root = tmp_path / "empty_cache"
    cache_root.mkdir()
    _make_plan(tmp_workspace, code_repo_url=None)
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=120)
    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    # Tier 3 may succeed (Cora skeleton) or fail (deps missing); either way code_source=template
    assert metrics["code_source"] == "template"


def test_timeout_kills_subprocess(tmp_workspace, tmp_path):
    """A stub that sleeps forever should be killed by --timeout."""
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "pygcn").mkdir()
    (cache_root / "pygcn" / "train.py").write_text(
        "import time\nwhile True: time.sleep(1)\n", encoding="utf-8"
    )
    _make_plan(tmp_workspace)
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=2)
    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    assert metrics["exit_code"] != 0
    assert any("timeout" in e.lower() for e in metrics["errors"])
