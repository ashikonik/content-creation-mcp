# content-creation-mcp

An MCP server that exposes **content-creation skills and agents** — video, images,
audio, text, 3D, and design — to **any MCP-capable agent**, not just a specific
coding harness.

## Why this exists

Most skill libraries are built for one harness: the skill is a `SKILL.md` with
Claude-style frontmatter, installed into `~/.claude/skills/`, and only Claude Code
knows what to do with it. This server takes the opposite approach.

**The skill is the unit of portability.** A skill here is a directory with a
`SKILL.md` and optional `references/`, `scripts/`, and `assets/`. The server
reads it, indexes it, and **renders it into whatever dialect the calling agent
understands** — Claude frontmatter, OpenAI YAML, AGENTS.md sections, Cursor
rules, or plain markdown. The tool layer never learns which client called it.

That is what `render_skill` is for. It returns a string. No filesystem writes, no
harness assumptions, no registry to enrol in.

```
                    ┌──────────────────────────────┐
  Claude Code ────► │                              │
  Codex ──────────► │   content-creation-mcp       │ ──► 64 skills
  Cursor ─────────► │   (stdio + HTTP)             │ ──► 15 agents
  OpenCode ───────► │                              │ ──► 8 content domains
  Anything else ───► │                              │ ──► 5 render dialects
                    └──────────────────────────────┘
```

## Transports

| Transport | Endpoint | Use case |
|---|---|---|
| **Streamable HTTP** (primary) | `http://localhost:8787/mcp` | One shared server, any MCP client, remote-capable |
| **stdio** | `node mcp/dist/index.js` | Local clients that spawn a subprocess |

Both transports expose an identical tool set and return identical payloads.

### Connecting

HTTP — the transport is authenticated. Set a token, then pass it to your
client:

```bash
export MCP_AUTH_TOKEN=$(openssl rand -hex 32)
node mcp/dist/http.js
```

The token is printed to stderr on startup if you do not set one (loopback
only). A server bound to a non-loopback address refuses to start without an
explicit `MCP_AUTH_TOKEN`.

```json
{
  "mcpServers": {
    "content-creation": {
      "url": "http://localhost:8787/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_AUTH_TOKEN}"
      }
    }
  }
}
```

stdio — for clients that spawn subprocesses. The subprocess is local, so no
token is involved:

```json
{
  "mcpServers": {
    "content-creation": {
      "command": "node",
      "args": ["/absolute/path/to/content-creation-mcp/mcp/dist/index.js"]
    }
  }
}
```

### HTTP configuration

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8787` | Listen port |
| `HOST` | `127.0.0.1` | Bind address. A non-loopback bind requires `MCP_AUTH_TOKEN` |
| `MCP_AUTH_TOKEN` | generated on loopback | Bearer token required from clients |
| `ALLOW_ORIGIN` | *(none)* | Comma-separated origins permitted to make browser requests. `*` opts into any origin |
| `MCP_MAX_BODY_BYTES` | `4194304` | Request body cap |

Browser requests are rejected with 403 unless their `Origin` is allowed, so
a web page cannot drive this local server on the user's behalf.

Or use the bundled registration helper:

    ./mcp/scripts/register.sh --mcp-url http://localhost:8787/mcp

## Tools

| Tool | Purpose |
|---|---|
| `search_skills` | Lexical search across skills, filterable by content modality |
| `get_skill` | Fetch one skill with frontmatter and body |
| `get_skill_bundle` | Fetch a skill's supporting files (`references/`, `scripts/`, `assets/`) |
| `list_skills` | Browse skills by modality |
| `get_agent` | Fetch one agent definition |
| `render_skill` | **Core.** Render a skill into a target dialect as a string |
| `run_agent` | Assemble a runnable prompt for an agent, plus the skills it should load |
| `list_modalities` | The content taxonomy, with per-modality counts |
| `get_stats` | Corpus statistics |

There are deliberately no `install_*` tools. This server serves MCP clients; it
does not bootstrap coding harnesses. Keeping that boundary is what makes it
usable by anything.

## Content modalities

`video` · `image` · `audio` · `text` · `3d` · `design` · `av_pipeline` · `writing`

Each skill and agent carries a `content_domain`, so a client can ask for "audio
skills" directly instead of guessing keywords. See `mcp/build/content_domains.py`.

Current distribution across the 79-record corpus (64 skills + 15 agents):

| Domain | Records | Domain | Records |
|---|---:|---|---:|
| `video` | 19 | `image` | 13 |
| `writing` | 13 | `text` | 11 |
| `design` | 11 | `audio` | 5 |
| `av_pipeline` | 4 | `3d` | 3 |

## Render dialects

`render_skill` is the reason this server is harness-agnostic. The same skill
renders to any of five formats, each pinned by a test in `mcp/tests/render.test.js`:

| Format | Shape |
|---|---|
| `markdown` | Body only, no frontmatter — the most portable form |
| `claude-frontmatter` | YAML frontmatter with `name` + `description` |
| `openai-yaml` | YAML with `interface`, `policy`, `metadata`, `instructions` |
| `agentsmd` | Markdown section wrapped in `<!-- skills-library:name:X -->` markers |
| `cursor-rules` | Prose rule file with a heading and an `Apply when:` line |

The dialect registry lives in `mcp/data/harnesses.json` — data, not `switch`
branches, so adding a client is a JSON edit.

That claim is enforced, not just documented. The server reads the registry at
startup and derives from it the list of formats `render_skill` accepts, the
file extension each format is written with, and the install convention of
every harness. The renderer dispatches through a map, and startup fails with a
message naming the format if the registry names one the renderer has no
implementation for — so a format can never be accepted and then fail on every
call. `tools/verify_all.py` checks the two sides against each other in both
directions.

Adding a *format* still requires a renderer function; there is no way to
express a new layout in JSON. Adding a *harness* — a client family with its
own directories and filename pattern — is genuinely a JSON edit.

## Quick start

```bash
cd mcp
npm install
npm run build
npm test

# run the HTTP server
node dist/http.js            # listens on :8787

# or stdio
node dist/index.js
```

## Project layout

```
skills/          skill directories — SKILL.md + references/ + scripts/ + assets/
agents/          agent definitions, one <name>.md each
mcp/
  src/           TypeScript server
    server.ts        tool registration (transport-agnostic core)
    index.ts         stdio entrypoint
    http.ts          Streamable HTTP entrypoint
    search.ts        lexical search
    render.ts        dialect rendering
    frontmatter.ts   parse + emit
    index-loader.ts  root-relative index loading
    harness-registry.ts  loads data/harnesses.json at runtime
  build/         index builder, taxonomy, provenance
  data/          generated index, harness registry, provenance, exclusions
  tests/         protocol, search, render-format, registry, HTTP + parity tests
  scripts/       register.sh — emits MCP client config snippets
tools/           repository tooling, not part of the server
  verify_all.py        the full verification suite
  build_survey.py      builds the survey artifacts from a raw sweep
  refresh_survey.py    recomputes the survey summary in place
  curate_repos.py      curates the reference tables
  link_reference_tools.py  points skills at their reference files
  vendor_skills.py     vendors upstream skills into this corpus
surveys/         the GitHub survey that seeded the corpus
```

## Rebuilding the index

```bash
python3 mcp/build/build_index.py        # regenerate mcp/data/index.json
python3 mcp/build/build_provenance.py   # regenerate mcp/data/provenance.json
python3 mcp/build/write_credits.py       # regenerate CREDITS.md
python3 tools/verify_all.py                # run the verification suite
```

The index is deterministic — running the builder twice produces a byte-identical
file, and `--check` fails if the on-disk copy is stale. It stores no absolute
paths, so the whole directory is portable.

`generated_at` in the index is pinned to `1970-01-01T00:00:00Z` on purpose. A
wall-clock timestamp would change the file on every rebuild, and the
`--check` gate could no longer distinguish "the corpus changed" from "the
clock moved". The field stays because the API contract declares it; its value
marks the index as a build artifact rather than a timestamped record.

## Verification

`tools/verify_all.py` runs 1000+ assertions across the corpus and the server:

- every skill and agent has valid frontmatter, and the index matches the tree
- every referenced file and markdown link resolves
- every record has a provenance row with a licence, and excluded content is
  documented in `NOTICE`
- all 29 required capabilities resolve to a skill, through a real search query
- no skill depends on a paid hosted service. The check names the services it
  forbids and scans for them; free stock-media APIs are in scope, and a hosted
  path is allowed only where a local default is the primary one and the
  fallback is an explicit user opt-in
- the index and provenance table are byte-reproducible
- the server's own test suite passes, including the cross-transport parity check

## Licences

MIT for the server and authored content. Vendored third-party skills keep their
upstream licence — see `NOTICE` and the generated `CREDITS.md`.

## Survey

`surveys/content_creation_github.jsonl` records a sweep of 43,362 GitHub
repositories for content-creation skills, agents, and tooling, sorted by stars,
with the modality each one fills. `surveys/content_creation_github.md` is the
readable report. They are the provenance for why these skills exist.

The JSONL is 18 MB — about 96% of the tracked repository — and it is kept
uncompressed on purpose: four tools read it directly
(`tools/refresh_survey.py`, `tools/curate_repos.py`, `tools/build_survey.py`,
and the verification suite), and a `.gz` file would mean every one of them
grows a decompression branch. It compresses to roughly 3.8 MB, so a
`git lfs` track or a gzip side-car would cut it to a fifth of the size if
that trade is ever worth making. The records themselves are not
regenerable: the raw sweep output they came from no longer exists, and
`tools/refresh_survey.py` recomputes the summary header and the Markdown
report from the published JSONL rather than from the sweep.
