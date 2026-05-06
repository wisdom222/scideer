# Libra Rebranding — Design Document

> Replace DeerFlow's user-facing visual and textual identity with Libra,
> a scientific-research-agent persona for the SciDeer / PH6725 project.
>
> Date: 2026-05-06
> Author: Jasper (with Claude Code, brainstorming skill)
> Status: Approved through brainstorming Sections 1-4 on 2026-05-06

---

## 0. Project Identity Decisions (Locked)

| Decision | Value | Reasoning |
|----------|-------|-----------|
| Project name | **Libra** | Latin "scales" — evokes weighing scientific evidence; constellation tie-in for visual identity |
| Logo concept | **Libra constellation** (4-star diamond) + center "L" + subtle starlight glow | Distinctive (no logo collision), scientific aesthetic, scales to favicon |
| Color palette | **Keep DeerFlow's existing warm minimal** (oklch warm beige, Anthropic-Claude style) | YAGNI — color change introduces accessibility/dark-mode bugs; time better spent on skill development |
| Tagline | "A scientific research agent for the full research lifecycle" | Direct, professional, mirrors design-doc selling point |
| DeerFlow attribution in UI | **None** — only in README + Report + PPT | User chose to make Libra look like an original product in UI; honesty preserved at the documentation layer |
| Rebrand scope | **Medium (B)** — all visible frontend + README + about page; backend code/internal docs untouched | Balanced effort vs visual coherence |
| Implementation approach | **Single batch commit** (vs incremental or config-driven) | Decisions are locked; no need for incremental verification; YAGNI rules out config-driven brand abstraction |

---

## 1. Scope Boundaries (What Changes / What Doesn't)

### IN scope (must change)

**Frontend visual:**
- `frontend/public/images/deer.svg` → replaced with `libra-logo.svg`
- `frontend/public/favicon.ico` → regenerated from new logo
- `frontend/public/images/libra-mark.svg` (new — header version)
- `frontend/public/favicon.svg` (new — minimal version)

**Frontend text strings:**
- `frontend/src/app/layout.tsx` (browser title, OG metadata)
- `frontend/src/components/workspace/workspace-header.tsx` (top-bar text)
- `frontend/src/app/(auth)/login/page.tsx` (login page brand)
- `frontend/src/app/(auth)/setup/page.tsx` (setup page brand)
- `frontend/src/components/workspace/settings/about-content.ts` (about page)
- `frontend/src/components/landing/*` (10 landing components — full marketing copy)

**Documentation:**
- `README.md` (rewrite for Libra)
- `README_zh.md` (Chinese rewrite)
- `backend/README.md` (developer docs)

### OUT of scope (intentionally untouched)

- `backend/packages/harness/deerflow/...` — Python package names; renaming would break imports without functional benefit
- `config.example.yaml` — example comments referencing deerflow models stay
- `backend/docs/*.md` — internal technical documentation
- `.github/`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` — project meta
- All `*.py` source files

Rationale: users never see these. Keeping internal code identifiers stable preserves upstream-merge compatibility for future DeerFlow releases.

---

## 2. Logo Specification

### 2.1 Astronomy Reference

The Libra constellation is anchored by 4 stars forming a diamond:

- **α Lib** (Zubenelgenubi, "south claw") — left
- **β Lib** (Zubeneschamali, "north claw") — top, brightest
- **γ Lib** (Zubenelhakrabi) — right
- **σ Lib** — bottom

### 2.2 Visual Layers (outside-in)

```
1. 4 Libra main stars in diamond layout
   - Each star rendered as filled circle
   - β Lib slightly larger (it's the brightest in real Libra)
   - SVG <filter> with feGaussianBlur stdDeviation=1.5 for soft halo glow
   - Glow radius ≈ 1.5x star diameter

2. 4 thin connecting lines forming the diamond
   - opacity 0.6 — present but secondary

3. Center letter "L"
   - Serif typeface (Times / Georgia family) — academic gravitas
   - Size: ~40% of diamond inner space
   - Color: same as stars but opacity 0.85 — visible but not dominant
```

### 2.3 ASCII Concept

```
          ✦ β
         /╱│╲╲
        /╱ │ ╲╲
   ✦ α─╱  L  ╲─✦ γ
        ╲╲│╱╱
         ╲╲│╱╱
          ✦ σ
```

### 2.4 Size Variants

| Variant | File | Used At | Elements Included |
|---------|------|---------|-------------------|
| Detailed | `libra-logo.svg` | hero, login (≥80px) | 4 stars + glow + connections + L |
| Standard | `libra-mark.svg` | header (24-32px) | 4 stars + L (no glow, no connections) |
| Minimal | `favicon.svg` | tab icon (16-32px) | 4 stars + L (very simplified) |
| Legacy | `favicon.ico` | older browsers | converted from minimal |

### 2.5 Theme Adaptation

Use `currentColor` so a single SVG handles both modes:

- **Light mode**: black stars + black L (visible on warm beige bg)
- **Dark mode**: white stars + white L (visible on dark warm gray bg)
- **Glow filter**: tinted to match foreground color, alpha-blended

No separate light/dark SVG files needed.

---

## 3. Text Replacement Catalog

### 3.1 Browser / System Metadata

| Location | Original | Replacement |
|----------|----------|-------------|
| Tab title | `DeerFlow` | `Libra` |
| Title suffix | `... \| DeerFlow` | `... \| Libra` |
| OG title | `DeerFlow` | `Libra — Scientific Research Agent` |
| OG description | (DeerFlow original) | `An AI agent for the scientific research lifecycle.` |

### 3.2 Workspace UI

| Location | Original | Replacement |
|----------|----------|-------------|
| Header brand text | `DeerFlow` | `Libra` |
| Loading state | `Loading DeerFlow...` | `Loading Libra...` |
| Empty welcome | (DeerFlow text) | `Welcome to Libra. What would you like to research today?` |

### 3.3 Login / Setup

| Location | Replacement |
|----------|-------------|
| Login page H1 | `Sign in to Libra` |
| Login subtitle | `A scientific research agent for the full research lifecycle` |
| Setup page H1 | `Set up your Libra workspace` |
| Setup intro | `Configure your model, tools, and workspace to start researching with Libra.` |

### 3.4 Landing Page (10 components)

| Component | Replacement |
|-----------|-------------|
| Hero H1 | `Libra` |
| Hero subtitle | `A scientific research agent for the full research lifecycle — from literature review to publication-ready papers.` |
| Hero CTA | `Start Researching` |
| Features section H2 | `What Libra Can Do` |
| Skills section H2 | `Built-in Research Skills` |
| Sandbox section H2 | `Reproducible Experiments in Isolated Sandboxes` |
| Footer copyright | `© 2026 Libra Project` |

### 3.5 About Page (`about-content.ts`)

```text
Libra is a scientific research agent that helps you navigate the full
research lifecycle: surveying literature, reproducing papers, designing
experiments, and writing up results.

Capabilities:
- Systematic literature review with arXiv integration
- Paper reproduction with sandboxed experiment execution
- Experiment design and data analysis with auto-generated visualizations
- LaTeX paper generation with bibliography management
- Cross-database citation graph analysis (Semantic Scholar)

Built for researchers, students, and scientists who want to focus on
ideas while delegating mechanical research workflow to an AI agent.
```

### 3.6 README.md (full rewrite)

```markdown
# Libra — Scientific Research Agent

> A research-lifecycle AI agent for surveying literature, reproducing
> papers, designing experiments, and writing publication-ready papers.

## Features
- Systematic literature review with arXiv search
- Paper reproduction with auto scale-down and sandbox execution
- Experiment design and data analysis with publication-quality figures
- LaTeX paper generation with bibliography compilation
- Cross-database citation graph analysis (Semantic Scholar)
- End-to-end research lifecycle orchestration via the sci-pi subagent

## Quick Start
[install + run instructions]

## Architecture
See docs/plans/2026-05-03-scideer-design.md for the full architecture.

## Acknowledgments
This project extends DeerFlow 2.0 (https://github.com/bytedance/deer-flow)
by ByteDance, adding:
- Two new skills (paper-reproduction, scientific-writing)
- A custom orchestrator subagent (sci-pi)
- Semantic Scholar MCP integration
- A mini sci-bench evaluation layer

## License
(Original DeerFlow license retained)
```

The **Acknowledgments** section is the academic-honesty anchor for this rebrand.

---

## 4. Implementation Order

```
Step 1: Asset creation
  ├─ Write libra-logo.svg (detailed)
  ├─ Write libra-mark.svg (header)
  ├─ Write favicon.svg (minimal)
  └─ Generate favicon.ico from minimal SVG

Step 2: Replace logo references
  ├─ Drop new SVGs into frontend/public/images/
  ├─ Replace favicon.ico in frontend/public/
  ├─ Update SVG src paths in components:
  │   ├─ workspace-header.tsx
  │   ├─ login/page.tsx
  │   ├─ setup/page.tsx
  │   └─ landing/hero.tsx
  └─ Verify all references point to new files

Step 3: Replace text strings (~15 files)
  ├─ frontend/src/app/layout.tsx
  ├─ frontend/src/components/workspace/* (header + about)
  ├─ frontend/src/components/landing/* (10 files)
  └─ frontend/src/app/(auth)/* (login + setup)

Step 4: Rewrite README docs
  ├─ README.md (English)
  ├─ README_zh.md (Chinese)
  └─ backend/README.md (developer-facing)

Step 5: Single commit + push to scideer-main
```

---

## 5. Verification Plan

### 5.1 Server Deploy

```bash
ssh ubuntu@43.156.100.148
cd ~/scideer
git pull origin scideer-main
bash scripts/serve.sh --restart --dev --daemon
```

### 5.2 Browser Smoke Test (hard-refresh `Ctrl+Shift+R` first)

- [ ] Browser tab title shows `Libra`
- [ ] Favicon is the Libra constellation (not deer)
- [ ] Workspace top bar shows Libra logo + text
- [ ] Login page shows Libra logo
- [ ] Landing page hero says `Libra`
- [ ] About page text matches Section 3.5
- [ ] No `DeerFlow` text appears anywhere in the UI
- [ ] Sending a message still gets a normal response (functionality unchanged)

### 5.3 Final Audit

```bash
# After verification, sanity-check no DeerFlow strings leaked into user-facing files
cd ~/scideer/frontend/src
grep -ri "DeerFlow\|deerflow" --include="*.tsx" --include="*.ts" 2>&1 | grep -v "deerflow\." | head -20
# Anything found here is a missed string and must be patched
```

---

## 6. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|------------|
| Browser/CDN cache shows old favicon | High | Low | Hard refresh; `?v=2` cache-bust suffix on icon URL |
| SVG renders inconsistently across browsers | Low | Medium | Test Chrome/Firefox/Safari before demo |
| Missed string in some component | Medium | Low | Final `grep` audit per Section 5.3 |
| Frontend hot-reload glitch | Low | Low | `serve.sh --restart --dev --daemon` |
| Lost in next DeerFlow upstream merge | Medium | Low (we're not pulling upstream) | Document changes in commit; can re-apply if needed |

---

## 7. Time Estimate

| Phase | Time |
|-------|------|
| SVG asset creation | 30 min |
| String replacement (15 files) | 60 min |
| README rewrite (3 files) | 30 min |
| Server deploy + smoke test | 15 min |
| **Total** | **~2 hours** |

This rebranding is an isolated track that can run in parallel with skill development (`paper-reproduction`, `scientific-writing`, etc.) since the file paths don't overlap with any of those tracks.

---

## 8. Out-of-Scope (Future Considerations)

If we later want to deepen the rebrand (post-demo):

- Backend Python package rename (`deerflow.*` → `libra.*`) — large refactor
- Internal log message strings
- Configuration field renaming (`deerflow_*` env vars)
- A custom favicon animation (subtle pulse on the brightest star)
- Per-language i18n support beyond English/Chinese

These are deliberately deferred. YAGNI for the May 12 deadline.
