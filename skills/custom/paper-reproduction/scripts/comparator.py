#!/usr/bin/env python3
"""comparator.py — compare reproduced metric to paper value, render report.md."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _percent(value: float | None, unit: str | None) -> float | None:
    """Normalise a metric to percent."""
    if value is None:
        return None
    if unit == "fraction":
        return value * 100.0
    return value  # already percent


def _tolerance(code_source: str, scaled_hparams: dict | None) -> tuple[float, str]:
    base = 0.03
    notes = []
    if code_source == "cache":
        notes.append("cache")
    elif code_source == "github_clone":
        notes.append("github_clone")
        base += 0.02
    elif code_source == "template":
        return 0.15, "template (Tier 3 fallback expects looser fit)"

    sh = scaled_hparams or {}
    if sh.get("data_subset_size"):
        base = max(base, 0.08)
        notes.append("data subsample")
    elif sh.get("epochs_used") is not None:
        base = max(base, 0.05)
        notes.append("epochs scaled")

    return base, " + ".join(notes) if notes else "default"


def _verdict(exit_code: int, our_pct: float | None, paper_pct: float, tol: float) -> str:
    if exit_code != 0 or our_pct is None:
        return "execution_failed"
    rel = abs(our_pct - paper_pct) / abs(paper_pct) if paper_pct else 0.0
    return "within_tolerance" if rel <= tol else "deviated"


def _emoji(v: str) -> str:
    return {"within_tolerance": "OK", "deviated": "WARN", "execution_failed": "FAIL"}[v]


def _verdict_text(v: str) -> str:
    return {"within_tolerance": "Within tolerance",
            "deviated": "Deviated",
            "execution_failed": "Execution failed"}[v]


def _conclusion(cmp: dict, errors: list[str]) -> str:
    v = cmp["verdict"]
    if v == "within_tolerance":
        return f"Reproduction successful within +/-{cmp['tolerance_used']:.0%} tolerance."
    if v == "deviated":
        delta_pct = cmp["delta_relative"] * 100
        hint = "scale-down" if cmp.get("scale_down_applied") else "hparam mismatch or training instability"
        return f"Reproduction deviated by {delta_pct:+.1f}%; possible cause: {hint}."
    first_err = errors[0] if errors else "unknown error"
    return f"Execution failed: {first_err}. Manual intervention required."


def _method_table(method: dict) -> str:
    rows = ["| Hparam | Value | Source |", "|---|---|---|"]
    for k in ["epochs", "learning_rate", "batch_size", "weight_decay",
              "hidden_dim", "dropout", "num_layers", "model_arch_hint", "dataset"]:
        if k in method:
            rows.append(f"| {k} | {method[k]} | {method.get('extracted_via', 'regex')} |")
    return "\n".join(rows)


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "None"
    return "\n".join(f"- {x}" for x in items)


def _scale_down_block(scaled: dict | None) -> str:
    if not scaled:
        return "None applied -- full hparams used."
    parts = []
    if scaled.get("epochs_used"):
        parts.append(f"- Epochs used: {scaled['epochs_used']}")
    if scaled.get("data_subset_size"):
        parts.append(f"- Data subsample: {scaled['data_subset_size']} samples")
    if scaled.get("rationale"):
        parts.append(f"- Rationale: {scaled['rationale']}")
    return "\n".join(parts) if parts else "None applied."


def _figures_block(output_dir: Path) -> str:
    figs = ["training_curve.png", "accuracy_curve.png"]
    blocks = []
    for f in figs:
        if (output_dir / "figures" / f).exists():
            blocks.append(f"![{f}](figures/{f})")
    return "\n".join(blocks) if blocks else "(no figures generated)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare reproduction vs paper, render report.md.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    plan = json.loads((args.workspace / "repro_plan.json").read_text(encoding="utf-8"))
    metrics = json.loads((args.workspace / "metrics.json").read_text(encoding="utf-8"))

    # Tolerance determination
    code_source = metrics.get("code_source", "cache")
    scaled = plan.get("scaled_hparams", {})
    scale_down_applied = bool(scaled and (scaled.get("epochs_used") is not None or
                                           scaled.get("data_subset_size")))
    tol, tol_basis = _tolerance(code_source, scaled)

    # Metric extraction
    target = plan["target"]
    paper_pct = _percent(target.get("expected_value"), target.get("expected_unit", "percent"))
    final_metrics = metrics.get("final_metrics") or {}
    our_pct = _percent(final_metrics.get("test_accuracy"),
                       final_metrics.get("test_accuracy_unit", "fraction"))

    delta_abs = (our_pct - paper_pct) if (our_pct is not None and paper_pct is not None) else None
    delta_rel = (delta_abs / paper_pct) if (delta_abs is not None and paper_pct) else None
    verdict = _verdict(metrics.get("exit_code", 0), our_pct, paper_pct, tol)

    cmp = {
        "schema_version": "1.0",
        "arxiv_id": metrics.get("arxiv_id") or plan.get("arxiv_id"),
        "paper_value": paper_pct,
        "paper_unit": "percent",
        "our_value": round(our_pct, 2) if our_pct is not None else None,
        "our_unit": "percent",
        "delta_absolute": round(delta_abs, 2) if delta_abs is not None else None,
        "delta_relative": round(delta_rel, 4) if delta_rel is not None else None,
        "tolerance_used": round(tol, 4),
        "tolerance_basis": tol_basis,
        "verdict": verdict,
        "wall_time_seconds": metrics.get("wall_time_seconds"),
        "code_source": code_source,
        "scale_down_applied": scale_down_applied,
    }

    # Render report
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "comparison.json").write_text(json.dumps(cmp, indent=2), encoding="utf-8")

    # Copy workspace artifacts to output
    for sub in ["code", "logs", "figures"]:
        src = args.workspace / sub
        dst = args.output / sub
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    template = (TEMPLATES_DIR / "report.md.tmpl").read_text(encoding="utf-8")
    rendered = template.format(
        paper_title=plan.get("paper_title", "(unknown title)"),
        arxiv_id=cmp["arxiv_id"],
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        verdict_emoji=_emoji(verdict),
        verdict_text=_verdict_text(verdict),
        target_description=target.get("description", "(none)"),
        paper_value=cmp["paper_value"] if cmp["paper_value"] is not None else "?",
        our_value=cmp["our_value"] if cmp["our_value"] is not None else "?",
        unit="%",
        delta_absolute_signed=(f"{cmp['delta_absolute']:+.2f}" if cmp["delta_absolute"] is not None else "?"),
        delta_relative_signed=(f"{cmp['delta_relative']:+.2%}" if cmp["delta_relative"] is not None else "?"),
        tolerance_pct=f"{cmp['tolerance_used']:.0%}",
        tolerance_basis=cmp["tolerance_basis"],
        wall_time_seconds=f"{cmp['wall_time_seconds']:.1f}" if cmp["wall_time_seconds"] else "?",
        code_source=code_source,
        code_repo_url=plan.get("code_repo_url") or "N/A",
        scale_down_block=_scale_down_block(scaled),
        figures_block=_figures_block(args.output),
        method_table=_method_table(plan.get("method", {})),
        warnings_block=_bullet_list(plan.get("warnings", []) + metrics.get("warnings", [])),
        errors_block=_bullet_list(metrics.get("errors", [])),
        conclusion_line=_conclusion(cmp, metrics.get("errors", [])),
    )
    (args.output / "report.md").write_text(rendered, encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
