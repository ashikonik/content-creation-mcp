#!/usr/bin/env python3
"""Build the publishable survey artifacts from the raw sweep output.

The sweep produced three lists, each sorted by stars:

* ``listA`` — repositories containing agent/skill definitions (SKILL.md,
  ``agents/``, MCP servers)
* ``listB`` — repositories that are content-generation tools or libraries
* ``final`` — the union of both, classified

This script turns that raw output into the two files that ship with the
repository: a JSON record of every repository, and a Markdown report of the
top of each list plus the capability gap analysis.

Usage:
    python3 .build_survey.py <raw-dir> [--out-dir surveys]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# The star thresholds the report breaks down by.
STAR_THRESHOLDS = [100, 500, 1_000, 10_000, 50_000]

# The capabilities the corpus must cover, with the query used to find them.
CAPABILITIES: dict[str, list[str]] = {
    "video": [
        "text to video model",
        "video upscaling interpolation",
        "background removal video",
        "video editing ffmpeg",
        "short form video reels shorts pipeline",
        "remotion video",
        "comfyui video workflow",
        "video dubbing translation",
        "subtitle caption generation video",
    ],
    "image": [
        "stable diffusion sdxl local",
        "comfyui image workflow",
        "background removal segmentation image",
        "thumbnail generation",
        "text to speech local tts",
        "image upscaling restoration",
    ],
    "audio": [
        "voice cloning rvc",
        "lip sync wav2lip",
        "music generation audiocraft musicgen",
        "audio source separation demucs",
        "text to speech piper coqui kokoro",
        "speech recognition whisper transcription",
    ],
    "design": [
        "slide deck presentation generation",
        "diagram mermaid excalidraw",
        "excalidraw",
        "3d blender rendering",
        "motion graphics animation",
    ],
    "publishing": [
        "stock footage sourcing",
        "social media publishing scheduling",
        "seo content writing",
        "content management publishing",
    ],
}

# Which query families map to which modality bucket, for the report's
# modality split.
MODALITY_HINTS: dict[str, list[str]] = {
    "video": ["video", "reel", "short", "tiktok", "youtube", "vlog", "clip"],
    "image": ["image", "photo", "picture", "thumbnail", "illustration", "diffusion"],
    "audio": ["audio", "voice", "speech", "music", "sound", "tts", "whisper"],
    "3d": ["3d", "blender", "model", "render", "mesh"],
    "design": ["design", "diagram", "slide", "deck", "mograph", "animation"],
    "text": ["writing", "seo", "copy", "content", "article", "blog"],
}


def classify_modality(record: dict) -> str:
    """Best-effort modality bucket for a repository."""
    haystack = " ".join(
        [
            record.get("desc") or "",
            " ".join(record.get("topics") or []),
            " ".join(record.get("queries") or []),
        ]
    ).lower()

    best = "other"
    best_hits = 0
    for modality, hints in MODALITY_HINTS.items():
        hits = sum(haystack.count(hint) for hint in hints)
        if hits > best_hits:
            best = modality
            best_hits = hits
    return best


def load_lists(raw_dir: Path) -> tuple[list[dict], list[dict]]:
    """Load listA and listB, tolerating the _full variants."""
    def pick(name: str) -> list[dict]:
        for candidate in (raw_dir / f"{name}.json", raw_dir / f"{name}_full.json"):
            if candidate.is_file():
                return json.loads(candidate.read_text(encoding="utf-8"))
        raise SystemExit(f"error: {name}.json not found in {raw_dir}")

    return pick("listA"), pick("listB")


def star_histogram(records: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for threshold in STAR_THRESHOLDS:
        counts[f">={threshold}"] = sum(1 for r in records if (r.get("stars") or 0) >= threshold)
    return counts


def modality_split(records: list[dict]) -> dict[str, int]:
    counter = Counter(classify_modality(r) for r in records)
    return dict(sorted(counter.items(), key=lambda kv: -kv[1]))


def compact(record: dict, list_name: str) -> dict:
    """The record shape that ships — full enough to be useful, small enough
    to read.

    Topics and paths are dropped: they are the bulk of the bytes and are
    recoverable from the repository URL when needed. Descriptions are
    truncated: the first sentence is what identifies a repository, and the
    full description is one click away on GitHub.
    """
    description = (record.get("desc") or "").strip()
    if len(description) > 200:
        description = description[:200].rsplit(" ", 1)[0] + "…"

    return {
        "full_name": record.get("full_name"),
        "stars": record.get("stars"),
        "url": record.get("url"),
        "description": description,
        "language": record.get("lang"),
        "license": record.get("license"),
        "modality": record.get("modality") or classify_modality(record),
        "list": list_name,
        "has_skill_defs": bool(record.get("skill_hit")),
        "is_agent": bool(record.get("is_agent")),
        "fork": bool(record.get("fork")),
        "updated": record.get("updated"),
    }


def render_report(list_a: list[dict], list_b: list[dict], total: int) -> str:
    lines: list[str] = []
    lines.append("# GitHub survey — content creation skills, agents, and tools")
    lines.append("")
    lines.append(
        "This survey drove the corpus in `skills/` and `agents/`. It swept "
        "GitHub for repositories that help create content — video, images, "
        "audio, text, 3D, and design — in two passes:"
    )
    lines.append("")
    lines.append(
        "* **List A** — repositories containing agent or skill definitions: "
        "`SKILL.md` files, `agents/` directories, or MCP servers."
    )
    lines.append(
        "* **List B** — repositories that are content-generation tools or "
        "libraries in their own right."
    )
    lines.append("")
    lines.append(
        f"**{total:,} repositories** classified in total "
        f"({len(list_a):,} in list A, {len(list_b):,} in list B). Both lists "
        "are sorted by stars, descending."
    )
    lines.append("")

    lines.append("## Star distribution")
    lines.append("")
    lines.append("| Threshold | List A | List B |")
    lines.append("|---|---|---|")
    hist_a = star_histogram(list_a)
    hist_b = star_histogram(list_b)
    for threshold in STAR_THRESHOLDS:
        key = f">={threshold}"
        lines.append(f"| {key} stars | {hist_a[key]:,} | {hist_b[key]:,} |")
    lines.append("")

    lines.append("## Modality split")
    lines.append("")
    lines.append("| Modality | List A | List B |")
    lines.append("|---|---|---|")
    split_a = modality_split(list_a)
    split_b = modality_split(list_b)
    for modality in sorted(set(split_a) | set(split_b)):
        lines.append(
            f"| {modality} | {split_a.get(modality, 0):,} | "
            f"{split_b.get(modality, 0):,} |"
        )
    lines.append("")

    lines.append("## Top repositories — list A (agent/skill definitions)")
    lines.append("")
    lines.append("| Stars | Repository | Description |")
    lines.append("|---:|---|---|")
    for record in list_a[:60]:
        desc = (record.get("desc") or "").replace("|", "\\|").replace("\n", " ")
        desc = desc[:110] + ("…" if len(desc) > 110 else "")
        lines.append(
            f"| {record.get('stars', 0):,} | [{record['full_name']}]"
            f"({record.get('url')}) | {desc} |"
        )
    lines.append("")

    lines.append("## Top repositories — list B (content-generation tools)")
    lines.append("")
    lines.append("| Stars | Repository | Description |")
    lines.append("|---:|---|---|")
    for record in list_b[:60]:
        desc = (record.get("desc") or "").replace("|", "\\|").replace("\n", " ")
        desc = desc[:110] + ("…" if len(desc) > 110 else "")
        lines.append(
            f"| {record.get('stars', 0):,} | [{record['full_name']}]"
            f"({record.get('url')}) | {desc} |"
        )
    lines.append("")

    lines.append("## Capabilities searched")
    lines.append("")
    lines.append(
        "Each capability below was searched for explicitly. The corpus in "
        "`skills/` was built to cover every one of them; where the survey "
        "found nothing usable, a skill was authored from scratch."
    )
    lines.append("")
    for capability, queries in CAPABILITIES.items():
        lines.append(f"### {capability}")
        lines.append("")
        for query in queries:
            lines.append(f"- `{query}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_dir", type=Path, help="Directory holding the raw sweep output")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "surveys",
        help="Where to write the survey artifacts",
    )
    args = parser.parse_args()

    list_a, list_b = load_lists(args.raw_dir)

    combined = sorted(
        [(r, "agent/skill repos") for r in list_a]
        + [(r, "tool repos") for r in list_b],
        key=lambda pair: -(pair[0].get("stars") or 0),
    )
    # De-duplicate by full_name, keeping the higher-starred record. A repo
    # found by both sweeps is labelled with both.
    seen: dict[str, tuple[dict, list[str]]] = {}
    for record, list_name in combined:
        name = record.get("full_name")
        if not name:
            continue
        if name in seen:
            existing, labels = seen[name]
            if list_name not in labels:
                labels.append(list_name)
            continue
        seen[name] = (record, [list_name])
    merged = sorted(seen.values(), key=lambda pair: -(pair[0].get("stars") or 0))

    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "counts": {
            "total": len(merged),
            "agent_skill_repos": len(list_a),
            "tool_repos": len(list_b),
        },
        "star_histogram": {
            "agent_skill_repos": star_histogram(list_a),
            "tool_repos": star_histogram(list_b),
        },
        "modality_split": {
            "agent_skill_repos": modality_split(list_a),
            "tool_repos": modality_split(list_b),
        },
    }

    # The repository list is written as JSON Lines: one record per line,
    # sorted by stars descending. A single pretty-printed JSON array of 43k
    # records is several times larger and no easier to read.
    jsonl_path = args.out_dir / "content_creation_github.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({"_summary": summary}, ensure_ascii=False) + "\n")
        for record, labels in merged:
            compact_record = compact(record, labels[0])
            if len(labels) > 1:
                compact_record["list"] = labels
            handle.write(json.dumps(compact_record, ensure_ascii=False) + "\n")
    print(f"wrote {jsonl_path} ({len(merged)} repositories)")

    md_path = args.out_dir / "content_creation_github.md"
    md_path.write_text(render_report(list_a, list_b, len(merged)), encoding="utf-8")
    print(f"wrote {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
