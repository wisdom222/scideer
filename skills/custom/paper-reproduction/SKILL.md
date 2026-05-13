---
name: paper-reproduction
description: Use this skill when the user wants to reproduce a specific quantitative result from an academic paper (e.g. "reproduce Table 2 of arxiv:1609.02907", "verify the GCN accuracy on Cora", "rerun the MNIST experiment from this paper"). The skill generates code, runs it in the sandbox at mini-scale (CPU < 5 min), and produces a comparison report. Not for surveys (use systematic-literature-review) or general code generation (use bash directly).
---

# Paper Reproduction Skill

> See `docs/plans/2026-05-06-paper-reproduction-design.md` for the full design rationale (locked decisions Q1–Q7, output schemas, failure-mode matrix).

## Overview

This skill reproduces a single quantitative result from an academic paper end-to-end inside the sandbox. Given an arxiv ID and a target metric (e.g. "Table 2 GCN/Cora row, expected ~81.5%"), it:

1. Downloads the paper PDF and extracts text
2. Pulls hyperparameters and the target value out of the text via deterministic regex (no LLM "memory" allowed)
3. Scales hparams down to fit a 4-minute CPU budget
4. Acquires runnable code via three-tier fallback (cache → github clone → built-in skeleton)
5. Runs training in a sandboxed subprocess with a hard timeout
6. Compares the reproduced metric to the paper's reported value with a tolerance band that auto-widens for scale-down / template fallback

Every failure mode produces a viewable `report.md` — the skill **never** silently fails.

## When to Use This Skill

Trigger on any of:

- "Reproduce Table N of arxiv:X" / "verify Y from this paper"
- "Run the GCN experiment from Kipf & Welling"
- "Confirm whether the MNIST result in this paper holds"
- Any request that names a paper + a specific quantitative claim and asks for an empirical check

## When NOT to Use This Skill

- **Multi-paper survey** → use `systematic-literature-review`
- **Single-paper peer review without execution** → use `academic-paper-review`
- **General code generation** ("write me a GCN") → use `bash` and direct coding
- **Data analysis on a CSV the user uploaded** → use `data-analysis`
- **Reproducing a result that requires GPUs, multi-day training, or pretrained checkpoints > 1 GB** — politely refuse and explain the CPU < 5 min budget

## Critical Workflow Rules

> **You MUST follow the 6 bash steps below in exact order. Do NOT skip any step. Do NOT improvise or substitute these calls. Do NOT extract method/run experiment in your own context using your knowledge of the paper. Each script enforces a contract that prevents hallucination.**

The skill works because the PDF is parsed exactly **once** by `extract_method.py`, and every downstream step consumes a JSON contract — never re-reading the paper. Your job as the agent is to glue the bash invocations together, not to substitute reasoning for any of them.

## Workflow

### Phase 1 — Plan (conversational, no script)

Before running anything, confirm two strings with the user. If either is missing or ambiguous, ask **one** clarification question:

- `arxiv_id`: e.g. `1609.02907`. If the user gave a URL, extract the bare id (no version suffix).
- `target`: a free-text description that **must** include a numeric expectation. Examples:
  - `"Table 2 GCN/Cora row, expected ~81.5%"`
  - `"MNIST CNN test accuracy, expected ~99.0%"`
  - `"Table 6 ResNet-56 row, expected ~93.0%"`

If the user does not give a numeric expectation, ask: *"What value should I be aiming for? Quote the table cell or paragraph from the paper if you can."*

Once you have both strings, set up the workspace and continue:

```bash
ARXIV_ID="<the arxiv id, e.g. 1609.02907>"
TARGET="<user's target, e.g. 'Table 2 GCN/Cora row, expected ~81.5%'>"
WS="/mnt/user-data/workspace/paper-reproduction-$ARXIV_ID"
OUT="/mnt/user-data/outputs/paper-reproduction-$ARXIV_ID"
mkdir -p "$WS" "$OUT"
```

### Phase 2 — Download Paper

Use bash to run:

```bash
python /mnt/skills/custom/paper-reproduction/scripts/download_paper.py "$ARXIV_ID" --workspace "$WS"
```

**What it does:** fetches `https://arxiv.org/pdf/{arxiv_id}.pdf`, extracts text via `pdfplumber` (falls back to `pypdf`), writes `paper.pdf` and `paper.txt` to the workspace.

**Expected outcome:** `$WS/paper.pdf` exists (typically 200KB–2MB) and `$WS/paper.txt` is at least 1KB of UTF-8 text.

**Failure handling:** if the script exits non-zero, do NOT proceed. Write a partial report:

```bash
echo "# Reproduction Report (FAILED at Phase 2)
arXiv: $ARXIV_ID
Verdict: FAIL Execution failed
## Errors
- Could not download paper: see workspace/run.log for stderr
## Conclusion
Could not download arxiv:$ARXIV_ID. Verify the id is valid and arxiv.org is reachable from the sandbox." > "$OUT/report.md"
```

Then stop. Do NOT improvise paper content.

### Phase 3 — Extract Method

Use bash to run:

```bash
python /mnt/skills/custom/paper-reproduction/scripts/extract_method.py \
    --workspace "$WS" \
    --target "$TARGET" \
    --arxiv-id "$ARXIV_ID"
```

**What it does:** reads `$WS/paper.txt`, extracts `epochs / learning_rate / dropout / weight_decay / hidden_dim / batch_size / num_layers / dataset / model_arch_hint` via regex, parses the numeric expectation out of `--target`, verifies that number actually appears in the paper text (anti-hallucination check), greps for the first `https://github.com/<owner>/<repo>` URL, and writes everything to `$WS/repro_plan.json`.

**Exit codes:**
- `0` — all critical fields populated, target verified in paper text
- `1` — usage error or missing input file
- `2` — target value NOT found in paper text (`verified_in_paper=false`)

**If exit code is 2,** the user gave a target that doesn't appear in the paper. Ask the user:

> "I couldn't find `{expected_value}` anywhere in the paper text. Either (a) the value is in a figure/table image that PDF extraction missed, or (b) you may have the wrong number. Could you double-check the paper and re-state the target — including the exact value and which Table/Figure it's in?"

Then loop: when the user gives a corrected `$TARGET`, re-run Phase 3. Do NOT proceed past Phase 3 with `verified_in_paper=false`.

**Failure handling:** for any other non-zero exit, write a partial report and stop.

### Phase 4 — Scale Down

Use bash to run:

```bash
python /mnt/skills/custom/paper-reproduction/scripts/scale_down.py --workspace "$WS"
```

**What it does:** mutates `$WS/repro_plan.json` in place by adding a `scaled_hparams` field. Two rules:

- `epochs_used = max(10, original_epochs // 2)` — halve epochs, floor at 10
- `data_subset_size = 10000` if dataset is NOT `Cora/Citeseer/Pubmed` (those are already small enough); otherwise `null`

**Failure handling:** if exit non-zero, the upstream `repro_plan.json` is malformed. Stop and write a partial report describing the issue.

### Phase 5 — Run Experiment

Use bash to run:

```bash
python /mnt/skills/custom/paper-reproduction/scripts/run_experiment.py \
    --workspace "$WS" \
    --timeout 240
```

**What it does:** the heart of the skill. Three-tier code acquisition:

1. **Tier 1 — Cache hit:** look for code at `$SCIDEER_CACHE_DIR/<repo_name>/` (default `/mnt/scideer-cache/`). Probes both `repo_name` (parsed from URL) and common fallbacks `pygcn` / `gcn`.
2. **Tier 2 — github clone:** if no cache hit and `repro_plan.json` has `code_repo_url`, run `git clone --depth 1 <url>` with a 60s timeout. If clone succeeds, use it.
3. **Tier 3 — Template skeleton:** if both fail, copy `templates/pytorch_skeleton.py` to `$WS/code/skeleton.py`. The skeleton routes by `SCIDEER_DATASET` env var: Cora/Citeseer/Pubmed → `run_gcn()`, MNIST/FashionMNIST → `run_cnn()`, anything else → graceful exit with `SKELETON_ERROR unsupported_dataset`.

After acquisition, the script:
- Detects an entrypoint (`train.py` / `main.py` / `run.py` / `skeleton.py`) inside `$WS/code/`
- Sets env vars: `SCIDEER_EPOCHS`, `SCIDEER_LR`, `SCIDEER_HIDDEN`, `SCIDEER_DROPOUT`, `SCIDEER_DATASET`, `SCIDEER_SUBSET`
- Runs the entrypoint as a subprocess with the supplied timeout (default 240s)
- Parses sentinel lines from stdout:
  - `SKELETON_METRIC test_accuracy=0.8023` → `final_metrics`
  - `SKELETON_EPOCH 1 train_loss=1.94 val_acc=0.30` → `training_curve`
- Writes `$WS/metrics.json` AND `$WS/logs/run.log`

**This script always writes `metrics.json` and always exits 0.** Even on subprocess failure (OOM / NaN / timeout / dep_missing), the script captures the failure cleanly. The `comparator.py` decides the verdict based on `exit_code` and `errors[]`.

**Important contract for cached / cloned code:** the entrypoint MUST emit metrics in the sentinel format above. The bundled fake cache fixture and the template skeleton both follow this convention. If a github-cloned repo doesn't emit sentinels, `metrics.json` will have empty `final_metrics` and the comparator will mark `execution_failed`.

### Phase 6 — Compare and Report

Use bash to run:

```bash
python /mnt/skills/custom/paper-reproduction/scripts/comparator.py \
    --workspace "$WS" \
    --output "$OUT"
```

**What it does:** reads `$WS/repro_plan.json` + `$WS/metrics.json`, computes:

- `delta_absolute = our_value - paper_value` (in percent)
- `delta_relative = delta_absolute / paper_value`
- `tolerance_used`: based on `code_source` and whether scale-down was applied
- `verdict`: `within_tolerance` / `deviated` / `execution_failed`

Tolerance auto-widening table:

| code_source | scale-down state | tolerance |
|---|---|---|
| cache | none | ±3% |
| cache | epochs scaled | ±5% |
| cache | data subsampled | ±8% |
| github_clone | (any) | above + 2pp |
| template | (any) | ±15% |

Then renders `$OUT/report.md` from `templates/report.md.tmpl`, writes `$OUT/comparison.json`, and copies `$WS/{code,logs,figures}/` into `$OUT/`.

**Final step:** show the user a preview of `report.md` and the path to the full file.

## Output Structure

After a successful run, the user sees:

```
/mnt/user-data/outputs/paper-reproduction-{arxiv_id}/
├── report.md              ⭐ primary deliverable (Markdown, viewable)
├── comparison.json        machine-readable verdict (consumed by sci-pi / benchmarks)
├── code/                  the actual code that ran (cache copy / github clone / skeleton)
├── logs/run.log           subprocess stdout (training log)
└── figures/               training curve PNGs (if the entrypoint produces them)
```

The `report.md` contains: target description, paper-reported value, our reproduced value, delta + tolerance, code source tier, scale-down rationale, method table (extracted hparams), warnings, errors, and an auto-generated one-line conclusion.

## Failure Modes

This skill never silently fails. Every failure class produces a viewable `report.md`. Map your behavior to the correct class.

| # | Failure | Where detected | Agent must do |
|---|---|---|---|
| **F1** | Invalid arxiv_id / network down | `download_paper.py` exit ≠ 0 | Stop. Write partial report (see Phase 2 failure handling). |
| **F2** | PDF parse fails / paper.txt < 1KB | `download_paper.py` warning to stderr | Inspect paper.txt. If < 1KB, treat as F2: report "image-based PDF, manual transcription required." |
| **F3** | Target absent from paper text | `extract_method.py` exit 2 | Re-prompt user (see Phase 3 failure handling). Do NOT proceed. |
| **F4** | Hparam extraction returned `null` | `repro_plan.json` warnings | Continue, but the report's Method table will show `null` rows. The skeleton/cached code will use script defaults. |
| **F5** | All 3 acquire tiers fail | `run_experiment.py` writes `code_source="template"` + `errors=["acquire_failed"]` | The comparator handles this — no extra agent action. |
| **F6** | Sandbox OOM | `run_experiment.py` greps `OutOfMemoryError` / `killed` in stdout | Same — the comparator labels `verdict=execution_failed`. |
| **F7** | NaN / non-convergence | `run_experiment.py` greps `nan` in stdout | Same. |
| **F8** | Timeout > 240s | `run_experiment.py` `subprocess.run(timeout=)` raises | Same. |
| **F9** | Metric deviates beyond tolerance | `comparator.py` `verdict="deviated"` | The report includes an auto-generated "possible cause" hint. Show it to the user. |

The agent is responsible for F1–F3 (early failures, before run_experiment). F4–F9 are handled by the scripts and the comparator — the agent just runs Phase 6 and presents the report.

## Examples

### Example 1 — GCN happy path (demo)

User: *"Reproduce Table 2 GCN/Cora row of arxiv:1609.02907."*

Your sequence:
1. Phase 1 — confirm `ARXIV_ID=1609.02907`, `TARGET="Table 2 GCN/Cora row, expected ~81.5%"`, set `$WS` and `$OUT`.
2. Phase 2 — `download_paper.py` 1609.02907 → paper.pdf + paper.txt
3. Phase 3 — `extract_method.py --target ...` → repro_plan.json with epochs=200, lr=0.01, hidden=16, dropout=0.5, dataset=Cora, code_repo_url=tkipf/gcn, target verified=true
4. Phase 4 — `scale_down.py` → epochs_used=100
5. Phase 5 — `run_experiment.py` → Tier 1 cache hit at `/mnt/scideer-cache/pygcn/` → 35s training → metrics.json with test_accuracy=0.8023
6. Phase 6 — `comparator.py` → delta=-1.27pp, tolerance=±5%, verdict=within_tolerance → report.md to `/mnt/user-data/outputs/paper-reproduction-1609.02907/`
7. Show user preview of report.md and the output path.

Total wall time: ~47 seconds.

### Example 2 — Target not found in paper

User: *"Reproduce arxiv:1609.02907 with expected accuracy 95% on Cora."*

Your sequence:
1. Phase 1 — `TARGET="expected ~95% on Cora"`
2. Phase 2 — download succeeds
3. Phase 3 — `extract_method.py` exits 2 because "95" doesn't appear in the paper near a Cora/accuracy context.
4. You re-prompt: *"I couldn't find `95` anywhere in the paper. The Table 2 row for GCN on Cora reports `81.5`. Did you mean that, or were you thinking of a different paper?"*
5. User clarifies: *"Right, 81.5%."*
6. Re-run Phase 3 with corrected target → exit 0 → continue Phases 4–6.

### Example 3 — OOM during execution

User: *"Reproduce ResNet-56 on CIFAR-10 from arxiv:1512.03385, expected ~93.0%."*

Your sequence:
1. Phases 1–4 succeed: target verified, hparams extracted (epochs=164, batch=128).
2. Phase 5 — Tier 1 cache miss (no ResNet-56 pre-cache), Tier 2 github clone of the official repo succeeds, but the subprocess hits OOM at epoch 23 in 8 GB sandbox.
3. `run_experiment.py` writes `metrics.json` with `exit_code=137`, `errors=["oom: out of memory"]`, `final_metrics=null`.
4. Phase 6 — comparator writes `verdict=execution_failed`. The report's Conclusion line says: *"Execution failed: oom: out of memory. Manual intervention required."*
5. Present the report to the user. Suggest they retry with `--timeout 480` or smaller batch (note: would require manual override; not in this skill's scope).

## Notes

- **Sandbox prerequisite:** `pdfplumber` (or `pypdf` as fallback) must be importable. PyTorch is needed for Tier 3 GCN/CNN skeleton; `torch_geometric` for the GCN branch; `torchvision` for the CNN branch.
- **Cache prerequisite for the demo:** `~/.scideer/cache/pygcn/` should contain the official `tkipf/pygcn` repo; `~/.scideer/cache/torch_geometric/Cora/` should contain the Planetoid Cora dataset. Ops/demo track owns staging this.
- **No web_fetch.** This skill does NOT use Jina/web_fetch. All external data flows are: arxiv PDF endpoint (Phase 2), and `git clone` to github (Phase 5 Tier 2). Both can be cached for offline demo.
- **No LLM extraction.** Phase 3 is pure regex. The reason: LLM-driven extraction can hallucinate hparams that look plausible but aren't in the paper. Regex extraction either finds the value or returns `null` (and adds a warning); the agent then sees `null` and asks the user.
- **The agent does NOT decide the verdict.** Tolerance and verdict are deterministic functions of `code_source` + `scale_down` state, computed in `comparator.py`. Do not "interpret" or "soften" the verdict in your final message to the user — quote the report verbatim.
- **5-minute budget.** The default timeout is 240s. If a paper truly cannot reproduce in that budget on CPU, the skill is the wrong tool — politely refuse rather than scaling down so aggressively that the result is meaningless.
