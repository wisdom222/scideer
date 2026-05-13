# Semantic Scholar MCP Server

stdio MCP server exposing Semantic Scholar's free-tier paper search + citation
graph API to SciDeer / Libra agents. **No API key required.**

## Tools

| Tool | Description |
|---|---|
| `semantic_scholar_search(query, limit=10)` | Free-text paper search across S2's corpus |
| `semantic_scholar_get_paper(paper_id)` | Paper metadata + top-20 references |
| `semantic_scholar_get_citations(paper_id, limit=20)` | Follow-up papers sorted by citation count |

`paper_id` accepts: raw arXiv ID (`1609.02907`), DOI (`10.x/y`), 40-char S2
hash, or any S2-prefixed form (`ARXIV:...`, `DOI:...`, `MAG:...`, `CorpusId:...`).
All tools return markdown strings.

## Install (server-side)

From the repo root:

```bash
cd /path/to/scideer
VIRTUAL_ENV="$(pwd)/backend/.venv" uv pip install -e mcp_servers/semantic-scholar
```

(If you don't use `uv`, any pip pointed at `backend/.venv` works too. The
package is small — only 2 runtime deps: `mcp[cli]>=1.2.0` and `httpx>=0.27`.)

## Enable in DeerFlow

If `extensions_config.json` doesn't exist yet:

```bash
cp extensions_config.example.json extensions_config.json
```

If it already exists, manually merge the `semantic-scholar` entry from
`extensions_config.example.json` into your `extensions_config.json` under the
top-level `mcpServers` key:

```json
"semantic-scholar": {
  "enabled": true,
  "type": "stdio",
  "command": "python",
  "args": ["-m", "semantic_scholar_mcp"],
  "env": {},
  "description": "Semantic Scholar paper search + citation graph (free tier, no API key required)..."
}
```

Then restart DeerFlow:

```bash
bash scripts/serve.sh --restart --dev --daemon
```

## Verify

### 1. Stdio smoke test (no API call)

Save these three lines to `/tmp/s2_smoke.txt` (the first one initializes, the
second is a required JSON-RPC notification, the third lists registered tools):

```
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

Then pipe to the server (timeout it after a few seconds; the server doesn't
exit on its own under stdio):

```bash
timeout 5 python -m semantic_scholar_mcp < /tmp/s2_smoke.txt
```

Expect: two JSON-RPC responses on stdout. The second one's `result.tools`
array contains exactly 3 entries named `semantic_scholar_search`,
`semantic_scholar_get_paper`, `semantic_scholar_get_citations`.

### 2. Live API check

```python
import asyncio
from semantic_scholar_mcp.server import (
    semantic_scholar_search,
    semantic_scholar_get_paper,
    semantic_scholar_get_citations,
)

async def check():
    # @mcp.tool() in mcp[cli]>=1.27 returns the original async function
    # unchanged, so we await it directly. No .fn accessor needed.
    print(await semantic_scholar_search("graph neural networks", limit=3))
    print(await semantic_scholar_get_paper("ARXIV:1609.02907"))
    print(await semantic_scholar_get_citations("ARXIV:1609.02907", limit=5))

asyncio.run(check())
```

Expect: three markdown blocks. The GCN paper (`1609.02907`) has ~35 000
citations and ~38 references. Citations returns up to 5 papers ordered by
`citationCount` desc.

Note: if you run all three back-to-back the first call may hit S2's
server-side rate limit (HTTP 429) — the tool returns a clean error markdown
in that case rather than crashing. Wait a minute and retry, or rely on the
in-process LRU cache to short-circuit repeated calls within the hour.

### 3. End-to-end via Web UI

After restart, ask Libra:

> Show me the most cited follow-up papers of arxiv:1609.02907

Expected: the agent calls `semantic_scholar_get_citations` and presents a
markdown-rendered list of follow-up papers (Graph Attention Networks etc. on
top).

## Design constraints

- **Free tier**: 100 calls / 5 min — enforced via in-process sliding-window
  limiter. The server-side limit at S2 is sometimes more aggressive on cold
  start; the tool returns a markdown error in that case rather than crashing.
- **In-memory LRU cache** (256 entries, 1 h TTL) per stdio subprocess. Cache
  is lost across DeerFlow restarts.
- **5xx retries** up to 3 times with exponential backoff (1 s, 2 s, 4 s).
- **4xx errors** fail fast (no retry) and are converted to markdown errors.
- **All exceptions caught at tool boundary** — the stdio subprocess never
  dies mid-call. The lead agent always receives a markdown string.

## Files

```
mcp_servers/semantic-scholar/
├── pyproject.toml
├── README.md                          ← this file
└── semantic_scholar_mcp/
    ├── __init__.py
    ├── __main__.py                    ← `python -m semantic_scholar_mcp` entry
    └── server.py                      ← single-file logic, ~450 LOC
```

## Out of scope

- API key support (paid tier)
- Disk cache for cross-restart persistence
- Author search / recommendation endpoints

See [docs/plans/2026-05-14-semantic-scholar-mcp-design.md](../../docs/plans/2026-05-14-semantic-scholar-mcp-design.md)
for the full design rationale.
