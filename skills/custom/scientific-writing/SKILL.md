---
name: scientific-writing
description: Use this skill when the user wants to assemble a publication-ready
  LaTeX academic paper from upstream artifacts produced by other skills
  (literature review via systematic-literature-review, paper reproduction via
  paper-reproduction, data analysis via data-analysis or chart-visualization).
  The skill scans /mnt/user-data/outputs/ and /mnt/user-data/workspace/ for
  upstream artifacts, generates a deterministic LaTeX skeleton, fills sections
  one at a time using the relevant artifacts, assembles references.bib from
  upstream BibTeX blocks, and compiles to PDF inside the sandbox using
  latexmk. Supports generic (default) and NeurIPS templates. Not for short
  reports (use Markdown), single-paper peer review (use academic-paper-review),
  or non-academic prose.
---

# Scientific Writing Skill

## Overview

This skill assembles a publication-ready **LaTeX academic paper** from research
artifacts produced upstream by other skills. It does not invent results,
search the literature, or re-run experiments — it consumes existing artifacts
(SLR markdown reports, paper-reproduction reports, data-analysis CSVs, figures)
and produces `paper.tex`, `references.bib`, and `paper.pdf`.

The workflow is six phases: **plan**, **collect** (scan upstream artifacts),
**skeleton** (deterministic LaTeX skeleton with TODO markers), **per-section
fill** (LLM uses `Edit` to fill each section in turn, reading only the
artifacts whitelisted for that section), **compile** (mandatory bash invocation
of `latexmk` inside the sandbox), and **present** (return the PDF to the user).

**Critical invariant:** the skill never *simulates* compilation. Phase 5
**must** invoke `bash` to run `compile_pdf.sh`. The script has a 3-attempt
retry loop with auto-fixes and a naked-PDF degradation as last-resort, so a
PDF is produced in nearly all error scenarios.

## When to Use This Skill

Use this skill when:

- The user has accumulated upstream artifacts in `/mnt/user-data/outputs/` or
  `/mnt/user-data/workspace/` (typically from `systematic-literature-review`,
  `paper-reproduction`, `data-analysis`, or `chart-visualization`) and now
  wants a single LaTeX paper PDF that consolidates them.
- The user explicitly asks for a "NeurIPS-style", "ICML-style", or "academic
  paper" output (we support **generic** and **NeurIPS** templates).
- The `sci-pi` orchestrator subagent has reached the end of a research
  lifecycle and needs to produce the final write-up.

Do **not** use this skill when:

- The user wants a short report or notes — use Markdown directly.
- The user wants peer review of a single paper — use `academic-paper-review`.
- The user wants a literature survey — use `systematic-literature-review`.
- The user wants non-academic prose (blog post, newsletter, marketing copy).

## Required Inputs

Before starting, the workflow requires three inputs (Phase 1 plan):

| Input | Type | Default | Source |
|---|---|---|---|
| `template` | `generic` or `neurips` | `generic` | user prompt or upstream metadata |
| `title` | string | required | user prompt |
| `stance` | one-sentence claim | required | user prompt |

If any of these is missing from the user's request, ask **one** clarification
question that covers all missing pieces. Do not ask one at a time.

Treat an input as "present" if the user gave it verbatim or if it is
unambiguously derivable from one short noun phrase in their request (e.g.
"GCN reproduction" → title "Reproducing GCN"); otherwise treat it as missing.

## Output Structure

```
/mnt/user-data/outputs/paper/
├── paper.tex              # editable LaTeX source
├── paper.pdf              # final PDF (may be naked-PDF in fallback case)
├── references.bib         # may be empty if no upstream bibtex blocks found
├── figures/               # all upstream figures, copied (only cited ones embed in PDF)
└── compile_errors.md      # always present after compile; documents the path taken
```

## Workflow

The workflow has six phases. Follow them strictly in order. Phases 2, 3, 5 are
**bash-driven** (must invoke the script via the `bash` tool); Phase 4 is
LLM-driven (must use the `Edit` tool, one section at a time).

### Phase 1: Plan

Confirm the three required inputs (template, title, stance). If any is
missing, ask **one** clarification question that bundles all missing items.

Once confirmed, proceed to Phase 2 — do **not** repeat the user's request back
or write a multi-paragraph plan summary. The plan is just the three values.

### Phase 2: Collect upstream artifacts

Run the bundled `collect` subcommand to scan `/mnt/user-data/outputs/` and
`/mnt/user-data/workspace/` for upstream artifacts and bibtex blocks.

```bash
python /mnt/skills/custom/scientific-writing/scripts/generate_latex.py collect \
  --root /mnt/user-data/outputs/ \
  --workspace /mnt/user-data/workspace/ \
  --out /mnt/user-data/workspace/scientific_writing_index.json
```

The script writes a JSON index file listing discovered SLR files, repro
reports, comparison JSONs, analysis directories, figures, and deduped bibtex
entries.

**Read the JSON.** Note especially:

- `summary.bibtex_unique_count` — if 0, you must avoid `\citep{}` calls in
  Phase 4 (the bib will be empty and citations will produce `[?]` in the PDF).
- `summary.figure_count` — figures available for inclusion.
- `summary.repro_count` and `slr_count` — drive whether Method/Experiments and
  Related Work have content to draw from.

If the index is mostly empty (no SLR, no repro, no figures), inform the user:
"I found no upstream artifacts. I can still produce a skeleton paper, but
sections will be mostly TODO placeholders. Continue, or run an upstream skill
first?"

### Phase 3: Generate skeleton

Run the bundled `skeleton` subcommand:

```bash
python /mnt/skills/custom/scientific-writing/scripts/generate_latex.py skeleton \
  --template <generic|neurips> \
  --title "<title from Phase 1>" \
  --stance "<stance from Phase 1>" \
  --index /mnt/user-data/workspace/scientific_writing_index.json \
  --out /mnt/user-data/outputs/paper/
```

This deterministically writes:

- `paper.tex` — six sections, each with `% TODO_<NAME>: <reason>` placeholder.
- `references.bib` — all deduped bibtex entries from upstream artifacts.
- `figures/*` — all upstream figures, copied (referenced in commented-out
  `\includegraphics` lines you will uncomment in Phase 4).

If `references.bib` is empty, the skeleton replaces `\bibliography{references}`
with a `% No bibliography (no upstream bibtex blocks found)` comment line.
This is intentional — do **not** re-add the `\bibliography` call manually,
or the bibtex pass will fail.

Read the resulting `paper.tex` to confirm the structure before Phase 4.

### Phase 4: Per-section fill (LLM, six `Edit` calls)

Use the `Edit` tool **once per section**, in this order:

1. **Introduction** (sources: `outputs/slr-*.md` themes only)
2. **Related Work** (sources: `outputs/slr-*.md` full body)
3. **Method** (sources: `outputs/repro-*/report.md` — Method section primarily,
   plus Setup / Implementation Notes if scale-down decisions are documented there)
4. **Experiments** (sources: `outputs/repro-*/comparison.json`,
   `workspace/analysis-*/*.csv`, `outputs/paper/figures/*` — uncomment the
   relevant `\includegraphics` lines you decide to cite)
5. **Conclusion** (sources: `outputs/repro-*/report.md` Conclusion + `slr-*.md`
   Gaps)
6. **Abstract** (sources: stance hint + the prose you wrote in 1–5; abstract is
   written **last** because it summarizes finished sections)

**Strict rules for Phase 4:**

- One `Edit` per section. Do not batch multiple sections in one Edit call.
- For each section's Edit, **read only the whitelisted artifacts** from the
  list above. Reading figures while writing Methods (or vice versa) leads to
  mixed-up content.
- Replace the `% TODO_<NAME>: <reason>` line with real prose. **Do not** leave
  the TODO marker in place if you have content for that section.
- If a section's source artifacts are missing or empty (e.g. no SLR was run, so
  Related Work has nothing to draw on), keep the `% TODO_<NAME>: ...` comment
  in place. The skeleton will still compile, and the comment documents what
  was missing.
- Use `\citep{key}` for inline citations. The `key` must already exist in
  `references.bib` (you can verify by reading the file, or equivalently by
  checking `summary.bibtex_unique_count == 0` from the Phase 2 index). If
  `references.bib` is empty, **do not** call `\citep{}` — write descriptive
  prose only.

**Per-section length guidance:**

- Abstract: 4–6 sentences, single paragraph.
- Introduction: 1–2 paragraphs (~300–500 words).
- Related Work: 2–3 paragraphs synthesizing themes (not a paper-by-paper
  enumeration).
- Method: 1–2 paragraphs summarizing the original paper's approach + your
  scale-down decisions.
- Experiments: 1–2 paragraphs presenting numbers + 1–3 figures.
- Conclusion: 1 paragraph.

### Phase 5: Compile (MANDATORY bash invocation)

**You must invoke `bash` to run the compile script.** Do not "describe" or
"simulate" the compile; the skill's correctness depends on actual `latexmk`
execution inside the sandbox.

```bash
bash /mnt/skills/custom/scientific-writing/scripts/compile_pdf.sh \
  /mnt/user-data/outputs/paper/
```

The script runs three `latexmk` attempts with sed-based auto-fixes between
attempts (drop missing image refs in attempt 2; drop undefined cites in
attempt 3). If all three fail, it triggers naked-PDF degradation: a stripped
version of the tex (no bibliography, no figures, no cite calls) is generated
and compiled. If naked compilation also fails, the script exits 1; otherwise
it exits 0 and `paper.pdf` exists.

After the script returns, **read `compile_errors.md`** to understand which
path was taken. Possible outcomes:

| Outcome | What to tell the user |
|---|---|
| Success on attempt 1 | "Paper compiled cleanly." |
| Success on attempt 2 | "Paper compiled after dropping a missing figure reference. See compile_errors.md for details." |
| Success on attempt 3 | "Paper compiled after dropping an undefined citation. See compile_errors.md." |
| Naked PDF | "Compilation hit unrecoverable errors; produced a naked PDF (no figures, no bibliography). The original paper.tex is preserved for manual debugging." |
| Failure (exit 1) | "Compilation failed even in naked mode. paper.tex and references.bib are preserved on disk; see compile_errors.md for the diagnostic." |

### Phase 6: Present to user

Use the `present_files` tool to surface `paper.pdf`:

```
present_files paths=["/mnt/user-data/outputs/paper/paper.pdf"]
```

Then write a short chat preview (do **not** dump the full PDF text):

1. Title (one line)
2. Abstract (verbatim, the paragraph you wrote in Phase 4)
3. Path summary: `paper.tex`, `paper.pdf`, `references.bib` locations
4. If any section in `paper.tex` still contains a `% TODO_*` marker
   (i.e. you couldn't fill it because the source artifact was missing),
   list those sections in the preview and name the missing source. Example:
   "Related Work and Method are placeholders because no SLR or repro
   artifacts were available."
5. If `compile_errors.md` indicates a non-vanilla path was taken, honestly
   note it: e.g. "Note: the PDF was produced via naked-PDF fallback after
   3 compile failures. See compile_errors.md for details."

## Failure Modes

The skill is designed to never fail silently. Every failure mode produces a
viewable artifact.

| Failure | Phase | Detection | Result |
|---|---|---|---|
| Missing user input | 1 | LLM check | one clarification question; loop until satisfied |
| No upstream artifacts | 2 | empty index | proceed; bib is empty; SKILL workflow tells the LLM to skip `\citep{}` |
| Template file missing | 3 | filesystem check | fall back to `generic.tex` |
| Empty bib | 3 | `bibtex_unique_count == 0` | empty `references.bib`; `\bibliography` line replaced by a `% No bibliography` comment in the skeleton |
| Missing figure file referenced in Phase 4 | 5 | latexmk error | attempt 2 sed comments out the `\includegraphics` line |
| Undefined cite key | 5 | latexmk warning | attempt 3 sed replaces `\citep{key}` with `[?]` |
| LLM left a section as `% TODO_*` | 4–5 | not detected; intentionally allowed | the TODO comment compiles to nothing in the PDF; the section appears as a heading with no body |
| Compile fails 3 times | 5 | retry loop exhausted | naked PDF generated |
| Naked also fails | 5 | naked compile error | `compile_errors.md` written; exit 1; LLM informs user `paper.tex` and `references.bib` are still on disk |

## Examples

### Example 1: Full lifecycle finish (sci-pi orchestrator)

User asked the `sci-pi` agent for a full GCN-on-Cora research pipeline. SLR
and paper-reproduction have already produced `outputs/slr-graph-neural-networks-20260506.md`
and `outputs/repro-1609.02907/{report.md,comparison.json,figures/training.png}`.

Workflow:

1. **Phase 1**: User said "NeurIPS template, title 'Reproducing GCN on Cora',
   stance 'we confirm 80% accuracy'." All three inputs present; no clarification.
2. **Phase 2**: `collect` finds 1 SLR, 1 repro, 1 figure, 12 bib entries.
3. **Phase 3**: `skeleton --template neurips` writes `paper.tex` with 6 TODO
   sections + `references.bib` (12 entries) + `figures/training.png` copy.
4. **Phase 4**: 6 `Edit` calls in order (Intro → Related → Method → Experiments
   → Conclusion → Abstract).
5. **Phase 5**: `compile_pdf.sh` succeeds on attempt 1.
6. **Phase 6**: `present_files paper.pdf`; chat preview shows title +
   abstract + path summary.

### Example 2: Standalone use, missing SLR

User has only a CSV they ran through `data-analysis`; no SLR and no repro.

Workflow:

1. **Phase 1**: User said "generic template, title 'Sales Analysis Q1',
   stance 'we identified a 15% drop'."
2. **Phase 2**: `collect` finds 0 SLR, 0 repro, 2 figures (from analysis), 0
   bib entries.
3. The LLM informs the user: "Found no SLR or repro artifacts; Related Work
   and Method sections will remain as TODO placeholders. Continue?"
4. **Phase 3**: `skeleton --template generic` produces a paper.tex with
   commented-out `\bibliography` line (since bib is empty) and figure includes
   for the 2 analysis figures.
5. **Phase 4**: LLM fills only Abstract + Introduction + Experiments +
   Conclusion. Related Work and Method retain `% TODO_*` markers.
6. **Phase 5**: Compile succeeds (TODOs are LaTeX comments, they don't break
   anything).
7. **Phase 6**: PDF shows title + filled sections; Related Work and Method
   appear as headings with no body. The chat preview honestly notes:
   "Related Work and Method are placeholders because no SLR or repro
   artifacts were available."

### Example 3: Compile failure → naked PDF

LLM accidentally inserted a `\badmacro` somewhere in Phase 4. All three
attempts fail (sed fixes only target missing images and undefined cites,
not generic syntax errors).

Workflow continues:

1. `compile_pdf.sh` triggers naked-PDF degradation.
2. `paper_naked.tex` is generated (no bib, no figures, no cite calls).
3. `latexmk paper_naked.tex` succeeds.
4. `paper_naked.pdf` is copied to `paper.pdf`.
5. `compile_errors.md` documents all three attempts + the naked fallback.
6. The chat preview honestly notes: "PDF was produced via naked-PDF fallback
   after 3 compile failures. The original paper.tex is preserved at
   `outputs/paper/paper.tex` for manual debugging. See `compile_errors.md`
   for the diagnostic."

## Notes

- **Compilation is mandatory bash.** Phase 5 must invoke `bash` to run
  `compile_pdf.sh`. Do not paraphrase the script's behavior, do not "imagine"
  what the PDF will look like, do not skip this step. The skill's value is
  precisely that it produces a real compiled PDF, not an LLM-narrated preview.
- **One `Edit` per section in Phase 4.** Batching multiple sections in one
  `Edit` call defeats the per-section artifact whitelist, which is the main
  defense against content cross-contamination.
- **Write Abstract last.** It summarizes the other sections; writing it first
  produces stale claims that don't match what was actually written in Methods
  and Experiments.
- **Default template is `generic`.** Use `neurips` only when the user
  explicitly requests it or when an upstream skill has set NeurIPS metadata.
- **The skill does not do literature review or experiments.** If the user
  wants those, route to `systematic-literature-review` or
  `paper-reproduction` first.
- **`references.bib` is built from upstream BibTeX blocks only.** The skill
  never queries arXiv at compile time. If a citation key is needed but missing,
  the workflow accepts a `[?]` placeholder rather than risking a network call
  during the demo.
- **Figures are copied wholesale in Phase 3.** Unused figures don't bloat the
  PDF (LaTeX only embeds `\includegraphics`-referenced images), so the
  Phase 4 LLM can pick from the full set without re-running collect.
- **Self-test:** the script bundles `python generate_latex.py --selftest` for
  development and CI. The `--selftest` mode runs internal `_test_*` functions
  using temporary directories and does not touch real artifacts.
