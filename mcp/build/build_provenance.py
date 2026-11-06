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

from origins import (  # noqa: E402
    UNKNOWN_LICENCE,
    relativise,
    resolve_licence,
    resolve_source,
)
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

# Vendored entries whose upstream licence could not be determined.
#
# These are published with licence "UNKNOWN" and verdict "needs-review".
# The list below is the explicit human sign-off: an entry may only appear
# in the published corpus if it is named here. Adding a name here is a
# deliberate decision to publish an item of unverified licence; removing
# one withdraws that decision.
#
# This gate exists because the previous behaviour silently attributed this
# repository's MIT licence to 64 rows, including 43 whose upstream had no
# discoverable licence at all.
LICENCE_SIGNOFF: set[str] = {
    "canva-branded-presentation",
    "draft-brief",
    "draft-long-form-memo",
    "geist",
    "google-slides",
    "humanizer",
    "hyperframes",
    "hyperframes-cli",
    "hyperframes-registry",
    "node-link-and-diagram-layout",
    "remotion-best-practices",
    "reports-pdfs-and-slide-automation",
    "sprite-pipeline",
    "uml-and-software-architecture-visualization",
    "web-3d-asset-pipeline",
    "website-to-hyperframes",
}

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

    A directory is authored when its provenance row records no vendored
    origin. The check is on the ``verdict`` rather than on the truthiness
    of ``source``: an authored row carries the literal string ``"authored"``
    as its source, which is truthy, so a truthiness test would classify
    authored content as vendored.
    """
    rows: list[dict] = []

    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        name = skill_dir.name
        prior = existing.get(("skill", name))
        if prior and prior.get("verdict") != "authored":
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
        if prior and prior.get("verdict") != "authored":
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
    """Rows for copied content.

    The licence is resolved from the *origin* of the copy, not from the
    directory it now lives in. Where no upstream licence can be found the
    entry is recorded as UNKNOWN with verdict ``needs-review``, rather
    than inheriting this repository's licence.
    """
    rows: list[dict] = []

    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        name = skill_dir.name
        prior = existing.get(("skill", name))
        if not prior or prior.get("verdict") == "authored":
            continue

        license_name, license_source = resolve_licence(prior)
        if license_name == UNKNOWN_LICENCE:
            verdict = "needs-review"
        elif license_name in NEEDS_REVIEW:
            verdict = "needs-review"
        elif license_name not in KNOWN_LICENCES:
            verdict = "unknown-licence"
        else:
            verdict = "publish"

        rows.append(
            {
                "name": name,
                "kind": "skill",
                "owner": prior.get("owner") or "vendored",
                "license": license_name,
                "license_source": license_source,
                "source": resolve_source(prior),
                "upstream": prior.get("upstream"),
                "upstream_root": (
                    relativise(prior["upstream_root"])
                    if prior.get("upstream_root")
                    else None
                ),
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
        if not prior or prior.get("verdict") == "authored":
            continue

        license_name, license_source = resolve_licence(prior)
        if license_name == UNKNOWN_LICENCE:
            verdict = "needs-review"
        elif license_name in NEEDS_REVIEW:
            verdict = "needs-review"
        elif license_name not in KNOWN_LICENCES:
            verdict = "unknown-licence"
        else:
            verdict = "publish"

        rows.append(
            {
                "name": name,
                "kind": "agent",
                "owner": prior.get("owner") or "vendored",
                "license": license_name,
                "license_source": license_source,
                "source": resolve_source(prior),
                "upstream": prior.get("upstream"),
                "upstream_root": (
                    relativise(prior["upstream_root"])
                    if prior.get("upstream_root")
                    else None
                ),
                "path": f"agents/{name}.md",
                "content_domain": domains.get(("agent", name), "")
                or prior.get("content_domain", ""),
                "vendored_on": prior.get("vendored_on", VENDORED_ON),
                "verdict": verdict,
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


def unlicensed_without_signoff(rows: list[dict]) -> list[str]:
    """Entries published with an unverified licence but no sign-off.

    An entry whose licence resolved to UNKNOWN may only be published if it
    is named in ``LICENCE_SIGNOFF``. Anything else is a build failure —
    the alternative is silently attributing a licence nobody verified.
    """
    out = []
    for row in rows:
        if row.get("verdict") != "needs-review":
            continue
        if (row.get("license") or "") != UNKNOWN_LICENCE:
            continue
        if row.get("name") not in LICENCE_SIGNOFF:
            out.append(f"{row['kind']}:{row['name']}")
    return sorted(out)


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

    # The gate applies in both modes: --check must fail on a table that
    # contains an unlicensed entry without sign-off, not just on a stale
    # table.
    #
    # Every failure is reported, not just the first. Removing a licence file
    # that the corpus ships makes the table stale *and* leaves an entry
    # without a verified licence, and the person fixing it needs to know
    # both. Reporting one and stopping would send them to fix a table that
    # was not the problem.
    failed = False

    unsigned = unlicensed_without_signoff(rows)
    if unsigned:
        failed = True
        print(
            "provenance: entries published with an unverified licence and no "
            "sign-off in LICENCE_SIGNOFF:\n  "
            + "\n  ".join(unsigned),
            file=sys.stderr,
        )

    if args.check:
        if not path.is_file():
            print("provenance.json missing", file=sys.stderr)
            return 1
        current = json.loads(path.read_text(encoding="utf-8"))
        if current != rows:
            failed = True
            print(
                "provenance.json is stale — run python3 build/build_provenance.py",
                file=sys.stderr,
            )
        if not failed:
            print(f"provenance.json is up to date ({len(rows)} entries)")
        return 1 if failed else 0

    save_provenance(rows)
    authored = sum(1 for e in rows if e["verdict"] == "authored")
    review = sum(1 for e in rows if e["verdict"] in ("needs-review", "unknown-licence"))
    unlicensed = sum(
        1 for e in rows if (e.get("license") or "") == UNKNOWN_LICENCE
    )
    print(
        f"wrote {path.relative_to(PROJECT_ROOT)}: {len(rows)} entries "
        f"({authored} authored, {review} needing review, "
        f"{unlicensed} with an unverified licence)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
