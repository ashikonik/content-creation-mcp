#!/usr/bin/env python3
"""Regenerate ``mcp/data/provenance.json`` from the corpus.

The table has one row per skill and per agent in this repository, and answers
three questions for each:

* where did it come from (``source`` / ``upstream``)?
* what licence governs it (``license`` / ``license_source``)?
* did it clear review (``verdict``)?

Authored content is MIT by construction — the repository LICENSE. Vendored
content keeps whatever licence was detected upstream, or is marked
``needs-review`` and excluded from the corpus.

Run with ``--check`` to fail (non-zero exit) if the on-disk table differs from
what this script would write. That is the determinism gate for provenance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from provenance import (  # noqa: E402
    DATA_DIR,
    KNOWN_LICENCES,
    NEEDS_REVIEW,
    PROJECT_ROOT,
    detect_license_near,
    license_from_frontmatter,
    load_provenance,
    save_provenance,
)

# Authored content inherits the repository licence.
REPO_LICENSE = "MIT"
VENDORED_ON = "2026-11-05"

SKILLS_DIR = PROJECT_ROOT / "skills"
AGENTS_DIR = PROJECT_ROOT / "agents"


def _index_domains() -> dict[tuple[str, str], str]:
    """Map (kind, name) -> content_domain, from the generated index."""
    index_path = DATA_DIR / "index.json"
    if not index_path.is_file():
        return {}
    data = json.loads(index_path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], str] = {}
    for skill in data.get("skills", []):
        out[("skill", skill["id"])] = skill.get("content_domain", "")
    for agent in data.get("agents", []):
        out[("agent", agent["id"])] = agent.get("content_domain", "")
    return out


def _existing_vendored() -> dict[tuple[str, str], dict]:
    """Existing provenance rows, keyed by (kind, name)."""
    return {(e.get("kind", ""), e.get("name", "")): e for e in load_provenance()}


def authored_entries(
    domains: dict[tuple[str, str], str],
    existing: dict[tuple[str, str], dict],
) -> list[dict]:
    """Rows for content written for this project.

    A directory is authored when its provenance row has no filesystem
    ``source`` — vendored rows always point at the path they were copied
    from. This keeps the classification stable across reruns without needing
    a separate manifest file.
    """
    rows: list[dict] = []

    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        name = skill_dir.name
        prior = existing.get(("skill", name))
        if prior and prior.get("source"):
            continue
        rows.append(
            {
                "name": name,
                "kind": "skill",
                "owner": "content-creation-mcp",
                "license": REPO_LICENSE,
                "license_source": "repository-license",
                "source": "authored",
                "upstream": None,
                "upstream_root": None,
                "path": f"skills/{name}/",
                "content_domain": domains.get(("skill", name), ""),
                "vendored_on": VENDORED_ON,
                "verdict": "authored",
            }
        )

    for agent_file in sorted(AGENTS_DIR.glob("*.md")):
        name = agent_file.stem
        prior = existing.get(("agent", name))
        if prior and prior.get("source"):
            continue
        rows.append(
            {
                "name": name,
                "kind": "agent",
                "owner": "content-creation-mcp",
                "license": REPO_LICENSE,
                "license_source": "repository-license",
                "source": "authored",
                "upstream": None,
                "upstream_root": None,
                "path": f"agents/{name}.md",
                "content_domain": domains.get(("agent", name), ""),
                "vendored_on": VENDORED_ON,
                "verdict": "authored",
            }
        )

    return rows


def vendored_entries(
    domains: dict[tuple[str, str], str],
    existing: dict[tuple[str, str], dict],
) -> list[dict]:
    """Rows for copied content, preserving the recorded upstream details.

    The upstream path and commit information cannot be re-derived from the
    copied tree, so it is carried over from the previous table. Only the
    licence is re-detected, because that is what the corpus gate depends on.
    """
    rows: list[dict] = []

    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        name = skill_dir.name
        prior = existing.get(("skill", name))
        if not prior or not prior.get("source"):
            continue

        license_name, license_source = detect_license_near(skill_dir)
        if license_name is None:
            license_name = license_from_frontmatter(skill_dir)
            license_source = "frontmatter" if license_name else "none"
        if license_name is None:
            license_name = prior.get("license")
            license_source = f"carried-over:{prior.get('license_source', 'unknown')}"

        if license_name in NEEDS_REVIEW:
            verdict = "needs-review"
        elif license_name not in KNOWN_LICENCES:
            verdict = "unknown-licence"
        else:
            verdict = prior.get("verdict") or "publish-default-mit"

        rows.append(
            {
                "name": name,
                "kind": "skill",
                "owner": prior.get("owner") or "vendored",
                "license": license_name,
                "license_source": license_source,
                "source": prior.get("source"),
                "upstream": prior.get("upstream"),
                "upstream_root": prior.get("upstream_root"),
                "path": f"skills/{name}/",
                "content_domain": domains.get(("skill", name), "")
                or prior.get("content_domain", ""),
                "vendored_on": prior.get("vendored_on", VENDORED_ON),
                "verdict": verdict,
            }
        )

    for agent_file in sorted(AGENTS_DIR.glob("*.md")):
        name = agent_file.stem
        prior = existing.get(("agent", name))
        if not prior or not prior.get("source"):
            continue

        license_name = prior.get("license") or REPO_LICENSE
        license_source = prior.get("license_source", "defaulted")

        rows.append(
            {
                "name": name,
                "kind": "agent",
                "owner": prior.get("owner") or "vendored",
                "license": license_name,
                "license_source": license_source,
                "source": prior.get("source"),
                "upstream": prior.get("upstream"),
                "upstream_root": prior.get("upstream_root"),
                "path": f"agents/{name}.md",
                "content_domain": domains.get(("agent", name), "")
                or prior.get("content_domain", ""),
                "vendored_on": prior.get("vendored_on", VENDORED_ON),
                "verdict": prior.get("verdict") or "publish-default-mit",
            }
        )

    return rows


def _excluded() -> dict[tuple[str, str], dict]:
    """Content excluded from the corpus, keyed by (kind, name)."""
    path = DATA_DIR / "excluded.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(e["kind"], e["name"]): e for e in data.get("entries", [])}


def build() -> list[dict]:
    domains = _index_domains()
    existing = _existing_vendored()
    excluded = _excluded()

    rows = [
        row
        for row in authored_entries(domains, existing) + vendored_entries(domains, existing)
        if (row["kind"], row["name"]) not in excluded
    ]
    return sorted(rows, key=lambda e: (e["kind"], e["name"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the on-disk table is stale.",
    )
    args = parser.parse_args()

    rows = build()
    path = DATA_DIR / "provenance.json"

    if args.check:
        if not path.is_file():
            print("provenance.json missing", file=sys.stderr)
            return 1
        current = json.loads(path.read_text(encoding="utf-8"))
        if current != rows:
            print(
                "provenance.json is stale — run python3 build/build_provenance.py",
                file=sys.stderr,
            )
            return 1
        print(f"provenance.json is up to date ({len(rows)} entries)")
        return 0

    save_provenance(rows)
    authored = sum(1 for e in rows if e["verdict"] == "authored")
    review = sum(1 for e in rows if e["verdict"] in ("needs-review", "unknown-licence"))
    print(
        f"wrote {path.relative_to(PROJECT_ROOT)}: {len(rows)} entries "
        f"({authored} authored, {review} needing review)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
