# `paper-reproduction` Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the `paper-reproduction` skill under `skills/custom/paper-reproduction/` end-to-end (5 scripts + 2 templates + 4 unit tests + 1 E2E test + SKILL.md), so it can reproduce arxiv:1609.02907 (GCN/Cora) Table 2 row in < 5 minutes on CPU.

**Architecture:** Five sequential bash scripts that the lead agent invokes in order via SKILL.md. Each script reads upstream JSON, never re-parses the PDF (anti-hallucination property). Code acquisition uses 3-tier fallback (cache → github clone → template skeleton). Failure modes always produce a viewable `report.md`.

**Tech Stack:** Python 3.12, `requests` + `urllib` fallback, `pdfplumber` (PDF→text), `pytest` (unit tests), bash (E2E test). No external API keys, no LLM calls inside scripts.

---

## Critical Operational Rules

1. **NO automatic git commits.** Per user instruction, every "commit" step in this plan is a checkpoint marker for the executing agent — do **not** run `git add` / `git commit`. The user runs all commits manually at the end.
2. **Touch only `skills/custom/paper-reproduction/`.** Any file outside that directory is out of scope.
3. **Stop for user review at the 3 checkpoints** (CP-A, CP-B, CP-C below). Do not auto-continue past them.
4. **TDD discipline.** Every script in Phase 1 follows: write failing test → confirm it fails → minimal impl → confirm it passes.
5. **Reference design** at every task: `docs/plans/2026-05-06-paper-reproduction-design.md` is the contract; do not deviate without asking.

---

## Phase Map

| Phase | Tasks | Est. time | Output |
|---|---|---|---|
| **Phase 0** | Setup directories + fixture | 0.5h | empty package structure + `gcn_paper_text.txt` |
| **Phase 1** | 5 scripts via TDD | 4-5h | scripts/*.py + tests/test_*.py all green |
| **Phase 2** | 2 templates | 1.5h | templates/pytorch_skeleton.py + report.md.tmpl |
| **CP-A** | **Stop for user review of scripts + templates** | — | — |
| **Phase 3** | SKILL.md | 1.5h | SKILL.md ~400 lines |
| **CP-B** | **Stop for user review of SKILL.md** | — | — |
| **Phase 4** | E2E bash test script | 0.5h | tests/test_e2e_gcn.sh |
| **CP-C** | **Stop before final hand-off (user runs E2E + commits manually)** | — | — |

---

# Phase 0 — Setup

## Task 0.1: Create directory tree

**Files:**
- Create: `skills/custom/paper-reproduction/scripts/__init__.py` (empty)
- Create: `skills/custom/paper-reproduction/templates/.gitkeep` (empty)
- Create: `skills/custom/paper-reproduction/tests/__init__.py` (empty)
- Create: `skills/custom/paper-reproduction/tests/fixtures/.gitkeep` (empty)

**Step 1: Make all directories**

Run:
```bash
mkdir -p "skills/custom/paper-reproduction/scripts" \
         "skills/custom/paper-reproduction/templates" \
         "skills/custom/paper-reproduction/tests/fixtures"
```

**Step 2: Create empty package markers and gitkeeps**

Use Write tool to create the four files above as empty files.

**Step 3: Verify tree**

Run:
```bash
find skills/custom/paper-reproduction -type f -o -type d | sort
```

Expected output (4 dirs + 4 files):
```
skills/custom/paper-reproduction
skills/custom/paper-reproduction/scripts
skills/custom/paper-reproduction/scripts/__init__.py
skills/custom/paper-reproduction/templates
skills/custom/paper-reproduction/templates/.gitkeep
skills/custom/paper-reproduction/tests
skills/custom/paper-reproduction/tests/__init__.py
skills/custom/paper-reproduction/tests/fixtures
skills/custom/paper-reproduction/tests/fixtures/.gitkeep
```

## Task 0.2: Create test conftest.py

**Files:**
- Create: `skills/custom/paper-reproduction/tests/conftest.py`

**Step 1: Write conftest with shared fixtures**

```python
"""Shared pytest fixtures for paper-reproduction tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make scripts/ importable as a package for tests
SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

import pytest


@pytest.fixture
def gcn_paper_text() -> str:
    """Pre-extracted GCN paper text used by extract_method.py tests."""
    fixture_path = Path(__file__).parent / "fixtures" / "gcn_paper_text.txt"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """A clean per-test workspace directory with the right layout."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "code").mkdir()
    (ws / "logs").mkdir()
    (ws / "figures").mkdir()
    return ws


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@pytest.fixture
def write_json():
    return _write_json
```

**Step 2: Verify pytest can collect**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/ --collect-only 2>&1 | head -20
```

Expected: no errors (no tests yet, just confirms conftest loads).

## Task 0.3: Create GCN paper text fixture

**Files:**
- Create: `skills/custom/paper-reproduction/tests/fixtures/gcn_paper_text.txt`

**Background:** Unit tests for `extract_method.py` require deterministic input text. We pre-extract it once. The fixture must contain the relevant snippets for testing: epochs/lr/dropout values, the Table 2 results, and the github URL.

**Step 1: Write minimal fixture text**

Use Write tool to create `tests/fixtures/gcn_paper_text.txt` with the following content (this is a hand-curated subset of GCN paper text; covers all extractor patterns the unit tests need):

```
Semi-Supervised Classification with Graph Convolutional Networks

Thomas N. Kipf, Max Welling
University of Amsterdam

ABSTRACT
We present a scalable approach for semi-supervised learning on graph-structured
data that is based on an efficient variant of convolutional neural networks
which operate directly on graphs. Code to reproduce our experiments is
available at https://github.com/tkipf/gcn.

5 EXPERIMENTS
We train a two-layer GCN as described in Section 3.1 and evaluate prediction
accuracy on a test set of 1,000 labeled examples.

5.1 EXPERIMENTAL SET-UP
We trained our models for a maximum of 200 epochs (training iterations) using
Adam (Kingma & Ba, 2015) with a learning rate of 0.01 and early stopping with
a window size of 10. We initialize weights using the initialization described
in Glorot & Bengio (2010) and accordingly (row-)normalize input feature
vectors. For the citation network datasets, we use 16 hidden units and have
trained for a maximum of 200 epochs. We chose dropout rate of 0.5 and L2
regularization factor with weight decay of 5e-4.

Datasets used: Cora, Citeseer, Pubmed.

6 RESULTS
6.1 SEMI-SUPERVISED NODE CLASSIFICATION
Results are summarized in Table 2. Reported numbers denote classification
accuracy in percent.

Table 2: Summary of results in terms of classification accuracy (in percent).

Method               Cora    Citeseer   Pubmed
ManiReg              59.5    60.1       70.7
SemiEmb              59.0    59.6       71.7
LP                   68.0    45.3       63.0
DeepWalk             67.2    43.2       65.3
ICA                  75.1    69.1       73.9
Planetoid            75.7    64.7       77.2
GCN (this paper)     81.5    70.3       79.0
GCN (rand. splits)   80.1    67.9       78.9

7 DISCUSSION
Our experiments demonstrate that the proposed graph convolutional network
model is capable of efficiently encoding both graph structure and node
features in a way that is useful for semi-supervised classification.
```

**Step 2: Verify fixture loads in conftest**

Run:
```bash
cd skills/custom/paper-reproduction && python -c "
from pathlib import Path
text = Path('tests/fixtures/gcn_paper_text.txt').read_text(encoding='utf-8')
print(f'Fixture length: {len(text)} chars')
assert 'GCN (this paper)     81.5' in text, 'target value missing'
assert 'github.com/tkipf/gcn' in text, 'github URL missing'
assert '200 epochs' in text, 'epochs missing'
print('✓ All fixture markers present')
"
```

Expected output:
```
Fixture length: ~1500 chars
✓ All fixture markers present
```

---

# Phase 1 — Scripts via TDD

> Order chosen by ascending complexity. Each script: 1 fixture if needed → failing test → minimal impl → green test → next behavior.

## Task 1.1: `scale_down.py` — pure-logic helper

**Files:**
- Create: `skills/custom/paper-reproduction/scripts/scale_down.py`
- Create: `skills/custom/paper-reproduction/tests/test_scale_down.py`

**Step 1: Write the first failing test (epochs halving)**

Write to `tests/test_scale_down.py`:

```python
"""Unit tests for scale_down.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _run_scale_down(workspace: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "scale_down.py"), "--workspace", str(workspace)],
        capture_output=True, text=True, check=False,
    )


def test_scale_down_halves_epochs(tmp_workspace, write_json):
    plan = {
        "schema_version": "1.0",
        "arxiv_id": "1609.02907",
        "method": {"epochs": 200, "dataset": "Cora"},
    }
    write_json(tmp_workspace / "repro_plan.json", plan)

    result = _run_scale_down(tmp_workspace)

    assert result.returncode == 0, result.stderr
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["epochs_used"] == 100
    assert out["scaled_hparams"]["data_subset_size"] is None
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_scale_down.py::test_scale_down_halves_epochs -v
```

Expected: FAIL — `scripts/scale_down.py` does not exist.

**Step 3: Write minimal impl**

Write to `scripts/scale_down.py`:

```python
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


def _scale_epochs(original: int | None) -> int | None:
    if original is None:
        return None
    return max(MIN_EPOCHS, original // 2)


def _scale_data(dataset: str | None) -> int | None:
    if dataset is None or dataset in SMALL_DATASETS:
        return None
    return SUBSAMPLE_SIZE


def scale(plan: dict) -> dict:
    method = plan.get("method", {})
    epochs_used = _scale_epochs(method.get("epochs"))
    dataset = method.get("dataset")
    subset = _scale_data(dataset)
    rationale_parts = []
    if epochs_used is not None and epochs_used != method.get("epochs"):
        rationale_parts.append(f"halved epochs ({method['epochs']}→{epochs_used})")
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
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_scale_down.py::test_scale_down_halves_epochs -v
```

Expected: PASS.

**Step 5: Add remaining test cases**

Append to `tests/test_scale_down.py`:

```python
def test_scale_down_floors_at_min(tmp_workspace, write_json):
    plan = {"method": {"epochs": 10, "dataset": "Cora"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    assert result.returncode == 0
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["epochs_used"] == 10


def test_scale_down_subsamples_large_dataset(tmp_workspace, write_json):
    plan = {"method": {"epochs": 10, "dataset": "MNIST"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    assert result.returncode == 0
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["data_subset_size"] == 10000


def test_scale_down_keeps_small_dataset(tmp_workspace, write_json):
    plan = {"method": {"epochs": 200, "dataset": "Cora"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["data_subset_size"] is None


def test_scale_down_handles_null_epochs(tmp_workspace, write_json):
    plan = {"method": {"epochs": None, "dataset": "Cora"}}
    write_json(tmp_workspace / "repro_plan.json", plan)
    result = _run_scale_down(tmp_workspace)
    assert result.returncode == 0
    out = json.loads((tmp_workspace / "repro_plan.json").read_text())
    assert out["scaled_hparams"]["epochs_used"] is None


def test_scale_down_missing_workspace_file_errors(tmp_workspace):
    result = _run_scale_down(tmp_workspace)
    assert result.returncode != 0
    assert "missing" in result.stderr.lower()
```

**Step 6: Run all scale_down tests**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_scale_down.py -v
```

Expected: all 5 tests PASS.

**Step 7: Checkpoint marker (no commit)**

Mark task done in TodoWrite. Move to Task 1.2.

## Task 1.2: `comparator.py` — delta + tolerance + report.md rendering

**Files:**
- Create: `skills/custom/paper-reproduction/scripts/comparator.py`
- Create: `skills/custom/paper-reproduction/tests/test_comparator.py`
- Create: `skills/custom/paper-reproduction/templates/report.md.tmpl`

**Step 1: Write report template first (it's a contract input)**

Write to `templates/report.md.tmpl` (Python `.format()` placeholders):

```markdown
# Reproduction Report: {paper_title}

**arXiv:** {arxiv_id} | **Reproduced:** {date} | **Mode:** mini-scale
**Verdict:** {verdict_emoji} {verdict_text}

## Target
- Metric: {target_description}
- Paper reported: **{paper_value}{unit}**

## Reproduced
- Our result: **{our_value}{unit}**
- Δ: {delta_absolute_signed}{unit} ({delta_relative_signed})
- Tolerance: ±{tolerance_pct} ({tolerance_basis})
- Wall time: {wall_time_seconds}s on CPU

## Code Source
- Tier: {code_source}
- Repo: {code_repo_url}

## Scale-Down Applied
{scale_down_block}

## Figures
{figures_block}

## Method (extracted from paper)
{method_table}

## Warnings
{warnings_block}

## Errors
{errors_block}

## Conclusion
{conclusion_line}
```

**Step 2: Write failing test for tolerance + verdict logic**

Write to `tests/test_comparator.py`:

```python
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
    assert cmp["tolerance_used"] == 0.05  # cache + scale_down → 5%
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
    # paper expects 81.5%, our 95% (synthetic) — out of even ±8% but tests tolerance basis
    result = _run(tmp_workspace, output)
    cmp = json.loads((output / "comparison.json").read_text())
    assert cmp["tolerance_used"] == 0.08  # cache + subsample
```

**Step 3: Run all tests, confirm all fail**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_comparator.py -v
```

Expected: all 5 FAIL — `comparator.py` does not exist.

**Step 4: Implement comparator.py**

Write to `scripts/comparator.py`:

```python
#!/usr/bin/env python3
"""comparator.py — compare reproduced metric to paper value, render report.md."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, UTC
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
    return {"within_tolerance": "✅", "deviated": "⚠️", "execution_failed": "❌"}[v]


def _verdict_text(v: str) -> str:
    return {"within_tolerance": "Within tolerance",
            "deviated": "Deviated",
            "execution_failed": "Execution failed"}[v]


def _conclusion(cmp: dict, errors: list[str]) -> str:
    v = cmp["verdict"]
    if v == "within_tolerance":
        return f"✅ Reproduction successful within ±{cmp['tolerance_used']:.0%} tolerance."
    if v == "deviated":
        delta_pct = cmp["delta_relative"] * 100
        hint = "scale-down" if cmp.get("scale_down_applied") else "hparam mismatch or training instability"
        return f"⚠️ Reproduction deviated by {delta_pct:+.1f}%; possible cause: {hint}."
    first_err = errors[0] if errors else "unknown error"
    return f"❌ Execution failed: {first_err}. Manual intervention required."


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
        return "None applied — full hparams used."
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
        date=datetime.now(UTC).strftime("%Y-%m-%d"),
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
```

**Step 5: Run all comparator tests**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_comparator.py -v
```

Expected: all 5 PASS. If a test fails (e.g. tolerance rounding edge), inspect the assertion and adjust either expected value or impl, but do NOT loosen test semantics.

## Task 1.3: `extract_method.py` — regex hparam extractor + target verifier + github URL grep

**Files:**
- Create: `skills/custom/paper-reproduction/scripts/extract_method.py`
- Create: `skills/custom/paper-reproduction/tests/test_extract_method.py`

**Step 1: Write failing tests for the 5 behaviors**

Write to `tests/test_extract_method.py`:

```python
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
```

**Step 2: Run, confirm all fail**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_extract_method.py -v
```

Expected: all 6 FAIL (script missing).

**Step 3: Implement extract_method.py**

Write to `scripts/extract_method.py`:

```python
#!/usr/bin/env python3
"""extract_method.py — regex-based extraction of hparams + target verification + repo URL.

Reads workspace/paper.txt, requires --target string, writes repro_plan.json.

Exit codes:
  0 — success, all critical fields populated
  1 — usage error or missing files
  2 — target not found in paper text (verified_in_paper=false)
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
NUM_LAYERS_PATTERNS = [
    r"(\d+)-layer",
    r"two-layer",  # treated specially below
]

KNOWN_DATASETS = ["Cora", "Citeseer", "Pubmed", "MNIST", "FashionMNIST",
                  "CIFAR-10", "CIFAR-100", "ImageNet"]

KNOWN_MODELS = ["GCN", "GAT", "GraphSAGE", "Transformer", "BERT", "ResNet",
                "VGG", "U-Net", "CNN", "MLP", "LSTM", "GRU"]

GITHUB_URL_PATTERN = re.compile(r"https?://github\.com/[\w\-]+/[\w\-\.]+")


def _try_patterns(text: str, patterns: list[str], cast=float) -> Any:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return cast(m.group(1))
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
    """Parse the user-supplied target string for an expected value.

    Examples:
      "Table 2 GCN/Cora row, expected ~81.5%" -> (81.5, "percent")
      "expected 0.815"                         -> (0.815, "fraction")
    """
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
    candidates = [f"{value:.1f}", f"{value:.2f}", str(int(value)) if value.is_integer() else None]
    for cand in filter(None, candidates):
        idx = text.find(cand)
        if idx >= 0:
            start = max(0, idx - 60)
            end = min(len(text), idx + 60)
            snippet = text[start:end].replace("\n", " ")
            return True, idx, snippet
    return False, -1, ""


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
    for k in ["epochs", "learning_rate", "dataset", "model_arch_hint"]:
        if method[k] is None:
            warnings.append(f"could not extract {k} via regex; consider --method-override")

    # Target
    expected_value, expected_unit = _extract_target_value(args.target)
    if expected_value is None:
        # Target string didn't carry a numeric expectation
        warnings.append("could not parse expected numeric value from --target")
        verified, offset, snippet = False, -1, ""
    else:
        verified, offset, snippet = _verify_in_paper(text, expected_value)

    target = {
        "description": args.target,
        "metric_name": "test_accuracy",  # heuristic default; may refine in future
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
        "scaled_hparams": None,  # populated by scale_down.py
        "warnings": warnings,
    }

    plan_path = args.workspace / "repro_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    if not verified:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Run all extract_method tests**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_extract_method.py -v
```

Expected: 6 PASS. If any fails, inspect: regex pattern may not match the fixture wording; either adjust the regex (preferred) or update the fixture (last resort, only if fixture text was unrealistic).

## Task 1.4: `download_paper.py` — arxiv API + PDF→text

**Files:**
- Create: `skills/custom/paper-reproduction/scripts/download_paper.py`
- (No unit tests — relies on network; verified via E2E in Phase 4)

**Step 1: Implement using `arxiv_search.py` patterns**

Write to `scripts/download_paper.py`:

```python
#!/usr/bin/env python3
"""download_paper.py — fetch arxiv PDF and extract text.

Reuses the requests-or-urllib-fallback pattern from
skills/public/systematic-literature-review/scripts/arxiv_search.py.

Outputs:
  workspace/paper.pdf
  workspace/paper.txt   (PDF text, one block per page joined with \n\n)

PDF extraction order of preference:
  1. pdfplumber  (most accurate text extraction)
  2. pypdf       (pure-python fallback, lower fidelity)
  3. fail with clear error message
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_TIMEOUT = 60


# --- HTTP shim (same fallback pattern as arxiv_search.py) ---
try:
    import requests  # type: ignore
except ImportError:
    import urllib.error
    import urllib.request

    class _UrllibResponse:
        def __init__(self, data: bytes, status: int) -> None:
            self.content = data
            self.status_code = status

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    class _UrllibShim:
        @staticmethod
        def get(url, timeout=DEFAULT_TIMEOUT, **_):
            req = urllib.request.Request(url, headers={"User-Agent": "scideer-paper-repro/0.1"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return _UrllibResponse(resp.read(), resp.status)
            except urllib.error.HTTPError as e:
                return _UrllibResponse(e.read(), e.code)

    requests = _UrllibShim()  # type: ignore


def _arxiv_pdf_url(arxiv_id: str) -> str:
    # Strip version suffix if present (e.g. 1609.02907v4 → 1609.02907)
    base = arxiv_id.split("v")[0] if "v" in arxiv_id and arxiv_id.split("v")[-1].isdigit() else arxiv_id
    return f"https://arxiv.org/pdf/{base}.pdf"


def _download_pdf(url: str, dst: Path) -> int:
    print(f"download_paper: GET {url}", file=sys.stderr)
    resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    dst.write_bytes(resp.content)
    return len(resp.content)


def _extract_text_pdfplumber(pdf_path: Path) -> str | None:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return None
    blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if txt:
                blocks.append(txt)
    return "\n\n".join(blocks)


def _extract_text_pypdf(pdf_path: Path) -> str | None:
    try:
        import pypdf  # type: ignore
    except ImportError:
        try:
            import PyPDF2 as pypdf  # type: ignore
        except ImportError:
            return None
    blocks = []
    reader = pypdf.PdfReader(str(pdf_path))
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt:
            blocks.append(txt)
    return "\n\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download arxiv PDF + extract text.")
    parser.add_argument("arxiv_id", help="e.g. 1609.02907")
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()

    args.workspace.mkdir(parents=True, exist_ok=True)
    pdf_path = args.workspace / "paper.pdf"
    txt_path = args.workspace / "paper.txt"

    # Download
    try:
        size = _download_pdf(_arxiv_pdf_url(args.arxiv_id), pdf_path)
        print(f"download_paper: wrote {size} bytes to {pdf_path}", file=sys.stderr)
    except Exception as exc:
        print(f"download_paper: FAILED to download arxiv:{args.arxiv_id}: {exc}", file=sys.stderr)
        return 1

    # Extract text — try pdfplumber, fall back to pypdf
    text = _extract_text_pdfplumber(pdf_path) or _extract_text_pypdf(pdf_path)
    if text is None:
        print("download_paper: neither pdfplumber nor pypdf is installed", file=sys.stderr)
        return 1
    if len(text) < 1024:
        print(f"download_paper: extracted only {len(text)} chars; PDF may be image-based", file=sys.stderr)
        # Still write what we got, downstream will mark F2 failure
    txt_path.write_text(text, encoding="utf-8")
    print(f"download_paper: wrote {len(text)} chars to {txt_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Verify --help works**

Run:
```bash
cd skills/custom/paper-reproduction && python scripts/download_paper.py --help
```

Expected: argparse help text shown, exit 0.

**Step 3: Note for E2E gate**

This script is exercised end-to-end in Phase 4 (`tests/test_e2e_gcn.sh`). No unit test in this phase.

## Task 1.5: `run_experiment.py` — 3-tier code acquire + sandbox subprocess + metrics extraction

**Files:**
- Create: `skills/custom/paper-reproduction/scripts/run_experiment.py`
- Create: `skills/custom/paper-reproduction/tests/test_run_experiment.py`
- Create: `skills/custom/paper-reproduction/tests/fixtures/fake_cache/pygcn/train.py` (minimal stub for cache mock)

**Step 1: Create fake cache fixture**

Write to `tests/fixtures/fake_cache/pygcn/train.py`:

```python
"""Minimal fake pygcn train script for unit tests.

Reads scaled epochs via env var SCIDEER_EPOCHS, prints sentinel metrics.
"""
import os
import sys
import time

epochs = int(os.environ.get("SCIDEER_EPOCHS", "100"))
for ep in range(1, epochs + 1):
    loss = 1.94 * (0.95 ** ep)
    acc = 0.30 + (0.50 * (1 - 0.95 ** ep))
    print(f"SKELETON_EPOCH {ep} train_loss={loss:.4f} val_acc={acc:.4f}", flush=True)
    time.sleep(0.001)

final_acc = 0.8023
print(f"SKELETON_METRIC test_accuracy={final_acc}", flush=True)
print(f"SKELETON_METRIC train_loss_final=0.234", flush=True)
print(f"SKELETON_METRIC epochs_actually_run={epochs}", flush=True)
```

Also write `tests/fixtures/fake_cache/pygcn/__init__.py` (empty).

**Step 2: Write failing tests**

Write to `tests/test_run_experiment.py`:

```python
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
    """No cache + no repo URL → falls through to Tier 3 template skeleton."""
    cache_root = tmp_path / "empty_cache"
    cache_root.mkdir()
    _make_plan(tmp_workspace, code_repo_url=None)
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=120)
    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    # Tier 3 may succeed (Cora skeleton) or fail (deps missing); either way code_source=template
    assert metrics["code_source"] == "template"


def test_timeout_kills_subprocess(tmp_workspace, tmp_path):
    """A skeleton with epochs=99999 should be killed by --timeout."""
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    # Use a stub that sleeps forever
    (cache_root / "pygcn").mkdir()
    (cache_root / "pygcn" / "train.py").write_text(
        "import time\nwhile True: time.sleep(1)\n", encoding="utf-8"
    )
    _make_plan(tmp_workspace)
    result = _run(tmp_workspace, cache_dir=cache_root, timeout=2)
    metrics = json.loads((tmp_workspace / "metrics.json").read_text())
    assert metrics["exit_code"] != 0
    assert any("timeout" in e.lower() for e in metrics["errors"])
```

**Step 3: Run, confirm fail**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_run_experiment.py -v
```

Expected: 3 FAIL.

**Step 4: Implement run_experiment.py**

Write to `scripts/run_experiment.py`:

```python
#!/usr/bin/env python3
"""run_experiment.py — 3-tier code acquisition + sandboxed subprocess execution.

Tiers:
  1. Cache: $SCIDEER_CACHE_DIR/<repo_name>/   (or /mnt/scideer-cache/<repo_name>/)
  2. github_clone: git clone --depth 1 --timeout 60 <code_repo_url>
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
EPOCH_RE = re.compile(r"SKELETON_EPOCH\s+(\d+)\s+train_loss=([\d.eE\+\-]+)\s+val_acc=([\d.eE\+\-]+)")


def _repo_name_from_url(url: str | None) -> str | None:
    if not url:
        return None
    name = url.rstrip("/").split("/")[-1]
    return name.removesuffix(".git")


def _try_cache(cache_root: Path, repo_url: str | None) -> Path | None:
    repo_name = _repo_name_from_url(repo_url)
    if not repo_name:
        # Try a few common names: pygcn, gcn
        for candidate in ["pygcn", "gcn"]:
            cand_dir = cache_root / candidate
            if cand_dir.exists():
                return cand_dir
        return None
    cand_dir = cache_root / repo_name
    return cand_dir if cand_dir.exists() else None


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
    # Preferred names in order
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
    """Run with timeout. Returns (exit_code, stdout_text, errors)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    errors = []
    stdout_chunks = []
    proc = subprocess.Popen(
        [sys.executable, entrypoint.name],
        cwd=str(entrypoint.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    start = time.time()
    log_f = log_path.open("w", encoding="utf-8")
    try:
        while True:
            if proc.stdout is None:
                break
            line = proc.stdout.readline()
            if line:
                log_f.write(line)
                log_f.flush()
                stdout_chunks.append(line)
            if proc.poll() is not None:
                break
            if time.time() - start > timeout:
                errors.append(f"timeout: killed after {timeout}s")
                if os.name == "posix":
                    proc.send_signal(signal.SIGKILL)
                else:
                    proc.kill()
                proc.wait(timeout=5)
                break
    finally:
        log_f.close()
    return proc.returncode if proc.returncode is not None else -1, "".join(stdout_chunks), errors


def _parse_metrics(stdout: str) -> tuple[dict, list[dict]]:
    final = {}
    curve = []
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
    errors = []
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

    cached = _try_cache(DEFAULT_CACHE_DIR, repo_url)
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
            return 0  # comparator will mark execution_failed

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

    return 0  # always 0 — comparator decides verdict


if __name__ == "__main__":
    sys.exit(main())
```

**Step 5: Run all run_experiment tests**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/test_run_experiment.py -v
```

Expected: 3 PASS.

**Step 6: Run full test suite**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/ -v
```

Expected: 5 + 5 + 6 + 3 = 19 PASS.

---

# Phase 2 — Templates

## Task 2.1: `pytorch_skeleton.py` — GCN + CNN dual-task with graceful exit

**Files:**
- Create: `skills/custom/paper-reproduction/templates/pytorch_skeleton.py`

**Step 1: Implement skeleton**

Write to `templates/pytorch_skeleton.py`:

```python
#!/usr/bin/env python3
"""pytorch_skeleton.py — Tier 3 fallback when neither cache nor github clone provide code.

Routes by SCIDEER_DATASET env var:
  Cora/Citeseer/Pubmed → run_gcn()        (requires torch_geometric)
  MNIST/FashionMNIST   → run_cnn()        (requires torchvision)
  other                → graceful exit with sentinel error metric

Reads:
  SCIDEER_EPOCHS, SCIDEER_LR, SCIDEER_HIDDEN, SCIDEER_DROPOUT, SCIDEER_DATASET, SCIDEER_SUBSET

Emits sentinel lines parsed by run_experiment.py:
  SKELETON_EPOCH <n> train_loss=<v> val_acc=<v>
  SKELETON_METRIC test_accuracy=<v>
  SKELETON_METRIC train_loss_final=<v>
  SKELETON_METRIC epochs_actually_run=<v>
"""
from __future__ import annotations

import os
import sys
import time

EPOCHS = int(os.environ.get("SCIDEER_EPOCHS", "100"))
LR = float(os.environ.get("SCIDEER_LR", "0.01"))
HIDDEN = int(os.environ.get("SCIDEER_HIDDEN", "16"))
DROPOUT = float(os.environ.get("SCIDEER_DROPOUT", "0.5"))
DATASET = os.environ.get("SCIDEER_DATASET", "Cora")
SUBSET = int(os.environ.get("SCIDEER_SUBSET", "0")) or None


def emit_metric(key: str, value) -> None:
    print(f"SKELETON_METRIC {key}={value}", flush=True)


def emit_epoch(epoch: int, train_loss: float, val_acc: float) -> None:
    print(f"SKELETON_EPOCH {epoch} train_loss={train_loss:.4f} val_acc={val_acc:.4f}", flush=True)


def run_gcn() -> int:
    try:
        import torch
        import torch.nn.functional as F
        from torch_geometric.datasets import Planetoid
        from torch_geometric.nn import GCNConv
    except ImportError as e:
        print(f"SKELETON_ERROR dep_missing: {e}", file=sys.stderr, flush=True)
        return 1

    dataset = Planetoid(root=os.path.expanduser("~/.scideer/cache/torch_geometric"),
                        name=DATASET)
    data = dataset[0]
    num_features = dataset.num_features
    num_classes = dataset.num_classes

    class GCN(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = GCNConv(num_features, HIDDEN)
            self.conv2 = GCNConv(HIDDEN, num_classes)

        def forward(self, data):
            x, edge_index = data.x, data.edge_index
            x = F.relu(self.conv1(x, edge_index))
            x = F.dropout(x, p=DROPOUT, training=self.training)
            x = self.conv2(x, edge_index)
            return F.log_softmax(x, dim=1)

    model = GCN()
    optim = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=5e-4)
    final_loss = 0.0
    final_acc = 0.0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        optim.zero_grad()
        out = model(data)
        loss = F.nll_loss(out[data.train_mask], data.y[data.train_mask])
        loss.backward()
        optim.step()

        model.eval()
        with torch.no_grad():
            out = model(data)
            pred = out.argmax(dim=1)
            val_acc = (pred[data.val_mask] == data.y[data.val_mask]).float().mean().item()
            test_acc = (pred[data.test_mask] == data.y[data.test_mask]).float().mean().item()
        emit_epoch(epoch, loss.item(), val_acc)
        final_loss = loss.item()
        final_acc = test_acc

    emit_metric("test_accuracy", final_acc)
    emit_metric("train_loss_final", final_loss)
    emit_metric("epochs_actually_run", EPOCHS)
    return 0


def run_cnn() -> int:
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torch.utils.data import DataLoader, Subset
        from torchvision import datasets, transforms
    except ImportError as e:
        print(f"SKELETON_ERROR dep_missing: {e}", file=sys.stderr, flush=True)
        return 1

    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])
    cache_dir = os.path.expanduser("~/.scideer/cache/torchvision")
    os.makedirs(cache_dir, exist_ok=True)
    train_set = datasets.MNIST(cache_dir, train=True, download=True, transform=transform)
    test_set = datasets.MNIST(cache_dir, train=False, download=True, transform=transform)
    if SUBSET:
        train_set = Subset(train_set, list(range(min(SUBSET, len(train_set)))))
    train_loader = DataLoader(train_set, batch_size=128, shuffle=True)
    test_loader = DataLoader(test_set, batch_size=512)

    class SimpleCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(1, 32, 3, padding=1)
            self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
            self.fc1 = nn.Linear(64 * 7 * 7, 128)
            self.fc2 = nn.Linear(128, 10)

        def forward(self, x):
            x = F.relu(self.conv1(x)); x = F.max_pool2d(x, 2)
            x = F.relu(self.conv2(x)); x = F.max_pool2d(x, 2)
            x = x.view(x.size(0), -1)
            x = F.relu(self.fc1(x)); x = F.dropout(x, p=DROPOUT, training=self.training)
            return self.fc2(x)

    model = SimpleCNN()
    optim = torch.optim.Adam(model.parameters(), lr=LR)
    final_loss = 0.0
    final_acc = 0.0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        running = 0.0
        for x, y in train_loader:
            optim.zero_grad()
            out = model(x)
            loss = F.cross_entropy(out, y)
            loss.backward()
            optim.step()
            running += loss.item()
        final_loss = running / max(len(train_loader), 1)

        model.eval()
        correct = 0; total = 0
        with torch.no_grad():
            for x, y in test_loader:
                pred = model(x).argmax(dim=1)
                correct += (pred == y).sum().item()
                total += y.size(0)
        final_acc = correct / total if total else 0.0
        emit_epoch(epoch, final_loss, final_acc)

    emit_metric("test_accuracy", final_acc)
    emit_metric("train_loss_final", final_loss)
    emit_metric("epochs_actually_run", EPOCHS)
    return 0


def main() -> int:
    if DATASET in {"Cora", "Citeseer", "Pubmed"}:
        return run_gcn()
    if DATASET in {"MNIST", "FashionMNIST"}:
        return run_cnn()
    # Graceful exit for unsupported datasets
    print(f"SKELETON_ERROR unsupported_dataset: '{DATASET}' not in {{Cora,Citeseer,Pubmed,MNIST,FashionMNIST}}",
          file=sys.stderr, flush=True)
    emit_metric("test_accuracy", "null")  # comparator will treat as execution_failed
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Quick syntax check**

Run:
```bash
cd skills/custom/paper-reproduction && python -c "import py_compile; py_compile.compile('templates/pytorch_skeleton.py', doraise=True); print('✓ syntax OK')"
```

Expected: `✓ syntax OK`.

**Step 3: Confirm template's smoke entry**

Run (this will fail because deps not installed in host env, but should fail gracefully):
```bash
cd skills/custom/paper-reproduction && SCIDEER_DATASET=UnknownDataset python templates/pytorch_skeleton.py
```

Expected: stderr contains `SKELETON_ERROR unsupported_dataset`, exit code 2.

## Task 2.2: Verify report.md.tmpl renders

**Note:** Already created in Task 1.2 alongside `comparator.py`. The comparator unit tests cover its rendering. Just confirm it exists:

Run:
```bash
cd skills/custom/paper-reproduction && wc -l templates/report.md.tmpl
```

Expected: ~40 lines.

---

# Checkpoint A — Stop for User Review

> **DO NOT proceed past this point without user approval.**

State to user:
> "Phase 1 + 2 complete. Scripts (5 .py + 1 conftest), templates (1 skeleton + 1 report tmpl), and unit tests (4 test files + 1 fixture) are in place. All 19 unit tests pass. Please review the code in `skills/custom/paper-reproduction/scripts/` and `templates/` before I write SKILL.md."

---

# Phase 3 — SKILL.md

## Task 3.1: Write SKILL.md (single task; ~400 lines)

**Files:**
- Create: `skills/custom/paper-reproduction/SKILL.md`

**Step 1: Draft SKILL.md**

Use the structure below. Hard-wire bash invocations exactly as specified in design Section 5.1.

The SKILL.md must contain these sections in order:
1. Frontmatter (per design 4.1, copied verbatim)
2. # Paper Reproduction Skill — overview + when to use
3. ## When NOT to Use This Skill
4. ## Workflow (the 6 hardcoded bash steps + critical rules)
5. ### Phase 1: Plan (conversational, ask user for arxiv_id + target if missing)
6. ### Phase 2: Download
7. ### Phase 3: Extract Method
8. ### Phase 4: Scale Down
9. ### Phase 5: Run Experiment
10. ### Phase 6: Compare and Report
11. ## Output Structure
12. ## Failure Modes (the 9-class matrix from design Section 6)
13. ## Examples (3 worked examples — GCN happy path, target-not-in-paper, OOM)
14. ## Notes (sandbox prerequisites, cache location, why we don't use web_fetch)

Write SKILL.md content following this rigid template. Use absolute paths `/mnt/skills/custom/paper-reproduction/scripts/...` for the bash commands so the lead agent can copy-paste them. Reference the design doc once at top: "See `docs/plans/2026-05-06-paper-reproduction-design.md` for design rationale."

**Important content rules:**
- Each Phase section starts with a code block containing the EXACT bash command — no variations, no inline edits.
- Each Phase section ends with: "If this step fails, stop and write a partial report.md describing the failure. Do NOT improvise or substitute behaviour."
- Workflow header includes a stern note: "Do NOT skip steps. Do NOT extract method/run experiment in your own context using your knowledge of the paper. Each script enforces a contract that prevents hallucination."
- Description frontmatter MUST be exactly the parent-design 4.1 text.

(Full SKILL.md text body is too long to inline here — use the structure above and the design doc Sections 4-7 as the source of truth. Aim for ~400 lines.)

**Step 2: Verify length and frontmatter**

Run:
```bash
cd skills/custom/paper-reproduction && wc -l SKILL.md && head -10 SKILL.md
```

Expected: 350-450 lines, frontmatter starts with `---` then `name: paper-reproduction`.

**Step 3: Verify description char count**

Run:
```bash
cd skills/custom/paper-reproduction && python -c "
import re
text = open('SKILL.md', encoding='utf-8').read()
desc = re.search(r'description:\s*(.*?)(?=\n[a-z]+:|---)', text, re.DOTALL)
if desc:
    d = ' '.join(desc.group(1).split())
    print(f'description length: {len(d)} chars')
    assert len(d) <= 500, 'description exceeds 500 char budget'
    print('✓ description OK')
"
```

Expected: ≤ 500 chars, prints `✓ description OK`.

---

# Checkpoint B — Stop for User Review

> **DO NOT proceed past this point without user approval.**

State to user:
> "SKILL.md is written. Please review `skills/custom/paper-reproduction/SKILL.md` (especially the workflow phases — they must use bash invocations exactly as designed). After your approval I'll write the E2E test bash script."

---

# Phase 4 — End-to-End Test

## Task 4.1: Create e2e bash script

**Files:**
- Create: `skills/custom/paper-reproduction/tests/test_e2e_gcn.sh`

**Step 1: Write the script**

Write to `tests/test_e2e_gcn.sh`:

```bash
#!/usr/bin/env bash
# End-to-end test for GCN reproduction.
#
# Prerequisites (set up by ops/demo track, not this script):
#   ~/.scideer/cache/pygcn/                — official pygcn repo cloned
#   ~/.scideer/cache/torch_geometric/Cora/ — Planetoid Cora downloaded
#   pdfplumber installed
#   torch + torch_geometric installed
#
# This script does NOT mount paths; it just runs the 5 scripts as if the agent
# would, and verifies the contract.

set -euo pipefail

ARXIV_ID="${1:-1609.02907}"
TARGET="${2:-Table 2 GCN/Cora row, expected ~81.5%}"

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WS="/tmp/test-pr-$ARXIV_ID-$$"
OUT="/tmp/test-pr-out-$ARXIV_ID-$$"

trap "rm -rf $WS $OUT" EXIT

rm -rf "$WS" "$OUT"
mkdir -p "$WS" "$OUT"

echo "=== Step 1: download_paper.py ==="
python "$SKILL_DIR/scripts/download_paper.py" "$ARXIV_ID" --workspace "$WS"

echo "=== Step 2: extract_method.py ==="
python "$SKILL_DIR/scripts/extract_method.py" \
    --workspace "$WS" --target "$TARGET" --arxiv-id "$ARXIV_ID"

echo "=== Step 3: scale_down.py ==="
python "$SKILL_DIR/scripts/scale_down.py" --workspace "$WS"

echo "=== Step 4: run_experiment.py ==="
SCIDEER_CACHE_DIR="$HOME/.scideer/cache" \
    python "$SKILL_DIR/scripts/run_experiment.py" --workspace "$WS" --timeout 240

echo "=== Step 5: comparator.py ==="
python "$SKILL_DIR/scripts/comparator.py" --workspace "$WS" --output "$OUT"

echo "=== Verifying contract ==="
test -f "$OUT/report.md" || { echo "FAIL: report.md missing"; exit 1; }
test -f "$OUT/comparison.json" || { echo "FAIL: comparison.json missing"; exit 1; }

VERDICT="$(python -c "import json; print(json.load(open('$OUT/comparison.json'))['verdict'])")"
OUR_VAL="$(python -c "import json; print(json.load(open('$OUT/comparison.json'))['our_value'])")"

echo "verdict: $VERDICT"
echo "our_value: $OUR_VAL"

if [ "$VERDICT" = "within_tolerance" ]; then
    echo "✓ E2E test PASSED"
else
    echo "✗ E2E test FAILED (verdict=$VERDICT, value=$OUR_VAL)"
    head -50 "$OUT/report.md"
    exit 1
fi
```

**Step 2: Make executable**

Run:
```bash
cd skills/custom/paper-reproduction && chmod +x tests/test_e2e_gcn.sh
```

**Step 3: Smoke-validate the script syntax**

Run:
```bash
cd skills/custom/paper-reproduction && bash -n tests/test_e2e_gcn.sh && echo "✓ syntax OK"
```

Expected: `✓ syntax OK`.

**Note:** Actual execution requires the ops cache + GPU/torch installed; that runs on the user's server, not here.

## Task 4.2: Final repo state self-check

**Step 1: Confirm we touched only the skill directory**

Run:
```bash
cd skills/custom/paper-reproduction && find . -type f -not -path '*/__pycache__/*' | sort
```

Expected output (16 files):
```
./SKILL.md
./scripts/__init__.py
./scripts/comparator.py
./scripts/download_paper.py
./scripts/extract_method.py
./scripts/run_experiment.py
./scripts/scale_down.py
./templates/pytorch_skeleton.py
./templates/report.md.tmpl
./tests/__init__.py
./tests/conftest.py
./tests/fixtures/fake_cache/pygcn/__init__.py
./tests/fixtures/fake_cache/pygcn/train.py
./tests/fixtures/gcn_paper_text.txt
./tests/test_comparator.py
./tests/test_e2e_gcn.sh
./tests/test_extract_method.py
./tests/test_run_experiment.py
./tests/test_scale_down.py
```

(Exact count is 19 files including `__init__.py`s and `.gitkeep` placeholders if any remain — drop `.gitkeep` from `templates/` once `pytorch_skeleton.py` exists.)

**Step 2: Confirm pytest still passes**

Run:
```bash
cd skills/custom/paper-reproduction && python -m pytest tests/ -v
```

Expected: 19 tests PASS.

**Step 3: Confirm `git status` shows changes only under the skill dir**

Run from repo root:
```bash
cd ../../.. && git status -s | head -50
```

Expected: every changed file path begins with `skills/custom/paper-reproduction/` or is a doc under `docs/plans/`. No untracked files elsewhere.

---

# Checkpoint C — Final Hand-Off

> **DO NOT auto-commit. Per user instruction, all git operations are manual.**

State to user:
> "Implementation complete. 16 source files + 4 unit test files + 1 e2e bash script + 1 fixture. All 19 unit tests pass on host. The e2e test (`tests/test_e2e_gcn.sh`) requires the server-side cache (`~/.scideer/cache/pygcn/` + Cora dataset) and torch + torch_geometric installed; please run it on the server after `git pull`. When you're ready to commit, you decide the message and `git add` set — I won't auto-commit per your instruction."

Provide a short summary:
- 5 scripts: download → extract → scale_down → run → comparator
- 2 templates: pytorch_skeleton (GCN+CNN) + report.md.tmpl
- 4 unit test files, 19 tests passing
- 1 E2E bash script, gated on server cache
- SKILL.md ~400 lines hard-wiring the 6-step bash workflow
- Tolerance auto-widening: cache-no-scale ±3%, cache-scaled ±5%, cache-subsampled ±8%, github_clone +2pp, template ±15%

Then list the F1–F9 failure-mode trigger commands for the user to run on the server (manual AC4 verification):
- F1: `python scripts/download_paper.py 9999.99999 --workspace /tmp/ws-f1`
- F3: pass `--target "Fake Table 99, expected ~99.9%"` for any real paper
- F8: pass `--timeout 1` to run_experiment.py with a long-running cache
- ...

---

# Done

Plan total tasks: 9 (Task 0.1 → 4.2). Estimated total time: 7-9 hours of focused work for an unfamiliar engineer; less for someone who already wrote the design.

**Plan complete and saved to `docs/plans/2026-05-06-paper-reproduction-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration on the same machine.

**2. Parallel Session (separate)** — Open a new session in this directory using `superpowers:executing-plans`, batch execute with the 3 checkpoints (CP-A / CP-B / CP-C) as natural review points.

**Which approach?**
