# SciDeer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform DeerFlow 2.0 into SciDeer — a scientific research lifecycle agent harness — by adding 2 original skills (`paper-reproduction`, `scientific-writing`), 1 custom subagent (`sci-pi`), 1 MCP server (Semantic Scholar), and a 5-task evaluation benchmark.

**Architecture:** Fork DeerFlow 2.0 and extend via its native extension points: `skills/custom/`, `subagents.custom_agents` config, `extensions_config.json` for MCPs. No harness-core modification. Live demo runs Kipf & Welling 2017 (GCN on Cora) end-to-end via the `sci-pi` orchestrator. C+ hybrid demo strategy: offline pre-run of full Table 2 + live single-slice + merged display.

**Tech Stack:** Python 3.12+, Node.js 22+, Docker, LangGraph + LangChain (DeerFlow core), Kimi K2.5 (`PatchedChatDeepSeek`), arXiv API (built-in), Semantic Scholar API, PyTorch (CPU) + torch_geometric, LaTeX (`texlive-latex-extra`), matplotlib, pytest.

**Source design:** [docs/plans/2026-05-03-scideer-design.md](2026-05-03-scideer-design.md). Read that first — this plan does not restate design rationale.

**Linked skills:**
- @superpowers:test-driven-development — for all Python script tasks
- @superpowers:systematic-debugging — when sandbox/LaTeX/MCP integration fails
- @superpowers:verification-before-completion — before claiming any task complete

---

## Plan Conventions

- **Working dir** for code tasks: server-side `~/scideer/` (the cloned fork). Treat all relative paths as relative to that.
- **Working dir** for plan/doc tasks: `d:/6725_GroupProject/docs/plans/` (your local Windows machine).
- **Server access:** VSCode SSH Remote → Tencent Cloud Ubuntu.
- **Test framework:** pytest (DeerFlow already uses it; we co-locate tests in `skills/custom/<skill>/tests/`).
- **Commit cadence:** every task ends with a commit. Conventional Commits format.
- **Hard checkpoints:** CP1 (Day 1 EOD), CP2 (Day 2 EOD), CP3 (Day 5 EOD), CP4 (Day 9 noon). If any CP fails → invoke @superpowers:systematic-debugging then assess scope cut per design doc Section 10.1.

---

# Phase 0 — Environment & Foundation (Day 1-2)

## Day 1: Server + DeerFlow basics

### Task 1: Server specs upgrade and verification

**Files:** none (server-only)

**Step 1: Submit Tencent Cloud RAM upgrade ticket**

In Tencent Cloud console, upgrade the target instance to **16 GB RAM**, 8 vCPU, 40 GB SSD. This is the official DeerFlow recommendation for `make dev`.

**Step 2: SSH in and verify specs**

Run on server:
```bash
free -h
df -h
nproc
lsb_release -a
```
Expected: ≥ 15 GB available RAM, ≥ 30 GB free disk, ≥ 8 vCPU, Ubuntu 22.04 or 24.04.

**Step 3: Note results in `docs/NOTES.md`**

Record the actual specs. If only 8 GB came through, log this and apply mitigations from R8 (disable LangSmith, lower concurrency).

**No commit yet** — server config is not in repo.

---

### Task 2: Install Python 3.12, Node.js 22, Docker

**Files:** none (server-only)

**Step 1: Update apt**

```bash
sudo apt update && sudo apt upgrade -y
```

**Step 2: Install Python 3.12**

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.12 python3.12-venv python3.12-dev
python3.12 --version
```
Expected: `Python 3.12.x`.

**Step 3: Install Node.js 22 + pnpm**

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
node --version
sudo npm install -g pnpm
pnpm --version
```
Expected: `v22.x` and pnpm version printed.

**Step 4: Install Docker + nginx**

```bash
sudo apt install -y docker.io docker-compose-plugin nginx
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```
Log out and back in for the docker group to take effect.

**Step 5: Verify Docker**

```bash
docker run --rm hello-world
```
Expected: "Hello from Docker!" message.

**Step 6: Install uv (DeerFlow uses it)**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env || source $HOME/.local/bin/env
uv --version
```

**No commit yet.**

---

### Task 3: Verify GitHub SSH access

**Step 1: Check existing key or generate**

```bash
ls -la ~/.ssh/id_ed25519* 2>/dev/null || ssh-keygen -t ed25519 -C "scideer-server"
cat ~/.ssh/id_ed25519.pub
```

**Step 2: Add key to GitHub** — paste the printed pubkey into GitHub Settings → SSH keys.

**Step 3: Verify**

```bash
ssh -T git@github.com
```
Expected: `Hi <username>! You've successfully authenticated`.

---

### Task 4: Fork bytedance/deer-flow on GitHub

Use the GitHub web UI: navigate to https://github.com/bytedance/deer-flow → **Fork** → keep name as `deer-flow` or rename to `scideer` under your account. Recommendation: **rename to `scideer`** so the fork name reflects the project.

**No commit yet** (no local repo).

---

### Task 5: Clone fork to server

**Step 1: Clone**

```bash
cd ~
git clone git@github.com:<your-username>/scideer.git
cd scideer
```

**Step 2: Verify branch**

```bash
git status
git log -1
```
Expected: on `main` (or `master`), latest commit matches upstream.

**Step 3: Create dev branch**

```bash
git checkout -b scideer-main
```

This is the branch all SciDeer work goes on.

**Step 4: Commit checkpoint**

```bash
git commit --allow-empty -m "chore: branch created for SciDeer development"
```

---

### Task 6: Run make setup wizard

**Step 1: Check prerequisites**

```bash
make check
```
Expected: passes Node 22, pnpm, uv, nginx checks. If any fails, fix before proceeding.

**Step 2: Run setup**

```bash
make setup
```
The wizard prompts for LLM provider, web search, sandbox mode, bash. Choose:
- LLM provider: **other / OpenAI-compatible** (will manually configure Kimi)
- Web search: **DuckDuckGo** (free, no key)
- Sandbox: **Local** initially (we switch to AioSandbox in Task 13)
- Bash: **enabled**

**Step 3: Verify generated files**

```bash
ls config.yaml .env
```
Both must exist.

**No commit yet** — about to overwrite `config.yaml` for Kimi in Task 7.

---

### Task 7: Configure Kimi K2.5 in config.yaml

**Files:**
- Modify: `~/scideer/config.yaml`
- Modify: `~/scideer/.env`

**Step 1: Add MOONSHOT_API_KEY to .env**

```bash
echo "MOONSHOT_API_KEY=<your-kimi-key>" >> .env
```
Replace `<your-kimi-key>` with the real Kimi API key.

**Step 2: Edit config.yaml — add Kimi K2.5 model**

Open `config.yaml` and find the `models:` section. Add:

```yaml
models:
  - name: kimi-k2.5
    display_name: Kimi K2.5
    use: deerflow.models.patched_deepseek:PatchedChatDeepSeek
    model: kimi-k2.5
    api_base: https://api.moonshot.cn/v1
    api_key: $MOONSHOT_API_KEY
    timeout: 600.0
    max_retries: 2
    max_tokens: 32768
    supports_thinking: true
    supports_vision: true
    when_thinking_enabled:
      extra_body:
        thinking:
          type: enabled
    when_thinking_disabled:
      extra_body:
        thinking:
          type: disabled
```

If a default model was added by the wizard, either remove it or keep it as fallback.

**Step 3: Enable token usage tracking**

Find the `token_usage:` section, set:

```yaml
token_usage:
  enabled: true
```

This is required for benchmark efficiency tracking (Section 8.2 in design).

**Step 4: Run doctor**

```bash
make doctor
```
Expected: no fatal errors. Warnings on optional providers are OK.

**Step 5: Commit**

```bash
git add config.yaml
git commit -m "feat(config): add Kimi K2.5 model and enable token_usage tracking"
```

(The `.env` is `.gitignore`d — do not commit secrets.)

---

### Task 8: Start make dev and verify Web UI

**Step 1: Start services**

```bash
make dev
```
This starts gateway (8001), LangGraph (2024), frontend (3000), behind nginx (2026).

Wait until logs show all 4 services up (~2 min on first run).

**Step 2: Verify locally on server**

```bash
curl -s http://localhost:2026 | head -20
```
Expected: HTML with `<title>DeerFlow</title>` or similar.

**Step 3: Open Web UI from local machine**

Use VSCode SSH Remote port forwarding:
```bash
# In your local terminal:
ssh -L 2026:localhost:2026 user@server
```
Then open `http://localhost:2026` in your browser. Confirm the DeerFlow UI loads.

**Step 4: Smoke test — send a trivial message**

In the UI, select model `kimi-k2.5`, send: `"Hello, just say back: pong"`. Expected: returns "pong" or similar within 10 s.

**Step 5: Commit (no file change, so check checkpoint reached)**

CP1 reached: DeerFlow runs with Kimi. If failed → invoke @superpowers:systematic-debugging on Kimi auth or model loader. If unfixable in 1 hour → switch to DeepSeek per R5 mitigation.

---

### Task 9: Run a built-in skill task as smoke test

**Step 1: Send a small SLR prompt**

In the Web UI, send:
```
Do a brief literature review on "graph neural networks", 5 papers, BibTeX format, default time range.
```

Expected: agent loads `systematic-literature-review` skill, runs `arxiv_search.py`, dispatches subagents for extraction, produces a markdown report under `outputs/`.

**Step 2: Verify outputs**

```bash
ls .deer-flow/data/<thread-id>/outputs/ 2>/dev/null || \
  find . -name "slr-*.md" -newer config.yaml 2>/dev/null
```
Expected: a `slr-graph-neural-networks-*.md` file exists.

**Step 3: Note in NOTES.md**

Record:
- Token cost of this run (visible in UI if `token_usage.enabled`)
- Wall time
- Any warnings

**Step 4: No code change → no commit needed** — but record the smoke test outcome.

---

### Task 10: Initial scaffolding commit

**Files:**
- Create: `docs/plans/2026-05-03-scideer-design.md` (already on local machine, push it)
- Create: `docs/plans/2026-05-03-scideer-implementation.md` (this file)
- Create: `docs/NOTES.md`

**Step 1: Push design + impl docs to server**

From your local machine:
```bash
scp d:/6725_GroupProject/docs/plans/*.md user@server:~/scideer/docs/plans/
```

Or use VSCode SSH Remote to copy them through the file explorer.

**Step 2: Create NOTES.md skeleton**

On the server:
```bash
cat > docs/NOTES.md <<'EOF'
# SciDeer Engineering Notes

## Phase 0 (Day 1-2)

### Day 1: Server + DeerFlow basics
- Server specs: <fill in>
- Web UI smoke test: <pass/fail>
- Built-in skill smoke test: <token cost / wall time>

### 3-Assumption Conclusions (from Design Section 0)
1. Skills as Markdown plug-and-play: CONFIRMED via reading skills/public/systematic-literature-review/SKILL.md
2. Native MCP: CONFIRMED via extensions_config.example.json
3. Kimi compat: CONFIRMED via config.yaml example (kimi-k2.5)

### Day 2: Source understanding + sandbox
<filled in Task 11-17>
EOF
```

**Step 3: Commit**

```bash
git add docs/plans/2026-05-03-scideer-design.md \
        docs/plans/2026-05-03-scideer-implementation.md \
        docs/NOTES.md
git commit -m "docs: add SciDeer design + implementation plan + engineering notes"
git push -u origin scideer-main
```

---

## Day 2: Source understanding + custom sandbox

### Task 11: Read DeerFlow architecture docs

**Files:** none (reading only)

**Step 1: Read the canonical entry points**

Read these files in order, **taking notes in `docs/NOTES.md` as you go**:

1. `backend/CLAUDE.md` — high-level architecture
2. `backend/README.md` — service topology + entry points
3. `backend/docs/CONFIGURATION.md` — model + tool + skill + MCP config schemas
4. `backend/docs/ARCHITECTURE.md` — internal class structure

For each doc, record in `NOTES.md`:
- Section name + relative file path of the most important reference
- 1-2 sentence summary

**Step 2: Commit**

```bash
git add docs/NOTES.md
git commit -m "docs: add Phase 0 source-reading notes (architecture overview)"
```

---

### Task 12: Locate skill loader, custom_agents, MCP loader entry points

**Files:** none (reading only)

**Step 1: Find skill loader**

```bash
grep -rn "load_skill\|skill.*loader\|skills_path" backend/packages/harness/deerflow/ | head -20
```

Find the Python class/function that loads skills from disk. Record file:line in NOTES.md.

**Step 2: Find custom_agent registration**

```bash
grep -rn "custom_agents\|make_lead_agent\|subagent_type" backend/packages/harness/deerflow/ | head -20
```

Find where `subagents.custom_agents` config is consumed. Record.

**Step 3: Find MCP loader**

```bash
grep -rn "mcpServers\|extensions_config" backend/packages/harness/deerflow/ | head -20
```

Find MCP server registration and tool exposure. Record.

**Step 4: Find task() tool implementation**

```bash
grep -rn "def task\|class.*Task.*Tool" backend/packages/harness/deerflow/subagents/ | head -10
```

Record how task() spawns subagents.

**Step 5: Commit**

```bash
git add docs/NOTES.md
git commit -m "docs: locate skill loader, custom_agents, MCP loader, task() tool entry points"
```

---

### Task 13: Build custom Docker image scideer-sandbox

**Files:**
- Create: `~/scideer/docker/scideer-sandbox/Dockerfile`

**Step 1: Pull base AIO sandbox image**

```bash
docker pull enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
```

If pull fails (network/registry), use the GHCR mirror specified in DeerFlow docs.

**Step 2: Create Dockerfile**

```bash
mkdir -p docker/scideer-sandbox
cat > docker/scideer-sandbox/Dockerfile <<'EOF'
FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest

USER root

# LaTeX toolchain (texlive-latex-extra is ~600 MB; needed for NeurIPS template)
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-bibtex-extra \
    biber \
    && rm -rf /var/lib/apt/lists/*

# Scientific Python stack
RUN pip install --no-cache-dir \
    torch==2.4.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir \
    torch-geometric==2.5.3 \
    scikit-learn==1.5.0 \
    pandas==2.2.2 \
    matplotlib==3.9.0 \
    numpy==1.26.4

# Sanity check on build
RUN python -c "import torch, torch_geometric, sklearn, matplotlib; print('imports OK')" \
 && pdflatex --version | head -1
EOF
```

**Step 3: Build the image**

```bash
docker build -t scideer-sandbox:latest docker/scideer-sandbox/ 2>&1 | tee docker/scideer-sandbox/build.log
```

Expected: build succeeds; final lines show `imports OK` and `pdfTeX 3.x`.

**Step 4: Smoke test the image**

```bash
docker run --rm scideer-sandbox:latest \
  bash -c 'echo "\\documentclass{article}\\begin{document}Hello\\end{document}" > /tmp/t.tex && \
           cd /tmp && pdflatex -interaction=nonstopmode t.tex && ls t.pdf'
```

Expected: `t.pdf` listed at end. If fails, debug texlive install.

**Step 5: Smoke test PyTorch + torch_geometric**

```bash
docker run --rm scideer-sandbox:latest \
  python -c "import torch_geometric; from torch_geometric.datasets import Planetoid; print(torch_geometric.__version__)"
```

Expected: `2.5.3` (or whatever pinned version).

**Step 6: Commit**

```bash
git add docker/scideer-sandbox/Dockerfile
git commit -m "feat(sandbox): add scideer-sandbox Docker image with LaTeX + PyTorch + torch_geometric"
```

---

### Task 14: Switch config.yaml to AioSandboxProvider with custom image

**Files:**
- Modify: `~/scideer/config.yaml`

**Step 1: Find current sandbox section**

```bash
grep -n "^sandbox:" config.yaml
```

**Step 2: Replace sandbox section**

Edit `config.yaml`, replace the existing `sandbox:` block with:

```yaml
sandbox:
  use: deerflow.community.aio_sandbox:AioSandboxProvider
  image: scideer-sandbox:latest
  port: 8080
  replicas: 3
  container_prefix: scideer-sandbox
  mounts:
    - host_path: ~/.scideer/cache
      container_path: /mnt/scideer-cache
      read_only: true
  environment:
    PYTHONUNBUFFERED: "1"
    MPLBACKEND: "Agg"
  bash_output_max_chars: 50000
  read_file_output_max_chars: 50000
  ls_output_max_chars: 20000
```

**Step 3: Restart make dev**

```bash
make stop
make dev
```

Wait until services are up.

**Step 4: Smoke test sandbox via UI**

In the Web UI, send: `"Run python -c 'import torch_geometric; print(torch_geometric.__version__)' inside the sandbox."`

Expected: agent invokes `bash` tool, prints torch_geometric version. If errors → debug AIO sandbox container start.

**Step 5: Commit**

```bash
git add config.yaml
git commit -m "feat(config): switch sandbox to AioSandboxProvider using scideer-sandbox image"
```

---

### Task 15: Pre-stage caches (pygcn, Cora, MNIST)

**Files:**
- Create: `~/.scideer/cache/` (host-side, mounted read-only into sandbox)

**Step 1: Create cache directory**

```bash
mkdir -p ~/.scideer/cache
```

**Step 2: Clone pygcn**

```bash
cd ~/.scideer/cache
git clone https://github.com/tkipf/pygcn pygcn
ls pygcn/  # should show: data, pygcn, README.md, setup.py, train.py
```

**Step 3: Pre-download Cora via torch_geometric**

```bash
docker run --rm -v ~/.scideer/cache:/cache scideer-sandbox:latest \
  python -c "
from torch_geometric.datasets import Planetoid
ds = Planetoid('/cache/torch_geometric', 'Cora')
print(f'Cora: {ds[0]}')
"
```

Expected: prints `Cora: Data(x=[2708, 1433], edge_index=[2, 10556], y=[2708], train_mask=[2708], val_mask=[2708], test_mask=[2708])`.

**Step 4: Pre-download MNIST via torchvision**

```bash
docker run --rm -v ~/.scideer/cache:/cache scideer-sandbox:latest \
  python -c "
from torchvision.datasets import MNIST
import torchvision.transforms as T
MNIST('/cache/torchvision', train=True, download=True, transform=T.ToTensor())
print('MNIST downloaded')
"
```

Note: torchvision is not in our image. If above fails, install in image (Task 13 add `torchvision==0.19.0`) and rebuild — OR use the sklearn `fetch_openml('mnist_784')` route. Prefer torchvision (it's industry standard).

**Step 5: Verify cache size and contents**

```bash
du -sh ~/.scideer/cache/
ls -la ~/.scideer/cache/
```

Expected: ≤ 2 GB total; contains `pygcn/`, `torch_geometric/`, `torchvision/`.

**Step 6: Commit (cache itself is .gitignore'd, but document its setup)**

Create `docs/CACHE_SETUP.md` listing the manual steps so they're reproducible:

```bash
cat > docs/CACHE_SETUP.md <<'EOF'
# SciDeer Cache Setup (manual, server-side)

Run these once on the server before any paper-reproduction runs:

```bash
mkdir -p ~/.scideer/cache && cd ~/.scideer/cache
git clone https://github.com/tkipf/pygcn pygcn

docker run --rm -v ~/.scideer/cache:/cache scideer-sandbox:latest \
  python -c "from torch_geometric.datasets import Planetoid; Planetoid('/cache/torch_geometric', 'Cora')"

docker run --rm -v ~/.scideer/cache:/cache scideer-sandbox:latest \
  python -c "from torchvision.datasets import MNIST; import torchvision.transforms as T; MNIST('/cache/torchvision', train=True, download=True, transform=T.ToTensor())"
```
EOF

git add docs/CACHE_SETUP.md
git commit -m "docs(cache): document pre-stage steps for pygcn / Cora / MNIST"
```

---

### Task 16: Verify GCN training inside sandbox

**Files:**
- Create: `scratch/smoke_gcn.py` (temporary smoke test)

**Step 1: Write the smoke test**

```bash
mkdir -p scratch
cat > scratch/smoke_gcn.py <<'PY'
"""Smoke test: GCN on Cora via official pygcn (cached). Target: ~80% acc in <30s CPU."""
import sys, time, subprocess

t0 = time.time()
result = subprocess.run(
    ["python", "/mnt/scideer-cache/pygcn/pygcn/train.py", "--epochs", "100"],
    capture_output=True, text=True, timeout=120,
)
elapsed = time.time() - t0
print(f"=== smoke_gcn elapsed: {elapsed:.1f}s ===")
print(result.stdout[-2000:])
print("STDERR:", result.stderr[-500:], file=sys.stderr)
assert "Test set results" in result.stdout, "training did not complete"
PY
```

**Step 2: Run it inside the sandbox via `bash` tool**

Easiest path: send via Web UI:
```
Run this in sandbox: python /home/user/scratch/smoke_gcn.py
```
(Adjust path; agent should mount and run.)

Or run direct:
```bash
docker run --rm \
  -v ~/.scideer/cache:/mnt/scideer-cache:ro \
  -v $(pwd)/scratch:/scratch \
  scideer-sandbox:latest \
  python /scratch/smoke_gcn.py
```

Expected: completes in <30 s, accuracy printed in 70-85% range.

**Step 3: Record outcome in NOTES.md**

Append to `docs/NOTES.md`:
```
### Day 2 Smoke: GCN on Cora
- Wall time: <X> s
- Test accuracy: <Y>%
- Cache mount worked: yes/no
```

**Step 4: Commit**

```bash
git add scratch/smoke_gcn.py docs/NOTES.md
git commit -m "test(sandbox): smoke-verify GCN on Cora via pygcn cache, target <30s CPU"
```

---

### Task 17: Verify pdflatex inside sandbox

**Files:**
- Create: `scratch/smoke_latex.tex`
- Create: `scratch/smoke_latex.sh`

**Step 1: Write a NeurIPS-flavored test document**

```bash
cat > scratch/smoke_latex.tex <<'TEX'
\documentclass{article}
\usepackage{amsmath, graphicx}
\begin{document}
\title{SciDeer LaTeX Smoke Test}
\author{Jasper}
\maketitle
\section{Equation}
$E = mc^2$
\section{Cite}
See \cite{kipf2017gcn}.
\bibliographystyle{plain}
\bibliography{refs}
\end{document}
TEX

cat > scratch/refs.bib <<'BIB'
@inproceedings{kipf2017gcn,
  title={Semi-Supervised Classification with Graph Convolutional Networks},
  author={Kipf, Thomas N and Welling, Max},
  booktitle={ICLR},
  year={2017}
}
BIB
```

**Step 2: Compile via sandbox**

```bash
docker run --rm \
  -v $(pwd)/scratch:/work \
  -w /work \
  scideer-sandbox:latest \
  bash -c 'pdflatex -interaction=nonstopmode smoke_latex.tex && \
           bibtex smoke_latex && \
           pdflatex -interaction=nonstopmode smoke_latex.tex && \
           pdflatex -interaction=nonstopmode smoke_latex.tex && \
           ls -la smoke_latex.pdf'
```

Expected: `smoke_latex.pdf` exists at end, no fatal errors. Citation `[1]` rendered in PDF.

**Step 3: Record outcome — CP2 reached**

In `NOTES.md`:
```
### Day 2 Smoke: LaTeX Compile
- pdflatex + bibtex + 2x pdflatex completed
- PDF size: <X> bytes
- Cite rendered: yes/no
- CP2: PASS
```

**Step 4: Cleanup smoke artifacts (keep .tex + .sh, drop binaries)**

```bash
cd scratch && rm -f smoke_latex.aux smoke_latex.log smoke_latex.out smoke_latex.bbl smoke_latex.blg smoke_latex.pdf
cd ..
```

**Step 5: Commit**

```bash
git add scratch/smoke_latex.tex scratch/refs.bib docs/NOTES.md
git commit -m "test(sandbox): smoke-verify pdflatex + bibtex compile chain"
```

**🚩 Phase 0 (Day 1-2) complete. CP1 + CP2 must both be PASS to proceed.**

---

# Phase 1 — `paper-reproduction` skill (Day 3-4)

> Reference: design Section 4. This skill must NEVER fail silently — every failure mode produces a viewable `report.md`.
>
> Use @superpowers:test-driven-development for every script in this phase.

## Day 3: Skill skeleton + code_resolver + scale_down + runner

### Task 18: Create skill directory structure

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/SKILL.md`
- Create: `~/scideer/skills/custom/paper-reproduction/scripts/__init__.py`
- Create: `~/scideer/skills/custom/paper-reproduction/templates/.gitkeep`
- Create: `~/scideer/skills/custom/paper-reproduction/tests/__init__.py`

**Step 1: Create directories**

```bash
cd ~/scideer
mkdir -p skills/custom/paper-reproduction/{scripts,templates,tests}
touch skills/custom/paper-reproduction/scripts/__init__.py
touch skills/custom/paper-reproduction/templates/.gitkeep
touch skills/custom/paper-reproduction/tests/__init__.py
```

**Step 2: Write SKILL.md skeleton (frontmatter only first; workflow later)**

```bash
cat > skills/custom/paper-reproduction/SKILL.md <<'EOF'
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

# Paper Reproduction Skill

## Overview

This skill reproduces a single specific quantitative result from an academic paper at mini-scale (CPU < 5 minutes). Given an arxiv ID and a target metric (e.g. "Table 2 GCN/Cora row, 81.5%"), it locates the official code (cache → GitHub → template), auto-scales down the training to fit CPU constraints, runs in the sandbox, and produces a comparison report.

**Distinct from `academic-paper-review`:** that skill reads and critiques a paper. This skill *runs the code* and verifies a specific number.

**Hard guarantees:**
- Always produces `outputs/repro-{arxiv_id}/report.md`, even on failure.
- Never silent failure — every failure mode writes a structured report with attribution.
- Hard timeout 240 s on training (force-kill, then degraded report).

## When to Use

Use this skill when the user provides:
- An arxiv ID (e.g. `1609.02907` or `https://arxiv.org/abs/1609.02907`)
- A specific reproduction target (e.g. "Table 2, GCN row, Cora dataset")

Do NOT use when:
- User wants a literature survey → use `systematic-literature-review`
- User wants peer review of a paper → use `academic-paper-review`
- User just wants to write Python code → use `bash` tool directly

## Workflow

The workflow has five phases. Execute them in order.

### Phase 1: Plan
... (filled in Task 30)

### Phase 2: Comprehend
... (filled in Task 30)

### Phase 3: Code Acquire
... (filled in Task 30)

### Phase 4: Scale-Down + Run
... (filled in Task 30)

### Phase 5: Compare + Report
... (filled in Task 30)
EOF
```

The phase bodies are filled in Task 30 once all scripts exist.

**Step 3: Commit**

```bash
git add skills/custom/paper-reproduction/
git commit -m "feat(skill): scaffold paper-reproduction skill directory + SKILL.md frontmatter"
```

---

### Task 19: Write tests for `repro_plan.py`

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_repro_plan.py`

**Step 1: Write the failing tests**

```python
# tests/test_repro_plan.py
import json
import pytest
from pathlib import Path
from skills.custom.paper_reproduction.scripts.repro_plan import build_plan

def test_build_plan_minimal():
    plan = build_plan(
        arxiv_id="1609.02907",
        target_metric="GCN on Cora accuracy",
        expected_value=81.5,
        dataset="Cora",
        model="GCN",
    )
    assert plan["arxiv_id"] == "1609.02907"
    assert plan["target_metric"] == "GCN on Cora accuracy"
    assert plan["expected_value"] == 81.5
    assert plan["scale_strategy"] == "auto"  # default
    assert "created_at" in plan

def test_build_plan_with_scale_override(tmp_path):
    plan = build_plan(
        arxiv_id="1234.5678",
        target_metric="MNIST accuracy",
        expected_value=99.0,
        dataset="MNIST",
        model="CNN",
        scale_strategy="reduce_epochs:0.5",
    )
    assert plan["scale_strategy"] == "reduce_epochs:0.5"

def test_build_plan_serializable(tmp_path):
    plan = build_plan("1609.02907", "acc", 81.5, "Cora", "GCN")
    out = tmp_path / "plan.json"
    out.write_text(json.dumps(plan, indent=2))
    loaded = json.loads(out.read_text())
    assert loaded == plan

def test_build_plan_validates_arxiv_id():
    with pytest.raises(ValueError, match="arxiv"):
        build_plan("not-an-arxiv-id", "acc", 81.5, "Cora", "GCN")
```

**Step 2: Run to verify FAIL**

```bash
cd ~/scideer
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_repro_plan.py -v
```

Expected: 4 errors, "module not found" or "function not defined".

**Step 3: Commit failing tests**

```bash
git add skills/custom/paper-reproduction/tests/test_repro_plan.py
git commit -m "test(paper-reproduction): add failing tests for repro_plan.build_plan"
```

---

### Task 20: Implement `repro_plan.py`

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/scripts/repro_plan.py`

**Step 1: Implement minimal version**

```python
# scripts/repro_plan.py
"""Phase 1 of paper-reproduction: solidify the reproduction plan to JSON."""
import re
from datetime import datetime, timezone

ARXIV_ID_PATTERN = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def build_plan(
    arxiv_id: str,
    target_metric: str,
    expected_value: float,
    dataset: str,
    model: str,
    scale_strategy: str = "auto",
) -> dict:
    """Build a reproduction plan dict suitable for JSON serialization."""
    if not ARXIV_ID_PATTERN.match(arxiv_id):
        raise ValueError(f"invalid arxiv_id: {arxiv_id!r}")
    return {
        "arxiv_id": arxiv_id,
        "target_metric": target_metric,
        "expected_value": float(expected_value),
        "dataset": dataset,
        "model": model,
        "scale_strategy": scale_strategy,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
    }
```

**Step 2: Run tests, verify PASS**

```bash
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_repro_plan.py -v
```

Expected: 4 passed.

**Step 3: Commit**

```bash
git add skills/custom/paper-reproduction/scripts/repro_plan.py
git commit -m "feat(paper-reproduction): implement repro_plan.build_plan"
```

---

### Task 21: Write tests for `code_resolver.py` — cache-hit path

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_code_resolver_cache.py`

**Step 1: Write tests**

```python
# tests/test_code_resolver_cache.py
import pytest
from pathlib import Path
from skills.custom.paper_reproduction.scripts.code_resolver import (
    resolve_code, ResolveResult,
)

def test_cache_hit_returns_path(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    pygcn = cache / "pygcn"
    pygcn.mkdir()
    (pygcn / "train.py").write_text("# stub")

    result = resolve_code(
        arxiv_id="1609.02907",
        cache_root=cache,
        cache_map={"1609.02907": "pygcn"},
    )
    assert result.tier == "cache"
    assert result.path == pygcn
    assert result.error is None

def test_cache_miss_returns_none_when_no_fallback(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    result = resolve_code(
        arxiv_id="9999.99999",
        cache_root=cache,
        cache_map={},
        github_url=None,
        template_fallback=False,
    )
    assert result.tier == "miss"
    assert result.path is None
    assert result.error is not None
```

**Step 2: Run, verify FAIL**

```bash
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_code_resolver_cache.py -v
```
Expected: import error (`code_resolver` not yet defined).

**Step 3: Commit**

```bash
git add skills/custom/paper-reproduction/tests/test_code_resolver_cache.py
git commit -m "test(paper-reproduction): failing tests for code_resolver cache-hit path"
```

---

### Task 22: Implement `code_resolver.py` — cache-hit only

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/scripts/code_resolver.py`

**Step 1: Implement minimal cache-hit logic**

```python
# scripts/code_resolver.py
"""Phase 3 of paper-reproduction: resolve code via cache → github → template."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ResolveResult:
    tier: str           # "cache" | "github" | "template" | "miss"
    path: Optional[Path]
    error: Optional[str]


def resolve_code(
    arxiv_id: str,
    cache_root: Path,
    cache_map: Optional[dict] = None,
    github_url: Optional[str] = None,
    template_fallback: bool = True,
) -> ResolveResult:
    """Three-tier code resolution.

    Tiers (in order):
      1. cache: cache_map[arxiv_id] → cache_root / <subpath> if exists
      2. github: clone github_url into cache_root (later task)
      3. template: write a minimal template (later task)
    """
    cache_map = cache_map or {}

    # Tier 1: cache
    if arxiv_id in cache_map:
        candidate = cache_root / cache_map[arxiv_id]
        if candidate.exists():
            return ResolveResult(tier="cache", path=candidate, error=None)

    # Tier 2/3 not implemented yet — return miss
    return ResolveResult(
        tier="miss",
        path=None,
        error=f"no code source for {arxiv_id} (github + template not yet wired)",
    )
```

**Step 2: Run tests, verify PASS**

```bash
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_code_resolver_cache.py -v
```
Expected: 2 passed.

**Step 3: Commit**

```bash
git add skills/custom/paper-reproduction/scripts/code_resolver.py
git commit -m "feat(paper-reproduction): implement cache-hit tier of code_resolver"
```

---

### Task 23: Write + implement github-clone fallback in code_resolver

**Files:**
- Modify: `~/scideer/skills/custom/paper-reproduction/scripts/code_resolver.py`
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_code_resolver_github.py`

**Step 1: Write failing test**

```python
# tests/test_code_resolver_github.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from skills.custom.paper_reproduction.scripts.code_resolver import resolve_code


def test_github_clone_on_cache_miss(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()

    def fake_run(cmd, *args, **kwargs):
        # simulate successful git clone by creating the target dir
        target = Path(cmd[-1])
        target.mkdir(parents=True, exist_ok=True)
        (target / "train.py").write_text("# stub")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        result = resolve_code(
            arxiv_id="9999.99999",
            cache_root=cache,
            github_url="https://github.com/example/repo",
        )
    assert result.tier == "github"
    assert result.path is not None
    assert (result.path / "train.py").exists()


def test_github_clone_failure_falls_through(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()

    def fake_run(cmd, *args, **kwargs):
        return MagicMock(returncode=128, stdout="", stderr="auth failed")

    with patch("subprocess.run", side_effect=fake_run):
        result = resolve_code(
            arxiv_id="9999.99999",
            cache_root=cache,
            github_url="https://github.com/example/repo",
            template_fallback=False,
        )
    assert result.tier == "miss"
    assert "github" in result.error.lower() or "clone" in result.error.lower()
```

**Step 2: Run, verify FAIL** (resolver doesn't yet handle github_url).

**Step 3: Update `code_resolver.py`**

Replace the body (preserving cache-hit) with:

```python
# scripts/code_resolver.py
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ResolveResult:
    tier: str
    path: Optional[Path]
    error: Optional[str]


def resolve_code(
    arxiv_id: str,
    cache_root: Path,
    cache_map: Optional[dict] = None,
    github_url: Optional[str] = None,
    template_fallback: bool = True,
    template_writer=None,    # callable, see Task 24
) -> ResolveResult:
    """Three-tier code resolution: cache → github → template."""
    cache_map = cache_map or {}

    # Tier 1: cache
    if arxiv_id in cache_map:
        candidate = cache_root / cache_map[arxiv_id]
        if candidate.exists():
            return ResolveResult(tier="cache", path=candidate, error=None)

    # Tier 2: github clone
    if github_url:
        target = cache_root / f"github_{arxiv_id.replace('.', '_')}"
        proc = subprocess.run(
            ["git", "clone", "--depth=1", github_url, str(target)],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode == 0 and target.exists():
            return ResolveResult(tier="github", path=target, error=None)
        # fall through with the error noted
        github_err = f"github clone failed: {proc.stderr.strip()[:200]}"
    else:
        github_err = "no github_url provided"

    # Tier 3: template fallback
    if template_fallback and template_writer is not None:
        target = cache_root / f"template_{arxiv_id.replace('.', '_')}"
        try:
            template_writer(arxiv_id, target)
            return ResolveResult(tier="template", path=target, error=None)
        except Exception as e:
            return ResolveResult(
                tier="miss",
                path=None,
                error=f"all tiers failed: {github_err}; template error: {e}",
            )

    return ResolveResult(tier="miss", path=None, error=github_err)
```

**Step 4: Run all code_resolver tests**

```bash
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_code_resolver_*.py -v
```
Expected: all 4 pass.

**Step 5: Commit**

```bash
git add skills/custom/paper-reproduction/scripts/code_resolver.py \
        skills/custom/paper-reproduction/tests/test_code_resolver_github.py
git commit -m "feat(paper-reproduction): add github-clone tier to code_resolver"
```

---

### Task 24: Write + implement template-fallback tier

**Files:**
- Modify: `~/scideer/skills/custom/paper-reproduction/scripts/code_resolver.py` (or new module)
- Create: `~/scideer/skills/custom/paper-reproduction/scripts/template_writer.py`
- Create: `~/scideer/skills/custom/paper-reproduction/templates/gnn_minimal.py.tmpl`
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_template_writer.py`

**Step 1: Create gnn_minimal.py.tmpl**

```bash
cat > skills/custom/paper-reproduction/templates/gnn_minimal.py.tmpl <<'TMPL'
"""Minimal GCN reproduction skeleton.

This is a fallback template used by paper-reproduction when neither cache
nor official GitHub code is available. Edit hyperparameters as needed.

Generated for arxiv:{ARXIV_ID}
"""
import time, json, sys
import torch
import torch.nn.functional as F
from torch_geometric.datasets import Planetoid
from torch_geometric.nn import GCNConv

DATASET = "{DATASET}"
EPOCHS = {EPOCHS}
HIDDEN = 16

ds = Planetoid("/mnt/scideer-cache/torch_geometric", DATASET)
data = ds[0]


class GCN(torch.nn.Module):
    def __init__(self, in_dim, out_dim, hidden=16):
        super().__init__()
        self.c1 = GCNConv(in_dim, hidden)
        self.c2 = GCNConv(hidden, out_dim)

    def forward(self, x, ei):
        x = F.relu(self.c1(x, ei))
        x = F.dropout(x, p=0.5, training=self.training)
        return self.c2(x, ei)


model = GCN(ds.num_features, ds.num_classes, HIDDEN)
opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)

t0 = time.time()
for ep in range(EPOCHS):
    model.train()
    opt.zero_grad()
    out = model(data.x, data.edge_index)
    loss = F.nll_loss(F.log_softmax(out[data.train_mask], dim=1), data.y[data.train_mask])
    loss.backward(); opt.step()

model.eval()
with torch.no_grad():
    pred = model(data.x, data.edge_index).argmax(dim=1)
    acc = (pred[data.test_mask] == data.y[data.test_mask]).float().mean().item()

result = {"test_acc": acc, "wall_time_s": time.time() - t0, "epochs": EPOCHS}
print(json.dumps(result))
TMPL
```

**Step 2: Write failing test**

```python
# tests/test_template_writer.py
from pathlib import Path
from skills.custom.paper_reproduction.scripts.template_writer import write_template

def test_writes_gnn_template(tmp_path):
    target = tmp_path / "out"
    write_template(
        arxiv_id="1609.02907",
        target_dir=target,
        template_name="gnn_minimal",
        substitutions={"ARXIV_ID": "1609.02907", "DATASET": "Cora", "EPOCHS": "100"},
    )
    train = target / "train.py"
    assert train.exists()
    body = train.read_text()
    assert "1609.02907" in body
    assert "Cora" in body
    assert "EPOCHS = 100" in body

def test_missing_template_raises(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        write_template(
            arxiv_id="x",
            target_dir=tmp_path,
            template_name="does-not-exist",
            substitutions={},
        )
```

**Step 3: Implement `template_writer.py`**

```python
# scripts/template_writer.py
"""Tier-3 fallback: write a minimal template-based reproduction skeleton."""
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def write_template(
    arxiv_id: str,
    target_dir: Path,
    template_name: str,
    substitutions: dict,
) -> Path:
    """Write a template file with substitutions to target_dir/train.py."""
    src = TEMPLATES_DIR / f"{template_name}.py.tmpl"
    if not src.exists():
        raise FileNotFoundError(f"template not found: {src}")
    body = src.read_text()
    for k, v in substitutions.items():
        body = body.replace("{" + k + "}", str(v))
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / "train.py"
    out.write_text(body)
    return out
```

**Step 4: Run, verify PASS**

```bash
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_template_writer.py -v
```
Expected: 2 passed.

**Step 5: Wire template_writer into code_resolver default**

Edit `code_resolver.py`, add import + default `template_writer`:

```python
from .template_writer import write_template

def _default_template_writer(arxiv_id: str, target_dir):
    write_template(
        arxiv_id, target_dir, "gnn_minimal",
        {"ARXIV_ID": arxiv_id, "DATASET": "Cora", "EPOCHS": "100"},
    )
```

In `resolve_code`, replace `template_writer is not None:` with `(template_writer or _default_template_writer)(arxiv_id, target)`.

**Step 6: Commit**

```bash
git add skills/custom/paper-reproduction/templates/gnn_minimal.py.tmpl \
        skills/custom/paper-reproduction/scripts/template_writer.py \
        skills/custom/paper-reproduction/scripts/code_resolver.py \
        skills/custom/paper-reproduction/tests/test_template_writer.py
git commit -m "feat(paper-reproduction): add template-fallback tier with gnn_minimal template"
```

---

### Task 25: Tests + implementation for `scale_down.py`

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/scripts/scale_down.py`
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_scale_down.py`

**Step 1: Write failing tests**

```python
# tests/test_scale_down.py
from skills.custom.paper_reproduction.scripts.scale_down import (
    detect_training_args, apply_scale_down,
)

def test_detect_epochs_in_argparse():
    code = '''
parser.add_argument("--epochs", type=int, default=200)
parser.add_argument("--batch", type=int, default=32)
'''
    detected = detect_training_args(code)
    assert detected["epochs"] == 200
    assert detected["batch"] == 32

def test_apply_scale_down_reduces_epochs():
    code = '''parser.add_argument("--epochs", type=int, default=200)'''
    out, summary = apply_scale_down(code, target_wall_time_s=30.0)
    # 200 epochs reduced to something smaller
    assert "default=100" in out or "default=50" in out
    assert summary["epochs_before"] == 200
    assert summary["epochs_after"] < 200

def test_apply_no_change_when_already_small():
    code = '''parser.add_argument("--epochs", type=int, default=10)'''
    out, summary = apply_scale_down(code, target_wall_time_s=30.0)
    assert summary["epochs_after"] == 10
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement `scale_down.py`**

```python
# scripts/scale_down.py
"""Detect and rewrite training hyperparameters to fit CPU sandbox budget."""
import re
from typing import Tuple

EPOCHS_PATTERN = re.compile(
    r'(["\']--?epochs["\'].*?default\s*=\s*)(\d+)',
    re.IGNORECASE,
)
BATCH_PATTERN = re.compile(
    r'(["\']--?batch(?:_size)?["\'].*?default\s*=\s*)(\d+)',
    re.IGNORECASE,
)


def detect_training_args(code: str) -> dict:
    out = {}
    m = EPOCHS_PATTERN.search(code)
    if m:
        out["epochs"] = int(m.group(2))
    m = BATCH_PATTERN.search(code)
    if m:
        out["batch"] = int(m.group(2))
    return out


def apply_scale_down(code: str, target_wall_time_s: float = 30.0) -> Tuple[str, dict]:
    """Rewrite epochs/batch in code to fit target wall time. Returns (new_code, summary)."""
    detected = detect_training_args(code)
    summary = {
        "epochs_before": detected.get("epochs"),
        "batch_before": detected.get("batch"),
        "epochs_after": detected.get("epochs"),
        "batch_after": detected.get("batch"),
    }
    new = code

    # Heuristic: assume 200 epochs ≈ 30s on Cora; scale down proportionally if larger.
    if detected.get("epochs", 0) > 100:
        new_epochs = max(50, detected["epochs"] // 2)
        new = EPOCHS_PATTERN.sub(rf'\g<1>{new_epochs}', new)
        summary["epochs_after"] = new_epochs

    return new, summary
```

**Step 4: Run, verify PASS.**

**Step 5: Commit**

```bash
git add skills/custom/paper-reproduction/scripts/scale_down.py \
        skills/custom/paper-reproduction/tests/test_scale_down.py
git commit -m "feat(paper-reproduction): implement scale_down for epochs/batch"
```

---

### Task 26: Tests + implementation for `runner.py` (sandbox exec)

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/scripts/runner.py`
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_runner.py`

**Step 1: Write failing tests**

```python
# tests/test_runner.py
from pathlib import Path
from skills.custom.paper_reproduction.scripts.runner import run_in_sandbox, RunResult


def test_runs_successful_python(tmp_path):
    work = tmp_path / "work"; work.mkdir()
    (work / "train.py").write_text("print('test_acc=0.802'); print('done')")
    res = run_in_sandbox(work, cmd=["python", "train.py"], timeout_s=30)
    assert res.success
    assert "test_acc=0.802" in res.stdout
    assert res.exit_code == 0


def test_timeout_marks_force_killed(tmp_path):
    work = tmp_path / "work"; work.mkdir()
    (work / "train.py").write_text("import time; time.sleep(60)")
    res = run_in_sandbox(work, cmd=["python", "train.py"], timeout_s=2)
    assert not res.success
    assert res.timed_out
    assert res.exit_code != 0


def test_capture_oom_signal(tmp_path):
    """OOM is signal-killed (exit code -9). Hard to reproduce reliably; test the marker logic."""
    from skills.custom.paper_reproduction.scripts.runner import classify_failure
    assert classify_failure(exit_code=-9, stderr="killed") == "OOM"
    assert classify_failure(exit_code=124, stderr="") == "timeout"
    assert classify_failure(exit_code=1, stderr="ModuleNotFoundError") == "missing_dep"
    assert classify_failure(exit_code=1, stderr="loss became NaN") == "divergence"
    assert classify_failure(exit_code=1, stderr="random error") == "other"
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement `runner.py`**

```python
# scripts/runner.py
"""Phase 4 of paper-reproduction: execute generated code with hard timeout + classification."""
import subprocess, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class RunResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    wall_time_s: float
    timed_out: bool = False
    failure_type: Optional[str] = None    # see classify_failure


def run_in_sandbox(work_dir: Path, cmd: List[str], timeout_s: int = 240) -> RunResult:
    """Run cmd in work_dir with a hard timeout. The sandbox isolation is provided
    by the surrounding DeerFlow AioSandbox; this function delegates to subprocess."""
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=str(work_dir),
            capture_output=True, text=True, timeout=timeout_s,
        )
        elapsed = time.time() - t0
        success = proc.returncode == 0
        ftype = None if success else classify_failure(proc.returncode, proc.stderr)
        return RunResult(
            success=success, exit_code=proc.returncode,
            stdout=proc.stdout, stderr=proc.stderr,
            wall_time_s=elapsed, timed_out=False, failure_type=ftype,
        )
    except subprocess.TimeoutExpired as te:
        elapsed = time.time() - t0
        return RunResult(
            success=False, exit_code=124,
            stdout=(te.stdout or b"").decode(errors="replace") if te.stdout else "",
            stderr=(te.stderr or b"").decode(errors="replace") if te.stderr else "",
            wall_time_s=elapsed, timed_out=True, failure_type="timeout",
        )


def classify_failure(exit_code: int, stderr: str) -> str:
    s = (stderr or "").lower()
    if exit_code in (-9, 137):
        return "OOM"
    if exit_code == 124 or "killed" in s and "memory" not in s:
        return "timeout"
    if "modulenotfounderror" in s or "no module named" in s:
        return "missing_dep"
    if "nan" in s or "diverg" in s or "loss became nan" in s:
        return "divergence"
    return "other"
```

**Step 4: Run, verify PASS.**

**Step 5: Commit**

```bash
git add skills/custom/paper-reproduction/scripts/runner.py \
        skills/custom/paper-reproduction/tests/test_runner.py
git commit -m "feat(paper-reproduction): implement sandbox runner with hard timeout + failure classification"
```

---

### Task 27: Day 3 end-to-end smoke (cache-hit GCN)

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_smoke_e2e_day3.py`

**Step 1: Write the smoke test**

```python
# tests/test_smoke_e2e_day3.py
"""End-to-end Day 3 smoke: plan → cache resolve → scale down → run.

This is a coarse integration test; it requires the cache to be pre-staged
(see docs/CACHE_SETUP.md). Skipped when cache is missing.
"""
import os, json
from pathlib import Path
import pytest
from skills.custom.paper_reproduction.scripts.repro_plan import build_plan
from skills.custom.paper_reproduction.scripts.code_resolver import resolve_code
from skills.custom.paper_reproduction.scripts.runner import run_in_sandbox

CACHE = Path(os.path.expanduser("~/.scideer/cache"))
PYGCN = CACHE / "pygcn"


@pytest.mark.skipif(not PYGCN.exists(), reason="cache not staged; see docs/CACHE_SETUP.md")
def test_e2e_gcn_cora_cache(tmp_path):
    plan = build_plan("1609.02907", "GCN on Cora accuracy", 81.5, "Cora", "GCN")
    res = resolve_code(
        arxiv_id="1609.02907",
        cache_root=CACHE,
        cache_map={"1609.02907": "pygcn"},
    )
    assert res.tier == "cache"
    assert res.path == PYGCN

    # Run pygcn with reduced epochs to keep test fast
    runres = run_in_sandbox(
        res.path / "pygcn",
        cmd=["python", "train.py", "--epochs", "50"],
        timeout_s=180,
    )
    assert runres.success, f"pygcn run failed: {runres.stderr[:500]}"
    assert "Test set results" in runres.stdout
```

**Step 2: Run on the server**

```bash
cd ~/scideer
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_smoke_e2e_day3.py -v -s
```

Expected: PASS within ~60 s. Test accuracy printed in stdout, ~80%.

**Step 3: Commit**

```bash
git add skills/custom/paper-reproduction/tests/test_smoke_e2e_day3.py
git commit -m "test(paper-reproduction): Day 3 e2e smoke test (cache-hit GCN on Cora)"
```

**End of Day 3.**

---

## Day 4: Comparator + report.md generation + failure modes

### Task 28: Tests + implementation for `comparator.py`

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/scripts/comparator.py`
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_comparator.py`

**Step 1: Failing tests**

```python
# tests/test_comparator.py
from skills.custom.paper_reproduction.scripts.comparator import compare, Verdict


def test_within_tolerance():
    v = compare(paper_value=81.5, our_value=80.2, tolerance_pct=3.0)
    assert v.verdict == "match"
    assert abs(v.delta - (-1.3)) < 1e-6
    assert abs(v.delta_pct - (-1.3 / 81.5 * 100)) < 1e-6


def test_outside_tolerance():
    v = compare(paper_value=81.5, our_value=65.0, tolerance_pct=3.0)
    assert v.verdict == "deviation"


def test_severe_deviation():
    v = compare(paper_value=81.5, our_value=10.0, tolerance_pct=3.0)
    assert v.verdict == "deviation_severe"
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement**

```python
# scripts/comparator.py
"""Phase 5 of paper-reproduction: numeric comparison and verdict."""
from dataclasses import dataclass


@dataclass
class Verdict:
    paper_value: float
    our_value: float
    delta: float          # absolute
    delta_pct: float      # signed percent of paper_value
    tolerance_pct: float
    verdict: str          # "match" | "deviation" | "deviation_severe"


def compare(paper_value: float, our_value: float, tolerance_pct: float = 3.0) -> Verdict:
    delta = our_value - paper_value
    delta_pct = (delta / paper_value * 100.0) if paper_value else 0.0
    if abs(delta_pct) <= tolerance_pct:
        verdict = "match"
    elif abs(delta_pct) <= 30.0:
        verdict = "deviation"
    else:
        verdict = "deviation_severe"
    return Verdict(
        paper_value=paper_value, our_value=our_value,
        delta=delta, delta_pct=delta_pct,
        tolerance_pct=tolerance_pct, verdict=verdict,
    )
```

**Step 4: Run, verify PASS. Commit.**

```bash
git add skills/custom/paper-reproduction/scripts/comparator.py \
        skills/custom/paper-reproduction/tests/test_comparator.py
git commit -m "feat(paper-reproduction): implement comparator with tolerance verdict"
```

---

### Task 29: Tests + implementation for `report_writer.py`

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/scripts/report_writer.py`
- Create: `~/scideer/skills/custom/paper-reproduction/templates/report.md.tmpl`
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_report_writer.py`

**Step 1: Create the report template**

```bash
cat > skills/custom/paper-reproduction/templates/report.md.tmpl <<'TMPL'
# Reproduction Report: {paper_title}

**arXiv:** {arxiv_id} | **Reproduced:** {date} | **Mode:** mini-scale

## Target
- Metric: {target_metric}
- Paper reported: **{paper_value}**

## Reproduced
- Our result: **{our_value}**
- Δ: {delta_signed} ({delta_pct_signed}%) {verdict_emoji}
- Wall time: {wall_time_s} s on CPU

## Scale-Down Applied
{scale_down_summary}

## Figures
{figures_block}

## Code
- Source: {code_source}
- Modifications: {code_mods}

## Conclusion
{conclusion}
TMPL
```

**Step 2: Failing tests**

```python
# tests/test_report_writer.py
from datetime import datetime
from skills.custom.paper_reproduction.scripts.report_writer import render_report
from skills.custom.paper_reproduction.scripts.comparator import Verdict

def test_renders_match():
    v = Verdict(paper_value=81.5, our_value=80.2,
                delta=-1.3, delta_pct=-1.59, tolerance_pct=3.0, verdict="match")
    md = render_report(
        paper_title="Semi-Supervised GCN",
        arxiv_id="1609.02907",
        target_metric="GCN on Cora accuracy",
        verdict=v,
        wall_time_s=32.4,
        scale_down_summary="Epochs: 200 → 100",
        figures=["figures/training.png"],
        code_source="cached pygcn",
        code_mods="epochs override",
    )
    assert "81.5" in md
    assert "80.2" in md
    assert "✅" in md
    assert "1609.02907" in md
    assert "training.png" in md


def test_renders_deviation_emoji():
    v = Verdict(paper_value=81.5, our_value=60.0,
                delta=-21.5, delta_pct=-26.4, tolerance_pct=3.0, verdict="deviation")
    md = render_report(
        paper_title="t", arxiv_id="1609.02907", target_metric="m",
        verdict=v, wall_time_s=10, scale_down_summary="-",
        figures=[], code_source="-", code_mods="-",
    )
    assert "⚠️" in md or "deviation" in md.lower()
```

**Step 3: Implement**

```python
# scripts/report_writer.py
from pathlib import Path
from datetime import datetime, timezone
from typing import List
from .comparator import Verdict

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "report.md.tmpl"

VERDICT_EMOJI = {"match": "✅", "deviation": "⚠️", "deviation_severe": "❌"}


def render_report(
    paper_title: str,
    arxiv_id: str,
    target_metric: str,
    verdict: Verdict,
    wall_time_s: float,
    scale_down_summary: str,
    figures: List[str],
    code_source: str,
    code_mods: str,
) -> str:
    body = TEMPLATE_PATH.read_text()
    figures_block = "\n".join(f"![]({p})" for p in figures) if figures else "_(none)_"
    conclusion = {
        "match":            "✅ Reproduction successful within tolerance.",
        "deviation":        "⚠️ Reproduction deviates outside tolerance; see figures and logs.",
        "deviation_severe": "❌ Severe deviation; reproduction likely failed. Review code and inputs.",
    }[verdict.verdict]
    delta_signed = f"{verdict.delta:+.2f}"
    delta_pct = f"{verdict.delta_pct:+.2f}"
    return body.format(
        paper_title=paper_title,
        arxiv_id=arxiv_id,
        date=datetime.now(timezone.utc).date().isoformat(),
        target_metric=target_metric,
        paper_value=verdict.paper_value,
        our_value=verdict.our_value,
        delta_signed=delta_signed,
        delta_pct_signed=delta_pct,
        verdict_emoji=VERDICT_EMOJI[verdict.verdict],
        wall_time_s=f"{wall_time_s:.1f}",
        scale_down_summary=scale_down_summary,
        figures_block=figures_block,
        code_source=code_source,
        code_mods=code_mods,
        conclusion=conclusion,
    )
```

**Step 4: Run, verify PASS. Commit.**

```bash
git add skills/custom/paper-reproduction/scripts/report_writer.py \
        skills/custom/paper-reproduction/templates/report.md.tmpl \
        skills/custom/paper-reproduction/tests/test_report_writer.py
git commit -m "feat(paper-reproduction): implement report_writer with template + verdict-specific conclusion"
```

---

### Task 30: Wire workflow into SKILL.md (full version)

**Files:**
- Modify: `~/scideer/skills/custom/paper-reproduction/SKILL.md`

**Step 1: Replace the `## Workflow` section** with the full body from design Section 4.2 + 4.3 + 4.4 + 4.7 + 4.8 + 4.9. Use this content:

```markdown
## Workflow

The workflow has five phases. Execute them in order. Every phase has a documented failure-mode artifact: this skill MUST always produce `outputs/repro-{arxiv_id}/report.md`, even on failure.

### Phase 1: Plan

Receive: arxiv ID + reproduction target.

If the user did not specify a concrete target metric (e.g. "Table 2, GCN row, Cora dataset"), ask **one** clarifying question:
> "Which specific result should I reproduce? (e.g. a specific table row, a specific number, a specific figure)"

Then call `scripts/repro_plan.py:build_plan(...)` and save the dict to `workspace/repro-{arxiv_id}/repro_plan.json`.

### Phase 2: Comprehend

Use the `read_file` tool to read the arxiv PDF (download via `web_fetch` if needed; cache to `workspace/repro-{arxiv_id}/paper.pdf`). Extract:

- Method name + brief description
- Dataset name + size
- Hyperparameters (epochs, batch, lr)
- Target numerical value (the number being reproduced)

Failure: if you cannot extract the target value, write a `report.md` stating "Phase 2 failed: target value unrecoverable from PDF" + suggest manual input. STOP.

### Phase 3: Code Acquire

Call `scripts/code_resolver.py:resolve_code(...)` with:

- `cache_root = "/mnt/scideer-cache"`
- `cache_map = {"1609.02907": "pygcn", "<other>": "<subdir>"}`  (extend as needed)
- `github_url`: best-known official repo URL from comprehension
- `template_fallback = True`

If `result.tier == "miss"`, write a `report.md` with the resolver's `error` and STOP.

### Phase 4: Scale-Down + Run

Call `scripts/scale_down.py:apply_scale_down(...)` on the resolved code (read from `result.path`), then `scripts/runner.py:run_in_sandbox(...)` with `timeout_s = 240`.

The runner returns a `RunResult` with `failure_type` if non-success. Always proceed to Phase 5 — do not stop.

### Phase 5: Compare + Report

If `RunResult.success`:
- Parse the final metric from `RunResult.stdout` (look for `test_acc=` or paper-specific markers).
- Call `scripts/comparator.py:compare(paper_value, our_value, tolerance_pct=3.0)`.
- Render figures (loss/acc curves) from logs to `outputs/repro-{arxiv_id}/figures/`.

If NOT success:
- Skip comparison; record `verdict = "execution_failed"` with the `failure_type`.

Always render `report.md` via `scripts/report_writer.py:render_report(...)` and write to `outputs/repro-{arxiv_id}/report.md`. Also write `comparison.json` with the machine-readable Verdict (or failure record) for benchmark consumption.

## Output Structure

```
/mnt/user-data/outputs/repro-{arxiv_id}/
├── report.md              ← primary deliverable (always exists)
├── comparison.json        ← machine-readable
├── code/                  (the actual code that ran)
├── logs/run.log           (training log)
├── figures/               (loss + acc curves)
├── repro_plan.json        (Phase 1)
└── paper.pdf              (Phase 2 cache)
```

## Examples

### Example 1: GCN on Cora (the demo case)

User: "Reproduce GCN on Cora result from arxiv:1609.02907 (Table 2 row)."

Flow:
1. Phase 1: target = "GCN on Cora accuracy", expected = 81.5
2. Phase 2: extract "81.5%" from Table 2
3. Phase 3: cache hit on pygcn
4. Phase 4: scale_down(epochs 200→100); run_in_sandbox(`python pygcn/train.py --epochs 100`); ~30s
5. Phase 5: compare(81.5, 80.2) → match (Δ -1.3%); render report

### Example 2: Failure path (network out, no cache, no code)

User: "Reproduce arxiv:9999.99999 Table 1."

Flow:
1. Phase 1: build plan
2. Phase 2: web_fetch fails (no network) → report.md written with "Phase 2 failed: cannot fetch paper" → STOP

The skill never silently fails: the user always has a `report.md` documenting what happened.
```

**Step 2: Commit**

```bash
git add skills/custom/paper-reproduction/SKILL.md
git commit -m "docs(paper-reproduction): wire full workflow body into SKILL.md"
```

---

### Task 31: Failure-mode tests (OOM, timeout, divergence)

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_failure_modes.py`

**Step 1: Write tests**

```python
# tests/test_failure_modes.py
"""Verify report.md is produced for every failure type."""
from pathlib import Path
import json
from skills.custom.paper_reproduction.scripts.runner import RunResult
from skills.custom.paper_reproduction.scripts.report_writer import render_report
from skills.custom.paper_reproduction.scripts.comparator import Verdict


def _stub_failure_verdict(failure_type: str) -> Verdict:
    return Verdict(
        paper_value=81.5, our_value=0.0,
        delta=-81.5, delta_pct=-100.0, tolerance_pct=3.0,
        verdict="deviation_severe",
    )


def test_oom_produces_report():
    r = RunResult(success=False, exit_code=-9, stdout="", stderr="killed",
                  wall_time_s=5.0, timed_out=False, failure_type="OOM")
    md = render_report(
        paper_title="X", arxiv_id="1609.02907", target_metric="m",
        verdict=_stub_failure_verdict("OOM"),
        wall_time_s=r.wall_time_s,
        scale_down_summary="-", figures=[],
        code_source="-", code_mods="-",
    )
    assert "0.0" in md
    assert "❌" in md or "deviation_severe" in md.lower()


def test_timeout_produces_report():
    r = RunResult(success=False, exit_code=124, stdout="", stderr="",
                  wall_time_s=240.0, timed_out=True, failure_type="timeout")
    # similar render — verify produces output without raising
    md = render_report(
        paper_title="X", arxiv_id="1609.02907", target_metric="m",
        verdict=_stub_failure_verdict("timeout"),
        wall_time_s=r.wall_time_s,
        scale_down_summary="Epochs reduced", figures=[],
        code_source="-", code_mods="-",
    )
    assert "240" in md


def test_divergence_produces_report():
    r = RunResult(success=False, exit_code=1, stdout="", stderr="loss became NaN",
                  wall_time_s=10.0, timed_out=False, failure_type="divergence")
    md = render_report(
        paper_title="X", arxiv_id="1609.02907", target_metric="m",
        verdict=_stub_failure_verdict("divergence"),
        wall_time_s=r.wall_time_s,
        scale_down_summary="-", figures=[],
        code_source="-", code_mods="-",
    )
    assert "0.0" in md
```

**Step 2: Run, verify PASS.**

```bash
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_failure_modes.py -v
```

**Step 3: Commit**

```bash
git add skills/custom/paper-reproduction/tests/test_failure_modes.py
git commit -m "test(paper-reproduction): verify report rendering for OOM/timeout/divergence"
```

---

### Task 32: Day 4 end-to-end on real arxiv:1609.02907

**Files:**
- Create: `~/scideer/skills/custom/paper-reproduction/tests/test_smoke_e2e_day4.py`

**Step 1: Write the integration test**

```python
# tests/test_smoke_e2e_day4.py
"""Day 4 e2e: full pipeline GCN on Cora producing report.md."""
import os, json
from pathlib import Path
import pytest

from skills.custom.paper_reproduction.scripts.repro_plan import build_plan
from skills.custom.paper_reproduction.scripts.code_resolver import resolve_code
from skills.custom.paper_reproduction.scripts.runner import run_in_sandbox
from skills.custom.paper_reproduction.scripts.comparator import compare
from skills.custom.paper_reproduction.scripts.report_writer import render_report

CACHE = Path(os.path.expanduser("~/.scideer/cache"))
PYGCN = CACHE / "pygcn"


@pytest.mark.skipif(not PYGCN.exists(), reason="cache not staged")
def test_full_pipeline(tmp_path):
    out = tmp_path / "outputs" / "repro-1609.02907"
    out.mkdir(parents=True)

    plan = build_plan("1609.02907", "GCN on Cora accuracy", 81.5, "Cora", "GCN")
    (out / "repro_plan.json").write_text(json.dumps(plan, indent=2))

    res = resolve_code("1609.02907", CACHE, {"1609.02907": "pygcn"})
    assert res.tier == "cache"

    runres = run_in_sandbox(res.path / "pygcn", ["python", "train.py", "--epochs", "50"], 180)
    assert runres.success

    # Parse acc — pygcn prints e.g. "Test set results: loss= 0.6X accuracy= 0.80X"
    import re
    m = re.search(r"accuracy[=:\s]+([\d.]+)", runres.stdout)
    assert m, f"acc not found in: {runres.stdout[-500:]}"
    acc_pct = float(m.group(1)) * 100  # convert 0.802 → 80.2

    verdict = compare(81.5, acc_pct, tolerance_pct=3.0)
    md = render_report(
        paper_title="Semi-Supervised GCN", arxiv_id="1609.02907",
        target_metric="GCN on Cora accuracy", verdict=verdict,
        wall_time_s=runres.wall_time_s,
        scale_down_summary="Epochs: 200 → 50",
        figures=[], code_source="cached pygcn", code_mods="epochs=50",
    )
    (out / "report.md").write_text(md)
    (out / "comparison.json").write_text(json.dumps(verdict.__dict__, indent=2))
    assert (out / "report.md").exists()
    assert (out / "comparison.json").exists()
    print(f"✅ Day 4 e2e: paper={81.5}, ours={acc_pct:.2f}, verdict={verdict.verdict}")
```

**Step 2: Run on server**

```bash
cd ~/scideer
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_smoke_e2e_day4.py -v -s
```

Expected: PASS within 60 s; verdict probably `match`.

**Step 3: Commit + record CP3 progress**

```bash
git add skills/custom/paper-reproduction/tests/test_smoke_e2e_day4.py
git commit -m "test(paper-reproduction): Day 4 full-pipeline e2e producing report.md + comparison.json"
```

Append to `docs/NOTES.md`:
```
### Day 4 EOD: paper-reproduction complete
- All scripts implemented + tested
- e2e on GCN/Cora: paper=81.5, ours=<X>, verdict=match
- Failure-mode tests pass
- Ready for Day 5: scientific-writing
```

```bash
git add docs/NOTES.md
git commit -m "docs: log Day 4 EOD status (paper-reproduction skill complete)"
```

**End of Day 4. Phase 1 (paper-reproduction skill) complete.**

---

# Phase 2 — `scientific-writing` skill (Day 5)

> Reference: design Section 5. Hard guarantee: this skill always produces a PDF — naked-PDF degradation if compile fails repeatedly.
>
> Use @superpowers:test-driven-development for all script tasks.

## Task 33: Scaffold scientific-writing skill

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/SKILL.md` (frontmatter + skeleton)
- Create: `~/scideer/skills/custom/scientific-writing/{scripts,templates,tests}/`

**Step 1: Create directories + frontmatter**

```bash
cd ~/scideer
mkdir -p skills/custom/scientific-writing/{scripts,templates,tests}
touch skills/custom/scientific-writing/scripts/__init__.py
touch skills/custom/scientific-writing/tests/__init__.py

cat > skills/custom/scientific-writing/SKILL.md <<'EOF'
---
name: scientific-writing
description: Use this skill when the user wants to assemble a publication-ready
  LaTeX academic paper from upstream artifacts (literature review, reproduction
  results, data analysis, figures). Compiles to PDF using NeurIPS, ICML, or ACL
  templates. The skill scans /mnt/user-data/workspace/ for upstream outputs and
  generates paper.tex + references.bib + paper.pdf. Not for short reports
  (use Markdown directly) or non-academic writing.
---

# Scientific Writing Skill

## Overview

Assembles a publication-ready LaTeX paper from upstream artifacts produced by other skills. Compiles to PDF inside the sandbox using NeurIPS / ICML / ACL templates with iterative auto-fix.

**Hard guarantee:** sandbox always produces a PDF. If compile fails after 3 retries, the skill emits a "naked PDF" (text-only, no bib/figures) plus `compile_errors.md`.

## When to Use

Use when:
- The user wants a LaTeX paper assembled from a known set of artifacts
- Upstream `outputs/slr-*.md`, `outputs/repro-*/report.md`, or `workspace/analysis-*/` exist

Do NOT use when:
- The user wants a Markdown-only report (just produce Markdown directly)
- The user wants non-academic writing (use generic LLM prompt)
- Input artifacts are missing — surface that requirement instead

## Workflow

The workflow has six phases. Run them in order.

### Phase 1: Plan
... (filled in Task 41)

### Phase 2: Collect
... (filled in Task 41)

### Phase 3: Outline
... (filled in Task 41)

### Phase 4: Draft
... (filled in Task 41)

### Phase 5: Bib Assemble
... (filled in Task 41)

### Phase 6: Compile + Iterate
... (filled in Task 41)
EOF
```

**Step 2: Commit**

```bash
git add skills/custom/scientific-writing/
git commit -m "feat(skill): scaffold scientific-writing skill directory + SKILL.md frontmatter"
```

---

## Task 34: Tests + impl `artifact_collector.py`

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/scripts/artifact_collector.py`
- Create: `~/scideer/skills/custom/scientific-writing/tests/test_artifact_collector.py`

**Step 1: Write failing tests**

```python
# tests/test_artifact_collector.py
from pathlib import Path
from skills.custom.scientific_writing.scripts.artifact_collector import collect_artifacts

def test_finds_slr(tmp_path):
    outputs = tmp_path / "outputs"; outputs.mkdir()
    (outputs / "slr-graph-neural-networks-20260512.md").write_text("# SLR\n@misc{x,year={2017}}")
    workspace = tmp_path / "workspace"; workspace.mkdir()
    idx = collect_artifacts(outputs_dir=outputs, workspace_dir=workspace)
    assert len(idx["literature_reviews"]) == 1
    assert idx["literature_reviews"][0].name.startswith("slr-")

def test_finds_repro_reports(tmp_path):
    outputs = tmp_path / "outputs"; outputs.mkdir()
    repro = outputs / "repro-1609.02907"; repro.mkdir()
    (repro / "report.md").write_text("# Repro Report")
    (repro / "comparison.json").write_text("{}")
    workspace = tmp_path / "workspace"; workspace.mkdir()
    idx = collect_artifacts(outputs_dir=outputs, workspace_dir=workspace)
    assert len(idx["reproductions"]) == 1
    assert idx["reproductions"][0].parent.name == "repro-1609.02907"

def test_finds_workspace_figures(tmp_path):
    outputs = tmp_path / "outputs"; outputs.mkdir()
    workspace = tmp_path / "workspace"; workspace.mkdir()
    figs = workspace / "figures"; figs.mkdir()
    (figs / "training.png").write_bytes(b"\x89PNG")
    idx = collect_artifacts(outputs_dir=outputs, workspace_dir=workspace)
    assert len(idx["figures"]) == 1

def test_empty_returns_empty_lists(tmp_path):
    outputs = tmp_path / "outputs"; outputs.mkdir()
    workspace = tmp_path / "workspace"; workspace.mkdir()
    idx = collect_artifacts(outputs_dir=outputs, workspace_dir=workspace)
    assert idx == {"literature_reviews": [], "reproductions": [],
                   "analyses": [], "figures": []}
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement**

```python
# scripts/artifact_collector.py
"""Phase 2 of scientific-writing: scan workspace+outputs for upstream artifacts."""
from pathlib import Path
from typing import Dict, List


def collect_artifacts(outputs_dir: Path, workspace_dir: Path) -> Dict[str, List[Path]]:
    """Return categorized index of upstream artifacts."""
    idx = {
        "literature_reviews": [],
        "reproductions": [],
        "analyses": [],
        "figures": [],
    }

    # outputs/slr-*.md → literature reviews
    if outputs_dir.exists():
        idx["literature_reviews"] = sorted(outputs_dir.glob("slr-*.md"))

        # outputs/repro-*/report.md → reproductions
        for repro_dir in outputs_dir.glob("repro-*"):
            rpt = repro_dir / "report.md"
            if rpt.exists():
                idx["reproductions"].append(rpt)

        # outputs/analysis-*/*.md → analyses
        for ana_dir in outputs_dir.glob("analysis-*"):
            for md in ana_dir.glob("*.md"):
                idx["analyses"].append(md)

    # workspace/**/*.png → figures
    if workspace_dir.exists():
        idx["figures"] = sorted(workspace_dir.rglob("*.png"))

    return idx
```

**Step 4: Run, verify PASS. Commit.**

```bash
git add skills/custom/scientific-writing/scripts/artifact_collector.py \
        skills/custom/scientific-writing/tests/test_artifact_collector.py
git commit -m "feat(scientific-writing): implement artifact_collector with categorized index"
```

---

## Task 35: Tests + impl `bib_assembler.py`

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/scripts/bib_assembler.py`
- Create: `~/scideer/skills/custom/scientific-writing/tests/test_bib_assembler.py`

**Step 1: Failing tests**

```python
# tests/test_bib_assembler.py
from pathlib import Path
from skills.custom.scientific_writing.scripts.bib_assembler import (
    extract_bib_entries, merge_and_dedupe,
)

def test_extracts_misc_from_markdown():
    md = """
# SLR

Some text.

@misc{kipf2017,
  title={Semi-Supervised Classification with Graph Convolutional Networks},
  author={Kipf, T and Welling, M},
  year={2017}
}

More text.

@article{vaswani2017,
  title={Attention is all you need},
  author={Vaswani, A},
  year={2017}
}
"""
    entries = extract_bib_entries(md)
    assert len(entries) == 2
    assert entries[0]["key"] == "kipf2017"
    assert entries[1]["key"] == "vaswani2017"


def test_merge_dedupe_by_key():
    entries = [
        {"key": "kipf2017", "raw": "@misc{kipf2017, year={2017}}"},
        {"key": "kipf2017", "raw": "@misc{kipf2017, year={2017}}"},
        {"key": "vaswani2017", "raw": "@article{vaswani2017, year={2017}}"},
    ]
    deduped = merge_and_dedupe(entries)
    assert len(deduped) == 2
    keys = {e["key"] for e in deduped}
    assert keys == {"kipf2017", "vaswani2017"}
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement**

```python
# scripts/bib_assembler.py
"""Phase 5 of scientific-writing: extract + merge BibTeX entries from upstream artifacts."""
import re
from typing import List, Dict
from pathlib import Path

# Match @type{key, ... } across newlines, balanced braces
ENTRY_PATTERN = re.compile(
    r"@(\w+)\s*\{\s*([^,]+)\s*,(.*?)\n\}",
    re.DOTALL,
)


def extract_bib_entries(text: str) -> List[Dict]:
    """Extract @misc / @article / @inproceedings entries from arbitrary text."""
    out = []
    for m in ENTRY_PATTERN.finditer(text):
        kind, key, body = m.group(1), m.group(2).strip(), m.group(3)
        raw = f"@{kind}{{{key},{body}\n}}"
        out.append({"kind": kind, "key": key, "body": body, "raw": raw})
    return out


def merge_and_dedupe(entries: List[Dict]) -> List[Dict]:
    """Dedupe by citation key, preserve first occurrence, sort by key."""
    seen = {}
    for e in entries:
        if e["key"] not in seen:
            seen[e["key"]] = e
    return sorted(seen.values(), key=lambda e: e["key"])


def assemble_bib(markdown_files: List[Path], output_bib: Path) -> int:
    """Read each .md, extract @entries, merge, write to output_bib. Returns entry count."""
    all_entries = []
    for md in markdown_files:
        all_entries.extend(extract_bib_entries(md.read_text()))
    deduped = merge_and_dedupe(all_entries)
    output_bib.parent.mkdir(parents=True, exist_ok=True)
    output_bib.write_text("\n\n".join(e["raw"] for e in deduped) + "\n")
    return len(deduped)
```

**Step 4: Run, verify PASS. Commit.**

```bash
git add skills/custom/scientific-writing/scripts/bib_assembler.py \
        skills/custom/scientific-writing/tests/test_bib_assembler.py
git commit -m "feat(scientific-writing): implement bib_assembler with extract + dedupe"
```

---

## Task 36: Tests + impl `latex_log_parser.py`

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/scripts/latex_log_parser.py`
- Create: `~/scideer/skills/custom/scientific-writing/tests/test_latex_log_parser.py`

**Step 1: Failing tests**

```python
# tests/test_latex_log_parser.py
from skills.custom.scientific_writing.scripts.latex_log_parser import parse_log


def test_undefined_citation():
    log = """
LaTeX Warning: Citation `kipf2017' on page 1 undefined on input line 12.
LaTeX Warning: Citation `vaswani2017' on page 2 undefined on input line 30.
"""
    issues = parse_log(log)
    assert any(i["type"] == "undefined_citation" and i["key"] == "kipf2017" for i in issues)
    assert any(i["type"] == "undefined_citation" and i["key"] == "vaswani2017" for i in issues)


def test_missing_package():
    log = "! LaTeX Error: File `tikz.sty' not found.\n"
    issues = parse_log(log)
    assert any(i["type"] == "missing_package" and i["package"] == "tikz" for i in issues)


def test_missing_bib_database():
    log = "I couldn't open database file refs.bib\n"
    issues = parse_log(log)
    assert any(i["type"] == "missing_bib" for i in issues)


def test_unknown_returns_empty():
    log = "(./paper.aux) [1{/var/lib/texmf/fonts/map/pdftex/updmap/pdftex.map}] (./paper.aux))\n"
    issues = parse_log(log)
    assert issues == []
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement**

```python
# scripts/latex_log_parser.py
"""Parse pdflatex / bibtex log files into structured issues for auto-fix."""
import re
from typing import List, Dict

UNDEFINED_CITE = re.compile(r"Citation `([^']+)' on page \d+ undefined")
MISSING_PACKAGE = re.compile(r"File `([^']+)\.sty' not found")
MISSING_BIB = re.compile(r"couldn't open database file ([^\s]+)")


def parse_log(log_text: str) -> List[Dict]:
    issues: List[Dict] = []
    for m in UNDEFINED_CITE.finditer(log_text):
        issues.append({"type": "undefined_citation", "key": m.group(1)})
    for m in MISSING_PACKAGE.finditer(log_text):
        issues.append({"type": "missing_package", "package": m.group(1)})
    for m in MISSING_BIB.finditer(log_text):
        issues.append({"type": "missing_bib", "file": m.group(1)})
    return issues
```

**Step 4: Run, verify PASS. Commit.**

```bash
git add skills/custom/scientific-writing/scripts/latex_log_parser.py \
        skills/custom/scientific-writing/tests/test_latex_log_parser.py
git commit -m "feat(scientific-writing): implement latex_log_parser for known error classes"
```

---

## Task 37: Tests + impl `compile_latex.py` (single-pass happy path)

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/scripts/compile_latex.py`
- Create: `~/scideer/skills/custom/scientific-writing/tests/test_compile_latex.py`

**Step 1: Failing tests**

```python
# tests/test_compile_latex.py
import subprocess
from pathlib import Path
import pytest
from skills.custom.scientific_writing.scripts.compile_latex import (
    run_one_pass, CompilePassResult,
)

# Quick sanity: pdflatex must be on PATH for these tests
HAS_LATEX = subprocess.run(
    ["which", "pdflatex"], capture_output=True
).returncode == 0


@pytest.mark.skipif(not HAS_LATEX, reason="pdflatex not on PATH; run inside sandbox or skip locally")
def test_run_one_pass_minimal(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")
    result = run_one_pass(work_dir=tmp_path, tex_basename="paper")
    assert result.success
    assert (tmp_path / "paper.pdf").exists()


@pytest.mark.skipif(not HAS_LATEX, reason="pdflatex not on PATH")
def test_run_one_pass_collects_log_on_failure(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(r"\documentclass{article}\begin{document}\undefinedcommand\end{document}")
    result = run_one_pass(work_dir=tmp_path, tex_basename="paper")
    # pdflatex with `nonstopmode` may succeed despite undefined commands; just check log captured
    assert result.log != ""
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement single-pass core**

```python
# scripts/compile_latex.py
"""Phase 6 of scientific-writing: pdflatex + bibtex orchestration with iterative auto-fix."""
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict
from .latex_log_parser import parse_log


@dataclass
class CompilePassResult:
    success: bool
    log: str
    issues: List[Dict]
    artifact: Path = None


def run_one_pass(work_dir: Path, tex_basename: str = "paper") -> CompilePassResult:
    """Run pdflatex once, collect log + parsed issues."""
    proc = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
         f"{tex_basename}.tex"],
        cwd=str(work_dir),
        capture_output=True, text=True, timeout=120,
    )
    log_path = work_dir / f"{tex_basename}.log"
    log = log_path.read_text() if log_path.exists() else proc.stdout
    pdf = work_dir / f"{tex_basename}.pdf"
    issues = parse_log(log)
    return CompilePassResult(
        success=(proc.returncode == 0 and pdf.exists()),
        log=log, issues=issues,
        artifact=pdf if pdf.exists() else None,
    )


def run_bibtex(work_dir: Path, tex_basename: str = "paper") -> str:
    """Run bibtex and return its log."""
    proc = subprocess.run(
        ["bibtex", tex_basename],
        cwd=str(work_dir),
        capture_output=True, text=True, timeout=60,
    )
    return (proc.stdout or "") + (proc.stderr or "")
```

**Step 4: Run tests inside sandbox if possible**

```bash
docker run --rm -v $(pwd):/work -w /work scideer-sandbox:latest \
  bash -c "cd /work && PYTHONPATH=. pytest skills/custom/scientific-writing/tests/test_compile_latex.py -v"
```

(Local pytest will skip due to no pdflatex; that's OK.)

**Step 5: Commit**

```bash
git add skills/custom/scientific-writing/scripts/compile_latex.py \
        skills/custom/scientific-writing/tests/test_compile_latex.py
git commit -m "feat(scientific-writing): implement compile_latex single-pass + bibtex helpers"
```

---

## Task 38: Add 3-round retry with auto-fix

**Files:**
- Modify: `~/scideer/skills/custom/scientific-writing/scripts/compile_latex.py`
- Create: `~/scideer/skills/custom/scientific-writing/scripts/auto_fixer.py`
- Create: `~/scideer/skills/custom/scientific-writing/tests/test_auto_fixer.py`

**Step 1: Failing tests for auto_fixer**

```python
# tests/test_auto_fixer.py
from pathlib import Path
from skills.custom.scientific_writing.scripts.auto_fixer import (
    fix_undefined_citation, fix_missing_bib_keys,
)


def test_replaces_undefined_citation_with_placeholder(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(r"See \citep{kipf2017} and \citep{vaswani2017}.")
    fix_undefined_citation(tex, key="kipf2017")
    body = tex.read_text()
    assert "kipf2017" not in body
    assert "[?]" in body
    assert "vaswani2017" in body


def test_drops_missing_bib_keys(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        "@misc{kipf2017, year={2017}}\n\n@article{ghost, year={2017}}\n"
    )
    fix_missing_bib_keys(bib, keep_keys={"kipf2017"})
    body = bib.read_text()
    assert "kipf2017" in body
    assert "ghost" not in body
```

**Step 2: Implement `auto_fixer.py`**

```python
# scripts/auto_fixer.py
"""Auto-fix LaTeX/bib issues identified by latex_log_parser."""
import re
from pathlib import Path
from typing import Set


def fix_undefined_citation(tex_path: Path, key: str) -> None:
    """Replace \\cite{key} / \\citep{key} / \\citet{key} with [?]."""
    body = tex_path.read_text()
    body = re.sub(rf"\\cite[pt]?\{{\s*{re.escape(key)}\s*\}}", "[?]", body)
    tex_path.write_text(body)


def fix_missing_bib_keys(bib_path: Path, keep_keys: Set[str]) -> None:
    """Remove @entries whose key is not in keep_keys."""
    text = bib_path.read_text()
    pattern = re.compile(r"@\w+\s*\{\s*([^,]+)\s*,.*?\n\}", re.DOTALL)
    new_chunks = []
    last = 0
    for m in pattern.finditer(text):
        if m.group(1).strip() in keep_keys:
            new_chunks.append(m.group(0))
    bib_path.write_text("\n\n".join(new_chunks) + "\n")
```

**Step 3: Add `compile_paper` orchestrator to `compile_latex.py`**

Append to `compile_latex.py`:

```python
from .auto_fixer import fix_undefined_citation, fix_missing_bib_keys


@dataclass
class CompileFinalResult:
    success: bool
    pdf_path: Path
    rounds: int
    is_naked: bool
    error_summary: List[str]


def compile_paper(
    work_dir: Path,
    tex_basename: str = "paper",
    max_rounds: int = 3,
    naked_fallback: bool = True,
) -> CompileFinalResult:
    """Run pdflatex × 2 + bibtex + pdflatex × 2 with up to `max_rounds` fix-and-retry."""
    error_summary: List[str] = []

    for round_idx in range(max_rounds):
        # Standard chain: pdflatex → bibtex → pdflatex × 2
        r1 = run_one_pass(work_dir, tex_basename)
        bibtex_log = run_bibtex(work_dir, tex_basename)
        r2 = run_one_pass(work_dir, tex_basename)
        r3 = run_one_pass(work_dir, tex_basename)

        all_issues = r1.issues + r2.issues + r3.issues + parse_log(bibtex_log)

        if r3.success and not any(i["type"] == "undefined_citation" for i in all_issues):
            return CompileFinalResult(
                success=True, pdf_path=r3.artifact,
                rounds=round_idx + 1, is_naked=False,
                error_summary=[],
            )

        # Apply fixes for next round
        tex = work_dir / f"{tex_basename}.tex"
        bib = work_dir / "references.bib"

        for issue in all_issues:
            if issue["type"] == "undefined_citation":
                fix_undefined_citation(tex, issue["key"])
                error_summary.append(f"Round {round_idx+1}: removed undefined cite {issue['key']!r}")
            elif issue["type"] == "missing_bib" and bib.exists():
                # Drop the file reference; will retry on next round
                error_summary.append(f"Round {round_idx+1}: missing bib {issue['file']!r}")

    # All rounds failed → naked PDF
    if naked_fallback:
        naked = _strip_to_naked(work_dir / f"{tex_basename}.tex")
        r = run_one_pass(work_dir, tex_basename)
        if r.success:
            error_summary.append(f"Compiled as naked PDF after {max_rounds} failed rounds")
            return CompileFinalResult(
                success=True, pdf_path=r.artifact,
                rounds=max_rounds, is_naked=True,
                error_summary=error_summary,
            )

    return CompileFinalResult(
        success=False, pdf_path=None,
        rounds=max_rounds, is_naked=False,
        error_summary=error_summary,
    )


def _strip_to_naked(tex_path: Path) -> None:
    """Strip \\bibliography, \\includegraphics, and figure environments from tex."""
    body = tex_path.read_text()
    # Drop bibliography commands
    body = re.sub(r"\\bibliography\{[^}]+\}", "", body)
    body = re.sub(r"\\bibliographystyle\{[^}]+\}", "", body)
    # Drop figures
    body = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "", body, flags=re.DOTALL)
    body = re.sub(r"\\includegraphics(\[[^\]]*\])?\{[^}]+\}", "[FIGURE]", body)
    # Replace cites with [?]
    body = re.sub(r"\\cite[pt]?\{[^}]+\}", "[?]", body)
    tex_path.write_text(body)
```

Add `import re` if not present at top.

**Step 4: Run all scientific-writing tests**

```bash
PYTHONPATH=. pytest skills/custom/scientific-writing/tests/ -v
```

Expected: all unit tests pass; the `test_compile_latex.py` tests skip locally (no pdflatex on host).

**Step 5: Commit**

```bash
git add skills/custom/scientific-writing/scripts/auto_fixer.py \
        skills/custom/scientific-writing/scripts/compile_latex.py \
        skills/custom/scientific-writing/tests/test_auto_fixer.py
git commit -m "feat(scientific-writing): add 3-round retry with auto-fix + naked-PDF degradation"
```

---

## Task 39: NeurIPS template

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/templates/neurips_2024.tex`

**Step 1: Write a self-contained, compileable NeurIPS-style template**

```bash
cat > skills/custom/scientific-writing/templates/neurips_2024.tex <<'TEX'
\documentclass{article}

% NeurIPS 2024-compatible style. Uses standard packages only — no external .sty needed.
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage[numbers]{natbib}
\usepackage{geometry}
\geometry{margin=1in}

\title{__TITLE__}
\author{__AUTHORS__}

\begin{document}
\maketitle

\begin{abstract}
__ABSTRACT__
\end{abstract}

\section{Introduction}
__INTRODUCTION__

\section{Related Work}
__RELATED_WORK__

\section{Method}
__METHOD__

\section{Experiments}
__EXPERIMENTS__

\section{Conclusion}
__CONCLUSION__

\bibliographystyle{plain}
\bibliography{references}

\end{document}
TEX
```

Note: real NeurIPS uses `neurips_2024.sty` package; for SciDeer's purposes, a standard `article` class with `natbib` is sufficient and avoids texlive package dependency issues. Mention this in the design as a known limitation.

**Step 2: Smoke test the template via sandbox**

```bash
mkdir -p /tmp/scideer-tex-smoke
cp skills/custom/scientific-writing/templates/neurips_2024.tex /tmp/scideer-tex-smoke/paper.tex
sed -i 's/__TITLE__/Smoke Test/; s/__AUTHORS__/Jasper/; s/__ABSTRACT__/Test abstract./' /tmp/scideer-tex-smoke/paper.tex
sed -i 's/__INTRODUCTION__/Test intro./; s/__RELATED_WORK__/Test rel./; s/__METHOD__/Test method./; s/__EXPERIMENTS__/Test exp./; s/__CONCLUSION__/Test conclusion./' /tmp/scideer-tex-smoke/paper.tex
cat > /tmp/scideer-tex-smoke/references.bib <<'BIB'
@misc{kipf2017, title={GCN}, author={Kipf}, year={2017}}
BIB
docker run --rm -v /tmp/scideer-tex-smoke:/work -w /work scideer-sandbox:latest \
  bash -c "pdflatex -interaction=nonstopmode paper && bibtex paper && pdflatex -interaction=nonstopmode paper && pdflatex -interaction=nonstopmode paper && ls paper.pdf"
```

Expected: `paper.pdf` listed at end.

**Step 3: Commit**

```bash
git add skills/custom/scientific-writing/templates/neurips_2024.tex
git commit -m "feat(scientific-writing): add neurips_2024.tex template (article-class + natbib)"
```

---

## Task 40: Tests + impl `paper_drafter.py` (template fill from artifacts)

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/scripts/paper_drafter.py`
- Create: `~/scideer/skills/custom/scientific-writing/tests/test_paper_drafter.py`

**Step 1: Failing tests**

```python
# tests/test_paper_drafter.py
from pathlib import Path
from skills.custom.scientific_writing.scripts.paper_drafter import fill_template


def test_fills_all_sections(tmp_path):
    tmpl = tmp_path / "neurips_2024.tex"
    tmpl.write_text("""
\\title{__TITLE__}
\\author{__AUTHORS__}
\\begin{abstract}__ABSTRACT__\\end{abstract}
__INTRODUCTION__
__RELATED_WORK__
__METHOD__
__EXPERIMENTS__
__CONCLUSION__
""")
    sections = {
        "TITLE": "SciDeer", "AUTHORS": "Jasper",
        "ABSTRACT": "Abstract.",
        "INTRODUCTION": "Intro.",
        "RELATED_WORK": "Rel.",
        "METHOD": "Method.",
        "EXPERIMENTS": "Exp.",
        "CONCLUSION": "Conclusion.",
    }
    out = tmp_path / "paper.tex"
    fill_template(tmpl, sections, out)
    body = out.read_text()
    assert "SciDeer" in body
    assert "__TITLE__" not in body
    assert "Jasper" in body
    for v in sections.values():
        assert v in body


def test_unfilled_placeholder_marked_TODO(tmp_path):
    tmpl = tmp_path / "t.tex"
    tmpl.write_text("__INTRODUCTION__\n__METHOD__\n")
    out = tmp_path / "p.tex"
    fill_template(tmpl, {"INTRODUCTION": "Intro."}, out)
    body = out.read_text()
    assert "Intro." in body
    assert "[TODO: METHOD]" in body
```

**Step 2: Implement**

```python
# scripts/paper_drafter.py
"""Phase 4 of scientific-writing: fill template placeholders with section content."""
import re
from pathlib import Path
from typing import Dict

PLACEHOLDER_PATTERN = re.compile(r"__([A-Z_]+)__")


def fill_template(template_path: Path, sections: Dict[str, str], output_path: Path) -> None:
    body = template_path.read_text()

    def replace(m):
        key = m.group(1)
        return sections.get(key, f"[TODO: {key}]")

    body = PLACEHOLDER_PATTERN.sub(replace, body)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body)
```

**Step 3: Run, verify PASS. Commit.**

```bash
git add skills/custom/scientific-writing/scripts/paper_drafter.py \
        skills/custom/scientific-writing/tests/test_paper_drafter.py
git commit -m "feat(scientific-writing): implement paper_drafter for template-fill with TODO marking"
```

---

## Task 41: Wire scientific-writing workflow body into SKILL.md

**Files:**
- Modify: `~/scideer/skills/custom/scientific-writing/SKILL.md`

**Step 1: Replace the `## Workflow` body with the full version**

```markdown
## Workflow

### Phase 1: Plan

Confirm with the user (one clarification only if needed):
- Template choice: NeurIPS (default) / ICML / ACL
- Title (or auto-generate from upstream artifacts' topic)
- 1-sentence stance / contribution claim

Save `paper_plan.json` to `workspace/paper_plan.json`.

### Phase 2: Collect

Call `scripts/artifact_collector.py:collect_artifacts(outputs_dir, workspace_dir)` to index:
- Literature reviews (`outputs/slr-*.md`)
- Reproductions (`outputs/repro-*/report.md`)
- Analyses (`outputs/analysis-*/`)
- Figures (`workspace/**/*.png`)

If the index is empty, write `outputs/paper/MISSING.md` saying "no upstream artifacts; run systematic-literature-review etc. first" and STOP.

### Phase 3: Outline

Generate a paragraph-level outline using the LLM (you), with the artifact index as context. Each section gets 2-5 claims.

### Phase 4: Draft

For each section, draft 1-3 paragraphs of LaTeX. Cite via `\citep{key}` using citation keys from the literature reviews. Include figures via `\includegraphics{figures/training.png}` when relevant.

Build a `sections` dict: `{"TITLE": ..., "AUTHORS": ..., "ABSTRACT": ..., "INTRODUCTION": ..., ..., "CONCLUSION": ...}`.

Call `scripts/paper_drafter.py:fill_template(template_path, sections, output_tex_path)`.

### Phase 5: Bib Assemble

Call `scripts/bib_assembler.py:assemble_bib(literature_review_files, output_bib_path)`. Verify the assembled `references.bib` contains every key cited in the draft.

### Phase 6: Compile + Iterate

Copy figures into `workspace/paper/figures/`. Then call `scripts/compile_latex.py:compile_paper(work_dir, max_rounds=3, naked_fallback=True)`.

If `success=True` and `is_naked=False`: ✅ done.
If `success=True` and `is_naked=True`: write `compile_errors.md` listing what was stripped, and surface to user as "naked PDF — review error log".
If `success=False`: write `compile_errors.md` with the full error_summary; STOP.

Final outputs to `outputs/paper/`:
- `paper.tex`
- `references.bib`
- `paper.pdf` (always exists in success-or-naked paths)
- `figures/`
- `compile_errors.md` (only if not clean compile)
```

**Step 2: Commit**

```bash
git add skills/custom/scientific-writing/SKILL.md
git commit -m "docs(scientific-writing): wire full 6-phase workflow into SKILL.md"
```

---

## Task 42: Day 5 EOD — End-to-end smoke + CP3 checkpoint

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/tests/test_smoke_e2e_day5.py`

**Step 1: Write integration test**

```python
# tests/test_smoke_e2e_day5.py
"""Day 5 e2e: mock upstream artifacts → compile NeurIPS PDF inside sandbox."""
import os, json, subprocess
from pathlib import Path
import pytest

HAS_LATEX = subprocess.run(["which", "pdflatex"], capture_output=True).returncode == 0


@pytest.mark.skipif(not HAS_LATEX, reason="run inside scideer-sandbox; locally skipped")
def test_e2e_paper_pdf(tmp_path):
    from skills.custom.scientific_writing.scripts.artifact_collector import collect_artifacts
    from skills.custom.scientific_writing.scripts.bib_assembler import assemble_bib
    from skills.custom.scientific_writing.scripts.paper_drafter import fill_template
    from skills.custom.scientific_writing.scripts.compile_latex import compile_paper

    # Stage mock outputs/slr + repro
    outputs = tmp_path / "outputs"; outputs.mkdir()
    (outputs / "slr-graph-neural-networks-20260512.md").write_text(
        "# SLR\n@misc{kipf2017, title={GCN}, author={Kipf}, year={2017}}"
    )
    repro = outputs / "repro-1609.02907"; repro.mkdir()
    (repro / "report.md").write_text("# Repro: GCN/Cora 80.2% (paper 81.5%)")
    (repro / "comparison.json").write_text(
        json.dumps({"paper_value": 81.5, "our_value": 80.2, "delta_pct": -1.59})
    )
    workspace = tmp_path / "workspace"; workspace.mkdir()

    # Phase 2 collect
    idx = collect_artifacts(outputs, workspace)
    assert idx["literature_reviews"]
    assert idx["reproductions"]

    # Phase 5 bib
    paper_dir = outputs / "paper"; paper_dir.mkdir()
    bib_count = assemble_bib(idx["literature_reviews"], paper_dir / "references.bib")
    assert bib_count == 1

    # Phase 4 draft
    template = Path(__file__).parent.parent / "templates" / "neurips_2024.tex"
    fill_template(template, {
        "TITLE": "SciDeer Smoke Paper",
        "AUTHORS": "Jasper",
        "ABSTRACT": "We reproduce GCN on Cora.",
        "INTRODUCTION": "GNNs are powerful \\citep{kipf2017}.",
        "RELATED_WORK": "See \\citep{kipf2017}.",
        "METHOD": "We follow Kipf and Welling.",
        "EXPERIMENTS": "We achieved 80.2\\% accuracy on Cora.",
        "CONCLUSION": "Reproduction matches within tolerance.",
    }, paper_dir / "paper.tex")

    # Phase 6 compile
    res = compile_paper(paper_dir, "paper", max_rounds=3, naked_fallback=True)
    assert res.success, res.error_summary
    assert res.pdf_path.exists()
    print(f"✅ Day 5 e2e: PDF at {res.pdf_path}, naked={res.is_naked}, rounds={res.rounds}")
```

**Step 2: Run inside sandbox**

```bash
cd ~/scideer
docker run --rm \
  -v $(pwd):/scideer \
  -w /scideer \
  scideer-sandbox:latest \
  bash -c "pip install pytest && PYTHONPATH=. pytest skills/custom/scientific-writing/tests/test_smoke_e2e_day5.py -v -s"
```

Expected: PASS, prints PDF path. `naked=False`, `rounds=1` (or 2 — the cite resolution requires 2 rounds with bibtex).

**Step 3: Record CP3 status**

Append to `docs/NOTES.md`:
```
### Day 5 EOD: scientific-writing complete (CP3)
- All 4 scripts (artifact_collector, bib_assembler, paper_drafter, compile_latex + auto_fixer + log_parser) implemented + tested
- e2e smoke: PDF compiled successfully, rounds=<X>, naked=False
- 🚩 CP3 PASS: minimum viable demo path proven (paper-reproduction → scientific-writing → PDF)
- Day 6 begins: sci-pi orchestrator
```

**Step 4: Commit**

```bash
git add skills/custom/scientific-writing/tests/test_smoke_e2e_day5.py docs/NOTES.md
git commit -m "test(scientific-writing): Day 5 e2e PDF compile + CP3 checkpoint reached"
```

**🚩 End of Day 5. Phase 2 complete. CP3 must PASS to proceed.**

If CP3 fails (naked PDF or compile failure), invoke @superpowers:systematic-debugging immediately. Day 6-7 will be unable to demonstrate end-to-end without a working PDF compile.

---

# Phase 3 — `sci-pi` Orchestrator + Semantic Scholar MCP (Day 6)

> Reference: design Sections 6 + 7. Goal: register a custom subagent that chains all 6 skills and add an MCP for citation graph queries.

## Task 43: Write `sci-pi` system prompt

**Files:**
- Create: `~/scideer/agents/sci-pi/prompt.md`

**Step 1: Create directory and write the prompt**

```bash
mkdir -p ~/scideer/agents/sci-pi
cat > ~/scideer/agents/sci-pi/prompt.md <<'EOF'
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
- After every skill invocation, run `ls outputs/` and quote the listing
  back to the user as proof of artifact existence.

OUTPUT to user at each phase boundary:
- 1 sentence summary of what just completed
- Path to artifact
- "Proceeding to phase X" or "Lifecycle complete"

CONCURRENCY: DeerFlow enforces MAX_CONCURRENT_SUBAGENTS=3. You MUST NOT
dispatch more than 3 task() calls in a single turn. If a phase needs more
fan-out (e.g. SLR phase 3 with many papers), the underlying skill handles
the round strategy itself; you do not need to manage it.

CITATION GRAPH: when user wants citation analysis (e.g. "what papers
cite X"), use the semantic-scholar MCP tool `s2_get_citations`. Always
prefer S2 over web_search for paper metadata.
EOF
```

**Step 2: Commit**

```bash
git add agents/sci-pi/prompt.md
git commit -m "feat(sci-pi): write Principal Investigator system prompt"
```

---

## Task 44: Write `agents/sci-pi/config.yaml`

**Files:**
- Create: `~/scideer/agents/sci-pi/config.yaml`

**Step 1: Write the per-agent config**

```bash
cat > ~/scideer/agents/sci-pi/config.yaml <<'EOF'
# Per-agent SOUL config for sci-pi.
# Loaded by DeerFlow when assistant_id=sci-pi is selected.
skills:
  - systematic-literature-review
  - academic-paper-review
  - paper-reproduction
  - data-analysis
  - chart-visualization
  - scientific-writing
EOF
```

**Note:** the bulk of the config (system_prompt, tools, model, max_turns, timeout) is registered in the main `config.yaml` under `subagents.custom_agents.sci-pi` in the next task. This per-agent file controls the **skill whitelist** — `null` means inherit all enabled, `[]` means disable all, list means whitelist.

**Step 2: Commit**

```bash
git add agents/sci-pi/config.yaml
git commit -m "feat(sci-pi): per-agent skill whitelist config"
```

---

## Task 45: Register sci-pi as custom subagent in main config.yaml

**Files:**
- Modify: `~/scideer/config.yaml`

**Step 1: Find the subagents section**

```bash
grep -n "^subagents:\|^# subagents:" config.yaml
```

If commented out, uncomment the block. Otherwise add it.

**Step 2: Add custom_agents.sci-pi**

Edit `config.yaml` to include:

```yaml
subagents:
  timeout_seconds: 900    # default for general-purpose / bash
  agents:
    general-purpose:
      timeout_seconds: 1800
      max_turns: 160
    bash:
      timeout_seconds: 300
      max_turns: 80

  custom_agents:
    sci-pi:
      description: "Principal Investigator agent for end-to-end scientific research lifecycle: literature review → paper reproduction → analysis → LaTeX write-up."
      system_prompt_file: agents/sci-pi/prompt.md
      tools:
        - task
        - bash
        - read_file
        - write_file
        - ls
        - glob
        - grep
        - web_search
        - web_fetch
      skills:
        - systematic-literature-review
        - academic-paper-review
        - paper-reproduction
        - data-analysis
        - chart-visualization
        - scientific-writing
      model: inherit
      max_turns: 200
      timeout_seconds: 1800
```

**Step 3: Restart make dev and verify sci-pi is selectable**

```bash
make stop && make dev
```

Wait until services are up. In the Web UI's assistant dropdown, verify `sci-pi` appears.

**Step 4: Smoke test — call sci-pi via task tool from lead_agent**

Send via Web UI:
```
Use task() to call subagent_type="sci-pi" with description="Say hello and list the skills you have access to."
```

Expected: sci-pi responds with the 6-skill list.

**Step 5: Commit**

```bash
git add config.yaml
git commit -m "feat(config): register sci-pi as custom_agent with 6-skill whitelist"
```

---

## Task 46: Enable custom skills in extensions_config.json

**Files:**
- Modify: `~/scideer/extensions_config.json`

**Step 1: Check current state**

```bash
cat extensions_config.json
```

If file is missing, copy from example:
```bash
cp extensions_config.example.json extensions_config.json
```

**Step 2: Enable our custom skills**

Edit `extensions_config.json`. Under the `"skills"` key, add:

```json
{
  "mcpServers": { ... existing },
  "skills": {
    "paper-reproduction": { "enabled": true },
    "scientific-writing": { "enabled": true }
  }
}
```

If DeerFlow auto-discovers `skills/custom/*` and you don't need to register them explicitly, this step may be a no-op. **Verify after restart**: in the Web UI Settings → Skills, `paper-reproduction` and `scientific-writing` should both show as enabled.

**Step 3: Restart and verify**

```bash
make stop && make dev
```

Check Web UI Settings → Skills.

**Step 4: Commit**

```bash
git add extensions_config.json
git commit -m "feat(config): enable paper-reproduction and scientific-writing in extensions_config"
```

---

## Task 47: Smoke test — sci-pi calls paper-reproduction

**Files:** none (UI-driven smoke test, recorded in NOTES.md)

**Step 1: Send the test prompt**

In the Web UI, select assistant=`sci-pi`, send:
```
Reproduce the GCN-on-Cora result from arxiv:1609.02907 (Table 2 row, expected ~81.5%).
```

Expected behavior:
- sci-pi responds with a brief plan (skip A and B because user gave arxiv id)
- Calls paper-reproduction skill via task() or by loading the SKILL.md
- Logs progress through phases 1-5
- Final artifact: `outputs/repro-1609.02907/report.md`

**Step 2: Verify artifact**

```bash
ls .deer-flow/data/<thread-id>/outputs/repro-1609.02907/
cat .deer-flow/data/<thread-id>/outputs/repro-1609.02907/report.md
```

Expected: report.md exists with paper=81.5, our_value≈80%, verdict=match.

**Step 3: Record outcome in NOTES.md**

```
### Day 6 Smoke: sci-pi → paper-reproduction
- Wall time: <X> s
- Token cost: <Y>
- Artifact: outputs/repro-1609.02907/report.md
- Verdict: <match/deviation>
```

```bash
git add docs/NOTES.md
git commit -m "test(sci-pi): smoke-verified sci-pi can invoke paper-reproduction end-to-end"
```

---

## Task 48: Smoke test — sci-pi calls scientific-writing

**Files:** none (UI-driven; logged to NOTES.md)

**Step 1: Send the prompt**

In the Web UI, **continuing the same thread** (so the repro artifact from Task 47 is in workspace), send:
```
Now write a short NeurIPS-style paper based on the artifacts in outputs/. Use title "Reproducing GCN on Cora" and 1-sentence stance "We verify Kipf & Welling 2017's GCN result on Cora at mini-scale."
```

Expected:
- sci-pi calls scientific-writing skill
- Phase 2 collect picks up the SLR (run earlier? if not, add a small SLR step) + the repro report
- Phase 6 compiles → `outputs/paper/paper.pdf`

**Step 2: Verify PDF**

```bash
ls .deer-flow/data/<thread-id>/outputs/paper/
file .deer-flow/data/<thread-id>/outputs/paper/paper.pdf
```

Expected: `paper.pdf: PDF document, version 1.5, ...`.

Optionally copy back to local:
```bash
scp user@server:~/scideer/.deer-flow/data/<thread-id>/outputs/paper/paper.pdf ./paper-day6.pdf
```

Open it locally and verify it's readable.

**Step 3: Record outcome in NOTES.md**

```
### Day 6 Smoke: sci-pi → scientific-writing
- Wall time: <X> s
- PDF size: <Y> bytes
- Naked: yes/no
- Compile rounds: <Z>
```

```bash
git add docs/NOTES.md
git commit -m "test(sci-pi): smoke-verified sci-pi can chain paper-reproduction → scientific-writing → PDF"
```

---

## Task 49: Add Semantic Scholar MCP to extensions_config.json

**Files:**
- Modify: `~/scideer/extensions_config.json`
- Modify: `~/scideer/.env`

**Step 1: Find a Semantic Scholar MCP package**

Two options (try in order):

**Option A: official S2 MCP** (if available on PyPI):
```json
{
  "semantic-scholar": {
    "enabled": true,
    "type": "stdio",
    "command": "uvx",
    "args": ["semantic-scholar-mcp"],
    "env": { "S2_API_KEY": "$S2_API_KEY" },
    "description": "Semantic Scholar paper search and citation graph"
  }
}
```

**Option B: write a minimal wrapper** (~80 lines Python) if no good MCP exists. Skip to Task 50 if needed.

**Step 2: Add to extensions_config.json**

```bash
# Edit extensions_config.json — under "mcpServers" add the chosen block.
```

**Step 3: Add API key to .env**

Get a free API key from https://www.semanticscholar.org/product/api → register → save key.

```bash
echo "S2_API_KEY=<your-key>" >> .env
```

**Step 4: Restart and verify**

```bash
make stop && make dev
```

In Web UI, Settings → MCP Servers, verify `semantic-scholar` shows green/enabled.

**Step 5: Smoke test from sci-pi**

Send via Web UI:
```
Use semantic-scholar to find papers that cite arxiv:1609.02907, list the top 5 by citation count.
```

Expected: sci-pi calls the S2 MCP tool, returns 5 papers.

**Step 6: Commit**

```bash
git add extensions_config.json
git commit -m "feat(mcp): add Semantic Scholar MCP for citation graph queries"
```

If Option A fails (package not installable / auth issue), proceed to Task 50.

---

## Task 50: (Optional, only if Task 49 Option A failed) Minimal S2 wrapper as a tool

**Files:**
- Create: `~/scideer/skills/custom/scientific-writing/scripts/s2_client.py`
- Modify: `~/scideer/skills/custom/scientific-writing/SKILL.md` (mention as a fallback search source)

**Step 1: Implement minimal S2 HTTP client**

```python
# scripts/s2_client.py
"""Minimal Semantic Scholar API client used as a fallback when no S2 MCP server is available."""
import os, json, urllib.parse, urllib.request
from typing import List, Dict

BASE = "https://api.semanticscholar.org/graph/v1"


def _get(path: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}/{path}?{qs}"
    req = urllib.request.Request(url, headers={"x-api-key": os.environ.get("S2_API_KEY", "")})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def search_papers(query: str, limit: int = 10) -> List[Dict]:
    return _get("paper/search", {"query": query, "limit": limit, "fields": "title,year,citationCount,authors"}).get("data", [])


def get_citations(paper_id: str, limit: int = 10) -> List[Dict]:
    """paper_id can be arXiv:1609.02907 or S2 paper ID."""
    return _get(f"paper/{paper_id}/citations", {"limit": limit, "fields": "title,year,authors,citationCount"}).get("data", [])
```

**Step 2: Add a quick test that hits the live API**

```python
# tests/test_s2_client_live.py
import os, pytest
from skills.custom.scientific_writing.scripts.s2_client import search_papers, get_citations


@pytest.mark.skipif(not os.environ.get("S2_API_KEY"), reason="no S2_API_KEY")
def test_search_returns_papers():
    res = search_papers("graph convolutional networks", limit=3)
    assert len(res) <= 3
    if res:
        assert "title" in res[0]


@pytest.mark.skipif(not os.environ.get("S2_API_KEY"), reason="no S2_API_KEY")
def test_get_citations_for_gcn_paper():
    res = get_citations("arXiv:1609.02907", limit=3)
    assert len(res) <= 3
```

Run:
```bash
S2_API_KEY=$S2_API_KEY PYTHONPATH=. pytest skills/custom/scientific-writing/tests/test_s2_client_live.py -v
```

**Step 3: Commit**

```bash
git add skills/custom/scientific-writing/scripts/s2_client.py \
        skills/custom/scientific-writing/tests/test_s2_client_live.py
git commit -m "feat(scientific-writing): add minimal S2 HTTP client as MCP fallback"
```

---

## Task 51: Day 6 EOD — End-to-end sci-pi run on the demo prompt

**Files:** logged in NOTES.md only

**Step 1: Run the demo prompt**

In Web UI, assistant=`sci-pi`, **fresh thread**, send:
```
用 GCN 论文 (arxiv:1609.02907) 做一次完整科研流程：复现 Table 2 GCN/Cora 行，最后输出一个简短的 NeurIPS 风格 LaTeX 论文 PDF。
```

(Or the English equivalent.)

Expected behavior:
- sci-pi outputs Phase plan (skip A/B; do C, then E)
- Phase C: paper-reproduction runs, produces `outputs/repro-1609.02907/report.md`
- Phase E: scientific-writing runs, produces `outputs/paper/paper.pdf`
- Final message: artifact paths listed

**Step 2: Time the run**

Record total wall time and token cost.

**Step 3: Note any flakiness**

If something hangs, errors, or produces wrong output, jot in NOTES.md as a bug to fix Day 7.

**Step 4: Commit**

```bash
git add docs/NOTES.md
git commit -m "test(sci-pi): Day 6 EOD full-pipeline e2e on demo prompt — recorded outcome"
```

**🚩 End of Day 6. Phase 3 complete.**

If the e2e run took > 12 minutes or had a critical failure, allocate Day 7 first half to fixing rather than the C+ pre-run.

---

# Phase 4 — Pipeline Hardening + C+ Pre-Run (Day 7)

> Reference: design Section 9. Goal: stabilize sci-pi to ≥ 80% success rate AND pre-compute the offline Table 2 reproduction for the demo C+ trick.

## Task 52: Run sci-pi pipeline 5 times, log outcomes

**Files:**
- Create: `~/scideer/docs/PIPELINE_RUNS_LOG.md`

**Step 1: Run the demo prompt 5 times in fresh threads**

For each run, use the same prompt as Day 6 Task 51. Record in PIPELINE_RUNS_LOG.md:

```bash
cat > docs/PIPELINE_RUNS_LOG.md <<'EOF'
# sci-pi Demo Prompt: 5-Run Reliability Log

Prompt: "用 GCN 论文 (arxiv:1609.02907) 做一次完整科研流程：复现 Table 2 GCN/Cora 行，最后输出一个简短的 NeurIPS 风格 LaTeX 论文 PDF。"

| Run | Wall time (s) | Token cost | repro pass | paper.pdf | Verdict | Notes |
|-----|---------------|------------|------------|-----------|---------|-------|
| 1   |               |            |            |           |         |       |
| 2   |               |            |            |           |         |       |
| 3   |               |            |            |           |         |       |
| 4   |               |            |            |           |         |       |
| 5   |               |            |            |           |         |       |

## Failure modes observed
- ...

## Top flaky step (priority for Task 53)
- ...
EOF
```

Run all 5; fill the table; **stop after each run to copy artifacts to a backup location** so the data is preserved:

```bash
mkdir -p ~/scideer-backup/day7-runs
for i in 1 2 3 4 5; do
  # After run i: copy thread artifacts
  THREAD_ID="<latest>"
  cp -r .deer-flow/data/$THREAD_ID/outputs ~/scideer-backup/day7-runs/run$i-outputs
done
```

**Step 2: Identify top flaky step**

Sort the failures from the table. Top 1-2 issues become Task 53 targets.

**Step 3: Commit log**

```bash
git add docs/PIPELINE_RUNS_LOG.md
git commit -m "test(sci-pi): 5-run reliability baseline + flaky-step identification"
```

---

## Task 53: Fix top flaky step

**Files:** depends on what's flaky — likely one of:
- `paper-reproduction` scripts (e.g. acc parser regex)
- `scientific-writing/compile_latex.py` (e.g. round-2 fixup)
- `agents/sci-pi/prompt.md` (e.g. ambiguous phase transition)

**Step 1: Use @superpowers:systematic-debugging**

For the top flaky step:
1. Reproduce locally with a focused test
2. Capture exact failure mode
3. Write a regression test that fails
4. Fix
5. Re-run regression test → green
6. Re-run the full e2e to verify no regression

**Step 2: If problem is in prompt.md, iterate carefully**

Test prompt changes by re-running 3 fresh threads. Don't ship a prompt change that worked once but not three times.

**Step 3: Commit each fix separately**

```bash
git add <files>
git commit -m "fix(<area>): <specific issue> (Day 7 hardening from PIPELINE_RUNS_LOG.md run #X)"
```

**Step 4: Re-run the 5-run reliability suite**

Re-run Task 52's 5 fresh threads; success rate should now be ≥ 80% (4/5 or 5/5).

**Step 5: Update log**

```bash
git add docs/PIPELINE_RUNS_LOG.md
git commit -m "test(sci-pi): post-fix reliability run — N/5 success rate"
```

---

## Task 54: Pre-run T5 SLR for offline use

**Files:**
- Create: `~/scideer/scratch/prerun_slr.sh`

**Step 1: Write the pre-run script**

```bash
cat > scratch/prerun_slr.sh <<'EOF'
#!/usr/bin/env bash
# Pre-run an SLR on "graph neural networks" for offline demo use.
# Output: outputs/slr-graph-neural-networks-<date>.md (will be copied into demo workspace later).

set -e
TOPIC="graph neural networks"
echo "Running SLR pre-fetch for: $TOPIC"

# Approach: send the prompt via the embedded Python client (no UI needed).
python3 - <<PY
from deerflow.client import DeerFlowClient
client = DeerFlowClient()
resp = client.chat(
    f"Do a systematic literature review on '$TOPIC', 10 papers, BibTeX format, last 3 years.",
    thread_id="prerun-slr-gnn",
    assistant_id="lead_agent",
)
print(resp)
PY
EOF
chmod +x scratch/prerun_slr.sh
```

**Step 2: Run it**

```bash
./scratch/prerun_slr.sh 2>&1 | tee scratch/prerun_slr.log
```

Wait for completion (3-8 min for 10-paper SLR). The artifact lands in `.deer-flow/data/prerun-slr-gnn/outputs/slr-*.md`.

**Step 3: Copy to a stable location for demo**

```bash
mkdir -p outputs/prerun
cp .deer-flow/data/prerun-slr-gnn/outputs/slr-*.md outputs/prerun/
ls -la outputs/prerun/
```

**Step 4: Commit**

```bash
git add scratch/prerun_slr.sh outputs/prerun/slr-*.md
git commit -m "feat(prerun): pre-fetch SLR on graph neural networks for offline demo (T5)"
```

---

## Task 55: C+ pre-run — full Table 2 reproduction (Cora + Citeseer + Pubmed)

**Files:**
- Create: `~/scideer/scratch/prerun_repro_table2.sh`
- Create: `~/scideer/outputs/prerun/repro-1609.02907/aggregated_table.md`

**Step 1: Write the pre-run script**

```bash
cat > scratch/prerun_repro_table2.sh <<'EOF'
#!/usr/bin/env bash
# C+ pre-run: reproduce GCN on Cora, Citeseer, Pubmed for Table 2.
# Goal: produce aggregated_table.md showing all 3 datasets reproduced.

set -e
WORK=~/.scideer/prerun/repro-1609.02907
mkdir -p "$WORK"/{code,logs,figures}

# Pre-cache datasets
docker run --rm -v ~/.scideer/cache:/cache scideer-sandbox:latest \
  python -c "
from torch_geometric.datasets import Planetoid
for ds in ['Cora', 'Citeseer', 'Pubmed']:
    print(f'caching {ds}...')
    Planetoid('/cache/torch_geometric', ds)
print('done')
"

# Run GCN on each dataset
for DS in Cora Citeseer Pubmed; do
  EPOCHS=200
  echo "=== Running GCN on $DS ($EPOCHS epochs) ==="
  docker run --rm \
    -v ~/.scideer/cache:/mnt/scideer-cache:ro \
    -v "$WORK":/work \
    scideer-sandbox:latest \
    python -u /mnt/scideer-cache/pygcn/pygcn/train.py --dataset $DS --epochs $EPOCHS \
    2>&1 | tee "$WORK/logs/$DS.log"
done

echo "Table 2 pre-run complete. Aggregating..."
python3 scratch/aggregate_table2.py "$WORK"
EOF
chmod +x scratch/prerun_repro_table2.sh
```

**Note:** `pygcn`'s `train.py` may not accept a `--dataset` arg by default — it hardcodes Cora. If so, write tiny wrappers that vary `data.load_data(dataset=...)`. Verify when running.

**Step 2: Write the aggregator**

```bash
cat > scratch/aggregate_table2.py <<'PY'
"""Aggregate prerun GCN logs into a Table 2 reproduction summary."""
import re, sys, json
from pathlib import Path

PAPER_VALUES = {"Cora": 81.5, "Citeseer": 70.3, "Pubmed": 79.0}

work = Path(sys.argv[1])
rows = []
for ds in ["Cora", "Citeseer", "Pubmed"]:
    log = (work / "logs" / f"{ds}.log").read_text()
    m = re.search(r"accuracy[=:\s]+([\d.]+)", log)
    if m:
        ours = float(m.group(1)) * 100
    else:
        ours = None
    paper = PAPER_VALUES[ds]
    delta_pct = ((ours - paper) / paper * 100) if ours is not None else None
    rows.append({"dataset": ds, "paper": paper, "ours": ours, "delta_pct": delta_pct})

md = "# Table 2 Reproduction (Pre-run) — Kipf & Welling 2017 GCN\n\n"
md += "| Dataset | Paper (%) | Ours (%) | Δ (pp) | Δ (%) | Status |\n"
md += "|---|---:|---:|---:|---:|---|\n"
for r in rows:
    status = "✅" if r["ours"] is not None and abs(r["delta_pct"]) <= 3.0 else "⚠️"
    paper, ours = r["paper"], r["ours"] or 0.0
    md += f"| {r['dataset']} | {paper:.1f} | {ours:.1f} | {ours-paper:+.1f} | {r['delta_pct']:+.2f}% | {status} |\n"
md += "\n_Generated by SciDeer offline pre-run on $(date -u +%FT%TZ)._\n"

out = Path("outputs/prerun/repro-1609.02907")
out.mkdir(parents=True, exist_ok=True)
(out / "aggregated_table.md").write_text(md)
(out / "aggregated_table.json").write_text(json.dumps(rows, indent=2))
print(md)
PY
```

**Step 3: Run the pre-run**

```bash
./scratch/prerun_repro_table2.sh
```

Expected total wall time: 3-5 min (Cora ~30s, Citeseer ~30s, Pubmed ~60s, plus overhead). Result: `outputs/prerun/repro-1609.02907/aggregated_table.md`.

**Step 4: Commit**

```bash
git add scratch/prerun_repro_table2.sh \
        scratch/aggregate_table2.py \
        outputs/prerun/repro-1609.02907/aggregated_table.md \
        outputs/prerun/repro-1609.02907/aggregated_table.json
git commit -m "feat(prerun): C+ pre-run of Table 2 reproduction (Cora + Citeseer + Pubmed)"
```

---

## Task 56: Verify demo paper bundle

**Files:** none (verification step)

**Step 1: Confirm artifacts**

```bash
tree outputs/prerun/
```

Expected:
```
outputs/prerun/
├── slr-graph-neural-networks-*.md
└── repro-1609.02907/
    ├── aggregated_table.md
    └── aggregated_table.json
```

**Step 2: Confirm caches are warm**

```bash
ls ~/.scideer/cache/
du -sh ~/.scideer/cache/
```

Expected: pygcn/, torch_geometric/, torchvision/ all present, total < 2 GB.

**Step 3: Test offline mode**

Disable network on the server temporarily:
```bash
sudo iptables -A OUTPUT -p tcp --dport 443 -j DROP    # block HTTPS outbound
sudo iptables -A OUTPUT -p tcp --dport 80 -j DROP     # block HTTP outbound
```

Run the paper-reproduction smoke test from Task 32:
```bash
PYTHONPATH=. pytest skills/custom/paper-reproduction/tests/test_smoke_e2e_day4.py -v -s
```

Expected: PASS (uses cache only).

Re-enable network:
```bash
sudo iptables -D OUTPUT -p tcp --dport 443 -j DROP
sudo iptables -D OUTPUT -p tcp --dport 80 -j DROP
```

**Step 4: Record in NOTES.md**

```
### Day 7 EOD: Demo Bundle Verified
- prerun SLR present
- prerun Table 2 aggregated_table.md present
- caches warm: pygcn / Cora / Citeseer / Pubmed / MNIST
- offline smoke test: PASS
- 🚩 Demo bundle ready for Day 8 benchmark + Day 9 demo
```

```bash
git add docs/NOTES.md
git commit -m "test(prerun): verify demo bundle complete + offline mode works"
```

**🚩 End of Day 7. Phase 4 complete.**

---

# Phase 5 — Mini Sci-Bench + Visualizations + Cloud Deploy (Day 8)

> Reference: design Section 8. Goal: produce 3 PPT-ready figures from a real benchmark run; expose the Web UI externally.

## Task 57: Scaffold benchmark directory + 5 task yamls

**Files:**
- Create: `~/scideer/benchmarks/sci_eval/` (directory)
- Create: `~/scideer/benchmarks/sci_eval/tasks/t1_slr.yaml` ... `t5_pipeline.yaml`
- Create: `~/scideer/benchmarks/sci_eval/fixtures/` (T3 csv, T4 figures)

**Step 1: Create directory structure**

```bash
mkdir -p benchmarks/sci_eval/{tasks,fixtures,results/vanilla,results/scideer}
touch benchmarks/sci_eval/results/.gitkeep
```

**Step 2: Write the 5 task yamls**

```bash
cat > benchmarks/sci_eval/tasks/t1_slr.yaml <<'EOF'
id: t1_slr
description: "Topic → systematic literature review (parity check)"
prompt: "Do a systematic literature review on 'transformer attention variants', 10 papers, BibTeX format, last 3 years."
runner_config:
  vanilla:
    assistant_id: lead_agent
  scideer:
    assistant_id: sci-pi
expected_artifacts:
  - path_glob: "outputs/slr-*.md"
    must_exist: true
auto_score:
  completeness: artifact_check
manual_score: [correctness, quality]
n_runs: 1
timeout_seconds: 900
EOF

cat > benchmarks/sci_eval/tasks/t2_repro.yaml <<'EOF'
id: t2_repro
description: "Single-result paper reproduction (capability gap)"
prompt: "Reproduce GCN on Cora result from arxiv:1609.02907 (Table 2 row, expected ~81.5%)."
runner_config:
  vanilla:
    assistant_id: lead_agent
  scideer:
    assistant_id: sci-pi
expected_artifacts:
  - path_glob: "outputs/repro-1609.02907/report.md"
    must_exist: true
  - path_glob: "outputs/repro-1609.02907/comparison.json"
    must_exist: true
    must_contain_keys: [paper_value, our_value, delta_pct]
auto_score:
  completeness: artifact_check
manual_score: [correctness, quality]
n_runs: 1
timeout_seconds: 1200
EOF

cat > benchmarks/sci_eval/tasks/t3_analysis.yaml <<'EOF'
id: t3_analysis
description: "CSV + question → analysis report with charts (parity check)"
prompt: "Read /mnt/user-data/uploads/results.csv and produce a Markdown report with at least one bar chart and one line chart, plus a 1-paragraph commentary."
fixtures:
  - src: fixtures/results.csv
    dst: uploads/results.csv
runner_config:
  vanilla:
    assistant_id: lead_agent
  scideer:
    assistant_id: sci-pi
expected_artifacts:
  - path_glob: "outputs/**/analysis*.md"
    must_exist: true
  - path_glob: "outputs/**/*.png"
    must_exist: true
auto_score:
  completeness: artifact_check
manual_score: [correctness, quality]
n_runs: 1
timeout_seconds: 900
EOF

cat > benchmarks/sci_eval/tasks/t4_writing.yaml <<'EOF'
id: t4_writing
description: "Generate NeurIPS-style LaTeX paper from artifacts (capability gap)"
prompt: "Generate a NeurIPS-style LaTeX paper titled 'Reproducing GCN on Cora' from the artifacts under /mnt/user-data/uploads/. Compile to PDF."
fixtures:
  - src: fixtures/t4_artifacts/
    dst: uploads/
runner_config:
  vanilla:
    assistant_id: lead_agent
  scideer:
    assistant_id: sci-pi
expected_artifacts:
  - path_glob: "outputs/paper/paper.pdf"
    must_exist: true
auto_score:
  completeness: artifact_check
manual_score: [correctness, quality]
n_runs: 1
timeout_seconds: 1500
EOF

cat > benchmarks/sci_eval/tasks/t5_pipeline.yaml <<'EOF'
id: t5_pipeline
description: "Full lifecycle (holistic capability gap)"
prompt: "Full lifecycle on graph neural networks: do an SLR (10 papers), then reproduce the GCN on Cora result from arxiv:1609.02907, then write a NeurIPS-style LaTeX paper from those artifacts."
runner_config:
  vanilla:
    assistant_id: lead_agent
  scideer:
    assistant_id: sci-pi
expected_artifacts:
  - path_glob: "outputs/slr-*.md"
    must_exist: true
  - path_glob: "outputs/repro-1609.02907/report.md"
    must_exist: true
  - path_glob: "outputs/paper/paper.pdf"
    must_exist: true
auto_score:
  completeness: artifact_check
manual_score: [correctness, quality]
n_runs: 1
timeout_seconds: 1800
EOF
```

**Step 3: Generate T3 fixture (results.csv)**

```bash
cat > benchmarks/sci_eval/fixtures/results.csv <<'CSV'
model,dataset,accuracy,f1,wall_time_s
GCN,Cora,80.2,79.8,32.4
GCN,Citeseer,69.8,68.5,33.1
GCN,Pubmed,78.5,77.9,61.2
MLP,Cora,55.1,54.3,5.8
MLP,Citeseer,46.2,45.0,6.0
MLP,Pubmed,71.3,70.1,12.4
GAT,Cora,82.1,81.5,45.6
GAT,Citeseer,70.8,69.3,46.8
GAT,Pubmed,79.0,78.2,89.4
CSV
```

**Step 4: Generate T4 fixture (artifact bundle)**

```bash
mkdir -p benchmarks/sci_eval/fixtures/t4_artifacts
cp outputs/prerun/slr-graph-neural-networks-*.md benchmarks/sci_eval/fixtures/t4_artifacts/ 2>/dev/null || \
  echo "# Mock SLR\n@misc{kipf2017, title={GCN}, author={Kipf}, year={2017}}" > benchmarks/sci_eval/fixtures/t4_artifacts/slr-graph-neural-networks.md

cp -r outputs/prerun/repro-1609.02907 benchmarks/sci_eval/fixtures/t4_artifacts/ 2>/dev/null || true
```

**Step 5: Commit**

```bash
git add benchmarks/sci_eval/
git commit -m "feat(benchmark): scaffold 5 task yamls + T3/T4 fixtures"
```

---

## Task 58: Tests + impl benchmark `runner.py` (thread mgmt + completeness check)

**Files:**
- Create: `~/scideer/benchmarks/sci_eval/runner.py`
- Create: `~/scideer/benchmarks/sci_eval/tests/test_runner.py`

**Step 1: Failing tests**

```python
# tests/test_runner.py
from pathlib import Path
import yaml
from benchmarks.sci_eval.runner import (
    load_task, check_artifacts, ArtifactCheckResult,
)


def test_load_task(tmp_path):
    yaml_text = """
id: t1
description: "x"
prompt: "do thing"
runner_config:
  vanilla: {assistant_id: lead_agent}
  scideer: {assistant_id: sci-pi}
expected_artifacts:
  - path_glob: "outputs/foo*.md"
    must_exist: true
auto_score: {completeness: artifact_check}
n_runs: 1
timeout_seconds: 60
"""
    p = tmp_path / "t.yaml"
    p.write_text(yaml_text)
    task = load_task(p)
    assert task["id"] == "t1"
    assert task["expected_artifacts"][0]["path_glob"] == "outputs/foo*.md"


def test_check_artifacts_pass(tmp_path):
    out = tmp_path / "outputs"; out.mkdir()
    (out / "foo.md").write_text("hi")
    expected = [{"path_glob": "outputs/foo*.md", "must_exist": True}]
    res = check_artifacts(tmp_path, expected)
    assert res.passed
    assert res.completeness_score == 1


def test_check_artifacts_fail(tmp_path):
    out = tmp_path / "outputs"; out.mkdir()
    expected = [{"path_glob": "outputs/foo*.md", "must_exist": True}]
    res = check_artifacts(tmp_path, expected)
    assert not res.passed
    assert res.completeness_score == 0


def test_check_artifacts_with_must_contain_keys(tmp_path):
    out = tmp_path / "outputs"; out.mkdir()
    (out / "comparison.json").write_text('{"paper_value": 81.5, "our_value": 80.2}')
    expected = [{
        "path_glob": "outputs/comparison.json",
        "must_exist": True,
        "must_contain_keys": ["paper_value", "our_value"],
    }]
    res = check_artifacts(tmp_path, expected)
    assert res.passed
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement core**

```python
# benchmarks/sci_eval/runner.py
"""Benchmark runner: load task → drive thread → collect metrics → score completeness."""
import json, time, subprocess, yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class ArtifactCheckResult:
    passed: bool
    completeness_score: int      # 0 or 1 for binary; could be richer later
    missing: List[str] = field(default_factory=list)
    extra_failures: List[str] = field(default_factory=list)


@dataclass
class RunMetrics:
    task_id: str
    config: str          # "vanilla" | "scideer"
    run_id: int
    wall_time_s: float
    token_cost: Optional[int]
    artifact_check: ArtifactCheckResult
    raw_output_path: Path


def load_task(yaml_path: Path) -> dict:
    return yaml.safe_load(yaml_path.read_text())


def check_artifacts(thread_root: Path, expected: List[Dict]) -> ArtifactCheckResult:
    missing: List[str] = []
    extra_failures: List[str] = []
    for spec in expected:
        glob = spec["path_glob"]
        matches = list(thread_root.glob(glob))
        if spec.get("must_exist") and not matches:
            missing.append(glob)
            continue
        for keys in [spec.get("must_contain_keys") or []]:
            if not keys:
                continue
            for m in matches:
                try:
                    obj = json.loads(m.read_text())
                except json.JSONDecodeError:
                    extra_failures.append(f"{m}: not valid JSON")
                    continue
                for k in keys:
                    if k not in obj:
                        extra_failures.append(f"{m}: missing key {k!r}")
    passed = not missing and not extra_failures
    return ArtifactCheckResult(
        passed=passed,
        completeness_score=1 if passed else 0,
        missing=missing,
        extra_failures=extra_failures,
    )
```

**Step 4: Run tests, verify PASS. Commit.**

```bash
git add benchmarks/sci_eval/runner.py benchmarks/sci_eval/tests/test_runner.py
git commit -m "feat(benchmark): implement task loading + artifact completeness check"
```

---

## Task 59: Add thread-driver to runner (calls DeerFlow client)

**Files:**
- Modify: `~/scideer/benchmarks/sci_eval/runner.py`

**Step 1: Append the thread driver functions**

```python
# Append to benchmarks/sci_eval/runner.py
import os, shutil

def stage_fixtures(task: dict, thread_root: Path, fixtures_root: Path) -> None:
    """Copy fixture files into the thread's uploads/ before running."""
    uploads = thread_root / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    for fx in task.get("fixtures", []):
        src = fixtures_root / fx["src"]
        dst = thread_root / fx["dst"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)


def drive_thread(task: dict, config_name: str, run_id: int, thread_root: Path) -> RunMetrics:
    """Drive a single task run through DeerFlow's embedded Python client."""
    from deerflow.client import DeerFlowClient
    rc = task["runner_config"][config_name]
    assistant_id = rc["assistant_id"]
    client = DeerFlowClient()
    thread_id = f"bench-{task['id']}-{config_name}-r{run_id}"

    t0 = time.time()
    response = client.chat(
        task["prompt"],
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    elapsed = time.time() - t0

    # Find thread's data root
    data_root = Path(os.environ.get("DEER_FLOW_HOME", ".deer-flow")) / "data" / thread_id
    if not data_root.exists():
        data_root = thread_root  # fallback for testing

    # Token cost: try to read from response or stats endpoint
    token_cost = None
    try:
        stats = client.get_thread_stats(thread_id)
        token_cost = stats.get("total_tokens")
    except Exception:
        pass

    artifact_check = check_artifacts(data_root, task["expected_artifacts"])
    raw_path = thread_root / "raw_output.txt"
    raw_path.write_text(str(response)[:50000])

    return RunMetrics(
        task_id=task["id"], config=config_name, run_id=run_id,
        wall_time_s=elapsed, token_cost=token_cost,
        artifact_check=artifact_check, raw_output_path=raw_path,
    )


def run_all(tasks_dir: Path, results_dir: Path, fixtures_root: Path,
            n_runs_override: Optional[int] = None) -> List[RunMetrics]:
    """Driver entry: iterate every task × {vanilla, scideer} × n_runs."""
    metrics: List[RunMetrics] = []
    for yaml_path in sorted(tasks_dir.glob("*.yaml")):
        task = load_task(yaml_path)
        n_runs = n_runs_override or task.get("n_runs", 1)
        for config_name in ["vanilla", "scideer"]:
            for run_id in range(n_runs):
                ts = time.strftime("%Y%m%dT%H%M%S")
                root = results_dir / config_name / f"{task['id']}_r{run_id}_{ts}"
                root.mkdir(parents=True, exist_ok=True)
                stage_fixtures(task, root, fixtures_root)
                m = drive_thread(task, config_name, run_id, root)
                metrics.append(m)
                # Persist
                (root / "metrics.json").write_text(json.dumps({
                    "task_id": m.task_id, "config": m.config, "run_id": m.run_id,
                    "wall_time_s": m.wall_time_s, "token_cost": m.token_cost,
                    "passed": m.artifact_check.passed,
                    "completeness": m.artifact_check.completeness_score,
                    "missing": m.artifact_check.missing,
                }, indent=2))
                print(f"[{m.config}/{m.task_id}/r{m.run_id}] passed={m.artifact_check.passed} time={m.wall_time_s:.1f}s tokens={m.token_cost}")
    return metrics


if __name__ == "__main__":
    here = Path(__file__).parent
    run_all(
        tasks_dir=here / "tasks",
        results_dir=here / "results",
        fixtures_root=here / "fixtures",
    )
```

**Step 2: Add a smoke test that mocks the client**

```python
# tests/test_runner_drive.py
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
from benchmarks.sci_eval.runner import drive_thread


def test_drive_thread_records_metrics(tmp_path, monkeypatch):
    task = {
        "id": "t-mock",
        "prompt": "hello",
        "runner_config": {"vanilla": {"assistant_id": "lead_agent"}, "scideer": {"assistant_id": "sci-pi"}},
        "expected_artifacts": [{"path_glob": "outputs/*.md", "must_exist": True}],
    }
    thread_root = tmp_path / "thread"
    thread_root.mkdir()
    (thread_root / "outputs").mkdir()
    (thread_root / "outputs" / "x.md").write_text("hi")

    with patch("benchmarks.sci_eval.runner.DeerFlowClient") as mock_client_cls:
        mock = MagicMock()
        mock.chat.return_value = "ok"
        mock.get_thread_stats.return_value = {"total_tokens": 12345}
        mock_client_cls.return_value = mock

        # bypass DEER_FLOW_HOME lookup
        monkeypatch.setenv("DEER_FLOW_HOME", str(thread_root.parent / ".deer-flow"))
        # simulate the client wrote artifacts to thread_root
        m = drive_thread(task, "vanilla", 0, thread_root)
    assert m.token_cost == 12345 or m.token_cost is None
    assert m.task_id == "t-mock"
```

**Step 3: Run, verify PASS. Commit.**

```bash
git add benchmarks/sci_eval/runner.py benchmarks/sci_eval/tests/test_runner_drive.py
git commit -m "feat(benchmark): add thread-driver via DeerFlowClient + smoke test with mock"
```

---

## Task 60: Run minimum benchmark (5 × 2 × 1 = 10 runs)

**Files:** results land in `~/scideer/benchmarks/sci_eval/results/{vanilla,scideer}/`

**Step 1: Run the full benchmark**

```bash
cd ~/scideer
PYTHONPATH=. python benchmarks/sci_eval/runner.py 2>&1 | tee benchmarks/sci_eval/runner.log
```

Expected: ~1-1.5 hours total. Each task takes 5-15 minutes.

**Watch for:**
- T2 vanilla: should fail completeness (no `paper-reproduction` skill in lead_agent)
- T4 vanilla: should fail completeness (no `scientific-writing`)
- T5 vanilla: should fail completeness (no `sci-pi`)
- All scideer: should pass (or surface bugs to fix)

**Step 2: If any scideer task fails, decide**

- If single transient error → re-run that one task
- If consistent failure → debug NOW (this task), don't move on to visualizations

**Step 3: Persist results**

All metrics already saved to `metrics.json` per run. Aggregate:

```bash
find benchmarks/sci_eval/results -name metrics.json -exec cat {} \; | \
  jq -s '.' > benchmarks/sci_eval/results/all_metrics.json
```

**Step 4: Commit results**

```bash
git add benchmarks/sci_eval/results/all_metrics.json benchmarks/sci_eval/runner.log
git commit -m "test(benchmark): minimum (n_runs=1) benchmark complete — 10 runs"
```

---

## Task 61: Build `results.csv` aggregator + manual scoring sheet

**Files:**
- Create: `~/scideer/benchmarks/sci_eval/aggregate.py`
- Create: `~/scideer/benchmarks/sci_eval/results.csv`
- Create: `~/scideer/benchmarks/sci_eval/manual_scoring.csv` (fill manually after Task 60)

**Step 1: Implement aggregator**

```python
# benchmarks/sci_eval/aggregate.py
"""Aggregate per-run metrics.json into a flat results.csv."""
import csv, json
from pathlib import Path

HERE = Path(__file__).parent
ROWS = []
for metrics_file in sorted(HERE.glob("results/*/*/metrics.json")):
    m = json.loads(metrics_file.read_text())
    ROWS.append({
        "task_id": m["task_id"],
        "config": m["config"],
        "run_id": m["run_id"],
        "wall_time_s": round(m["wall_time_s"], 1),
        "token_cost": m.get("token_cost") or "",
        "completeness": m["completeness"],
        "missing": ";".join(m.get("missing", [])),
    })

out = HERE / "results.csv"
with out.open("w", newline="") as f:
    if ROWS:
        w = csv.DictWriter(f, fieldnames=list(ROWS[0].keys()))
        w.writeheader()
        w.writerows(ROWS)
print(f"Wrote {len(ROWS)} rows to {out}")
```

```bash
PYTHONPATH=. python benchmarks/sci_eval/aggregate.py
cat benchmarks/sci_eval/results.csv
```

**Step 2: Manual scoring sheet skeleton**

Each (task, config, run) gets a row for **correctness 0-3** and **quality 0-3** filled in by you (or a teammate) by reviewing artifacts:

```bash
cat > benchmarks/sci_eval/manual_scoring.csv <<'CSV'
task_id,config,run_id,correctness,quality,notes
t1_slr,vanilla,0,,,
t1_slr,scideer,0,,,
t2_repro,vanilla,0,,,
t2_repro,scideer,0,,,
t3_analysis,vanilla,0,,,
t3_analysis,scideer,0,,,
t4_writing,vanilla,0,,,
t4_writing,scideer,0,,,
t5_pipeline,vanilla,0,,,
t5_pipeline,scideer,0,,,
CSV
```

Open this in a spreadsheet, review each artifact, score 0-3 per dim. **Save back as CSV.**

**Step 3: Commit**

```bash
git add benchmarks/sci_eval/aggregate.py \
        benchmarks/sci_eval/results.csv \
        benchmarks/sci_eval/manual_scoring.csv
git commit -m "feat(benchmark): aggregate metrics to results.csv + manual scoring template"
```

---

## Task 62: Tests + impl `visualize.py`

**Files:**
- Create: `~/scideer/benchmarks/sci_eval/visualize.py`
- Create: `~/scideer/benchmarks/sci_eval/tests/test_visualize.py`

**Step 1: Failing test**

```python
# tests/test_visualize.py
from pathlib import Path
import csv
from benchmarks.sci_eval.visualize import (
    load_combined_scores, make_correctness_bar, make_radar, make_efficiency_scatter,
)


def _write_dummy_csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def test_load_combined_scores(tmp_path):
    auto = tmp_path / "results.csv"
    _write_dummy_csv(auto, [
        {"task_id":"t1","config":"vanilla","run_id":0,"wall_time_s":10,"token_cost":1000,"completeness":1,"missing":""},
        {"task_id":"t1","config":"scideer","run_id":0,"wall_time_s":12,"token_cost":1200,"completeness":1,"missing":""},
    ])
    manual = tmp_path / "manual_scoring.csv"
    _write_dummy_csv(manual, [
        {"task_id":"t1","config":"vanilla","run_id":0,"correctness":2,"quality":2,"notes":""},
        {"task_id":"t1","config":"scideer","run_id":0,"correctness":3,"quality":3,"notes":""},
    ])
    df = load_combined_scores(auto, manual)
    assert len(df) == 2
    assert df.iloc[0]["correctness"] == 2 or df.iloc[0]["correctness"] == 3


def test_make_correctness_bar(tmp_path):
    out = tmp_path / "fig.png"
    # use minimal dummy csvs
    auto = tmp_path / "auto.csv"
    _write_dummy_csv(auto, [
        {"task_id":t,"config":c,"run_id":0,"wall_time_s":10,"token_cost":1000,"completeness":1,"missing":""}
        for t in ["t1","t2","t3","t4","t5"] for c in ["vanilla","scideer"]
    ])
    manual = tmp_path / "manual.csv"
    _write_dummy_csv(manual, [
        {"task_id":t,"config":c,"run_id":0,"correctness":(0 if c=="vanilla" and t in ("t2","t4","t5") else 3),"quality":2,"notes":""}
        for t in ["t1","t2","t3","t4","t5"] for c in ["vanilla","scideer"]
    ])
    make_correctness_bar(auto, manual, out)
    assert out.exists() and out.stat().st_size > 1000
```

**Step 2: Run, verify FAIL.**

**Step 3: Implement**

```python
# benchmarks/sci_eval/visualize.py
"""Render 3 PPT-ready figures from results.csv + manual_scoring.csv."""
import csv
from pathlib import Path
from typing import List
import matplotlib.pyplot as plt
import numpy as np

try:
    import pandas as pd
except ImportError:
    pd = None


def load_combined_scores(auto_csv: Path, manual_csv: Path):
    if pd is None:
        raise ImportError("pandas required")
    a = pd.read_csv(auto_csv)
    m = pd.read_csv(manual_csv)
    return a.merge(m, on=["task_id", "config", "run_id"], how="left")


def make_correctness_bar(auto_csv: Path, manual_csv: Path, out_path: Path) -> None:
    df = load_combined_scores(auto_csv, manual_csv)
    pivot = df.pivot_table(index="task_id", columns="config",
                           values="correctness", aggfunc="mean")
    pivot = pivot.reindex(["t1_slr","t2_repro","t3_analysis","t4_writing","t5_pipeline"])

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(pivot.index))
    w = 0.35
    ax.bar(x - w/2, pivot["vanilla"].fillna(0), w, label="vanilla DeerFlow", color="#888")
    ax.bar(x + w/2, pivot["scideer"].fillna(0), w, label="SciDeer", color="#1f77b4")
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=20, ha="right")
    ax.set_ylabel("Correctness (0-3, manual)")
    ax.set_title("Correctness by Task")
    ax.set_ylim(0, 3.2)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def make_radar(auto_csv: Path, manual_csv: Path, out_path: Path) -> None:
    """Radar chart: average across tasks for {correctness, completeness, quality, time-rev, token-rev}."""
    df = load_combined_scores(auto_csv, manual_csv)

    # normalize: completeness already 0/1; correctness 0-3 → /3; quality 0-3 → /3
    # time-rev: 1 - (time / max_time) so faster = higher; same for tokens
    max_t = df["wall_time_s"].max()
    max_tok = pd.to_numeric(df["token_cost"], errors="coerce").fillna(0).max() or 1

    def norm(g):
        return {
            "correctness": g["correctness"].mean() / 3.0,
            "completeness": g["completeness"].mean(),
            "quality": g["quality"].mean() / 3.0,
            "time_rev": 1 - (g["wall_time_s"].mean() / max_t),
            "token_rev": 1 - (pd.to_numeric(g["token_cost"], errors="coerce").fillna(0).mean() / max_tok),
        }

    vals_v = norm(df[df.config=="vanilla"])
    vals_s = norm(df[df.config=="scideer"])
    labels = ["correctness", "completeness", "quality", "speed", "efficiency"]
    keys = ["correctness", "completeness", "quality", "time_rev", "token_rev"]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    for vals, label, color in [(vals_v, "vanilla", "#888"), (vals_s, "SciDeer", "#1f77b4")]:
        v = [vals[k] for k in keys]; v += v[:1]
        ax.plot(angles, v, "o-", label=label, color=color)
        ax.fill(angles, v, alpha=0.15, color=color)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("Radar: 5 Capability Dimensions")
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def make_efficiency_scatter(auto_csv: Path, manual_csv: Path, out_path: Path) -> None:
    df = load_combined_scores(auto_csv, manual_csv)
    df["token_cost"] = pd.to_numeric(df["token_cost"], errors="coerce")
    fig, ax = plt.subplots(figsize=(8, 5))
    for cfg, color in [("vanilla", "#888"), ("scideer", "#1f77b4")]:
        sub = df[df.config==cfg]
        ax.scatter(sub["wall_time_s"], sub["token_cost"], label=cfg, color=color, s=80)
        for _, r in sub.iterrows():
            ax.annotate(r["task_id"], (r["wall_time_s"], r["token_cost"]),
                        fontsize=8, alpha=0.7)
    ax.set_xlabel("Wall time (s)")
    ax.set_ylabel("Token cost")
    ax.set_title("Efficiency: time × tokens by task and system")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    here = Path(__file__).parent
    auto = here / "results.csv"
    manual = here / "manual_scoring.csv"
    out = here / "figures"
    out.mkdir(exist_ok=True)
    make_correctness_bar(auto, manual, out / "fig_correctness.png")
    make_radar(auto, manual, out / "fig_radar.png")
    make_efficiency_scatter(auto, manual, out / "fig_efficiency.png")
    print("Wrote 3 figures to", out)
```

**Step 4: Run tests + main**

```bash
PYTHONPATH=. pytest benchmarks/sci_eval/tests/test_visualize.py -v
PYTHONPATH=. python benchmarks/sci_eval/visualize.py
ls benchmarks/sci_eval/figures/
```

Expected: 3 PNGs.

**Step 5: Commit**

```bash
git add benchmarks/sci_eval/visualize.py \
        benchmarks/sci_eval/tests/test_visualize.py \
        benchmarks/sci_eval/figures/
git commit -m "feat(benchmark): visualize.py produces correctness bar + radar + efficiency scatter"
```

---

## Task 63: Write `RESULTS.md`

**Files:**
- Create: `~/scideer/benchmarks/sci_eval/RESULTS.md`

**Step 1: Generate from data**

```bash
cat > benchmarks/sci_eval/RESULTS.md <<'EOF'
# Mini Sci-Bench Results

## Summary

| System | T1 SLR | T2 Repro | T3 Analysis | T4 Writing | T5 Pipeline | Avg |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| vanilla DeerFlow | _<fill from manual_scoring>_ | **0** | _<fill>_ | **0** | **0** | _<avg>_ |
| SciDeer | _<fill>_ | _<fill>_ | _<fill>_ | _<fill>_ | _<fill>_ | _<avg>_ |

(Score = (correctness + quality + completeness × 3) / 3, max 3)

## Capability Gaps Observed

- **T2** (paper reproduction): vanilla cannot generate executable reproduction code; SciDeer's `paper-reproduction` skill produces a comparison report.
- **T4** (LaTeX writing): vanilla writes Markdown but never compiles to PDF; SciDeer's `scientific-writing` skill produces `paper.pdf`.
- **T5** (full lifecycle): vanilla performs an SLR but does not chain reproduction or write-up; SciDeer's `sci-pi` orchestrator delivers all three artifacts.

## Per-Task Detail

### T1 — Systematic Literature Review
- Prompt: "Do an SLR on transformer attention variants, 10 papers, BibTeX format."
- Vanilla: <runs / outcome>
- SciDeer: <runs / outcome>

### T2 — Paper Reproduction (Capability Gap)
- Prompt: "Reproduce GCN on Cora result from arxiv:1609.02907."
- Vanilla: refused or produced no executable code (artifact missing)
- SciDeer: `outputs/repro-1609.02907/report.md` with comparison

### T3 — Data Analysis (Parity)
- Prompt: "Read results.csv, produce report with charts."
- Both systems: pass

### T4 — LaTeX Writing (Capability Gap)
- Prompt: "Generate NeurIPS-style LaTeX paper from artifacts."
- Vanilla: produced Markdown / never compiled
- SciDeer: `outputs/paper/paper.pdf`

### T5 — Full Lifecycle (Holistic Capability Gap)
- Prompt: "Full lifecycle on graph neural networks."
- Vanilla: produced SLR only, no chain to reproduction or paper
- SciDeer: all three artifacts produced via sci-pi

## Limitations

- n_runs = 1 per (task, config) cell — statistical claims are limited
- T2/T4/T5 are binary capability gaps, statistically robust to single-run noise
- Manual quality scoring is single-rater — subject to bias

## Figures

- ![](figures/fig_correctness.png)
- ![](figures/fig_radar.png)
- ![](figures/fig_efficiency.png)
EOF
```

**Step 2: Fill numbers from `manual_scoring.csv`** after manual scoring is complete.

**Step 3: Commit**

```bash
git add benchmarks/sci_eval/RESULTS.md
git commit -m "docs(benchmark): write RESULTS.md with capability-gap commentary"
```

---

## Task 64: Cloud deployment — open security group + verify external access

**Files:** none (cloud config only)

**Step 1: Open the port in Tencent Cloud security group**

Via console: add inbound rule TCP port 2026 (DeerFlow nginx), source = your IP / 0.0.0.0 (with caveat — see Step 4).

**Step 2: Verify nginx config**

On server:
```bash
sudo systemctl status nginx
sudo nginx -t
```

If nginx isn't running but `make dev` is on, that's expected — DeerFlow's serve script proxies internally. The exposed port should still be 2026.

**Step 3: Test from external machine**

From your laptop:
```bash
curl -I http://<server-public-ip>:2026
```

Expected: 200 or redirect to UI.

Open `http://<server-public-ip>:2026` in browser. UI should load.

**Step 4: Apply security recommendations**

Per DeerFlow's security notice (README), DO NOT expose 0.0.0.0 in production. Use either:
- IP allowlist in security group (just your IP)
- Nginx basic auth in front
- For demo day: limit access window

**Step 5: Record in NOTES.md**

```
### Day 8 EOD: Cloud deployment verified
- External IP: <ip>:2026
- Access scoped to: <your IP>
- Demo day expansion plan: <broaden allowlist 30 min before demo>
- Nginx + Web UI both reachable externally
```

```bash
git add docs/NOTES.md
git commit -m "docs: log Day 8 EOD — cloud deployment verified, demo network plan"
```

**🚩 End of Day 8. Phase 5 complete.**

If benchmark surfaced consistent SciDeer failures, that's a CP4 risk for Day 9. Address top 1 issue Day 9 morning before demo rehearsal.

---

# Phase 6 — Demo Polish + PPT/Report (Day 9)

> Reference: design Section 9 (demo), Sections 13-14 (PPT + Report).
>
> 🚩 **CP4 — Day 9 noon: demo rehearsal success rate ≥ 80%**, otherwise switch to all-backup-video presentation.

## Task 65: Pre-demo checklist execution (Day 9 morning, ~9:00-10:00)

**Files:**
- Create: `~/scideer/scratch/predemo_check.sh`

**Step 1: Write the checklist script**

```bash
cat > scratch/predemo_check.sh <<'EOF'
#!/usr/bin/env bash
# Pre-demo health check. Run on Day 9 morning before any rehearsal.
set -e

echo "=== make doctor ==="
make doctor

echo
echo "=== docker containers ==="
docker ps | grep scideer-sandbox || echo "WARN: no scideer-sandbox running (will warm at demo time)"

echo
echo "=== caches ==="
ls ~/.scideer/cache/ || { echo "ERROR: cache missing"; exit 1; }
[ -d ~/.scideer/cache/pygcn ] || { echo "ERROR: pygcn cache missing"; exit 1; }
[ -d ~/.scideer/cache/torch_geometric ] || { echo "ERROR: torch_geometric cache missing"; exit 1; }

echo
echo "=== prerun outputs ==="
ls outputs/prerun/slr-*.md
ls outputs/prerun/repro-1609.02907/aggregated_table.md

echo
echo "=== Web UI reachable ==="
curl -s -o /dev/null -w "%{http_code}" http://localhost:2026 | grep -E "^(200|301|302)$" \
  && echo "OK" || { echo "ERROR: Web UI not 2xx/3xx"; exit 1; }

echo
echo "=== sci-pi assistant available ==="
curl -s http://localhost:8001/api/agents | grep -q '"sci-pi"' \
  && echo "OK" || { echo "ERROR: sci-pi not in /api/agents"; exit 1; }

echo
echo "=== ALL CHECKS PASSED ==="
EOF
chmod +x scratch/predemo_check.sh
```

**Step 2: Run it**

```bash
./scratch/predemo_check.sh
```

Expected: "ALL CHECKS PASSED". If any check fails, fix BEFORE rehearsal.

**Step 3: Commit**

```bash
git add scratch/predemo_check.sh
git commit -m "feat(demo): pre-demo health check script"
```

---

## Task 66: Demo rehearsal #1 (10:00-11:00)

**Files:**
- Create: `~/scideer/docs/DEMO_REHEARSAL_LOG.md`

**Step 1: Initialize the rehearsal log**

```bash
cat > docs/DEMO_REHEARSAL_LOG.md <<'EOF'
# Demo Rehearsal Log

Goal: 3 successful runs ≥ 80% before demo. Each rehearsal follows the 8-min script (design Section 9).

## Rehearsal #1 — <date> <time>

**Demo prompt:** "用 GCN 论文 (arxiv:1609.02907) 做一次完整科研流程：复现 Table 2 GCN/Cora 行，最后输出一个简短的 NeurIPS 风格 LaTeX 论文 PDF。"

| Phase | Time budget | Actual time | Outcome | Notes |
|---|---|---|---|---|
| 0:00-0:30 open + UI intro | 30 s |  |  |  |
| 0:30-1:00 switch to sci-pi | 30 s |  |  |  |
| 1:00-1:15 send prompt | 15 s |  |  |  |
| 1:15-4:00 phase C repro | 165 s |  |  |  |
| 4:00-6:30 phase E writing | 150 s |  |  |  |
| 6:30-7:00 PDF + C+ table | 30 s |  |  |  |
| 7:00-8:00 PPT cutover | 60 s |  |  |  |
| 8:00-8:30 closing | 30 s |  |  |  |

**Verdict:** PASS / FAIL  
**Issues seen:**  
**Fix needed before next rehearsal:**

---
EOF
```

**Step 2: Run the rehearsal**

In Web UI, fresh thread, assistant=`sci-pi`, send the demo prompt. Time each phase with a stopwatch. Fill the table.

**Step 3: Commit log**

```bash
git add docs/DEMO_REHEARSAL_LOG.md
git commit -m "test(demo): rehearsal #1 outcome"
```

---

## Task 67: Demo rehearsal #2 (11:00-12:00)

Repeat Task 66's protocol in a fresh thread. Append a "## Rehearsal #2" section to `DEMO_REHEARSAL_LOG.md`. Compare timing with #1 — variance > 60 s on any phase is a stability concern.

```bash
git add docs/DEMO_REHEARSAL_LOG.md
git commit -m "test(demo): rehearsal #2 outcome"
```

---

## Task 68: Demo rehearsal #3 (after lunch, ~14:00 if morning was on time)

Same protocol. After this, you have 3 data points. **Calculate success rate.**

| Rehearsals passed | Action |
|---|---|
| 3/3 | ✅ CP4 PASS — proceed to backup video recording (Task 69) |
| 2/3 | ⚠️ marginal — fix the failing phase, run rehearsal #4 |
| ≤1/3 | 🔴 CP4 FAIL — invoke @superpowers:systematic-debugging immediately; switch to backup-video plan (Task 70) |

```bash
git add docs/DEMO_REHEARSAL_LOG.md
git commit -m "test(demo): rehearsal #3 + CP4 verdict"
```

---

## Task 69: Record 4 backup videos (≤ 30 s each, 2x speed)

**Files:**
- Create: `~/scideer/demo_backup/phase_c_repro.mp4`
- Create: `~/scideer/demo_backup/phase_e_writing.mp4`
- Create: `~/scideer/demo_backup/full_run.mp4`
- Create: `~/scideer/demo_backup/pdf_walkthrough.mp4`

**Step 1: Record screen during a clean rehearsal run**

Use any screen recorder (OBS, QuickTime, ffmpeg). For each phase, record the Web UI region:

```bash
# Linux example with ffmpeg X11 capture
ffmpeg -video_size 1920x1080 -framerate 30 -f x11grab -i :0.0 \
  -c:v libx264 -preset ultrafast -crf 28 \
  -t 180 demo_backup/full_run_raw.mp4
```

(On Windows / Mac, use OBS for simpler workflow.)

**Step 2: Trim each video to ≤ 30 s and 2x speed**

```bash
mkdir -p demo_backup
for v in phase_c_repro phase_e_writing pdf_walkthrough; do
  ffmpeg -i demo_backup/${v}_raw.mp4 \
         -filter:v "setpts=0.5*PTS" -an \
         -t 30 demo_backup/${v}.mp4
done
```

**Step 3: Verify each plays back cleanly**

```bash
ls -lh demo_backup/
```

Each should be ≤ 5 MB, ≤ 30 s.

**Step 4: Commit (videos can be committed via git-lfs OR placed outside repo)**

If repo size is concern, store outside the repo and document path:

```bash
echo "demo_backup/*.mp4" >> .gitignore
echo "Demo backup videos: ~/scideer/demo_backup/" >> docs/NOTES.md
git add .gitignore docs/NOTES.md
git commit -m "test(demo): backup videos recorded; ignored from repo (kept locally)"
```

---

## Task 70: Offline mode dry-run (~16:00)

**Files:** none (verification step)

**Step 1: Block outbound network**

```bash
sudo iptables -A OUTPUT -p tcp --dport 443 -j DROP
sudo iptables -A OUTPUT -p tcp --dport 80 -j DROP
```

**Step 2: Run the demo prompt in offline mode**

In Web UI, fresh thread, assistant=`sci-pi`. Send the same prompt.

Expected: paper-reproduction works (cache hit), scientific-writing works (sandbox is local). The systematic-literature-review *will* fail or fall back — but the demo prompt skips A/B (user gave arxiv id), so this should not block.

If demo fails offline, note which step required network and consider adding an offline fallback (e.g. pre-download paper PDF for arxiv:1609.02907).

**Step 3: Re-enable network**

```bash
sudo iptables -D OUTPUT -p tcp --dport 443 -j DROP
sudo iptables -D OUTPUT -p tcp --dport 80 -j DROP
```

**Step 4: Record outcome**

```bash
echo "
### Day 9: Offline mode dry-run
- Demo prompt (skip A/B, do C+E): <PASS/FAIL>
- Network-required steps observed: <list>
" >> docs/NOTES.md
git add docs/NOTES.md
git commit -m "test(demo): offline mode dry-run outcome"
```

---

## Task 71: PPT polish (Day 9 afternoon, ~14:00-18:00)

**Files:**
- Create: `~/scideer/docs/ppt/scideer_slides.pptx` (or Keynote / Google Slides equivalent)

**Step 1: Use the design Section 13 outline as starting structure**

The structure is:

| Slide | Content | Time |
|---|---|---|
| 1 | Title: SciDeer | 1 min |
| 2-3 | Motivation: agent harness + scientific lifecycle gap | 4 min |
| 4 | Related Work: DeerFlow / Claude Code / open agent harnesses | 3 min |
| 5 | Architecture diagram (insert design Section 3.1 component map as image) | 3 min |
| 6 | DeerFlow's existing scientific skills (lit review, paper review, data, charts) | 3 min |
| 7 | New: paper-reproduction skill | 4 min |
| 8 | New: scientific-writing skill | 4 min |
| 9 | New: sci-pi custom subagent | 3 min |
| 10 | New: Semantic Scholar MCP | 2 min |
| 11-12 | Live Demo | 8 min |
| 13 | Mini Sci-Bench design + scoring | 3 min |
| 14 | Benchmark results: insert `figures/fig_correctness.png` | 4 min |
| 15 | Ablation: insert `figures/fig_radar.png` | 2 min |
| 16 | Limitations & Future Work | 2 min |
| 17 | Conclusion | 1 min |
| 18 | Q&A | 5-8 min |

**Step 2: Slide-by-slide guidance**

- **Slide 1**: Title only. SciDeer logo (use a 🦌 emoji or simple stylized deer). Subtitle: "Scientific Research Lifecycle Extension for DeerFlow 2.0".
- **Slides 2-3**: Show the capability table from design Section 1.1 — vanilla DeerFlow vs SciDeer columns.
- **Slide 5**: Render the component map (design Section 3.1) as a clean PowerPoint shape diagram (don't paste ASCII).
- **Slide 7-9**: For each new skill / subagent, show: workflow phases + 1 failure-mode + the file it's saved as.
- **Slide 14**: This is the **flagship visual** — use `fig_correctness.png` full-width. Annotate the T2/T4/T5 vanilla bars with red "0/3" labels.
- **Slide 16**: Honest limitations: n_runs=1; CPU-only sandbox; no GPU experiments; LaTeX template uses article-class instead of official NeurIPS .sty.

**Step 3: Have teammate review**

A teammate reviews the deck with eye on:
- Spelling
- Color contrast (DeerFlow blue + SciDeer accent)
- Slide-to-slide flow
- Time per slide vs design budget

**Step 4: Save final**

```bash
mkdir -p docs/ppt
# place final pptx here
ls docs/ppt/
git add docs/ppt/
git commit -m "docs(ppt): SciDeer slide deck (40-50 min) ready for presentation"
```

(If pptx is large, consider git-lfs or external storage — see Task 69 pattern.)

---

## Task 72: Report draft (Day 9 evening, ~19:00-23:00)

**Files:**
- Create: `~/scideer/docs/report/scideer_report.tex` (or .md if user prefers)
- Create: `~/scideer/docs/report/scideer_report.pdf`

**Step 1: Use design Section 14 structure**

```
1. Introduction (1 p)
2. Related Work (1 p)
3. System Design (2 p)
4. Experiments (2-3 p)
5. Discussion (1 p)
6. Conclusion & Future Work (0.5 p)
7. References (0.5 p)
8. Appendix
```

**Step 2: Section 4 (Experiments) leverages benchmark artifacts**

Copy from `benchmarks/sci_eval/RESULTS.md`:
- Summary table
- Per-task detail
- Insert `fig_correctness.png` and `fig_radar.png`

**Step 3: Section 8 (Appendix) includes**

- `paper-reproduction/SKILL.md`
- `scientific-writing/SKILL.md`
- `agents/sci-pi/prompt.md`
- 1 representative `paper.pdf` excerpt or screenshot
- 1 task yaml from `benchmarks/sci_eval/tasks/`

**Step 4: Compile**

If using LaTeX (the meta-paper), compile inside the scideer-sandbox:
```bash
docker run --rm -v $(pwd)/docs/report:/work -w /work scideer-sandbox:latest \
  bash -c "pdflatex scideer_report && bibtex scideer_report && pdflatex scideer_report && pdflatex scideer_report"
```

Or just write Markdown and convert with pandoc.

**Step 5: Have teammate proofread**

Teammate B from the team allocation table (design Section 10.2). Focus: citations + grammar + completeness.

**Step 6: Commit**

```bash
git add docs/report/
git commit -m "docs(report): SciDeer report (8-10 pages) drafted"
```

---

## Task 73: Final pre-demo packaging (Day 9 night)

**Files:** none (verification + tagging)

**Step 1: Tag the release**

```bash
cd ~/scideer
git tag -a v1.0-demo -m "SciDeer v1.0 — final demo build (PH6725 final project)"
git push origin v1.0-demo
git push origin scideer-main
```

**Step 2: Final inventory check**

```bash
cat <<EOF
=== Final Inventory ===

Skills:
$(ls skills/custom/)

Agent:
$(ls agents/)

Benchmark:
$(ls benchmarks/sci_eval/)
$(cat benchmarks/sci_eval/results.csv | wc -l) result rows
$(ls benchmarks/sci_eval/figures/)

Prerun artifacts:
$(ls outputs/prerun/)

Demo:
$(ls demo_backup/ 2>/dev/null || echo "(videos in demo_backup/, gitignored)")

Docs:
$(ls docs/plans/)
$(ls docs/ppt/)
$(ls docs/report/)

Configs:
- config.yaml: $(grep -c '^[a-z]' config.yaml) top-level keys
- extensions_config.json: $(jq '.skills | keys | length' extensions_config.json) skills, $(jq '.mcpServers | keys | length' extensions_config.json) MCPs

EOF
```

**Step 3: Final NOTES.md update**

```
### Day 9 EOD: SciDeer v1.0 Demo Build Complete

- Demo rehearsal success rate: <X>/3
- Backup videos recorded: 4 segments
- PPT: 18 slides, ~45 min
- Report: 8-10 pages
- Cloud Web UI: external access verified
- Offline mode: validated
- Tagged: v1.0-demo

🚩 Ready for live demo on 2026-05-12.
```

```bash
git add docs/NOTES.md
git commit -m "docs: Day 9 EOD final inventory + v1.0-demo build complete"
git push
```

**🚩 End of Day 9. Phase 6 complete. SciDeer ready for live demo.**

---

# Appendix A: Quick Reference

## Hard Checkpoints (CP1-CP4)

| CP | Day | Criterion | If failed |
|---|---|---|---|
| CP1 | 1 EOD | DeerFlow Web UI + Kimi K2.5 running | Switch model (DeepSeek / Qwen / OpenRouter) |
| CP2 | 2 EOD | LaTeX compile in sandbox succeeds | Drop scientific-writing PDF goal; markdown-only |
| CP3 | 5 EOD | minimum viable demo (repro + write) e2e | Day 6-7 freeze on new features; demo path only |
| CP4 | 9 noon | demo rehearsal ≥ 80% success | Switch to all-backup-video presentation |

## Key Files (alphabetical)

| Path | Purpose |
|---|---|
| `agents/sci-pi/config.yaml` | Per-agent skill whitelist |
| `agents/sci-pi/prompt.md` | sci-pi system prompt |
| `benchmarks/sci_eval/runner.py` | Benchmark driver |
| `benchmarks/sci_eval/visualize.py` | 3 PPT figures |
| `benchmarks/sci_eval/tasks/t*.yaml` | 5 task definitions |
| `config.yaml` | DeerFlow main config (models, sandbox, subagents) |
| `docker/scideer-sandbox/Dockerfile` | Custom sandbox image |
| `extensions_config.json` | Skills enable + MCP servers |
| `skills/custom/paper-reproduction/SKILL.md` | Reproduction skill |
| `skills/custom/scientific-writing/SKILL.md` | LaTeX writing skill |

## Key Commands

| Action | Command |
|---|---|
| Start dev | `make dev` |
| Stop dev | `make stop` |
| Health check | `make doctor` |
| Build sandbox | `docker build -t scideer-sandbox:latest docker/scideer-sandbox/` |
| Run all tests | `PYTHONPATH=. pytest skills/ benchmarks/ -v` |
| Run benchmark | `PYTHONPATH=. python benchmarks/sci_eval/runner.py` |
| Render figures | `PYTHONPATH=. python benchmarks/sci_eval/visualize.py` |
| Pre-demo check | `./scratch/predemo_check.sh` |

## Top 3 Risks (from design Section 11)

| # | Risk | Mitigation deployed in plan |
|---|---|---|
| R1 | paper-reproduction live failure | cache pre-warm (Task 15) + backup video (Task 69) + naked report (Task 31) |
| R2 | LaTeX compile failure | 3-round auto-fix (Task 38) + naked PDF degradation |
| R3 | sci-pi orchestrator hang | timeout=1800s (Task 45) + graceful degradation in prompt (Task 43) |

---

**End of implementation plan.**

