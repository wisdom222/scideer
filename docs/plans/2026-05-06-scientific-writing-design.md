# `scientific-writing` Skill + Libra Sandbox Image — Design Document

> Track: skill (`skills/custom/scientific-writing/`) + Docker image (`docker/scideer-sandbox/`)
> Date: 2026-05-06
> Author: Jasper (with Claude Code)
> Status: brainstormed and approved 2026-05-06; supersedes Section 5 of `2026-05-03-scideer-design.md` for `scientific-writing` specifics
> Companion track: `paper-reproduction` skill (out of scope here)

---

## 0. Context

This document refines Section 5 (`scientific-writing` skill) and Section 3.3 (custom sandbox image) of the parent SciDeer design (`docs/plans/2026-05-03-scideer-design.md`) into an implementation-ready spec. The parent design fixed the workflow shape (6 phases, output structure, failure-mode policy) and the deliverables list. This document locks down:

- the **shape of the two scripts** (`generate_latex.py` CLI + `compile_pdf.sh` retry loop)
- the **content of the two templates** (`generic.tex`, `neurips.tex`)
- the **per-section LLM workflow** that operates on the deterministic skeleton
- the **Dockerfile** layer set + smoke test
- the **delivery boundary**: zero modification to existing files in the repo; `config.yaml` patch is delivered as a snippet inside `docker/scideer-sandbox/README.md`

It does **not** attempt to redesign the parent decisions (template list, output paths, sandbox provider choice).

---

## 1. Scope

### 1.1 In scope

- `skills/custom/scientific-writing/SKILL.md` — workflow definition
- `skills/custom/scientific-writing/scripts/generate_latex.py` — multi-subcommand CLI (`collect`, `skeleton`, `naked`)
- `skills/custom/scientific-writing/scripts/compile_pdf.sh` — 3-attempt retry + naked-PDF degradation
- `skills/custom/scientific-writing/templates/generic.tex` — default minimal-package template
- `skills/custom/scientific-writing/templates/neurips.tex` — simplified NeurIPS-style clone (no external `.sty`)
- `docker/scideer-sandbox/Dockerfile` — `aio-sandbox` + texlive layers
- `docker/scideer-sandbox/README.md` — build, smoke test, `config.yaml` patch snippet, troubleshooting

### 1.2 Out of scope (delivered by other tracks or skipped)

- `paper-reproduction` skill (separate track)
- `agents/sci-pi/` orchestrator (separate track)
- `benchmarks/sci_eval/` (separate track)
- `extensions_config.json` (skill is auto-discovered via filesystem scan; no registration needed)
- Image build execution (the user runs `docker build` on the server; this track only writes the Dockerfile)
- Modifying `frontend/`, `backend/`, `agents/`, `benchmarks/`, other `skills/`

### 1.3 Boundary contract

- The skill **must not** modify any file outside `skills/custom/scientific-writing/` and `docker/scideer-sandbox/`.
- `config.yaml` is **not created** in the repo. The patch snippet is delivered inside `docker/scideer-sandbox/README.md` for the user to merge manually on the server.

---

## 2. Architecture

### 2.1 File layout

```
skills/custom/scientific-writing/
├── SKILL.md                       # workflow definition (LLM-facing)
├── scripts/
│   ├── generate_latex.py          # ~280 LOC, Python stdlib only
│   └── compile_pdf.sh             # ~80 LOC, bash
└── templates/
    ├── generic.tex                # ~70 LOC
    └── neurips.tex                # ~110 LOC

docker/scideer-sandbox/
├── Dockerfile                     # ~30 LOC, FROM aio-sandbox + texlive layers
└── README.md                      # ~80 LOC, build + config patch + troubleshooting
```

### 2.2 Workflow (six phases)

| Phase | Driver | Produces | Artifacts read | Failure handling |
|---|---|---|---|---|
| 1. Plan | LLM (SKILL workflow) | inferred `template`, `title`, `stance` | user prompt | one (and only one) clarification question if any field missing |
| 2. Collect | `bash` → `generate_latex.py collect` | `workspace/scientific_writing_index.json` | `outputs/slr-*.md`, `outputs/repro-*/{report.md,comparison.json}`, `workspace/analysis-*/`, all `figures/*.{png,pdf,jpg}` | empty index → continue with empty bib; SKILL workflow informs LLM to omit `\citep{}` calls in that case |
| 3. Skeleton | `bash` → `generate_latex.py skeleton` | `outputs/paper/{paper.tex, references.bib, figures/}` | template + index | template not found → fall back to `generic`; bib empty → emit `% No bibliography ...` line |
| 4. Per-section fill | LLM (`Edit` tool, six sequential edits) | filled `paper.tex` | per-section whitelist (see 2.3) | section fails → keep `% TODO_*` marker, continue to next section |
| 5. Compile | `bash` → `compile_pdf.sh outputs/paper/` | `paper.pdf`, `compile_errors.md` | `paper.tex`, `references.bib` | three retry attempts with sed-based auto-fixes, then naked-PDF degradation (see 2.6) |
| 6. Present | LLM | chat preview + `present_files paper.pdf` | `paper.pdf` | naked-PDF case → preview text honestly notes the degradation |

The terminal state is `outputs/paper/paper.pdf` plus `outputs/paper/paper.tex` editable source.

### 2.3 Per-section artifact whitelist (Phase 4)

| Section | Allowed artifacts | Rationale |
|---|---|---|
| Abstract | stance hint + Conclusion (after it's written) | abstract is a synthesis, written last in practice but placed first |
| Introduction | `outputs/slr-*.md` (themes only) | motivation; cite key references via `\citep{}` |
| Related Work | `outputs/slr-*.md` (full) | thematic synthesis; if bib empty, prose-only with inline `% needs citation` markers |
| Method | `outputs/repro-*/report.md` (Method section) | original-paper method + scale-down decisions |
| Experiments | `outputs/repro-*/comparison.json`, `workspace/analysis-*/*.csv`, `outputs/paper/figures/*` | quantitative results + figure inclusion |
| Conclusion | `outputs/repro-*/report.md` (Conclusion), `outputs/slr-*.md` (Gaps) | contribution + limitations + future work |

The skill's SKILL.md instructs the LLM to use `Edit` once per section, reading only the whitelisted artifacts for that section. This is prompt engineering — the harness does not enforce it — but the workflow text is written to make violations visibly inconsistent.

### 2.4 Skeleton output (deterministic, by `generate_latex.py skeleton`)

The skeleton consists of:
- a complete LaTeX preamble appropriate to the chosen template
- six `\section{...}` blocks, each containing a single-line `% TODO_<NAME>: <reason describing the source>` comment as placeholder content
- a `{{FIGURE_INCLUDES}}` block, expanded to a list of **commented-out** `\includegraphics` lines (one per figure copied to `outputs/paper/figures/`); the LLM uncomments the ones it cites in Experiments
- a `{{BIBLIOGRAPHY_LINE}}` block, expanded to either `\bibliographystyle{plain}\n\bibliography{references}` (if bib non-empty) or a single comment line
- a `references.bib` file with all deduplicated bibtex blocks scraped from upstream artifacts
- a `figures/` directory with all upstream figures copied (cheap, deterministic; unused figures don't bloat the PDF since unreferenced images are not embedded)

Critically: the skeleton is structurally valid LaTeX from the moment `generate_latex.py skeleton` exits. Even if Phase 4 leaves every section as `% TODO_*` (worst case), Phase 5 still compiles into a valid PDF showing only the title and section headers.

### 2.5 Naked-PDF degradation (last-resort)

`generate_latex.py naked` produces `paper_naked.tex` from `paper.tex` via regex transforms:

1. comment out `\bibliography{...}` and `\bibliographystyle{...}` (prefix `% NAKED: `)
2. replace each `\includegraphics[...]{...}` with the literal string `\textit{[Figure omitted in naked-PDF degradation]}`
3. replace each `\citep{...}` and `\cite{...}` (single- or multi-key) with `[?]`
4. preserve `% TODO_*` comments so the reviewer sees which sections were never filled

The original `paper.tex` is **not modified** (so the user can hand-debug it). On naked success, `paper_naked.pdf` is copied to `paper.pdf`.

### 2.6 Compile retry loop (`compile_pdf.sh`)

| Attempt | Pre-action | Compile command | Success criterion |
|---|---|---|---|
| 1 | none | `latexmk -pdf -interaction=nonstopmode -file-line-error paper.tex` | exit 0 |
| 2 | sed: comment out `\includegraphics` lines whose target file is reported missing in `paper.log` | same | exit 0 |
| 3 | sed: replace `\citep{X}`/`\cite{X}` → `[?]` for each key reported "undefined" in `paper.log` | same | exit 0 |
| Naked | `python generate_latex.py naked --tex paper.tex --out paper_naked.tex` | `latexmk -pdf paper_naked.tex` then `cp paper_naked.pdf paper.pdf` | exit 0 if naked compiles |

`compile_errors.md` always exists after the script runs. It records which path was taken and (if attempts ≥ 2 ran) the parsed errors. Exit 0 means a `paper.pdf` exists somewhere on the success ladder; exit 1 means even naked failed and the user must hand-debug.

Attempts 2 and 3 are **destructive** to `paper.tex` (modifications stick). Naked is non-destructive (writes a new file). This split reflects intent: attempts 2–3 fix things that "should not have been there" (broken references), naked is a global degradation that the user shouldn't lose their original to.

---

## 3. Script Specifications

### 3.1 `generate_latex.py` — CLI shapes

```
generate_latex.py collect --root <outputs-dir> [--workspace <workspace-dir>] [--out <jsonpath>]

  Walks --root for slr-*.md, repro-*/, and figures.
  Walks --workspace for analysis-*/ and figures.
  Parses ```bibtex fenced blocks from all discovered .md files;
  dedupes by entry key (later occurrences override earlier).
  Writes JSON to --out (default: <workspace>/scientific_writing_index.json).

generate_latex.py skeleton --template {generic|neurips} --title "<str>" --stance "<str>" --index <jsonpath> --out <paperdir>

  Loads templates/<template>.tex.
  Substitutes {{TITLE}}, {{AUTHORS}} (default empty), {{DATE}} (today, ISO),
  {{STANCE_HINT}} (injected into Abstract TODO comment),
  {{FIGURE_INCLUDES}} (commented-out \includegraphics lines, one per figure),
  {{BIBLIOGRAPHY_LINE}}.
  Writes <paperdir>/paper.tex, <paperdir>/references.bib, <paperdir>/figures/*.
  Prints one-line summary to stdout.

generate_latex.py naked --tex <paperdir>/paper.tex --out <paperdir>/paper_naked.tex

  Reads --tex, applies regex degradation transforms (see 2.5),
  writes --out. Original --tex is not modified.
```

**Implementation constraints:**
- Python standard library only (no jinja2, no pyyaml). Templates use `{{NAME}}` markers replaced by `str.replace`. The marker syntax does not collide with LaTeX `{}`.
- All paths are passed via CLI flags; no env vars, no config files.
- All filesystem operations are idempotent (rerunning `skeleton` overwrites `paper.tex` and `references.bib`; figures are re-copied).
- BibTeX parser is regex-based: matches `\n@(\w+)\s*\{\s*([^,]+)\s*,\s*` to extract entry type and key, then balances braces to capture the full entry. Good enough for arXiv-format entries; not a general bib parser.

### 3.2 `compile_pdf.sh` — bash structure

```
Usage: compile_pdf.sh <paper-dir>

Behavior:
  cd <paper-dir>
  for attempt in 1, 2, 3:
    parse paper.log if attempt > 1 and apply sed fix
    run latexmk; if success → exit 0 with note in compile_errors.md
  call generate_latex.py naked; run latexmk on paper_naked.tex
  if naked succeeds → cp paper_naked.pdf paper.pdf; exit 0 with naked note
  else → exit 1 with full diagnostic in compile_errors.md
```

Implementation notes:
- `set -u` (catch unset vars) but not `-e` (we control error paths)
- All `latexmk` invocations use `-pdf -interaction=nonstopmode -file-line-error` (no `-halt-on-error`; we want latexmk to plow through warnings and produce a PDF where possible)
- Per-attempt log saved as `compile_attempt_N.log` for forensic analysis
- The script locates `generate_latex.py` via `dirname $(readlink -f $0)` — works regardless of where it's invoked from

### 3.3 `templates/generic.tex` — package set

| Package | Purpose | Provided by |
|---|---|---|
| `inputenc` (utf8) | UTF-8 source files | texlive-latex-base |
| `amsmath` | math macros | texlive-latex-base |
| `graphicx` | `\includegraphics` | texlive-latex-base |
| `hyperref` | clickable links | texlive-latex-recommended |
| `natbib` | `\citep` / `\citet` | texlive-latex-recommended |
| `geometry` | margin control | texlive-latex-recommended |

All six packages are pulled in by `texlive-latex-extra` (which depends on `texlive-latex-recommended` which depends on `texlive-latex-base`).

### 3.4 `templates/neurips.tex` — additions over generic

- `\documentclass[10pt,letterpaper]{article}` (vs `11pt,a4paper`)
- additional package `titlesec` (texlive-latex-extra) for section heading style tweaks
- redefined `\@maketitle` for centered title block resembling NeurIPS layout
- `geometry` margins set to `1.25in` (vs `1in`)
- `hyperref` colors set to subdued (`linkcolor=black,citecolor=black,urlcolor=blue`)
- otherwise identical TODO/section structure to `generic.tex` so `generate_latex.py` substitution logic handles both uniformly

No external `.sty` is required. All packages are in `texlive-latex-extra`.

---

## 4. Docker Image (`libra-sandbox:latest`)

### 4.1 Dockerfile shape

```
FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
USER root
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        texlive-latex-extra \
        texlive-fonts-recommended \
        texlive-bibtex-extra \
        latexmk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN pdflatex --version > /dev/null && \
    bibtex --version > /dev/null && \
    latexmk --version > /dev/null
LABEL org.opencontainers.image.description="..."
LABEL org.opencontainers.image.source="..."
```

The smoke-test `RUN` line forces `docker build` to fail if any binary is missing — earlier failure than discovering it at skill-execution time.

### 4.2 Image size budget

| Layer | Approximate added size |
|---|---|
| base aio-sandbox | ~3.0 GB |
| texlive-latex-extra (pulls -recommended, -base) | ~1.0 GB |
| texlive-fonts-recommended | ~0.3 GB |
| texlive-bibtex-extra | ~0.05 GB |
| latexmk | ~0.005 GB |
| **Total** | **~4.4 GB** |

This is well under `texlive-full` (which is ~4 GB on its own, total image ~7 GB). Acceptable per parent design's "image size control" requirement.

### 4.3 USER context risk

The base image's default USER is unknown without inspection. The Dockerfile sets `USER root` for the apt install and does not reset. If the base image expects to run skills as a non-root user, this may surface as permission issues at skill-execution time (e.g. `figures/` directory writes failing).

**Mitigation:** the README has a Troubleshooting entry specifying the symptom and the fix (`RUN chown -R <user>:<user> /home/<user>` after the texlive layer). The user verifies on first build via `docker run --rm libra-sandbox:latest whoami`.

### 4.4 `config.yaml` patch snippet (delivered in README)

```yaml
sandbox:
  use: deerflow.community.aio_sandbox:AioSandboxProvider
  image: libra-sandbox:latest
  port: 8080
  replicas: 3
  # mounts:
  #   - host_path: /home/<user>/.scideer/cache
  #     container_path: /mnt/scideer-cache
  #     read_only: true
```

The README explicitly instructs the user to **replace** the existing `sandbox:` block (typically `LocalSandboxProvider` from `config.example.yaml`), not append.

---

## 5. Failure Modes (consolidated)

| Failure | Phase | Detection | Resulting artifact |
|---|---|---|---|
| Missing user input (template/title/stance) | 1 | LLM check | one clarification question; loop until satisfied |
| No upstream artifacts | 2 | empty `index.json` | proceed with empty bib; SKILL workflow tells LLM to skip `\citep{}` |
| Template file missing | 3 | filesystem check | fall back to `generic.tex` |
| Empty bib | 3 | `bibtex_unique_count == 0` | `references.bib` is empty file; skeleton omits `\bibliography` |
| Missing figure file referenced in Phase 4 | 5 | latexmk error | attempt 2 sed comments out the line |
| Undefined cite key | 5 | latexmk warning | attempt 3 sed replaces with `[?]` |
| LLM left a section as `% TODO_*` | 4–5 | not detected; intentionally allowed | the TODO comment compiles to nothing in the PDF (it's just a comment); section appears as a heading with no body |
| Compile fails 3 times | 5 | retry loop exhausted | naked PDF generated |
| Naked also fails | 5 | naked compile error | `compile_errors.md` written; exit 1; SKILL workflow informs user `paper.tex` and `references.bib` are still on disk for manual debug |

The workflow's invariant: **if Phase 5 runs at all, either `paper.pdf` exists on disk or the user is honestly told why not, with full diagnostic.**

---

## 6. Acceptance Criteria

- `skills/custom/scientific-writing/SKILL.md` parses (YAML frontmatter valid, body markdown well-formed); body explicitly states the bash-call requirement for `compile_pdf.sh` so the LLM cannot hallucinate a "virtual compile".
- `generate_latex.py collect/skeleton/naked` each work standalone (testable from CLI) using the standard library only.
- `generate_latex.py skeleton` produces a `paper.tex` that compiles to a valid (if mostly empty) PDF when fed through `compile_pdf.sh` — even if every section is still `% TODO_*`.
- `compile_pdf.sh` returns exit 0 in all of: vanilla success, attempt-2 success, attempt-3 success, naked success. Returns exit 1 only if naked fails.
- `Dockerfile` builds without warnings on a Linux host; the smoke-test `RUN` succeeds.
- `README.md` contains the exact `config.yaml` patch snippet and a working `docker build` invocation.
- All deliverables fit the file count contract: 6 files, listed in §2.1.
- Zero modification to `frontend/`, `backend/`, `agents/`, `benchmarks/`, other `skills/`, `config.yaml`, `extensions_config.json`.

---

## 7. Open Questions Deferred to Implementation

- Exact NeurIPS-style spacing values in `neurips.tex` (mimicked by eyeballing the official `neurips_2024.sty`; will iterate during implementation if the rendered PDF looks too off).
- Whether `texlive-bibtex-extra` is strictly necessary (can be dropped if the image-size budget tightens; base bibtex is in `texlive-binaries`).
- Whether `compile_pdf.sh` attempt-2 sed regex correctly matches `\includegraphics` with various optional arguments (`[width=...]`, `[scale=...]`, multi-line). Will be verified during implementation against representative outputs from `chart-visualization` and `paper-reproduction`.

---

## 8. Next Step

Invoke `superpowers:writing-plans` skill to convert this design into a step-by-step implementation plan covering both tracks (skill files + Dockerfile + README).

---

**End of design document.**
