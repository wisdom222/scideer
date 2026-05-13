# Semantic Scholar MCP Server — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. **Stop and request review at the 3 checkpoints marked `🛑 STOP`.**

**Goal:** Build a stdio MCP server exposing 3 Semantic Scholar tools (search / get_paper / get_citations) to Libra agents.

**Architecture:** Single-file `server.py` (~280 LOC) using `mcp[cli]` FastMCP + `httpx`. Sliding-window rate limiter + in-memory TTL LRU cache + paper-id normalization + retry-on-5xx. All tools return markdown strings; all exceptions caught and converted to error markdown to prevent stdio subprocess death.

**Tech Stack:** Python 3.12, `mcp[cli]>=1.2.0`, `httpx>=0.27`, hatchling.

**Reference:** [2026-05-14-semantic-scholar-mcp-design.md](2026-05-14-semantic-scholar-mcp-design.md)

**YAGNI overrides default TDD:** This MCP is not a graded benchmark target nor part of the core demo path. Per design Section 1, no pytest tests. Verification is manual smoke tests documented in README + 3 stop checkpoints.

**Hard rules (from CLAUDE.md):**
- Never `git commit` / `git push` / `git branch` unless user explicitly asks.
- Don't touch `frontend/`, `backend/` (except no — `extensions_config.example.json` is project root, allowed), `agents/`, `benchmarks/`, `docker/`, or other `skills/` / `mcp_servers/` directories.
- Don't modify `config.yaml`.

---

## Task 1: Scaffold package layout + pyproject.toml

**Files:**
- Create: `mcp_servers/semantic-scholar/pyproject.toml`
- Create: `mcp_servers/semantic-scholar/semantic_scholar_mcp/__init__.py` (empty)
- Create: `mcp_servers/semantic-scholar/semantic_scholar_mcp/__main__.py`

**Step 1: Create directories**

Use the Write tool — it creates parents automatically.

**Step 2: Write `pyproject.toml`**

```toml
[project]
name = "semantic-scholar-mcp"
version = "0.1.0"
description = "Semantic Scholar MCP server for SciDeer / Libra"
requires-python = ">=3.12"
dependencies = [
  "mcp[cli]>=1.2.0",
  "httpx>=0.27",
]

[project.scripts]
semantic-scholar-mcp = "semantic_scholar_mcp.server:main"

[tool.hatch.build.targets.wheel]
packages = ["semantic_scholar_mcp"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 3: Write `__init__.py`**

Empty file (0 bytes).

**Step 4: Write `__main__.py`**

```python
"""Package entry-point for `python -m semantic_scholar_mcp`."""
from semantic_scholar_mcp.server import main

if __name__ == "__main__":
    main()
```

**Acceptance:** `ls mcp_servers/semantic-scholar/` shows `pyproject.toml`, `semantic_scholar_mcp/` and inside `__init__.py`, `__main__.py`.

---

## Task 2: Write server.py — full single-file implementation

**Files:**
- Create: `mcp_servers/semantic-scholar/semantic_scholar_mcp/server.py`

**Step 1: Write the complete file**

```python
"""Semantic Scholar MCP server — stdio transport, 3 tools.

Provides arXiv-beyond paper search, paper detail, and citation graph traversal
for SciDeer / Libra agents. Free Semantic Scholar tier — no API key required.
"""
from __future__ import annotations

import asyncio
import re
import sys
import time
from collections import OrderedDict, deque
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

S2_BASE = "https://api.semanticscholar.org/graph/v1"
HTTP_TIMEOUT = 30.0
MAX_REFERENCES_IN_OUTPUT = 20
RATE_LIMIT_MAX_CALLS = 100
RATE_LIMIT_WINDOW_SEC = 300
CACHE_MAX_ENTRIES = 256
CACHE_TTL_SEC = 3600
RETRY_MAX = 3

SEARCH_FIELDS = "title,authors,year,abstract,citationCount,externalIds"
PAPER_FIELDS = (
    "title,authors,year,abstract,citationCount,referenceCount,"
    "influentialCitationCount,externalIds,"
    "references.title,references.year,references.citationCount,references.externalIds"
)
CITATIONS_FIELDS = "title,year,authors,citationCount,externalIds"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class S2Error(Exception):
    """Base class — never raised past the tool boundary."""


class S2ClientError(S2Error):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body


class S2ServerError(S2Error):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body


class S2NetworkError(S2Error):
    pass


# ---------------------------------------------------------------------------
# Paper-id normalization
# ---------------------------------------------------------------------------

_PREFIX_RE = re.compile(r"^(ARXIV|DOI|MAG|ACL|PMID|PMCID|CORPUSID|URL):", re.IGNORECASE)
_NEW_ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
_OLD_ARXIV_RE = re.compile(r"^[a-z\-]+/\d{7}$")
_DOI_RE = re.compile(r"^10\.\d{4,}/\S+$")
_S2_HASH_RE = re.compile(r"^[0-9a-f]{40}$")


def _normalize_paper_id(raw: str) -> str:
    """Coerce common paper-id formats into S2-prefixed syntax."""
    raw = raw.strip()
    if not raw:
        return raw

    m = _PREFIX_RE.match(raw)
    if m:
        prefix = m.group(1).upper()
        if prefix == "CORPUSID":
            prefix = "CorpusId"
        return f"{prefix}:{raw[m.end():]}"

    if _NEW_ARXIV_RE.match(raw):
        no_version = re.sub(r"v\d+$", "", raw)
        return f"ARXIV:{no_version}"

    if _OLD_ARXIV_RE.match(raw):
        return f"ARXIV:{raw}"

    if _DOI_RE.match(raw):
        return f"DOI:{raw}"

    if _S2_HASH_RE.match(raw):
        return raw

    return raw


# ---------------------------------------------------------------------------
# Sliding-window rate limiter
# ---------------------------------------------------------------------------

class SlidingWindowLimiter:
    def __init__(self, max_calls: int = RATE_LIMIT_MAX_CALLS, window_seconds: int = RATE_LIMIT_WINDOW_SEC) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] > self._window:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max:
                    self._timestamps.append(now)
                    return
                wait_for = self._window - (now - self._timestamps[0]) + 0.1
            print(f"[s2-mcp] rate-limit: sleeping {wait_for:.1f}s", file=sys.stderr)
            await asyncio.sleep(wait_for)


# ---------------------------------------------------------------------------
# TTL LRU cache
# ---------------------------------------------------------------------------

class TTLCache:
    def __init__(self, maxsize: int = CACHE_MAX_ENTRIES, ttl: float = CACHE_TTL_SEC) -> None:
        self._maxsize = maxsize
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[str, float]] = OrderedDict()

    def get(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None
        value, expires_at = item
        if time.monotonic() > expires_at:
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value: str) -> None:
        self._data[key] = (value, time.monotonic() + self._ttl)
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)


# ---------------------------------------------------------------------------
# HTTP helpers with retry
# ---------------------------------------------------------------------------

_limiter = SlidingWindowLimiter()
_cache = TTLCache()


async def _request_with_retry(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict[str, Any]:
    last_err: S2Error | None = None
    for attempt in range(RETRY_MAX + 1):
        try:
            await _limiter.acquire()
            resp = await client.get(url, params=params, timeout=HTTP_TIMEOUT)
            if resp.status_code < 400:
                return resp.json()
            if 400 <= resp.status_code < 500:
                raise S2ClientError(resp.status_code, resp.text[:500])
            last_err = S2ServerError(resp.status_code, resp.text[:200])
        except S2ClientError:
            raise
        except (httpx.NetworkError, httpx.TimeoutException) as e:
            last_err = S2NetworkError(str(e))
        if attempt < RETRY_MAX:
            await asyncio.sleep(2 ** attempt)
    assert last_err is not None
    raise last_err


# ---------------------------------------------------------------------------
# Markdown formatters
# ---------------------------------------------------------------------------

def _authors_line(authors: list[dict[str, Any]] | None) -> str:
    if not authors:
        return "Unknown"
    names = [a.get("name", "?") for a in authors]
    if len(names) > 6:
        return ", ".join(names[:6]) + f", … (+{len(names) - 6} more)"
    return ", ".join(names)


def _external_id(externals: dict[str, Any] | None, key: str) -> str:
    if not externals:
        return "N/A"
    val = externals.get(key)
    return val if val else "N/A"


def _truncate_abstract(text: str | None, limit: int = 300) -> str:
    if not text:
        return "_(no abstract)_"
    text = text.strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _format_search_paper(idx: int, paper: dict[str, Any]) -> str:
    return (
        f"## {idx}. {paper.get('title', 'Untitled')}\n"
        f"- **Paper ID:** `{paper.get('paperId', '?')}`\n"
        f"- **Authors:** {_authors_line(paper.get('authors'))}\n"
        f"- **Year:** {paper.get('year', 'N/A')} · **Citations:** {paper.get('citationCount', 0)}\n"
        f"- **arXiv:** {_external_id(paper.get('externalIds'), 'ArXiv')}\n\n"
        f"> {_truncate_abstract(paper.get('abstract'))}\n"
    )


def _format_reference(idx: int, ref: dict[str, Any]) -> str:
    return (
        f"{idx}. **{ref.get('title', 'Untitled')}** "
        f"({ref.get('year', 'N/A')}) · {ref.get('citationCount', 0)} citations"
    )


def _format_citation(idx: int, citing_wrap: dict[str, Any]) -> str:
    paper = citing_wrap.get("citingPaper", {})
    return (
        f"## {idx}. {paper.get('title', 'Untitled')} ({paper.get('year', 'N/A')}) · "
        f"{paper.get('citationCount', 0)} citations\n"
        f"- **Authors:** {_authors_line(paper.get('authors'))}\n"
        f"- **Paper ID:** `{paper.get('paperId', '?')}`\n"
        f"- **arXiv:** {_external_id(paper.get('externalIds'), 'ArXiv')}\n"
    )


def _format_error(tool: str, exc: S2Error, user_input: str) -> str:
    if isinstance(exc, S2ClientError):
        reason = f"Paper not found (HTTP {exc.status})" if exc.status == 404 else f"Client error (HTTP {exc.status})"
        if exc.status == 404:
            hint = "Check the arXiv/DOI/paper ID format or try searching by title first."
        elif exc.status == 400:
            hint = "Invalid paper ID format. Use a raw arXiv ID (e.g. 1609.02907), a DOI, or a 40-char S2 paper hash."
        elif exc.status == 429:
            hint = "Semantic Scholar rate limit exceeded despite local throttling. Retry in a few minutes."
        else:
            hint = "Inspect the input and retry."
    elif isinstance(exc, S2ServerError):
        reason = f"Server error (HTTP {exc.status}) after {RETRY_MAX} retries"
        hint = "Semantic Scholar service is currently unavailable. Try again later."
    elif isinstance(exc, S2NetworkError):
        reason = f"Network error: {exc}"
        hint = "Network error reaching Semantic Scholar. Check connectivity."
    else:
        reason = f"Unknown error: {exc}"
        hint = "Report this as a bug."
    return (
        f"# Semantic Scholar Error\n\n"
        f"**Tool:** {tool}\n"
        f"**Reason:** {reason}\n"
        f"**Input:** `{user_input}`\n\n"
        f"Hint: {hint}\n"
    )


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = FastMCP("semantic-scholar")


@mcp.tool()
async def semantic_scholar_search(query: str, limit: int = 10) -> str:
    """Search papers across Semantic Scholar's corpus (Beyond arXiv).

    Args:
        query: Free-text search query, e.g. "graph neural networks".
        limit: Number of papers to return (1-100, default 10).

    Returns:
        Markdown-formatted list of matching papers.
    """
    limit = max(1, min(100, limit))
    cache_key = f"search:{query}:{limit}"
    if cached := _cache.get(cache_key):
        return cached
    try:
        async with httpx.AsyncClient() as client:
            data = await _request_with_retry(
                client,
                f"{S2_BASE}/paper/search",
                {"query": query, "limit": limit, "fields": SEARCH_FIELDS},
            )
        papers = data.get("data", [])
        total = data.get("total", len(papers))
        if not papers:
            result = f"# Search results for \"{query}\"\n\nNo papers found.\n"
        else:
            blocks = [_format_search_paper(i + 1, p) for i, p in enumerate(papers)]
            result = (
                f"# Search results for \"{query}\"\n\n"
                f"Found {total} papers (showing top {len(papers)})\n\n"
                f"---\n\n"
                + "\n---\n\n".join(blocks)
            )
        _cache.set(cache_key, result)
        return result
    except S2Error as e:
        return _format_error("semantic_scholar_search", e, query)
    except Exception as e:
        return _format_error("semantic_scholar_search", S2NetworkError(str(e)), query)


@mcp.tool()
async def semantic_scholar_get_paper(paper_id: str) -> str:
    """Get a paper's full metadata + reference list.

    Args:
        paper_id: Accepts raw arXiv ID (1609.02907), DOI (10.x/y), S2 hash, or
                  any S2-prefixed form (ARXIV:..., DOI:..., MAG:..., etc.).

    Returns:
        Markdown-formatted paper details with up to 20 top-cited references.
    """
    normalized = _normalize_paper_id(paper_id)
    cache_key = f"paper:{normalized}"
    if cached := _cache.get(cache_key):
        return cached
    try:
        async with httpx.AsyncClient() as client:
            data = await _request_with_retry(
                client,
                f"{S2_BASE}/paper/{normalized}",
                {"fields": PAPER_FIELDS},
            )
        externals = data.get("externalIds") or {}
        refs = data.get("references") or []
        refs_sorted = sorted(refs, key=lambda r: r.get("citationCount") or 0, reverse=True)
        top_refs = refs_sorted[:MAX_REFERENCES_IN_OUTPUT]
        refs_block = (
            "\n".join(_format_reference(i + 1, r) for i, r in enumerate(top_refs))
            if top_refs
            else "_(no references available)_"
        )
        result = (
            f"# Paper Details\n\n"
            f"## {data.get('title', 'Untitled')}\n"
            f"- **Paper ID:** `{data.get('paperId', normalized)}`\n"
            f"- **Authors:** {_authors_line(data.get('authors'))}\n"
            f"- **Year:** {data.get('year', 'N/A')}\n"
            f"- **arXiv:** {_external_id(externals, 'ArXiv')} · "
            f"**DOI:** {_external_id(externals, 'DOI')}\n"
            f"- **Citations:** {data.get('citationCount', 0)} "
            f"(Influential: {data.get('influentialCitationCount', 0)}) · "
            f"**References:** {data.get('referenceCount', 0)}\n\n"
            f"### Abstract\n"
            f"> {_truncate_abstract(data.get('abstract'), limit=2000)}\n\n"
            f"### References (top {min(len(top_refs), MAX_REFERENCES_IN_OUTPUT)} by citation count)\n"
            f"{refs_block}\n"
        )
        _cache.set(cache_key, result)
        return result
    except S2Error as e:
        return _format_error("semantic_scholar_get_paper", e, paper_id)
    except Exception as e:
        return _format_error("semantic_scholar_get_paper", S2NetworkError(str(e)), paper_id)


@mcp.tool()
async def semantic_scholar_get_citations(paper_id: str, limit: int = 20) -> str:
    """Get follow-up papers that cite the given paper, sorted by citationCount.

    Args:
        paper_id: Same id formats as semantic_scholar_get_paper.
        limit: Number of citing papers to return after sorting (1-100, default 20).

    Returns:
        Markdown list of top-cited follow-ups.
    """
    limit = max(1, min(100, limit))
    normalized = _normalize_paper_id(paper_id)
    cache_key = f"citations:{normalized}:{limit}"
    if cached := _cache.get(cache_key):
        return cached
    try:
        async with httpx.AsyncClient() as client:
            fetch = min(100, limit * 3)
            data = await _request_with_retry(
                client,
                f"{S2_BASE}/paper/{normalized}/citations",
                {"fields": CITATIONS_FIELDS, "limit": fetch},
            )
        citations = data.get("data") or []
        if not citations:
            result = f"# Papers citing `{normalized}`\n\nNo citing papers found.\n"
        else:
            citations_sorted = sorted(
                citations,
                key=lambda c: (c.get("citingPaper") or {}).get("citationCount") or 0,
                reverse=True,
            )[:limit]
            arxiv = _external_id((citations_sorted[0].get("citingPaper") or {}).get("externalIds"), "ArXiv")
            header_id = f"arxiv:{arxiv}" if arxiv != "N/A" else normalized
            blocks = [_format_citation(i + 1, c) for i, c in enumerate(citations_sorted)]
            result = (
                f"# Papers citing `{normalized}`\n\n"
                f"Top {len(citations_sorted)} most-cited follow-up papers "
                f"(of {len(citations)} fetched):\n\n"
                f"---\n\n"
                + "\n---\n\n".join(blocks)
            )
        _cache.set(cache_key, result)
        return result
    except S2Error as e:
        return _format_error("semantic_scholar_get_citations", e, paper_id)
    except Exception as e:
        return _format_error("semantic_scholar_get_citations", S2NetworkError(str(e)), paper_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server over stdio."""
    print("[s2-mcp] starting Semantic Scholar MCP server (stdio)", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
```

**Step 2: Sanity-check imports (no run yet)**

Run: `python -c "import ast; ast.parse(open('mcp_servers/semantic-scholar/semantic_scholar_mcp/server.py').read())"`
Expected: no output, exit 0 (syntax OK).

**Acceptance:** `server.py` exists, parses cleanly, all 3 `@mcp.tool()` decorators present.

### 🛑 STOP — Checkpoint 1: server.py written, before install

Tell the user: "server.py done. Ready to install and smoke-test. Proceed?"

---

## Task 3: Install + stdio smoke test (verify server boots)

**Files:** None modified, only run commands.

**Step 1: Install the package into DeerFlow's venv**

Run: `cd D:/6725_GroupProject/scideer && uv pip install -e mcp_servers/semantic-scholar`
Expected: `Installed 1 package: semantic-scholar-mcp` (or similar), exit 0.

**Step 2: Stdio smoke test — list_tools**

Create a temporary file `/tmp/s2_smoke.txt` (or `$TEMP/s2_smoke.txt` on Windows) with:
```
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

Run: `python -m semantic_scholar_mcp < /tmp/s2_smoke.txt`
(Windows bash equivalent: `python -m semantic_scholar_mcp < "$TEMP/s2_smoke.txt"`)

Expected stdout: JSON-RPC responses including a `tools/list` result with 3 tool names: `semantic_scholar_search`, `semantic_scholar_get_paper`, `semantic_scholar_get_citations`.
Expected stderr: `[s2-mcp] starting Semantic Scholar MCP server (stdio)`.

**Acceptance:** All 3 tool names appear in JSON-RPC response.

If smoke test fails: report stderr verbatim to the user before continuing.

---

## Task 4: Live API verification (3 happy-path + 2 error-path)

**Files:** None modified; ad-hoc Python REPL or temp script.

**Step 1: Write a one-shot tester `/tmp/s2_check.py`** (delete after)

```python
import asyncio
from semantic_scholar_mcp.server import (
    semantic_scholar_search,
    semantic_scholar_get_paper,
    semantic_scholar_get_citations,
)

async def main():
    print("=== Test 1: search ===")
    print((await semantic_scholar_search.fn("graph neural networks", limit=3))[:600])
    print("\n=== Test 2: get_paper (GCN) ===")
    print((await semantic_scholar_get_paper.fn("1609.02907"))[:600])
    print("\n=== Test 3: get_citations (GCN) ===")
    print((await semantic_scholar_get_citations.fn("ARXIV:1609.02907", limit=5))[:600])
    print("\n=== Test 4: 404 error ===")
    print(await semantic_scholar_get_paper.fn("ARXIV:9999.99999"))
    print("\n=== Test 5: bad id ===")
    print(await semantic_scholar_get_paper.fn("not-an-id"))

asyncio.run(main())
```

Note: `@mcp.tool()`-decorated functions are accessed via `.fn` attribute to bypass MCP wrapping in direct calls.

**Step 2: Run the tester**

Run: `python /tmp/s2_check.py`
Expected:
- Test 1: 3 papers, GCN likely #1 with ≥25 000 citations.
- Test 2: GCN paper title, citations ≥ 25 000, references section present.
- Test 3: Includes "Graph Attention Networks" or "GraphSAGE" in top 5.
- Test 4: `# Semantic Scholar Error` markdown, HTTP 404, hint present.
- Test 5: Either 404 or 400 markdown, no Python traceback.

**Step 3: Delete tester**

Run: `rm /tmp/s2_check.py`

**Step 4: Report to user**

Tell the user: "Live API verification passed. All 5 cases behave correctly."

**Acceptance:** No Python traceback in any of the 5 cases. Every output starts with `#` (valid markdown).

If `.fn` accessor pattern fails (FastMCP API change), fall back to calling the underlying async function directly — read `mcp[cli]` docs to find the right accessor for the installed version.

---

## Task 5: Modify extensions_config.example.json

**Files:**
- Modify: `extensions_config.example.json` (project root)

### 🛑 STOP — Checkpoint 2: before modifying extensions_config.example.json

Tell the user: "Live tests passed. About to edit extensions_config.example.json to add the semantic-scholar entry. Proceed?"

**Step 1: Read the current file** (already known: has `filesystem`, `github`, `postgres`, all `enabled: false`).

**Step 2: Use Edit tool to insert after the `postgres` block**

Locate the `postgres` block close:
```json
    "postgres": {
      ...
      "description": "PostgreSQL database access"
    }
  },
  "skills": {}
```

Replace with:
```json
    "postgres": {
      ...
      "description": "PostgreSQL database access"
    },
    "semantic-scholar": {
      "enabled": true,
      "type": "stdio",
      "command": "python",
      "args": ["-m", "semantic_scholar_mcp"],
      "env": {},
      "description": "Semantic Scholar paper search + citation graph (free tier, no API key required). Provides arXiv-beyond paper search, paper detail with references, and citation graph traversal."
    }
  },
  "skills": {}
```

(Preserve the existing `postgres` content verbatim; only add the comma after its closing brace and append the new entry.)

**Step 3: Verify valid JSON**

Run: `python -c "import json; json.load(open('extensions_config.example.json'))"`
Expected: no output, exit 0.

**Acceptance:** File parses as JSON; `semantic-scholar` key present with `enabled: true`.

---

## Task 6: Write README.md

**Files:**
- Create: `mcp_servers/semantic-scholar/README.md`

**Step 1: Write README**

```markdown
# Semantic Scholar MCP Server

stdio MCP server exposing Semantic Scholar's free-tier paper search + citation
graph API to SciDeer / Libra agents. No API key required.

## Tools

| Tool | Description |
|---|---|
| `semantic_scholar_search(query, limit=10)` | Free-text paper search across S2's corpus |
| `semantic_scholar_get_paper(paper_id)` | Paper metadata + top-20 references |
| `semantic_scholar_get_citations(paper_id, limit=20)` | Follow-up papers sorted by citation count |

`paper_id` accepts: raw arXiv ID (`1609.02907`), DOI (`10.x/y`), 40-char S2
hash, or any S2-prefixed form (`ARXIV:...`, `DOI:...`, `MAG:...`, etc.).
All tools return markdown strings.

## Install (server-side)

```bash
cd /path/to/scideer
uv pip install -e mcp_servers/semantic-scholar
```

## Enable in DeerFlow

If `extensions_config.json` doesn't exist yet:

```bash
cp extensions_config.example.json extensions_config.json
```

If it exists, manually merge the `semantic-scholar` entry from
`extensions_config.example.json` into your `extensions_config.json` under
`mcpServers`.

Then restart DeerFlow:

```bash
bash scripts/serve.sh --restart --dev --daemon
```

## Verify

### Stdio smoke test (no API call)

```bash
python -m semantic_scholar_mcp <<EOF
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
EOF
```
Expected: response lists 3 tools.

### Live API check (real Semantic Scholar calls)

```python
import asyncio
from semantic_scholar_mcp.server import (
    semantic_scholar_search,
    semantic_scholar_get_paper,
    semantic_scholar_get_citations,
)

async def check():
    print(await semantic_scholar_search.fn("graph neural networks", limit=3))
    print(await semantic_scholar_get_paper.fn("ARXIV:1609.02907"))
    print(await semantic_scholar_get_citations.fn("ARXIV:1609.02907", limit=5))

asyncio.run(check())
```

### End-to-end via Web UI

After restart, ask Libra:

> Show me the most cited follow-up papers of arxiv:1609.02907

Expected: the agent calls `semantic_scholar_get_citations` and presents a
sorted list of follow-up papers (Graph Attention Networks etc.) at the top.

## Design constraints

- Free tier: 100 calls / 5 min — enforced via in-process sliding-window limiter.
- In-memory LRU cache (256 entries, 1 h TTL) per stdio subprocess.
- 5xx retries up to 3 times with exponential backoff (1s, 2s, 4s).
- 4xx errors fail fast and are converted to markdown error responses.
- All exceptions caught at tool boundary — the subprocess never dies mid-call.

## Files

```
mcp_servers/semantic-scholar/
├── pyproject.toml
├── README.md                          ← this file
└── semantic_scholar_mcp/
    ├── __init__.py
    ├── __main__.py                    ← python -m entry-point
    └── server.py                      ← main logic
```

## Out of scope

- API key support (paid tier)
- Disk cache
- Author / recommendation endpoints

See [docs/plans/2026-05-14-semantic-scholar-mcp-design.md](../../docs/plans/2026-05-14-semantic-scholar-mcp-design.md) for full design.
```

**Acceptance:** README contains install + enable + restart + 2 verification methods.

---

## Task 7: Final pre-push review

### 🛑 STOP — Checkpoint 3: before any git operation

**Files inventory check:**

Run: `ls mcp_servers/semantic-scholar/ mcp_servers/semantic-scholar/semantic_scholar_mcp/`
Expected:
```
mcp_servers/semantic-scholar/:
README.md  pyproject.toml  semantic_scholar_mcp/

mcp_servers/semantic-scholar/semantic_scholar_mcp/:
__init__.py  __main__.py  server.py
```

Run: `git status -sb`
Expected (modulo the 2 pre-existing untracked plan files):
```
## scideer-main...origin/scideer-main [ahead 2]
 M extensions_config.example.json
?? docs/plans/2026-05-14-semantic-scholar-mcp-design.md
?? docs/plans/2026-05-14-semantic-scholar-mcp-implementation.md
?? mcp_servers/
```

**Boundary verification (CLAUDE.md hard rule):**

Run: `git status -sb | grep -E "^[ AM\?]+ (frontend|backend|agents|benchmarks|docker|skills|config.yaml)" || echo "BOUNDARY OK"`
Expected: `BOUNDARY OK`.

If anything outside `mcp_servers/`, `extensions_config.example.json`, or `docs/plans/2026-05-14-*` shows up — STOP and report to user.

**Tell the user:** "All work complete. Files: pyproject.toml, __init__.py, __main__.py, server.py, README.md, extensions_config.example.json (modified), 2 plan docs. Ready for your review and your `git add` / `git commit` / `git push` decision."

**Do NOT run `git add`, `git commit`, or `git push` autonomously.** Wait for explicit user instruction.

---

## Done. Expected total time

~25 minutes (Tasks 1-6) + checkpoints.

## Recovery: what to do if a checkpoint test fails

| Failure | Action |
|---|---|
| `uv pip install -e` errors | Read error stderr; common cause: missing build-backend → verify `[build-system]` in pyproject.toml |
| `python -m semantic_scholar_mcp` fails with `ModuleNotFoundError` | Reinstall with `-e` flag; ensure cwd doesn't matter (entry from site-packages) |
| Live API returns empty data | Check `httpx` connectivity; S2 API rarely fails — try one more time |
| `.fn` accessor not available | Read `from mcp.server.fastmcp import FastMCP` source for the right accessor; fall back to extracting the function via tool registry |
| 4xx on `ARXIV:1609.02907` | Normalization bug; print `_normalize_paper_id('1609.02907')` to diagnose |
