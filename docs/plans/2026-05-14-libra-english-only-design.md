# Libra English-Only UI — Design Document

> Make the Libra frontend display in English regardless of the browser's
> locale, by clamping the i18n framework's locale detector to `en-US`
> and deleting the Nextra `/zh/docs` content tree. Two surgical user-
> visible Chinese leaks are fixed in the same pass.

- Date: 2026-05-14
- Author: Jasper (with Claude Code, brainstorming skill)
- Status: Approved through brainstorming Q1–Q4 on 2026-05-14

---

## 0. Context

The Libra rebranding pass ([2026-05-06-libra-rebranding-design.md](2026-05-06-libra-rebranding-design.md))
translated the major user-visible strings but kept the i18n framework intact.
DeerFlow's `detectLocaleServer` reads a `locale` cookie and falls back
to a browser-language guess via `normalizeLocale`, so a Chrome running
under a `zh-CN` UA still resolves to `zh-CN` and the workspace renders
in Chinese.

The PH6725 final-project defence may have English-speaking reviewers,
so the user wants the UI to read English under any browser setting, no
language switcher needed.

The 2026-05-14 Chinese-character audit (1665 hits across 44 files) lays
out the actual surface area:

| Source | Hits | Nature |
|--------|-----:|--------|
| `core/i18n/locales/zh-CN.ts` | 309 | Chinese translation table (consumed only if locale = `zh-CN`) |
| `content/zh/` (44 files) | ~1100 | Nextra Chinese docs tree (consumed only at `/zh/docs/*`) |
| Code comments in `utils.ts` / `message-group.tsx` / `message-list.tsx` | ~30 | Developer notes about LangGraph streaming edge cases — never reach UI |
| `citation-link.tsx:24` | 1 | `childrenText === "来源"` — runtime check for Chinese "Source" label |
| `app/[lang]/docs/layout.tsx:12` | 1 | `{ locale: "zh", name: "中文" }` language-switcher entry |
| `content/en/reference/model-providers/_meta.ts:5` | 1 | `title: "火山方舟"` — **Chinese title leaked into the English docs tree** |

The audit also reconfirms that the rebrand correctly translated the user-
visible strings in landing components, login/setup pages, About page, and
workspace shell — so the only path through which Chinese still reaches the
UI is `locale === "zh-CN"` (resolved by `detectLocaleServer`) plus the
two stray hardcoded leaks at the bottom of the table.

---

## 1. Decisions (Locked)

| # | Decision | Reasoning |
|---|----------|-----------|
| 1 | **Path A**: keep the i18n framework, force `detectLocaleServer()` to always return `en-US` | Single-line change, zero regression risk, instant 100% UI-English. Path B (rip out i18n + literalise 50+ components) would touch ~80 files for ~10 kB bundle saving and lose future re-i18n ergonomics |
| 2 | **Delete `content/zh/` entirely** (44 files), remove `zh` from the Nextra language switcher, and add a `/zh/*` → `/en/*` middleware redirect | Repo cleanup, prevents stale bookmark 404, and makes the "all English" promise honest in both UI buttons and direct URL access |
| 3 | **Keep `README_zh.md`** at repo root | Out of UI scope; useful for Chinese-speaking defence committee members |
| 4 | **Do not translate Chinese developer comments** in code files | Not user-visible; rewriting risks misinterpreting LangGraph timing notes the parallel agent wrote with full context |
| 5 | **Fix two user-visible Chinese leaks**: drop the `"来源"` fallback in `citation-link.tsx`, rename `"火山方舟"` → `"Volcengine Ark"` in the English-tree `_meta.ts` | These are bugs regardless of the i18n strategy — first one becomes dead code under Path A, second one is a mis-labelled doc page in production today |

The Chinese translation table `zh-CN.ts` is **not deleted**. Path A's
guarantee is "the framework never selects zh", not "the framework
forgets zh exists". Keeping the file gives a one-revert path back to
bilingual UI if priorities change post-defence.

---

## 2. Scope Boundaries

### IN scope

- `frontend/src/core/i18n/server.ts` (clamp `detectLocaleServer`)
- `frontend/src/app/[lang]/docs/layout.tsx` (remove `zh` from `i18n.locales`)
- `frontend/middleware.ts` (NEW, or extend existing) — redirect `/zh/*` to `/en/*`
- `frontend/src/content/zh/` (delete entire directory — 44 files)
- `frontend/src/components/workspace/citations/citation-link.tsx` (drop `"来源"` fallback)
- `frontend/src/content/en/reference/model-providers/_meta.ts` (`火山方舟` → `Volcengine Ark`)

### OUT of scope

- `frontend/src/core/i18n/locales/zh-CN.ts` (the 309-line Chinese table — keep dormant)
- `frontend/src/core/i18n/hooks.ts`, `client.tsx`, `provider.tsx`, `locale.ts`, `translations.ts` (the i18n machinery itself is untouched)
- All component-side `t.xxx.yyy` references (still resolved against the en-US table — no rewrites)
- Chinese developer comments in `utils.ts`, `message-group.tsx`, `message-list.tsx`, etc.
- `README_zh.md`
- `backend/`, `agents/`, `benchmarks/`, `docker/`, `skills/`, `mcp_servers/`
- `_reference/deer-flow/` (read-only upstream mirror)

---

## 3. Implementation Details

### 3.1 `server.ts` clamp

```ts
// Before
export async function detectLocaleServer(): Promise<Locale> {
  const cookieStore = await cookies();
  let locale = cookieStore.get("locale")?.value;
  if (locale !== undefined) {
    try { locale = decodeURIComponent(locale); } catch {}
  }
  return normalizeLocale(locale);
}

// After
export async function detectLocaleServer(): Promise<Locale> {
  // Locked to en-US for the PH6725 defence — see
  // docs/plans/2026-05-14-libra-english-only-design.md §1 decision #1.
  return "en-US";
}
```

`getI18n` still threads `localeOverride` through `normalizeLocale`, so
the `[lang]/docs` Nextra route's `lang` URL param still works for `en`.
But Nextra after step 3.2 only offers `en` anyway.

`setLocale` is left untouched — writing to a `locale` cookie is now a
no-op given the new detector, but removing the function would require
finding and updating every caller in language-switcher UIs. **YAGNI:
the function is harmless dead-write.**

### 3.2 Nextra language switcher

`app/[lang]/docs/layout.tsx:9-16` currently:

```ts
const i18n = {
  locales: [
    { locale: "en", name: "English" },
    { locale: "zh", name: "中文" },
  ],
};
```

After:

```ts
const i18n = {
  locales: [{ locale: "en", name: "English" }],
};
```

This removes the `zh` button from the docs page language switcher.

### 3.3 `/zh/*` → `/en/*` redirect

Add (or extend) `frontend/middleware.ts`:

```ts
import { NextResponse, type NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname.startsWith("/zh/") || pathname === "/zh") {
    const target = pathname.replace(/^\/zh(\/|$)/, "/en$1");
    return NextResponse.redirect(new URL(target, req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/zh/:path*", "/zh"],
};
```

If a `middleware.ts` already exists at the same path, **merge** the
redirect logic into the existing handler rather than overwriting.
Implementation step 0 must check.

### 3.4 Delete `content/zh/`

```bash
git rm -r frontend/src/content/zh/
```

Nextra reads MDX from `content/<locale>/` so removing `content/zh/`
combined with step 3.2 eliminates the Chinese docs route surface
entirely. After deletion, any leftover `/zh/docs/*` URL hits the
middleware redirect from 3.3.

### 3.5 `citation-link.tsx` fallback cleanup

`frontend/src/components/workspace/citations/citation-link.tsx:24`:

```ts
// Before
const isGenericText = childrenText === "Source" || childrenText === "来源";

// After
const isGenericText = childrenText === "Source";
```

Under Path A the `childrenText` is always the English label, so the
Chinese branch is dead code. Removing it improves readability.

### 3.6 `火山方舟` → `Volcengine Ark`

`frontend/src/content/en/reference/model-providers/_meta.ts:5`:

```ts
// Before
"ark": { title: "火山方舟" },

// After
"ark": { title: "Volcengine Ark" },
```

The Chinese `_meta.ts` (under `content/zh/`) keeps `"火山方舟"` — but
since we're deleting that whole tree in step 3.4, this is moot.

---

## 4. Implementation Order

1. **Audit + safety check** — confirm no component imports from `content/zh/` (sanity grep) and confirm whether `frontend/middleware.ts` already exists.
2. **server.ts clamp** — single change, no other dependencies.
3. **citation-link.tsx + en `_meta.ts`** — two unrelated user-visible fixes; commit together.
4. **Nextra switcher + middleware redirect** — pair these so the docs route surface is consistent in one commit.
5. **Delete `content/zh/`** — its own commit so the diff stat is legible.
6. **Final verification** — `pnpm typecheck` + `pnpm lint` + `pnpm build` (build is the gate; Nextra build picks up missing `content/zh/` and must still succeed).

These five steps become five task families in the implementation plan.

---

## 5. Verification Plan

After server deploy + hard refresh:

| Check | Method | Expected |
|------|--------|----------|
| Landing page header reads "Docs" not "文档" under Chinese-locale Chrome | Set Chrome `chrome://settings/languages` Chinese first | English |
| Workspace shell (sidebar "New Chat" etc) reads English | Same Chrome | English |
| `/zh/docs/introduction/getting-started` → `/en/docs/introduction/getting-started` | Direct URL access | 307 redirect |
| `/zh/docs` (no path) → `/en/docs` | Direct URL access | 307 redirect |
| `/en/docs/reference/model-providers/ark` page title | Browser tab + page content | "Volcengine Ark" |
| Workspace citation link with `>` chevron renders the English "Source" label | Trigger a citation in a thread | "Source", no "来源" anywhere |
| `pnpm build` succeeds with `content/zh/` deleted | CI build | Exit 0 |

---

## 6. Risks and Mitigations

| Risk | P × I | Mitigation |
|------|:-----:|------------|
| Nextra config still references the deleted `zh` locale somewhere → build fail | M × M | Step 3.2 removes the `i18n.locales` `zh` entry; if Nextra config is duplicated elsewhere, `pnpm build` will surface it before commit |
| Browser still sends `Cookie: locale=zh-CN` from old sessions | M × L | server.ts ignores the cookie now; cookie ages out naturally, or user can clear |
| A stale `setLocale("zh-CN")` call from a language-switcher UI persists in code | L × L | `setLocale` is left as dead-write; cookies it sets are ignored by `detectLocaleServer` |
| Nextra `[lang]/docs/[[...slug]]/page.tsx` requires `lang` param values list including zh for static-param generation | M × L | After 3.2 the `i18n.locales` array only contains `en`, so SSG only generates `/en/docs/*`. If any `generateStaticParams` is hard-coded with `zh`, it must be updated — implementation must grep for `lang.*zh` |
| Some component still hardcodes `useI18n("zh-CN")` or similar | L × L | The i18n hook reads from the provider, which reads from `detectLocaleServer`. No client-side override exists in current codebase (verified via grep before implementing) |
| `middleware.ts` already exists and conflicts | M × L | Step 1 (audit) checks; if it exists, the redirect handler merges into the existing flow |

---

## 7. Out-of-Scope (Future Considerations)

- **Re-enabling bilingual UI**: trivial — revert step 3.1 (one-line change) and `zh-CN.ts` is still on disk. Re-adding `zh` to Nextra requires restoring `content/zh/` from git history (we won't `git rm --cached`, the deletion is a real delete recoverable via `git show <pre-commit>:content/zh/...`).
- **Translating Chinese developer comments**: the parallel agent's notes on LangGraph streaming edge cases are technical documentation in the wrong language; useful future cleanup but not gated on this PR.
- **Removing the `zh-CN.ts` translation table**: deletes 309 lines but takes away the easy revert path. YAGNI until a maintenance pass.
- **Removing `[lang]` from the docs route entirely**: a deeper refactor that would move `app/[lang]/docs/*` to `app/docs/*`. Out of scope for the May 14 defence deadline.
