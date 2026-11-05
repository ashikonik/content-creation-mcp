#!/usr/bin/env python3
"""Insert a "Reference tools" pointer into each skill that received a
generated domain reference file.

The reference files are auto-discovered by the index builder and served via
`get_skill_bundle`, but a reader opening SKILL.md should still be able to
find them. This adds a short section above the trailing "Related skills"
section (or at the end of the file) pointing at the generated table.

Idempotent: running it twice does not duplicate the section.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent

# skill id -> (domain, human label)
TARGETS: dict[str, tuple[str, str]] = {
    "text-to-video-local": ("video", "Video"),
    "shorts-reels-pipeline": ("video", "Video"),
    "video-editing": ("video", "Video"),
    "local-diffusion-suite": ("image", "Image"),
    "background-removal-segmentation": ("image", "Image"),
    "comfyui-image-workflows": ("image", "Image"),
    "local-tts-engines": ("audio", "Audio"),
    "voice-cloning-rvc": ("audio", "Audio"),
    "music-generation": ("audio", "Audio"),
    "lip-sync": ("audio", "Audio"),
    "audio-separation": ("audio", "Audio"),
    "article-writing": ("text", "Text"),
    "seo": ("text", "Text"),
    "content-engine": ("text", "Text"),
    "social-publish-scheduling": ("text", "Text"),
    "blender-3d-content": ("3d", "3D"),
    "web-3d-asset-pipeline": ("3d", "3D"),
    "agent-slide-decks": ("design", "Design"),
    "diagram-generation": ("design", "Design"),
    "frontend-slides": ("design", "Design"),
    "media-transcode-pipeline": ("av_pipeline", "AV pipeline"),
    "video-translation-dubbing": ("av_pipeline", "AV pipeline"),
    "subtitle-generation": ("av_pipeline", "AV pipeline"),
}

MARKER = "## Reference tools"


def insert_pointer(skill_md: pathlib.Path, domain: str, label: str) -> bool:
    text = skill_md.read_text(encoding="utf-8")

    if MARKER in text:
        return False

    ref = f"references/{domain}-reference-tools.md"
    if not (skill_md.parent / ref).is_file():
        print(f"  missing {ref} for {skill_md.parent.name}", file=sys.stderr)
        return False

    section = (
        f"{MARKER}\n\n"
        f"Other open-source {label.lower()} tools worth knowing, each over 1,000\n"
        f"GitHub stars — see `{ref}`.\n\n"
    )

    # Prefer inserting before a trailing "## Related skills" section.
    m = re.search(r"^## Related skills\s*$", text, flags=re.MULTILINE)
    if m:
        new_text = text[: m.start()] + section + text[m.start():]
    else:
        new_text = text.rstrip() + "\n\n" + section

    skill_md.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for skill_id, (domain, label) in TARGETS.items():
        skill_md = ROOT / "skills" / skill_id / "SKILL.md"
        if not skill_md.is_file():
            print(f"  skill not found: {skill_id}", file=sys.stderr)
            continue
        if insert_pointer(skill_md, domain, label):
            changed += 1
            print(f"  linked {skill_id} -> {domain}-reference-tools.md")
    print(f"linked {changed} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
