# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versions are released as git tags on the `master` branch. The pre-remediation
state is tagged `v1.0.0`.

## [Unreleased]

Nothing yet.

## [1.5.0] — 2026-11-06

Stage 6 of the remediation: the fixes stay fixed. The documented extension
point now exists, CI runs the gates, and the repository's own tooling sits
where a reader will look for it.

### Fixed

- **The CI workflow did not install PyYAML, and every run failed on a clean
  runner.** The dependency was declared in `mcp/pyproject.toml` but the
  workflow only installed the Node dependencies, so
  `build_index.py --check` died with `ModuleNotFoundError: No module named
  'yaml'` on all four matrix legs. It passed locally because PyYAML happened
  to be installed on the machine that wrote the workflow. The workflow now
  installs `PyYAML>=6.0` before the Python gates, with pip caching against
  `mcp/pyproject.toml`. The failure was reproduced and the fix verified in
  a virtualenv without PyYAML — a stand-in for the clean runner.
- **The dialect registry is now the registry.** `mcp/data/harnesses.json` was
  described in the README as the extension point such that "adding a client is
  a JSON edit", but the renderer dispatched through a hardcoded `switch`, the
  accepted format list was a literal in `types.ts`, and nothing under
  `mcp/src/` had ever opened the file. The registry was documentation.
  A new `mcp/src/harness-registry.ts` loads it at startup, and the server
  derives from it the formats `render_skill` accepts, the file extension
  each format is written with, and the install convention of every
  harness. The renderer now dispatches through a map rather than a switch,
  and the two sides are checked against each other: startup fails with a
  message naming the format if the registry names one the renderer has no
  implementation for, so a format can never be accepted and then fail on
  every call that uses it. `.verify_all.py` checks the same relationship in
  both directions from the source text, and `mcp/tests/registry.test.js`
  pins it from the running server.
- **`list_modalities` now reports the harnesses**, not just the modality
  counts and a format list. A client asking "how do I install this for
  Cursor?" had no way to ask.
- **The README's survey count was stale.** It said 43,359 repositories; the
  survey holds 43,362. The two had drifted because nothing compared them.
  The count in the README is now checked against the survey, as is the
  number of required capabilities (the README said 24 while the suite
  enforced 29).
- **The npm lockfile's version had never been kept in sync.** It sat at
  1.0.0 for the project's entire history while `package.json` moved through
  four releases — and `npm ci` installs the version the lockfile records.
  It is now in sync, and the version-consistency check covers it.

### Added

- **CI** (`.github/workflows/ci.yml`). Runs on every push and pull request:
  `npm ci`, the build, the test suite, both reproducibility gates
  (`build_index.py --check` and `build_provenance.py --check`), and the
  full verification suite. The matrix covers Node 20 and 22 against Python
  3.10 and 3.12, with `fail-fast: false` so a Node-version problem and a
  Python-version problem are both reported rather than one masking the
  other. The reproducibility gates are what catch a corpus change that
  forgets to regenerate the index.
- **`mcp/tests/registry.test.js`** — seven tests covering the registry
  wiring, including the case where a format in the registry has no
  renderer.

### Changed

- **The repository's own tooling moved to `tools/`.** The six Python
  scripts at the repository root — a dot-prefixed naming convention that
  hid them from `ls` and from the project layout in the README — now live
  in `tools/` alongside `vendor_skills.py`, which was already there. Each
  script's project-root resolution was updated for the new depth, and all
  four survey scripts were re-run to confirm they still work.
- **The version is now consistent across five files** — `package.json`,
  `package-lock.json`, `server.ts`, `index.json`, and `pyproject.toml` —
  and the check asserts all five agree.

### Not changed, on purpose

- **`surveys/content_creation_github.jsonl` stays uncompressed** at 18 MB,
  about 96% of the tracked repository. Four tools read it directly, and a
  `.gz` side-car would mean every one of them grows a decompression
  branch. It compresses to roughly 3.8 MB, so a `git lfs` track would cut
  it to a fifth of the size — but LFS is not installed here, and making
  every consumer of the file install it is a worse trade than the bytes.
  The size, the reason it is kept this way, and the fact that the records
  are *not* regenerable from the original sweep are now documented in the
  README rather than left as an unexplained bulk in the tree.

### Notes

- `mcp/data/index.json`'s `generated_at` remains pinned to
  `1970-01-01T00:00:00Z`. A wall-clock timestamp would change the file on
  every rebuild, and the `--check` gate could no longer distinguish "the
  corpus changed" from "the clock moved". The intent is now documented
  where the field is emitted, in the builder and in the server.

## [1.4.0] — 2026-11-06

Stage 5 of the remediation: the corpus matches the project's own stated
constraints, and the check that was supposed to enforce them actually
enforces them.

### Fixed

- **The hosted-service check was passing because its pattern was
  incomplete, not because the corpus was clean.** It scanned for a list of
  literal API hostnames — `openai.com/v1`, `api.elevenlabs.io`,
  `fal.run` — and the corpus passed while containing `resend.com`,
  `videodb.io`, and `api.openai.com`, none of which matched. A check that
  reports a guarantee it is not keeping is worse than no check. The policy
  is now expressed as a list of services the corpus may not depend on, and
  every reference to one of them is a hit, matched by service name and API
  key variable rather than by URL. The new check was tested against
  samples of both kinds before it was adopted.
- **Four skills that depended on hosted services are no longer in the
  corpus.** `fal-ai-media` (fal.ai and ElevenLabs), `videodb` (a hosted
  video database with no self-hosted path), `email` (Resend, with a
  Vercel-specific workflow), and `social-publisher` (SocialClaw, a hosted
  workspace service). Each is listed in `mcp/data/excluded.json` with its
  reason, documented in `NOTICE`, and removed from the tree — the runtime
  is index-only, so a file that is not in the index cannot be served by
  any tool, and shipping it was shipping dead weight.
- **The coverage those skills provided was not lost.** `video-editing`
  gained a section on searching your own footage — transcript search over
  local Whisper output, and visual search over CLIP frame embeddings — with
  six new trigger phrases. The queries that used to reach `videodb` now
  reach `video-editing`, and four of them are pinned in the verification
  suite. `taste` and `video-editing` now point at
  `media-transcode-pipeline` where they pointed at `videodb`.
- **`taste` pointed at a section that no longer existed.** It referred to
  `video-editing (ElevenLabs section)`; `video-editing` has no such
  section and never did in its current form. Its voice reference now
  names the local skills that actually do it.
- **`website-to-hyperframes` offered hosted TTS as a peer option.** Its
  voice audition list put ElevenLabs and HeyGen next to the local engine.
  The hosted options are gone and the local ones — Kokoro and Piper — are
  named with the skills that cover the wider comparison.
- **`remotion-best-practices` pointed at a rewrite that had already
  happened.** Its rules index described `rules/voiceover.md` as "using
  ElevenLabs TTS" while that file had been rewritten to use local Piper
  and Kokoro. The index line now matches the file.
- **The remotion corpus had two copies of the same upstream rules.**
  `remotion-video-creation` and `remotion-best-practices` had
  near-identical descriptions and 28 shared rule files, and every shared
  file differed. `remotion-best-practices` is the newer revision — it
  additionally rewrote the captioning rule off the paid OpenAI Whisper
  API and onto local Whisper.cpp, and it carries ten rules the other
  lacks. It is now the only Remotion skill. The `assets/` directory of
  example components existed only in the older copy, and two links in the
  surviving skill pointed at it; it has been ported, which also fixed
  those two broken links. The nine cross-references to the retired skill
  now name the survivor.
- **`google-slides` now states its requirement instead of assuming it.**
  The skill's tool names are Codex's (`mcp__codex_apps__google_drive_*`)
  and it opened with "use this skill in Codex local-plugin sessions",
  which told a non-Codex client nothing about why it could not be used.
  It now names the capability it needs — a Google Slides connector — lists
  what that connector is called in each harness, and points at the
  harness-agnostic slide skills for clients that have none.
- **`imagegen` no longer assumes Codex.** Its description said "Use when
  Codex should create a brand-new image", and its save-path policy
  asserted a Codex path as fact. Both are now expressed as what the
  harness does, with the Codex path given as the concrete instance, and
  the skill points at `local-diffusion-suite` for users with no
  image-generation tool at all.

### Changed

- The corpus is now 64 skills and 15 agents, down from 68 and 15. Four
  skills were excluded for depending on hosted services and two Remotion
  skills were merged into one.
- The vendoring script no longer lists the excluded skills. Re-vendoring
  would have put them back on disk, where the index builder skips them
  but the files still ship.

### Tests

- The hosted-service check now names the services it forbids and scans for
  them. Two named services are exempt by pattern — `heygen-com` is the
  GitHub organisation that publishes Hyperframes, and
  `hyperframes.heygen.com` is that project's own host; neither is the
  HeyGen product API.
- A hosted path is allowed only where the skill is on an explicit
  allowlist, and each entry states why it qualifies. `imagegen` qualifies
  because its built-in tool is the default and the hosted CLI is only
  reachable on an explicit request; `local-tts-engines` qualifies because
  it names ElevenLabs to say "use this instead". The check also asserts
  that each allowlisted skill still documents a local default, so an
  exemption cannot outlive the thing that justified it.
- The required-capability list grew from 24 to 29, pinning the
  capabilities whose skills changed hands.

Verification: 94 tests pass, and the full local suite reports 1060 checks
passing. Both determinism gates pass — `index.json` is byte-identical to a
fresh build and `provenance.json` is up to date.

## [1.3.0] — 2026-11-06

Stage 4 of the remediation: the search ranker describes the corpus it is
ranking, the server counts the records it holds, and the transport stops
rebuilding what it does not need to rebuild.

### Fixed

- **The idf table now describes the corpus being ranked.** It was built
  from the whole corpus and then used to rank a filtered subset, so a
  token that was common across all 83 records but rare within, say, the
  five audio records scored as if it were distinctive — and a narrow
  modality search was weighted against its own corpus. It is now built
  from the filtered set.
- **Bigrams no longer straddle a field boundary.** They were built from
  the name and the description concatenated, so a skill named `video` with
  a description beginning "generate images" produced the bigram
  "video generate". Bigrams are now built per field.
- **`get_stats.by_source` counts the records the corpus actually holds.**
  It counted only skills, while its sibling `by_domain` counted skills
  and agents, so the two reported totals that disagreed — 36 against 48
  for an 83-record corpus — and neither said which basis it used. Both
  now count skills and agents, and the payload states the basis
  explicitly in `by_source_basis`.
- **An unknown licence is absent, not null.** `get_skill` emitted
  `license: null` while its neighbours emitted `[]` for absent lists.
  The field is now omitted from the index when there is no licence, so
  the API contract describes one convention.
- **A mis-installed server no longer serves the wrong corpus.** The
  project-root walk fell back to `MCP_ROOT`'s parent when it found no
  directory containing both `skills/` and `agents/`, which meant a
  mis-installed server could silently serve a *different* project's
  `skills/` directory. It now fails loudly with a message that says what
  went wrong and why the server refuses to guess.
- **The bundle manifest no longer stats a file twice.** It called
  `existsSync` and then `statSync` on the same path; the file can change
  between the two. It is one `stat` now, and `exists` reports whether
  the path is a file rather than whether it exists at all.

### Changed

- **The HTTP transport shares one server instance.** It constructed a
  fresh `McpServer` and re-registered all nine tools on every request,
  which was pure overhead and made the README's "one shared server"
  claim inaccurate. The server now holds no per-client state — its tools
  read the generated index and the filesystem, both shared by every
  caller — so it is built once. The *transport* is still per-request:
  that is what keeps the server stateless, and the stateless model is what
  lets any MCP client connect without a session handshake. Only the
  transport is closed on abort; closing the server would take down the
  whole listener.
- **`SkillFrontmatter` no longer has an open index signature.** The
  top-level `[key: string]: unknown` defeated the checking on every named
  field, since any typo would still typecheck. Vendored skills' extra
  keys (`metadata.origin`, `metadata.sources`) are still allowed, under
  `metadata`, where they live.
- **`descriptionOf` is inlined.** A one-line wrapper around `oneLine`
  that four call sites each spelled out differently.

### Tests

- `mcp/tests/protocol.test.js`: asserts that `by_source` and `by_domain`
  total to the same number as the corpus, and that an absent licence is
  reported as absent.
- `mcp/tests/search.test.js`: asserts that a modality-filtered search
  ranks within its own corpus and still surfaces the domain's own
  skills, and that filtering does not change the relative order of the
  results it returns.
- `mcp/tests/http.test.js`: eight sequential requests against one shared
  server instance all return correct answers, and a repeated query
  returns an identical count — so no state leaks between calls.

Verification: 94 tests pass, and the full local suite reports 1099 checks
passing. Both determinism gates pass — `index.json` is byte-identical to
a fresh build and `provenance.json` is up to date. The shared server was
also exercised live: three sequential `tools/call` requests against a
running `dist/http.js` returned identical, correct payloads.

## [1.2.0] — 2026-11-06

Stage 3 of the remediation: the renderer stops emitting broken output
silently, and the two rankers — skill search and agent skill-suggestion —
now answer the question they are asked.

### Fixed

- **Frontmatter that is not a mapping is now an error, not empty output.**
  `parseYaml(...) ?? {}` cast the result to `SkillFrontmatter` without
  checking it, so a YAML sequence or a bare scalar produced
  `## undefined` and reached the client as a broken render. The parser
  rejects it and the tool handler reports the failure as a tool error.
- **`agentsmd` renders the index id when the frontmatter has no name.** The
  marker comment is the documented replace-anchor, so
  `<!-- skills-library:name:undefined -->` meant a harness keying on that
  marker would never find the installed skill. The id is used for the
  marker, the heading, and the end marker.
- **`cursor-rules` keeps its structural blank lines.** The header was built
  by filtering every empty line out of the array, which collapsed the
  deliberate separators and took the conditional "Apply when:" line with
  them. The line is now omitted when it has no value, and the structural
  blank lines survive.
- **An empty `**Triggers:**` line is no longer emitted.** A skill with no
  trigger phrases rendered `**Triggers:** ` with a trailing space and no
  value, which reads as a truncation bug. The line is omitted entirely.
- **Render dialects prefer the curated trigger phrases.** The render paths
  read the file's own `metadata.promptSignals.phrases` while the index
  carries the curated `prompt_signals`; for vendored skills the two
  disagreed and the curated values were ignored. The curated list wins
  when it is non-empty.
- **The agent ranker no longer matches inside words.** Ranking used raw
  substring containment, so `video` matched inside `videography`, and
  `cinematic-video-editor` was pointed at `taste` — a music-video
  direction skill — instead of at `video-editing`. Matching is now on
  token boundaries.
- **The search phrase bonus is awarded once per document.** It was awarded
  per matching phrase, so a skill declaring six trigger phrases collected
  six times the bonus of a skill declaring one, for the same single
  matching word. "generate an image" ranked the image-CDN skill (six
  phrases containing "image") above the image-generation skill, whose
  trigger phrase is literally "generate an image". The bonus is now
  awarded once, on whole-word matches, scaled by how much of the query
  the phrase covers.
- **The authored/vendored bias no longer decides skill-versus-agent
  rankings.** It was a score component, so an authored agent outranked a
  vendored skill that matched identically — "edit a script" returned the
  agent that consults skills rather than the skill that does the work. The
  bias is now a tiebreak in the sort, where it cannot outrank a genuine
  difference in match quality.

### Added

- **`script-and-story-editing`** — a new authored skill for editing scripts,
  storyboards, voiceover copy and narrative structure. The corpus had no
  skill for it: the `script-and-story-editor` agent was pointed at
  `article-writing`, whose subject is long-form articles, not material that
  has to survive being performed or timed. The skill carries two reference
  files: beat-by-beat format shapes with word budgets, and hook and title
  patterns with their failure modes.
- **Curated trigger phrases for all 68 skills.** The vendored skills had
  trigger phrases derived mechanically from their filenames and
  descriptions, which matched almost nothing a client would say. Each now
  declares six or seven phrases written as the things a user would
  actually type. Both rankers key on this list, so it was the single
  largest source of bad rankings in the corpus.

### Changed

- **The ranker's stemmer no longer rewrites words that never lost a
  vowel.** The "restore the dropped e" rule existed to undo a silent-vowel
  loss caused by stripping `-ing` or `-ed`, but it fired unconditionally
  and turned `model` into `modele`, `rather` into `rathere`, and `plans`
  into `plane`. It now applies only where a vowel was actually dropped.
- **Token comparison tolerates the `-e` variants that no stemmer can
  distinguish.** `edit` and `writ` are irreducibly different to a stemmer;
  tokens are now compared through their variant sets, so an agent that
  says "editing" still reaches the editing skill.
- **Compound splitting is confined to skill ids.** `imagegen` is reached
  through its head `gen`, but `checkpoint` was being split into
  `check` and `point` and double-counted. A token that is itself a corpus
  word is never split.

### Tests

- New `mcp/tests/agents.test.js` pins the leading skill for all 15 agents.
  A wrong leading skill is not cosmetic: the client follows the
  suggestion, so an agent pointed at the wrong instructions is pointed
  away from its own subject. The table is the reviewable statement of what
  each agent is for; a reviewer reads it when the corpus or the ranker
  changes.
- `mcp/tests/render.test.js` gained assertions that a skill with a
  non-object frontmatter is an error, that a skill with no name renders the
  index id, that `cursor-rules` keeps its structural blank lines, that
  `agentsmd` with no triggers omits the `**Triggers:**` line, that every
  skill in the corpus has a name and a description, and that every skill
  declares at least three trigger phrases.
- `mcp/tests/search.test.js` gained a check that a capability query ranks
  the skill ahead of the agent that consults it, and a check that the
  prompt-signal phrase bonus is awarded once per document.

Verification: 89 tests pass, and the full local suite reports 1099 checks
passing. Both determinism gates pass — `index.json` is byte-identical to a
fresh build and `provenance.json` is up to date.

## [1.1.0] — 2026-11-06

Stage 2 of the remediation: makes the attribution record state what is
actually true about where the vendored content came from and which licence
governs it.

### Fixed

- **Licence detection no longer escapes the upstream tree.**
  `detect_license_near()` walked upward from a vendored directory until it
  found a licence file, and in nearly every case that was this repository's
  own root `LICENSE` (MIT). The search is now bounded so it cannot leave
  the tree it started in, and it consults package metadata when no licence
  file is present — the documented detection order was previously never
  reached, because the upward walk always succeeded first.
- **Licences are detected at the origin, not at the destination.** New
  `mcp/build/origins.py` resolves each vendored entry's true upstream tree
  and looks for the licence there. 29 of the 46 vendored entries have a
  licence that was detected upstream; the remaining 17 have none.
- **An unverified licence is recorded as `UNKNOWN`, never assumed.** The 17
  entries whose upstream carries no licence are published with verdict
  `needs-review` and are listed under "Unverified licence" in `CREDITS.md`,
  so the gap is visible instead of being absorbed into the totals.
- **Publishing an unverified entry now requires a sign-off.** `LICENCE_SIGNOFF`
  in `mcp/build/build_provenance.py` names the entries allowed to publish with
  an unverified licence. The build fails — in both write and `--check` mode —
  if an unverified entry is published without one, so an inherited MIT claim
  cannot be reintroduced silently.
- **Self-attribution removed from the index.** `build_index.py` resolved
  `upstream` by walking up from the *destination* directory, which found this
  repository's own remote and recorded 43 skills as originating from the
  project that merely redistributed them. The upstream is now read from the
  provenance table.
- **Owner derivation handles every URL shape.** `owner_from_upstream()`
  returned `github.com` for a bare `https://github.com/owner` path and an
  empty string for `https://github.com`. Both are now handled.
- **Absolute local paths no longer reach the published record.** `CREDITS.md`
  printed `/home/biloi/Projects/Skills_n_Agents/...` in its `Source:` lines.
  Origin paths are now recorded home-relative (`~/Projects/ECC`), which stays
  a usable locator without identifying the account that assembled the
  distribution. `Source:` lines prefer the upstream repository URL and
  otherwise describe the *kind* of origin rather than publishing a local path.
- **The authored/vendored classification was a latent bug.** The check tested
  the truthiness of a row's `source`, but authored rows carry the literal
  string `"authored"`, which is truthy — so authored content was classified
  as vendored. It now tests the `verdict`.

### Changed

- **Content-domain corrections.** The taxonomy in
  `mcp/build/content_domains.py` is the single source of truth for the
  `modality` filter, and two of its entries were wrong: `geist` is a UI
  typography skill (now `design`, was `writing`) and `taste` is a
  creative-direction layer for music video and short-form edits (now `video`,
  was `writing`).
- **The vendoring script no longer carries its own domain map.** It held a
  `MODALITY` map that had drifted from the taxonomy on 14 of 44 skills, so a
  re-vendoring would have silently reclassified content that clients already
  index by domain. The script now reads the taxonomy. It has moved from
  `.vendor_skills.py` to `tools/vendor_skills.py`.
- **Packaging fixed.** `mcp/pyproject.toml` pointed `readme` at `../README.md`,
  which is outside the package root and made the wheel unbuildable; the
  `Homepage` URL named the wrong repository; `packages = ["build"]` had no
  `__init__.py`, so the console-script entry points could not resolve; and
  `mcp/data/*.json` was not declared as package data, so an installed wheel
  shipped the build scripts without the files they read. All four are fixed
  and the wheel is now verified to contain the data files.

### Tests

- `tools/verify_all.py` now asserts the new provenance invariants: an
  unverified-licence entry must be signed off, a `needs-review` entry must not
  claim a licence that was never detected, and a published entry that claims a
  licence must name where it was detected. It also asserts that `CREDITS.md`,
  `index.json` and `provenance.json` carry no absolute home-directory paths.
- The sign-off list is read from `build_provenance.py` rather than duplicated,
  so the verification gate and the build gate cannot disagree.

Verification: 61 tests pass, and the full local suite reports 1084 checks
passing (up from 1061). Both determinism gates pass — `index.json` is
byte-identical to a fresh build and `provenance.json` is up to date.

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
- Local verification suite (`tools/verify_all.py`) running 1061 checks.
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

[Unreleased]: https://github.com/ashikonik/content-creation-mcp/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/ashikonik/content-creation-mcp/releases/tag/v1.5.0
[1.4.0]: https://github.com/ashikonik/content-creation-mcp/releases/tag/v1.4.0
[1.3.0]: https://github.com/ashikonik/content-creation-mcp/releases/tag/v1.3.0
[1.2.0]: https://github.com/ashikonik/content-creation-mcp/releases/tag/v1.2.0
[1.1.0]: https://github.com/ashikonik/content-creation-mcp/releases/tag/v1.1.0
[1.0.1]: https://github.com/ashikonik/content-creation-mcp/releases/tag/v1.0.1
[1.0.0]: https://github.com/ashikonik/content-creation-mcp/releases/tag/v1.0.0
