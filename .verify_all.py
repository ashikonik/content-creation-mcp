#!/usr/bin/env python3
"""End-to-end verification of the content-creation-mcp corpus and server.

Every check here is a gate, not a lint. A failure means the corpus or the
server is broken in a way a client would notice.

Run:

    python3 .verify_all.py

Exits non-zero on the first failing category, after running every check so
one run reports every problem rather than one at a time.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
MCP_DIR = PROJECT_ROOT / "mcp"
DATA_DIR = MCP_DIR / "data"
SKILLS_DIR = PROJECT_ROOT / "skills"
AGENTS_DIR = PROJECT_ROOT / "agents"

INDEX_PATH = DATA_DIR / "index.json"
PROVENANCE_PATH = DATA_DIR / "provenance.json"
HARNESSES_PATH = DATA_DIR / "harnesses.json"
CREDITS_PATH = PROJECT_ROOT / "CREDITS.md"

# The 24 capabilities the plan requires. Each must resolve to at least one
# skill in the corpus, and that skill must be searchable by a query that
# names the capability.
REQUIRED_CAPABILITIES: list[tuple[str, str, str]] = [
    # (capability, expected skill id, a query that should surface it)
    ("short-form video", "shorts-reels-pipeline", "make a reel for instagram"),
    ("local text-to-video", "text-to-video-local", "generate a video from a prompt locally"),
    ("comfyui video", "comfyui-video-workflows", "comfyui video workflow"),
    ("video upscale", "video-upscale-interpolate", "upscale a video and interpolate frames"),
    ("video background removal", "video-background-removal", "remove the background from a video"),
    ("comfyui image", "comfyui-image-workflows", "comfyui image workflow"),
    ("local diffusion", "local-diffusion-suite", "stable diffusion sdxl local image"),
    ("background removal", "background-removal-segmentation", "remove the background from a photo"),
    ("thumbnails", "thumbnail-generator", "make a thumbnail"),
    ("stock media", "stock-media-sourcing", "find stock footage"),
    ("local tts", "local-tts-engines", "text to speech local"),
    ("voice cloning", "voice-cloning-rvc", "clone a voice"),
    ("lip sync", "lip-sync", "lip sync"),
    ("music generation", "music-generation", "generate background music"),
    ("audio separation", "audio-separation", "separate vocals from a song"),
    ("subtitles", "subtitle-generation", "generate subtitles"),
    ("tts to video", "tts-to-video", "turn a script into a narrated video"),
    ("repurposing", "long-to-short-repurpose", "turn a podcast into vertical clips"),
    ("3d", "blender-3d-content", "blender 3d render"),
    ("slide decks", "agent-slide-decks", "slide deck"),
    ("diagrams", "diagram-generation", "generate a diagram"),
    ("social scheduling", "social-publish-scheduling", "schedule posts across platforms"),
    ("transcoding", "media-transcode-pipeline", "transcode for instagram"),
    ("dubbing", "video-translation-dubbing", "dub a video in another language"),
]

# The 12 agents the plan requires.
REQUIRED_AGENTS = {
    "short-form-producer",
    "cinematic-video-editor",
    "image-art-director",
    "comfyui-workflow-builder",
    "voice-and-sound-designer",
    "lip-sync-technician",
    "script-and-story-editor",
    "seo-content-strategist",
    "social-publish-manager",
    "media-pipeline-engineer",
    "thumbnail-designer",
    "stock-media-researcher",
}

RENDER_FORMATS = {"markdown", "claude-frontmatter", "openai-yaml", "agentsmd", "cursor-rules"}
CONTENT_DOMAINS = {
    "video",
    "image",
    "audio",
    "text",
    "3d",
    "design",
    "av_pipeline",
    "writing",
}


class Report:
    """Collects pass/fail results per category."""

    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def check(self, condition: bool, message: str) -> bool:
        self.checks += 1
        if not condition:
            self.failures.append(message)
        return condition

    def category(self, name: str) -> None:
        print(f"\n--- {name} ---")

    def ok(self, message: str) -> None:
        print(f"  ok    {message}")

    def fail(self, message: str) -> None:
        print(f"  FAIL  {message}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def licence_signoff() -> set[str]:
    """The names signed off for publication with an unverified licence.

    Read from ``LICENCE_SIGNOFF`` in the build script rather than
    duplicated here, so the verification gate and the build gate cannot
    disagree about what is allowed to publish.
    """
    build_dir = str(MCP_DIR / "build")
    if build_dir not in sys.path:
        sys.path.insert(0, build_dir)
    try:
        from build_provenance import LICENCE_SIGNOFF  # type: ignore

        return set(LICENCE_SIGNOFF)
    except Exception:
        return set()


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Read YAML frontmatter and split it from the body.

    Uses PyYAML when available so that block scalars (``>``, ``|``) are
    handled the same way the server's own parser handles them. Falls back to
    a minimal line reader when PyYAML is not installed.
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[4:end]
    body = text[end + 4 :].lstrip("\n")

    try:
        import yaml  # type: ignore

        data = yaml.safe_load(block)
        if not isinstance(data, dict):
            data = {}
        return data, body
    except ImportError:
        pass

    data: dict = {}
    current_key: str | None = None
    for line in block.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(stripped[2:].strip().strip("\"'"))
            continue
        if ":" in stripped and not line.startswith(" "):
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip("\"'")
            current_key = key
            if value:
                data[key] = value
            else:
                data[key] = ""
    return data, body


# --------------------------------------------------------------- checks


def check_frontmatter(report: Report, index: dict) -> None:
    report.category("frontmatter")
    skills = index.get("skills", [])
    agents = index.get("agents", [])

    for skill in skills:
        path = PROJECT_ROOT / skill["path"]
        if not report.check(path.is_file(), f"missing SKILL.md for {skill['id']}"):
            continue
        fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        report.check(
            bool(fm.get("name")),
            f"skill {skill['id']} has no name in frontmatter",
        )
        report.check(
            bool(fm.get("description")),
            f"skill {skill['id']} has no description in frontmatter",
        )
        report.check(
            len(fm.get("description", "")) > 20,
            f"skill {skill['id']} has a suspiciously short description",
        )

    for agent in agents:
        path = PROJECT_ROOT / agent["path"]
        if not report.check(path.is_file(), f"missing agent file for {agent['id']}"):
            continue
        fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        report.check(
            bool(fm.get("name")), f"agent {agent['id']} has no name in frontmatter"
        )
        report.check(
            bool(fm.get("description")),
            f"agent {agent['id']} has no description in frontmatter",
        )
        report.check(
            bool(fm.get("tools")), f"agent {agent['id']} has no tools in frontmatter"
        )

    report.ok(f"checked frontmatter for {len(skills)} skills and {len(agents)} agents")


def check_uniqueness(report: Report, index: dict) -> None:
    report.category("uniqueness")
    skill_ids = [s["id"] for s in index.get("skills", [])]
    agent_ids = [a["id"] for a in index.get("agents", [])]

    dupes = [k for k, v in Counter(skill_ids).items() if v > 1]
    report.check(not dupes, f"duplicate skill ids: {dupes}")

    agent_dupes = [k for k, v in Counter(agent_ids).items() if v > 1]
    report.check(not agent_dupes, f"duplicate agent ids: {agent_dupes}")

    excluded = excluded_skill_names()
    on_disk = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()} - excluded
    missing = set(skill_ids) - on_disk
    report.check(not missing, f"index lists skills not on disk: {sorted(missing)}")

    extra = on_disk - set(skill_ids)
    report.check(not extra, f"skills on disk missing from index: {sorted(extra)}")

    report.ok("ids are unique and the index matches the tree")


def check_references(report: Report, index: dict) -> None:
    report.category("references and scripts")
    for skill in index.get("skills", []):
        # skill["path"] points at SKILL.md; supporting files are relative to
        # its parent directory.
        base = (PROJECT_ROOT / skill["path"]).parent
        for ref in skill.get("references", []):
            report.check(
                (base / ref).is_file(),
                f"skill {skill['id']} references missing file {ref}",
            )
        for script in skill.get("scripts", []):
            report.check(
                (base / script).is_file(),
                f"skill {skill['id']} lists missing script {script}",
            )

        # Markdown links inside the body must resolve.
        skill_md = PROJECT_ROOT / skill["path"]
        if skill_md.is_file():
            text = skill_md.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^)#][^)]*)\)", text):
                if not is_checkable_link(link):
                    continue
                target = (base / link).resolve()
                report.check(
                    target.exists(),
                    f"skill {skill['id']} has a dead link to {link}",
                )

    report.ok("every referenced file and link resolves")


def is_checkable_link(link: str) -> bool:
    """Whether a markdown link target should exist on disk.

    Only links into the skill's own supporting directories are checked: those
    are the ones the index promises to serve via ``get_skill_bundle``. Links
    to arbitrary filenames (``hero.jpg``) are usually illustrative filenames
    inside a code example, not bundled assets.

    Also excludes URLs, non-file schemes (``plugin://``), bare anchors, and
    fragments that are clearly regex or template placeholders.
    """
    link = link.strip()
    if not link or link.startswith("#"):
        return False
    if "://" in link:
        return False
    if link.startswith(("mailto:", "tel:", "data:")):
        return False
    # Regex fragments and template placeholders: \d{3}, {name}, <id>, ...
    if re.search(r"[\\{}$<>]", link):
        return False
    return link.startswith(("references/", "scripts/", "assets/"))


def check_provenance(report: Report, index: dict) -> None:
    report.category("provenance")
    entries = load_json(PROVENANCE_PATH)
    by_key = {(e["kind"], e["name"]): e for e in entries}

    for skill in index.get("skills", []):
        key = ("skill", skill["id"])
        if not report.check(key in by_key, f"no provenance row for skill {skill['id']}"):
            continue
        entry = by_key[key]
        report.check(
            bool(entry.get("license")),
            f"provenance row for {skill['id']} has no licence",
        )
        report.check(
            bool(entry.get("verdict")),
            f"provenance row for {skill['id']} has no verdict",
        )

    for agent in index.get("agents", []):
        key = ("agent", agent["id"])
        if not report.check(key in by_key, f"no provenance row for agent {agent['id']}"):
            continue
        report.check(
            bool(by_key[key].get("license")),
            f"provenance row for {agent['id']} has no licence",
        )

    vendored = [e for e in entries if e.get("source") != "authored"]
    for entry in vendored:
        report.check(
            bool(entry.get("source")),
            f"vendored entry {entry['name']} has no recorded source path",
        )

    # An entry whose upstream licence could not be verified is published with
    # verdict "needs-review" and licence "UNKNOWN". Publishing it requires an
    # explicit human sign-off, recorded in LICENCE_SIGNOFF in
    # mcp/build/build_provenance.py. The check here mirrors that gate: it
    # fails if an unverified entry was published without a sign-off, and if
    # an entry carries a licence that was never actually detected.
    signoff = licence_signoff()
    for entry in vendored:
        verdict = entry.get("verdict")
        licence = entry.get("license") or ""
        if verdict != "needs-review":
            continue
        report.check(
            entry["name"] in signoff,
            f"vendored entry {entry['name']} is published with an unverified "
            f"licence and no sign-off",
        )
        report.check(
            licence == "UNKNOWN",
            f"vendored entry {entry['name']} is needs-review but records "
            f"licence {licence!r} — a needs-review entry must not claim a "
            f"licence that was never detected",
        )

    # Every vendored entry that claims a licence must name where that
    # licence was detected. "none" would mean the claim is unsupported.
    for entry in vendored:
        if entry.get("verdict") == "needs-review":
            continue
        report.check(
            (entry.get("license_source") or "none") != "none",
            f"vendored entry {entry['name']} claims licence "
            f"{entry.get('license')!r} but records no licence source",
        )

    report.ok(
        f"checked {len(entries)} provenance rows "
        f"({sum(1 for e in entries if e.get('source') == 'authored')} authored, "
        f"{len(vendored)} vendored, "
        f"{sum(1 for e in vendored if e.get('verdict') == 'needs-review')} "
        f"unverified-licence entries all signed off)"
    )


def check_no_local_paths(report: Report) -> None:
    """Published files must not carry the builder's absolute paths.

    ``CREDITS.md`` and ``index.json`` are shipped to consumers. The
    provenance table is internal, but it is published too, so its paths are
    checked as well — the origin locators are stored home-relative
    (``~/Projects/ECC``) precisely so the account name of whoever assembled
    the distribution is not part of the artefact.
    """
    report.category("no local path leakage")
    for path in (CREDITS_PATH, INDEX_PATH, PROVENANCE_PATH):
        text = path.read_text(encoding="utf-8")
        report.check(
            "/home/" not in text,
            f"{path.name} contains an absolute home-directory path",
        )
        report.check(
            "/Users/" not in text,
            f"{path.name} contains an absolute macOS home-directory path",
        )
    report.ok(
        "CREDITS.md, index.json and provenance.json carry no absolute "
        "home-directory paths"
    )


def check_capabilities(report: Report, index: dict) -> None:
    report.category("capability coverage")
    skill_ids = {s["id"] for s in index.get("skills", [])}

    for capability, expected, query in REQUIRED_CAPABILITIES:
        report.check(
            expected in skill_ids,
            f"capability '{capability}': expected skill '{expected}' is not in the corpus",
        )

    agent_ids = {a["id"] for a in index.get("agents", [])}
    for agent in sorted(REQUIRED_AGENTS):
        report.check(
            agent in agent_ids, f"required agent '{agent}' is not in the corpus"
        )

    report.ok(f"{len(REQUIRED_CAPABILITIES)} capabilities and {len(REQUIRED_AGENTS)} agents present")


def check_domains(report: Report, index: dict) -> None:
    report.category("content domains")
    for skill in index.get("skills", []):
        report.check(
            skill.get("content_domain") in CONTENT_DOMAINS,
            f"skill {skill['id']} has invalid content_domain "
            f"{skill.get('content_domain')!r}",
        )
    for agent in index.get("agents", []):
        report.check(
            agent.get("content_domain") in CONTENT_DOMAINS,
            f"agent {agent['id']} has invalid content_domain "
            f"{agent.get('content_domain')!r}",
        )
    report.ok("every record has a valid content_domain")


def check_harnesses(report: Report) -> None:
    report.category("harness registry")
    registry = load_json(HARNESSES_PATH)
    harnesses = registry.get("harnesses", {})
    for name, spec in harnesses.items():
        report.check("dirs" in spec, f"harness {name} has no dirs")
        report.check(
            "skill_format" in spec, f"harness {name} has no skill_format"
        )
        report.check(
            "agent_format" in spec, f"harness {name} has no agent_format"
        )
        report.check(
            spec.get("skill_format") in RENDER_FORMATS,
            f"harness {name} names unknown skill_format {spec.get('skill_format')!r}",
        )
        report.check(
            spec.get("agent_format") in RENDER_FORMATS,
            f"harness {name} names unknown agent_format {spec.get('agent_format')!r}",
        )

    # Every dialect the renderer supports must be reachable from the registry.
    for fmt in RENDER_FORMATS:
        report.check(
            fmt in registry.get("formats", {}),
            f"render format {fmt} has no entry in the harness registry",
        )

    report.ok(f"checked {len(harnesses)} harness dialects")


def check_version_consistency(report: Report, index: dict) -> None:
    """The project version must be the same everywhere it is written.

    The version appears in four places: the Node package manifest, the
    server's ``SERVER_VERSION`` constant, the generated index, and the
    Python distribution metadata. They were previously allowed to drift —
    the index said 1.0.0 while the server said 1.0.1 — so a client
    reporting the server's version had no way to tell which artifact it
    was talking about.
    """
    report.category("version consistency")

    package = load_json(MCP_DIR / "package.json")
    versions = {
        "mcp/package.json": package.get("version"),
        "mcp/data/index.json": index.get("version"),
    }

    server_src = (MCP_DIR / "src" / "server.ts").read_text(encoding="utf-8")
    match = re.search(r'const\s+SERVER_VERSION\s*=\s*"([^"]+)"', server_src)
    versions["mcp/src/server.ts"] = match.group(1) if match else None

    pyproject = (MCP_DIR / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    versions["mcp/pyproject.toml"] = match.group(1) if match else None

    for where, value in versions.items():
        report.check(bool(value), f"no version found in {where}")

    distinct = {v for v in versions.values() if v}
    report.check(
        len(distinct) == 1,
        "version strings disagree: "
        + ", ".join(f"{k}={v}" for k, v in sorted(versions.items())),
    )

    if len(distinct) == 1:
        report.ok(f"version {distinct.pop()} is consistent across all four files")


def check_index_determinism(report: Report) -> None:
    report.category("determinism")
    result = subprocess.run(
        [sys.executable, str(MCP_DIR / "build" / "build_index.py"), "--check"],
        capture_output=True,
        text=True,
    )
    report.check(
        result.returncode == 0,
        f"index.json is not reproducible: {result.stdout.strip()}{result.stderr.strip()}",
    )

    result = subprocess.run(
        [sys.executable, str(MCP_DIR / "build" / "build_provenance.py"), "--check"],
        capture_output=True,
        text=True,
    )
    report.check(
        result.returncode == 0,
        f"provenance.json is not reproducible: {result.stdout.strip()}{result.stderr.strip()}",
    )
    report.ok("index.json and provenance.json are byte-reproducible")


def check_server(report: Report) -> None:
    report.category("server")
    result = subprocess.run(
        ["npm", "test"],
        cwd=MCP_DIR,
        capture_output=True,
        text=True,
    )
    passed = re.search(r"^ℹ pass (\d+)$", result.stdout, re.M)
    failed = re.search(r"^ℹ fail (\d+)$", result.stdout, re.M)
    report.check(
        result.returncode == 0,
        f"npm test failed:\n{result.stdout[-3000:]}{result.stderr[-2000:]}",
    )
    if passed and failed:
        report.ok(f"server tests: {passed.group(1)} passed, {failed.group(1)} failed")


def check_search(report: Report) -> None:
    report.category("search ranking")
    """Each capability query must surface its skill through the real search."""
    result = subprocess.run(
        [
            "node",
            "-e",
            """
            const { Client } = require("@modelcontextprotocol/sdk/client/index.js");
            const { InMemoryTransport } = require("@modelcontextprotocol/sdk/inMemory.js");
            const { createServer } = require("./dist/server.js");
            (async () => {
              const [c, s] = InMemoryTransport.createLinkedPair();
              const server = createServer();
              await server.connect(s);
              const client = new Client({ name: "verify", version: "1.0.0" });
              await client.connect(c);
              const queries = JSON.parse(process.argv[1]);
              const out = {};
              for (const [key, q] of Object.entries(queries)) {
                const res = await client.callTool({
                  name: "search_skills",
                  arguments: { query: q, limit: 10 },
                });
                out[key] = JSON.parse(res.content[0].text).results.map(r => r.id);
              }
              console.log(JSON.stringify(out));
              await client.close();
              await server.close();
            })();
            """,
            json.dumps({cap: query for cap, _, query in REQUIRED_CAPABILITIES}),
        ],
        cwd=MCP_DIR,
        capture_output=True,
        text=True,
    )

    if not report.check(
        result.returncode == 0, f"search probe failed: {result.stderr[-2000:]}"
    ):
        return

    try:
        hits = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        report.check(False, f"could not parse search probe output: {result.stdout[:500]}")
        return

    for capability, expected, _ in REQUIRED_CAPABILITIES:
        ids = hits.get(capability, [])
        report.check(
            expected in ids,
            f"query for '{capability}' did not surface '{expected}' (got {ids})",
        )
    report.ok(f"{len(REQUIRED_CAPABILITIES)} capability queries resolve through search")


def check_no_paid_apis(report: Report) -> None:
    """The corpus is open/local only — no paid, hosted AI generation APIs.

    Free stock-media APIs (Pexels, Pixabay, Unsplash, Wikimedia Commons) are a
    different category: they serve open-licensed media rather than generating
    it, and are within scope. What is excluded is the paid generation and
    transcription tier — fal.ai, Replicate, OpenAI, ElevenLabs, and their
    equivalents.
    """
    report.category("open-source constraint")
    banned = re.compile(
        r"\b(replicate\.com|api\.deepai\.com|api\.deepai|openai\.com/v1|"
        r"api\.stability\.ai|dashscope\.com|api\.elevenlabs\.io|"
        r"api\.runwayml\.com|heygen\.com/api|api\.clipdrop\.com|"
        r"api\.groq\.com|fal\.run|fal\.ai)\b",
        re.I,
    )
    hits: list[str] = []
    for path in sorted(SKILLS_DIR.rglob("*.md")):
        # Excluded skills are not published and are not scanned.
        if any(
            path.is_relative_to(SKILLS_DIR / name)
            for name in excluded_skill_names()
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in banned.finditer(text):
            hits.append(f"{path.relative_to(PROJECT_ROOT)}: {match.group(0)}")
    report.check(not hits, f"hosted-only API references found: {hits}")
    report.ok("no hosted-only generation or transcription APIs referenced")


def excluded_skill_names() -> set[str]:
    """Skill names listed in the exclusion table."""
    path = DATA_DIR / "excluded.json"
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {e["name"] for e in data.get("entries", []) if e["kind"] == "skill"}


def check_exclusions(report: Report, index: dict) -> None:
    """Excluded content must not appear in the published index."""
    report.category("exclusions")
    path = DATA_DIR / "excluded.json"
    if not report.check(path.is_file(), "excluded.json is missing"):
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    report.check(bool(entries), "excluded.json lists no entries")

    indexed = {s["id"] for s in index.get("skills", [])}
    indexed |= {a["id"] for a in index.get("agents", [])}

    for entry in entries:
        report.check(
            bool(entry.get("reason")),
            f"excluded entry {entry['name']} has no reason",
        )
        report.check(
            entry["name"] not in indexed,
            f"excluded entry {entry['name']} is still in the published index",
        )

    # NOTICE must document every exclusion.
    notice = (PROJECT_ROOT / "NOTICE").read_text(encoding="utf-8")
    for entry in entries:
        report.check(
            entry["name"] in notice,
            f"excluded entry {entry['name']} is not documented in NOTICE",
        )

    report.ok(f"checked {len(entries)} exclusions")


def check_survey(report: Report) -> None:
    """The survey artifact must exist and be well-formed."""
    report.category("survey")
    jsonl = PROJECT_ROOT / "surveys" / "content_creation_github.jsonl"
    md = PROJECT_ROOT / "surveys" / "content_creation_github.md"

    if not report.check(jsonl.is_file(), "surveys/content_creation_github.jsonl missing"):
        return
    report.check(md.is_file(), "surveys/content_creation_github.md missing")

    count = 0
    summary = None
    unparseable = 0
    with jsonl.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                unparseable += 1
                continue
            if "_summary" in record:
                summary = record["_summary"]
            else:
                count += 1

    report.check(unparseable == 0, f"{unparseable} unparseable lines in the survey")
    report.check(count > 100, f"survey has only {count} repositories")
    report.check(summary is not None, "survey has no summary record")
    if summary:
        report.check(
            summary["counts"]["total"] == count,
            "survey summary count does not match the number of records",
        )
    report.ok(f"survey has {count} repositories")


def check_readme(report: Report, index: dict) -> None:
    """The README must not claim numbers the corpus does not have."""
    report.category("readme")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    skill_count = len(index.get("skills", []))
    agent_count = len(index.get("agents", []))

    report.check(
        f"{skill_count} skills" in readme,
        f"README does not state the skill count ({skill_count})",
    )
    report.check(
        f"{agent_count} agents" in readme,
        f"README does not state the agent count ({agent_count})",
    )

    # Every tool named in the README must actually be registered.
    for tool in (
        "search_skills",
        "get_skill",
        "get_skill_bundle",
        "list_skills",
        "get_agent",
        "render_skill",
        "run_agent",
        "list_modalities",
        "get_stats",
    ):
        report.check(tool in readme, f"README does not mention the {tool} tool")

    report.ok("README counts and tool list match the corpus")


def main() -> int:
    report = Report()

    if not INDEX_PATH.is_file():
        print(f"error: {INDEX_PATH} not found — run build/build_index.py", file=sys.stderr)
        return 1

    index = load_json(INDEX_PATH)

    check_frontmatter(report, index)
    check_uniqueness(report, index)
    check_references(report, index)
    check_provenance(report, index)
    check_no_local_paths(report)
    check_capabilities(report, index)
    check_domains(report, index)
    check_harnesses(report)
    check_exclusions(report, index)
    check_no_paid_apis(report)
    check_survey(report)
    check_readme(report, index)
    check_version_consistency(report, index)
    check_index_determinism(report)
    check_server(report)
    check_search(report)

    print("\n" + "=" * 60)
    if report.failures:
        print(f"FAILED: {len(report.failures)} of {report.checks} checks failed")
        for failure in report.failures:
            print(f"  - {failure}")
        return 1

    print(f"PASSED: all {report.checks} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
