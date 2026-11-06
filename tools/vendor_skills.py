#!/usr/bin/env python3
"""Vendor content-creation skills and agents from a source library into this project.

Copies (never links) skill directories and agent files, recording provenance for
each: origin path, upstream source repo, licence, and the vendoring timestamp.

Usage:
    python3 tools/vendor_skills.py <source-library-root>

Content domains are NOT declared here. They come from the taxonomy in
``mcp/build/content_domains.py``, which is the single source of truth for the
``modality`` filter exposed by the server. This script used to carry its own
``MODALITY`` map, which drifted from the taxonomy on 14 of 44 skills — a
re-vendoring would then have silently reclassified content that clients
already index by domain.
"""
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

DEST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_OUT = os.path.join(DEST, "skills")
AGENTS_OUT = os.path.join(DEST, "agents")
PROV_OUT = os.path.join(DEST, "mcp", "data", "provenance.json")

sys.path.insert(0, os.path.join(DEST, "mcp", "build"))

from content_domains import AGENT_DOMAINS, SKILL_DOMAINS  # noqa: E402

# Only vendored content is listed here. Authored skills are written for this
# project and are not re-vendored.
#
# Skills that were excluded from the corpus are deliberately absent — see
# `mcp/data/excluded.json` for the list and the reason for each. Re-vendoring
# them would put them back on disk, where the index builder would skip them
# but the files would still ship. `remotion-video-creation` is absent because
# it was merged into `remotion-best-practices`, which is the newer upstream
# revision and the only one of the two the corpus keeps.
VENDORED_SKILLS = [
    "video-editing",
    "remotion-best-practices", "hyperframes",
    "hyperframes-cli", "hyperframes-registry",
    "website-to-hyperframes", "manim-video",
    "imagegen", "netlify-image-cdn",
    "sprite-pipeline", "ios-icon-gen",
    "article-writing", "seo", "content-engine",
    "batch-draft-writer",
    "draft-brief", "draft-long-form-memo",
    "brand-discovery", "brand-voice", "crosspost",
    "marketing-campaign", "writing-skills",
    "writing-plans", "writing-hookify-rules",
    "email-ops", "social-graph-ranker",
    "humanizer",
    "frontend-slides", "google-slides",
    "canva-branded-presentation",
    "reports-pdfs-and-slide-automation",
    "node-link-and-diagram-layout",
    "uml-and-software-architecture-visualization",
    "design-system", "frontend-design", "geist",
    "taste",
    "web-3d-asset-pipeline", "blender-motion-state-inspection",
]

AGENT_NAMES = [
    "seo-specialist", "marketing-agent", "planner",
]

SKILL_FILES = ("SKILL.md", "LICENSE.txt", "LICENSE", "COPYING")


def detect_license(path):
    """Read a licence identifier out of a LICENSE file if one sits beside the skill."""
    for name in ("LICENSE.txt", "LICENSE", "COPYING"):
        p = os.path.join(path, name)
        if not os.path.exists(p):
            continue
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        head = text[:4000].lower()
        if "apache license" in head:
            return "Apache-2.0"
        if "gnu affero" in head or "agpl" in head:
            return "AGPL-3.0"
        if "gnu general public" in head or "gpl" in head:
            return "GPL-3.0"
        if "creative commons" in head and "attribution" in head:
            return "CC-BY-4.0"
        if "mit license" in head or "permission is hereby granted" in head:
            return "MIT"
        if "bsd" in head:
            return "BSD-3-Clause"
        return "SEE-LICENSE"
    return None


def find_upstream(source_path):
    """Walk up from a skill's source directory looking for a git remote or repo marker."""
    cur = os.path.abspath(source_path)
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, ".git")):
            cfg = os.path.join(cur, ".git", "config")
            if os.path.exists(cfg):
                try:
                    text = open(cfg, encoding="utf-8", errors="replace").read()
                except OSError:
                    text = ""
                m = re.search(r"url\s*=\s*(\S+)", text)
                if m:
                    return m.group(1).strip(), cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None, os.path.abspath(source_path)


def main():
    if len(sys.argv) < 2:
        print("usage: tools/vendor_skills.py <source-library-root>", file=sys.stderr)
        return 1
    src_root = os.path.abspath(sys.argv[1])
    lib = json.load(open(os.path.join(src_root, ".library_data.json")))
    by_name = {s["name"]: s for s in lib["skills"]}
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    os.makedirs(SKILLS_OUT, exist_ok=True)
    os.makedirs(AGENTS_OUT, exist_ok=True)
    os.makedirs(os.path.dirname(PROV_OUT), exist_ok=True)

    prov = []
    copied = skipped = 0

    for name in sorted(VENDORED_SKILLS):
        modality = SKILL_DOMAINS.get(name)
        if modality is None:
            print(f"  skip (no taxonomy entry): {name}")
            skipped += 1
            continue
        rec = by_name.get(name)
        if rec is None:
            print(f"  skip (not in source): {name}")
            skipped += 1
            continue
        src = os.path.join(src_root, rec["path"].rstrip("/"))
        dst = os.path.join(SKILLS_OUT, name)
        if not os.path.isdir(src):
            print(f"  skip (no dir): {name} -> {src}")
            skipped += 1
            continue
        if os.path.exists(dst):
            shutil.rmtree(dst)

        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "node_modules", ".DS_Store",
            "agents",  # OpenAI-specific sidecar; this server renders dialects on demand
        ))

        lic = detect_license(dst)
        upstream, upstream_root = find_upstream(rec.get("source") or src)
        prov.append({
            "name": name,
            "kind": "skill",
            "owner": "vendored",
            "license": lic or "MIT",
            "license_source": "adjacent LICENSE file" if lic else "defaulted",
            "source": os.path.abspath(src),
            "upstream": upstream,
            "upstream_root": upstream_root,
            "path": f"skills/{name}/",
            "content_domain": modality,
            "vendored_on": stamp,
            "verdict": "publish" if lic else "publish-default-mit",
        })
        copied += 1

    for name in AGENT_NAMES:
        src = os.path.join(src_root, "agents", f"{name}.md")
        if not os.path.exists(src):
            print(f"  skip (no agent): {name}")
            skipped += 1
            continue
        shutil.copy2(src, os.path.join(AGENTS_OUT, f"{name}.md"))
        lic = detect_license(os.path.dirname(src))
        prov.append({
            "name": name,
            "kind": "agent",
            "owner": "vendored",
            "license": lic or "MIT",
            "license_source": "adjacent LICENSE file" if lic else "defaulted",
            "source": src,
            "upstream": None,
            "upstream_root": None,
            "path": f"agents/{name}.md",
            "content_domain": AGENT_DOMAINS.get(name, "text"),
            "vendored_on": stamp,
            "verdict": "publish" if lic else "publish-default-mit",
        })
        copied += 1

    prov.sort(key=lambda p: (p["kind"], p["name"]))
    json.dump(prov, open(PROV_OUT, "w"), indent=2, sort_keys=True)
    print(f"\nvendored {copied} entries, skipped {skipped}")
    print(f"provenance -> {PROV_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
