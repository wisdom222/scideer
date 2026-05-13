#!/usr/bin/env python3
"""run_experiment.py -- 3-tier code acquisition + sandboxed subprocess execution.

Tiers:
  1. Cache: $SCIDEER_CACHE_DIR/<repo_name>/   (or /mnt/scideer-cache/<repo_name>/)
  2. github_clone: git clone --depth 1 <code_repo_url>  (60s timeout)
  3. template: copy templates/pytorch_skeleton.py into code/

Run convention:
  - Set env SCIDEER_EPOCHS, SCIDEER_LR, SCIDEER_HIDDEN, SCIDEER_DROPOUT, SCIDEER_DATASET
    so the cached code or template can read scaled hparams without arg parsing.
  - Subprocess runs with cwd=code_dir; stdout streams to logs/run.log.
  - Sentinel lines ('SKELETON_METRIC k=v', 'SKELETON_EPOCH n train_loss=v val_acc=v')
    are parsed into metrics.json.

Always writes metrics.json before returning, even on failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
DEFAULT_CACHE_DIR = Path(os.environ.get("SCIDEER_CACHE_DIR", "/mnt/scideer-cache"))
GIT_CLONE_TIMEOUT = 60

METRIC_RE = re.compile(r"SKELETON_METRIC\s+(\w+)\s*=\s*([\d.eE\+\-]+)")
EPOCH_RE = re.compile(
    r"SKELETON_EPOCH\s+(\d+)\s+train_loss=([\d.eE\+\-]+)\s+val_acc=([\d.eE\+\-]+)"
)


def _repo_name_from_url(url: str | None) -> str | None:
    if not url:
        return None
    name = url.rstrip("/").split("/")[-1]
    return name.removesuffix(".git")


def _try_cache(cache_root: Path, repo_url: str | None) -> Path | None:
    """Look for cached code by repo_name (from URL) or common fallbacks (pygcn/gcn).

    Rationale: GCN paper says "github.com/tkipf/gcn" (TF original) but the demo
    cache uses "pygcn" (PyTorch port at github.com/tkipf/pygcn). Always probe
    both common names so the demo path is robust to which repo was cloned.
    """
    candidates: list[str] = []
    repo_name = _repo_name_from_url(repo_url)
    if repo_name:
        candidates.append(repo_name)
    for fallback in ["pygcn", "gcn"]:
        if fallback not in candidates:
            candidates.append(fallback)
    for candidate in candidates:
        cand_dir = cache_root / candidate
        if cand_dir.exists():
            return cand_dir
    return None


def _try_clone(repo_url: str, dst: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(dst)],
            capture_output=True, text=True, timeout=GIT_CLONE_TIMEOUT,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _use_template(workspace_code: Path) -> None:
    template = TEMPLATES_DIR / "pytorch_skeleton.py"
    if not template.exists():
        raise FileNotFoundError(f"template missing: {template}")
    workspace_code.mkdir(parents=True, exist_ok=True)
    shutil.copy(template, workspace_code / "skeleton.py")


def _detect_entrypoint(code_dir: Path) -> Path:
    """Find a runnable Python entrypoint inside code_dir."""
    for name in ["train.py", "main.py", "run.py", "skeleton.py"]:
        for p in code_dir.rglob(name):
            return p
    raise FileNotFoundError(f"No entrypoint found in {code_dir}")


def _build_env(plan: dict) -> dict:
    env = os.environ.copy()
    method = plan.get("method", {})
    scaled = plan.get("scaled_hparams", {}) or {}
    epochs = scaled.get("epochs_used") or method.get("epochs") or 100
    env["SCIDEER_EPOCHS"] = str(epochs)
    env["SCIDEER_LR"] = str(method.get("learning_rate") or 0.01)
    env["SCIDEER_HIDDEN"] = str(method.get("hidden_dim") or 16)
    env["SCIDEER_DROPOUT"] = str(method.get("dropout") or 0.5)
    env["SCIDEER_DATASET"] = str(method.get("dataset") or "Cora")
    if scaled.get("data_subset_size"):
        env["SCIDEER_SUBSET"] = str(scaled["data_subset_size"])
    return env


def _run_subprocess(entrypoint: Path, env: dict, timeout: int, log_path: Path):
    """Run with timeout. Returns (exit_code, stdout_text, errors).

    Uses subprocess.run with a hard timeout. We sacrifice live log streaming
    (log written all at once at the end) for cross-platform timeout reliability:
    blocking readline() on Windows cannot be interrupted by a wall-clock check.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    try:
        result = subprocess.run(
            [sys.executable, entrypoint.name],
            cwd=str(entrypoint.parent),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = (result.stdout or "") + (result.stderr or "")
        log_path.write_text(stdout, encoding="utf-8")
        return result.returncode, stdout, errors
    except subprocess.TimeoutExpired as exc:
        # Capture whatever output was produced before the kill.
        partial = exc.stdout or b""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        log_path.write_text(partial, encoding="utf-8")
        errors.append(f"timeout: killed after {timeout}s")
        return -1, partial, errors


def _parse_metrics(stdout: str) -> tuple[dict, list[dict]]:
    final: dict = {}
    curve: list[dict] = []
    for line in stdout.splitlines():
        m = METRIC_RE.search(line)
        if m:
            key, val = m.group(1), m.group(2)
            try:
                final[key] = float(val) if "." in val or "e" in val.lower() else int(val)
            except ValueError:
                final[key] = val
            continue
        e = EPOCH_RE.search(line)
        if e:
            curve.append({
                "epoch": int(e.group(1)),
                "train_loss": float(e.group(2)),
                "val_acc": float(e.group(3)),
            })
    if "test_accuracy" in final:
        final["test_accuracy_unit"] = "fraction"
    return final, curve


def _scan_for_failure_signals(stdout: str) -> list[str]:
    errors: list[str] = []
    if re.search(r"\bnan\b", stdout, re.IGNORECASE):
        errors.append("nan: training diverged (NaN detected)")
    if re.search(r"OutOfMemoryError|killed|cuda out of memory", stdout, re.IGNORECASE):
        errors.append("oom: out of memory")
    if re.search(r"ModuleNotFoundError|ImportError", stdout):
        errors.append("dep_missing: missing python dependency")
    return errors


def _write_metrics(workspace: Path, **kwargs):
    metrics = {
        "schema_version": "1.0",
        "arxiv_id": kwargs.get("arxiv_id", ""),
        "code_source": kwargs.get("code_source", "unknown"),
        "code_path_in_workspace": kwargs.get("code_path_in_workspace", ""),
        "wall_time_seconds": kwargs.get("wall_time_seconds", 0.0),
        "exit_code": kwargs.get("exit_code", -1),
        "final_metrics": kwargs.get("final_metrics"),
        "training_curve": kwargs.get("training_curve", []),
        "errors": kwargs.get("errors", []),
        "warnings": kwargs.get("warnings", []),
    }
    (workspace / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def _read_cache_dir() -> Path:
    """Re-read SCIDEER_CACHE_DIR each run for testability."""
    return Path(os.environ.get("SCIDEER_CACHE_DIR", "/mnt/scideer-cache"))


def main() -> int:
    parser = argparse.ArgumentParser(description="3-tier code acquire + run.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    plan = json.loads((args.workspace / "repro_plan.json").read_text(encoding="utf-8"))
    code_dir = args.workspace / "code"
    if code_dir.exists():
        shutil.rmtree(code_dir)
    code_dir.mkdir(parents=True)

    # --- 3-tier acquisition ---
    code_source = "unknown"
    repo_url = plan.get("code_repo_url")
    cache_root = _read_cache_dir()

    cached = _try_cache(cache_root, repo_url)
    if cached is not None:
        shutil.copytree(cached, code_dir / cached.name)
        code_source = "cache"
    elif repo_url and _try_clone(repo_url, code_dir / (_repo_name_from_url(repo_url) or "repo")):
        code_source = "github_clone"
    else:
        try:
            _use_template(code_dir)
            code_source = "template"
        except Exception as exc:
            _write_metrics(args.workspace, arxiv_id=plan.get("arxiv_id", ""),
                           code_source="template", exit_code=-1,
                           errors=[f"acquire_failed: all 3 tiers exhausted: {exc}"])
            return 0

    # --- Run ---
    try:
        entrypoint = _detect_entrypoint(code_dir)
    except FileNotFoundError as exc:
        _write_metrics(args.workspace, arxiv_id=plan.get("arxiv_id", ""),
                       code_source=code_source, exit_code=-1,
                       errors=[f"no_entrypoint: {exc}"])
        return 0

    env = _build_env(plan)
    log_path = args.workspace / "logs" / "run.log"
    started = time.time()
    exit_code, stdout, run_errors = _run_subprocess(entrypoint, env, args.timeout, log_path)
    elapsed = time.time() - started

    final_metrics, curve = _parse_metrics(stdout)
    failure_errors = _scan_for_failure_signals(stdout)
    all_errors = run_errors + failure_errors

    _write_metrics(
        args.workspace,
        arxiv_id=plan.get("arxiv_id", ""),
        code_source=code_source,
        code_path_in_workspace=str(entrypoint.parent.relative_to(args.workspace)),
        wall_time_seconds=round(elapsed, 2),
        exit_code=exit_code,
        final_metrics=final_metrics or None,
        training_curve=curve,
        errors=all_errors,
        warnings=[],
    )

    return 0  # always 0 -- comparator decides verdict


if __name__ == "__main__":
    sys.exit(main())
