# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versions are released as git tags on the `master` branch. The pre-remediation
state is tagged `v1.0.0`.

## [Unreleased]

Nothing yet.

## [1.0.1] — 2026-11-06

Stage 1 of the remediation: closes the arbitrary-file-read and hardens the
HTTP transport.

### Security

- **Fixed: arbitrary file read in `get_skill_bundle`.** The bundle base
  directory was the skill's *parent* and read paths were built with `join()`
  and no containment check, so `files: ["../../../../../../etc/hostname"]`
  returned file contents. Paths are now resolved inside the skill directory
  only; absolute paths and `..` segments are refused outright, and a refused
  path reports an error rather than probing for existence.
- **HTTP authentication.** Every request must carry
  `Authorization: Bearer <token>`. The token comes from `MCP_AUTH_TOKEN`, or
  is generated at startup on loopback and printed to stderr. A non-loopback
  bind with no token configured refuses to start rather than serving
  unauthenticated. Tokens are compared in constant time.
- **HTTP origin checks.** A request carrying an `Origin` header is rejected
  with 403 unless that origin is explicitly allowed via `ALLOW_ORIGIN`. This
  blocks the "any web page the user visits" attack, where a page in the
  user's browser posts to the local server.
- **CORS no longer defaults to a wildcard.** `Access-Control-Allow-Origin: *`
  was the default; it is now emitted only when `ALLOW_ORIGIN=*` is set
  explicitly. The CORS headers are applied to the MCP response itself, which
  the transport was previously overwriting.
- **Request body limit.** Bodies are capped (4 MiB by default,
  `MCP_MAX_BODY_BYTES`) and the cap is enforced while the stream is read, so
  an oversized body is abandoned rather than buffered. Over-limit requests
  return 413.
- **Internal errors are no longer echoed to clients.** The 500 handler
  returned `String(err)`, which could disclose paths; it now returns a generic
  error and logs the detail to stderr.
- **Fixed: request teardown on `res.on("close")`.** That event also fires on a
  normally completed response and could close the server before the response
  was flushed. Teardown now happens on request abort.

### Fixed

- `get_skill_bundle` applied its `max_bytes` cap in UTF-16 code units rather
  than bytes, so multi-byte content could exceed the documented cap by up to
  three times. The cap is now measured in bytes.
- `get_skill_bundle` accepted an unbounded list of file paths, allowing
  unbounded filesystem calls per request. The list is capped at 200.
- `readIfExists` performed an `existsSync`/`statSync`/`readFileSync` sequence
  that could throw if the file changed between the stat and the read. It now
  returns null on error.

### Tests

- New `mcp/tests/security.test.js`: twelve escaping paths must yield no
  content, the manifest must contain no escaping path, legitimate relative
  paths must still resolve, truncation must honour the byte cap, and an
  oversized file list must be rejected.
- `mcp/tests/http.test.js`: added coverage for missing and wrong tokens, an
  unexpected origin, an allowed origin, malformed JSON, an oversized body, and
  the absence of a wildcard CORS header by default.
- The cross-transport parity matrix now covers all nine tools; `list_skills`
  and `get_skill_bundle` were previously untested for parity.

Verification: 61 tests pass, and the full local suite reports 1061 checks
passing. The original exploit was re-run against a live server and now
returns `path is outside the skill directory` with no content.

## [1.0.0] — 2026-11-06

Baseline. The state of the project as published, before the security and
attribution remediation.

- MCP server exposing 67 skills and 15 agents over stdio and Streamable HTTP.
- Nine tools: `search_skills`, `get_skill`, `get_skill_bundle`, `list_skills`,
  `get_agent`, `render_skill`, `run_agent`, `list_modalities`, `get_stats`.
- `render_skill` renders a skill into five dialects: `markdown`,
  `claude-frontmatter`, `openai-yaml`, `agentsmd`, `cursor-rules`.
- Deterministic index build with byte-reproducibility gates
  (`build_index.py --check`, `build_provenance.py --check`).
- Local verification suite (`.verify_all.py`) running 1061 checks.
- Node test suite running 49 tests.

### Known issues at this tag

Recorded here so the audit trail shows what the remediation addressed.

- **Arbitrary file read.** `get_skill_bundle` built read paths with `join()`
  and no containment check. Verified live against a running server:
  `files: ["../../../../../../etc/hostname"]` returned the file contents.
  The HTTP transport compounded this — it served `Access-Control-Allow-Origin: *`
  with no `Origin` validation and no authentication.
- **Licence attribution overstated.** `detect_license_near()` walked up from a
  skill directory until it found this repository's own root `LICENSE` (MIT),
  so 64 of 82 provenance rows reported a licence inherited from the project
  rather than from upstream. 43 vendored items have no discoverable upstream
  licence at all.
- **Local paths leaked into the published record.** 46 provenance rows, and
  the `Source:` lines of `CREDITS.md`, carried absolute paths under
  `/home/biloi/Projects/Skills_n_Agents/`.
- **Self-attribution in the index.** `build_index.py` resolved `upstream` from
  the destination directory, so 43 skills were recorded as originating from
  this repository's own remote.
- **Silent corruption in the renderer.** A non-object YAML frontmatter was cast
  to `SkillFrontmatter` without validation; a skill with no `name` rendered the
  literal marker `<!-- skills-library:name:undefined -->`; the `cursor-rules`
  dialect stripped its own structural blank lines.
- **Unbounded resource use.** The HTTP transport buffered request bodies with
  no size limit, and `get_skill_bundle` applied its `max_bytes` cap using UTF-16
  code units rather than bytes.
- **Documented extension point did not exist.** `README.md` described
  `mcp/data/harnesses.json` as the dialect registry such that "adding a client
  is a JSON edit", but the renderer dispatched through a hardcoded `switch` and
  no runtime code read the file.
- **No CI, no changelog, no tags** prior to this file.

[Unreleased]: https://github.com/ashikonik/content-creation-mcp/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ashikonik/content-creation-mcp/releases/tag/v1.0.0
