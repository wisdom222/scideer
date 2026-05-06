# scientific-writing Skill + libra-sandbox Image Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a `scientific-writing` skill that turns upstream research artifacts into a compiled LaTeX PDF inside the DeerFlow sandbox, plus the custom Docker image that provides the LaTeX toolchain.

**Architecture:** Two scripts (Python CLI + bash retry loop) operating on a deterministic LaTeX skeleton produced from a JSON artifact index. The skeleton is filled per-section by the LLM via the `Edit` tool, then compiled via `latexmk` in 3 retry rounds with naked-PDF degradation as last-resort. A custom Docker image extends the official AIO sandbox with texlive (~+1.4 GB).

**Tech Stack:** Python 3 (stdlib only — no pip deps), bash, LaTeX (`latexmk` + `texlive-latex-extra` + `texlive-fonts-recommended` + `texlive-bibtex-extra`), Docker (FROM `enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest`).

**Reference design:** [`2026-05-06-scientific-writing-design.md`](2026-05-06-scientific-writing-design.md). Read it before each task.

**Repo boundaries:** Only `skills/custom/scientific-writing/` and `docker/scideer-sandbox/` may be created/modified. Zero changes to `frontend/`, `backend/`, `agents/`, `benchmarks/`, other `skills/`, `config.yaml`, `extensions_config.json`.

**Git policy (from user prompt):** No `git push --force`, no `git commit --amend`. Final commit step is gated on explicit user approval — do **not** commit autonomously between tasks.

**TDD via `--selftest`:** Because the deliverable contract caps the file count at 7 (no separate `tests/` directory), tests for `generate_latex.py` are written as functions inside the script itself, gated by `python generate_latex.py --selftest`. This preserves TDD discipline without adding files outside the skill directory.

---

## Task 0: Read the design document

**Step 1:** Read `docs/plans/2026-05-06-scientific-writing-design.md` end-to-end. Note especially:
- §2.4 Skeleton output structure
- §2.5 Naked-PDF transforms (regex semantics)
- §2.6 Compile retry table
- §3.1 CLI shapes
- §3.3 Package set for `generic.tex`
- §4.1 Dockerfile shape
- §5 Failure mode matrix

**Step 2:** Verify current repo state. Run:
```bash
ls -la "D:/6725_GroupProject/scideer/skills/" && \
ls -la "D:/6725_GroupProject/scideer/docker/" && \
[ -f "D:/6725_GroupProject/scideer/config.yaml" ] && echo "config.yaml EXISTS" || echo "config.yaml ABSENT"
```
Expected: `skills/public/` exists, `skills/custom/` does not exist, `docker/` has `docker-compose*.yaml` + `nginx/` + `provisioner/` (no `scideer-sandbox/`), `config.yaml ABSENT`. If anything differs, stop and reconcile with the user before proceeding.

---

## Task 1: Create skill directory layout

**Files:**
- Create: `skills/custom/scientific-writing/` (directory)
- Create: `skills/custom/scientific-writing/scripts/` (directory)
- Create: `skills/custom/scientific-writing/templates/` (directory)
- Create: `docker/scideer-sandbox/` (directory)

**Step 1:** Create the four directories. Bash:
```bash
mkdir -p \
  "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts" \
  "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/templates" \
  "D:/6725_GroupProject/scideer/docker/scideer-sandbox"
```

**Step 2:** Verify with `ls`. Expected: all four paths now exist as empty directories.

---

## Task 2: Scaffold `generate_latex.py` with `--selftest` harness

**Files:**
- Create: `skills/custom/scientific-writing/scripts/generate_latex.py`

**Step 1:** Write the file with this content (no implementation yet — just argparse skeleton, three subcommand stubs that raise `NotImplementedError`, and the `--selftest` harness that discovers and runs `_test_*` functions in module scope):

```python
#!/usr/bin/env python3
"""
generate_latex.py — multi-subcommand CLI for the scientific-writing skill.

Subcommands:
  collect   — scan upstream artifacts, emit JSON index
  skeleton  — render LaTeX skeleton + references.bib + figures/
  naked     — produce paper_naked.tex (degraded PDF source)

Self-test:
  python generate_latex.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path
from typing import Any


# ---------- Subcommand: collect ----------

def cmd_collect(args: argparse.Namespace) -> int:
    raise NotImplementedError("cmd_collect not implemented yet")


# ---------- Subcommand: skeleton ----------

def cmd_skeleton(args: argparse.Namespace) -> int:
    raise NotImplementedError("cmd_skeleton not implemented yet")


# ---------- Subcommand: naked ----------

def cmd_naked(args: argparse.Namespace) -> int:
    raise NotImplementedError("cmd_naked not implemented yet")


# ---------- Self-test harness ----------

def run_selftest() -> int:
    """Discover and run _test_* functions in module scope."""
    g = globals()
    test_names = sorted(name for name in g if name.startswith("_test_") and callable(g[name]))
    if not test_names:
        print("No tests found.", file=sys.stderr)
        return 1
    failures = 0
    for name in test_names:
        try:
            g[name]()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(test_names) - failures}/{len(test_names)} tests passed.")
    return 0 if failures == 0 else 1


# ---------- argparse entry ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="generate_latex.py")
    p.add_argument("--selftest", action="store_true", help="Run internal self-tests and exit")
    sub = p.add_subparsers(dest="cmd")

    c = sub.add_parser("collect", help="Scan artifacts, emit JSON index")
    c.add_argument("--root", required=True, help="outputs/ directory")
    c.add_argument("--workspace", default=None, help="workspace/ directory (optional)")
    c.add_argument("--out", default=None, help="JSON output path (default: <workspace>/scientific_writing_index.json)")

    s = sub.add_parser("skeleton", help="Render LaTeX skeleton")
    s.add_argument("--template", choices=["generic", "neurips"], default="generic")
    s.add_argument("--title", required=True)
    s.add_argument("--stance", required=True)
    s.add_argument("--index", required=True, help="JSON path produced by `collect`")
    s.add_argument("--out", required=True, help="output paper directory (will be created)")
    s.add_argument("--authors", default="")
    s.add_argument("--templates-dir", default=None, help="override default templates location")

    n = sub.add_parser("naked", help="Produce naked (degraded) tex")
    n.add_argument("--tex", required=True, help="input paper.tex")
    n.add_argument("--out", required=True, help="output paper_naked.tex")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.selftest:
        return run_selftest()
    if args.cmd == "collect":
        return cmd_collect(args)
    if args.cmd == "skeleton":
        return cmd_skeleton(args)
    if args.cmd == "naked":
        return cmd_naked(args)
    build_parser().print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2:** Verify the file is syntactically valid:
```bash
python -m py_compile "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py"
```
Expected: no output, exit 0.

**Step 3:** Verify `--selftest` runs:
```bash
python "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py" --selftest
```
Expected: `No tests found.` printed, exit 1. (No tests exist yet — that's correct.)

**Step 4:** Verify help works:
```bash
python "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py" --help
```
Expected: usage text listing `collect`, `skeleton`, `naked` subcommands.

---

## Task 3: TDD — `collect` subcommand

**Files:**
- Modify: `skills/custom/scientific-writing/scripts/generate_latex.py`

### Step 1 (RED): add `_test_collect_*` functions

Insert these test functions above the `# ---------- Self-test harness ----------` line. They use `tempfile.TemporaryDirectory` to build mock `outputs/` and `workspace/` trees, invoke `cmd_collect` via the parser, and assert on the produced JSON.

```python
# ---------- Tests (run via --selftest) ----------

def _make_temp_outputs(root: Path) -> None:
    """Build a representative outputs/ tree for collect tests."""
    (root / "slr-diffusion-models-20260506.md").write_text(
        "# SLR\n\nSome content.\n\n```bibtex\n"
        "@misc{vaswani2017attention, title={Attention}, author={Vaswani et al.}, year={2017}}\n"
        "```\n", encoding="utf-8")
    repro = root / "repro-1609.02907"
    (repro / "figures").mkdir(parents=True)
    (repro / "report.md").write_text(
        "# Repro\n\n```bibtex\n@article{kipf2017semi, title={GCN}, year={2017}}\n```\n",
        encoding="utf-8")
    (repro / "comparison.json").write_text('{"paper_value":81.5}', encoding="utf-8")
    (repro / "figures" / "training.png").write_bytes(b"\x89PNG\r\n\x1a\nFAKE")


def _test_collect_finds_slr_and_repro():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        outputs = td_path / "outputs"
        outputs.mkdir()
        _make_temp_outputs(outputs)
        out_json = td_path / "index.json"
        rc = main(["collect", "--root", str(outputs), "--out", str(out_json)])
        assert rc == 0, f"cmd_collect exit code {rc}"
        index = json.loads(out_json.read_text(encoding="utf-8"))
        assert len(index["slr_files"]) == 1, index
        assert len(index["repro_reports"]) == 1, index
        assert len(index["comparison_files"]) == 1, index
        assert len(index["figures"]) == 1, index
        assert index["summary"]["bibtex_unique_count"] == 2, index


def _test_collect_dedupes_bibtex_by_key():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        outputs = td_path / "outputs"
        outputs.mkdir()
        # Two files reference the same key — should dedupe to one entry.
        (outputs / "slr-a.md").write_text(
            "```bibtex\n@misc{shared_key, title={A}}\n```\n", encoding="utf-8")
        (outputs / "slr-b.md").write_text(
            "```bibtex\n@misc{shared_key, title={B}}\n```\n", encoding="utf-8")
        out_json = td_path / "index.json"
        rc = main(["collect", "--root", str(outputs), "--out", str(out_json)])
        assert rc == 0
        index = json.loads(out_json.read_text(encoding="utf-8"))
        keys = [e["key"] for e in index["bibtex_entries"]]
        assert keys == ["shared_key"], keys


def _test_collect_handles_empty_root():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        outputs = td_path / "outputs"
        outputs.mkdir()
        out_json = td_path / "index.json"
        rc = main(["collect", "--root", str(outputs), "--out", str(out_json)])
        assert rc == 0
        index = json.loads(out_json.read_text(encoding="utf-8"))
        assert index["summary"]["bibtex_unique_count"] == 0
        assert index["slr_files"] == []
```

### Step 2 (RED verify): run selftest, expect failures

```bash
python "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py" --selftest
```
Expected: 3 FAIL lines, all attributable to `NotImplementedError` in `cmd_collect`.

### Step 3 (GREEN): implement `cmd_collect`

Replace the `cmd_collect` stub with this implementation:

```python
_BIBTEX_BLOCK_RE = re.compile(r"```bibtex\s*\n(.*?)```", re.DOTALL)
_BIBTEX_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)


def _extract_bibtex_blocks(md_text: str) -> list[tuple[str, str, str]]:
    """Return list of (entry_type, key, raw_entry) tuples from a markdown file."""
    out: list[tuple[str, str, str]] = []
    for block in _BIBTEX_BLOCK_RE.findall(md_text):
        # Walk the block, splitting at top-level @-entries by brace balance.
        i = 0
        n = len(block)
        while i < n:
            m = _BIBTEX_ENTRY_RE.search(block, i)
            if not m:
                break
            entry_type = m.group(1)
            key = m.group(2)
            # Find the opening brace of the entry body
            brace_start = block.find("{", m.end() - 1)
            if brace_start < 0:
                break
            depth = 0
            j = brace_start
            while j < n:
                c = block[j]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if depth != 0:
                break
            raw = block[m.start() : j + 1]
            out.append((entry_type, key, raw))
            i = j + 1
    return out


def cmd_collect(args: argparse.Namespace) -> int:
    root = Path(args.root)
    workspace = Path(args.workspace) if args.workspace else None

    slr_files: list[str] = []
    repro_dirs: list[str] = []
    repro_reports: list[str] = []
    comparison_files: list[str] = []
    analysis_dirs: list[str] = []
    figures: list[str] = []
    bibtex_entries: dict[str, dict[str, str]] = {}  # key -> {key, raw, source}

    image_exts = {".png", ".pdf", ".jpg", ".jpeg"}

    def scan_md(p: Path) -> None:
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return
        for entry_type, key, raw in _extract_bibtex_blocks(text):
            bibtex_entries[key] = {"key": key, "raw": raw, "source": str(p), "type": entry_type}

    if root.exists():
        for entry in sorted(root.iterdir()):
            name = entry.name
            if entry.is_file() and name.startswith("slr-") and name.endswith(".md"):
                slr_files.append(str(entry))
                scan_md(entry)
            elif entry.is_dir() and name.startswith("repro-"):
                repro_dirs.append(str(entry))
                report = entry / "report.md"
                if report.exists():
                    repro_reports.append(str(report))
                    scan_md(report)
                comp = entry / "comparison.json"
                if comp.exists():
                    comparison_files.append(str(comp))
                fig_dir = entry / "figures"
                if fig_dir.exists():
                    for f in sorted(fig_dir.iterdir()):
                        if f.suffix.lower() in image_exts:
                            figures.append(str(f))

    if workspace and workspace.exists():
        for entry in sorted(workspace.iterdir()):
            if entry.is_dir() and entry.name.startswith("analysis-"):
                analysis_dirs.append(str(entry))
        fig_dir = workspace / "figures"
        if fig_dir.exists():
            for f in sorted(fig_dir.iterdir()):
                if f.suffix.lower() in image_exts:
                    figures.append(str(f))

    index: dict[str, Any] = {
        "slr_files": slr_files,
        "repro_dirs": repro_dirs,
        "repro_reports": repro_reports,
        "comparison_files": comparison_files,
        "analysis_dirs": analysis_dirs,
        "figures": figures,
        "bibtex_entries": list(bibtex_entries.values()),
        "summary": {
            "slr_count": len(slr_files),
            "repro_count": len(repro_dirs),
            "figure_count": len(figures),
            "bibtex_unique_count": len(bibtex_entries),
        },
    }

    if args.out:
        out_path = Path(args.out)
    elif workspace:
        out_path = workspace / "scientific_writing_index.json"
    else:
        out_path = root.parent / "scientific_writing_index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"collect: wrote {out_path} ({len(bibtex_entries)} bib entries, {len(figures)} figures)")
    return 0
```

### Step 4 (GREEN verify): run selftest, expect 3 PASS

```bash
python "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py" --selftest
```
Expected: `PASS _test_collect_dedupes_bibtex_by_key`, `PASS _test_collect_finds_slr_and_repro`, `PASS _test_collect_handles_empty_root`, `3/3 tests passed.`

---

## Task 4: TDD — `skeleton` subcommand

**Files:**
- Modify: `skills/custom/scientific-writing/scripts/generate_latex.py`

### Step 1 (RED): add `_test_skeleton_*` functions

Append below existing tests:

```python
def _make_dummy_template(dir_path: Path) -> None:
    (dir_path / "generic.tex").write_text(
        r"""\documentclass{article}
\title{ {{TITLE}} }
\author{ {{AUTHORS}} }
\date{ {{DATE}} }
\begin{document}
\maketitle
\begin{abstract}
% TODO_ABSTRACT: {{STANCE_HINT}}
\end{abstract}
\section{Introduction}
% TODO_INTRO: motivate
\section{Conclusion}
% TODO_CONCLUSION: summarize
{{FIGURE_INCLUDES}}
{{BIBLIOGRAPHY_LINE}}
\end{document}
""",
        encoding="utf-8",
    )


def _test_skeleton_writes_paper_tex_and_bib():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        templates = td_path / "tpl"
        templates.mkdir()
        _make_dummy_template(templates)

        outputs = td_path / "outputs"
        outputs.mkdir()
        _make_temp_outputs(outputs)

        index_path = td_path / "index.json"
        rc = main(["collect", "--root", str(outputs), "--out", str(index_path)])
        assert rc == 0

        paper_dir = td_path / "paper"
        rc = main([
            "skeleton",
            "--template", "generic",
            "--title", "Test Paper",
            "--stance", "We test things.",
            "--index", str(index_path),
            "--out", str(paper_dir),
            "--templates-dir", str(templates),
        ])
        assert rc == 0
        tex = (paper_dir / "paper.tex").read_text(encoding="utf-8")
        assert "Test Paper" in tex
        assert "We test things." in tex
        assert "{{TITLE}}" not in tex, "TITLE marker not substituted"
        assert "{{FIGURE_INCLUDES}}" not in tex
        assert "{{BIBLIOGRAPHY_LINE}}" not in tex
        bib = (paper_dir / "references.bib").read_text(encoding="utf-8")
        assert "vaswani2017attention" in bib
        assert "kipf2017semi" in bib
        # Figure copied
        assert (paper_dir / "figures" / "training.png").exists()


def _test_skeleton_with_empty_bib_omits_bibliography():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        templates = td_path / "tpl"
        templates.mkdir()
        _make_dummy_template(templates)
        outputs = td_path / "outputs"
        outputs.mkdir()
        index_path = td_path / "index.json"
        main(["collect", "--root", str(outputs), "--out", str(index_path)])

        paper_dir = td_path / "paper"
        rc = main([
            "skeleton",
            "--template", "generic",
            "--title", "Empty",
            "--stance", "Nothing.",
            "--index", str(index_path),
            "--out", str(paper_dir),
            "--templates-dir", str(templates),
        ])
        assert rc == 0
        tex = (paper_dir / "paper.tex").read_text(encoding="utf-8")
        # Bib line should be a comment, not an actual \bibliography call
        assert "\\bibliography{references}" not in tex
        assert "% No bibliography" in tex
```

### Step 2 (RED verify):
```bash
python "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py" --selftest
```
Expected: prior 3 tests still pass; 2 new tests FAIL with `NotImplementedError`.

### Step 3 (GREEN): implement `cmd_skeleton`

Replace the stub:

```python
def _resolve_templates_dir(args_dir: str | None) -> Path:
    if args_dir:
        return Path(args_dir)
    return Path(__file__).resolve().parent.parent / "templates"


def cmd_skeleton(args: argparse.Namespace) -> int:
    templates_dir = _resolve_templates_dir(args.templates_dir)
    template_path = templates_dir / f"{args.template}.tex"
    if not template_path.exists():
        # Fall back to generic if requested template missing
        fallback = templates_dir / "generic.tex"
        if not fallback.exists():
            print(f"skeleton: no templates found in {templates_dir}", file=sys.stderr)
            return 1
        print(f"skeleton: template {args.template} not found, falling back to generic", file=sys.stderr)
        template_path = fallback

    template_text = template_path.read_text(encoding="utf-8")

    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    bib_entries = index.get("bibtex_entries", [])
    figures = index.get("figures", [])

    out_dir = Path(args.out)
    figures_out = out_dir / "figures"
    figures_out.mkdir(parents=True, exist_ok=True)

    # Copy figures
    copied: list[str] = []
    for src in figures:
        src_p = Path(src)
        if not src_p.exists():
            continue
        dst = figures_out / src_p.name
        try:
            shutil.copyfile(src_p, dst)
            copied.append(src_p.name)
        except OSError as e:
            print(f"skeleton: failed to copy {src_p}: {e}", file=sys.stderr)

    # Build figure-include block (commented out; LLM uncomments selectively)
    if copied:
        fig_lines = []
        for i, name in enumerate(copied):
            fig_lines.append(
                f"% \\begin{{figure}}[h]\\centering"
                f"\\includegraphics[width=0.7\\linewidth]{{{name}}}"
                f"\\caption{{TODO}}\\label{{fig:{Path(name).stem}}}\\end{{figure}}"
            )
        figure_block = "\n".join(fig_lines)
    else:
        figure_block = "% No figures discovered in upstream artifacts."

    # Build bibliography line
    if bib_entries:
        bib_line = "\\bibliographystyle{plain}\n\\bibliography{references}"
    else:
        bib_line = "% No bibliography (no upstream bibtex blocks found)."

    rendered = (
        template_text
        .replace("{{TITLE}}", _latex_escape(args.title))
        .replace("{{AUTHORS}}", _latex_escape(args.authors) or "")
        .replace("{{DATE}}", date.today().isoformat())
        .replace("{{STANCE_HINT}}", _latex_escape_comment(args.stance))
        .replace("{{FIGURE_INCLUDES}}", figure_block)
        .replace("{{BIBLIOGRAPHY_LINE}}", bib_line)
    )

    (out_dir / "paper.tex").write_text(rendered, encoding="utf-8")

    bib_text = "\n\n".join(e["raw"] for e in bib_entries)
    (out_dir / "references.bib").write_text(bib_text, encoding="utf-8")

    print(
        f"skeleton: wrote {out_dir}/paper.tex "
        f"({len(bib_entries)} bib entries, {len(copied)} figures copied)"
    )
    return 0


def _latex_escape(s: str) -> str:
    """Minimal escape for title/author values inserted into LaTeX text."""
    if not s:
        return ""
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in s:
        out.append(repl.get(ch, ch))
    return "".join(out)


def _latex_escape_comment(s: str) -> str:
    """Stance hint goes inside a LaTeX comment — only escape line breaks."""
    return (s or "").replace("\n", " ")
```

### Step 4 (GREEN verify):
```bash
python "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py" --selftest
```
Expected: 5/5 tests pass.

---

## Task 5: TDD — `naked` subcommand

**Files:**
- Modify: `skills/custom/scientific-writing/scripts/generate_latex.py`

### Step 1 (RED): add `_test_naked_*` functions

```python
def _test_naked_strips_bibliography_and_includegraphics_and_cites():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        tex_in = td_path / "paper.tex"
        tex_in.write_text(
            r"""\documentclass{article}
\begin{document}
\maketitle
We follow \citep{vaswani2017} and \cite{kipf2017,goodfellow2014}.
\includegraphics[width=0.5\linewidth]{figures/x.png}
\bibliographystyle{plain}
\bibliography{references}
\end{document}
""",
            encoding="utf-8",
        )
        tex_out = td_path / "paper_naked.tex"
        rc = main(["naked", "--tex", str(tex_in), "--out", str(tex_out)])
        assert rc == 0
        result = tex_out.read_text(encoding="utf-8")
        # Bibliography commented out
        assert "\\bibliography{references}" not in result, result
        assert "% NAKED:" in result
        # \includegraphics replaced
        assert "\\includegraphics" not in result, result
        assert "Figure omitted" in result
        # \citep / \cite replaced
        assert "\\citep{" not in result
        assert "\\cite{" not in result
        assert "[?]" in result
        # Original preserved
        assert "\\citep{vaswani2017}" in tex_in.read_text(encoding="utf-8")


def _test_naked_preserves_todo_comments():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        tex_in = td_path / "paper.tex"
        tex_in.write_text(
            "\\section{Method}\n% TODO_METHOD: fill from repro report\n",
            encoding="utf-8",
        )
        tex_out = td_path / "paper_naked.tex"
        rc = main(["naked", "--tex", str(tex_in), "--out", str(tex_out)])
        assert rc == 0
        result = tex_out.read_text(encoding="utf-8")
        assert "% TODO_METHOD" in result
```

### Step 2 (RED verify): run selftest, expect 2 new failures.

### Step 3 (GREEN): implement `cmd_naked`

```python
_BIBLIOGRAPHY_LINE_RE = re.compile(r"^(\s*)(\\bibliography(?:style)?\{[^}]*\})", re.MULTILINE)
_INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}")
_CITE_RE = re.compile(r"\\cite[pt]?\{[^}]*\}")


def cmd_naked(args: argparse.Namespace) -> int:
    src = Path(args.tex).read_text(encoding="utf-8")
    out = src
    out = _BIBLIOGRAPHY_LINE_RE.sub(r"\1% NAKED: \2", out)
    out = _INCLUDEGRAPHICS_RE.sub(
        r"\\textit{[Figure omitted in naked-PDF degradation]}", out
    )
    out = _CITE_RE.sub("[?]", out)
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"naked: wrote {args.out}")
    return 0
```

### Step 4 (GREEN verify):
```bash
python "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py" --selftest
```
Expected: 7/7 tests pass.

---

## Task 6: Write `templates/generic.tex`

**Files:**
- Create: `skills/custom/scientific-writing/templates/generic.tex`

**Step 1:** Write the file. Per design §3.3:

```latex
\documentclass[11pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue]{hyperref}
\usepackage{natbib}
\usepackage[margin=1in]{geometry}

\graphicspath{{figures/}}

\title{ {{TITLE}} }
\author{ {{AUTHORS}} }
\date{ {{DATE}} }

\begin{document}
\maketitle

\begin{abstract}
% TODO_ABSTRACT: write a 4-6 sentence abstract.
% Stance hint from skill input: {{STANCE_HINT}}
% Sources: outputs/repro-*/report.md (if reproduction was performed),
%          outputs/slr-*.md (if literature review was performed).
\end{abstract}

\section{Introduction}
% TODO_INTRO: motivate the problem; cite key references via \citep{key}
%             (key must exist in references.bib). If references.bib is empty,
%             write descriptive prose without citations and add inline
%             "% needs citation" markers.

\section{Related Work}
% TODO_RELATED: synthesize from outputs/slr-*.md.
%               Use \citep{key} for inline cites; key must exist in references.bib.
%               If references.bib is empty, prose only with "% needs citation".

\section{Method}
% TODO_METHOD: describe approach;
%              source: outputs/repro-*/report.md (Method section).
%              Include any scale-down decisions explicitly.

\section{Experiments}
% TODO_EXPERIMENTS: present quantitative results.
%                   Sources: outputs/repro-*/comparison.json (paper_value, our_value, delta)
%                            workspace/analysis-*/*.csv (if data-analysis was performed).
%                   Use the figure-include lines below; uncomment ones you cite.

% Figure includes (uncomment as you write Experiments prose):
{{FIGURE_INCLUDES}}

\section{Conclusion}
% TODO_CONCLUSION: 1-paragraph summary of contribution + limitations + future work.

{{BIBLIOGRAPHY_LINE}}

\end{document}
```

**Step 2:** Verify the skeleton renders successfully against this real template:
```bash
cd "D:/6725_GroupProject/scideer"
python -c "
from pathlib import Path
import json, subprocess, sys, tempfile
script = Path('skills/custom/scientific-writing/scripts/generate_latex.py').resolve()
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    out = td / 'outputs'
    out.mkdir()
    idx = td / 'idx.json'
    subprocess.run([sys.executable, str(script), 'collect', '--root', str(out), '--out', str(idx)], check=True)
    paper = td / 'paper'
    subprocess.run([sys.executable, str(script), 'skeleton',
                    '--template', 'generic',
                    '--title', 'Smoke',
                    '--stance', 'Smoke test.',
                    '--index', str(idx),
                    '--out', str(paper)], check=True)
    tex = (paper / 'paper.tex').read_text(encoding='utf-8')
    assert '{{' not in tex, f'unsubstituted markers: {tex}'
    assert 'Smoke' in tex
    print('generic.tex skeleton rendering OK')
"
```
Expected: prints `generic.tex skeleton rendering OK`.

---

## Task 7: Write `templates/neurips.tex`

**Files:**
- Create: `skills/custom/scientific-writing/templates/neurips.tex`

**Step 1:** Write the file:

```latex
\documentclass[10pt,letterpaper]{article}

\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage[colorlinks=true,linkcolor=black,citecolor=black,urlcolor=blue]{hyperref}
\usepackage{natbib}
\usepackage[left=1.25in,right=1.25in,top=1in,bottom=1in]{geometry}
\usepackage{titlesec}

% NeurIPS-ish section heading
\titleformat{\section}{\large\bfseries}{\thesection}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{0.5em}{}

% NeurIPS-ish title block (centered, large title, smaller author)
\makeatletter
\renewcommand{\@maketitle}{
  \begin{center}
  {\LARGE\bfseries \@title \par}
  \vspace{0.5em}
  {\large \@author \par}
  \vspace{0.3em}
  {\itshape \@date \par}
  \end{center}
  \vspace{1em}
}
\makeatother

\graphicspath{{figures/}}

\title{ {{TITLE}} }
\author{ {{AUTHORS}} }
\date{ {{DATE}} }

\begin{document}
\maketitle

\begin{abstract}
% TODO_ABSTRACT: 4-6 sentence abstract.
% Stance hint: {{STANCE_HINT}}
\end{abstract}

\section{Introduction}
% TODO_INTRO: motivate; cite via \citep{key}.

\section{Related Work}
% TODO_RELATED: synthesize from outputs/slr-*.md.

\section{Method}
% TODO_METHOD: source outputs/repro-*/report.md.

\section{Experiments}
% TODO_EXPERIMENTS: source outputs/repro-*/comparison.json + workspace/analysis-*.

% Figure includes (uncomment as you write Experiments prose):
{{FIGURE_INCLUDES}}

\section{Conclusion}
% TODO_CONCLUSION: summary + limitations + future work.

{{BIBLIOGRAPHY_LINE}}

\end{document}
```

**Step 2:** Verify both templates render via skeleton:
```bash
cd "D:/6725_GroupProject/scideer"
python -c "
from pathlib import Path
import json, subprocess, sys, tempfile
script = Path('skills/custom/scientific-writing/scripts/generate_latex.py').resolve()
for tpl in ('generic', 'neurips'):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out = td / 'outputs'
        out.mkdir()
        idx = td / 'idx.json'
        subprocess.run([sys.executable, str(script), 'collect', '--root', str(out), '--out', str(idx)], check=True)
        paper = td / 'paper'
        subprocess.run([sys.executable, str(script), 'skeleton',
                        '--template', tpl, '--title', 'X', '--stance', 'Y.',
                        '--index', str(idx), '--out', str(paper)], check=True)
        tex = (paper / 'paper.tex').read_text(encoding='utf-8')
        assert '{{' not in tex, f'{tpl}: unsubstituted markers'
        print(f'{tpl}.tex skeleton rendering OK')
"
```
Expected: two `OK` lines.

---

## Task 8: Write `compile_pdf.sh`

**Files:**
- Create: `skills/custom/scientific-writing/scripts/compile_pdf.sh`

**Step 1:** Write the file:

```bash
#!/bin/bash
# compile_pdf.sh — 3-attempt retry + naked-PDF degradation.
# Always produces paper.pdf and compile_errors.md if at all possible.
#
# Usage: compile_pdf.sh <paper-dir>
#   Expects: <paper-dir>/paper.tex, <paper-dir>/references.bib (may be empty),
#            <paper-dir>/figures/ (may be empty)
#   Produces: <paper-dir>/paper.pdf, <paper-dir>/compile_errors.md
#
# Exit codes:
#   0 — paper.pdf was produced (vanilla, attempt 2/3, or naked)
#   1 — even naked PDF compilation failed; user must hand-debug

set -u

PAPER_DIR="${1:-outputs/paper}"
if [ ! -d "$PAPER_DIR" ]; then
    echo "compile_pdf.sh: paper dir not found: $PAPER_DIR" >&2
    exit 1
fi
cd "$PAPER_DIR" || exit 1

if [ ! -f paper.tex ]; then
    echo "compile_pdf.sh: paper.tex not found in $PAPER_DIR" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")" && pwd)"
LOG="compile_errors.md"

{
    echo "# LaTeX Compile Log"
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Paper directory: $PAPER_DIR"
} > "$LOG"

run_compile() {
    # $1 = attempt number, $2 = source tex (without .tex)
    local attempt="$1"
    local src="$2"
    latexmk -pdf -interaction=nonstopmode -file-line-error "$src.tex" \
        > "compile_attempt_${attempt}.log" 2>&1
}

dump_tail() {
    local attempt="$1"
    {
        echo '```'
        if [ -f paper.log ]; then
            grep -E '^(\!|paper\.tex:|.*Error)' paper.log | head -40 || true
        fi
        echo "--- compile_attempt_${attempt}.log (tail) ---"
        tail -30 "compile_attempt_${attempt}.log" 2>/dev/null || true
        echo '```'
    } >> "$LOG"
}

# ---------- Attempt 1: vanilla ----------
echo "" >> "$LOG"
echo "## Attempt 1 (vanilla)" >> "$LOG"
if run_compile 1 paper; then
    echo "Result: success" >> "$LOG"
    exit 0
fi
dump_tail 1

# ---------- Attempt 2: drop missing image refs ----------
echo "" >> "$LOG"
echo "## Attempt 2 (after dropping missing image refs)" >> "$LOG"
if [ -f paper.log ]; then
    # Extract filenames LaTeX reports as missing.
    MISSING_FILES=$(grep -oE "File \`[^']+' not found" paper.log | \
                    sed -E "s/File \`([^']+)' not found/\1/" | sort -u || true)
    if [ -n "${MISSING_FILES:-}" ]; then
        for img in $MISSING_FILES; do
            base=$(basename "$img")
            echo "- Removing reference to missing file: $img" >> "$LOG"
            # Comment out lines containing \includegraphics + that base filename
            sed -i.bak -E "/\\\\includegraphics([^{]*\\{)?[^}]*${base}/s/^/% MISSING_FIG: /" paper.tex
            rm -f paper.tex.bak
        done
    else
        echo "- No missing-image errors detected; retrying anyway." >> "$LOG"
    fi
fi
if run_compile 2 paper; then
    echo "Result: success after image-ref cleanup" >> "$LOG"
    exit 0
fi
dump_tail 2

# ---------- Attempt 3: drop undefined cites ----------
echo "" >> "$LOG"
echo "## Attempt 3 (after dropping undefined cites)" >> "$LOG"
if [ -f paper.log ]; then
    BAD_KEYS=$(grep -oE "Citation \`[^']+' (on page [0-9]+ )?undefined" paper.log | \
               sed -E "s/Citation \`([^']+)'.*/\1/" | sort -u || true)
    if [ -n "${BAD_KEYS:-}" ]; then
        for key in $BAD_KEYS; do
            echo "- Replacing undefined cite key: $key" >> "$LOG"
            # Replace single-key \citep{key} and \cite{key} with [?].
            # Multi-key cites containing this key are left alone (LaTeX still
            # warns but compiles); they'll just print [?] inline at compile time.
            esc=$(printf '%s\n' "$key" | sed -e 's/[]\/$*.^|[]/\\&/g')
            sed -i.bak -E "s/\\\\citep\\{${esc}\\}/[?]/g; s/\\\\cite\\{${esc}\\}/[?]/g" paper.tex
            rm -f paper.tex.bak
        done
    else
        echo "- No undefined-cite errors detected; retrying anyway." >> "$LOG"
    fi
fi
if run_compile 3 paper; then
    echo "Result: success after cite cleanup" >> "$LOG"
    exit 0
fi
dump_tail 3

# ---------- Naked PDF fallback ----------
echo "" >> "$LOG"
echo "## Naked PDF Fallback" >> "$LOG"
echo "After 3 failed attempts, generating text-only naked PDF." >> "$LOG"

GEN_PY="$SCRIPT_DIR/generate_latex.py"
if [ ! -f "$GEN_PY" ]; then
    echo "compile_pdf.sh: generate_latex.py not found at $GEN_PY" >> "$LOG"
    exit 1
fi

if ! python3 "$GEN_PY" naked --tex paper.tex --out paper_naked.tex \
        >> "$LOG" 2>&1; then
    echo "Naked tex generation failed." >> "$LOG"
    exit 1
fi

if latexmk -pdf -interaction=nonstopmode paper_naked.tex \
        > compile_naked.log 2>&1 && [ -f paper_naked.pdf ]; then
    cp paper_naked.pdf paper.pdf
    echo "Naked PDF compiled. Original paper.tex preserved; paper_naked.tex is the compiled source." >> "$LOG"
    exit 0
fi

{
    echo "Naked compile also failed."
    echo '```'
    tail -30 compile_naked.log 2>/dev/null || true
    echo '```'
    echo ""
    echo "paper.pdf was NOT produced. paper.tex and references.bib are preserved on disk for manual debugging."
} >> "$LOG"
exit 1
```

**Step 2:** Make it executable + verify bash syntax:
```bash
chmod +x "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/compile_pdf.sh"
bash -n "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/compile_pdf.sh"
```
Expected: no output, exit 0.

**Step 3:** Verify the script handles "missing paper.tex" gracefully:
```bash
cd "$(mktemp -d)" && \
mkdir paper && \
bash "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/compile_pdf.sh" paper && \
echo "unexpected: should have exited non-zero"
```
Expected: error message printed to stderr, exit 1, no `unexpected` line.

**Step 4 (optional, requires local LaTeX):** If you have `latexmk` locally, run a real compile against an empty skeleton. If not, this is verified on the server after Docker build. Skip otherwise.

---

## Task 9: Write `docker/scideer-sandbox/Dockerfile`

**Files:**
- Create: `docker/scideer-sandbox/Dockerfile`

**Step 1:** Write the file:

```dockerfile
# Libra Sandbox — DeerFlow AIO sandbox + LaTeX toolchain
#
# Built on top of Volcengine's all-in-one-sandbox image. Adds:
#   - texlive-latex-extra      (compile core + most academic packages)
#   - texlive-fonts-recommended (Latin Modern et al.)
#   - texlive-bibtex-extra     (bibtex tools beyond the base set)
#   - latexmk                  (multi-pass orchestration; used by compile_pdf.sh)
#
# Resulting image is ~1.4 GB larger than base (vs ~4 GB+ for texlive-full).

FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest

USER root

# Install LaTeX toolchain.
#   --no-install-recommends keeps the layer lean; we add fonts explicitly.
#   DEBIAN_FRONTEND=noninteractive avoids tzdata interactive prompts.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        texlive-latex-extra \
        texlive-fonts-recommended \
        texlive-bibtex-extra \
        latexmk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Smoke test: fail the build if any binary is missing.
RUN pdflatex --version > /dev/null && \
    bibtex --version > /dev/null && \
    latexmk --version > /dev/null

LABEL org.opencontainers.image.description="DeerFlow AIO sandbox + LaTeX (texlive-latex-extra) for SciDeer/Libra scientific-writing skill"
LABEL org.opencontainers.image.source="https://github.com/wisdom222/scideer"
```

**Step 2:** Verify Dockerfile syntax via `docker build --check` if Docker is available locally; otherwise verify by static inspection (no obvious typos, all `RUN` commands quoted properly). The user will run `docker build` on the server.

---

## Task 10: Write `docker/scideer-sandbox/README.md`

**Files:**
- Create: `docker/scideer-sandbox/README.md`

**Step 1:** Write the file:

```markdown
# scideer-sandbox / libra-sandbox

DeerFlow AIO sandbox extended with the LaTeX toolchain required by the
`scientific-writing` skill. Adds `texlive-latex-extra` + fonts +
`texlive-bibtex-extra` + `latexmk` on top of the base image.

**Image size:** base ~3 GB + LaTeX layer ~1.4 GB ≈ ~4.4 GB (vs 7 GB for texlive-full).

## Prerequisites

- Docker 20+ (or Apple Container on macOS)
- Network access to `enterprise-public-cn-beijing.cr.volces.com` for the base pull
- ~6 GB free disk

## Build

From the repo root:

```bash
docker build -t libra-sandbox:latest -f docker/scideer-sandbox/Dockerfile docker/scideer-sandbox/
```

First-time build downloads ~1 GB of texlive packages. Expect 10–15 min.

## Smoke Test

After the build:

```bash
docker run --rm libra-sandbox:latest pdflatex --version
docker run --rm libra-sandbox:latest latexmk --version
```

Both should print version strings without error.

User-context check (first build only):

```bash
docker run --rm libra-sandbox:latest whoami
```

If it prints `root`, no action needed. If it prints another user and you later
hit permission errors at skill-execution time, see Troubleshooting below.

## Wire Up to DeerFlow

Edit `config.yaml` on the server. Locate the existing `sandbox:` block (usually
`LocalSandboxProvider` from `config.example.yaml`, or a commented-out AIO
section). **Replace** it with:

```yaml
sandbox:
  use: deerflow.community.aio_sandbox:AioSandboxProvider
  image: libra-sandbox:latest
  port: 8080
  replicas: 3
  # Optional: mount the SciDeer cache used by paper-reproduction.
  # mounts:
  #   - host_path: /home/<user>/.scideer/cache
  #     container_path: /mnt/scideer-cache
  #     read_only: true
```

Do **not** delete other sections of `config.yaml` (models, subagents,
extensions, etc.) — only the `sandbox:` block is replaced.

Restart DeerFlow:

```bash
make dev-daemon-stop && make dev-daemon
```

(Or your local equivalent — `pkill -f 'deerflow' && make dev` on a hand-rolled
setup.)

Verify in the Web UI: ask any agent to run `which pdflatex` in a sandboxed
bash. Expected output: `/usr/bin/pdflatex`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `pdflatex: command not found` inside skill | Wrong image active | Confirm `docker images \| grep libra-sandbox`; check `config.yaml` `image:` field; restart DeerFlow |
| Compile hangs > 5 min | latexmk in interactive mode (rare) | Verify `compile_pdf.sh` uses `-interaction=nonstopmode` (it does by default; do not modify) |
| Permission denied writing `outputs/paper/figures/` | USER mismatch from base image | Rebuild with `RUN chown -R <user>:<user> /home/<user>` appended to the Dockerfile after the texlive layer |
| Image larger than 5 GB | `texlive-full` was substituted | Confirm Dockerfile uses `texlive-latex-extra`, not `texlive-full`; rebuild |
| `apt-get update` fails during build | Network policy or registry mirror | Configure Docker `--build-arg http_proxy` or replace registry mirror |

## Related Files

- `docker/scideer-sandbox/Dockerfile` — image definition
- `skills/custom/scientific-writing/scripts/compile_pdf.sh` — uses `latexmk` provided by this image
- `docs/plans/2026-05-06-scientific-writing-design.md` §4 — design rationale
```

**Step 2:** Verify the README renders cleanly. Visual check that the `config.yaml` patch snippet is correct.

---

## Task 11: Write `SKILL.md` — frontmatter + Overview + When-to-use

**Files:**
- Create: `skills/custom/scientific-writing/SKILL.md`

**Step 1:** Write the first half of the file (frontmatter through "When to Use This Skill"):

```markdown
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

## Output Structure

```
/mnt/user-data/outputs/paper/
├── paper.tex              # editable LaTeX source
├── paper.pdf              # final PDF (may be naked-PDF in fallback case)
├── references.bib         # may be empty if no upstream bibtex blocks found
├── figures/               # all upstream figures, copied (only cited ones embed in PDF)
└── compile_errors.md      # always present after compile; documents the path taken
```
```

**Step 2:** Verify the YAML frontmatter parses:
```bash
python -c "
import yaml
with open('D:/6725_GroupProject/scideer/skills/custom/scientific-writing/SKILL.md') as f:
    text = f.read()
parts = text.split('---', 2)
front = yaml.safe_load(parts[1])
assert front['name'] == 'scientific-writing'
print('frontmatter OK:', list(front.keys()))
"
```
Expected: `frontmatter OK: ['name', 'description']`. Note: this requires PyYAML; if not installed locally, skip and verify by visual inspection of the `name:`/`description:` block.

---

## Task 12: Write `SKILL.md` — Workflow section (6 phases)

**Files:**
- Modify: `skills/custom/scientific-writing/SKILL.md` (append)

**Step 1:** Append the Workflow section. It is the heart of the skill and the longest single section.

```markdown
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

Read the resulting `paper.tex` to confirm the structure before Phase 4.

### Phase 4: Per-section fill (LLM, six `Edit` calls)

Use the `Edit` tool **once per section**, in this order:

1. **Introduction** (sources: `outputs/slr-*.md` themes only)
2. **Related Work** (sources: `outputs/slr-*.md` full body)
3. **Method** (sources: `outputs/repro-*/report.md` Method section)
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
  table above. Reading figures while writing Methods (or vice versa) leads to
  mixed-up content.
- Replace the `% TODO_<NAME>: <reason>` line with real prose. **Do not** leave
  the TODO marker in place if you have content for that section.
- If a section's source artifacts are missing or empty (e.g. no SLR was run, so
  Related Work has nothing to draw on), keep the `% TODO_<NAME>: ...` comment
  in place. The skeleton will still compile, and the comment documents what
  was missing.
- Use `\citep{key}` for inline citations. The `key` must already exist in
  `references.bib` (you can verify by reading the file). If `references.bib`
  is empty, **do not** call `\citep{}` — write descriptive prose only.

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
4. If `compile_errors.md` indicates a non-vanilla path was taken, honestly
   note it: e.g. "Note: the PDF was produced via naked-PDF fallback after
   3 compile failures. See compile_errors.md for details."
```

**Step 2:** Verify section structure by reading the file back:
```bash
grep -E '^### Phase' "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/SKILL.md"
```
Expected: 6 lines, one per phase.

---

## Task 13: Write `SKILL.md` — Failure Modes + Examples + Notes

**Files:**
- Modify: `skills/custom/scientific-writing/SKILL.md` (append)

**Step 1:** Append the remaining sections:

```markdown
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
```

**Step 2:** Verify the full SKILL.md:
```bash
wc -l "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/SKILL.md"
grep -c '^## ' "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/SKILL.md"
```
Expected: ~400–500 lines, 7 H2 sections (Overview, When to Use, Required Inputs, Output Structure, Workflow, Failure Modes, Examples, Notes).

Wait — that's 8 H2s. Recount from the file. Adjust expectations to match actual section count.

---

## Task 14: Final verification (file count + content review)

**Step 1:** Verify the deliverable file list matches the design exactly. Run:

```bash
cd "D:/6725_GroupProject/scideer"
echo "=== Skill files ==="
find skills/custom/scientific-writing -type f | sort
echo "=== Docker files ==="
find docker/scideer-sandbox -type f | sort
echo "=== Files outside boundary that have changed (should be EMPTY) ==="
git status --porcelain | grep -v -E '^\?\? (skills/custom/scientific-writing/|docker/scideer-sandbox/|docs/plans/2026-05-06-scientific-writing-)' || echo "(boundary respected)"
```

Expected output:
```
=== Skill files ===
skills/custom/scientific-writing/SKILL.md
skills/custom/scientific-writing/scripts/compile_pdf.sh
skills/custom/scientific-writing/scripts/generate_latex.py
skills/custom/scientific-writing/templates/generic.tex
skills/custom/scientific-writing/templates/neurips.tex
=== Docker files ===
docker/scideer-sandbox/Dockerfile
docker/scideer-sandbox/README.md
=== Files outside boundary that have changed (should be EMPTY) ===
(boundary respected)
```

**Step 2:** Run the full Python self-test suite one final time:
```bash
python "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/generate_latex.py" --selftest
```
Expected: `7/7 tests passed.` exit 0.

**Step 3:** Bash-syntax-check the compile script:
```bash
bash -n "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/scripts/compile_pdf.sh"
```
Expected: no output, exit 0.

**Step 4:** Verify SKILL.md frontmatter parses (visual check is fine if PyYAML
is unavailable):
```bash
head -20 "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/SKILL.md"
```
Expected: `---` line, `name: scientific-writing`, `description: ...`
(several lines), `---` close.

**Step 5:** Sanity-check templates have all expected substitution markers:
```bash
for f in generic neurips; do
  echo "=== $f.tex ==="
  grep -E '\{\{[A-Z_]+\}\}' "D:/6725_GroupProject/scideer/skills/custom/scientific-writing/templates/$f.tex" | sort -u
done
```
Expected: each template lists `{{TITLE}}`, `{{AUTHORS}}`, `{{DATE}}`,
`{{STANCE_HINT}}`, `{{FIGURE_INCLUDES}}`, `{{BIBLIOGRAPHY_LINE}}`.

**Step 6:** Spot-check Dockerfile syntax (no parser available locally; visual
check is the bar):
```bash
cat "D:/6725_GroupProject/scideer/docker/scideer-sandbox/Dockerfile"
```
Confirm: `FROM` line points to the volces.com image, `RUN apt-get install`
includes the four packages, smoke-test `RUN` is present, two `LABEL` lines
at the bottom.

---

## Task 15 (gated on user approval): Stage, commit, and report

**Do NOT execute this task until the user explicitly says "commit it" or
"ready to push" or equivalent.** The user's prompt is explicit: "如果用户没有
主动要求,绝对不要计划和执行 git 提交和分支等操作". The plan stops at Task 14
by default.

**When approved:**

**Step 1:** Stage only the boundary-respected paths:

```bash
cd "D:/6725_GroupProject/scideer"
git add skills/custom/scientific-writing/ \
        docker/scideer-sandbox/ \
        docs/plans/2026-05-06-scientific-writing-design.md \
        docs/plans/2026-05-06-scientific-writing-implementation.md
```

**Step 2:** Verify staged paths match expectation:

```bash
git status --short
```
Expected: only paths under the staged directories listed above; nothing else.
If anything else is staged, **stop and reconcile with the user** — the
boundary contract was violated.

**Step 3:** Commit (single commit; do not split unless the user asks):

```bash
git commit -m "feat(scientific-writing): scientific-writing skill + libra-sandbox image

- skills/custom/scientific-writing/{SKILL.md,scripts/,templates/}
  6-phase workflow (plan → collect → skeleton → per-section fill → compile → present);
  generate_latex.py multi-subcommand CLI (collect/skeleton/naked) with self-test;
  compile_pdf.sh 3-attempt retry + naked-PDF degradation;
  generic.tex (default) and neurips.tex (simplified clone, no external sty) templates.
- docker/scideer-sandbox/{Dockerfile,README.md}
  FROM aio-sandbox + texlive-latex-extra + fonts-recommended + bibtex-extra + latexmk;
  README documents build, smoke test, config.yaml patch, troubleshooting.
- docs/plans/2026-05-06-scientific-writing-{design,implementation}.md
  brainstormed design + step-by-step implementation plan for this track.

No modification to frontend/, backend/, agents/, benchmarks/, other skills/,
config.yaml, extensions_config.json. Skill is auto-discovered by DeerFlow's
filesystem scan (no registration needed). User merges sandbox: section into
their server's config.yaml manually using the patch in docker/scideer-sandbox/README.md."
```

**Step 4:** Report to the user. Do **not** push without an additional explicit
go-ahead. State:

> Local commit complete on branch `scideer-main`. To deploy:
>
> 1. `git push` (when you're ready)
> 2. On the server: `git pull && docker build -t libra-sandbox:latest -f docker/scideer-sandbox/Dockerfile docker/scideer-sandbox/`
> 3. Edit `config.yaml` per `docker/scideer-sandbox/README.md`
> 4. Restart DeerFlow

---

## Plan Summary

15 tasks, ~3–5 hours of careful work:

| # | Task | Track | TDD? |
|---|---|---|:---:|
| 0 | Read design doc + verify repo state | meta | — |
| 1 | Create directories | scaffolding | — |
| 2 | Scaffold `generate_latex.py` + selftest harness | script | bootstrap |
| 3 | TDD `collect` subcommand | script | ✓ |
| 4 | TDD `skeleton` subcommand | script | ✓ |
| 5 | TDD `naked` subcommand | script | ✓ |
| 6 | Write `generic.tex` + smoke test | template | smoke |
| 7 | Write `neurips.tex` + smoke test | template | smoke |
| 8 | Write `compile_pdf.sh` | script | bash-syntax |
| 9 | Write `Dockerfile` | docker | inspection |
| 10 | Write `docker README.md` | docker | inspection |
| 11 | SKILL.md frontmatter + Overview + When-to-use | skill doc | YAML parse |
| 12 | SKILL.md Workflow (6 phases) | skill doc | structural grep |
| 13 | SKILL.md Failure Modes + Examples + Notes | skill doc | review |
| 14 | Final verification (boundaries + selftest + lints) | meta | full |
| 15 | (gated) Stage, commit, report | meta | — |

**Boundary contract:** zero modifications outside `skills/custom/scientific-writing/`,
`docker/scideer-sandbox/`, and the two design/implementation docs in `docs/plans/`.

---

**End of implementation plan.**
