#!/usr/bin/env python3
"""extract_method.py -- regex-based extraction of hparams + target verification + repo URL.

Reads workspace/paper.txt, requires --target string, writes repro_plan.json.

Exit codes:
  0 -- success, all critical fields populated
  1 -- usage error or missing files
  2 -- target not found in paper text (verified_in_paper=false)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# --- Regex patterns ---
EPOCHS_PATTERNS = [
    r"trained for a maximum of (\d+) epochs",
    r"trained for (\d+) epochs",
    r"training for (\d+) epochs",
    r"(\d+)\s+epochs",
    r"epochs\s*[=:]\s*(\d+)",
]
LR_PATTERNS = [
    r"learning rate of ([\d.eE\-]+)",
    r"learning rate\s*[=:]\s*([\d.eE\-]+)",
    r"\blr\s*[=:]\s*([\d.eE\-]+)",
]
DROPOUT_PATTERNS = [
    r"dropout(?: rate)?(?: of)?\s*[=:]?\s*(0?\.\d+)",
]
WEIGHT_DECAY_PATTERNS = [
    r"weight decay(?: of)?\s*[=:]?\s*([\d.eE\-]+)",
    r"L2 regularization.*?([\d.eE\-]+)",
]
HIDDEN_DIM_PATTERNS = [
    r"(\d+)\s+hidden units",
    r"hidden(?:_dim| dim)?\s*[=:]\s*(\d+)",
]
BATCH_SIZE_PATTERNS = [
    r"batch size of (\d+)",
    r"batch_size\s*[=:]\s*(\d+)",
]

KNOWN_DATASETS = ["Cora", "Citeseer", "Pubmed", "MNIST", "FashionMNIST",
                  "CIFAR-10", "CIFAR-100", "ImageNet"]

KNOWN_MODELS = ["GCN", "GAT", "GraphSAGE", "Transformer", "BERT", "ResNet",
                "VGG", "U-Net", "CNN", "MLP", "LSTM", "GRU"]

# Reference-implementation defaults for well-known architectures. Used to fill
# in fields the paper's body text omits or phrases in ways our regex can't
# catch. Pulled from each model's canonical open-source reference repo, not
# guessed: GCN -> tkipf/pygcn; GAT -> PetarV-/GAT. New entries should also
# cite their authoritative source.
KNOWN_ARCH_DEFAULTS: dict[str, dict] = {
    "GCN": {
        "epochs": 200, "learning_rate": 0.01, "hidden_dim": 16,
        "dropout": 0.5, "weight_decay": 5e-4, "num_layers": 2,
    },
    "GAT": {
        "epochs": 1000, "learning_rate": 0.005, "hidden_dim": 8,
        "dropout": 0.6, "weight_decay": 5e-4, "num_layers": 2,
    },
}

GITHUB_URL_PATTERN = re.compile(r"https?://github\.com/[\w\-]+/[\w\-\.]+")


def _try_patterns(text: str, patterns: list[str], cast=float) -> Any:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            # Strip trailing punctuation (period from end-of-sentence) before casting.
            raw = m.group(1).rstrip(".,;:")
            try:
                return cast(raw)
            except (ValueError, IndexError):
                continue
    return None


def _extract_num_layers(text: str) -> int | None:
    if re.search(r"two-layer", text, re.IGNORECASE):
        return 2
    if re.search(r"three-layer", text, re.IGNORECASE):
        return 3
    m = re.search(r"(\d+)-layer", text)
    if m:
        return int(m.group(1))
    return None


def _extract_dataset(text: str, target: str) -> str | None:
    # Prefer dataset name explicitly mentioned in user's target
    for ds in KNOWN_DATASETS:
        if ds.lower() in target.lower():
            return ds
    # Else first dataset name found in paper text
    for ds in KNOWN_DATASETS:
        if re.search(rf"\b{re.escape(ds)}\b", text):
            return ds
    return None


def _extract_model(text: str, target: str) -> str | None:
    for m in KNOWN_MODELS:
        if re.search(rf"\b{re.escape(m)}\b", target):
            return m
    for m in KNOWN_MODELS:
        if re.search(rf"\b{re.escape(m)}\b", text):
            return m
    return None


def _extract_target_value(target: str) -> tuple[float | None, str]:
    """Parse the user-supplied target string for an expected value."""
    m = re.search(r"~?\s*(\d+\.?\d*)\s*%", target)
    if m:
        return float(m.group(1)), "percent"
    m = re.search(r"expected\s*~?\s*(\d+\.?\d*)", target, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        return val, ("percent" if val > 1.0 else "fraction")
    return None, "percent"


def _verify_in_paper(text: str, value: float) -> tuple[bool, int, str]:
    """Find the value in the paper text. Returns (verified, offset, snippet)."""
    candidates = [f"{value:.1f}", f"{value:.2f}",
                  str(int(value)) if value.is_integer() else None]
    for cand in filter(None, candidates):
        idx = text.find(cand)
        if idx >= 0:
            start = max(0, idx - 60)
            end = min(len(text), idx + 60)
            snippet = text[start:end].replace("\n", " ")
            return True, idx, snippet
    return False, -1, ""


def _apply_arch_defaults(method: dict, warnings: list[str]) -> None:
    """Fill None hparams from KNOWN_ARCH_DEFAULTS when the architecture matches.

    Modifies `method` in place. Appends a warning per filled field so the
    final report makes clear which numbers came from regex vs reference
    defaults (preserves the skill's "no silent fabrication" property).
    """
    arch = method.get("model_arch_hint")
    defaults = KNOWN_ARCH_DEFAULTS.get(arch) if arch else None
    if not defaults:
        return
    for key, default_value in defaults.items():
        if method.get(key) is None:
            method[key] = default_value
            warnings.append(
                f"{key}: regex miss, used {arch} reference default ({default_value})"
            )


def _grep_github_url(text: str) -> str | None:
    m = GITHUB_URL_PATTERN.search(text)
    if m:
        url = m.group(0)
        # Strip trailing punctuation
        url = url.rstrip(".,;)")
        return url
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract hparams + target from paper.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--target", required=True, type=str)
    parser.add_argument("--arxiv-id", default="", type=str)
    parser.add_argument("--paper-title", default="", type=str)
    args = parser.parse_args()

    paper_txt = args.workspace / "paper.txt"
    if not paper_txt.exists():
        print(f"extract_method.py: missing {paper_txt}", file=sys.stderr)
        return 1

    text = paper_txt.read_text(encoding="utf-8", errors="replace")

    # Hparams
    method = {
        "model_arch_hint": _extract_model(text, args.target),
        "dataset": _extract_dataset(text, args.target),
        "epochs": _try_patterns(text, EPOCHS_PATTERNS, cast=int),
        "learning_rate": _try_patterns(text, LR_PATTERNS, cast=float),
        "batch_size": _try_patterns(text, BATCH_SIZE_PATTERNS, cast=int),
        "weight_decay": _try_patterns(text, WEIGHT_DECAY_PATTERNS, cast=float),
        "hidden_dim": _try_patterns(text, HIDDEN_DIM_PATTERNS, cast=int),
        "dropout": _try_patterns(text, DROPOUT_PATTERNS, cast=float),
        "num_layers": _extract_num_layers(text),
        "extracted_via": "regex",
    }

    warnings = []
    # Fill regex misses from known-architecture reference defaults BEFORE
    # surfacing "could not extract" warnings. _apply_arch_defaults appends
    # its own "used <arch> reference default" warnings only for fields it
    # actually filled, so the remaining loop only complains about fields
    # that neither regex nor defaults could supply.
    _apply_arch_defaults(method, warnings)
    for k in ["epochs", "learning_rate", "dataset", "model_arch_hint"]:
        if method[k] is None:
            warnings.append(f"could not extract {k} via regex; consider --method-override")

    # Target
    expected_value, expected_unit = _extract_target_value(args.target)
    if expected_value is None:
        warnings.append("could not parse expected numeric value from --target")
        verified, offset, snippet = False, -1, ""
    else:
        verified, offset, snippet = _verify_in_paper(text, expected_value)

    target = {
        "description": args.target,
        "metric_name": "test_accuracy",
        "expected_value": expected_value,
        "expected_unit": expected_unit,
        "verified_in_paper": verified,
        "found_at_offset": offset,
        "context_snippet": snippet,
    }

    code_repo_url = _grep_github_url(text)

    plan = {
        "schema_version": "1.0",
        "arxiv_id": args.arxiv_id,
        "paper_title": args.paper_title,
        "target": target,
        "method": method,
        "code_repo_url": code_repo_url,
        "code_repo_url_source": "pdf_grep" if code_repo_url else None,
        "scaled_hparams": None,
        "warnings": warnings,
    }

    plan_path = args.workspace / "repro_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    if not verified:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
