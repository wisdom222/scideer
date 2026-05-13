# Libra Frontend UI Polish — Design Document

> Make the Libra constellation logo unmistakably visible on the landing
> hero, introduce a consistent gold accent across the marketing surface,
> and replace mismatched DeerFlow-era case studies with research ones —
> all without breaking the locked warm-minimal palette.

- Date: 2026-05-13
- Author: Jasper (with Claude Code, brainstorming skill)
- Status: Approved through brainstorming Q1–Q7 on 2026-05-13

---

## 0. Context

The Libra rebranding ([2026-05-06-libra-rebranding-design.md](2026-05-06-libra-rebranding-design.md))
locked the name, the constellation logo concept, and a "warm minimal"
palette. After deploy, the landing-page constellation effect — a
`FlickeringGrid` masked by `libra-logo.svg` — turned out to read as a
"bordered noise cloud" rather than a recognisable constellation, because
the SVG's stars and connecting lines were never actually drawn; they only
shaped the area where the grid flickered.

This polish pass keeps the warm-minimal baseline but adds a single gold
accent thread for visual identity and identifies four collateral issues
(stale case studies, off-palette aurora colours, dark-only tags, missing
header mark) that erode credibility in a live grading demo.

The brainstorming session also reconfirmed the **grading-outcome
priority**: live-demo reliability > defensible novelty > quantitative
benchmark > polished writeup. Every change below is justified against
this priority.

---

## 1. Decisions (Locked)

| # | Decision | Reasoning |
|---|----------|-----------|
| 1 | **Hero**: render an actual SVG constellation on top of the Galaxy background, give the 4 stars staggered CSS twinkle animations, and downgrade `FlickeringGrid` to a low-opacity stardust layer | Mask-based "constellation" is visually unrecognisable; an actual SVG is the only path to instant brand recognition during a 30-second demo |
| 2 | **Palette**: add a single **gold accent** thread (`#d19e1d → #e9c665 → #e3a812`) on top of the warm-minimal base; reuse the existing `.golden-text` gradient | Stars = gold = constellation theme. Single-colour accent is YAGNI-compliant; full deep-navy / dual-mode palettes were considered and rejected as low ROI under the May deadline |
| 3 | **Configuration**: keep `:root` and `.dark` token sets untouched; expose gold only as new `--gold-1/2/3/glow` tokens consumed in specific places | Avoids accessibility regressions and the dark-mode palette rework that section 0 of the rebranding doc warned against |
| 4 | **Skills surface**: rewrite the existing `WhatsNewSection` 6-card grid to be Libra-skill-centric with lucide icons; do **not** introduce a new section | Cards already exist; rewriting copy + injecting icons is lower risk than adding a new section file and competing with `SkillsSection` |
| 5 | **Case studies**: replace 6 ByteDance demo threads (Doraemon, Pride & Prejudice, Titanic EDA, Fei-Fei Li) with 6 Libra research cases using CSS-gradient placeholders + lucide icons (no new image assets) | The current cards are the single biggest credibility hit for a "scientific research agent". Image-free placeholders avoid the asset-pipeline blocker |
| 6 | **Landing header**: add an 18px `libra-mark.svg` to the left of the wordmark | Carries the constellation identity from hero into every scrolled view |
| 7 | **Workspace, login, setup**: untouched in this pass | Brainstorm Q7 narrowed scope to landing-page-only; workspace already received the rebranding mark on 2026-05-06 |

---

## 2. Scope Boundaries

### IN scope

- `frontend/public/images/libra-constellation-hero.svg` (new — hero overlay with per-star IDs)
- `frontend/src/components/landing/hero.tsx`
- `frontend/src/components/landing/header.tsx`
- `frontend/src/components/landing/sections/community-section.tsx`
- `frontend/src/components/landing/sections/case-study-section.tsx`
- `frontend/src/components/landing/sections/whats-new-section.tsx`
- `frontend/src/components/ui/word-rotate.tsx` (one-line colour change)
- `frontend/src/components/ui/magic-bento.tsx` (only if icon prop needs threading; check first)
- `frontend/src/styles/globals.css` (new gold tokens + `@keyframes star-twinkle`)

### OUT of scope (deferred / out of bounds)

- `backend/`, `agents/`, `benchmarks/`, `docker/`, `skills/`, `mcp_servers/` (per user instruction)
- i18n translation tables (a separate parallel track)
- workspace, login, setup pages
- `SandboxSection` dark-only tag colours (option C in Q7 — explicitly deferred)
- `MagicBento` card base colour (`#0a0a0a` — deferred; component is designed for dark backgrounds)
- New image assets beyond the constellation SVG (case-study cards use CSS gradients + lucide icons)
- Workspace header mark (already covered in the 2026-05-06 rebranding pass)

---

## 3. Hero Composition

### 3.1 Layer stack (back to front)

```
z-0: <Galaxy /> — unchanged (mouseRepulsion=false, starSpeed=0.2, density=0.6, glowIntensity=0.35)
z-0: <FlickeringGrid /> — opacity reduced to 0.15, color="#e9c665", no mask
       → becomes a faint warm-gold stardust field instead of a masked shape
z-1: <LibraConstellation /> — NEW. Absolute-centered, 200px on mobile, 320px on md+
       → actually-drawn 4 stars + diamond + serif L, each star animated
z-10: <hero text block> — WordRotate + headline + tagline + CTA (unchanged structure)
```

### 3.2 The constellation SVG

`libra-constellation-hero.svg` is a refactor of `libra-logo.svg` so each
star is a tagged element CSS can target:

```xml
<svg viewBox="0 0 200 200" ...>
  <defs>
    <filter id="star-glow">
      <feGaussianBlur stdDeviation="2.5" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g stroke="currentColor" stroke-width="1" opacity="0.45">
    <line x1="100" y1="40"  x2="40"  y2="100"/>
    <line x1="100" y1="40"  x2="160" y2="100"/>
    <line x1="40"  y1="100" x2="100" y2="160"/>
    <line x1="160" y1="100" x2="100" y2="160"/>
  </g>
  <g filter="url(#star-glow)">
    <circle id="star-beta"  cx="100" cy="40"  r="7"   class="libra-star libra-star--beta"/>
    <circle id="star-alpha" cx="40"  cy="100" r="4.5" class="libra-star libra-star--alpha"/>
    <circle id="star-gamma" cx="160" cy="100" r="4.5" class="libra-star libra-star--gamma"/>
    <circle id="star-sigma" cx="100" cy="160" r="4.5" class="libra-star libra-star--sigma"/>
  </g>
  <text x="100" y="115" text-anchor="middle"
        font-family="Georgia, 'Times New Roman', serif"
        font-size="48" font-weight="500"
        fill="currentColor" opacity="0.85">L</text>
</svg>
```

Stars are filled with `currentColor` so the component can recolour them
via the wrapper's `text-` class. The hero will render the SVG with
`text-[#e9c665]` to land on gold-2.

### 3.3 Twinkle animation

```css
@keyframes star-twinkle {
  0%, 100% { transform: scale(1);    opacity: 1.0; filter: drop-shadow(0 0 6px  var(--gold-2)); }
  50%      { transform: scale(1.15); opacity: 0.6; filter: drop-shadow(0 0 14px var(--gold-2)); }
}

.libra-star { animation: star-twinkle 2.4s ease-in-out infinite; transform-origin: center; transform-box: fill-box; }
.libra-star--beta  { animation-delay: 0s;   }
.libra-star--alpha { animation-delay: 0.6s; }
.libra-star--gamma { animation-delay: 1.2s; }
.libra-star--sigma { animation-delay: 1.8s; }
```

`transform-box: fill-box` is required so the SVG `<circle>`'s
`transform-origin: center` evaluates relative to its own bounding box,
not the SVG root.

### 3.4 WordRotate gold

Single-line change in `word-rotate.tsx`:

```ts
colors={["#efefbb", "#e9c665", "#e3a812"]}
// →
colors={["#d19e1d", "#e9c665", "#e3a812"]}
```

The pale `#efefbb` was effectively invisible on warm-beige; the deep
`#d19e1d` stop holds contrast at the top of every aurora cycle.

### 3.5 CTA button

`<Button>` keeps its default white/black styling. Inline className adds:

```
transition-all duration-200
hover:shadow-[0_0_24px_4px_var(--gold-glow)]
hover:scale-[1.05]
focus-visible:shadow-[0_0_24px_4px_var(--gold-glow)]
```

No new variants needed in `button.tsx`.

---

## 4. Landing Header (`header.tsx:34`)

```tsx
// Before
<h1 className="font-serif text-xl">Libra</h1>

// After
<div className="flex items-center gap-2">
  <img src="/images/libra-mark.svg" alt="" className="size-5" />
  <h1 className="font-serif text-xl">Libra</h1>
</div>
```

The mark is decorative (the `<h1>` carries the accessible name), so
`alt=""`.

---

## 5. CommunitySection Colour Fix

`community-section.tsx:15`:

```tsx
<AuroraText colors={["#60A5FA", "#A5FA60", "#A560FA"]}>
// →
<AuroraText colors={["#d19e1d", "#e9c665", "#e3a812"]}>
```

This brings the section in line with hero WordRotate and removes the
only blue/green/purple aurora on the page.

---

## 6. CaseStudy Rewrite

Replace the `caseStudies` array in `case-study-section.tsx:10-47` with
the six entries below. `threadId` values are preserved so existing
`?mock=true` deep links still resolve (the cards become non-clickable if
the mock data does not match, but the navigation contract is unchanged).

```ts
const caseStudies = [
  {
    threadId: "7cfa5f8f-a2f8-47ad-acbd-da7137baf990",
    title: "Reproduce GCN on the Cora Dataset",
    description:
      "Parse arXiv:1609.02907, extract the method and hyperparameters, run a 2-layer GCN in the sandbox, and compare accuracy against the paper's reported 81.5%.",
    icon: "FlaskConical",
    tint: "amber",
  },
  {
    threadId: "4f3e55ee-f853-43db-bfb3-7d1a411f03cb",
    title: "Systematic Review of Mixture-of-Experts Papers",
    description:
      "Search 50+ MoE papers on arXiv since 2023, cluster by architectural approach, and generate a structured SLR report with citations.",
    icon: "BookOpen",
    tint: "rose",
  },
  {
    threadId: "21cfea46-34bd-4aa6-9e1f-3009452fbeb9",
    title: "Write a NeurIPS-Style LaTeX Paper from Notes",
    description:
      "Convert raw experiment notes and result figures into a conference-ready LaTeX paper with auto-compiled bibliography and PDF output.",
    icon: "FileText",
    tint: "lime",
  },
  {
    threadId: "ad76c455-5bf9-4335-8517-fc03834ab828",
    title: "Citation Graph for \"Attention Is All You Need\"",
    description:
      "Use Semantic Scholar MCP to expand the 2-hop influential descendants and visualize the citation tree by year and venue.",
    icon: "Network",
    tint: "sky",
  },
  {
    threadId: "d3e5adaf-084c-4dd5-9d29-94f1d6bccd98",
    title: "Exploratory Analysis of the Cora Citation Network",
    description:
      "Compute graph statistics, plot the degree distribution, and identify research community clusters with publication-grade figures.",
    icon: "BarChart3",
    tint: "violet",
  },
  {
    threadId: "3823e443-4e2b-4679-b496-a9506eae462b",
    title: "Design an Ablation Study for a Vision Transformer",
    description:
      "Generate a complete ablation matrix, recommend hyperparameter sweeps, execute in the sandbox, and summarise findings.",
    icon: "Microscope",
    tint: "emerald",
  },
];
```

### 6.1 Card visuals (no image assets)

```tsx
<div
  className="absolute inset-0 z-0 bg-[linear-gradient(135deg,oklch(0.95_0.03_var(--tint-h))_0%,oklch(0.82_0.05_var(--tint-h))_100%)]"
  style={{ "--tint-h": tintHue[caseStudy.tint] } as React.CSSProperties}
/>
<div className="absolute inset-0 flex items-center justify-center text-foreground/40 group-hover/card:text-foreground/70 transition-colors">
  {/* lucide icon at size-16 */}
</div>
```

`tintHue` maps the string tag to an oklch hue (`amber → 70`, `rose → 20`,
etc.), giving each card a distinct warm wash without breaking the
warm-minimal palette. The hover scale + dim from the original card
markup is preserved verbatim.

---

## 7. WhatsNewSection Rewrite

`MagicBento` accepts an array of `BentoCardProps`. Replace the 6 entries
with skill-centric content:

```ts
const features: BentoCardProps[] = [
  { color: COLOR, label: "Literature",   title: "Systematic Search",   description: "arXiv + Semantic Scholar with auto-clustering",        icon: BookOpen },
  { color: COLOR, label: "Reproduction", title: "Paper-to-Code",       description: "Extract method + hparams, run in sandbox, compare",     icon: FlaskConical },
  { color: COLOR, label: "Experiment",   title: "Design & Analyze",    description: "Plan ablations, run, generate publication figures",     icon: BarChart3 },
  { color: COLOR, label: "Writing",      title: "LaTeX Papers",        description: "NeurIPS/ICML templates, auto-bib, PDF compile",         icon: FileText },
  { color: COLOR, label: "Citation",     title: "Graph Exploration",   description: "2-hop citation graph via Semantic Scholar MCP",         icon: Network },
  { color: COLOR, label: "Open Source",  title: "MIT License",         description: "Self-hosted, swappable models, full control",           icon: Github },
];
```

### 7.1 Icon prop on MagicBento

Before writing code, the implementer **MUST** read `magic-bento.tsx`
first to confirm whether `BentoCardProps` already accepts an icon. Three
outcomes:

1. **It already does** → just pass `icon: LucideIcon` directly.
2. **It doesn't, simple add** (one prop, rendered in a known slot) →
   extend `BentoCardProps` with `icon?: LucideIcon`, render in card header.
3. **It doesn't, structural change required** → fall back to label-only
   change (no icons); accept the YAGNI hit rather than touch an auto-generated
   component file.

This decision is part of the implementation plan, not pre-judged here.

### 7.2 Gold label

The `label` colour inside the bento card should switch from its current
muted-foreground tone to `var(--gold-2)`. If this lives inside
`magic-bento.tsx`, prefer wrapping the label at the call site (a `<span
className="text-[var(--gold-2)]">...</span>`) over editing the
auto-generated component.

---

## 8. globals.css

Append after `.golden-text`:

```css
:root {
  --gold-1: #d19e1d;
  --gold-2: #e9c665;
  --gold-3: #e3a812;
  --gold-glow: rgba(233, 198, 101, 0.45);
}

@keyframes star-twinkle {
  0%, 100% { transform: scale(1);    opacity: 1.0; filter: drop-shadow(0 0 6px  var(--gold-2)); }
  50%      { transform: scale(1.15); opacity: 0.6; filter: drop-shadow(0 0 14px var(--gold-2)); }
}

.libra-star {
  transform-origin: center;
  transform-box: fill-box;
  animation: star-twinkle 2.4s ease-in-out infinite;
}
.libra-star--beta  { animation-delay: 0s;   }
.libra-star--alpha { animation-delay: 0.6s; }
.libra-star--gamma { animation-delay: 1.2s; }
.libra-star--sigma { animation-delay: 1.8s; }

@media (prefers-reduced-motion: reduce) {
  .libra-star { animation: none; }
}
```

The `prefers-reduced-motion` opt-out is mandatory for a hero element
that pulses 4 times in parallel.

---

## 9. Verification Plan

After the user deploys (`git pull` + `bash scripts/serve.sh --restart
--dev --daemon`) and hard-refreshes:

| Check | Expected |
|------|----------|
| Hero shows 4 gold stars connected by faint diamond lines with a serif `L` in the middle | Constellation is unmistakable from across the room |
| The 4 stars pulse out of phase | Visual "breathing" — no two stars at peak simultaneously |
| WordRotate cycles through 7 phrases in deep-to-light gold | No phrase washes out against the warm-beige background |
| CTA glows gold on hover and on keyboard focus | Hover scale stays 1.05, no layout shift |
| Landing header (top-left) shows the mini constellation next to "Libra" | Mark is 20px, vertically centred |
| CommunitySection title reads in gold (not blue/green/purple) | Aurora colours align with hero |
| CaseStudy cards show research titles + gradient backgrounds + lucide icons | No Doraemon, no Pride & Prejudice, no ByteDance jpegs |
| WhatsNewSection cards read as Libra skills with icons | Each card has a lucide icon and a gold label |
| `prefers-reduced-motion: reduce` system setting freezes the stars | No CSS animation when the user has motion disabled |

A targeted Playwright smoke test (`pnpm test:e2e`) is **not** required
for this pass — the changes are purely cosmetic and not exercised by the
existing e2e suite. Manual visual verification suffices.

---

## 10. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|------------|
| Hero composition becomes too busy (Galaxy + stardust + constellation + WordRotate + Galaxy stars all moving) | Medium | Medium | `FlickeringGrid` opacity drops from 0.30 → 0.15; star animation period stretched to 2.4s; we can drop the grid entirely if reviewers find it noisy |
| `MagicBento` icon prop requires structural changes | Medium | Low | Fallback to label-only update; do not refactor an auto-generated component |
| Case-study card `?mock=true` deep links return 404 because the mock thread does not match the new title | Low | Low | Demo path is the homepage, not these threads; clicks are not on the rehearsal critical path |
| Gold accent disappears in dark mode (cards already on dark backgrounds) | Low | Low | `--gold-2` `#e9c665` retains contrast on both `#FAF8F2` and `#1a1a1a` (verified by quick eyeball; can run aXe later if needed) |
| Two parallel rebrand tracks (this and i18n strings) edit the same files | Medium | Medium | This pass does not touch `messages/*.json` or strings consumed via `t()`; merge conflicts limited to component bodies |

---

## 11. Implementation Order (high level)

1. **Foundation** — `globals.css` tokens + `@keyframes`, new `libra-constellation-hero.svg`
2. **Hero composition** — `hero.tsx` overlay + FlickeringGrid downgrade, WordRotate colours, CTA glow
3. **Landing header** — add mark
4. **Section consistency** — CommunitySection aurora colours
5. **Content rewrites** — CaseStudy entries + card visuals, WhatsNewSection cards
6. **Polish** — verify reduced-motion, sanity-check colour contrast

Each numbered step is a candidate "task family" for the implementation
plan and a natural commit boundary. The actual plan and task split is
the writing-plans skill's job.

---

## 12. Out-of-Scope (Future Considerations)

If a second polish pass is requested after the May deadline:

- SandboxSection dark-only tag colours (Q7 option C, explicitly deferred)
- `MagicBento` lightening / `#1a1a1a` background and particle-animation re-tune
- Workspace header gold accent (currently fully neutral)
- Login/setup page accent (currently fully neutral)
- A subtle pulse on the brightest β star inside `favicon.svg` so the
  browser tab animates while a thread is streaming
- Replacing CSS-gradient case-study cards with real screenshots once
  Libra runs end-to-end demos for each case
