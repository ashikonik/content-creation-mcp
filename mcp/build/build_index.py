#!/usr/bin/env python3
"""Build the generated index.

Reads ``skills/`` and ``agents/`` from the project root and writes
``mcp/data/index.json``. The output is deterministic: running it twice on an
unchanged tree produces byte-identical files.

Usage:
    python3 build/build_index.py            # write the index
    python3 build/build_index.py --check    # verify determinism
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_domains import (  # noqa: E402
    domain_for_agent,
    domain_for_skill,
    stale_entries,
    unmapped_agents,
    unmapped_skills,
)
from provenance import (  # noqa: E402
    detect_license_near,
    find_upstream,
    license_from_frontmatter,
    load_provenance,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"
AGENTS_DIR = PROJECT_ROOT / "agents"
DATA_DIR = PROJECT_ROOT / "mcp" / "data"
INDEX_PATH = DATA_DIR / "index.json"
EXCLUDED_PATH = DATA_DIR / "excluded.json"

INDEX_VERSION = "1.1.0"


def provenance_upstream() -> dict[tuple[str, str], dict]:
    """The provenance table, keyed by (kind, name).

    The upstream remote is read from here rather than by walking up from the
    destination directory: the copy lives inside this repository, so that
    walk finds *this* repository's remote and records every vendored skill
    as originating from the project that merely redistributed it.
    """
    return {
        (e.get("kind", ""), e.get("name", "")): e
        for e in load_provenance()
    }


def owner_from_upstream(upstream: str | None) -> str | None:
    """The owner segment of a repository URL.

    Handles the shapes that actually occur: ``https://host/owner/repo``,
    ``https://host/owner``, and a bare host.
    """
    if not upstream:
        return None
    trimmed = upstream.rstrip("/")
    parts = trimmed.split("/")
    if len(parts) >= 2:
        candidate = parts[-2]
        if candidate and candidate not in ("", "github.com", "gitlab.com", "bitbucket.org"):
            return candidate
    return None


def load_excluded() -> dict[tuple[str, str], dict]:
    """Content excluded from the corpus, keyed by (kind, name)."""
    if not EXCLUDED_PATH.is_file():
        return {}
    data = json.loads(EXCLUDED_PATH.read_text(encoding="utf-8"))
    return {(e["kind"], e["name"]): e for e in data.get("entries", [])}

FRONTMATTER_RE = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?", re.M)

# Authored skills — the ones written for this project. Everything else under
# skills/ was vendored from an upstream repository.
AUTHORED_SKILLS = {
    "shorts-reels-pipeline",
    "text-to-video-local",
    "comfyui-video-workflows",
    "video-upscale-interpolate",
    "video-background-removal",
    "comfyui-image-workflows",
    "local-diffusion-suite",
    "background-removal-segmentation",
    "thumbnail-generator",
    "stock-media-sourcing",
    "local-tts-engines",
    "voice-cloning-rvc",
    "lip-sync",
    "music-generation",
    "audio-separation",
    "subtitle-generation",
    "tts-to-video",
    "long-to-short-repurpose",
    "blender-3d-content",
    "agent-slide-decks",
    "diagram-generation",
    "social-publish-scheduling",
    "media-transcode-pipeline",
    "video-translation-dubbing",
}

AUTHORED_AGENTS = {
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

# Files that are not content.
SKIP_NAMES = {"__pycache__", "node_modules", ".git", ".DS_Store", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def parse_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter.

    PyYAML is required, not optional. A hand-rolled reader cannot handle
    block scalars (``>``, ``|``) or escaped quotes, and a skill whose
    description parsed to the literal string ``">"`` would be invisible to
    search — a silent failure that is much worse than a hard import error.

    The MCP server reads the same files with the same library, so the index
    and the server always agree.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}

    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        return {}
    return _normalise_lists(data)


def _scalar(value: str):
    """Convert a YAML scalar to a Python value."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value in ("null", "~", ""):
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in inner.split(",")]
    return value


def _normalise_lists(node):
    """Drop empty dicts that were placeholders for lists, recursing."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if isinstance(value, dict) and not value:
                # An empty dict where a list was expected is an empty list.
                out[key] = []
            else:
                out[key] = _normalise_lists(value)
        return out
    return node


def extract_phrases(frontmatter: dict) -> list[str]:
    """Pull promptSignals.phrases out of the parsed frontmatter."""
    phrases: list[str] = []

    metadata = frontmatter.get("metadata")
    if isinstance(metadata, dict):
        signals = metadata.get("promptSignals")
        if isinstance(signals, dict):
            raw = signals.get("phrases")
            if isinstance(raw, list):
                phrases.extend(str(p).strip() for p in raw)
            elif isinstance(raw, str) and raw:
                phrases.extend(p.strip() for p in raw.split(","))
        elif isinstance(signals, list):
            phrases.extend(str(p).strip() for p in signals)

    direct = frontmatter.get("promptSignals")
    if isinstance(direct, dict):
        raw = direct.get("phrases")
        if isinstance(raw, list):
            phrases.extend(str(p).strip() for p in raw)
    elif isinstance(direct, list):
        phrases.extend(str(p).strip() for p in direct)

    seen: set[str] = set()
    out: list[str] = []
    for phrase in phrases:
        if not phrase:
            continue
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(phrase)
    return out


def supporting_files(skill_dir: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (all, references, scripts) relative to the skill directory."""
    all_files: list[str] = []
    references: list[str] = []
    scripts: list[str] = []

    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_NAMES for part in path.parts):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        if path.name == "SKILL.md":
            continue

        rel = path.relative_to(skill_dir).as_posix()
        all_files.append(rel)
        if rel.startswith("references/"):
            references.append(rel)
        elif rel.startswith("scripts/"):
            scripts.append(rel)

    return all_files, references, scripts


def build_skills() -> tuple[list[dict], list[str]]:
    """Build the skill records. Returns (records, warnings)."""
    records: list[dict] = []
    warnings: list[str] = []
    excluded = load_excluded()
    prov = provenance_upstream()

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in SKIP_NAMES:
            continue
        if ("skill", skill_dir.name) in excluded:
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            warnings.append(f"{skill_dir.name}: no SKILL.md, skipped")
            continue

        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)

        name = str(fm.get("name", "")).strip()
        description = str(fm.get("description", "")).strip()

        if not name:
            warnings.append(f"{skill_dir.name}: frontmatter missing 'name'")
            continue
        if not description:
            warnings.append(f"{skill_dir.name}: frontmatter missing 'description'")
            continue

        domain = domain_for_skill(skill_dir.name)
        if domain is None:
            warnings.append(f"{skill_dir.name}: no content_domain in taxonomy")
            continue

        authored = skill_dir.name in AUTHORED_SKILLS
        license_value = license_from_frontmatter(skill_dir) if authored else None
        if not authored:
            license_value, _ = detect_license_near(skill_dir)
            if not license_value:
                license_value = license_from_frontmatter(skill_dir)

        all_files, references, scripts = supporting_files(skill_dir)
        upstream = None
        owner = None
        if not authored:
            # The upstream remote comes from the provenance table, which
            # records where the content was copied from.
            row = prov.get(("skill", skill_dir.name))
            upstream = (row or {}).get("upstream")
            owner = owner_from_upstream(upstream)

        body_start = FRONTMATTER_RE.match(text)
        body = text[body_start.end():] if body_start else text

        records.append(
            {
                "id": skill_dir.name,
                "name": name,
                "description": description,
                "content_domain": domain,
                "source": "authored" if authored else "vendored",
                "license": license_value,
                "prompt_signals": extract_phrases(fm),
                "path": f"skills/{skill_dir.name}/SKILL.md",
                "files": all_files,
                "references": references,
                "scripts": scripts,
                "body_chars": len(body),
                **({"upstream": upstream} if upstream else {}),
                **({"upstream_owner": owner} if owner else {}),
            }
        )

    return records, warnings


def build_agents() -> tuple[list[dict], list[str]]:
    """Build the agent records. Returns (records, warnings)."""
    records: list[dict] = []
    warnings: list[str] = []
    excluded = load_excluded()
    prov = provenance_upstream()

    for agent_file in sorted(AGENTS_DIR.glob("*.md")):
        agent_id = agent_file.stem
        if ("agent", agent_id) in excluded:
            continue
        text = agent_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)

        name = str(fm.get("name", "")).strip()
        description = str(fm.get("description", "")).strip()
        tools_raw = fm.get("tools", "")
        model = str(fm.get("model", "")).strip()

        if not name:
            warnings.append(f"{agent_id}: frontmatter missing 'name'")
            continue
        if not description:
            warnings.append(f"{agent_id}: frontmatter missing 'description'")
            continue
        if not tools_raw:
            warnings.append(f"{agent_id}: frontmatter missing 'tools'")
            continue

        tools = []
        if isinstance(tools_raw, list):
            tools = [str(t).strip() for t in tools_raw]
        else:
            tools = [t.strip().strip("\"'") for t in tools_raw.split(",") if t.strip()]
        tools = [t for t in tools if t]

        domain = domain_for_agent(agent_id)
        if domain is None:
            warnings.append(f"{agent_id}: no content_domain in taxonomy")
            continue

        authored = agent_id in AUTHORED_AGENTS
        license_value = None
        upstream = None
        owner = None
        if not authored:
            license_value, _ = detect_license_near(agent_file.parent)
            row = prov.get(("agent", agent_id))
            upstream = (row or {}).get("upstream")
            owner = owner_from_upstream(upstream)

        body_start = FRONTMATTER_RE.match(text)
        body = text[body_start.end():] if body_start else text

        records.append(
            {
                "id": agent_id,
                "name": name,
                "description": description,
                "content_domain": domain,
                "tools": tools,
                "model": model or "inherit",
                "source": "authored" if authored else "vendored",
                "license": license_value,
                "path": f"agents/{agent_id}.md",
                "files": [],
                "prompt_signals": [],
                "body_chars": len(body),
                **({"upstream": upstream} if upstream else {}),
                **({"upstream_owner": owner} if owner else {}),
            }
        )

    return records, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the content index.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the existing index is byte-identical to a fresh build.",
    )
    args = parser.parse_args()

    skills, skill_warnings = build_skills()
    agents, agent_warnings = build_agents()
    warnings = skill_warnings + agent_warnings

    skill_ids = [s["id"] for s in skills]
    agent_ids = [a["id"] for a in agents]

    unmapped_s = unmapped_skills(skill_ids)
    unmapped_a = unmapped_agents(agent_ids)
    excluded_names = {name for kind, name in load_excluded() if kind == "skill"}
    stale = stale_entries(skill_ids, agent_ids, excluded_names)

    if unmapped_s:
        warnings.append(f"skills with no taxonomy entry: {', '.join(unmapped_s)}")
    if unmapped_a:
        warnings.append(f"agents with no taxonomy entry: {', '.join(unmapped_a)}")
    if stale["skills"]:
        warnings.append(f"taxonomy entries with no skill: {', '.join(stale['skills'])}")
    if stale["agents"]:
        warnings.append(f"taxonomy entries with no agent: {', '.join(stale['agents'])}")

    by_domain: dict[str, int] = {}
    for record in skills + agents:
        domain = record["content_domain"]
        by_domain[domain] = by_domain.get(domain, 0) + 1

    index = {
        "version": INDEX_VERSION,
        "generated_at": "1970-01-01T00:00:00Z",  # fixed for determinism
        "project_root": ".",
        "counts": {
            "skills": len(skills),
            "agents": len(agents),
            "by_domain": dict(sorted(by_domain.items())),
        },
        "skills": skills,
        "agents": agents,
    }

    payload = json.dumps(index, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

    if args.check:
        if not INDEX_PATH.is_file():
            print("FAIL: index.json does not exist", file=sys.stderr)
            return 1
        existing = INDEX_PATH.read_text(encoding="utf-8")
        if existing != payload:
            print("FAIL: index.json is not deterministic", file=sys.stderr)
            return 1
        print("OK: index.json is byte-identical to a fresh build")
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(payload, encoding="utf-8")

    print(f"wrote {INDEX_PATH.relative_to(PROJECT_ROOT)}")
    print(f"  {len(skills)} skills, {len(agents)} agents")
    for domain, count in sorted(by_domain.items()):
        print(f"    {domain:<12} {count}")

    if warnings:
        print("\nwarnings:", file=sys.stderr)
        for warning in warnings:
            print(f"  - {warning}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
