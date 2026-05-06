# Libra Rebranding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace DeerFlow's user-facing visual and textual identity with "Libra" — a Libra-constellation logo + center "L" + soft glow — across the frontend Web UI, About page, and project README, while keeping the existing warm minimal color palette and all backend code untouched.

**Architecture:** Single-batch rebrand. Each task is one file (or one SVG asset) with exact line-number replacements. Verification is visual (browser smoke test) since no unit tests exist for branding strings. The whole rebrand lives on branch `scideer-main` and ships as one logical commit per task family (assets / strings / readme), pushed to GitHub for the user to pull on the Tencent Cloud server.

**Tech Stack:** Next.js 15 (frontend), Tailwind CSS, SVG (vector graphics), Markdown (README). All edits are static file changes — no Python, no rebuild scripts.

---

## Pre-flight Check

**Before starting, verify:**

```bash
cd D:/6725_GroupProject/scideer
git branch --show-current
# Expected output: scideer-main

git status
# Expected: clean working tree (or only the untracked design docs)

git pull origin scideer-main
# Expected: Already up to date
```

If anything looks off, stop and report.

---

## Task 1: Create Libra Logo SVG (detailed version)

**Files:**
- Create: `frontend/public/images/libra-logo.svg`

**Step 1: Write the SVG**

Save the following content to `frontend/public/images/libra-logo.svg`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" fill="none" stroke="currentColor">
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Connecting lines (the diamond) -->
  <g stroke="currentColor" stroke-width="1" opacity="0.45">
    <line x1="100" y1="40"  x2="40"  y2="100"/>
    <line x1="100" y1="40"  x2="160" y2="100"/>
    <line x1="40"  y1="100" x2="100" y2="160"/>
    <line x1="160" y1="100" x2="100" y2="160"/>
  </g>

  <!-- 4 stars (β top brightest, others equal) with soft glow -->
  <g fill="currentColor" filter="url(#glow)">
    <circle cx="100" cy="40"  r="6"/>          <!-- β Lib (brightest) -->
    <circle cx="40"  cy="100" r="4.5"/>        <!-- α Lib -->
    <circle cx="160" cy="100" r="4.5"/>        <!-- γ Lib -->
    <circle cx="100" cy="160" r="4.5"/>        <!-- σ Lib -->
  </g>

  <!-- Center letter L (serif) -->
  <text x="100" y="115"
        text-anchor="middle"
        font-family="Georgia, 'Times New Roman', serif"
        font-size="48"
        font-weight="500"
        fill="currentColor"
        opacity="0.85">L</text>
</svg>
```

**Step 2: Verify the SVG file is well-formed**

```bash
cd D:/6725_GroupProject/scideer
python -c "import xml.etree.ElementTree as ET; ET.parse('frontend/public/images/libra-logo.svg'); print('OK')"
```

Expected output: `OK`

**Step 3: Visually preview**

Open the file in a browser:
- File path (Windows): `D:/6725_GroupProject/scideer/frontend/public/images/libra-logo.svg`
- Drag into a Chrome tab. Should show a black diamond constellation with center "L".

---

## Task 2: Create Libra Mark SVG (header version, no glow/lines)

**Files:**
- Create: `frontend/public/images/libra-mark.svg`

**Step 1: Write the simplified SVG**

Save to `frontend/public/images/libra-mark.svg`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <!-- 4 stars only, no glow, no connections -->
  <g fill="currentColor">
    <circle cx="100" cy="40"  r="8"/>
    <circle cx="40"  cy="100" r="6"/>
    <circle cx="160" cy="100" r="6"/>
    <circle cx="100" cy="160" r="6"/>
  </g>

  <!-- Center L -->
  <text x="100" y="118"
        text-anchor="middle"
        font-family="Georgia, 'Times New Roman', serif"
        font-size="56"
        font-weight="500"
        fill="currentColor">L</text>
</svg>
```

**Step 2: Verify**

```bash
python -c "import xml.etree.ElementTree as ET; ET.parse('frontend/public/images/libra-mark.svg'); print('OK')"
```

---

## Task 3: Create Favicon SVG (minimal version)

**Files:**
- Create: `frontend/public/favicon.svg`

**Step 1: Write the minimal SVG**

Save to `frontend/public/favicon.svg`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <g fill="currentColor">
    <circle cx="16" cy="6"  r="2"/>
    <circle cx="6"  cy="16" r="1.5"/>
    <circle cx="26" cy="16" r="1.5"/>
    <circle cx="16" cy="26" r="1.5"/>
  </g>
  <text x="16" y="20"
        text-anchor="middle"
        font-family="Georgia, serif"
        font-size="13"
        font-weight="600"
        fill="currentColor">L</text>
</svg>
```

**Step 2: Verify**

```bash
python -c "import xml.etree.ElementTree as ET; ET.parse('frontend/public/favicon.svg'); print('OK')"
```

---

## Task 4: Generate favicon.ico (legacy browser support)

**Files:**
- Replace: `frontend/public/favicon.ico`

**Step 1: Try Python image library route**

```bash
cd D:/6725_GroupProject/scideer
pip install cairosvg pillow 2>&1 | tail -3

python << 'PYEOF'
import cairosvg
from PIL import Image
import io

png_bytes = cairosvg.svg2png(
    url="frontend/public/favicon.svg",
    output_width=64,
    output_height=64,
)
img = Image.open(io.BytesIO(png_bytes))
img.save("frontend/public/favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
print("favicon.ico generated")
PYEOF
```

Expected: `favicon.ico generated`

**Step 2: If that fails, use online conversion fallback**

If `cairosvg` doesn't install on Windows (common because it needs Cairo native libs), the user converts manually:

1. Open `frontend/public/favicon.svg` in browser
2. Take a screenshot (or use https://favicon.io/favicon-converter/)
3. Upload the SVG, download the .ico
4. Replace `frontend/public/favicon.ico`

Tell the user explicitly if you're falling back to the online tool — they need to do this step.

**Step 3: Verify**

```bash
ls -la frontend/public/favicon.ico
# Expected: file size > 0 bytes (any size; ICO files vary)
```

---

## Task 5: Commit asset task family

**Step 1: Stage and commit**

```bash
cd D:/6725_GroupProject/scideer
git add frontend/public/images/libra-logo.svg \
        frontend/public/images/libra-mark.svg \
        frontend/public/favicon.svg \
        frontend/public/favicon.ico

git commit -m "feat(brand): add Libra constellation logo SVG assets

Add three SVG variants of the Libra logo (4-star diamond + center L)
plus regenerated favicon.ico:
- libra-logo.svg: detailed with starlight glow + connections (hero pages)
- libra-mark.svg: header version, stars + L only
- favicon.svg / favicon.ico: minimal tab-icon variant

All assets use currentColor for automatic light/dark mode adaptation."
```

**Step 2: Don't push yet — batch with the next task families.**

---

## Task 6: Update Browser Title and Metadata

**Files:**
- Modify: `frontend/src/app/layout.tsx:10-13`

**Step 1: Read current state**

The current file has:

```typescript
export const metadata: Metadata = {
  title: "DeerFlow",
  description: "A LangChain-based framework for building super agents.",
};
```

**Step 2: Replace with Libra metadata**

Edit `frontend/src/app/layout.tsx` lines 10-13:

```typescript
export const metadata: Metadata = {
  title: "Libra",
  description: "A scientific research agent for the full research lifecycle.",
};
```

**Step 3: Verify the file parses**

```bash
cd D:/6725_GroupProject/scideer/frontend
npx tsc --noEmit src/app/layout.tsx 2>&1 | head -10
```

Expected: no errors (or only unrelated type errors from imports). If new errors mention `layout.tsx`, the edit broke syntax — fix and retry.

---

## Task 7: Update Workspace Header Brand Text

**Files:**
- Modify: `frontend/src/components/workspace/workspace-header.tsx:32-46`

**Step 1: Update collapsed-state initials (line 32-34)**

Original:
```tsx
<div className="text-primary block pt-1 font-serif group-hover/workspace-header:hidden">
  DF
</div>
```

Replace `DF` with `L`:
```tsx
<div className="text-primary block pt-1 font-serif group-hover/workspace-header:hidden">
  L
</div>
```

**Step 2: Update expanded-state brand text (lines 40-46)**

Original:
```tsx
{env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ? (
  <Link href="/" className="text-primary ml-2 font-serif">
    DeerFlow
  </Link>
) : (
  <div className="text-primary ml-2 cursor-default font-serif">
    DeerFlow
  </div>
)}
```

Replace both `DeerFlow` strings with `Libra`:

```tsx
{env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ? (
  <Link href="/" className="text-primary ml-2 font-serif">
    Libra
  </Link>
) : (
  <div className="text-primary ml-2 cursor-default font-serif">
    Libra
  </div>
)}
```

**Step 3: Verify no DeerFlow strings remain in this file**

```bash
cd D:/6725_GroupProject/scideer
grep -n "DeerFlow\|^DF$" frontend/src/components/workspace/workspace-header.tsx
```

Expected: no output (file clean of brand strings).

---

## Task 8: Update Login Page Brand

**Files:**
- Modify: `frontend/src/app/(auth)/login/page.tsx:135,144`

**Step 1: Replace the SVG mask URL (line 135)**

Original:
```tsx
className="absolute inset-0 z-0 mask-[url(/images/deer.svg)] mask-size-[100vw] mask-center mask-no-repeat md:mask-size-[72vh]"
```

Replace `mask-[url(/images/deer.svg)]` with `mask-[url(/images/libra-logo.svg)]`:

```tsx
className="absolute inset-0 z-0 mask-[url(/images/libra-logo.svg)] mask-size-[100vw] mask-center mask-no-repeat md:mask-size-[72vh]"
```

**Step 2: Replace the brand title (line 144)**

Original:
```tsx
<h1 className="text-foreground font-serif text-3xl">DeerFlow</h1>
```

Replace with:
```tsx
<h1 className="text-foreground font-serif text-3xl">Libra</h1>
```

**Step 3: Verify**

```bash
grep -n "DeerFlow\|deer\.svg" frontend/src/app/\(auth\)/login/page.tsx
# Expected: no output
```

---

## Task 9: Update Setup Page Brand

**Files:**
- Modify: `frontend/src/app/(auth)/setup/page.tsx:160,169,231,240`

**Step 1: Replace SVG mask URL (line 160)**

Same as login — replace `/images/deer.svg` with `/images/libra-logo.svg`.

**Step 2: Replace H1 brand text (line 169)**

Original (init_admin form):
```tsx
<h1 className="font-serif text-3xl">DeerFlow</h1>
```

Replace with:
```tsx
<h1 className="font-serif text-3xl">Libra</h1>
```

**Step 3: Replace second SVG mask URL (line 231)**

Same as Step 1 — same file, second occurrence.

**Step 4: Replace second H1 (line 240)**

Original (change-password form):
```tsx
<h1 className="font-serif text-3xl">DeerFlow</h1>
```

Replace with:
```tsx
<h1 className="font-serif text-3xl">Libra</h1>
```

**Step 5: Verify**

```bash
grep -n "DeerFlow\|deer\.svg" frontend/src/app/\(auth\)/setup/page.tsx
# Expected: no output
```

---

## Task 10: Update Landing Hero

**Files:**
- Modify: `frontend/src/components/landing/hero.tsx:32,58,72-80,83`

**Step 1: Replace SVG mask URL (line 32)**

Replace `/images/deer.svg` with `/images/libra-logo.svg`.

**Step 2: Replace `with DeerFlow` text (line 58)**

Original:
```tsx
<div>with DeerFlow</div>
```

Replace with:
```tsx
<div>with Libra</div>
```

**Step 3: Replace the long subtitle paragraph (lines 72-80)**

Original:
```tsx
<p className="text-muted-foreground mt-8 scale-105 text-center text-2xl text-shadow-sm">
  An open-source SuperAgent harness that researches, codes, and creates.
  With
  <br />
  the help of sandboxes, memories, tools, skills and subagents, it
  handles
  <br />
  different levels of tasks that could take minutes to hours.
</p>
```

Replace with:
```tsx
<p className="text-muted-foreground mt-8 scale-105 text-center text-2xl text-shadow-sm">
  A scientific research agent for the full research lifecycle.
  <br />
  Survey literature, reproduce papers, design experiments,
  <br />
  and write publication-ready papers — all in one workspace.
</p>
```

**Step 4: Replace the CTA button text (line 83)**

Original:
```tsx
<span className="text-md">Get Started with 2.0</span>
```

Replace with:
```tsx
<span className="text-md">Start Researching</span>
```

**Step 5: Update the WordRotate words (lines 42-56) — optional but recommended**

The current word rotation doesn't fit Libra's research focus. Replace lines 42-56:

Original:
```tsx
<WordRotate
  words={[
    "Deep Research",
    "Collect Data",
    "Analyze Data",
    "Generate Webpages",
    "Vibe Coding",
    "Generate Slides",
    "Generate Images",
    "Generate Podcasts",
    "Generate Videos",
    "Generate Songs",
    "Organize Emails",
    "Do Anything",
    "Learn Anything",
  ]}
/>{" "}
```

Replace with:
```tsx
<WordRotate
  words={[
    "Survey Literature",
    "Reproduce Papers",
    "Design Experiments",
    "Visualize Data",
    "Write LaTeX Papers",
    "Build Citation Graphs",
    "Discover Research",
  ]}
/>{" "}
```

**Step 6: Verify**

```bash
grep -n "DeerFlow\|deer\.svg" frontend/src/components/landing/hero.tsx
# Expected: no output
```

---

## Task 11: Update Landing Header & Footer

**Files:**
- Modify: `frontend/src/components/landing/header.tsx:34`
- Modify: `frontend/src/components/landing/footer.tsx:26`

**Step 1: Update header (line 34)**

Original:
```tsx
<h1 className="font-serif text-xl">DeerFlow</h1>
```

Replace with:
```tsx
<h1 className="font-serif text-xl">Libra</h1>
```

**Step 2: Update footer (line 26)**

Original:
```tsx
<p>&copy; {year} DeerFlow</p>
```

Replace with:
```tsx
<p>&copy; {year} Libra Project</p>
```

**Step 3: Verify**

```bash
grep -n "DeerFlow" frontend/src/components/landing/header.tsx frontend/src/components/landing/footer.tsx
# Expected: no output
```

---

## Task 12: Update Landing Section Components

**Files:**
- Modify: `frontend/src/components/landing/sections/case-study-section.tsx:52`
- Modify: `frontend/src/components/landing/sections/community-section.tsx:19`
- Modify: `frontend/src/components/landing/sections/sandbox-section.tsx:18`
- Modify: `frontend/src/components/landing/sections/skills-section.tsx:18`
- Modify: `frontend/src/components/landing/sections/whats-new-section.tsx:55-56`

**Step 1: case-study-section.tsx line 52**

Replace `subtitle="See how DeerFlow is used in the wild"` with `subtitle="See how Libra is used in real research workflows"`.

**Step 2: community-section.tsx line 19**

Replace `subtitle="Contribute brilliant ideas to shape the future of DeerFlow. Collaborate, innovate, and make impacts."` with `subtitle="Contribute ideas to shape the future of Libra. Collaborate on better research workflows."`.

**Step 3: sandbox-section.tsx line 18**

Original:
```
We give DeerFlow a &quot;computer&quot;, which can execute commands,
```

Replace with:
```
Libra runs experiments in isolated sandboxes, so reproductions stay
```

(Adjust the surrounding sentence if needed for grammar — read 3 lines before and 3 after to match the prose style.)

**Step 4: skills-section.tsx line 18**

Original:
```
Extend DeerFlow with your own skill files, or use our built-in
```

Replace with:
```
Extend Libra with your own skill files, or use our built-in
```

**Step 5: whats-new-section.tsx lines 55-56**

Original:
```
title="Whats New in DeerFlow 2.0"
subtitle="DeerFlow is now evolving from a Deep Research agent into a full-stack Super Agent"
```

Replace with:
```
title="What's New in Libra"
subtitle="Libra brings the full scientific research lifecycle to one agent — from arXiv search to LaTeX paper compilation."
```

**Step 6: Verify all section files**

```bash
cd D:/6725_GroupProject/scideer
grep -rn "DeerFlow" frontend/src/components/landing/sections/
# Expected: no output
```

---

## Task 13: Update Progressive Skills Animation

**Files:**
- Modify: `frontend/src/components/landing/progressive-skills-animation.tsx:464,694`

**Step 1: Line 464**

Original:
```tsx
<span className="text-sm text-zinc-400">DeerFlow Agent</span>
```

Replace with:
```tsx
<span className="text-sm text-zinc-400">Libra Agent</span>
```

**Step 2: Line 694**

Original:
```tsx
Ask DeerFlow anything...
```

Replace with:
```tsx
Ask Libra anything about your research...
```

**Step 3: Verify**

```bash
grep -n "DeerFlow" frontend/src/components/landing/progressive-skills-animation.tsx
# Expected: no output
```

---

## Task 14: Rewrite About Page Content

**Files:**
- Modify: `frontend/src/components/workspace/settings/about-content.ts` (entire file)

**Step 1: Replace the entire `aboutMarkdown` export**

Original file starts with:
```typescript
/*
 * About DeerFlow markdown content. Inlined to avoid raw-loader dependency
 * ...
 */

export const aboutMarkdown = `# 🦌 [About DeerFlow 2.0](https://github.com/bytedance/deer-flow)
...
`;
```

Replace the entire file content with:

```typescript
/*
 * About Libra markdown content. Inlined to avoid raw-loader dependency.
 */

export const aboutMarkdown = `# About Libra

Libra is a scientific research agent that helps you navigate the full research lifecycle: surveying literature, reproducing papers, designing experiments, and writing up results.

## What Libra Can Do

* **Systematic literature review** — multi-paper survey with arXiv integration and APA / IEEE / BibTeX output.
* **Paper reproduction** — generate executable code from a paper's method section, run it in a sandboxed environment, and produce a comparison report against the original.
* **Experiment design and data analysis** — design baselines, run experiments, generate publication-quality figures with matplotlib.
* **LaTeX paper generation** — write up results in NeurIPS / ICML / ACL templates and compile to PDF.
* **Cross-database citation analysis** — combine arXiv search with Semantic Scholar's citation graph for richer context.
* **End-to-end orchestration** — the \`sci-pi\` subagent chains all of the above into a single research-lifecycle workflow.

## Built For

Researchers, students, and scientists who want to focus on ideas while delegating the mechanical parts of research workflow to an AI agent.

## License

Libra is open source under the **MIT License**.
`;
```

**Step 2: Verify the file is valid TypeScript**

```bash
cd D:/6725_GroupProject/scideer/frontend
npx tsc --noEmit src/components/workspace/settings/about-content.ts 2>&1 | head -5
# Expected: no errors
```

**Step 3: Verify no DeerFlow strings remain**

```bash
grep -n "DeerFlow\|deer-flow\|deerflow" frontend/src/components/workspace/settings/about-content.ts
# Expected: no output
```

> Note: Per design Section 0, UI carries no DeerFlow attribution. Acknowledgment lives in README only.

---

## Task 15: Commit Frontend String Changes (task family)

**Step 1: Stage and commit all frontend string changes**

```bash
cd D:/6725_GroupProject/scideer
git add frontend/src/app/layout.tsx \
        frontend/src/app/\(auth\)/login/page.tsx \
        frontend/src/app/\(auth\)/setup/page.tsx \
        frontend/src/components/workspace/workspace-header.tsx \
        frontend/src/components/workspace/settings/about-content.ts \
        frontend/src/components/landing/

git commit -m "feat(brand): replace DeerFlow strings with Libra in user-facing UI

Replace all user-visible DeerFlow / DF brand strings with Libra in the
Web UI: browser metadata, workspace header, login/setup pages, landing
hero / sections / footer / progressive-skills animation, and the About
page markdown. Logo SVG references swap from deer.svg to libra-logo.svg.
Backend code, internal docs, and config examples are intentionally
untouched (per docs/plans/2026-05-06-libra-rebranding-design.md Sec 1)."
```

---

## Task 16: Rewrite README.md

**Files:**
- Modify: `README.md` (entire file)

**Step 1: Replace with Libra-focused README**

Save the following as the entire `README.md`:

```markdown
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
```

**Step 2: Verify the markdown renders**

Open `README.md` in VSCode preview or any markdown viewer. Spot-check headings render correctly.

---

## Task 17: Rewrite Chinese README

**Files:**
- Modify: `README_zh.md` (entire file)

**Step 1: Replace with the Chinese version**

Save the following as the entire `README_zh.md`:

```markdown
# Libra — 科研智能体

> 一个面向科研全生命周期的 AI 智能体：文献调研、论文复现、实验设计、学术写作。

## 功能

- **系统性文献综述** —— 集成 arXiv 搜索，输出 APA / IEEE / BibTeX 引用格式
- **论文复现** —— 自动缩放规模并在隔离沙箱中执行实验代码
- **实验设计与数据分析** —— 生成出版级可视化图表
- **LaTeX 论文生成** —— 支持 NeurIPS / ICML / ACL 模板，自动编译 PDF
- **跨数据库引文图谱分析** —— 通过 Semantic Scholar 扩展 arXiv 之外的引文数据
- **科研生命周期编排** —— 由 `sci-pi` 子智能体串联完整流程

## 快速开始

```bash
# 1. 安装依赖
make config
make install

# 2. 在 .env 配置你的 LLM API key
echo "DEEPSEEK_API_KEY=sk-..." >> .env

# 3. 启动
make dev
```

浏览器打开 `http://localhost:2026`。

## 架构设计

详见 [`docs/plans/2026-05-03-scideer-design.md`](docs/plans/2026-05-03-scideer-design.md)。

核心组件：

- **Skills** (`skills/public/`, `skills/custom/`) —— Markdown 定义的科研工作流
- **Subagents** (`agents/`) —— 专用智能体，如负责编排的 `sci-pi`
- **MCP 集成** (`extensions_config.json`) —— Semantic Scholar 等外部工具
- **Sandbox** (`docker/scideer-sandbox/`) —— 论文复现实验用的隔离容器
- **评测层** (`benchmarks/sci_eval/`) —— 用于衡量科研任务能力的 mini sci-bench

## 致谢

Libra 基于 [DeerFlow 2.0](https://github.com/bytedance/deer-flow)（字节跳动开源）扩展而来，新增了：

- 两个新 skill：`paper-reproduction`（论文复现）和 `scientific-writing`（学术写作）
- 一个自定义编排子智能体：`sci-pi`
- Semantic Scholar MCP 集成（引文图谱分析）
- 一套 mini sci-bench 评测层

DeerFlow 提供了 harness 底层基础设施（LangGraph 编排、skill 加载、subagent 调度、sandbox 提供者、MCP 客户端）。Libra 在此基础上增加了科研领域专属能力。

## 许可证

保留原 DeerFlow MIT 许可证，详见 [`LICENSE`](LICENSE)。
```

---

## Task 18: Update backend/README.md

**Files:**
- Modify: `backend/README.md`

**Step 1: Read the current file to know its structure**

```bash
head -30 backend/README.md
```

**Step 2: Add a brief Libra header at the top**

Insert at the top of `backend/README.md` (before any existing content), keeping the original DeerFlow developer docs intact below:

```markdown
# Libra Backend (extends DeerFlow 2.0 harness)

This directory contains the Libra backend, which extends DeerFlow 2.0's
harness with scientific-research-specific skills, the sci-pi orchestrator
subagent, and Semantic Scholar MCP integration. The original DeerFlow
backend documentation follows below for harness-internals reference.

---

```

Then keep all existing content as-is.

> The reason we keep the original DeerFlow backend docs intact: developers reading the backend will need to understand DeerFlow's internals (LangGraph orchestration, skill loader, etc.) to extend Libra. Hiding that lineage causes confusion.

---

## Task 19: Commit README task family

**Step 1: Stage and commit**

```bash
cd D:/6725_GroupProject/scideer
git add README.md README_zh.md backend/README.md

git commit -m "docs(brand): rewrite READMEs for Libra with DeerFlow attribution

Rewrite the project READMEs (English, Chinese, and backend developer
README) to describe Libra as a scientific research agent. Each README
includes an Acknowledgments / 致谢 section that openly cites DeerFlow
2.0 as the upstream harness — this is where the academic-honesty
attribution lives, since the design (Sec 0) keeps the UI free of
DeerFlow branding."
```

---

## Task 20: Final Audit — No DeerFlow Strings In User-Facing UI

**Step 1: Grep all touched paths**

```bash
cd D:/6725_GroupProject/scideer

echo "=== Frontend visual files ==="
grep -rni "DeerFlow\|deer\.svg" \
  frontend/src/app/layout.tsx \
  frontend/src/app/\(auth\)/ \
  frontend/src/components/workspace/ \
  frontend/src/components/landing/ \
  frontend/public/

echo "=== READMEs ==="
grep -ni "DeerFlow" README.md README_zh.md backend/README.md
# README hits are EXPECTED — they're the Acknowledgments section.
# Anything else needs investigating.
```

**Expected output:**
- Frontend section: NO results (clean)
- README section: Only the `Acknowledgments` / `致谢` mentions of DeerFlow

If anything else shows up in the frontend section, fix it before pushing.

---

## Task 21: Push to GitHub

**Step 1: Verify branch and commit log**

```bash
cd D:/6725_GroupProject/scideer
git branch --show-current
# Expected: scideer-main

git log --oneline -10
# Expected: 3 new commits at the top:
# - docs(brand): rewrite READMEs for Libra with DeerFlow attribution
# - feat(brand): replace DeerFlow strings with Libra in user-facing UI
# - feat(brand): add Libra constellation logo SVG assets
```

**Step 2: Push (this affects the remote — it's authorized for scideer-main per existing workflow)**

```bash
git push origin scideer-main
```

Expected output: `2396d3a8..<new-hash>  scideer-main -> scideer-main`

---

## Task 22: Server Deployment + Smoke Test

> **This task runs on the Tencent Cloud server, not locally.** The user executes via SSH.

**Step 1: Pull on server**

```bash
ssh ubuntu@43.156.100.148

cd ~/scideer
git pull origin scideer-main
# Expected: 3 new commits pulled in
```

**Step 2: Restart frontend (backend doesn't need restart since only frontend changed)**

```bash
cd ~/scideer
bash scripts/serve.sh --restart --dev --daemon
# Expected: services restart, "🌐 http://localhost:2026" appears in output
```

**Step 3: Browser smoke test**

Open `http://43.156.100.148:2026` in browser.

**Hard refresh first** (`Ctrl+Shift+R`) to bypass cached CSS/SVG.

Tick each item:

- [ ] Browser tab title shows `Libra`
- [ ] Favicon is the Libra constellation (4 stars + L), not deer
- [ ] Workspace top bar (left side) shows `Libra` text
- [ ] Click sidebar collapse — collapsed initial shows `L` (not `DF`)
- [ ] Logout, return to login page — page shows Libra logo and `Libra` heading
- [ ] Visit `/setup` (in private/incognito tab to bypass auth) — shows Libra heading
- [ ] Visit `/` (landing page) — hero section shows `Libra`, footer says `© 2026 Libra Project`
- [ ] In workspace, navigate to Settings → About — content matches the new aboutMarkdown
- [ ] Send a chat message ("hello") — response works normally (functionality preserved)

**Step 4: Final grep audit on server (sanity check)**

```bash
cd ~/scideer
grep -rni "DeerFlow" frontend/src/app/layout.tsx frontend/src/components/workspace/workspace-header.tsx frontend/src/app/\(auth\)/login/page.tsx
# Expected: no output (all clean)
```

---

## Task 23: Update GitHub Repo Description (optional polish)

**Step 1: Manual step on GitHub**

User opens https://github.com/wisdom222/scideer in browser:

1. Click the gear icon next to "About"
2. Change **Description** to: `Libra — A scientific research agent for the full research lifecycle. Built on DeerFlow 2.0.`
3. Optionally update topics: add `research`, `scientific-agent`, `arxiv`, `latex`, `agent-harness`
4. Save

This makes the GitHub project page itself look like Libra, not DeerFlow.

---

## Rollback Plan

If something is visibly broken after Task 22 smoke test:

```bash
# On local machine
cd D:/6725_GroupProject/scideer
git log --oneline -5
# Identify the bad commit hash

# Revert specific commit
git revert <bad-commit-hash>
git push origin scideer-main

# On server
cd ~/scideer
git pull
bash scripts/serve.sh --restart --dev --daemon
```

If the issue is just one wrong string, fix-forward instead: edit the file, commit, push, server pull.

---

## Time Budget

| Task | Estimated Time |
|------|----------------|
| Tasks 1-4 (SVG assets) | 30 min |
| Task 5 (commit) | 2 min |
| Tasks 6-14 (string replacements) | 60 min |
| Task 15 (commit) | 2 min |
| Tasks 16-18 (READMEs) | 30 min |
| Task 19 (commit) | 2 min |
| Tasks 20-21 (audit + push) | 5 min |
| Task 22 (server deploy + smoke test) | 15 min |
| Task 23 (GitHub repo description) | 3 min |
| **Total** | **~2.5 hours** |

This is one of two parallel tracks during the SciDeer May-deadline sprint. The other tracks (paper-reproduction skill, scientific-writing skill, sci-pi subagent, Semantic Scholar MCP, sci-bench, sandbox Docker image) live in disjoint file paths and can run concurrently without merge conflicts.
