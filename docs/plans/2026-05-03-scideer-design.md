# SciDeer: Scientific Research Lifecycle Extension for DeerFlow 2.0 — Design Document

> PH6725 (AI for Sciences) Final Project
> Date: 2026-05-03 (revised after DeerFlow 2.0 source review)
> Author: Jasper (with Claude Code)
> Base Project: [bytedance/deer-flow](https://github.com/bytedance/deer-flow) — DeerFlow 2.0 (ground-up rewrite, ranked #1 GitHub Trending Feb 28 2026)
> Status: Approved through brainstorming Section 1-6 on 2026-05-03

---

## 0. Why This Document Was Rewritten

The initial design (same date, earlier draft) was based on assumptions about DeerFlow 2.0 that were verified by reading the actual source. Key findings that drove the rewrite:

| Original assumption | Reality in DeerFlow 2.0 |
|---|---|
| "Skills are pure Markdown" | ✅ Confirmed — `skills/public/*/SKILL.md` + optional `scripts/`, `templates/`, `evals/` |
| "Native MCP support" | ✅ Confirmed — `extensions_config.json` with stdio + HTTP/SSE + OAuth |
| "Kimi-K2 directly compatible" | ⚠️ Partial — DeerFlow officially supports `kimi-k2.5` via `deerflow.models.patched_deepseek:PatchedChatDeepSeek` (not raw ChatOpenAI) |
| "DeerFlow has no scientific skills" | ❌ **Wrong** — already ships `systematic-literature-review`, `academic-paper-review`, `deep-research`, `data-analysis`, `chart-visualization`, plus a bundled `arxiv_search.py` script |
| "Need separate arXiv MCP" | ❌ Unnecessary — built-in skill already searches arXiv natively |
| "Skills triggered by keywords" | ❌ Wrong — Lead Agent selects skills by reading `description` frontmatter |
| "8 GB RAM is sufficient" | ⚠️ Marginal — official recommendation is 16 GB for `make dev` workflow |
| "Python 3.10+, Node.js 18+" | ❌ Wrong — DeerFlow 2.0 requires Python 3.12+, Node.js 22+ |

**Conclusion:** four out of the originally planned ten components were redundant or wrong. SciDeer is now repositioned as a **focused extension** that closes the *real* capability gap rather than rebuilding what already works.

---

## 1. Repositioned Project Summary

> **SciDeer = DeerFlow 2.0 + the missing scientific-research lifecycle pieces.**
>
> Vanilla DeerFlow can search literature and analyze data, but it cannot **reproduce a paper's quantitative results**, cannot **write a publication-ready LaTeX paper**, and has no **PI-style orchestrator** that chains the full lifecycle. SciDeer fills exactly those three gaps.

### 1.1 What SciDeer adds beyond vanilla DeerFlow

| Capability | vanilla DeerFlow | SciDeer |
|---|:---:|:---:|
| Literature review (arXiv) | ✅ `systematic-literature-review` | ✅ reuse |
| Single-paper peer review | ✅ `academic-paper-review` | ✅ reuse |
| Data analysis + charts | ✅ `data-analysis` + `chart-visualization` | ✅ reuse |
| **Paper reproduction (code gen + sandbox exec + comparison)** | ❌ | ✅ **new `paper-reproduction` skill** |
| **LaTeX paper generation (with bib + compile)** | ❌ | ✅ **new `scientific-writing` skill** |
| **End-to-end research lifecycle orchestration** | ❌ | ✅ **new `sci-pi` custom subagent** |
| Citation graph / cross-database paper search | ❌ (arXiv only) | ✅ **new Semantic Scholar MCP** |

### 1.2 Strict scope (YAGNI applied)

**In scope:**
- 2 original skills: `paper-reproduction`, `scientific-writing`
- 1 custom subagent: `sci-pi` (using DeerFlow native `subagents.custom_agents` mechanism)
- 1 MCP server: Semantic Scholar
- Mini Sci-Bench: 5 tasks comparing vanilla vs SciDeer

**Explicitly cut from original plan:**
- ❌ `literature-review` skill (reuse `systematic-literature-review`)
- ❌ `experiment-runner` skill (use `data-analysis` + `chart-visualization`)
- ❌ arXiv MCP (existing skill bundles `arxiv_search.py`)
- ❌ Wolfram Alpha MCP (no demo trigger; not worth build cost)

---

## 2. Key Constraints

| Dimension | Status |
|---|---|
| Deadline | 2026-05-12 (9 days) |
| Team | Jasper solo dev; teammates assist PPT/Report |
| LLM | Kimi K2.5 (via `PatchedChatDeepSeek`, OpenAI-compatible base `https://api.moonshot.cn/v1`) |
| Dev environment | VSCode SSH Remote → Tencent Cloud Ubuntu (16 GB target, 8 GB minimum) |
| Deployment | Same Tencent Cloud server, Web UI exposed via security-group rule |
| Deliverables | Live Demo (5-10 min) + Report (8-10 pages) + PPT (40-50 min) |
| Output format | LaTeX → PDF for the `scientific-writing` skill |
| Live demo paper | **Primary: arxiv:1609.02907 (GCN on Cora, Kipf & Welling 2017); Backup: simple MNIST CNN** |
| Demo reproduction strategy | **C+ hybrid**: offline pre-run of full Table 2 + live single-slice run + merged display |

---

## 3. System Architecture

### 3.1 Component map

```
+---------------------------------------------------------------+
|                       SciDeer (fork of DeerFlow 2.0)           |
+---------------------------------------------------------------+
|  [Layer 3]  benchmarks/sci_eval/                               |
|             runner.py + 5 task yamls + visualize.py            |
+---------------------------------------------------------------+
|  [Layer 2]  agents/sci-pi/             (custom subagent)       |
|             extensions_config.json     (skills enable + MCP)   |
+---------------------------------------------------------------+
|  [Layer 1]  skills/custom/                                     |
|             ├─ paper-reproduction/     (new)                   |
|             └─ scientific-writing/     (new)                   |
|             docker/scideer-sandbox/    (custom image w/ LaTeX) |
+---------------------------------------------------------------+
|  [Phase 0 / reused, no modification]                           |
|             skills/public/             (21 built-ins reused)   |
|             ├─ systematic-literature-review                    |
|             ├─ academic-paper-review                           |
|             ├─ data-analysis                                   |
|             ├─ chart-visualization                             |
|             └─ ... (16 others)                                 |
|             DeerFlow harness:                                  |
|             ├─ LangGraph orchestration                         |
|             ├─ Lead agent + middleware pipeline                |
|             ├─ Subagent dispatcher (task tool)                 |
|             ├─ AioSandboxProvider (Docker)                     |
|             ├─ MCP server loader                               |
|             └─ Memory + summarization middleware               |
+---------------------------------------------------------------+
```

### 3.2 Repository strategy

Fork-and-extend, no harness-core modification:

```
scideer/  (fork from bytedance/deer-flow, branch: scideer-main)
├── skills/
│   ├── public/         (DeerFlow's 21 built-ins, unchanged)
│   └── custom/         ⭐ SciDeer's primary work area
│       ├── paper-reproduction/
│       │   ├── SKILL.md
│       │   ├── scripts/
│       │   └── templates/
│       └── scientific-writing/
│           ├── SKILL.md
│           ├── scripts/
│           └── templates/
│
├── agents/
│   └── sci-pi/
│       ├── config.yaml                  ⭐ DeerFlow native custom_agent
│       └── prompt.md                    (system_prompt body)
│
├── benchmarks/sci_eval/
│   ├── runner.py
│   ├── tasks/                           (t1_slr.yaml ... t5_pipeline.yaml)
│   ├── fixtures/                        (T3 csv, T4 figures)
│   ├── results/
│   │   ├── vanilla/{task}_{run}_{ts}/
│   │   └── scideer/{task}_{run}_{ts}/
│   ├── visualize.py
│   ├── results.csv
│   └── RESULTS.md
│
├── docker/scideer-sandbox/
│   └── Dockerfile                       (base AIO + pytorch + torch_geometric + texlive)
│
├── config.yaml                          ⭐ models, sandbox (AioSandbox), subagents
├── extensions_config.json               ⭐ enabled skills + Semantic Scholar MCP
├── .env                                 (MOONSHOT_API_KEY, S2 key, etc.)
└── docs/plans/2026-05-03-scideer-design.md     (this document)
```

### 3.3 Sandbox approach

| Decision | Value |
|---|---|
| Provider | `deerflow.community.aio_sandbox:AioSandboxProvider` |
| Image | Custom `scideer-sandbox`, built from official AIO base + extra layers |
| Pre-installed | python3.11, pytorch (CPU), sklearn, numpy, pandas, matplotlib, torch_geometric, texlive-latex-extra, biber, bibtex |
| Build timing | Once during Phase 0 (Day 2); reused by all threads thereafter |
| Fallback | If Docker build fails: skill-internal `apt install` (slower, repeated per thread) |

The custom sandbox image is critical for Demo reliability: it removes runtime `apt install` waits and guarantees the LaTeX toolchain is present.

### 3.4 Cross-skill data flow

DeerFlow's `ThreadDataMiddleware` already provides per-thread isolated directories. SciDeer reuses this — no custom state-passing protocol:

```
Thread start → ThreadDataMiddleware creates:
  /mnt/user-data/uploads/        (user-uploaded PDFs)
  /mnt/user-data/workspace/      (skill intermediate region)
  /mnt/user-data/outputs/        (final deliverables)

sci-pi orchestration example:
  systematic-literature-review → outputs/slr-{topic}.md
                                      ↓
  paper-reproduction        → workspace/repro-{arxiv_id}/code/
                            → workspace/repro-{arxiv_id}/results.json
                            → outputs/repro-{arxiv_id}/report.md
                                      ↓
  data-analysis (reused)
  chart-visualization (reused)
                            → workspace/figures/*.png
                                      ↓
  scientific-writing        ← reads all of the above
                            → outputs/paper/paper.tex
                            → outputs/paper/references.bib
                            → outputs/paper/paper.pdf
```

---

## 4. New Component: `paper-reproduction` skill

### 4.1 SKILL.md frontmatter

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

### 4.2 Five-phase workflow

| Phase | Input | Action | Failure-mode artifact |
|---|---|---|---|
| **1. Plan** | arxiv ID + target ("Table 2 GCN/Cora row") | One clarification if target missing; emit `repro_plan.json` (target_metric, expected_value, dataset, model, scale_strategy) | "Need target before continuing" |
| **2. Comprehend** | arxiv PDF + plan | Use built-in `read_file` (PDF→Markdown supported) to extract method/dataset/hparams/expected number | "Cannot extract key value, need manual input" |
| **3. Code Acquire** | plan + comprehension | Three-tier fallback: ① local cache (`~/.scideer/cache/`) → ② official GitHub repo → ③ template + LLM patch | "Cannot acquire code, list of attempted paths" |
| **4. Scale-Down + Run** | acquired code + plan | Auto-rewrite epochs/batch/data subset; write to `workspace/repro-{id}/`; run in AioSandbox with hard timeout 240 s | "Execution failed + error attribution (OOM/dep/numerical/other)" |
| **5. Compare + Report** | run output + plan target | Compute delta (absolute + percent); emit Markdown report + figures (loss/acc curves) | "Executed but deviates > 10%, marked deviation" |

### 4.3 Output structure (deterministic)

```
/mnt/user-data/outputs/repro-{arxiv_id}/
├── report.md              ⭐ primary deliverable
├── code/                  (the actual code that ran)
├── logs/run.log           (training log)
├── figures/               (loss + acc curves)
├── repro_plan.json        (Phase 1 plan)
└── comparison.json        (machine-readable; consumed by benchmark)
```

### 4.4 `report.md` template

```markdown
# Reproduction Report: {paper_title}

**arXiv:** {id} | **Reproduced:** {date} | **Mode:** mini-scale

## Target
- Metric: {Table 2, GCN on Cora}
- Paper reported: **81.5%**

## Reproduced
- Our result: **80.2%**
- Δ: -1.3% (within ±3% tolerance) ✅
- Wall time: 32.4 s on CPU

## Scale-Down Applied
- Epochs: 200 → 100 (saved ~50% time)
- Batch: unchanged
- Dataset: full Cora used

## Figures
![Training curve](figures/training.png)

## Code
- Source: official pygcn (cached)
- Modifications: epochs override only

## Conclusion
✅ Reproduction successful within tolerance.
```

### 4.5 Bundled scripts (`paper-reproduction/scripts/`)

| Script | Purpose | LOC est |
|---|---|---|
| `repro_plan.py` | Solidify Phase 1 output to JSON | ~60 |
| `code_resolver.py` | Three-tier fallback resolver | ~150 |
| `scale_down.py` | Detect and rewrite epochs/batch/data | ~120 |
| `runner.py` | Sandbox exec + log capture + hard timeout | ~80 |
| `comparator.py` | Numeric diff + delta + tolerance judgment | ~80 |

Total: ~500 lines, achievable by Day 4.

### 4.6 Bundled templates (`paper-reproduction/templates/`)

| Template | Use |
|---|---|
| `report.md.tmpl` | Output report skeleton |
| `pytorch_minimal.py` | Fallback: pure PyTorch with standard training loop |
| `sklearn_minimal.py` | Fallback: sklearn task |
| `gnn_minimal.py` | Fallback: torch_geometric GCN — **demo primary path** |

### 4.7 Demo pre-cache strategy (high-score critical)

Phase 0 manual prep on the server:

```bash
mkdir -p ~/.scideer/cache/
git clone https://github.com/tkipf/pygcn ~/.scideer/cache/pygcn
python -c "from torch_geometric.datasets import Planetoid; \
           Planetoid('~/.scideer/cache/torch_geometric', 'Cora')"
```

`code_resolver.py` priority:

1. **Cache hit** → demo path, deterministic < 5 s
2. GitHub clone → first-time or cache-miss, ~30 s
3. Template + LLM patch → no open-source code, ~60 s

Sandbox mounts:

```yaml
sandbox:
  mounts:
    - host_path: ~/.scideer/cache
      container_path: /mnt/scideer-cache
      read_only: true
```

### 4.8 Failure-mode matrix (never silent)

| Failure | Detection | Report content |
|---|---|---|
| Code unobtainable | All three resolver tiers fail | "Tried cache/github/template; all failed. Suggest manual code path." |
| Sandbox OOM | Exit code + dmesg | "OOM detected; suggest batch=8 or subset sampling" |
| NaN / non-convergence | Loss inspection | "Diverged; final loss=NaN at epoch X" |
| Timeout > 240 s | Runner timer | "Force-stopped; suggest epochs ≤ X" |
| Deviation > 10% | Comparator | "Reproduction deviated: paper 81.5%, ours 65%, Δ -16.5%; possible causes:" |

Every case writes a usable `report.md`. **The skill never fails silently and always produces a viewable artifact for demo.**

### 4.9 C+ mode (offline full Table 2 pre-run)

The `sci-pi` orchestrator drives this loop during Day 7 prep:

```python
for row in [("Cora", 81.5), ("Citeseer", 70.3), ("Pubmed", 79.0)]:
    invoke_skill("paper-reproduction", arxiv="1609.02907", target=row)
```

Output: `outputs/repro-1609.02907/aggregated_table.md`. During Demo, only Cora is run live; the result is merged into the pre-computed table for display.

---

## 5. New Component: `scientific-writing` skill

### 5.1 SKILL.md frontmatter

```yaml
---
name: scientific-writing
description: Use this skill when the user wants to assemble a publication-ready
  LaTeX academic paper from upstream artifacts (literature review, reproduction
  results, data analysis, figures). Compiles to PDF using NeurIPS, ICML, or ACL
  templates. The skill scans /mnt/user-data/workspace/ for upstream outputs
  and generates paper.tex + references.bib + paper.pdf. Not for short reports
  (use Markdown directly) or non-academic writing.
---
```

### 5.2 Six-phase workflow

| Phase | Input | Action | Failure-mode artifact |
|---|---|---|---|
| **1. Plan** | template choice + paper title + 1-sentence stance | Emit `paper_plan.json` | One clarification if missing |
| **2. Collect** | thread workspace + outputs | Index every upstream artifact: `slr-*.md`, `repro-*/report.md`, `analysis-*/`, `figures/*.png` | "No upstream artifacts; run systematic-literature-review etc. first" |
| **3. Outline** | plan + index | LLM emits paragraph-level outline (Abstract/Intro/Related/Method/Experiments/Conclusion) + per-paragraph claim list | Skip section + mark `[TODO]` |
| **4. Draft** | outline + artifacts | Fill `.tex` paragraph-by-paragraph; cite via `\citep{}`; figures via `\includegraphics` | Empty section + reason annotation |
| **5. Bib Assemble** | `slr-*.md` (already contains BibTeX blocks) | Merge → `references.bib`; dedupe; sort by citation key | Report uncited keys |
| **6. Compile + Iterate** | sandbox: `pdflatex → bibtex → pdflatex × 2` | **At most 3 retry rounds**, each round parses `.log` and auto-fixes (undefined ref / missing package / cite key) | "Partial PDF" + `compile_errors.md` |

### 5.3 Output structure

```
/mnt/user-data/outputs/paper/
├── paper.tex              ⭐ editable LaTeX source
├── references.bib
├── paper.pdf              ⭐ what reviewer reads
├── figures/               (copied from upstream)
└── compile_errors.md      (only if compile warnings/errors)
```

### 5.4 Bundled scripts

| Script | Purpose | LOC est |
|---|---|---|
| `artifact_collector.py` | Scan workspace+outputs, index upstream | ~80 |
| `bib_assembler.py` | Merge + dedupe `.bib` | ~100 |
| `compile_latex.py` | Orchestrate pdflatex+bibtex sequence + error parsing + auto-fix | ~200 |
| `latex_log_parser.py` | Extract key errors from LaTeX log | ~80 |

### 5.5 Bundled templates

| Template | Source | Note |
|---|---|---|
| `neurips_2024.tex` | NeurIPS official | **demo default**, most rigorous |
| `icml.tex` | ICML official | |
| `acl.tex` | ACL official | |
| `figure_block.tex` | own | `\input`-able figure block |

### 5.6 LaTeX failure defense (high-score critical)

| Failure | Detection | Auto-fix |
|---|---|---|
| Undefined `\cite{X}` | LaTeX warning `Citation 'X' undefined` | Remove cite, leave `[?]` placeholder |
| Missing package | `! LaTeX Error: File 'X.sty' not found` | Use equivalent macro / sandbox `tlmgr install` |
| Missing BibTeX key | bibtex `couldn't find database` | Drop orphan from references.bib |
| Repeated compile failure | ≥ 3 retries | **Degrade to "naked PDF"**: drop bib + figures, text-only; emit `compile_errors.md` |

**Core promise: the sandbox always produces a PDF (even naked); demo is never empty-handed.**

---

## 6. New Component: `sci-pi` Custom Subagent

### 6.1 `agents/sci-pi/config.yaml`

```yaml
name: sci-pi
description: |
  Principal Investigator agent for end-to-end scientific research lifecycle:
  literature review → paper reproduction → analysis → LaTeX write-up.
  Use when the user wants a full research workflow on a topic or paper.
system_prompt_file: prompt.md
skills:
  - systematic-literature-review
  - academic-paper-review
  - paper-reproduction
  - data-analysis
  - chart-visualization
  - scientific-writing
tools:
  - task
  - bash
  - read_file
  - write_file
  - ls
  - glob
  - web_search
  - web_fetch
model: inherit
max_turns: 200
timeout_seconds: 1800
```

### 6.2 `agents/sci-pi/prompt.md` (system_prompt)

```
You are SciPI, a Principal Investigator agent for end-to-end scientific research.

When given a research goal, follow this lifecycle decision tree:

PHASE A — Lit Review (always for new topic)
  → call systematic-literature-review skill
  → confirm: artifact at outputs/slr-{topic}.md

PHASE B — Paper Selection (if user wants reproduction)
  → present top 3 papers from SLR; ask user to pick OR auto-pick most cited
  → if user gave a specific arxiv id, skip A and B

PHASE C — Reproduction
  → call paper-reproduction skill with selected paper + target metric
  → confirm: artifact at outputs/repro-{id}/report.md + comparison.json

PHASE D — Extension Experiments (optional, only if user requests)
  → call data-analysis + chart-visualization for follow-up
  → artifacts to workspace/analysis-*/

PHASE E — Write-up (always last)
  → call scientific-writing skill
  → confirm: outputs/paper/paper.pdf exists

GRACEFUL DEGRADATION:
- If C fails (reproduction did not converge), still proceed to E with the
  failure report as a "limitations" section. Never block the pipeline.
- If E compile fails, present naked PDF + compile_errors.md to user.
- Never claim success without verifying the artifact exists.

OUTPUT to user at each phase boundary:
- 1 sentence summary of what just completed
- Path to artifact
- "Proceeding to phase X" or "Lifecycle complete"
```

### 6.3 Invocation paths

- **Demo primary path:** user picks `sci-pi` as assistant in Web UI
- **Fallback:** from `lead_agent`, call `task(subagent_type="sci-pi", description="...")`

---

## 7. New Component: Semantic Scholar MCP

### 7.1 Why

DeerFlow's `systematic-literature-review` is arXiv-only by design (per the SKILL.md comment). Adding Semantic Scholar via MCP brings:
- Citation graph traversal (`get_citations`)
- Cross-database search (papers not on arXiv)
- Influence metrics (h-index, citation counts)

### 7.2 Integration

Add to `extensions_config.json`:

```json
{
  "mcpServers": {
    "semantic-scholar": {
      "enabled": true,
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "semantic-scholar-mcp", "run"],
      "env": {
        "S2_API_KEY": "$S2_API_KEY"
      },
      "description": "Semantic Scholar paper search and citation graph"
    }
  }
}
```

(Exact command depends on chosen MCP impl; verified Day 6.)

### 7.3 Risk policy

If S2 MCP integration breaks (R6 in risk register), drop it and cite as future work. Removal does not block any demo path.

---

## 8. Mini Sci-Bench

### 8.1 Five tasks

| # | Task | vanilla | SciDeer | Gap nature |
|---|---|:---:|:---:|---|
| **T1** | "Do an SLR on diffusion models, 10 papers, BibTeX" | ✅ existing | ✅ same | parity (no regression check) |
| **T2** | "Reproduce GCN Cora row of Table 2 from arxiv:1609.02907" | ❌ no skill | ✅ `paper-reproduction` | 🔥 hard gap |
| **T3** | "Analyze attached results.csv and produce a report with charts" | ✅ existing | ✅ same | parity |
| **T4** | "Generate a NeurIPS-style LaTeX paper from artifacts in /uploads" | ❌ no skill | ✅ `scientific-writing` | 🔥 hard gap |
| **T5** | "Full lifecycle on graph neural networks: SLR → reproduce GCN → write paper PDF" | ❌ no orchestrator | ✅ `sci-pi` | 🔥 holistic gap |

T2/T4/T5: vanilla scores 0/0; bar chart visual impact maximised.

### 8.2 Scoring dimensions per task

| Dimension | Range | Source |
|---|---|---|
| Correctness | 0-3 | manual |
| Completeness | 0/1 (artifact exists + structure correct) | **automatic** (runner) |
| Token cost | numeric | **automatic** (DeerFlow `token_usage.enabled`) |
| Wall time | seconds | **automatic** (runner) |
| Quality | 0-3 | manual |

### 8.3 Runner architecture

```
benchmarks/sci_eval/
├── runner.py
├── tasks/
│   ├── t1_slr.yaml ... t5_pipeline.yaml
├── fixtures/                       (csv files for T3, figures for T4)
├── results/
│   ├── vanilla/{task}_{run_id}_{ts}/
│   └── scideer/{task}_{run_id}_{ts}/
├── visualize.py
├── results.csv
└── RESULTS.md
```

Example task yaml:

```yaml
id: t2_repro
description: "Single-result paper reproduction"
prompt: "Reproduce GCN on Cora result from arxiv:1609.02907 (Table 2 row)."
runner_config:
  vanilla:
    assistant_id: lead_agent
  scideer:
    assistant_id: sci-pi
expected_artifacts:
  - path: outputs/repro-1609.02907/report.md
    must_exist: true
  - path: outputs/repro-1609.02907/comparison.json
    must_exist: true
    must_contain_keys: [paper_value, our_value, delta]
auto_score:
  completeness: artifact_check
manual_score: [correctness, quality]
n_runs: 3
timeout_seconds: 1200
```

Runner core (~250 lines):

```python
for task in tasks:
    for config in [vanilla, scideer]:
        for run in range(task.n_runs):
            thread = create_thread()
            send_prompt(thread, task.prompt, assistant=config.assistant_id)
            wait_for_completion(timeout=task.timeout_seconds)
            metrics = collect_metrics(thread)        # tokens, time, artifacts
            score = auto_score(thread, task)         # completeness check
            save_result(config, task, run, metrics, score)
```

### 8.4 Visualizations (PPT-ready)

| Figure | Type | Use |
|---|---|---|
| `fig_correctness.png` | grouped bar (5 tasks × 2 systems) | flagship visual on PPT |
| `fig_radar.png` | radar (5 dimensions) | ablation summary |
| `fig_efficiency.png` | scatter (token cost × wall time) | efficiency commentary |

### 8.5 Run-scale plan

| Dimension | Day 8 minimum | Day 8 stretch |
|---|---|---|
| Tasks | 5 | 5 |
| n_runs / task | **1 (mandatory)** | 3 (ideal) |
| Total runs | 5 × 2 × 1 = 10 | 5 × 2 × 3 = 30 |
| Time budget | ~1.5 h | ~4 h |

---

## 9. Live Demo Flow (5-10 min, default 8-min script)

| Time | Content | Risk | Backup |
|---|---|:---:|---|
| 0:00 - 0:30 | Open: SciDeer 1-line positioning + Web UI screenshot | 🟢 | — |
| 0:30 - 1:00 | Switch to `sci-pi` assistant; intro 6-skill orchestration | 🟢 | — |
| 1:00 - 1:15 | Send demo prompt: full lifecycle on GCN paper | 🟢 | — |
| **1:15 - 4:00** | **Phase C: paper-reproduction (live)** | 🟡 | backup video, same chunk |
|  | 1:15-1:45  agent plan + extract target 81.5% |  |  |
|  | 1:45-2:15  code_resolver hits cache (pygcn) |  |  |
|  | 2:15-3:15  GCN training in sandbox (live log) |  |  |
|  | 3:15-4:00  comparison report (80.2% vs 81.5%) |  |  |
| **4:00 - 6:30** | **Phase E: scientific-writing (live)** | 🟡 | backup video |
|  | 4:00-4:30  artifact_collector reads SLR + repro (SLR pre-run) |  |  |
|  | 4:30-5:30  outline → draft (streaming) |  |  |
|  | 5:30-6:00  bib assemble + first pdflatex (one warning fixed) |  |  |
|  | 6:00-6:30  auto-fix + compile success → PDF appears |  |  |
| 6:30 - 7:00 | Open PDF; **demo C+ trick**: live single-row + offline full table merged | 🟢 | static display |
| 7:00 - 8:00 | Switch to PPT: benchmark bar chart + radar | 🟢 | — |
| 8:00 - 8:30 | Closing: 3-sentence contribution summary | 🟢 | — |

### 9.1 Five-layer demo defense

1. **Sandbox warm-up** — 5 min before demo, run a dummy task → container running
2. **Cache pre-fill** — `~/.scideer/cache/` warmed at end of Day 8
3. **Pre-run artifacts** — T5 SLR + complete Table 2 reproduction pre-computed → in `outputs/`
4. **Backup video** — each phase has a 2x-speed recording (≤ 30 s each, ≥ 4 segments, individually switchable)
5. **Offline fallback** — API key has fallback; full external API outage still completes via cache + pre-runs

### 9.2 Pre-demo checklist (Day 9 morning)

- [ ] `make doctor` passes
- [ ] `sci-pi` assistant visible in Web UI
- [ ] Sandbox container running (`docker ps` shows aio-sandbox)
- [ ] `~/.scideer/cache/` contains pygcn + Cora + MNIST
- [ ] `outputs/` contains pre-run SLR + complete Table 2 markdown
- [ ] Network-down test: paper-reproduction still completes
- [ ] Full demo run-through ≥ 3 times, success rate ≥ 80%
- [ ] Backup videos recorded (≥ 4 segments)

### 9.3 Demo failure decision tree

```
            phase stuck > 30 s
                   │
        ┌──────────┴──────────┐
       yes                    no
        │                  (continue)
   switch to backup video (same chunk)
        │
   [video ends]
        │
   [continue next phase live]
```

---

## 10. Timeline (9 days)

| Day | Date | Phase | Required deliverable | Buffer / stretch |
|---|---|---|---|---|
| **1** | 5/4 | Phase 0 (env) | Server 16 GB upgrade; Python 3.12 + Node 22 + Docker; fork DeerFlow → scideer; `make setup` with Kimi K2.5; `make dev` Web UI accessible; one built-in skill verified | If smooth: start Day 2 tasks early afternoon |
| **2** | 5/5 | Phase 0 (sandbox) | Read backend/CLAUDE.md and key source; build `scideer-sandbox` Docker image (pytorch + torch_geometric + texlive); switch config.yaml to AioSandbox; pre-stage caches; verify GCN training + pdflatex inside sandbox | If image build fails: fallback to skill-internal apt install |
| **3** | 5/6 | Layer 1 (repro 1/2) | `paper-reproduction/SKILL.md` written; `code_resolver.py` + `scale_down.py` + `runner.py` complete; cache-hit GCN-on-Cora runs in sandbox | — |
| **4** | 5/7 | Layer 1 (repro 2/2) | `comparator.py` + `report.md.tmpl` complete; failure-mode tests (OOM/timeout/divergence/cache-miss); end-to-end arxiv:1609.02907 → outputs/repro-1609.02907/ complete | MNIST CNN backup path verification |
| **5** | 5/8 | Layer 1 (writing) | `scientific-writing/SKILL.md` written; `artifact_collector.py` + `bib_assembler.py` + `compile_latex.py` complete; NeurIPS template + 3-round auto-fix + naked PDF degradation; mock-input → paper.pdf produced | **🚩 Layer 1 checkpoint: minimum viable demo path proven** |
| **6** | 5/9 | Layer 2 (orchestrator) | `agents/sci-pi/config.yaml` + `prompt.md` configured; `custom_agents` registered in config.yaml; Semantic Scholar MCP added to `extensions_config.json`; sci-pi end-to-end runs demo prompt | Edge-case fixes |
| **7** | 5/10 | Layer 2 (pipeline + C+ pre-run) | sci-pi full pipeline executed 5 times, flaky steps identified; **C+ pre-run: full Table 2 (Cora + Citeseer + Pubmed) → outputs/**; demo paper bundle verified | Time permitting: ablation data |
| **8** | 5/11 | Layer 3 (benchmark + deploy) | `benchmarks/sci_eval/runner.py` complete; 5 task yamls complete; morning runs minimum 5 × 2 × n_runs=1 = 10; afternoon `visualize.py` produces 3 figures + `RESULTS.md`; cloud Web UI external access verified | n_runs=3 stretch if time |
| **9** | 5/12 | Wrap-up | Morning: pre-demo checklist all green; full demo rehearsal ≥ 3 times, ≥ 80% success; record 4 backup videos; **afternoon: PPT 40-50 min polish**; **evening: Report 8-10 p draft** | Re-record demo screencast if time |

### 10.1 Hard checkpoints (stop-loss)

| CP | Time | If not passed → emergency action |
|---|---|---|
| **CP1** | Day 1 EOD | DeerFlow Web UI + Kimi running. If fails: switch to backup model (DeepSeek / Qwen / OpenRouter) |
| **CP2** | Day 2 EOD | LaTeX compile succeeds inside sandbox. If fails: drop `scientific-writing` PDF goal, output Markdown only |
| **CP3** | Day 5 EOD | Minimum viable demo (repro + write) runs end-to-end. If fails: Day 6-7 freeze on new features, all effort to demo path |
| **CP4** | Day 9 noon | Demo rehearsal success rate ≥ 80%. If fails: switch to all-backup-video presentation |

### 10.2 Team allocation

| Person | Day 1-7 | Day 8-9 |
|---|---|---|
| Jasper | Full-stack coding | Final coding + recording videos + demo presentation |
| Teammate A | Phase 0 research notes (feeds Report sections 1-2) | PPT polish (visualize.py outputs + colour + layout) |
| Teammate B | Benchmark task yaml drafting (Day 6-7 handoff) | Report proofreading + citation normalization |

---

## 11. Risk Register

| # | Risk | P | I | Mitigation |
|---|---|:---:|:---:|---|
| **R1** | paper-reproduction fails live | 🟡 M | 🔴 H | cache pre-warm + backup video + naked report degradation + MNIST CNN swap |
| **R2** | LaTeX repeated compile failure | 🟡 M | 🟡 M | 3-round auto-fix + naked PDF degradation → always produces PDF |
| **R3** | sci-pi orchestrator hang / infinite loop | 🟡 M | 🟡 M | `timeout_seconds: 1800`; explicit graceful degradation in prompt |
| **R4** | Custom Docker image build fails | 🟢 L | 🔴 H | Day 2 reserved fully; fallback to skill-internal apt install |
| **R5** | Kimi K2.5 incompatibility | 🟢 L | 🔴 H | CP1 verification; backup DeepSeek / Qwen / OpenRouter |
| **R6** | Semantic Scholar MCP integration breaks | 🟢 L | 🟢 L | Drop entirely; cite as future work |
| **R7** | Live network outage | 🟢 L | 🔴 H | All deps local-cached; Day 9 offline test |
| **R8** | 16 GB RAM upgrade not approved in time | 🟢 L | 🟡 M | Day 1 first action: ticket; 8 GB degradable (disable LangSmith / lower concurrency) |
| **R9** | Benchmark n_runs=1 lacks statistical power | 🟡 M | 🟢 L | Mark as limitation in Report; T2/T4/T5 are binary capability gaps, statistically insensitive |
| **R10** | 9-day workload overruns | 🟡 M | 🔴 H | CP1-CP4 stop-loss; any CP miss → cut non-core scope |
| **R11** | Demo time overruns 10 min | 🟡 M | 🟡 M | 8-min script with 2-min buffer; if overrunning, skip to PPT |
| **R12** | Reviewer questions novelty | 🟢 L | 🟡 M | T2/T4/T5 vanilla=0 bar chart directly answers; show sci-pi custom_agent mechanism |
| **R13** | PPT/Report rushed | 🟢 L | 🟡 M | Day 9 dedicated to PPT/Report; teammates share load |
| **R14** | LLM API quota exhausted | 🟢 L | 🟡 M | Benchmark uses minimum n_runs; K2.5 unit price is low |

Top 3 priority risks (R1, R2, R3): all covered by "graceful degradation + always produces output" principle.

---

## 12. Deliverables

```
scideer/ (fork of bytedance/deer-flow @ branch scideer-main)
├── skills/custom/
│   ├── paper-reproduction/SKILL.md + scripts/ + templates/
│   └── scientific-writing/SKILL.md + scripts/ + templates/
├── agents/sci-pi/
│   ├── config.yaml
│   └── prompt.md
├── benchmarks/sci_eval/
│   ├── runner.py
│   ├── visualize.py
│   ├── tasks/ (5 yamls)
│   ├── fixtures/
│   ├── results/ (vanilla + scideer)
│   ├── results.csv
│   └── RESULTS.md
├── docker/scideer-sandbox/Dockerfile
├── config.yaml                          (modified)
├── extensions_config.json               (modified)
├── docs/plans/2026-05-03-scideer-design.md     (this document)
├── docs/plans/2026-05-03-scideer-implementation.md   (separate, written by writing-plans)
├── docs/NOTES.md                        (Phase 0 source-reading notes)
├── outputs/                             (demo output examples + pre-runs)
└── README.md                            (with SciDeer badge / motivation / quick start)
```

---

## 13. PPT Structure (40-50 min)

| Slide | Content | Time |
|---|---|---|
| 1 | Title: SciDeer | 1 min |
| 2-3 | Motivation: agent harness + scientific lifecycle gap | 4 min |
| 4 | Related Work: DeerFlow / Claude Code / Open-Source agent harnesses | 3 min |
| 5 | Architecture diagram (Section 3 component map) | 3 min |
| 6 | DeerFlow's existing scientific skills (lit review, paper review, data, charts) | 3 min |
| 7 | New: paper-reproduction skill (workflow + cache strategy + failure modes) | 4 min |
| 8 | New: scientific-writing skill (LaTeX workflow + 3-round retry + naked PDF) | 4 min |
| 9 | New: sci-pi custom subagent (DeerFlow native mechanism, lifecycle decision tree) | 3 min |
| 10 | New: Semantic Scholar MCP (closes the arxiv-only gap) | 2 min |
| 11-12 | **Live Demo** (8 min default, 10 min cap) | 8-10 min |
| 13 | Mini Sci-Bench: 5 tasks design + scoring rubric | 3 min |
| 14 | Benchmark results: bar chart + radar + table | 4 min |
| 15 | Ablation insight: where SciDeer wins (T2/T4/T5) | 2 min |
| 16 | Limitations & Future Work | 2 min |
| 17 | Conclusion | 1 min |
| 18 | Q&A | 5-8 min |

---

## 14. Report Structure (8-10 pages)

1. **Introduction (1 p)** — Agent harness background; scientific research lifecycle gap; SciDeer positioning
2. **Related Work (1 p)** — Agent harness ecosystem; DeerFlow 2.0 (after rewrite); scientific AI tools
3. **System Design (2 p)** — Architecture; the 3 new components; integration points; data flow via thread workspace
4. **Experiments (2-3 p)** — Mini Sci-Bench design; 5 tasks; comparison results; ablation; visualizations
5. **Discussion (1 p)** — Why "fill the gap" beats "from scratch"; limitations (n_runs=1, paper scope, CPU-only sandbox)
6. **Conclusion & Future Work (0.5 p)** — Multi-MCP integration; GPU sandbox; multi-agent ablations
7. **References (0.5 p)**
8. **Appendix** — SKILL.md files; benchmark task yamls; sci-pi prompt; representative LaTeX output

---

## 15. Acceptance Criteria

| Phase | Criterion |
|---|---|
| **Phase 0 (Day 1-2)** | DeerFlow + Kimi running; AioSandbox with custom image working; LaTeX compiles inside sandbox; caches pre-staged |
| **Layer 1 (Day 3-5)** | paper-reproduction produces report.md for GCN-on-Cora end-to-end; scientific-writing produces paper.pdf for mock inputs; full failure-mode coverage |
| **Layer 2 (Day 6-7)** | sci-pi runs full lifecycle from prompt to PDF; C+ Table 2 pre-run artifacts saved; demo paper bundle complete |
| **Layer 3 (Day 8-9)** | Benchmark 5 × 2 × n_runs=1 minimum; 3 PPT-ready figures; cloud Web UI externally reachable; demo rehearsal ≥ 80% success; backup videos recorded |
| **Final (Day 9)** | PPT 40-50 min ready; Report 8-10 p drafted; live demo executable end-to-end |

---

## 16. Glossary

| Term | Meaning |
|---|---|
| **Harness** | Runtime infrastructure that gives agents filesystem, memory, sandbox, tools, skills (DeerFlow's term for itself) |
| **Skill** | Markdown-defined capability module (`SKILL.md` + scripts + templates), loaded progressively by Lead Agent based on task |
| **Custom subagent** | DeerFlow native mechanism (`subagents.custom_agents`) for defining specialized agents with own prompt/tools/skills/model |
| **MCP** | Model Context Protocol; DeerFlow loads MCP servers via `extensions_config.json` |
| **AioSandbox** | DeerFlow's Docker-based isolated execution environment |
| **C+ mode** | Demo strategy: offline pre-run of full table + live single-slice + merged display |
| **Naked PDF** | Degraded LaTeX output (no bib, no figures) used as last-resort fallback when compile repeatedly fails |

---

**End of design document. Next step: invoke `superpowers:writing-plans` skill to convert this design into a detailed implementation plan.**
