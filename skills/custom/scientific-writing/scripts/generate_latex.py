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
            brace_start = block.find("{", m.start())
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
                i = m.end()
                continue
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


# ---------- Subcommand: skeleton ----------

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

    try:
        index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"skeleton: failed to read --index {args.index}: {e}", file=sys.stderr)
        return 1
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


# ---------- Subcommand: naked ----------

_BIBLIOGRAPHY_LINE_RE = re.compile(r"^(\s*)(\\bibliography(?:style)?\{[^}]*\})", re.MULTILINE)
_INCLUDEGRAPHICS_RE = re.compile(
    r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{[^}]*\}",
    re.DOTALL,
)
_CITE_RE = re.compile(r"\\cite[pt]?(?:\[[^\]]*\])*\{[^}]*\}")


def cmd_naked(args: argparse.Namespace) -> int:
    try:
        src = Path(args.tex).read_text(encoding="utf-8")
    except OSError as e:
        print(f"naked: failed to read --tex {args.tex}: {e}", file=sys.stderr)
        return 1
    out = src
    out = _BIBLIOGRAPHY_LINE_RE.sub(r"\1% NAKED: \2", out)
    out = _INCLUDEGRAPHICS_RE.sub(
        r"\\textit{[Figure omitted in naked-PDF degradation]}", out
    )
    out = _CITE_RE.sub("[?]", out)
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"naked: wrote {args.out}")
    return 0


# ---------- Tests (run via --selftest) ----------

def _make_temp_outputs(root: Path) -> None:
    """Build a representative outputs/ tree for collect tests."""
    (root / "slr-diffusion-models-20260506.md").write_text(
        "# SLR\n\nSome content.\n\n```bibtex\n"
        "@misc{vaswani2017attention, title={Attention {Is All You} Need}, author={Vaswani et al.}, year={2017}}\n"
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
        # Verify raw bibtex entries are structurally complete (closing brace preserved
        # through nested-brace and multi-field handling).
        for entry in index["bibtex_entries"]:
            raw = entry["raw"]
            assert raw.startswith("@"), f"raw doesn't start with @: {raw!r}"
            assert raw.endswith("}"), f"raw missing closing brace: {raw!r}"
            # Open and close braces should balance
            assert raw.count("{") == raw.count("}"), f"unbalanced braces in {raw!r}"


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


def _test_naked_strips_bibliography_and_includegraphics_and_cites():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        tex_in = td_path / "paper.tex"
        tex_in.write_text(
            r"""\documentclass{article}
\begin{document}
\maketitle
We follow \citep{vaswani2017} and \cite{kipf2017,goodfellow2014}.
We also cite \citep[p.~5]{kipf2017} and \citep[see][]{another}.
\includegraphics[width=0.5\linewidth]{figures/x.png}
\includegraphics[
    width=0.7\linewidth,
    height=4cm
]{figures/multiline.png}
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
        # Bibliography commented out (text preserved but inert under "% NAKED: ")
        for line in result.splitlines():
            stripped = line.lstrip()
            assert not stripped.startswith("\\bibliography{"), f"active \\bibliography survived: {line!r}"
            assert not stripped.startswith("\\bibliographystyle{"), f"active \\bibliographystyle survived: {line!r}"
        assert "% NAKED: \\bibliography{references}" in result
        assert "% NAKED: \\bibliographystyle{plain}" in result
        # \includegraphics replaced
        assert "\\includegraphics" not in result, result
        assert "Figure omitted" in result
        # Multi-line \includegraphics also degraded
        assert "multiline.png" not in result, f"multi-line includegraphics survived: {result}"
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
