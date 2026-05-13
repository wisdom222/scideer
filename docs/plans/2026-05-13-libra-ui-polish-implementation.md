# Libra UI Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the Libra constellation logo unmistakably visible on the landing hero, weave a single gold accent across the marketing surface, and replace stale ByteDance case studies with research ones — without touching the locked warm-minimal palette tokens, backend, agents, skills, or i18n strings.

**Architecture:** Six bite-sized task families that each end at a clean commit boundary. Each family is independently revertable. Frontend-only: hero composition layering, CSS tokens + keyframe animations, one new SVG asset, and four section file edits. No new components, no MagicBento internals touched.

**Tech Stack:** Next.js 16, React 19, TypeScript 5.8, Tailwind 4 (CSS variables in `globals.css`), Framer Motion via `motion/react`, `lucide-react` icons, GSAP (already in deps via MagicBento).

---

## Source Design

Everything here implements [2026-05-13-libra-ui-polish-design.md](2026-05-13-libra-ui-polish-design.md). When a code detail is ambiguous, re-read that doc — do not improvise.

## Hard Rules

1. **No git push** — every task family commits locally. Push is the user's call; the plan will stop after the final commit.
2. **No `--no-verify`** — pre-commit hooks must pass; fix root causes rather than skip.
3. **No edits outside the IN-scope file list in design §2** — if a refactor seems needed elsewhere, stop and ask.
4. **Do NOT edit `magic-bento.tsx`** — the design (§7.1, §7.2) routes around it by passing ReactNode for `label`. If you find yourself wanting to add an `icon` prop, stop.
5. **`_reference/deer-flow/` is read-only** — only edit inside `scideer/`.
6. Run `pnpm check` (lint + typecheck) at the end of each task family before committing. **No commit on failing check.**

## Working Directory

All `cd` and `pnpm` commands run from `scideer/frontend/`. All `git` commands run from `scideer/`. Use forward slashes; on Windows Git Bash is the shell (see root CLAUDE.md).

## Verification Strategy

This is a visual change — there are no meaningful unit tests for "the star pulses" or "the case-study card uses a gradient." Each task family is verified by:

1. **`pnpm typecheck`** — TypeScript compiles
2. **`pnpm lint`** — ESLint clean
3. **Build sanity** — at the very end of the plan, one `pnpm build` to confirm Next.js production build succeeds
4. **Visual smoke** — the user does the final visual verification after deploy (see design §9)

The existing Playwright e2e suite is not extended — it does not target the landing page surface.

---

## Task Family 1: Foundation (CSS tokens, keyframes, SVG asset)

**Goal:** Land the new gold tokens, `@keyframes star-twinkle`, and the constellation SVG so later tasks can simply consume them.

### Task 1A: Add gold tokens, twinkle keyframe, and `.libra-star` classes to `globals.css`

**Files:**
- Modify: `frontend/src/styles/globals.css` (append after the existing `.golden-text` block, end of `@layer base`)

**Step 1: Read the surrounding context once**

Read `frontend/src/styles/globals.css:378-392` to confirm `.golden-text` is the last class inside `@layer base` and `:root` block is at the bottom of the file.

**Step 2: Apply the edit**

Two insertions, both in `frontend/src/styles/globals.css`:

(a) Inside the **existing** `:root { ... }` block at the bottom (the one starting on line 387 with `--container-width-xs`), add four lines at the end of that block:

```css
:root {
  --container-width-xs: calc(var(--spacing) * 72);
  --container-width-sm: calc(var(--spacing) * 144);
  --container-width-md: calc(var(--spacing) * 204);
  --container-width-lg: calc(var(--spacing) * 256);
  --gold-1: #d19e1d;
  --gold-2: #e9c665;
  --gold-3: #e3a812;
  --gold-glow: rgba(233, 198, 101, 0.45);
}
```

(b) Append a new block at the very end of the file (after the last `:root` closing brace):

```css
@keyframes star-twinkle {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
    filter: drop-shadow(0 0 6px var(--gold-2));
  }
  50% {
    transform: scale(1.15);
    opacity: 0.6;
    filter: drop-shadow(0 0 14px var(--gold-2));
  }
}

.libra-star {
  transform-origin: center;
  transform-box: fill-box;
  animation: star-twinkle 2.4s ease-in-out infinite;
}
.libra-star--beta {
  animation-delay: 0s;
}
.libra-star--alpha {
  animation-delay: 0.6s;
}
.libra-star--gamma {
  animation-delay: 1.2s;
}
.libra-star--sigma {
  animation-delay: 1.8s;
}

@media (prefers-reduced-motion: reduce) {
  .libra-star {
    animation: none;
  }
}
```

**Step 3: Verify Tailwind still parses the stylesheet**

Run from `frontend/`:
```
pnpm typecheck
```
Expected: exit 0. (Typecheck doesn't parse the CSS but confirms nothing else broke; CSS parsing happens at build time. The build-time verification is at the end of the plan.)

### Task 1B: Create `libra-constellation-hero.svg`

**Files:**
- Create: `frontend/public/images/libra-constellation-hero.svg`

**Step 1: Write the file**

Exact content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" fill="none" stroke="currentColor" aria-hidden="true">
  <defs>
    <filter id="libra-star-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Diamond connectors -->
  <g stroke="currentColor" stroke-width="1" opacity="0.45">
    <line x1="100" y1="40"  x2="40"  y2="100"/>
    <line x1="100" y1="40"  x2="160" y2="100"/>
    <line x1="40"  y1="100" x2="100" y2="160"/>
    <line x1="160" y1="100" x2="100" y2="160"/>
  </g>

  <!-- 4 Libra main stars with soft halo -->
  <g fill="currentColor" filter="url(#libra-star-glow)">
    <circle class="libra-star libra-star--beta"  cx="100" cy="40"  r="7"/>
    <circle class="libra-star libra-star--alpha" cx="40"  cy="100" r="4.5"/>
    <circle class="libra-star libra-star--gamma" cx="160" cy="100" r="4.5"/>
    <circle class="libra-star libra-star--sigma" cx="100" cy="160" r="4.5"/>
  </g>

  <!-- Serif center L -->
  <text x="100" y="115"
        text-anchor="middle"
        font-family="Georgia, 'Times New Roman', serif"
        font-size="48"
        font-weight="500"
        fill="currentColor"
        opacity="0.85">L</text>
</svg>
```

Note: this SVG uses CSS class names (`libra-star`, `libra-star--*`) defined in 1A. For these classes to apply, the SVG must be inlined into the DOM — `<img src="...">` does not run page CSS against SVG internals. The hero in Task Family 2 will read the SVG and inline it, or render an equivalent inline `<svg>` directly. **Decision deferred to Task 2B.**

**Step 2: Verify the file is well-formed**

Open the file in the editor / IDE; it should render as a static constellation. No CLI verification needed at this point.

### Task 1C: Commit foundation

**Step 1: Stage and commit from `scideer/`**

```bash
git add frontend/src/styles/globals.css frontend/public/images/libra-constellation-hero.svg
git commit -m "feat(frontend): add gold accent tokens and Libra constellation SVG

Introduces --gold-1/2/3 CSS variables, the star-twinkle keyframe and
.libra-star animation classes, and the inlinable hero constellation
SVG with per-star IDs for staggered twinkle.

Refs docs/plans/2026-05-13-libra-ui-polish-design.md §3, §8."
```

**Step 2: Pause for user review**

After this commit, stop and surface the diff. The user is reviewing each task family. Do not proceed to Task Family 2 without an explicit "continue".

---

## Task Family 2: Hero composition (constellation overlay, WordRotate gold, CTA glow)

**Goal:** Make the constellation unmistakably visible and apply the gold accent thread to the hero.

### Task 2A: Update `WordRotate` aurora colours

**Files:**
- Modify: `frontend/src/components/ui/word-rotate.tsx:46`

**Step 1: Single-line replacement**

Replace `colors={["#efefbb", "#e9c665", "#e3a812"]}` with `colors={["#d19e1d", "#e9c665", "#e3a812"]}`.

**Step 2: Verify typecheck**

```
pnpm typecheck
```
Expected: exit 0.

### Task 2B: Refactor `hero.tsx` to overlay the inline constellation + dim FlickeringGrid + add CTA hover glow

**Files:**
- Modify: `frontend/src/components/landing/hero.tsx` (full file)

**Step 1: Read current file**

Re-read `frontend/src/components/landing/hero.tsx` so the diff is intentional. It's currently 128 lines including the `BytePlusIcon` component.

**Step 2: Apply the edit**

Replace the existing `<FlickeringGrid />` line and the surrounding container so the final structure matches:

```tsx
<div
  className={cn(
    "flex size-full flex-col items-center justify-center",
    className,
  )}
>
  {/* Layer 0: Galaxy backdrop (unchanged) */}
  <div className="absolute inset-0 z-0 bg-black/40">
    <Galaxy
      mouseRepulsion={false}
      starSpeed={0.2}
      density={0.6}
      glowIntensity={0.35}
      twinkleIntensity={0.3}
      speed={0.5}
    />
  </div>

  {/* Layer 1: Faint gold stardust (replaces the old mask) */}
  <FlickeringGrid
    className="absolute inset-0 z-0"
    squareSize={4}
    gridGap={4}
    color="#e9c665"
    maxOpacity={0.15}
    flickerChance={0.2}
  />

  {/* Layer 2: Real Libra constellation overlay (inline SVG so CSS classes apply) */}
  <div
    aria-hidden="true"
    className="pointer-events-none absolute inset-0 z-[1] flex items-center justify-center text-[#e9c665]"
  >
    <svg
      viewBox="0 0 200 200"
      fill="none"
      stroke="currentColor"
      className="size-[200px] md:size-[320px] drop-shadow-[0_0_24px_rgba(233,198,101,0.35)]"
    >
      <defs>
        <filter
          id="libra-star-glow-inline"
          x="-50%"
          y="-50%"
          width="200%"
          height="200%"
        >
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g stroke="currentColor" strokeWidth="1" opacity="0.45">
        <line x1="100" y1="40" x2="40" y2="100" />
        <line x1="100" y1="40" x2="160" y2="100" />
        <line x1="40" y1="100" x2="100" y2="160" />
        <line x1="160" y1="100" x2="100" y2="160" />
      </g>
      <g fill="currentColor" filter="url(#libra-star-glow-inline)">
        <circle className="libra-star libra-star--beta" cx="100" cy="40" r="7" />
        <circle className="libra-star libra-star--alpha" cx="40" cy="100" r="4.5" />
        <circle className="libra-star libra-star--gamma" cx="160" cy="100" r="4.5" />
        <circle className="libra-star libra-star--sigma" cx="100" cy="160" r="4.5" />
      </g>
      <text
        x="100"
        y="115"
        textAnchor="middle"
        fontFamily="Georgia, 'Times New Roman', serif"
        fontSize="48"
        fontWeight="500"
        fill="currentColor"
        opacity="0.85"
      >
        L
      </text>
    </svg>
  </div>

  {/* Layer 3: hero text + CTA (existing) */}
  <div className="container-md relative z-10 mx-auto flex h-screen flex-col items-center justify-center">
    {/* ...existing content of this div stays unchanged, including WordRotate, BytePlus banner, tagline, CTA... */}
  </div>
</div>
```

Inside the existing CTA `<Link href="/workspace"><Button>...</Button></Link>` block, replace the `Button` className from `"size-lg mt-8 scale-108"` to:

```tsx
className="size-lg mt-8 scale-108 transition-all duration-200 hover:scale-[1.13] hover:shadow-[0_0_24px_4px_var(--gold-glow)] focus-visible:shadow-[0_0_24px_4px_var(--gold-glow)]"
```

(The hover scale of 1.13 = original 1.08 × 1.05 multiplier so it visibly lifts.)

**Notes on the SVG choice:**
- We inline the SVG into the React tree rather than `<img src="/images/libra-constellation-hero.svg" />` because CSS class animations (`libra-star`) only apply to inline SVG elements — they cannot reach inside an `<img>` referenced as a foreign resource.
- The standalone `libra-constellation-hero.svg` file from Task 1B is retained for future reuse (e.g. an `<Image>` import in a doc page) and as a single source-of-truth reference for the geometry. Both paths use identical coordinates.
- The filter id is renamed to `libra-star-glow-inline` to avoid colliding with the standalone SVG if both are ever rendered on the same page.

**Step 3: Verify**

```
pnpm typecheck
pnpm lint
```
Expected: both exit 0.

If lint complains about the JSX inline SVG (e.g. attribute casing), correct any false-positives by switching `textAnchor` / `fontFamily` to JSX casing (already done above) — no `eslint-disable` comments.

### Task 2C: Visual sanity (optional dev-server peek)

This step is optional and the user may skip it if they prefer to verify on the remote server later.

**Step 1 (optional):** From `frontend/`, run `pnpm dev`, open `http://localhost:3000`, hard-refresh. Expect: large gold constellation pulsing in the hero, golden WordRotate text, CTA glowing on hover.

**Step 2:** Stop dev server with Ctrl+C.

### Task 2D: Commit hero family

```bash
git add frontend/src/components/ui/word-rotate.tsx frontend/src/components/landing/hero.tsx
git commit -m "feat(landing): inline Libra constellation overlay with twinkle + gold CTA glow

Replaces the FlickeringGrid mask-based constellation (which read as a
noise cloud) with a real inline SVG overlay. The 4 stars pulse out of
phase via .libra-star CSS classes; FlickeringGrid is downgraded to a
faint gold stardust field. WordRotate aurora drops its near-invisible
pale stop and gains a deep #d19e1d to hold contrast on warm beige.
CTA picks up a gold glow on hover and keyboard focus.

Refs docs/plans/2026-05-13-libra-ui-polish-design.md §3."
```

Pause for user review.

---

## Task Family 3: Landing header mark

**Goal:** Carry the constellation identity into the persistent top bar.

### Task 3A: Inject `libra-mark.svg` next to the wordmark

**Files:**
- Modify: `frontend/src/components/landing/header.tsx:34`

**Step 1: Apply edit**

Replace:

```tsx
<h1 className="font-serif text-xl">Libra</h1>
```

with:

```tsx
<div className="flex items-center gap-2">
  <img
    src="/images/libra-mark.svg"
    alt=""
    aria-hidden="true"
    className="size-5"
  />
  <h1 className="font-serif text-xl">Libra</h1>
</div>
```

Use `<img>` (not `next/image`) — `libra-mark.svg` is in `public/` and the header is rendered server-side with no width/height optimisation benefit. This matches how `BytePlusIcon` is inlined in the hero.

**Step 2: Verify**

```
pnpm typecheck
pnpm lint
```
Expected: exit 0. If lint flags `<img>` for missing `next/image`, suppress that single rule via `eslint-disable-next-line` only if it's flagged — verify first, do not pre-emptively disable.

### Task 3B: Commit

```bash
git add frontend/src/components/landing/header.tsx
git commit -m "feat(landing): add Libra mark to the top-bar wordmark

Carries the constellation identity past the hero fold."
```

Pause for review.

---

## Task Family 4: CommunitySection aurora colour fix

**Goal:** Remove the only blue/green/purple aurora on the page; align with the gold accent thread.

### Task 4A: Replace aurora colours

**Files:**
- Modify: `frontend/src/components/landing/sections/community-section.tsx:15`

**Step 1: Apply edit**

Replace:

```tsx
<AuroraText colors={["#60A5FA", "#A5FA60", "#A560FA"]}>
```

with:

```tsx
<AuroraText colors={["#d19e1d", "#e9c665", "#e3a812"]}>
```

**Step 2: Verify**

```
pnpm typecheck
pnpm lint
```
Expected: exit 0.

### Task 4B: Commit

```bash
git add frontend/src/components/landing/sections/community-section.tsx
git commit -m "fix(landing): align CommunitySection aurora with gold accent

The blue/green/purple aurora was the only off-palette element on the
marketing surface after the May 6 rebrand."
```

Pause for review.

---

## Task Family 5: CaseStudy rewrite to research scenarios

**Goal:** Replace the 6 ByteDance demo threads (Doraemon, Pride & Prejudice, Titanic EDA, Fei-Fei Li, …) with Libra research scenarios. Use CSS-gradient backgrounds + lucide icons so no new image assets are required.

### Task 5A: Rewrite `case-study-section.tsx`

**Files:**
- Modify: `frontend/src/components/landing/sections/case-study-section.tsx` (full file)

**Step 1: Read current file**

Confirm the structure: top-level `caseStudies` array of 6 entries, then a `<Section>` wrapping a grid of `<Link>` → `<Card>` blocks.

**Step 2: Apply edit (full replacement)**

New file content:

```tsx
import {
  BarChart3,
  BookOpen,
  FileText,
  FlaskConical,
  Microscope,
  Network,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { Card } from "@/components/ui/card";
import { pathOfThread } from "@/core/threads/utils";
import { cn } from "@/lib/utils";

import { Section } from "../section";

type CaseStudy = {
  threadId: string;
  title: string;
  description: string;
  Icon: LucideIcon;
  /** oklch hue in degrees — keeps cards on the warm-minimal palette */
  hue: number;
};

const CASE_STUDIES: CaseStudy[] = [
  {
    threadId: "7cfa5f8f-a2f8-47ad-acbd-da7137baf990",
    title: "Reproduce GCN on the Cora Dataset",
    description:
      "Parse arXiv:1609.02907, extract the method and hyperparameters, run a 2-layer GCN in the sandbox, and compare accuracy against the paper's reported 81.5%.",
    Icon: FlaskConical,
    hue: 70,
  },
  {
    threadId: "4f3e55ee-f853-43db-bfb3-7d1a411f03cb",
    title: "Systematic Review of Mixture-of-Experts Papers",
    description:
      "Search 50+ MoE papers on arXiv since 2023, cluster by architectural approach, and generate a structured SLR report with citations.",
    Icon: BookOpen,
    hue: 20,
  },
  {
    threadId: "21cfea46-34bd-4aa6-9e1f-3009452fbeb9",
    title: "Write a NeurIPS-Style LaTeX Paper from Notes",
    description:
      "Convert raw experiment notes and result figures into a conference-ready LaTeX paper with auto-compiled bibliography and PDF output.",
    Icon: FileText,
    hue: 130,
  },
  {
    threadId: "ad76c455-5bf9-4335-8517-fc03834ab828",
    title: "Citation Graph for “Attention Is All You Need”",
    description:
      "Use Semantic Scholar MCP to expand the 2-hop influential descendants and visualize the citation tree by year and venue.",
    Icon: Network,
    hue: 240,
  },
  {
    threadId: "d3e5adaf-084c-4dd5-9d29-94f1d6bccd98",
    title: "Exploratory Analysis of the Cora Citation Network",
    description:
      "Compute graph statistics, plot the degree distribution, and identify research community clusters with publication-grade figures.",
    Icon: BarChart3,
    hue: 290,
  },
  {
    threadId: "3823e443-4e2b-4679-b496-a9506eae462b",
    title: "Design an Ablation Study for a Vision Transformer",
    description:
      "Generate a complete ablation matrix, recommend hyperparameter sweeps, execute in the sandbox, and summarise findings.",
    Icon: Microscope,
    hue: 160,
  },
];

export function CaseStudySection({ className }: { className?: string }) {
  return (
    <Section
      className={className}
      title="Case Studies"
      subtitle="See how Libra accelerates the full research lifecycle"
    >
      <div className="container-md mt-8 grid grid-cols-1 gap-4 px-4 md:grid-cols-2 md:px-20 lg:grid-cols-3">
        {CASE_STUDIES.map(({ threadId, title, description, Icon, hue }) => (
          <Link
            key={threadId}
            href={pathOfThread(threadId) + "?mock=true"}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Card className="group/card relative h-64 overflow-hidden">
              {/* Gradient wash — keeps the warm-minimal palette */}
              <div
                className="absolute inset-0 z-0 transition-transform duration-300 group-hover/card:scale-105"
                style={{
                  background: `linear-gradient(135deg, oklch(0.95 0.03 ${hue}) 0%, oklch(0.82 0.06 ${hue}) 100%)`,
                }}
              />
              {/* Centred icon */}
              <div className="pointer-events-none absolute inset-0 z-[1] flex items-center justify-center text-foreground/30 transition-colors duration-300 group-hover/card:text-foreground/60">
                <Icon className="size-16" strokeWidth={1.25} />
              </div>
              {/* Title / description tray — same slide-up reveal as before */}
              <div
                className={cn(
                  "absolute right-0 bottom-0 left-0 z-[2] flex h-full w-full translate-y-[calc(100%-60px)] flex-col items-center",
                  "transition-all duration-300",
                  "group-hover/card:translate-y-[calc(100%-128px)]",
                )}
              >
                <div
                  className="flex w-full flex-col p-4"
                  style={{
                    background:
                      "linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.85) 100%)",
                  }}
                >
                  <div className="flex flex-col gap-2">
                    <h3 className="flex h-14 items-center text-xl font-bold text-white text-shadow-black">
                      {title}
                    </h3>
                    <p className="overflow-hidden text-sm text-white/85 text-shadow-black">
                      {description}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </Section>
  );
}
```

Notes on the rewrite:
- `caseStudies` is renamed to `CASE_STUDIES` (const-of-consts naming).
- The 6 `threadId` UUIDs from the original file are kept verbatim so `?mock=true` deep links still resolve. Order is preserved.
- The Section subtitle is updated from "See how Libra is used in real research workflows" to the slightly tighter "See how Libra accelerates the full research lifecycle".
- `bg-cover bg-center bg-no-repeat` and the `style={{ backgroundImage: \`url(/images/${threadId}.jpg)\` }}` are removed. The 6 `.jpg` files in `public/images/` are **not deleted** — leaving them in tree avoids breaking anything that might still reference them and they total < 5 MB; cleanup is deferred to a future YAGNI pass.
- Text tray gradient: original used `rgba(0,0,0,1) 100%` which crushed the description against the gradient at 100%. New value `0.85` lets the description text remain readable while still ensuring contrast against the icon underneath.

**Step 3: Verify**

```
pnpm typecheck
pnpm lint
```
Expected: exit 0. If `lucide-react` icons aren't already in deps, this typecheck will fail; check `package.json` first — lucide is a transitive dep of several shadcn primitives already in use, so this should be a no-op install.

### Task 5B: Commit

```bash
git add frontend/src/components/landing/sections/case-study-section.tsx
git commit -m "feat(landing): replace ByteDance case studies with Libra research scenarios

Six new cards — GCN/Cora reproduction, MoE SLR, NeurIPS LaTeX writing,
Attention citation graph, Cora EDA, ViT ablation design — each backed by
a gradient wash + lucide icon (no jpg dependency). Preserves the
original threadId list so existing ?mock=true deep links still resolve."
```

Pause for review.

---

## Task Family 6: WhatsNewSection skill cards rewrite

**Goal:** Turn the 6 generic "agent capability" cards into Libra-skill-centric content with lucide icons, leveraging `BentoCardProps.label` accepting `ReactNode` (so we do not edit `magic-bento.tsx`).

### Task 6A: Rewrite `whats-new-section.tsx`

**Files:**
- Modify: `frontend/src/components/landing/sections/whats-new-section.tsx` (full file)

**Step 1: Apply edit (full replacement)**

```tsx
"use client";

import {
  BarChart3,
  BookOpen,
  FileText,
  FlaskConical,
  Github,
  Network,
  type LucideIcon,
} from "lucide-react";

import MagicBento, { type BentoCardProps } from "@/components/ui/magic-bento";
import { cn } from "@/lib/utils";

import { Section } from "../section";

const CARD_BG = "#0a0a0a";

function buildLabel(label: string, Icon: LucideIcon): React.ReactNode {
  return (
    <span className="flex items-center gap-2 text-[color:var(--gold-2)]">
      <Icon className="size-4" strokeWidth={2} />
      {label}
    </span>
  );
}

const features: BentoCardProps[] = [
  {
    color: CARD_BG,
    label: buildLabel("Literature", BookOpen),
    title: "Systematic Search",
    description: "arXiv + Semantic Scholar with auto-clustering",
  },
  {
    color: CARD_BG,
    label: buildLabel("Reproduction", FlaskConical),
    title: "Paper-to-Code",
    description: "Extract method and hparams, run in sandbox, compare metrics",
  },
  {
    color: CARD_BG,
    label: buildLabel("Experiment", BarChart3),
    title: "Design & Analyze",
    description: "Plan ablations, run, generate publication figures",
  },
  {
    color: CARD_BG,
    label: buildLabel("Writing", FileText),
    title: "LaTeX Papers",
    description: "NeurIPS/ICML templates, auto-bibliography, PDF compile",
  },
  {
    color: CARD_BG,
    label: buildLabel("Citation", Network),
    title: "Graph Exploration",
    description: "2-hop citation graph via Semantic Scholar MCP",
  },
  {
    color: CARD_BG,
    label: buildLabel("Open Source", Github),
    title: "MIT License",
    description: "Self-hosted, swappable models, full control",
  },
];

export function WhatsNewSection({ className }: { className?: string }) {
  return (
    <Section
      className={cn("", className)}
      title="What's New in Libra"
      subtitle="Libra brings the full scientific research lifecycle to one agent — from arXiv search to LaTeX paper compilation."
    >
      <div className="flex w-full items-center justify-center">
        <MagicBento data={features} />
      </div>
    </Section>
  );
}
```

Notes:
- Six lucide icons match the case-study set so the visual language carries between sections (BookOpen for literature, FlaskConical for reproduction, BarChart3 for analysis, FileText for LaTeX writing, Network for citation graphs, Github for open source).
- `buildLabel(label, Icon)` is a pure helper so the JSX in the `features` array stays tabular and readable.
- The gold colour is applied at the call site via `text-[color:var(--gold-2)]`. This is Tailwind 4 arbitrary-value syntax — verify it produces a valid utility class. If Tailwind's parser rejects this exact form, fall back to inline `style={{ color: "var(--gold-2)" }}` on the span.
- `MagicBento` props are unchanged (no `enableStars` / `glowColor` overrides). The card body colour stays `#0a0a0a` per design §1 decision 3.
- `Section` subtitle is unchanged.

**Step 2: Verify**

```
pnpm typecheck
pnpm lint
```
Expected: exit 0.

### Task 6B: Final build sanity

This is the only `pnpm build` in the plan — gates the whole change against production-mode Next.js compilation.

```
pnpm build
```
Expected: exit 0, no Tailwind warnings about unknown classes, no TypeScript errors. If `text-[color:var(--gold-2)]` was rejected at this stage (possible Tailwind 4 quirk with arbitrary colour values referencing CSS vars), revert that one className to `style={{ color: "var(--gold-2)" }}` and re-run build.

### Task 6C: Commit

```bash
git add frontend/src/components/landing/sections/whats-new-section.tsx
git commit -m "feat(landing): rewrite WhatsNew cards as Libra skills with gold-icon labels

Six skill-centric cards (Literature/Reproduction/Experiment/Writing/
Citation/Open Source) replace the generic agent-capability cards.
Icons + gold label colour are passed via the existing
ReactNode-typed BentoCardProps.label slot — magic-bento.tsx itself is
untouched, preserving the auto-generated-component contract."
```

Pause for review.

---

## Final Steps After All Task Families

### Step F1: Confirm working tree state

From `scideer/`:
```
git status
git log --oneline -8
```

Expected: clean tree, 6 new commits ahead of `origin/scideer-main` (one per task family — except Task Family 1 is one commit, Family 2 is one commit, etc., so 6 total).

### Step F2: Report back to user

Surface:
- Total commits ahead of origin
- One-line summary per commit
- The two paths the user can choose next:
  1. Review locally → tell agent to `git push origin scideer-main` → user pulls on server → restarts via `bash scripts/serve.sh --restart --dev --daemon`
  2. Revert any task family that doesn't pass review

### Step F3: DO NOT PUSH WITHOUT EXPLICIT GO-AHEAD

`git push` is a separate user-authorised step per root CLAUDE.md hard rule #1 and the user's brief. Stop after Step F2 and wait.

---

## Skill References

- @superpowers:executing-plans — drives this plan task-by-task
- @superpowers:systematic-debugging — if a verification step fails unexpectedly
- @superpowers:verification-before-completion — required before claiming any task family done

## Risks Recap (from design §10)

| Risk | Where it bites in this plan | Pre-empted by |
|------|-----------------------------|---------------|
| Hero too busy | Task 2B | FlickeringGrid opacity 0.15; twinkle period 2.4s |
| MagicBento structural change | Task 6A | Label is `ReactNode`, no component edit needed |
| Tailwind arbitrary CSS-var class rejected | Task 6B (final build) | Fallback to inline `style={{ color: "var(--gold-2)" }}` |
| Case-study `?mock=true` deep link 404 | Task 5A | UUIDs preserved verbatim |
| Pre-commit hook blocks a commit | Every commit step | Fix root cause; do **not** `--no-verify` |
