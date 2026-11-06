#!/usr/bin/env python3
"""Origin resolution for vendored content.

A vendored entry's *true* origin is not the directory it was copied into —
it is the upstream tree it was copied *from*. The copy sits inside this
repository, so walking up from it finds this repository's own LICENSE and
attributes the upstream's licence to the project that merely redistributed
it.

The ground truth is recorded in the provenance table's ``upstream_root``
field, which names the upstream container (a plugin root, a repository
root). This module resolves that container to a licence by looking for a
LICENSE file at that origin, and reports honestly when there is none.

The resolution order for a vendored entry is:

1. the plugin/repository root named by ``upstream_root``
2. the library manifest's ``source`` field, when it names a real tree
3. package metadata in the origin directory
4. the skill's own frontmatter ``license:`` field

When none of those yields a licence, the entry is reported as
``UNKNOWN`` with verdict ``needs-review``. It is never silently given this
repository's licence.
"""

from __future__ import annotations

import json
from pathlib import Path

from provenance import (
    LICENSE_FILES,
    detect_license_text,
    license_from_frontmatter,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "mcp" / "data"

# The local library that recorded where each vendored item was copied from.
# It is a development-time input, not a runtime dependency: when it is
# absent, resolution falls back to the provenance table's upstream_root.
LIBRARY_MANIFEST = Path("/home/biloi/Projects/Skills_n_Agents/.library_data.json")

# Licence recorded for an entry whose upstream licence could not be found.
UNKNOWN_LICENCE = "UNKNOWN"

# How far up from an origin directory to look for a licence file. Plugin
# layouts put the licence at the plugin root, one or two levels above the
# skill directory.
MAX_ORIGIN_WALK = 4

# Home directories are stripped from recorded paths. An origin path like
# ``/home/biloi/Projects/ECC`` is machine-specific and leaks the account
# name of whoever built the distribution; ``~/Projects/ECC`` identifies the
# same tree without it. The path stays a usable locator — it still names
# the upstream repository — and it no longer identifies the builder.
_HOME_PREFIXES = ("/home/", "/Users/")


def relativise(path: str | Path) -> str:
    """Strip the home directory prefix from a path.

    ``/home/someone/Projects/ECC`` becomes ``~/Projects/ECC``. Paths
    outside a home directory are left alone — they are already
    machine-independent (``/usr/share/...``) or are genuinely the
    upstream's own path.
    """
    text = str(path)
    for prefix in _HOME_PREFIXES:
        if text.startswith(prefix):
            remainder = text[len(prefix):]
            slash = remainder.find("/")
            if slash == -1:
                return "~"
            return "~" + remainder[slash:]
    return text


def expand(path: str | Path) -> Path:
    """Restore a home-relative path to an absolute one.

    The inverse of :func:`relativise`. A path stored as ``~/Projects/ECC``
    is expanded back to the builder's home directory so it can still be
    resolved on disk; a path that is already absolute is returned as-is.
    """
    text = str(path)
    if not text.startswith("~"):
        return Path(text)
    return Path.home() / text[1:].lstrip("/")


def _library_manifest() -> dict[str, dict]:
    """Load the library manifest, keyed by library-relative path."""
    if not LIBRARY_MANIFEST.is_file():
        return {}
    try:
        data = json.loads(LIBRARY_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, dict] = {}
    for entry in data.get("skills", []):
        path = entry.get("path")
        if path:
            out[str(path).rstrip("/") + "/"] = entry
    for entry in data.get("agents", []):
        path = entry.get("path")
        if path:
            out[str(path).rstrip("/") + "/"] = entry
    return out


def origin_for(row: dict) -> Path | None:
    """The upstream directory a vendored entry was copied from.

    Prefers the library manifest, whose ``source`` field names the true
    origin path. Falls back to the provenance table's ``upstream_root``.
    """
    manifest = _library_manifest()
    path = str(row.get("path", "")).rstrip("/") + "/"

    entry = manifest.get(path)
    if entry:
        source = entry.get("source")
        if source:
            candidate = Path(source)
            if candidate.exists():
                return candidate

    upstream_root = row.get("upstream_root")
    if upstream_root:
        # The stored value may be home-relative (see ``relativise``), so it
        # is expanded before it is checked on disk.
        candidate = expand(upstream_root)
        if candidate.exists():
            return candidate

    return None


def _candidate_roots(origin: Path) -> list[Path]:
    """Directories to search for a licence, nearest first.

    Plugin layouts place the licence at the plugin root, which is a parent
    of the ``skills/<name>`` directory. Repository layouts place it at the
    repository root.
    """
    roots: list[Path] = []
    current = origin
    for _ in range(MAX_ORIGIN_WALK):
        if current not in roots:
            roots.append(current)
        # Step out of a skills/<name> directory to its plugin root.
        if current.parent.name == "skills":
            if current.parent.parent not in roots:
                roots.append(current.parent.parent)
        if current.parent == current:
            break
        current = current.parent
    return roots


def _licence_in(directory: Path) -> tuple[str, str] | None:
    """Find a licence file in a single directory."""
    for name in LICENSE_FILES:
        candidate = directory / name
        if not candidate.is_file():
            continue
        try:
            found = detect_license_text(
                candidate.read_text(encoding="utf-8", errors="replace")
            )
        except OSError:
            continue
        if found:
            return found, relativise(candidate)
    return None


def resolve_licence(row: dict) -> tuple[str, str]:
    """Resolve the licence governing a vendored entry.

    Returns ``(licence, source_description)``. The licence is
    ``UNKNOWN`` when no upstream licence can be found — never this
    repository's own licence.
    """
    origin = origin_for(row)

    if origin is not None:
        for base in _candidate_roots(origin):
            hit = _licence_in(base)
            if hit:
                licence, path = hit
                return licence, f"origin:{path}"

        # Package metadata inside the origin directory.
        for meta in ("package.json", "plugin.json"):
            candidate = origin / meta
            if candidate.is_file():
                try:
                    data = json.loads(candidate.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                value = data.get("license") or data.get("licence")
                if isinstance(value, str) and value.strip():
                    return value.strip(), f"origin:{relativise(candidate)}"

    # The skill's own frontmatter is the last resort.
    skill_dir = PROJECT_ROOT / str(row.get("path", "")).rstrip("/")
    if skill_dir.is_dir():
        frontmatter = license_from_frontmatter(skill_dir)
        if frontmatter:
            return frontmatter, "frontmatter"

    return UNKNOWN_LICENCE, "none"


def resolve_source(row: dict) -> str:
    """A human-meaningful description of where the entry came from.

    The previous implementation recorded the absolute path of the local
    aggregator the copy passed through, which leaked a machine-specific
    path into the published CREDITS file. The true origin is preferred; the
    aggregator path is only used as a last resort.

    The home directory prefix is stripped from whichever path is chosen —
    see :func:`relativise`.
    """
    origin = origin_for(row)
    if origin is not None:
        return relativise(origin)

    upstream_root = row.get("upstream_root")
    if upstream_root:
        return relativise(upstream_root)

    source = row.get("source")
    if isinstance(source, str) and source and source != "authored":
        return relativise(source)

    return "unknown"
