#!/usr/bin/env python3
"""Content-domain taxonomy.

Every skill and agent is assigned exactly one ``content_domain``. This is the
axis exposed as the ``modality`` filter on ``search_skills`` — it lets a client
ask for "audio skills" instead of guessing keywords.

The mapping is explicit, not inferred. A skill that could arguably belong to
two domains gets its primary domain by hand; the secondary is documented in
the skill's own frontmatter if it matters.
"""

DOMAINS = [
    "video",
    "image",
    "audio",
    "text",
    "3d",
    "design",
    "av_pipeline",
    "writing",
]

# Skill id -> content_domain. Explicit beats heuristic: a wrong domain sends
# a client to the wrong skill, while a missing entry silently hides one.
SKILL_DOMAINS = {
    # --- authored gap-filling skills -----------------------------------
    "shorts-reels-pipeline": "video",
    "text-to-video-local": "video",
    "comfyui-video-workflows": "video",
    "video-upscale-interpolate": "video",
    "video-background-removal": "video",
    "comfyui-image-workflows": "image",
    "local-diffusion-suite": "image",
    "background-removal-segmentation": "image",
    "thumbnail-generator": "image",
    "stock-media-sourcing": "image",
    "local-tts-engines": "audio",
    "voice-cloning-rvc": "audio",
    "lip-sync": "video",
    "music-generation": "audio",
    "audio-separation": "audio",
    "subtitle-generation": "av_pipeline",
    "tts-to-video": "video",
    "long-to-short-repurpose": "video",
    "blender-3d-content": "3d",
    "agent-slide-decks": "design",
    "diagram-generation": "design",
    "social-publish-scheduling": "text",
    "media-transcode-pipeline": "av_pipeline",
    "video-translation-dubbing": "av_pipeline",
    # --- vendored skills ------------------------------------------------
    "video-editing": "video",
    "remotion-video-creation": "video",
    "remotion-best-practices": "video",
    "hyperframes": "video",
    "hyperframes-cli": "video",
    "hyperframes-registry": "video",
    "manim-video": "video",
    "videodb": "video",
    "imagegen": "image",
    "fal-ai-media": "image",
    "ios-icon-gen": "image",
    "netlify-image-cdn": "image",
    "content-engine": "text",
    "social-publisher": "text",
    "social-graph-ranker": "text",
    "article-writing": "writing",
    "seo": "text",
    "brand-voice": "writing",
    "brand-discovery": "writing",
    "batch-draft-writer": "writing",
    "crosspost": "text",
    "marketing-campaign": "text",
    "writing-skills": "writing",
    "writing-plans": "writing",
    "email": "writing",
    "email-ops": "text",
    "frontend-slides": "design",
    "google-slides": "design",
    "canva-branded-presentation": "design",
    "reports-pdfs-and-slide-automation": "design",
    "node-link-and-diagram-layout": "design",
    "uml-and-software-architecture-visualization": "design",
    "taste": "video",
    "draft-brief": "writing",
    "draft-long-form-memo": "writing",
    "writing-hookify-rules": "writing",
    "humanizer": "writing",
    "geist": "design",
    "design-system": "design",
    "frontend-design": "design",
    "web-3d-asset-pipeline": "3d",
    "blender-motion-state-inspection": "3d",
    "sprite-pipeline": "image",
    "website-to-hyperframes": "video",
}

# Agent id -> content_domain.
AGENT_DOMAINS = {
    # authored
    "short-form-producer": "video",
    "cinematic-video-editor": "video",
    "image-art-director": "image",
    "comfyui-workflow-builder": "image",
    "voice-and-sound-designer": "audio",
    "lip-sync-technician": "video",
    "script-and-story-editor": "writing",
    "seo-content-strategist": "text",
    "social-publish-manager": "text",
    "media-pipeline-engineer": "av_pipeline",
    "thumbnail-designer": "image",
    "stock-media-researcher": "image",
    # vendored
    "seo-specialist": "text",
    "marketing-agent": "text",
    "planner": "writing",
}


def domain_for_skill(skill_id: str) -> str | None:
    """Return the content domain for a skill id, or None if unmapped."""
    return SKILL_DOMAINS.get(skill_id)


def domain_for_agent(agent_id: str) -> str | None:
    """Return the content domain for an agent id, or None if unmapped."""
    return AGENT_DOMAINS.get(agent_id)


def unmapped_skills(skill_ids) -> list[str]:
    """Skill ids present in the corpus but missing from the taxonomy."""
    return sorted(set(skill_ids) - set(SKILL_DOMAINS))


def unmapped_agents(agent_ids) -> list[str]:
    """Agent ids present in the corpus but missing from the taxonomy."""
    return sorted(set(agent_ids) - set(AGENT_DOMAINS))


def stale_entries(
    skill_ids, agent_ids, excluded_skills: set[str] | None = None
) -> dict[str, list[str]]:
    """Taxonomy entries with no corresponding record in the corpus.

    A taxonomy entry for content that was deliberately excluded is not stale —
    the mapping is kept so the content can be reinstated without re-taxonomy.
    """
    excluded_skills = excluded_skills or set()
    return {
        "skills": sorted(
            (set(SKILL_DOMAINS) - set(skill_ids)) - excluded_skills
        ),
        "agents": sorted(set(AGENT_DOMAINS) - set(agent_ids)),
    }


if __name__ == "__main__":
    print(f"domains: {', '.join(DOMAINS)}")
    print(f"skill mappings: {len(SKILL_DOMAINS)}")
    print(f"agent mappings: {len(AGENT_DOMAINS)}")
