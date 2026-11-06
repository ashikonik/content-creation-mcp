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


def _in_repo_licence(skill_dir: Path) -> tuple[str, str] | None:
    """Find a licence file shipped inside this repository, next to the skill.

    Some vendored skills carry a copy of their upstream licence in the
    vendored directory itself — ``skills/imagegen/LICENSE.txt`` and two
    others. That file travels with the corpus, so it is checkable on any
    machine, and it is the only licence evidence the repository ships for
    those entries.

    It is checked before the recorded fallback so that deleting one of
    these files is detected as drift rather than being papered over by the
    recorded value.

    The path is reported relative to the repository root. An absolute path
    would leak the builder's home directory into a published table, and a
    home-relative one would still name a machine that may not exist.
    """
    for name in LICENSE_FILES:
        candidate = skill_dir / name
        if not candidate.is_file():
            continue
        try:
            found = detect_license_text(
                candidate.read_text(encoding="utf-8", errors="replace")
            )
        except OSError:
            continue
        if found:
            return found, _repo_relative(candidate)
    return None


def _repo_relative(path: Path) -> str:
    """Report a path inside this repository relative to its root."""
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_licence(row: dict) -> tuple[str, str]:
    """Resolve the licence governing a vendored entry.

    Returns ``(licence, source_description)``. The licence is
    ``UNKNOWN`` when no upstream licence can be found — never this
    repository's own licence.
    """
    skill_dir = PROJECT_ROOT / str(row.get("path", "")).rstrip("/")

    # A licence file shipped inside the repository, next to the skill.
    #
    # This is checked first because it is the only licence evidence that
    # travels with the corpus. Every other source below depends on the
    # authoring machine's filesystem, so reading this one first is what
    # makes the result the same on every machine — and it means removing
    # one of these files shows up as drift instead of being masked by the
    # value recorded when it was there.
    #
    # A row whose recorded source is ``in-repo:`` is decided here and only
    # here. Its licence evidence is a file in this repository, so the
    # upstream origin must not be consulted as a substitute: doing so would
    # resolve the licence on the authoring machine and report it as unknown
    # everywhere else, which is the machine-dependent result this whole
    # fallback exists to prevent.
    recorded_source = str(row.get("license_source") or "")
    if skill_dir.is_dir():
        in_repo = _in_repo_licence(skill_dir)
        if in_repo:
            licence, path = in_repo
            return licence, f"in-repo:{path}"
    if recorded_source.startswith("in-repo:"):
        return UNKNOWN_LICENCE, "none"

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
    if skill_dir.is_dir():
        frontmatter = license_from_frontmatter(skill_dir)
        if frontmatter:
            return frontmatter, "frontmatter"

    # The origin is not on this machine.
    #
    # The origin paths are absolute and belong to the machine that vendored
    # the content, so they resolve on the authoring machine and nowhere
    # else. Without this fallback the builder produced a different licence
    # for every vendored entry on any other machine — a CI runner included
    # — and `--check` failed on a table that was in fact correct. The
    # provenance table already records what was resolved and where it came
    # from; when the origin is unavailable, that recorded answer is the
    # durable one, and it is what gets carried forward.
    #
    # The recorded licence is only trusted when it is not UNKNOWN. An
    # entry that was already unknown stays unknown, so this can never
    # manufacture a licence that was not previously resolved.
    recorded = row.get("license")
    if isinstance(recorded, str) and recorded.strip() and recorded != UNKNOWN_LICENCE:
        return recorded, recorded_source or "recorded"

    return UNKNOWN_LICENCE, "none"


def resolve_source(row: dict) -> str:
    """A human-meaningful description of where the entry came from.

    The previous implementation recorded the absolute path of the local
    aggregator the copy passed through, which leaked a machine-specific
    path into the published CREDITS file. The recorded source names the
    exact directory the entry was copied from and is what gets used; the
    repository that contained it (``upstream_root``) is the fallback.

    The recorded value is used rather than the resolved origin because the
    origin only exists on the machine that vendored the content. Deriving
    the field from the filesystem would make it machine-dependent, and
    ``--check`` would then fail on every machine but the authoring one.

    The home directory prefix is stripped from whichever path is chosen —
    see :func:`relativise`.
    """
    source = row.get("source")
    if isinstance(source, str) and source and source != "authored":
        return relativise(source)

    upstream_root = row.get("upstream_root")
    if upstream_root:
        return relativise(upstream_root)

    return "unknown"
