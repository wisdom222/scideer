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
        "schema_version": "1.1",
        "arxiv_id": kwargs.get("arxiv_id", ""),
        "code_source": kwargs.get("code_source", "unknown"),
        "code_path_in_workspace": kwargs.get("code_path_in_workspace", ""),
        "wall_time_seconds": kwargs.get("wall_time_seconds", 0.0),
        "exit_code": kwargs.get("exit_code", -1),
        "final_metrics": kwargs.get("final_metrics"),
        "training_curve": kwargs.get("training_curve", []),
        "errors": kwargs.get("errors", []),
        "warnings": kwargs.get("warnings", []),
        # tier_attempts: chronological list of code-acquisition attempts. Each
        # entry: {"tier": "cache"|"github_clone"|"template",
        #         "outcome": "ran"|"miss"|"no_entrypoint"|"execution_failed",
        #         "reason": short string explaining outcome}
        # Added in schema 1.1 to surface execution-failure fallback chain (e.g.
        # cache acquired but dep_missing -> fell through to template).
        "tier_attempts": kwargs.get("tier_attempts", []),
    }
    (workspace / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def _read_cache_dir() -> Path:
    """Re-read SCIDEER_CACHE_DIR each run for testability."""
    return Path(os.environ.get("SCIDEER_CACHE_DIR", "/mnt/scideer-cache"))


# Reasons that trigger automatic fall-through to the next tier.
# (OOM/timeout/NaN are NOT here -- they're non-recoverable: the next tier would
# hit the same wall, and silently switching would mask real reproduction issues.)
_FALLBACK_REASONS = {"dep_missing", "no_entrypoint"}


def _acquire_cache(cache_root: Path, repo_url: str | None, code_dir: Path) -> tuple[bool, str]:
    cached = _try_cache(cache_root, repo_url)
    if cached is None:
        return False, "cache_miss"
    shutil.copytree(cached, code_dir / cached.name)
    return True, "acquired"


def _acquire_github_clone(repo_url: str | None, code_dir: Path) -> tuple[bool, str]:
    if not repo_url:
        return False, "no_url"
    target = code_dir / (_repo_name_from_url(repo_url) or "repo")
    if _try_clone(repo_url, target):
        return True, "acquired"
    return False, "clone_failed"


def _acquire_template(code_dir: Path) -> tuple[bool, str]:
    try:
        _use_template(code_dir)
        return True, "acquired"
    except FileNotFoundError as exc:
        return False, f"template_missing: {exc}"


def _run_one_tier(code_dir: Path, plan: dict, timeout: int, log_path: Path):
    """Detect entrypoint and run subprocess. Returns a dict describing outcome.

    Keys: status ("ran"|"no_entrypoint"), entrypoint, exit_code, elapsed,
          final_metrics, training_curve, errors.
    """
    try:
        entrypoint = _detect_entrypoint(code_dir)
    except FileNotFoundError as exc:
        return {"status": "no_entrypoint",
                "entrypoint": None, "exit_code": -1, "elapsed": 0.0,
                "final_metrics": None, "training_curve": [],
                "errors": [f"no_entrypoint: {exc}"]}

    env = _build_env(plan)
    started = time.time()
    exit_code, stdout, run_errors = _run_subprocess(entrypoint, env, timeout, log_path)
    elapsed = time.time() - started

    final_metrics, curve = _parse_metrics(stdout)
    failure_errors = _scan_for_failure_signals(stdout)
    return {"status": "ran", "entrypoint": entrypoint,
            "exit_code": exit_code, "elapsed": elapsed,
            "final_metrics": final_metrics, "training_curve": curve,
            "errors": run_errors + failure_errors}


def _is_fallback_eligible(outcome: dict) -> tuple[bool, str]:
    """Decide whether this tier outcome should trigger fall-through to next tier.

    Returns (eligible, reason_string).
    """
    if outcome["status"] == "no_entrypoint":
        return True, "no_entrypoint"
    errors = outcome["errors"]
    if any("dep_missing" in e for e in errors):
        return True, "dep_missing"
    return False, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="3-tier code acquire + run with execution-failure fallback.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    plan = json.loads((args.workspace / "repro_plan.json").read_text(encoding="utf-8"))
    code_dir = args.workspace / "code"
    repo_url = plan.get("code_repo_url")
    cache_root = _read_cache_dir()
    log_path = args.workspace / "logs" / "run.log"

    # Tiers are tried in order. Each tier: clean code_dir, acquire, run.
    # If the run fails with a fallback-eligible reason (dep_missing /
    # no_entrypoint), fall through to the next tier. All other run outcomes
    # (success, OOM, timeout, NaN, generic non-zero exit) are accepted as final
    # — we do not silently mask real reproduction problems with skeleton output.
    tiers_def: list[tuple[str, callable]] = [
        ("cache", lambda: _acquire_cache(cache_root, repo_url, code_dir)),
        ("github_clone", lambda: _acquire_github_clone(repo_url, code_dir)),
        ("template", lambda: _acquire_template(code_dir)),
    ]

    tier_attempts: list[dict] = []
    final_outcome: dict | None = None
    final_tier_name: str = ""

    for tier_name, acquire_fn in tiers_def:
        # Clean code_dir for this tier attempt
        if code_dir.exists():
            shutil.rmtree(code_dir)
        code_dir.mkdir(parents=True)

        acquired, acquire_reason = acquire_fn()
        if not acquired:
            tier_attempts.append({"tier": tier_name, "outcome": "miss", "reason": acquire_reason})
            continue

        # Acquired. Try to run.
        outcome = _run_one_tier(code_dir, plan, args.timeout, log_path)

        eligible, fallback_reason = _is_fallback_eligible(outcome)
        if eligible:
            tier_attempts.append({"tier": tier_name,
                                  "outcome": outcome["status"] if outcome["status"] != "ran" else "execution_failed",
                                  "reason": fallback_reason})
            continue

        # Not eligible for fallback -- accept this outcome as the final result.
        tier_attempts.append({"tier": tier_name, "outcome": "ran", "reason": "accepted"})
        final_outcome = outcome
        final_tier_name = tier_name
        break

    arxiv_id = plan.get("arxiv_id", "")

    if final_outcome is None:
        # All tiers exhausted without a finalisable outcome (e.g. every tier
        # dep_missing'd). Use the last attempted tier as code_source so the
        # comparator can still render a report (verdict will be execution_failed).
        last_tier = tier_attempts[-1]["tier"] if tier_attempts else "unknown"
        chain = " -> ".join(f"{a['tier']}({a['reason']})" for a in tier_attempts)
        _write_metrics(
            args.workspace,
            arxiv_id=arxiv_id,
            code_source=last_tier,
            exit_code=-1,
            final_metrics=None,
            errors=[f"acquire_failed: all tiers exhausted: {chain}"],
            tier_attempts=tier_attempts,
        )
        return 0

    # Successful tier (or non-fallback-eligible failure such as timeout/OOM).
    entrypoint = final_outcome["entrypoint"]
    _write_metrics(
        args.workspace,
        arxiv_id=arxiv_id,
        code_source=final_tier_name,
        code_path_in_workspace=str(entrypoint.parent.relative_to(args.workspace)),
        wall_time_seconds=round(final_outcome["elapsed"], 2),
        exit_code=final_outcome["exit_code"],
        final_metrics=final_outcome["final_metrics"] or None,
        training_curve=final_outcome["training_curve"],
        errors=final_outcome["errors"],
        tier_attempts=tier_attempts,
        warnings=[],
    )

    return 0  # always 0 -- comparator decides verdict


if __name__ == "__main__":
    sys.exit(main())
