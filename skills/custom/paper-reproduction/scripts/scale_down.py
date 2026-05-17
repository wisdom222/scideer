#!/usr/bin/env python3
"""scale_down.py — derive scaled hparams to fit CPU < 5 min budget.

Reads workspace/repro_plan.json, writes back the same file with a new
`scaled_hparams` field. Two rules:
  - epochs_used = max(10, original_epochs // 2)
  - data_subset_size = 10000 if dataset training set > 10K else None
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Datasets known to be small enough to use in full.
SMALL_DATASETS = {"Cora", "Citeseer", "Pubmed"}
SUBSAMPLE_SIZE = 10000
MIN_EPOCHS = 10


def _scale_epochs(original: int | None, dataset: str | None = None) -> int | None:
    if original is None:
        return None
    if not isinstance(original, int) or isinstance(original, bool):
        return None
    # Small graph datasets (Cora/Citeseer/Pubmed) train in <5s on CPU at full
    # 200 epochs — halving them just hurts convergence without saving runtime.
    # Mirrors _scale_data() logic so both axes of scaling respect SMALL_DATASETS.
    if dataset in SMALL_DATASETS:
        return original
    return max(MIN_EPOCHS, original // 2)


def _scale_data(dataset: str | None) -> int | None:
    if dataset is None or dataset in SMALL_DATASETS:
        return None
    return SUBSAMPLE_SIZE


def scale(plan: dict) -> dict:
    method = plan.get("method", {})
    dataset = method.get("dataset")
    epochs_used = _scale_epochs(method.get("epochs"), dataset)
    subset = _scale_data(dataset)
    rationale_parts = []
    if epochs_used is not None and epochs_used != method.get("epochs"):
        rationale_parts.append(f"halved epochs ({method['epochs']}->{epochs_used})")
    if subset is not None:
        rationale_parts.append(f"subsampled {dataset} to {subset}")
    plan["scaled_hparams"] = {
        "epochs_used": epochs_used,
        "data_subset_size": subset,
        "rationale": "; ".join(rationale_parts) or "no scaling needed",
    }
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Scale down hparams to CPU budget.")
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    plan_path = args.workspace / "repro_plan.json"
    if not plan_path.exists():
        print(f"scale_down.py: missing {plan_path}", file=sys.stderr)
        return 1
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan = scale(plan)
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
