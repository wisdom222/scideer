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
        except httpx.RequestError as e:
            # RequestError is the parent of NetworkError, TimeoutException,
            # InvalidURL, ProtocolError, etc. — catches all transport-level failures
            last_err = S2NetworkError(str(e))
        except ValueError as e:
            # resp.json() raises ValueError on malformed JSON; treat as transient
            last_err = S2NetworkError(f"malformed response: {e}")
        if attempt < RETRY_MAX:
            await asyncio.sleep(2 ** attempt)
    if last_err is None:
        raise S2NetworkError("retry loop exited without recording error")
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
        f"- **Year:** {paper.get('year') or 'N/A'} · **Citations:** {paper.get('citationCount') or 0}\n"
        f"- **arXiv:** {_external_id(paper.get('externalIds'), 'ArXiv')}\n\n"
        f"> {_truncate_abstract(paper.get('abstract'))}\n"
    )


def _format_reference(idx: int, ref: dict[str, Any]) -> str:
    return (
        f"{idx}. **{ref.get('title', 'Untitled')}** "
        f"({ref.get('year') or 'N/A'}) · {ref.get('citationCount') or 0} citations"
    )


def _format_citation(idx: int, citing_wrap: dict[str, Any]) -> str:
    paper = citing_wrap.get("citingPaper", {})
    return (
        f"## {idx}. {paper.get('title', 'Untitled')} ({paper.get('year') or 'N/A'}) · "
        f"{paper.get('citationCount') or 0} citations\n"
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
# NOTE: In mcp[cli]>=1.27, `@mcp.tool()` registers the tool with the FastMCP
# instance and returns the original async function unchanged — so tests and
# scripts that want to invoke a tool directly (bypassing JSON-RPC) can just
# `await` it: `await semantic_scholar_search("query", limit=3)`. No `.fn`
# accessor is needed. If a future SDK version wraps the function, switch to
# the documented invocation path.


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
            f"- **Year:** {data.get('year') or 'N/A'}\n"
            f"- **arXiv:** {_external_id(externals, 'ArXiv')} · "
            f"**DOI:** {_external_id(externals, 'DOI')}\n"
            f"- **Citations:** {data.get('citationCount') or 0} "
            f"(Influential: {data.get('influentialCitationCount') or 0}) · "
            f"**References:** {data.get('referenceCount') or 0}\n\n"
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
