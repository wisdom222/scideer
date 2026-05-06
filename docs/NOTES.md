# DeerFlow 2.0 Source Code Analysis Notes

> Phase 0 Task 3 deliverable for SciDeer.
> Date: 2026-05-06
> Source: `bytedance/deer-flow` @ `scideer-main` (fork: `wisdom222/scideer`)

This document maps DeerFlow 2.0's architecture and answers the design-doc assumptions before SciDeer implementation begins. Reference paths are relative to repo root.

---

## 1. Skill System (highest priority for SciDeer)

### Loader

- Central loader: `SkillStorage.load_skills()` at `backend/packages/harness/deerflow/skills/storage/skill_storage.py:212-246`
- Storage backends:
  - `LocalSkillStorage` (production) at `backend/packages/harness/deerflow/skills/storage/local_skill_storage.py`
  - Container variant for sandboxed execution
- Frontmatter parser: `backend/packages/harness/deerflow/skills/parser.py:12-81`

### Skill File Format (verified)

```yaml
---
name: skill-name
description: One-line description (used by the lead agent to decide when to invoke)
license: (optional)
compatibility:  # optional
  nodejs: ">=18.0.0"
---
# Main markdown content (workflow, examples, references)
```

Each skill is a **directory** under `skills/public/<name>/` or `skills/custom/<name>/` containing:

- `SKILL.md` (required)
- `scripts/` (optional, e.g. `arxiv_search.py`)
- `templates/` (optional, e.g. paper templates)
- `references/` (optional)
- `assets/` (optional)
- `evals/` (optional)

### Discovery

- Pure filesystem scan — **no registration needed**
- Scans `skills/public/` and `skills/custom/` directories at startup
- Categorized as `public` or `custom` (enum at `backend/packages/harness/deerflow/skills/types.py`)
- Enabled state merged from `extensions_config.json` `skills:` section

### How Lead Agent Invokes Skills

> ⚠️ Important: Skills are **NOT** triggered by keywords (this corrects an early design assumption).

- Skills are injected into the **system prompt** as `<available_skills>` XML block at `backend/packages/harness/deerflow/agents/lead_agent/prompt.py:606-636`
- Each skill appears with: `name`, `description`, container file path
- System prompt instructs the agent: when a user query matches a skill description, **call `read_file`** on the skill's main file
- Progressive loading: agent reads SKILL.md → loads referenced resources from subdirs as needed
- No "skill dispatcher tool" — the lead agent decides via natural reasoning over `description` fields

### Implications for SciDeer

- New skills go in `skills/custom/<name>/` (or `skills/public/<name>/` if we prefer to keep them discoverable on disk alongside built-ins)
- The `description:` frontmatter is the **most important field** — it's what the lead agent reads to decide when to invoke
- Workflow steps live in markdown body; agent follows them sequentially after `read_file`

---

## 2. Existing Skills Inventory (21 total)

| Name | One-line Description | Category |
|------|----------------------|----------|
| academic-paper-review | Review/critique/summarize papers with peer-review-quality assessments | 🔬 Scientific |
| bootstrap | Generate personalized SOUL.md through onboarding conversation | Generic |
| chart-visualization | Visualize data with 26 chart types and image generation | 🔬 Scientific |
| claude-to-deerflow | HTTP API integration for delegating research/analysis tasks | Integration |
| code-documentation | Generate professional code/API/library documentation | Dev |
| consulting-analysis | Generate consulting-grade analytical reports (two phases) | Business |
| data-analysis | Analyze Excel/CSV with statistics, pivot, SQL, structured exploration | 🔬 Scientific |
| deep-research | Multi-angle systematic web research methodology | 🔬 Scientific |
| find-skills | Help discover and install agent skills | Meta |
| frontend-design | Create production-grade web components, pages, dashboards | Dev |
| github-deep-research | Multi-round deep research on GitHub repos with timelines/diagrams | Dev |
| image-generation | Generate images for characters, scenes, products | Generic |
| newsletter-generation | Generate newsletters, email digests, weekly roundups | Generic |
| podcast-generation | Generate two-host conversational podcasts from text | Generic |
| ppt-generation | Generate visually rich slide presentations with images | Generic |
| skill-creator | Create/modify/benchmark new skills | Meta |
| surprise-me | Creatively combine other skills for delightful experiences | Generic |
| **systematic-literature-review** | Multi-paper SLR with arXiv search and APA/IEEE/BibTeX output | 🔬 Scientific |
| vercel-deploy-claimable | Deploy to Vercel with preview URLs and claimable links | Deployment |
| video-generation | Generate videos with structured prompts and reference images | Generic |
| web-design-guidelines | Audit UI code for accessibility/Web Interface Guidelines | Dev |

### Scientific Skills — Detail (the 5 we will reuse)

- **systematic-literature-review** (`skills/public/systematic-literature-review/`)
  - Searches arXiv via bundled `scripts/arxiv_search.py` (no API key required)
  - Synthesizes multi-paper research, outputs APA/IEEE/BibTeX
  - **Replaces our originally-planned `literature-review` skill**

- **academic-paper-review** (`skills/public/academic-paper-review/`)
  - Single-paper analysis from URL or PDF
  - Structured peer-review-quality output: methodology, contributions, positioning, feedback
  - Useful as a sub-step within paper-reproduction's "extract method/experiments" phase

- **data-analysis** (`skills/public/data-analysis/`)
  - Excel/CSV analysis: aggregation, filtering, joins, multi-format export
  - **Replaces our originally-planned `experiment-runner` skill** (combined with chart-visualization)

- **chart-visualization** (`skills/public/chart-visualization/`)
  - 26 chart types for visualization
  - Pairs with data-analysis for full experiment reporting

- **deep-research** (`skills/public/deep-research/`)
  - Multi-angle web research
  - Complements arXiv search for non-academic sources

### What SciDeer Adds (the gaps)

| Capability | DeerFlow has? | SciDeer adds |
|------------|:-------------:|:------------:|
| Literature review (arXiv) | ✅ | reuse |
| Single paper review | ✅ | reuse |
| Data analysis + charts | ✅ | reuse |
| **Paper reproduction (code-gen + sandbox-exec + comparison)** | ❌ | ✅ new skill |
| **LaTeX paper generation (with bib + compile)** | ❌ | ✅ new skill |
| **End-to-end research lifecycle orchestration** | ❌ | ✅ `sci-pi` custom subagent |
| Citation graph / cross-database paper search | ❌ (arXiv only) | ✅ Semantic Scholar MCP |

---

## 3. Lead Agent / Orchestrator

### Entry Point

- `create_lead_agent()` at `backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- Built on LangChain's `create_agent` with LangGraph runtime
- System prompt at `backend/packages/harness/deerflow/agents/lead_agent/prompt.py:341-518`

### Orchestration Pattern

Lead agent has 4 dispatch paths:

1. **Direct tools** (built-in): `read_file`, `bash`, `web_search`, `view_image`
2. **Skills** (system-prompt injected): agent reads SKILL.md and follows workflow
3. **Subagents** (task tool): delegate specialized work
4. **MCP tools** (optional): external tool servers

### Middleware Pipeline

12+ middleware classes at `backend/packages/harness/deerflow/agents/middlewares/`:

- `ClarificationMiddleware` — intercepts ambiguous requests
- `MemoryMiddleware` — thread memory
- `SubagentLimitMiddleware` — caps concurrent task tool calls
- `LoopDetectionMiddleware` — infinite-loop guard
- `DeerFlowSummarizationMiddleware` — long-context handling
- `TokenUsageMiddleware`, `TitleMiddleware`, `TodoMiddleware`, ...

> Don't modify these for SciDeer — they're orthogonal to our skill/subagent additions.

---

## 4. Subagents / Custom Agents Mechanism

### Config Format

`SubagentConfig` at `backend/packages/harness/deerflow/subagents/config.py:10-36`:

```python
@dataclass
class SubagentConfig:
    name: str
    description: str
    system_prompt: str
    tools: list[str] | None       # None = inherit all
    disallowed_tools: list[str]   # default ["task"] to prevent nesting
    skills: list[str] | None      # None = inherit all, [] = none
    model: str = "inherit"
    max_turns: int = 50
    timeout_seconds: int = 900
```

### Built-in Subagent Types

- `general-purpose` — multi-step reasoning, exploration, action
- `bash` — command execution (only when host bash allowed or sandbox)

### Defining Custom Subagents (sci-pi)

Two ways:

**Option A**: in `config.yaml` under `subagents.custom_agents`:

```yaml
subagents:
  custom_agents:
    sci-pi:
      description: "Principal Investigator that orchestrates the full research lifecycle"
      system_prompt: |
        You are sci-pi, a research-lifecycle orchestrator...
      tools: [task, read_file, write_file, bash]
      skills:
        - systematic-literature-review
        - academic-paper-review
        - data-analysis
        - chart-visualization
        - paper-reproduction       # SciDeer new
        - scientific-writing        # SciDeer new
      model: inherit
      max_turns: 80
      timeout_seconds: 1800
```

**Option B**: as `agents/sci-pi/config.yaml` + `agents/sci-pi/prompt.md` (more modular, our design doc's choice)

### Task Tool

- `task(description, prompt, subagent_type, max_turns=None) -> str` at `backend/packages/harness/deerflow/tools/builtins/task_tool.py:51-79`
- Returns subagent execution result as string
- Background async execution with auto-poll

### Executor

- `backend/packages/harness/deerflow/subagents/executor.py`
- Runs subagents asynchronously, backend auto-polls for completion (no manual poll required)

---

## 5. MCP / Tool Registration

### Extensions Config

`extensions_config.example.json`:

```json
{
  "mcpInterceptors": ["my_package.mcp.auth:build_auth_interceptor"],
  "mcpServers": {
    "filesystem": {
      "enabled": false,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
      "env": {}
    }
  },
  "skills": {}
}
```

### MCP Server Types

- `stdio` — local process spawning
- `sse` / `http` — remote servers
- OAuth via interceptor pattern

### Loader

- `build_server_params()` at `backend/packages/harness/deerflow/mcp/client.py:11-68` (config → langchain-mcp-adapters)
- `initialize_mcp_tools()` at `backend/packages/harness/deerflow/mcp/cache.py:56-79` (load + cache at startup)
- Hot-reload by config mtime monitoring

### Tool Discovery at Runtime

`get_available_tools()` at `backend/packages/harness/deerflow/tools/tools.py:36-155` loads:

1. Built-in tools (`present_file`, `clarification`, `task` if subagents enabled)
2. Config-defined tools via `resolve_variable()` reflection (`use: "deerflow.sandbox.tools:bash_tool"` syntax)
3. Cached MCP tools
4. Tool search deferred registry (if `tool_search.enabled: true`)

### Adding Semantic Scholar MCP for SciDeer

Two-step:

1. Find or write a Semantic Scholar MCP server (stdio-style Python script)
2. Add to `extensions_config.json`:

```json
{
  "mcpServers": {
    "semantic-scholar": {
      "enabled": true,
      "type": "stdio",
      "command": "python",
      "args": ["-m", "semantic_scholar_mcp"],
      "env": {"S2_API_KEY": "$S2_API_KEY"}
    }
  }
}
```

---

## 6. SciDeer-Critical Findings

### ✅ arxiv_search.py (built-in, ready to use)

`skills/public/systematic-literature-review/scripts/arxiv_search.py`

- Standalone Python script
- Uses public arXiv API (`http://export.arxiv.org/api/query`) — **no API key required**
- Parses Atom XML with namespace support
- Max 50 results
- Fallback from `requests` to `urllib`

> **Implication**: We do NOT need a separate arXiv MCP. The existing `systematic-literature-review` skill already integrates this. Drop the originally-planned arXiv MCP from scope.

### ✅ PatchedChatDeepSeek (used by our config)

`backend/packages/harness/deerflow/models/patched_deepseek.py:17-73`

- Fixes parent class bug: `reasoning_content` not preserved across multi-turn
- Overrides `_get_request_payload()` to inject reasoning_content into all assistant messages
- Required for thinking-enabled DeepSeek models

> **Implication**: When we eventually use thinking-enabled models, this is what makes it work. For now (DeepSeek V4 Pro/Flash, `supports_thinking: false`), it's just a normal OpenAI-compatible client.

### Sandbox Providers

| Provider | Purpose | Use Case |
|----------|---------|----------|
| `LocalSandboxProvider` | Direct host execution, read-only skills mount | Local dev, trusted single-user |
| `AioSandboxProvider` | Containerized isolation, lifecycle management | Production, untrusted code, paper-reproduction |

For SciDeer's `paper-reproduction` skill, we need `AioSandboxProvider` to safely execute paper code. Configure via:

```yaml
sandbox:
  use: deerflow.community.aio_sandbox:AioSandboxProvider
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  port: 8080
  replicas: 3
```

> **TODO**: We may need to extend the sandbox image to include LaTeX (`texlive-full`) for the `scientific-writing` skill. See `docker/scideer-sandbox/Dockerfile` planned in the design doc.

---

## 7. Updated Assumptions Verification (Phase 0 Gate)

| Original Assumption | Verified? | Evidence |
|--------------------|:---------:|----------|
| Skills are pure Markdown plug-and-play | ✅ | SKILL.md + YAML frontmatter, no compilation, filesystem discovery (`skills/storage/skill_storage.py:212`) |
| Native MCP support (stdio + HTTP/SSE + OAuth) | ✅ | `extensions_config.json` schema, `mcp/client.py:11-68` |
| ~~Skills triggered by keywords~~ | ❌ | Wrong — agent reads `description` in system prompt, calls `read_file` on SKILL.md (`prompt.py:606-636`) |
| Lead agent uses LangGraph | ✅ | LangChain `create_agent` with LangGraph runtime support (`agents/lead_agent/agent.py`) |
| Built-in arXiv search exists | ✅ | `skills/public/systematic-literature-review/scripts/arxiv_search.py` |
| ~~Need separate arXiv MCP~~ | ❌ | Unnecessary — arxiv_search.py already in built-in skill |
| ~~DeerFlow has no scientific skills~~ | ❌ | Wrong — has 5 (literature-review, paper-review, data-analysis, chart-visualization, deep-research) |
| Subagent composition mechanism exists | ✅ | `task` tool + `SubagentConfig` + `custom_agents` (`subagents/config.py`) |
| Middleware pipeline | ✅ | 12+ middlewares at `agents/middlewares/`, extensible |
| PatchedChatDeepSeek for thinking models | ✅ | `models/patched_deepseek.py:17-73` |

### Configuration State (current setup)

- LLM: **DeepSeek V4 Pro / Flash** via `PatchedChatDeepSeek` at `https://api.deepseek.com/v1`, env var `DEEPSEEK_API_KEY`
- Sandbox: `LocalSandboxProvider` (default; switch to `AioSandboxProvider` before paper-reproduction work)
- Server: Tencent Cloud Singapore, 8GB RAM, Ubuntu 24.04, Docker 29.4 + Python 3.12 + Node 22 + uv 0.11
- Web UI: `http://43.156.100.148:2026` (running via `make dev-daemon`)

---

## 8. Implementation Decisions Confirmed by This Analysis

Based on the source review, here are the locked-in decisions for SciDeer:

1. **Skills go in `skills/custom/`** — keeps fork clean, easy to upstream-merge later
2. **Skills are pure `.md` files with YAML frontmatter** — no Python registration code needed
3. **`description:` field is critical** — invest time crafting it; that's what the lead agent uses to route
4. **`sci-pi` subagent** uses Option B layout: `agents/sci-pi/{config.yaml,prompt.md}` (modular, our design doc choice)
5. **Drop arXiv MCP from scope** — reuse `systematic-literature-review` skill instead
6. **Drop standalone `literature-review` and `experiment-runner` skills** — covered by built-ins
7. **Build only 2 new skills**: `paper-reproduction` and `scientific-writing`
8. **Build 1 MCP**: Semantic Scholar (citation graph; arXiv has no citation data)
9. **Switch sandbox to `AioSandboxProvider`** before paper-reproduction work
10. **Custom Docker image** required for LaTeX compilation in `scientific-writing` skill

---

## 9. Next Steps (entering Layer 1)

1. Test DeerFlow's existing `systematic-literature-review` skill with a real query, document behavior in `docs/observations/baseline-slr.md`
2. Pull AIO sandbox image (`make setup-sandbox`)
3. Switch `config.yaml` `sandbox:` to `AioSandboxProvider`
4. Start writing `skills/custom/paper-reproduction/SKILL.md` (Layer 1, Task 6 in implementation plan)
