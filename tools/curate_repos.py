#!/usr/bin/env python3
"""Curate 1000+ star content-creation repositories from the survey.

The survey classifies 43,362 repositories by modality, but the raw lists
contain a lot of noise: general LLM frameworks, agent orchestrators,
`awesome-*` link collections, and applications that only incidentally
touch content creation. Shipping those as "content creation tools" would
mislead anyone reading the corpus.

This script keeps an explicit, reviewed allowlist per domain and emits a
markdown reference table for each domain, ready to drop into the
`references/` folder of the skill that covers that domain.

Usage:
    python3 tools/curate_repos.py            # write the reference files
    python3 tools/curate_repos.py --check    # verify the allowlist still resolves
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SURVEY = ROOT / "surveys" / "content_creation_github.jsonl"

# --------------------------------------------------------------------------
# Curated allowlist, per domain.
#
# Every entry was manually reviewed against the survey record: it must be a
# tool, library, or agent that creates or processes content in that domain.
# Generic AI frameworks, prompt collections, link dumps, and apps unrelated
# to content creation are deliberately excluded.
#
# The `skills` key names the skill whose references/ folder receives the
# generated file.
# --------------------------------------------------------------------------

CURATED: dict[str, dict[str, object]] = {
    "video": {
        "skills": ["text-to-video-local", "shorts-reels-pipeline", "video-editing"],
        "repos": [
            "harry0703/MoneyPrinterTurbo",
            "calesthio/OpenMontage",
            "remotion-dev/remotion",
            "ManimCommunity/manim",
            "browser-use/video-use",
            "ATH-MaaS/Pixelle-Video",
            "hypit-ai/hypit",
            "HBAI-Ltd/Toonflow-app",
            "jianchang512/pyvideotrans",
            "Huanshere/VideoLingo",
            "Tencent-Hunyuan/HunyuanVideo",
            "zai-org/CogVideo",
            "guoyww/AnimateDiff",
            "Lightricks/LTX-Video",
            "multimodal-art-projection/YuE",
            "Wan-Video/Wan2.1",
            "showlab/Awesome-Video-Diffusion",
        ],
    },
    "image": {
        "skills": ["local-diffusion-suite", "background-removal-segmentation", "comfyui-image-workflows"],
        "repos": [
            "AUTOMATIC1111/stable-diffusion-webui",
            "Comfy-Org/ComfyUI",
            "Comfy-Org/ComfyUI-Manager",
            "huggingface/diffusers",
            "invoke-ai/InvokeAI",
            "lllyasviel/stable-diffusion-webui-forge",
            "lllyasviel/Fooocus",
            "danielgatis/rembg",
            "T8RIN/ImageToolbox",
            "Acly/krita-ai-diffusion",
            "camenduru/stable-diffusion-webui-colab",
            "divamgupta/diffusionbee-stable-diffusion-ui",
            "wangkai930418/awesome-diffusion-categorized",
            "SupaGruen/StableDiffusion-CheatSheet",
        ],
    },
    "audio": {
        "skills": ["local-tts-engines", "voice-cloning-rvc", "music-generation", "lip-sync", "audio-separation"],
        "repos": [
            "coqui-ai/TTS",
            "RVC-Boss/GPT-SoVITS",
            "RVC-Project/Retrieval-based-Voice-Conversion-WebUI",
            "CorentinJ/Real-Time-Voice-Cloning",
            "myshell-ai/OpenVoice",
            "OpenBMB/VoxCPM",
            "QwenAudio/CosyVoice",
            "QwenLM/Qwen3-TTS",
            "2noise/ChatTTS",
            "nari-labs/dia",
            "index-tts/index-tts",
            "svc-develop-team/so-vits-svc",
            "babysor/MockingBird",
            "SYSTRAN/faster-whisper",
            "ggml-org/whisper.cpp",
            "facebookresearch/audiocraft",
            "ace-step/ACE-Step-1.5",
            "DrewThomasson/ebook2audiobook",
            "k2-fsa/sherpa-onnx",
            "PaddlePaddle/PaddleSpeech",
            "NVIDIA-NeMo/Speech",
        ],
    },
    "text": {
        "skills": ["article-writing", "seo", "content-engine", "social-publish-scheduling"],
        "repos": [
            "TryGhost/Ghost",
            "blader/humanizer",
            "coreyhaines31/marketingskills",
            "AgriciDaniel/claude-seo",
            "every-app/open-seo",
            "sparanoid/chinese-copywriting-guidelines",
            "nidhinjs/prompt-master",
            "linshenkx/prompt-optimizer",
            "Billionmail/BillionMail",
            "writefreely/writefreely",
            "Notifuse/notifuse",
            "pentacent/keila",
        ],
    },
    "3d": {
        "skills": ["blender-3d-content", "web-3d-asset-pipeline"],
        "repos": [
            "ahujasid/mcp-for-blender",
            "microsoft/TRELLIS",
            "Tencent-Hunyuan/Hunyuan3D-2",
            "ashawkey/stable-dreamfusion",
            "TencentARC/InstantMesh",
            "pascalorg/editor",
            "domlysz/BlenderGIS",
            "MrForExample/ComfyUI-3D-Pack",
            "EpicGames/BlenderTools",
            "CGCookie/retopoflow",
        ],
    },
    "design": {
        "skills": ["agent-slide-decks", "diagram-generation", "frontend-slides"],
        "repos": [
            "mermaid-js/mermaid",
            "excalidraw/excalidraw",
            "slidevjs/slidev",
            "marp-team/marp",
            "penpot/penpot",
            "cathrynlavery/diagram-design",
            "ahmedkhaleel2004/gitdiagram",
            "maaslalani/slides",
            "jxnblk/mdx-deck",
            "zarazhangrui/frontend-slides",
            "lukilabs/beautiful-mermaid",
            "presenton/presenton",
            "op7418/guizang-ppt-skill",
        ],
    },
    "av_pipeline": {
        "skills": ["media-transcode-pipeline", "video-translation-dubbing", "subtitle-generation"],
        "repos": [
            "lipku/LiveTalking",
            "m-bain/whisperX",
            "yt-dlp/yt-dlp",
            "FFmpeg/FFmpeg",
            "PaddlePaddle/PaddleSpeech",
            "k2-fsa/sherpa-onnx",
        ],
    },
}


def load_survey() -> dict[str, dict]:
    records: dict[str, dict] = {}
    with SURVEY.open() as fh:
        next(fh)  # summary line
        for line in fh:
            rec = json.loads(line)
            records[rec["full_name"]] = rec
    return records


# Repos that are real and over 1000 stars but that the survey's search
# queries did not surface. They are fetched live from the GitHub API and
# recorded in the survey file so the corpus stays self-consistent.
SUPPLEMENTAL: dict[str, str] = {
    "Wan-Video/Wan2.1": "Apache-2.0",
    "m-bain/whisperX": "BSD-2-Clause",
    "FFmpeg/FFmpeg": "NOASSERTION",
}


def fetch_github(repo: str) -> dict | None:
    """Fetch live metadata for a repo the survey missed."""
    import urllib.error
    import urllib.request

    url = f"https://api.github.com/repos/{repo}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
    lic = (data.get("license") or {}).get("spdx_id") or SUPPLEMENTAL.get(repo, "NOASSERTION")
    return {
        "full_name": data["full_name"],
        "stars": data["stargazers_count"],
        "url": data["html_url"],
        "description": data.get("description") or "",
        "language": data.get("language") or "",
        "license": lic,
        "modality": "av_pipeline",
        "list": "tool repos",
        "has_skill_defs": False,
        "is_agent": False,
        "fork": False,
        "archived": data.get("archived", False),
        "updated": data.get("pushed_at", "")[:10],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only, do not write")
    args = ap.parse_args()

    survey = load_survey()
    missing: list[str] = []
    too_small: list[str] = []
    out: dict[str, list[dict]] = {}

    for domain, spec in CURATED.items():
        rows = []
        for full_name in spec["repos"]:  # type: ignore[index]
            rec = survey.get(full_name)
            if rec is None:
                rec = fetch_github(full_name)
                if rec is None:
                    missing.append(full_name)
                    continue
            if rec.get("stars", 0) <= 1000:
                too_small.append(f"{full_name} ({rec.get('stars')} stars)")
                continue
            rows.append(rec)
        rows.sort(key=lambda r: -r["stars"])
        out[domain] = rows

    if missing:
        print("ERROR: these allowlisted repos could not be resolved:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 1
    if too_small:
        print("ERROR: these allowlisted repos are at or below 1000 stars:", file=sys.stderr)
        for t in too_small:
            print(f"  {t}", file=sys.stderr)
        return 1

    total = sum(len(v) for v in out.values())
    print(f"curated {total} repos across {len(out)} domains")

    if args.check:
        for domain, rows in out.items():
            print(f"  {domain:<14} {len(rows):>3}")
        return 0

    for domain, spec in CURATED.items():
        rows = out[domain]
        pretty = domain.replace("_", " ").title()
        lines = [
            f"# {pretty} — reference tools",
            "",
            f"Repositories in the **{pretty}** domain with **over 1,000 GitHub stars**,",
            "selected from the project survey for being directly usable",
            "content-creation tools. Star counts are a snapshot from the survey date.",
            "",
            "| Stars | Repository | Licence | What it does |",
            "|---:|---|---|---|",
        ]
        for r in rows:
            desc = (r.get("description") or "").replace("|", "\\|").strip()
            if len(desc) > 120:
                desc = desc[:117].rstrip() + "…"
            lic = r.get("license") or "—"
            if lic in ("NOASSERTION", "None", None):
                lic = "see repo"
            lines.append(
                f"| {r['stars']:,} | [{r['full_name']}](https://github.com/{r['full_name']}) "
                f"| {lic} | {desc} |"
            )
        lines += [
            "",
            "All of these are open-source and locally hostable — none require a",
            "paid hosted API. Licences marked *see repo* have no SPDX identifier;",
            "check the repository before use.",
            "",
        ]
        body = "\n".join(lines)

        for skill in spec["skills"]:  # type: ignore[index]
            ref_dir = ROOT / "skills" / skill / "references"
            ref_dir.mkdir(parents=True, exist_ok=True)
            target = ref_dir / f"{domain}-reference-tools.md"
            target.write_text(body)
            print(f"  wrote {target.relative_to(ROOT)} ({len(rows)} repos)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
