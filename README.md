# Libra

**A scientific research agent for the full research lifecycle.**

From literature survey to publication-ready paper, Libra handles the mechanical parts of research so you can focus on the ideas.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Built on DeerFlow 2.0](https://img.shields.io/badge/Built%20on-DeerFlow%202.0-blue)](https://github.com/bytedance/deer-flow)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-green)](./backend/pyproject.toml)

---

## What Libra does

A typical research workflow with Libra:

1. **Survey** — *"Find all papers on transformer-based protein folding from 2023–2025, ranked by citation impact."* Libra searches arXiv + Semantic Scholar, dedupes, and produces a BibTeX-formatted reading list with abstracts and key findings.
2. **Reproduce** — Drop in a paper PDF. Libra extracts the method, generates executable code, runs it in a sandboxed Docker container, and produces a reproduction report comparing your numbers against the paper's.
3. **Experiment** — Describe your idea. Libra designs baselines, runs experiments end-to-end, and generates publication-quality matplotlib figures.
4. **Write** — Hand over your results. Libra drafts a full LaTeX paper in NeurIPS / ICML / ACL templates, compiles to PDF, and manages the bibliography.

All driven by the `sci-pi` orchestrator subagent that chains these four skills into one continuous workflow.

## Quick Start

```bash
git clone https://github.com/wisdom222/scideer
cd scideer
make config
make install
echo "DEEPSEEK_API_KEY=sk-..." >> .env
make dev
```

Open `http://localhost:2026` in your browser.

## Built On

Libra extends [DeerFlow 2.0](https://github.com/bytedance/deer-flow) by ByteDance — an open-source agent harness providing LangGraph orchestration, skill loader, sandbox execution, and MCP integration.

Libra adds the scientific-research domain layer:

- **`paper-reproduction` skill** — paper → executable code → comparison report
- **`scientific-writing` skill** — results → LaTeX paper → compiled PDF
- **`sci-pi` orchestrator subagent** — chains the lifecycle end-to-end
- **Semantic Scholar MCP integration** — citation graph beyond arXiv
- **Mini sci-bench** — quantitative evaluation layer for research-task performance

## Repository Layout

| Path | What's there |
|------|--------------|
| [`skills/`](skills/) | Markdown-defined research workflows |
| [`agents/`](agents/) | Specialized agents including `sci-pi` orchestrator |
| [`backend/`](backend/) | Python harness extending DeerFlow runtime |
| [`benchmarks/sci_eval/`](benchmarks/sci_eval/) | Mini sci-bench evaluation suite |
| [`docs/plans/2026-05-03-scideer-design.md`](docs/plans/2026-05-03-scideer-design.md) | Full architecture and design rationale |

## Acknowledgments

Libra builds on upstream work from the [DeerFlow](https://github.com/bytedance/deer-flow) team — the harness, skill system, sandbox abstraction, and MCP client all come from there. Libra contributes the scientific-research-specific extensions on top.

## License

MIT — see [`LICENSE`](LICENSE).
