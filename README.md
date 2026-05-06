# Libra — Scientific Research Agent

> A research-lifecycle AI agent for surveying literature, reproducing papers, designing experiments, and writing publication-ready papers.

## Features

- **Systematic literature review** with arXiv integration and APA / IEEE / BibTeX output
- **Paper reproduction** with auto scale-down and sandbox execution
- **Experiment design and data analysis** with auto-generated publication-quality figures
- **LaTeX paper generation** with bibliography compilation (NeurIPS / ICML / ACL templates)
- **Cross-database citation graph analysis** via Semantic Scholar
- **End-to-end research lifecycle orchestration** via the `sci-pi` subagent

## Quick Start

```bash
# 1. Install dependencies
make config
make install

# 2. Set your LLM API key in .env (see config.yaml for supported providers)
echo "DEEPSEEK_API_KEY=sk-..." >> .env

# 3. Run
make dev
```

Open `http://localhost:2026` in your browser.

## Architecture

See [`docs/plans/2026-05-03-scideer-design.md`](docs/plans/2026-05-03-scideer-design.md) for the full architecture and design rationale.

Key components:

- **Skills** (`skills/public/`, `skills/custom/`) — markdown-defined research workflows
- **Subagents** (`agents/`) — specialized agents like `sci-pi` for orchestration
- **MCP integrations** (`extensions_config.json`) — external tools like Semantic Scholar
- **Sandbox** (`docker/scideer-sandbox/`) — isolated containers for paper-reproduction experiments
- **Benchmark** (`benchmarks/sci_eval/`) — mini sci-bench for measuring research-task performance

## Acknowledgments

Libra extends [DeerFlow 2.0](https://github.com/bytedance/deer-flow) by ByteDance, adding scientific-research-specific capabilities:

- Two new skills: `paper-reproduction` and `scientific-writing`
- A custom orchestrator subagent: `sci-pi`
- Semantic Scholar MCP integration for citation graph analysis
- A mini sci-bench evaluation layer for measuring research-task performance

DeerFlow provides the harness foundation (LangGraph, skill loader, subagent dispatcher, sandbox providers, MCP client). Libra provides the scientific-research domain extensions.

## License

Original DeerFlow license retained — see [`LICENSE`](LICENSE).
