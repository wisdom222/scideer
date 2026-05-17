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


def test_dep_missing_falls_back_to_next_tier(tmp_workspace, tmp_path):
    """Tier 1 acquires code but it fails with ModuleNotFoundError -> falls back to Tier 3.

    This guards against the demo failure observed on 2026-05-13 where Tier 2
    cloned the official tkipf/gcn (TensorFlow 1.x) which lacked sandbox deps.
    Tier 2 'acquired' but couldn't run, so the old code reported execution_failed
    instead of falling through to the PyTorch skeleton.
    """
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "pygcn").mkdir()
    # Tier 1 cache contains code that imports a nonexistent module
    (cache_root / "pygcn" / "train.py").write_text(
        "import this_module_does_not_exist_xyz\nprint('should never reach this line')\n",
        encoding="utf-8",
    )
    _make_plan(tmp_workspace, code_repo_url=None)  # skip Tier 2 cleanly
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=30)

    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    # Tier 1 was tried but dep_missing -> fell back to Tier 3
    # (Tier 3 template may itself fail with dep_missing if torch/torch_geometric
    # are absent in the test environment; that's fine, we just need to see the
    # tier chain was attempted.)
    assert "tier_attempts" in metrics, "metrics.json must include tier_attempts after refactor"
    attempts = metrics["tier_attempts"]
    assert len(attempts) >= 2, f"expected fallback chain, got: {attempts}"
    # First attempt: cache, dep_missing
    assert attempts[0]["tier"] == "cache"
    assert "dep_missing" in attempts[0]["reason"]
    # Last attempt: template (whether it succeeds or also dep_missings is env-dependent)
    assert attempts[-1]["tier"] == "template"
    # Final code_source reflects the last tier attempted
    assert metrics["code_source"] == "template"


def test_no_entrypoint_falls_back_to_next_tier(tmp_workspace, tmp_path):
    """Tier 1 acquires an empty directory (no train.py) -> falls back."""
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "pygcn").mkdir()  # empty dir, no entrypoint
    _make_plan(tmp_workspace, code_repo_url=None)
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=30)
    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    assert "tier_attempts" in metrics
    attempts = metrics["tier_attempts"]
    assert attempts[0]["tier"] == "cache"
    assert "no_entrypoint" in attempts[0]["reason"]
    # Fell through to template
    assert metrics["code_source"] == "template"


def test_epochs_flag_passed_when_entrypoint_supports_it(tmp_workspace, tmp_path):
    """run_experiment should pass --epochs <N> to entrypoints that accept it.

    Regression: previously run_experiment only set SCIDEER_EPOCHS env var, but
    many reference codebases (e.g. tkipf/pygcn) use argparse with their own
    defaults and ignore env vars. The result: scale_down outputs `epochs_used`
    that has no effect on actual training, breaking the scale-down contract.
    """
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "pygcn").mkdir()
    # Entrypoint that DOES accept --epochs and echoes the value it received.
    (cache_root / "pygcn" / "train.py").write_text(
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--epochs', type=int, default=200)\n"
        "args = p.parse_args()\n"
        "print(f'SKELETON_METRIC epochs_actually_run={args.epochs}', flush=True)\n"
        "print(f'SKELETON_METRIC test_accuracy=0.5', flush=True)\n",
        encoding="utf-8",
    )
    _make_plan(tmp_workspace,
               scaled_hparams={"epochs_used": 7, "data_subset_size": None,
                               "rationale": "halved epochs (200->7)"})
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=30)
    assert result.returncode == 0, result.stderr

    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    assert metrics["exit_code"] == 0
    # The entrypoint echoed back the value of --epochs it received.
    # If run_experiment passed --epochs 7, this should be 7.
    # If run_experiment only relied on env vars (the bug), the value would be 200.
    assert metrics["final_metrics"]["epochs_actually_run"] == 7, (
        "run_experiment.py should pass --epochs 7 to entrypoints that support it; "
        f"entrypoint received default 200 instead, suggesting --epochs was not passed."
    )


def test_pythonpath_lets_packaged_repo_import_sibling_module(tmp_workspace, tmp_path):
    """Reference repos like tkipf/pygcn use `from pygcn.utils import load_data`,
    which only works if the *package root* (pygcn/, the parent of pygcn/pygcn/
    where train.py lives) is on PYTHONPATH. Without this, every Tier-1 run
    against a packaged reference repo dep_missing's.

    Regression: previously _run_subprocess only set cwd=entrypoint.parent
    (i.e. pygcn/pygcn/), so `import pygcn` failed because pygcn/ itself
    wasn't on sys.path. Fix: inject entrypoint.parent + parent.parent +
    parent.parent.parent into PYTHONPATH.
    """
    cache_root = tmp_path / "cache"
    # Mimic tkipf/pygcn layout: cache_root/pygcn/pygcn/{train.py,utils.py}
    pkg_root = cache_root / "pygcn"
    pkg_inner = pkg_root / "pygcn"
    pkg_inner.mkdir(parents=True)
    (pkg_inner / "__init__.py").write_text("", encoding="utf-8")
    (pkg_inner / "utils.py").write_text(
        "def load_data():\n    return 'cora-data'\n", encoding="utf-8",
    )
    (pkg_inner / "train.py").write_text(
        "from pygcn.utils import load_data\n"
        "data = load_data()\n"
        "print(f'SKELETON_METRIC test_accuracy=0.7', flush=True)\n",
        encoding="utf-8",
    )
    _make_plan(tmp_workspace)
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=30)

    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    assert metrics["exit_code"] == 0, (
        f"packaged import should resolve via PYTHONPATH injection; "
        f"got exit_code={metrics['exit_code']}, errors={metrics.get('errors')}"
    )
    assert metrics["final_metrics"]["test_accuracy"] == 0.7


def test_run_history_log_preserves_per_tier_output(tmp_workspace, tmp_path):
    """When a tier falls through, the next tier's stdout overwrites run.log.
    run_history.log appends so debug-after-the-fact retains every tier's
    output. Triggers cache(dep_missing) -> template fallback chain.
    """
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "pygcn").mkdir()
    (cache_root / "pygcn" / "train.py").write_text(
        "import this_module_does_not_exist_xyz\n", encoding="utf-8",
    )
    _make_plan(tmp_workspace, code_repo_url=None)
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=30)

    history = (tmp_workspace / "logs" / "run_history.log")
    assert history.exists(), "run_history.log should be created on tier execution"
    history_text = history.read_text(encoding="utf-8")
    # Both attempts (cache + template) should have left a banner each.
    assert history_text.count("=== TIER ATTEMPT") >= 2, (
        f"expected >=2 tier banners in run_history.log, got: {history_text[:500]}"
    )


def test_epochs_flag_skipped_when_entrypoint_rejects_it(tmp_workspace, tmp_path):
    """If entrypoint doesn't accept --epochs (argparse would reject), skip it.

    Pre-probe via --help should detect the absence and not pass --epochs.
    Falls back to env-var convention (entrypoint uses its own default).
    """
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "pygcn").mkdir()
    # Entrypoint that does NOT take --epochs. If run_experiment naively passes
    # --epochs, argparse will exit with 2 and the test fails.
    (cache_root / "pygcn" / "train.py").write_text(
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--steps', type=int, default=42)\n"  # NOT --epochs
        "args = p.parse_args()\n"
        "print(f'SKELETON_METRIC test_accuracy=0.5', flush=True)\n",
        encoding="utf-8",
    )
    _make_plan(tmp_workspace,
               scaled_hparams={"epochs_used": 7, "data_subset_size": None,
                               "rationale": "halved"})
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=30)

    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    # Entrypoint should have run cleanly (no argparse rejection). exit_code=0.
    assert metrics["exit_code"] == 0, (
        f"Entrypoint without --epochs flag should still run; got exit_code="
        f"{metrics['exit_code']} with errors={metrics.get('errors')}"
    )
    assert metrics["final_metrics"]["test_accuracy"] == 0.5
