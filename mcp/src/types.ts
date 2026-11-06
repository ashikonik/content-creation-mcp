/**
 * Core types for the content-creation MCP server.
 *
 * The server is transport-agnostic: everything in here is built from the
 * generated index and knows nothing about stdio vs HTTP.
 */

/** Content taxonomy axis. Every skill and agent is assigned exactly one. */
export type ContentDomain =
  | "video"
  | "image"
  | "audio"
  | "text"
  | "3d"
  | "design"
  | "av_pipeline"
  | "writing";

export const CONTENT_DOMAINS: ContentDomain[] = [
  "video",
  "image",
  "audio",
  "text",
  "3d",
  "design",
  "av_pipeline",
  "writing",
];

/** Where a record came from: authored here, or vendored from upstream. */
export type SkillSource = "authored" | "vendored";

/**
 * A skill's frontmatter.
 *
 * The fields the renderer and the tools actually read are named. Vendored
 * skills carry additional keys (`metadata.origin`, `metadata.sources`, …)
 * that no code depends on, so they are allowed through — but only under
 * `metadata`, where they live. An open index signature at the top level
 * would defeat the checking on the named fields, since every typo would
 * still typecheck.
 */
export interface SkillFrontmatter {
  name: string;
  description: string;
  license?: string;
  version?: string;
  allowed_tools?: string[];
  compatibility?: string;
  metadata?: {
    promptSignals?: {
      phrases?: string[];
    };
    [key: string]: unknown;
  };
}

export interface SkillRecord {
  /** Directory name under skills/ — the stable identifier. */
  id: string;
  name: string;
  description: string;
  content_domain: ContentDomain;
  source: SkillSource;
  license?: string;
  /** Prompt-trigger phrases used by the search ranker. */
  prompt_signals: string[];
  /** Path relative to the project root, e.g. "skills/foo/SKILL.md". */
  path: string;
  /** Supporting files relative to the skill directory. */
  files: string[];
  /** Supporting files that are references/ documents. */
  references: string[];
  /** Supporting files that are executable scripts. */
  scripts: string[];
  /** Token count of the body, used for reporting. */
  body_chars: number;
  /** Upstream repository, for vendored skills. */
  upstream?: string;
  upstream_owner?: string;
}

export interface AgentRecord {
  id: string;
  name: string;
  description: string;
  content_domain: ContentDomain;
  tools: string[];
  model: string;
  source: SkillSource;
  license?: string;
  path: string;
  files: string[];
  prompt_signals: string[];
  body_chars: number;
  upstream?: string;
  upstream_owner?: string;
}

export interface LibraryIndex {
  version: string;
  generated_at: string;
  project_root: string;
  counts: {
    skills: number;
    agents: number;
    by_domain: Record<string, number>;
  };
  skills: SkillRecord[];
  agents: AgentRecord[];
}

/**
 * Dialect names understood by render_skill.
 *
 * The names are a union so that a typo in a format string is a compile error
 * rather than a runtime rejection. The *list* of accepted names is not
 * hardcoded here — it comes from the dialect registry in
 * `data/harnesses.json`, so adding a format is a JSON edit. The union below
 * still has to be extended when a new renderer is written, because the type
 * is what makes `render_skill`'s parameter checkable.
 */
export type RenderFormat =
  | "markdown"
  | "claude-frontmatter"
  | "openai-yaml"
  | "agentsmd"
  | "cursor-rules";

export interface SearchResult {
  id: string;
  kind: "skill" | "agent";
  name: string;
  description: string;
  content_domain: ContentDomain;
  score: number;
  source: SkillSource;
  matched_signals: string[];
}
