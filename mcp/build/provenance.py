#!/usr/bin/env python3
"""Provenance and licence resolution.

Two distinct kinds of content live in this repository:

``authored``
    Written for this project. MIT, like the server code.

``vendored``
    Copied from an upstream repository. The upstream licence applies, and it
    is recorded per entry — the mix includes MIT, Apache-2.0, and others.

The important distinction, written into NOTICE: **documenting** a tool in a
skill is not the same as **vendoring** it. A skill that explains how to run
ComfyUI (GPL-3.0) does not import ComfyUI's code, so it does not inherit
ComfyUI's licence obligations. The skills we author are MIT. The skills we
copy keep their original licence.

Licence detection order for a vendored entry:

1. ``plugin.json`` in the skill directory
2. the nearest ``LICENSE`` / ``LICENSE.txt`` / ``COPYING`` file
3. package metadata (``package.json``, ``pyproject.toml``)
4. the skill's own frontmatter ``license:`` field

Entries with no detectable licence are excluded from the corpus and listed in
NOTICE. That exclusion is intentional, not a bug to work around.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_DIR = PROJECT_ROOT / "mcp"
DATA_DIR = MCP_DIR / "data"

# Licences we accept. Anything else is reported for manual review.
KNOWN_LICENCES = {
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "BSD-2-Clause",
    "GPL-3.0",
    "AGPL-3.0",
    "CC-BY-4.0",
    "CC0-1.0",
    "Unlicense",
    "MPL-2.0",
    "ISC",
}

# Licences that need a human decision before inclusion.
NEEDS_REVIEW = {"CC-BY-4.0", "NOASSERTION", "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0"}

LICENSE_FILES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "LICENSE.rst")

# A ``license:`` frontmatter field that points at a licence file rather than
# naming one. These are not licence identifiers and must not be recorded as
# the licence of an entry.
LICENSE_POINTER_RE = re.compile(
    r"\b(?:see|refer to|in|under|per|as|terms\s+in|full\s+terms|"
    r"complete\s+terms|license\s+file|licence\s+file)\b|"
    r"license\.(?:txt|md|rst)|licence\.(?:txt|md|rst)|"
    r"\bLICENSE\b|\bCOPYING\b",
    re.I,
)

# Ordered most-specific-first: a specific licence beats a generic one.
LICENSE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AGPL-3.0", re.compile(r"Affero General Public License", re.I)),
    ("AGPL-3.0", re.compile(r"\bAGPL\b", re.I)),
    ("GPL-3.0", re.compile(r"GNU GENERAL PUBLIC LICENSE\s+Version 3", re.I)),
    ("GPL-3.0", re.compile(r"\bGPL\b|\bGPLv3\b", re.I)),
    ("Apache-2.0", re.compile(r"Apache License\s+Version 2\.0", re.I)),
    ("Apache-2.0", re.compile(r"\bApache-2\.0\b", re.I)),
    ("BSD-3-Clause", re.compile(r"Redistribution and use in source and binary forms", re.I)),
    ("BSD-3-Clause", re.compile(r"\bBSD-3-Clause\b", re.I)),
    ("BSD-2-Clause", re.compile(r"\bBSD-2-Clause\b", re.I)),
    ("MPL-2.0", re.compile(r"Mozilla Public License", re.I)),
    ("CC0-1.0", re.compile(r"CC0 1\.0|Creative Commons Zero", re.I)),
    ("CC-BY-4.0", re.compile(r"Creative Commons Attribution 4\.0", re.I)),
    ("CC-BY-NC-4.0", re.compile(r"Attribution-NonCommercial 4\.0", re.I)),
    ("CC-BY-NC-SA-4.0", re.compile(r"Attribution-NonCommercial-ShareAlike 4\.0", re.I)),
    ("Unlicense", re.compile(r"This is free and unencumbered software", re.I)),
    ("ISC", re.compile(r"ISC License|Permission to use, copy, modify, and/or distribute", re.I)),
    ("MIT", re.compile(r"Permission is hereby granted, free of charge", re.I)),
    ("MIT", re.compile(r"\bMIT License\b", re.I)),
]


def detect_license_text(text: str) -> str | None:
    """Identify a licence from its text."""
    for name, pattern in LICENSE_PATTERNS:
        if pattern.search(text):
            return name
    return None


def detect_license_near(skill_dir: Path, stop_at: Path | None = None) -> tuple[str | None, str]:
    """Find the licence governing a skill directory.

    The search walks up from ``skill_dir`` but never past ``stop_at``
    (defaulting to ``skill_dir`` itself). Without that bound the walk
    climbs out of the vendored tree and into this repository, where it
    finds this project's own MIT LICENSE and reports it as the upstream
    licence — which it is not.

    Returns ``(licence, source_description)``.
    """
    # 1. plugin.json
    plugin = skill_dir / "plugin.json"
    if plugin.is_file():
        try:
            data = json.loads(plugin.read_text(encoding="utf-8"))
            lic = data.get("license") or data.get("licence")
            if isinstance(lic, str) and lic.strip():
                return lic.strip(), "plugin.json"
        except (json.JSONDecodeError, OSError):
            pass

    # 2. nearest LICENSE file, walking up — but only within the bounded
    #    subtree. The bound is what stops this repository's own licence
    #    from being attributed to the upstream.
    boundary = (stop_at or skill_dir).resolve()
    current = skill_dir.resolve()
    for _ in range(8):
        for name in LICENSE_FILES:
            candidate = current / name
            if candidate.is_file():
                try:
                    found = detect_license_text(candidate.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    found = None
                if found:
                    return found, _describe_licence_source(candidate)
        if current == boundary or current.parent == current:
            break
        current = current.parent

    # 3. package metadata
    pkg = skill_dir / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            lic = data.get("license")
            if isinstance(lic, str) and lic.strip():
                return lic.strip(), "package.json"
        except (json.JSONDecodeError, OSError):
            pass

    return None, "none"


def _describe_licence_source(candidate: Path) -> str:
    """Describe where a licence file was found, without losing the path.

    A path inside the project is reported relative to the project root; a
    path outside it is reported absolutely, so the reader can tell that the
    licence came from somewhere other than this repository.
    """
    try:
        return str(candidate.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(candidate)


def license_from_frontmatter(skill_dir: Path) -> str | None:
    """Read the ``license:`` field from a SKILL.md or agent frontmatter.

    Only a recognised licence name is returned. A ``license:`` field is not
    always a licence: some skills write a pointer instead, such as
    ``license: Complete terms in LICENSE.txt`` or ``license: See LICENSE``.
    Recording one of those as the licence puts a sentence where an SPDX
    identifier belongs, and the entry then fails the known-licence check
    while looking like it had one.

    A pointer is not discarded here — it says the licence lives in a file
    that is not next to the skill. It is simply not an answer, so the
    caller keeps looking.
    """
    for name in ("SKILL.md",):
        path = skill_dir / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r"^license:\s*(.+?)\s*$", text, re.M)
        if not match:
            continue
        value = match.group(1).strip().strip("\"'")
        if value in KNOWN_LICENCES:
            return value
        # A pointer to a licence file, or a licence named in a form this
        # table does not carry. Neither is an identifier.
        if LICENSE_POINTER_RE.search(value):
            continue
        return value
    return None


def find_upstream(path: Path) -> str | None:
    """Find the upstream git remote for a directory by walking up."""
    current = path.resolve()
    for _ in range(8):
        git_config = current / ".git" / "config"
        if git_config.is_file():
            try:
                text = git_config.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return None
            match = re.search(r"url\s*=\s*(\S+)", text)
            if match:
                url = match.group(1)
                url = url.removesuffix(".git")
                return url
        if current.parent == current:
            break
        current = current.parent
    return None


def load_provenance() -> list[dict]:
    """Load the provenance table, if it exists."""
    path = DATA_DIR / "provenance.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_provenance(entries: list[dict]) -> None:
    """Write the provenance table, sorted for a stable diff."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entries = sorted(entries, key=lambda e: (e.get("kind", ""), e.get("name", "")))
    path = DATA_DIR / "provenance.json"
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def entries_needing_review(entries: list[dict]) -> list[dict]:
    """Entries whose licence is not in the known set, or needs a decision."""
    out = []
    for entry in entries:
        lic = (entry.get("license") or "").strip()
        if not lic or lic in NEEDS_REVIEW or lic not in KNOWN_LICENCES:
            out.append(entry)
    return out
