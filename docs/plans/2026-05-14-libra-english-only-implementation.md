# Libra English-Only UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Force the Libra frontend to render in English under any browser locale, delete the Nextra `/zh/docs` content tree with a `/zh/* → /en/*` redirect, and fix two user-visible Chinese leaks — all without disturbing the i18n framework's structure or component-side `t.xxx.yyy` references.

**Architecture:** Five bite-sized task families. The first is a no-commit audit step that confirms three assumptions from the design (`middleware.ts` doesn't exist, no cross-tree imports of `content/zh/`, no hardcoded `zh` in `generateStaticParams`). The remaining four are commit-bounded changes mapping 1:1 to design §4. Each commit boundary is a natural pause point for user review per the existing workflow rule.

**Tech Stack:** Next.js 16 (App Router), Nextra 4 (MDX docs), TypeScript 5.8. Single shell: Git Bash on Windows.

---

## Source Design

Implements [2026-05-14-libra-english-only-design.md](2026-05-14-libra-english-only-design.md).
When a code detail is ambiguous, re-read that doc — do not improvise.

## Hard Rules

1. **No git push** — every task family commits locally. Push is the user's call; the plan stops after Task Family 5's commit.
2. **No `--no-verify`** — pre-commit hooks must pass; fix root causes rather than skip.
3. **No edits outside the IN-scope list in design §2** — if something else seems to need a touch, stop and ask.
4. **Do NOT delete `frontend/src/core/i18n/locales/zh-CN.ts`** — the design explicitly keeps it dormant as a one-revert path.
5. **Do NOT translate Chinese developer comments** in `utils.ts`, `message-group.tsx`, `message-list.tsx`, etc. — explicitly out of scope.
6. **Do NOT touch `README_zh.md`** — kept by design.
7. **`_reference/deer-flow/` is read-only** — only edit inside `scideer/`.
8. Run `pnpm typecheck` + `pnpm lint` at the end of each editing task family before committing; `pnpm build` runs only at the end of Task Family 5 (the final gate).
9. Use the **tempfile + `git commit -F`** pattern for every commit (HEREDOC has bitten this project on Windows Git Bash).

## Working Directory

All `pnpm` commands run from `frontend/`. All `git` commands run from `scideer/`. Use forward slashes; on Windows Git Bash is the shell.

## Verification Strategy

This is a mix of config edits (server.ts, layout.tsx, new middleware.ts) + content deletion (`content/zh/`). There are no meaningful unit tests for "the locale is clamped" beyond confirming the file content. Verification per task family:

1. **`pnpm typecheck`** — TypeScript compiles
2. **`pnpm lint`** — ESLint clean
3. **`pnpm build`** (only at TF5) — production Next.js build succeeds with `content/zh/` gone and middleware redirect in place
4. **Manual visual smoke** — the user does it after deploy (design §5)

---

## Task Family 1: Audit + safety checks (no commit)

**Goal:** Confirm three design assumptions before any edit. All three should already be true based on the brainstorming-stage audit, but verify in case anything has shifted.

### Task 1A: Confirm `middleware.ts` does not exist

**Step 1: Check for the file**

```bash
ls -la frontend/middleware.ts frontend/src/middleware.ts 2>&1
```
Expected: both `ls` invocations report "No such file or directory".

If a `middleware.ts` is found, **stop and report** — TF4's plan to create a fresh middleware would silently overwrite it. The user will tell you how to merge.

### Task 1B: Confirm no source file outside `content/zh/` imports from `content/zh/`

```
Grep tool: pattern="content/zh", path="frontend/src"
```
Expected: zero hits outside the `content/zh/` directory itself. (Files inside `content/zh/` may reference siblings — that's fine; we delete the whole tree.)

If hits are found in `frontend/src/components/` or `frontend/src/app/` (excluding `content/zh/`), **stop and report**.

### Task 1C: Confirm `generateStaticParams` does not hardcode `zh`

```
Grep tool: pattern="generateStaticParams", path="frontend/src/app"
Grep tool: pattern="zh.*[Ll]ocale|[Ll]ocale.*zh", path="frontend/src/app"
```
Expected: `generateStaticParams = generateStaticParamsFor("mdxPath")` (Nextra helper that reads the file tree), and **no** hardcoded locale strings.

If a hardcoded `zh` locale list is found in a `generateStaticParams`, **stop and report** — TF5's tree deletion would not eliminate the static-param entry by itself.

### Task 1D: Confirm no committed state changes

```bash
git status
```
Expected: clean working tree (untracked plan docs are fine), no staged or modified tracked files. If unexpected modifications exist, **stop and surface** rather than commit through them.

**No commit at the end of TF1.** This is a verification phase.

---

## Task Family 2: Clamp `detectLocaleServer` to en-US

**Goal:** Single-line change that defangs every Chinese-locale code path in the i18n framework.

### Task 2A: Edit `frontend/src/core/i18n/server.ts`

**Files:**
- Modify: `frontend/src/core/i18n/server.ts:6-18`

**Step 1: Read the file once**

Confirm the current `detectLocaleServer` body matches the BEFORE block in design §3.1.

**Step 2: Replace the function body**

Replace the entire `detectLocaleServer` function with:

```ts
export async function detectLocaleServer(): Promise<Locale> {
  // Locked to en-US for the PH6725 defence — see
  // docs/plans/2026-05-14-libra-english-only-design.md §1 decision #1.
  return "en-US";
}
```

The `cookies` import at top of file becomes unused. Remove that line too (`import { cookies } from "next/headers";` — verify via grep that no other function in the file calls `cookies()`).

`setLocale` is untouched — it still writes the cookie. That's a harmless no-op now and avoids hunting down every caller in language-switcher UI.

`getI18n` is untouched.

**Step 3: Verify**

From `frontend/`:
```
pnpm typecheck
pnpm lint
```
Both exit 0.

### Task 2B: Commit

Tempfile + `git commit -F`. Message:

```
feat(i18n): clamp detectLocaleServer to en-US

The PH6725 defence panel may include English-speaking reviewers, so the
UI must read English under any browser locale. Replace the
cookie+normalize flow with a literal "en-US" return so every code path
through getI18n() resolves to the English translation table, regardless
of cookie or browser-language headers.

Path A from docs/plans/2026-05-14-libra-english-only-design.md — keeps
the i18n framework intact (zh-CN.ts is dormant on disk; reverting this
one line restores bilingual UI in a single commit). setLocale is left
as a harmless no-op cookie write.

Refs docs/plans/2026-05-14-libra-english-only-design.md §3.1.
```

**Pause for user review** after commit. Surface the `git show` summary.

---

## Task Family 3: User-visible Chinese leaks

**Goal:** Fix two unrelated bugs that are user-visible regardless of i18n strategy. Bundled because each is a one-line tweak.

### Task 3A: Drop the `"来源"` fallback in `citation-link.tsx`

**Files:**
- Modify: `frontend/src/components/workspace/citations/citation-link.tsx:24`

**Step 1: Read line 24** to confirm current text.

**Step 2: Apply edit**

```ts
// Before
const isGenericText = childrenText === "Source" || childrenText === "来源";

// After
const isGenericText = childrenText === "Source";
```

Under Path A `childrenText` always resolves to the English label, so the Chinese branch is dead code.

### Task 3B: Rename `火山方舟` → `Volcengine Ark`

**Files:**
- Modify: `frontend/src/content/en/reference/model-providers/_meta.ts:5`

**Step 1: Read line 5**.

**Step 2: Apply edit**

```ts
// Before
"ark": { title: "火山方舟" },

// After
"ark": { title: "Volcengine Ark" },
```

The exact original syntax may differ slightly (could be `ark: ...` without quotes); preserve the surrounding object shape and only change the title string.

### Task 3C: Verify

```
pnpm typecheck
pnpm lint
```
Both exit 0.

### Task 3D: Commit

Tempfile + `git commit -F`. Message:

```
fix(workspace,docs): drop Chinese "来源" citation fallback and Volcengine Ark label

Two user-visible Chinese leaks the i18n clamp doesn't address by itself:

- citation-link.tsx compared rendered text against "来源" alongside
  "Source" to detect generic citation labels. Under Path A the Chinese
  branch is unreachable, so the dead || clause goes.

- The English docs tree had "火山方舟" hardcoded as the Ark model-
  provider page title (an oversight at translation time; the zh tree
  carried the same key). Translate to "Volcengine Ark" so /en/docs
  reads English end to end.

Refs docs/plans/2026-05-14-libra-english-only-design.md §3.5, §3.6.
```

**Pause for user review.**

---

## Task Family 4: Nextra switcher + `/zh/*` redirect

**Goal:** Remove the `zh` choice from the docs language switcher and create middleware that redirects any direct `/zh/*` URL access to its `/en/*` equivalent.

### Task 4A: Remove `zh` from the Nextra `i18n` array

**Files:**
- Modify: `frontend/src/app/[lang]/docs/layout.tsx:10-13`

**Step 1: Apply edit**

```ts
// Before
const i18n = [
  { locale: "en", name: "English" },
  { locale: "zh", name: "中文" },
];

// After
const i18n = [{ locale: "en", name: "English" }];
```

Only the `zh` entry is removed. The variable name `i18n` and the array form remain. The rest of `layout.tsx` (the `formatPageRoute` helper, `DocLayout` function, `Layout` JSX with `i18n={i18n}` prop) is unchanged.

### Task 4B: Create `frontend/middleware.ts`

**Files:**
- Create: `frontend/middleware.ts`

**Step 1: Write file content (exact)**

```ts
import { NextResponse, type NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (pathname === "/zh" || pathname.startsWith("/zh/")) {
    const target = pathname.replace(/^\/zh(\/|$)/, "/en$1") + search;
    return NextResponse.redirect(new URL(target, req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/zh", "/zh/:path*"],
};
```

Notes:
- Preserves the `?search` query string on redirect.
- The matcher tells Next.js to only invoke this middleware on `/zh*` paths — zero performance overhead on every other request.
- HTTP 307 redirect (Next.js default) — preserves HTTP method, browser warns on POST to `/zh/...` though POST is unlikely on a static docs route.

### Task 4C: Verify

From `frontend/`:
```
pnpm typecheck
pnpm lint
```
Both exit 0. (Build is held until TF5.)

### Task 4D: Commit

Tempfile + `git commit -F`. Message:

```
feat(docs): drop zh from Nextra switcher, redirect /zh/* to /en/*

Remove the "中文" entry from the Nextra docs language switcher in
app/[lang]/docs/layout.tsx so users can no longer click into the
Chinese docs tree.

Add frontend/middleware.ts to catch any direct /zh/* URL access (old
bookmarks, links from external pages) and 307-redirect to the matching
/en/* path. Matcher is scoped to /zh* so other routes pay zero cost.

Pairs with the content/zh/ deletion in the next commit.

Refs docs/plans/2026-05-14-libra-english-only-design.md §3.2, §3.3.
```

**Pause for user review.**

---

## Task Family 5: Delete `content/zh/` tree + final build gate

**Goal:** Remove the 44-file Chinese docs tree from disk and verify the whole change set compiles in production mode.

### Task 5A: `git rm -r` the Chinese docs

**Files:**
- Delete: `frontend/src/content/zh/` (entire directory tree, 44 files)

**Step 1: Confirm directory contents one more time**

```bash
ls frontend/src/content/zh/ | head -20
git ls-files frontend/src/content/zh/ | wc -l
```
Expected: directory exists, contains ~44 tracked files.

**Step 2: Remove the directory**

```bash
git rm -r frontend/src/content/zh/
```

This stages the deletion. Working-tree files are also removed.

**Step 3: Confirm**

```bash
ls frontend/src/content/zh/ 2>&1
git status
```
Expected: directory gone, `git status` shows ~44 `deleted:` entries staged.

### Task 5B: Final production build

This is the **only** `pnpm build` in the plan — the gate that confirms everything from TF2–TF5 composes correctly in production. Specifically validates:

- `[lang]/docs` route still SSGs for `lang=en` (Nextra-generated params)
- No build error from `i18n.locales` array now having only one entry
- Middleware compiles
- `Volcengine Ark` Mdx page renders

From `frontend/`:
```
pnpm typecheck
pnpm lint
pnpm build
```
All exit 0. If `pnpm build` fails:

- **Common cause**: Nextra config elsewhere referencing `zh` (unlikely — `app/[lang]/docs/layout.tsx` was the only known referent). Search via Grep, fix the offender, re-run.
- **`generateStaticParams` reports no params**: should not happen because `generateStaticParamsFor("mdxPath")` reads the file tree, and `content/en/` still has files. If it does happen, the cause is likely a Nextra cache; `rm -rf .next` and rebuild.
- **A docs page links to `/zh/...`**: middleware will redirect but during SSG the linker may flag broken links. The redirect doesn't break SSG; relative `/zh` references inside MDX would.

Report any build error in full and pause; do not commit on a failing build.

### Task 5C: Commit

Tempfile + `git commit -F`. Message:

```
chore(docs): delete content/zh tree

Companion to the previous commit. The /zh route is now switcher-less
and middleware-redirected to /en, so the 44 Chinese MDX files under
content/zh/ are dead weight in the build output.

Bookmarks pointing at /zh/docs/* are caught by the middleware and
redirected to the matching /en/docs/* page. If we ever want to revive
bilingual docs, restore from git history (this commit's parent).

Verified pnpm build exit 0 after deletion.

Refs docs/plans/2026-05-14-libra-english-only-design.md §3.4.
```

**Pause for user review.** This is the final task family commit.

---

## Final Steps After All Task Families

### Step F1: Confirm working tree state

From `scideer/`:
```
git status
git log --oneline -8
```

Expected: clean tracked files, 4 new commits ahead of `origin/scideer-main` (TF2, TF3, TF4, TF5 each one commit — TF1 was no-commit verification).

### Step F2: Report back to user

Surface:
- 4 commit summary
- `pnpm build` exit code from TF5B
- The push command the user can authorise: `git push origin scideer-main`
- Server-side pull + restart command sequence (same pattern as previous rounds)

### Step F3: DO NOT PUSH WITHOUT EXPLICIT GO-AHEAD

`git push` is a user-authorised step per the project's hard rules and the workflow brief. Stop after Step F2 and wait.

---

## Skill References

- @superpowers:executing-plans — drives this plan task-by-task
- @superpowers:systematic-debugging — if `pnpm build` fails unexpectedly in TF5B
- @superpowers:verification-before-completion — required before claiming any task family done

## Risks Recap (from design §6)

| Risk | Where it bites in this plan | Pre-empted by |
|------|-----------------------------|---------------|
| Nextra references `zh` elsewhere | TF5B `pnpm build` | Build gate catches it before commit |
| Middleware overwrites existing file | TF1A safety check | We confirmed `frontend/middleware.ts` does not exist |
| `generateStaticParams` hardcodes `zh` | TF1C safety check | We confirmed the generator is the Nextra `generateStaticParamsFor("mdxPath")` helper that reads the file tree |
| Component imports from `content/zh/` | TF1B safety check | We confirmed via Grep — zero hits outside `content/zh/` itself |
| Stale `locale=zh-CN` cookie in user browsers | TF2 server.ts clamp | Detector ignores cookie now; old cookies age out |
| Pre-commit hook fails on any commit | Every commit step | Investigate root cause; do not `--no-verify` |
