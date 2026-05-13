# Semantic Scholar MCP Server — Design Document

> SciDeer / Libra component
> Date: 2026-05-14
> Status: Approved through brainstorming Sections 1-5 on 2026-05-14
> Author: Jasper (with Claude Code)
> Scope: Layer 2 component per [docs/plans/2026-05-03-scideer-design.md](2026-05-03-scideer-design.md) Section 7

---

## 0. Why This Exists

DeerFlow's built-in `systematic-literature-review` skill is arXiv-only. SciDeer needs citation-graph capabilities — "which papers cite X" / "what does X cite" / "search papers across S2's corpus" — to support follow-up analysis tasks like *"Show me the most cited follow-up papers of arxiv:1609.02907"*.

Semantic Scholar's free tier API is public, requires no API key, and exposes both search and citation traversal. A thin stdio MCP server wraps it for Libra.

---

## 1. Scope (YAGNI)

**In scope:**

- 3 tools: `semantic_scholar_search`, `semantic_scholar_get_paper`, `semantic_scholar_get_citations`
- Sliding-window rate limiter (5 min / 100 calls) to stay within the free tier
- In-memory LRU + TTL cache (256 entries, 1 h)
- paper_id auto-normalization (raw arXiv ID / DOI / S2 hash → S2 prefix syntax)
- Markdown output for all tools (LLM-friendly, directly presentable to users)
- English text in all titles, labels, and error messages
- Wire-up via `extensions_config.example.json` (committed); document the local-copy step in README

**Explicitly cut (YAGNI):**

- ❌ S2 API key support — free tier is enough for demo + benchmark
- ❌ Disk cache — in-memory is enough for single-session usage; stdio subprocess restarts on DeerFlow restart anyway
- ❌ pytest unit tests — this MCP is not part of the core demo path nor a benchmark scoring target; manual smoke tests in README suffice
- ❌ Mock S2 API for testing — divergence between mock and real API is high; not worth the maintenance
- ❌ Structured logging framework — `print(..., file=sys.stderr)` is fine; DeerFlow captures stdio MCP server stderr
- ❌ JSON output mode or `data + summary` hybrid — markdown only

---

## 2. Architecture

### 2.1 File layout

```
scideer/
├── mcp_servers/
│   └── semantic-scholar/
│       ├── pyproject.toml
│       ├── README.md
│       └── semantic_scholar_mcp/        ← Python package (snake_case)
│           ├── __init__.py              ← empty
│           ├── __main__.py              ← `from .server import main; main()`
│           └── server.py                ← ~280 LOC main logic
└── extensions_config.example.json       ← modified: add semantic-scholar entry
```

### 2.2 Runtime model

- **Transport**: stdio (subprocess spawned by DeerFlow's `MultiServerMCPClient`)
- **Entry**: `python -m semantic_scholar_mcp` → `__main__.py` → `server.main()`
- **Lifecycle**: process restarts on DeerFlow restart; per-process in-memory cache (no persistence)
- **Environment**: installed into DeerFlow's `uv` virtualenv (`uv pip install -e mcp_servers/semantic-scholar`), not a separate venv

### 2.3 Tool registration

All 3 tools registered via `@mcp.tool()` from `mcp[cli]` SDK on a single `FastMCP("semantic-scholar")` instance. Each returns `str` (markdown).

---

## 3. Tool Contracts (LLM-facing)

### 3.1 `semantic_scholar_search(query: str, limit: int = 10) -> str`

- **API**: `GET /graph/v1/paper/search?query={q}&limit={n}&fields=title,authors,year,abstract,citationCount,externalIds`
- **Cache key**: `f"search:{query}:{limit}"`
- **Output**:

```markdown
# Search results for "graph neural networks"

Found N papers (showing top K)

---

## 1. Semi-Supervised Classification with Graph Convolutional Networks
- **Paper ID:** `649def34f8be52c8b66281af98ae884c09aef38b`
- **Authors:** Thomas N. Kipf, Max Welling
- **Year:** 2016 · **Citations:** 29847
- **arXiv:** 1609.02907

> {abstract first 300 chars}...

---
## 2. ...
```

### 3.2 `semantic_scholar_get_paper(paper_id: str) -> str`

- **Normalize**: `paper_id = _normalize_paper_id(paper_id)` (see Section 4.1)
- **API**: `GET /graph/v1/paper/{id}?fields=title,authors,year,abstract,citationCount,referenceCount,influentialCitationCount,externalIds,references.title,references.year,references.citationCount`
- **Cache key**: `f"paper:{normalized_id}"`
- **Output**:

```markdown
# Paper Details

## {title}
- **Paper ID:** `{s2_id}`
- **Authors:** {comma-separated}
- **Year:** {year}
- **arXiv:** {arxiv_id or "N/A"} · **DOI:** {doi or "N/A"}
- **Citations:** {N} (Influential: {M}) · **References:** {K}

### Abstract
> {full abstract}

### References (top 20 by citation count)
1. **{title}** ({year}) · {N} citations
2. ...
```

References capped at top 20 (sorted by `citationCount` desc) to control token cost.

### 3.3 `semantic_scholar_get_citations(paper_id: str, limit: int = 20) -> str`

- **Normalize**: same as 3.2
- **API**: `GET /graph/v1/paper/{id}/citations?fields=title,year,authors,citationCount,externalIds&limit={limit*3}` (over-fetch to ensure good sort)
- **Client-side**: sort by `citationCount` desc, take `limit`
- **Cache key**: `f"citations:{normalized_id}:{limit}"`
- **Output**:

```markdown
# Papers citing "{cited paper title}" ({arxiv:id if available})

Top {limit} most-cited follow-up papers:

---

## 1. {title} ({year}) · {N} citations
- **Authors:** {comma-separated}
- **Paper ID:** `{s2_id}`
- **arXiv:** {arxiv_id or "N/A"}

---
## 2. ...
```

### 3.4 Unified error output

Any error (4xx, 5xx after retries, network failure, normalization failure) returns markdown:

```markdown
# Semantic Scholar Error

**Tool:** semantic_scholar_get_paper
**Reason:** Paper not found (HTTP 404)
**Input:** `ARXIV:9999.99999`

Hint: Check the arXiv ID format or try searching by title first.
```

Hints by error class:

| Error | Hint |
|---|---|
| 404 | "Check the {arxiv/DOI/paper} ID format or try searching by title first." |
| 400 | "Invalid paper ID format. Use a raw arXiv ID (e.g. 1609.02907), a DOI, or a 40-char S2 paper hash." |
| 429 | "Semantic Scholar rate limit exceeded despite local throttling. Retry in a few minutes." |
| 5xx (after 3 retries) | "Semantic Scholar service is currently unavailable. Try again later." |
| Network | "Network error reaching Semantic Scholar. Check connectivity." |

**Critical invariant**: tool functions never raise to the MCP server layer. All exceptions caught and converted to markdown error strings. This prevents the stdio subprocess from dying mid-conversation.

---

## 4. Internal Logic

### 4.1 `_normalize_paper_id(raw: str) -> str`

Match in order; first hit wins:

| Input pattern | Regex | Output |
|---|---|---|
| Already-prefixed (case-insensitive) | `^(ARXIV\|DOI\|MAG\|ACL\|PMID\|PMCID\|CorpusId\|URL):` | Re-emit with upper-case prefix |
| New arXiv ID | `^\d{4}\.\d{4,5}(v\d+)?$` | `ARXIV:{id without v-suffix}` |
| Old arXiv ID | `^[a-z\-]+/\d{7}$` | `ARXIV:{id}` |
| DOI | `^10\.\d{4,}/\S+$` | `DOI:{doi}` |
| 40-hex S2 ID | `^[0-9a-f]{40}$` | Return as-is |
| Otherwise | — | Return as-is (let S2 decide) |

### 4.2 Rate limiter (sliding window 5 min / 100 calls)

```python
class SlidingWindowLimiter:
    def __init__(self, max_calls: int = 100, window_seconds: int = 300):
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
            await asyncio.sleep(wait_for)
```

Note: `while True` loop, not recursion. After sleep, re-acquire the lock and re-check the window.

### 4.3 TTL cache (LRU, size 256, TTL 1 h)

```python
class TTLCache:
    def __init__(self, maxsize: int = 256, ttl: float = 3600):
        self._maxsize = maxsize
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[str, float]] = OrderedDict()

    def get(self, key: str) -> str | None:
        if key not in self._data:
            return None
        value, expires_at = self._data[key]
        if time.monotonic() > expires_at:
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value: str) -> None:
        self._data[key] = (value, time.monotonic() + self._ttl)
        self._data.move_to_end(key)
        if len(self._data) > self._maxsize:
            self._data.popitem(last=False)
```

### 4.4 Retry policy

```python
async def _request_with_retry(client, url, params, max_retries=3):
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            await limiter.acquire()
            resp = await client.get(url, params=params, timeout=30)
            if resp.status_code < 400:
                return resp.json()
            if 400 <= resp.status_code < 500:
                raise S2ClientError(resp.status_code, resp.text)
            last_err = S2ServerError(resp.status_code, resp.text[:200])
        except (httpx.NetworkError, httpx.TimeoutException) as e:
            last_err = S2NetworkError(str(e))
        if attempt < max_retries:
            await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise last_err
```

- 4xx → raise immediately (no retry)
- 5xx → retry up to 3 times with exponential backoff
- Network error → retry up to 3 times with exponential backoff
- After exhaustion → raise `S2ServerError` / `S2NetworkError`
- All exceptions caught at tool function boundary, converted to markdown

---

## 5. Integration: extensions_config.example.json

Add to `mcpServers` map after `postgres`:

```json
"semantic-scholar": {
  "enabled": true,
  "type": "stdio",
  "command": "python",
  "args": ["-m", "semantic_scholar_mcp"],
  "env": {},
  "description": "Semantic Scholar paper search + citation graph (free tier, no API key required). Provides arXiv-beyond paper search, paper detail with references, and citation graph traversal."
}
```

Default `enabled: true` because this MCP is part of SciDeer's core extensions (per [2026-05-03-scideer-design.md Section 7](2026-05-03-scideer-design.md)).

### 5.1 pyproject.toml

```toml
[project]
name = "semantic-scholar-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "mcp[cli]>=1.2.0",
  "httpx>=0.27"
]

[project.scripts]
semantic-scholar-mcp = "semantic_scholar_mcp.server:main"

[tool.hatch.build.targets.wheel]
packages = ["semantic_scholar_mcp"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 5.2 README.md (server-side instructions)

Three sections:

1. **Install** (one command):
   ```bash
   cd /path/to/scideer
   uv pip install -e mcp_servers/semantic-scholar
   ```

2. **Enable** (one command):
   ```bash
   cp extensions_config.example.json extensions_config.json
   # or manually merge "semantic-scholar" entry into existing extensions_config.json
   ```

3. **Restart DeerFlow**:
   ```bash
   bash scripts/serve.sh --restart --dev --daemon
   ```

4. **Verify** (stdio smoke test):
   ```bash
   python -m semantic_scholar_mcp <<EOF
   {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}
   {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
   EOF
   ```
   Expect: stdout contains 3 tools, no stack trace.

---

## 6. Validation Strategy

Manual smoke tests documented in README.md (no pytest):

### 6.1 Happy path (3 calls)

| Case | Call | Expected |
|---|---|---|
| Search | `semantic_scholar_search("graph neural networks", limit=5)` | 5 markdown entries, all fields populated |
| Get Paper | `semantic_scholar_get_paper("ARXIV:1609.02907")` | GCN paper, ≥ 25 000 citations, ≥ 20 refs |
| Get Citations | `semantic_scholar_get_citations("ARXIV:1609.02907", limit=10)` | 10 follow-ups sorted by citationCount, includes GAT (1710.10903) |

### 6.2 Error path (3 calls)

| Case | Call | Expected |
|---|---|---|
| 404 | `semantic_scholar_get_paper("ARXIV:9999.99999")` | Markdown error, HTTP 404, hint included |
| Bad ID | `semantic_scholar_get_paper("not-an-id")` | Markdown error, no crash |
| Rate limit | 110 consecutive `semantic_scholar_search` calls | After call #100, sleeps ~300 s, no 429 errors observed |

### 6.3 End-to-end on server (user action)

1. `git pull origin scideer-main`
2. `uv pip install -e mcp_servers/semantic-scholar`
3. `cp extensions_config.example.json extensions_config.json` (or merge entry)
4. `bash scripts/serve.sh --restart --dev --daemon`
5. Web UI prompt: *"Show me the most cited follow-up papers of arxiv:1609.02907"*
6. Expect: agent calls `semantic_scholar_get_citations`, returns top 10-20 sorted follow-ups including GAT.

---

## 7. Risks & Mitigations

| # | Risk | P | I | Mitigation |
|---|---|:---:|:---:|---|
| R1 | S2 free tier 429 during demo | 🟡 M | 🟡 M | Sliding-window pre-throttle; LRU caches the GCN paper after first call |
| R2 | `python -m semantic_scholar_mcp` fails due to PATH issue | 🟢 L | 🔴 H | README documents `uv pip install -e` step explicitly; smoke test catches before restart |
| R3 | S2 API schema change | 🟢 L | 🟡 M | Use only stable `fields=` projections documented at api-docs |
| R4 | extensions_config.json merge conflict on server | 🟡 M | 🟢 L | README's "or manually merge" note; entry is self-contained |
| R5 | stdio subprocess crashes on unhandled exception | 🟢 L | 🔴 H | All tool functions wrap with `try/except Exception` → markdown error |
| R6 | Token cost explosion from large reference lists | 🟢 L | 🟡 M | Reference list hard-capped at top 20 by citationCount |

---

## 8. Acceptance Criteria

- [ ] `mcp_servers/semantic-scholar/semantic_scholar_mcp/server.py` exists and runs
- [ ] `pyproject.toml` validates with `uv pip install -e .`
- [ ] `python -m semantic_scholar_mcp` responds to stdio JSON-RPC `tools/list`
- [ ] All 3 tools return markdown for happy-path inputs
- [ ] All 3 tools return markdown error for error-path inputs (never raise)
- [ ] `extensions_config.example.json` has `semantic-scholar` entry with `enabled: true`
- [ ] README.md contains install + enable + restart + verify steps
- [ ] Server-side end-to-end test in Section 6.3 passes

---

## 9. Out of Scope (Future Work)

- API key support (paid tier, 10x rate limit)
- Disk cache for cross-restart persistence
- `bulk` endpoint for batch paper lookups
- Author search (`/graph/v1/author/search`)
- Recommendation endpoint (`/recommendations/v1/papers/forpaper/{id}`)

---

**End of design. Next: invoke `superpowers:writing-plans` to produce the implementation plan.**
