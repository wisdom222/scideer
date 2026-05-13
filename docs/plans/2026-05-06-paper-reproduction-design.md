# `paper-reproduction` Skill — Design Document

> SciDeer Track: paper-reproduction skill
> Date: 2026-05-06
> Author: Jasper (with Claude Code)
> Parent design: [docs/plans/2026-05-03-scideer-design.md](2026-05-03-scideer-design.md) Section 4
> Status: Approved through brainstorming on 2026-05-06; ready for writing-plans

---

## 0. Why This Document Exists

The parent SciDeer design (2026-05-03) gives a high-level treatment of `paper-reproduction` in Section 4. This document is the **track-level** design that closes Section 4's open variables and sets the contract for an isolated implementation that does NOT touch other tracks (frontend / sci-pi / benchmarks / docker).

**This document supersedes** the older Task 6 description in `docs/plans/2026-05-03-scideer-implementation.md` — the latter was the initial Day-3-to-Day-5 sketch and is now stale.

---

## 1. Scope and Boundaries

### 1.1 In scope (this track delivers)

```
skills/custom/paper-reproduction/      ← single new directory, all work here
├── SKILL.md                           ~400 lines
├── scripts/                           5 scripts, ~700 LOC
├── templates/                         2 templates, ~220 LOC
└── tests/                             4 unit files + 1 e2e + 1 fixture
```

Total: 16 files, ~1170 LOC + 400 line SKILL.md.

### 1.2 Out of scope (other tracks own these)

- `frontend/`, `agents/sci-pi/`, `benchmarks/`, `docker/scideer-sandbox/`
- `config.yaml`, `extensions_config.json` (skill is filesystem-discovered, no registration needed)
- `skills/public/` (reused, never modified)
- Any pre-cache provisioning on the server (`~/.scideer/cache/pygcn/` etc.) — owned by ops/demo track

### 1.3 Demo-critical paper

**arxiv:1609.02907 (Kipf & Welling 2017, GCN on Cora).** The skill must reproduce Table 2's GCN/Cora row (~81.5%) end-to-end via cache-tier code acquisition. Backup MNIST CNN coverage is provided through the dual-task skeleton (Section 5.6).

---

## 2. Locked Design Decisions

Seven design questions were resolved through brainstorming on 2026-05-06. Each cascades through SKILL.md and scripts.

| # | Question | Decision |
|---|---|---|
| **Q1** | Scripts/templates granularity | **5 scripts + 2 templates** (option C — user-instruction names + helpers split out for testability) |
| **Q2** | Method extraction strategy | **Rule-based + mandatory user-supplied target + verification** (option 3 — script greps regex hparams; agent must pass `--target`; script verifies target value exists in PDF text) |
| **Q3** | Code acquisition tiers | **3-tier fallback**: cache → github clone → template+hparams injection |
| **Q4** | How to discover github URL for tier 2 | **PDF-text grep** with regex `github\.com/[\w\-]+/[\w\-\.]+`, take first match |
| **Q5** | Output / workspace paths | `/mnt/user-data/workspace/paper-reproduction-{arxiv_id}/` (intermediate) and `/mnt/user-data/outputs/paper-reproduction-{arxiv_id}/` (final); cache mount at `/mnt/scideer-cache/` |
| **Q6** | `pytorch_skeleton.py` coverage | **Dual-task: GCN + simple CNN**, with graceful exit when dataset is unsupported (option B) |
| **Q7** | `scale_down.py` policy | **Halve epochs + subsample data when training set > 10K**, with comparator's tolerance auto-widening based on scale-down + code source (option B) |

---

## 3. SKILL.md Frontmatter

```yaml
---
name: paper-reproduction
description: Use this skill when the user wants to reproduce a specific
  quantitative result from an academic paper (e.g. "reproduce Table 2 of
  arxiv:1609.02907", "verify the GCN accuracy on Cora", "rerun the MNIST
  experiment from this paper"). The skill generates code, runs it in the
  sandbox at mini-scale (CPU < 5 min), and produces a comparison report.
  Not for surveys (use systematic-literature-review) or general code
  generation (use bash directly).
---
```

(Description copied verbatim from parent design 4.1 to match the lead-agent prompt budget.)

---

## 4. File Layout (final)

```
skills/custom/paper-reproduction/
├── SKILL.md                          ~400 lines
│
├── scripts/
│   ├── __init__.py                   (empty package marker)
│   ├── download_paper.py             ~110 lines  — L1: arxiv API + PDF→text
│   ├── extract_method.py             ~190 lines  — L2+L3: hparams + target verify + github URL grep
│   ├── scale_down.py                 ~80 lines   — L5: epochs halve + data subsample
│   ├── run_experiment.py             ~220 lines  — L4+L6: 3-tier code acquire + sandbox exec
│   └── comparator.py                 ~100 lines  — L7+L8: delta + tolerance + report.md
│
├── templates/
│   ├── pytorch_skeleton.py           ~180 lines  — Tier 3 GCN+CNN dual-task skeleton
│   └── report.md.tmpl                ~40 lines   — comparator.py renders this
│
└── tests/
    ├── __init__.py
    ├── test_extract_method.py
    ├── test_scale_down.py
    ├── test_comparator.py
    ├── test_run_experiment.py
    ├── test_e2e_gcn.sh               — manual end-to-end gate (Day 4 acceptance)
    └── fixtures/
        └── gcn_paper_text.txt        — pre-extracted GCN paper text
```

### 4.1 Module dependency graph

```
SKILL.md (workflow forces agent to call 5 scripts in order)
    │
    ▼
download_paper.py → paper.pdf, paper.txt              (workspace/)
    │
    ▼
extract_method.py → repro_plan.json                   (workspace/)
    │
    ▼
scale_down.py    → repro_plan.json (+ scaled_hparams) (workspace/)
    │
    ▼
run_experiment.py → metrics.json, code/, logs/, figures/ (workspace/)
    │
    ▼
comparator.py    → comparison.json + report.md → outputs/
```

Each script reads only upstream artifacts; the PDF is parsed exactly once. This is the core anti-hallucination property: downstream steps consume JSON, never re-read the PDF.

### 4.2 Path conventions

| Path | Purpose | Layer |
|---|---|---|
| `/mnt/user-data/uploads/` | Optional user-uploaded PDFs | sandbox |
| `/mnt/user-data/workspace/paper-reproduction-{arxiv_id}/` | Intermediate artifacts | sandbox |
| `/mnt/user-data/outputs/paper-reproduction-{arxiv_id}/` | Final deliverables (visible to user) | sandbox |
| `/mnt/scideer-cache/{repo}/` (read-only mount of `~/.scideer/cache/`) | Tier-1 code cache | sandbox mount |

---

## 5. Workflow and Data Contracts

### 5.1 Six bash steps the agent MUST run in order

SKILL.md hardwires these — no improvisation, no skipping. Each script encodes determinism that prevents the agent from "reproducing" a paper in its head.

```bash
# Phase 1 — Plan (conversational; no script)
ARXIV_ID="<the arxiv id>"
TARGET="<user's target, e.g. 'Table 2 GCN/Cora row, expected ~81.5%'>"
WS="/mnt/user-data/workspace/paper-reproduction-$ARXIV_ID"
OUT="/mnt/user-data/outputs/paper-reproduction-$ARXIV_ID"
mkdir -p "$WS" "$OUT"

# Phase 2 — Download
python /mnt/skills/custom/paper-reproduction/scripts/download_paper.py "$ARXIV_ID" --workspace "$WS"

# Phase 3 — Extract method
python /mnt/skills/custom/paper-reproduction/scripts/extract_method.py --workspace "$WS" --target "$TARGET"

# Phase 4 — Scale down
python /mnt/skills/custom/paper-reproduction/scripts/scale_down.py --workspace "$WS"

# Phase 5 — Run experiment
python /mnt/skills/custom/paper-reproduction/scripts/run_experiment.py --workspace "$WS" --timeout 240

# Phase 6 — Compare and report
python /mnt/skills/custom/paper-reproduction/scripts/comparator.py --workspace "$WS" --output "$OUT"
```

If any step exits non-zero, the agent stops and writes a partial `report.md` describing which step failed. It does NOT guess missing data and proceed.

### 5.2 `repro_plan.json` schema (Phase 3 + 4 output)

```json
{
  "schema_version": "1.0",
  "arxiv_id": "1609.02907",
  "paper_title": "Semi-Supervised Classification with Graph Convolutional Networks",
  "target": {
    "description": "Table 2 GCN/Cora row, expected ~81.5%",
    "metric_name": "test_accuracy",
    "expected_value": 81.5,
    "expected_unit": "percent",
    "verified_in_paper": true,
    "found_at_offset": 12483,
    "context_snippet": "...GCN (this paper) | 81.5 | 70.3 | 79.0..."
  },
  "method": {
    "model_arch_hint": "GCN",
    "dataset": "Cora",
    "epochs": 200,
    "learning_rate": 0.01,
    "batch_size": null,
    "weight_decay": 5e-4,
    "hidden_dim": 16,
    "dropout": 0.5,
    "num_layers": 2,
    "extracted_via": "regex"
  },
  "code_repo_url": "https://github.com/tkipf/gcn",
  "code_repo_url_source": "pdf_grep",
  "scaled_hparams": {
    "epochs_used": 100,
    "data_subset_size": null,
    "rationale": "halved epochs to fit 4-min CPU budget"
  },
  "warnings": []
}
```

Conventions:
- Any unextracted field becomes `null` and a description is appended to `warnings`.
- `extracted_via` is `"regex"` or `"user_provided"`.
- `verified_in_paper=false` causes `extract_method.py` to exit 2 and SKILL.md forces the agent to ask the user a clarification.

### 5.3 `metrics.json` schema (Phase 5 output)

```json
{
  "schema_version": "1.0",
  "arxiv_id": "1609.02907",
  "code_source": "cache",
  "code_path_in_workspace": "code/pygcn/",
  "wall_time_seconds": 32.4,
  "exit_code": 0,
  "final_metrics": {
    "test_accuracy": 0.8023,
    "test_accuracy_unit": "fraction",
    "train_loss_final": 0.234,
    "epochs_actually_run": 100
  },
  "training_curve": [
    {"epoch": 1, "train_loss": 1.94, "val_acc": 0.302},
    {"epoch": 10, "train_loss": 0.85, "val_acc": 0.729}
  ],
  "errors": [],
  "warnings": []
}
```

Conventions:
- `code_source` ∈ `{"cache", "github_clone", "template"}` — drives comparator's tolerance band.
- On crash: `exit_code != 0`, `final_metrics: null`, `errors[]` populated with category (`oom` / `nan` / `timeout` / `dep_missing` / `other`).

### 5.4 `comparison.json` schema (Phase 6 output)

```json
{
  "schema_version": "1.0",
  "arxiv_id": "1609.02907",
  "paper_value": 81.5,
  "paper_unit": "percent",
  "our_value": 80.23,
  "our_unit": "percent",
  "delta_absolute": -1.27,
  "delta_relative": -0.0156,
  "tolerance_used": 0.05,
  "tolerance_basis": "cache + scale_down (epochs halved)",
  "verdict": "within_tolerance",
  "wall_time_seconds": 32.4,
  "code_source": "cache",
  "scale_down_applied": true
}
```

`verdict` ∈ `{"within_tolerance", "deviated", "execution_failed"}`.

### 5.5 Tolerance-widening rules (in `comparator.py`)

| Condition | Tolerance |
|---|---|
| `code_source=cache` AND no scale-down | ±3% (default) |
| `code_source=cache` AND epochs scaled only | ±5% |
| `code_source=cache` AND data subsampled | ±8% |
| `code_source=github_clone` | above + 2 percentage points |
| `code_source=template` | ±15% (Tier 3 expects looser fit) |

### 5.6 `pytorch_skeleton.py` (templates/) structure

Dual-task skeleton with graceful exit:

```python
def main(plan):
    dataset = plan["method"]["dataset"]
    if dataset in {"Cora", "Citeseer", "Pubmed"}:
        run_gcn(plan)            # ~70 lines: 2-layer GCN, full Planetoid dataset
    elif dataset in {"MNIST", "FashionMNIST"}:
        run_cnn(plan)            # ~70 lines: 3-conv + 2-fc small CNN
    else:
        # Graceful exit — write metrics.json with errors=[], code_source="template",
        # final_metrics=null, exit_code=2, errors=["Dataset {x} not supported by skeleton"]
        write_failure_metrics(...)
        sys.exit(2)
```

Hparams are read from `repro_plan.json` (scaled values used). Output to stdout uses sentinel lines:
```
SKELETON_METRIC test_accuracy=0.8023
SKELETON_METRIC train_loss_final=0.234
SKELETON_EPOCH 1 train_loss=1.94 val_acc=0.302
```

`run_experiment.py` greps these sentinel lines from the subprocess stdout to populate `metrics.json`.

### 5.7 `report.md` template structure

```markdown
# Reproduction Report: {paper_title}

**arXiv:** {arxiv_id} | **Reproduced:** {date} | **Mode:** mini-scale
**Verdict:** {verdict_emoji} {verdict_text}

## Target
- Metric: {target.description}
- Paper reported: **{paper_value}{unit}**

## Reproduced
- Our result: **{our_value}{unit}**
- Δ: {delta_absolute:+.2f}{unit} ({delta_relative:+.2%})
- Tolerance: ±{tolerance_used:.0%} ({tolerance_basis})
- Wall time: {wall_time_seconds:.1f}s on CPU

## Code Source
- Tier: {code_source}
- Repo: {code_repo_url or "N/A"}

## Scale-Down Applied
{scaled_hparams_block_or_"None"}

## Figures
![Training curve](figures/training_curve.png)
![Accuracy curve](figures/accuracy_curve.png)

## Method (extracted from paper)
| Hparam | Value | Source |
|---|---|---|
| epochs | {epochs} | regex |
| learning_rate | {lr} | regex |
| ... | ... | ... |

## Warnings
{warnings_list_or_"None"}

## Errors
{errors_list_or_"None"}

## Conclusion
{auto_conclusion}
```

`auto_conclusion` is one line, generated from `verdict`:
- `within_tolerance` → "✅ Reproduction successful within ±{tol:.0%} tolerance."
- `deviated` → "⚠️ Reproduction deviated by {delta:+.2%}; possible causes: {hint}."
- `execution_failed` → "❌ Execution failed at phase {phase}: {first_error}. Manual intervention required."

---

## 6. Failure-Mode Matrix (never silent)

Nine failure classes; every one produces a viewable `report.md`.

| # | Failure | Detection (which script) | report.md content |
|---|---|---|---|
| **F1** | Invalid arxiv_id / network down | `download_paper.py` exit ≠ 0 | "❌ Could not download arxiv:{id}: {http_error}. Verify arxiv_id." |
| **F2** | PDF parse fails / paper.txt < 1KB | `download_paper.py` post-check | "❌ PDF parsed to {N} chars. Image-based PDF; manual transcription needed." |
| **F3** | No target / target absent from PDF | `extract_method.py` exit 2 | (writes `verified_in_paper:false` to plan) SKILL.md forces agent to re-prompt user |
| **F4** | Critical hparam unextracted | `extract_method.py` writes `null` + warnings | Method table shows `null` rows; Warnings section enumerates |
| **F5** | All 3 code-acquire tiers fail | `run_experiment.py` after T1/T2/T3 | "❌ Could not acquire code: cache miss + clone failed + skeleton dataset unsupported" |
| **F6** | Sandbox OOM | `run_experiment.py` SIGKILL + dmesg keyword | "❌ OOM at epoch {N}. Consider batch=8 or subset." |
| **F7** | NaN / non-convergence | `run_experiment.py` greps `nan` in log | "❌ Diverged; final loss=NaN at epoch {X}." |
| **F8** | Timeout > 240s | `run_experiment.py` `--timeout` | "❌ Force-stopped at 240s. {epochs_run}/{target_epochs} completed." |
| **F9** | Metric deviates beyond tolerance | `comparator.py` `verdict="deviated"` | "⚠️ Deviated by {delta:+.2%}; possible causes: {auto-hint}." |

---

## 7. Demo Path: GCN End-to-End Trace

Concrete trace for the 2026-05-12 demo (cache hit case):

```
[T+0s]   user: "Reproduce Table 2 GCN/Cora row of arxiv:1609.02907"
[T+0s]   agent reads SKILL.md, parses arxiv_id and target
[T+0s]   agent: mkdir -p $WS $OUT
[T+0s]   agent: bash download_paper.py 1609.02907 --workspace $WS
[T+5s]   ✓ paper.pdf (487KB) + paper.txt (38KB)
[T+5s]   agent: bash extract_method.py --workspace $WS --target "Table 2 GCN/Cora row, expected ~81.5%"
[T+7s]   ✓ repro_plan.json: target verified=true, hparams populated, repo_url=tkipf/gcn
[T+7s]   agent: bash scale_down.py --workspace $WS
[T+7s]   ✓ scaled_hparams.epochs_used=100, no subsample (Cora < 10K)
[T+7s]   agent: bash run_experiment.py --workspace $WS --timeout 240
[T+8s]   Tier 1: cache hit at /mnt/scideer-cache/pygcn/  ← demo critical path
[T+8s]   copy code/, inject scaled hparams
[T+10s]  start training
[T+45s]  ✓ metrics.json: test_accuracy=0.8023, wall_time=35.1s
[T+45s]  agent: bash comparator.py --workspace $WS --output $OUT
[T+46s]  delta=-1.27, tolerance=±5%, verdict=within_tolerance
[T+47s]  ✓ outputs/paper-reproduction-1609.02907/{report.md, comparison.json, code/, logs/, figures/}

Total: ~47 seconds (well within 5-min budget)
```

### 7.1 Tier 2 (cache miss, github clone hits) trace

```
[T+8s]   Tier 1: cache miss
[T+8s]   Tier 2: git clone --depth 1 --timeout 60 https://github.com/tkipf/gcn
[T+25s]  ✓ clone OK
... continues normally, total ~62s
```

### 7.2 Tier 3 (cache miss + clone fails) trace

```
[T+8s]   Tier 1: cache miss
[T+68s]  Tier 2: git clone timeout
[T+68s]  Tier 3: copy templates/pytorch_skeleton.py to $WS/code/
[T+70s]  skeleton routes Cora to run_gcn() branch, injects hparams, starts training
[T+105s] ✓ test_accuracy=0.7912 (lower than Tier 1 because skeleton is minimal)
[T+105s] comparator: tolerance="template" → ±15%, |delta|=2% → within_tolerance
... total ~110s, demo still successful
```

All 3 traces produce a valid `report.md` — the operationalisation of "never silent failure".

---

## 8. Testing Strategy

### 8.1 Unit tests (host, ~250 LOC, 4 files)

| Test file | Coverage | Fixture |
|---|---|---|
| `test_extract_method.py` | • GCN paper text → epochs=200, lr=0.01<br>• `--target "Table 2 GCN/Cora"` → expected_value=81.5, verified=true<br>• fake target "Table 99" → verified=false, exit 2<br>• github URL grep → matches `tkipf/gcn`<br>• no-URL paper → code_repo_url=null | `tests/fixtures/gcn_paper_text.txt` |
| `test_scale_down.py` | • epochs=200 → 100<br>• epochs=10 → 10 (floor)<br>• 60K samples → subsample 10K<br>• Cora 2708 → no subsample | inline JSON |
| `test_comparator.py` | • paper=81.5, our=80.23, cache → tolerance=0.03, within<br>• paper=81.5, our=70.0 → deviated<br>• exit_code=137 (OOM) → execution_failed<br>• template + scaled → tolerance≥0.15 | inline JSON |
| `test_run_experiment.py` | • Tier 1 cache mock<br>• Tier 2 clone fail → Tier 3 fallback<br>• timeout SIGKILL → metrics.errors=["timeout"] | `tests/fixtures/fake_cache/` |

Run: `pytest skills/custom/paper-reproduction/tests/ -v`.

### 8.2 End-to-end test (manual gate)

`tests/test_e2e_gcn.sh` — bash script run on the actual server after `~/.scideer/cache/pygcn/` is staged. Asserts `report.md`, `comparison.json` exist and `verdict=within_tolerance`. This is the Day-4 acceptance gate.

### 8.3 Out of test scope (YAGNI)

- Real AioSandbox integration (sci-pi track owns)
- Lead-agent skill-routing path (DeerFlow harness owns)
- Bulk reproduction of 100 papers (9-day budget excludes)
- Backup video recording flow (demo track owns)

---

## 9. Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| **AC1** | All 4 unit test files pass on host | `pytest skills/custom/paper-reproduction/tests/ -v` |
| **AC2** | E2E test produces `outputs/paper-reproduction-1609.02907/report.md` on the server | Jasper's manual run after git pull |
| **AC3** | report.md `verdict=within_tolerance`, `our_value` ∈ [78%, 84%] | manual check |
| **AC4** | F1–F9 each manually triggered, `report.md` always present and readable | trigger script + visual check |
| **AC5** | SKILL.md `description` ≤ 500 chars | wc -c |
| **AC6** | All scripts respond to `--help` | python scripts/X.py --help |
| **AC7** | No file outside `skills/custom/paper-reproduction/` is touched | `git status` |

---

## 10. Deliverables

```
skills/custom/paper-reproduction/
├── SKILL.md
├── scripts/__init__.py
├── scripts/download_paper.py
├── scripts/extract_method.py
├── scripts/scale_down.py
├── scripts/run_experiment.py
├── scripts/comparator.py
├── templates/pytorch_skeleton.py
├── templates/report.md.tmpl
├── tests/__init__.py
├── tests/test_extract_method.py
├── tests/test_scale_down.py
├── tests/test_comparator.py
├── tests/test_run_experiment.py
├── tests/test_e2e_gcn.sh
└── tests/fixtures/gcn_paper_text.txt
```

16 files, 1 new directory, 0 modifications elsewhere.

---

## 11. Track-Boundary Contract (with sci-pi and other tracks)

The sci-pi orchestrator (other track, Day 6-7) will invoke this skill via `read_file` of `SKILL.md`. The contract sci-pi consumes:

- **Input**: `arxiv_id` (string) + `target` (string)
- **Output paths** (deterministic): `outputs/paper-reproduction-{arxiv_id}/{report.md, comparison.json, code/, logs/, figures/}`
- **Status detection**: parse `comparison.json` `verdict` field — `within_tolerance` is success, `deviated` is partial, `execution_failed` is hard fail
- **Cache responsibility**: ops track stages `~/.scideer/cache/pygcn/` before demo (this track does NOT pre-cache)
- **Sandbox responsibility**: docker track ensures pytorch + torch_geometric + git pre-installed in `scideer-sandbox` image (this track does NOT install deps at runtime)

If the sandbox image is not ready when this track is implementation-tested, unit tests still pass on host (they don't require the sandbox). E2E test is gated on the sandbox image being ready.

---

## 12. Next Step

Invoke `superpowers:writing-plans` skill to convert this design into a step-by-step implementation plan with TDD discipline.

**End of design document.**
