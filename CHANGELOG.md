# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versions are released as git tags on the `master` branch. The pre-remediation
state is tagged `v1.0.0`.

## [Unreleased]

Nothing yet.

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
