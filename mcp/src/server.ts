/**
 * Tool registration — the transport-agnostic core.
 *
 * `createServer()` builds the tool set from the generated index alone. Neither
 * this file nor anything it imports knows whether the server will be reached
 * over stdio or Streamable HTTP; that decision lives entirely in the two
 * entrypoints.
 */
import { readFileSync, existsSync, statSync } from "node:fs";
import { join, resolve, sep, dirname } from "node:path";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import { loadIndex, PROJECT_ROOT } from "./index-loader.js";
import { parseFrontmatter } from "./frontmatter.js";
import { search } from "./search.js";
import { contextFromFile, renderSkill, runAgent } from "./render.js";
import {
  CONTENT_DOMAINS,
  RENDER_FORMATS,
  type AgentRecord,
  type ContentDomain,
  type RenderFormat,
  type SkillFrontmatter,
  type SkillRecord,
} from "./types.js";

const SERVER_NAME = "content-creation-mcp";
const SERVER_VERSION = "1.4.0";

/** Maximum number of file paths a single get_skill_bundle call may request. */
const MAX_BUNDLE_FILES = 200;

/** Read a file, returning null when it is missing rather than throwing. */
function readIfExists(path: string): string | null {
  try {
    if (!existsSync(path)) return null;
    const stat = statSync(path);
    if (!stat.isFile()) return null;
    return readFileSync(path, "utf8");
  } catch {
    // The file may vanish between the stat and the read.
    return null;
  }
}

/**
 * Resolve `rel` inside `base`, refusing anything that escapes it.
 *
 * `join` normalises `..` segments, so containment has to be checked after
 * resolution — a naive join lets `../../etc/passwd` walk out of the skill
 * directory. Returns null when the path is not inside `base`.
 */
function resolveInside(base: string, rel: string): string | null {
  // Reject absolute paths and any `..` segment outright, so the refusal is
  // explicit rather than relying only on the containment check below.
  if (rel.length === 0) return null;
  if (rel.startsWith("/") || rel.startsWith("\\")) return null;
  if (/^[a-zA-Z]:/.test(rel)) return null;
  const segments = rel.split(/[\\/]+/);
  if (segments.some((s) => s === "..")) return null;

  const abs = resolve(base, rel);
  if (abs !== base && !abs.startsWith(base + sep)) return null;
  return abs;
}

function skillPath(skill: SkillRecord): string {
  return join(PROJECT_ROOT, skill.path);
}

function agentPath(agent: AgentRecord): string {
  return join(PROJECT_ROOT, agent.path);
}

function findSkill(id: string): SkillRecord | undefined {
  const index = loadIndex();
  const needle = id.trim().toLowerCase();
  return (
    index.skills.find((s) => s.id === needle) ??
    index.skills.find((s) => s.name.toLowerCase() === needle) ??
    index.skills.find((s) => s.name.toLowerCase().replace(/\s+/g, "-") === needle)
  );
}

function findAgent(id: string): AgentRecord | undefined {
  const index = loadIndex();
  const needle = id.trim().toLowerCase();
  return (
    index.agents.find((a) => a.id === needle) ??
    index.agents.find((a) => a.name.toLowerCase() === needle) ??
    index.agents.find((a) => a.name.toLowerCase().replace(/\s+/g, "-") === needle)
  );
}

export function createServer(): McpServer {
  const server = new McpServer(
    { name: SERVER_NAME, version: SERVER_VERSION },
    {
      instructions:
        "Search, read, and render content-creation skills and agents. " +
        "This server is harness-agnostic: use render_skill to obtain a " +
        "skill in whatever dialect your client understands.",
    },
  );

  // ---------------------------------------------------------------- search

  server.registerTool(
    "search_skills",
    {
      title: "Search skills and agents",
      description:
        "Lexical search across the content-creation corpus. Matches skill " +
        "names, descriptions, and curated prompt-trigger phrases. Filters " +
        "by modality and source.",
      inputSchema: {
        query: z.string().describe("Search query, e.g. 'make a short from a podcast'"),
        limit: z.number().int().min(1).max(100).optional().describe("Max results (default 10)"),
        modality: z
          .enum(CONTENT_DOMAINS as [ContentDomain, ...ContentDomain[]])
          .optional()
          .describe("Filter by content domain"),
        source: z
          .enum(["authored", "vendored"])
          .optional()
          .describe("Filter by origin"),
        kind: z
          .enum(["skill", "agent", "all"])
          .optional()
          .describe("Restrict to skills, agents, or both (default all)"),
      },
    },
    async ({ query, limit, modality, source, kind }) => {
      const index = loadIndex();
      const results = search(index, query, { limit, modality, source, kind });
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ query, count: results.length, results }, null, 2),
          },
        ],
      };
    },
  );

  // ----------------------------------------------------------- get_skill

  server.registerTool(
    "get_skill",
    {
      title: "Get a skill",
      description:
        "Return one skill's frontmatter and body. Set include_body=false for " +
        "metadata only.",
      inputSchema: {
        id: z.string().describe("Skill id (directory name) or name"),
        include_body: z.boolean().optional().describe("Include the full body (default true)"),
      },
    },
    async ({ id, include_body }) => {
      const skill = findSkill(id);
      if (!skill) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: `Skill not found: ${id}` }],
        };
      }

      const text = readIfExists(skillPath(skill));
      if (text === null) {
        return {
          isError: true,
          content: [
            { type: "text" as const, text: `Skill file missing: ${skill.path}` },
          ],
        };
      }

      let frontmatter: SkillFrontmatter;
      let body: string;
      try {
        ({ frontmatter, body } = parseFrontmatter(text));
      } catch (err) {
        return {
          isError: true,
          content: [
            {
              type: "text" as const,
              text: `Cannot read ${skill.id}: ${(err as Error).message}`,
            },
          ],
        };
      }

      const payload = {
        id: skill.id,
        name: skill.name,
        description: skill.description,
        content_domain: skill.content_domain,
        source: skill.source,
        license: skill.license,
        prompt_signals: skill.prompt_signals,
        path: skill.path,
        files: skill.files,
        references: skill.references,
        scripts: skill.scripts,
        frontmatter,
        body: include_body === false ? undefined : body,
      };

      return {
        content: [{ type: "text" as const, text: JSON.stringify(payload, null, 2) }],
      };
    },
  );

  // --------------------------------------------------- get_skill_bundle

  server.registerTool(
    "get_skill_bundle",
    {
      title: "Get a skill's supporting files",
      description:
        "Return the supporting files of a skill — references, scripts, and " +
        "assets. Omit files for the manifest only.",
      inputSchema: {
        id: z.string().describe("Skill id or name"),
        files: z.array(z.string()).max(MAX_BUNDLE_FILES).optional().describe("Specific relative file paths to fetch"),
        max_bytes: z.number().int().min(1).max(2_000_000).optional().describe("Total byte cap (default 200000)"),
      },
    },
    async ({ id, files, max_bytes }) => {
      const skill = findSkill(id);
      if (!skill) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: `Skill not found: ${id}` }],
        };
      }

      if (files && files.length > MAX_BUNDLE_FILES) {
        return {
          isError: true,
          content: [
            {
              type: "text" as const,
              text: `Too many files requested: ${files.length} (max ${MAX_BUNDLE_FILES})`,
            },
          ],
        };
      }

      // The skill's own directory. `skill.path` points at the SKILL.md file,
      // so the bundle's root is its parent. Paths are resolved inside that
      // directory and nowhere else.
      const dir = dirname(resolve(PROJECT_ROOT, skill.path));
      const manifest = skill.files.map((f) => {
        const abs = resolveInside(dir, f);
        if (abs === null) {
          return { path: f, bytes: 0, exists: false };
        }
        try {
          // One stat, not an existsSync followed by a statSync: the file
          // can change between the two, and the second call could throw
          // for a path the first one just confirmed.
          const stat = statSync(abs);
          return { path: f, bytes: stat.size, exists: stat.isFile() };
        } catch {
          return { path: f, bytes: 0, exists: false };
        }
      });

      if (!files || files.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({ id: skill.id, manifest }, null, 2),
            },
          ],
        };
      }

      const cap = max_bytes ?? 200_000;
      let used = 0;
      const contents: Array<{
        path: string;
        content?: string;
        truncated: boolean;
        error?: string;
      }> = [];

      for (const rel of files) {
        const abs = resolveInside(dir, rel);
        if (abs === null) {
          // Refuse the path rather than reading it. Reporting it as an error
          // keeps the caller informed without leaking whether it exists.
          contents.push({
            path: rel,
            truncated: false,
            error: "path is outside the skill directory",
          });
          continue;
        }
        const text = readIfExists(abs);
        if (text === null) {
          contents.push({ path: rel, truncated: false });
          continue;
        }
        const remaining = cap - used;
        if (remaining <= 0) {
          contents.push({ path: rel, truncated: true });
          continue;
        }
        // The cap is in bytes, not UTF-16 code units.
        const bytes = Buffer.byteLength(text, "utf8");
        if (bytes > remaining) {
          contents.push({
            path: rel,
            content: Buffer.from(text, "utf8").subarray(0, remaining).toString("utf8"),
            truncated: true,
          });
          used += remaining;
        } else {
          contents.push({ path: rel, content: text, truncated: false });
          used += bytes;
        }
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ id: skill.id, manifest, contents }, null, 2),
          },
        ],
      };
    },
  );

  // --------------------------------------------------------- list_skills

  server.registerTool(
    "list_skills",
    {
      title: "List skills",
      description:
        "Browse the corpus by modality. Returns id, name, description, and " +
        "domain for each matching skill.",
      inputSchema: {
        modality: z
          .enum(CONTENT_DOMAINS as [ContentDomain, ...ContentDomain[]])
          .optional()
          .describe("Filter by content domain"),
        source: z.enum(["authored", "vendored"]).optional(),
        limit: z.number().int().min(1).max(500).optional(),
      },
    },
    async ({ modality, source, limit }) => {
      const index = loadIndex();
      let skills = index.skills;
      if (modality) skills = skills.filter((s) => s.content_domain === modality);
      if (source) skills = skills.filter((s) => s.source === source);
      if (limit) skills = skills.slice(0, limit);

      const rows = skills.map((s) => ({
        id: s.id,
        name: s.name,
        content_domain: s.content_domain,
        source: s.source,
        description: s.description,
      }));

      return {
        content: [
          { type: "text" as const, text: JSON.stringify({ count: rows.length, skills: rows }, null, 2) },
        ],
      };
    },
  );

  // ---------------------------------------------------------- get_agent

  server.registerTool(
    "get_agent",
    {
      title: "Get an agent",
      description:
        "Return one agent's definition — frontmatter, tools, model, and body.",
      inputSchema: {
        id: z.string().describe("Agent id or name"),
      },
    },
    async ({ id }) => {
      const agent = findAgent(id);
      if (!agent) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: `Agent not found: ${id}` }],
        };
      }

      const text = readIfExists(agentPath(agent));
      if (text === null) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: `Agent file missing: ${agent.path}` }],
        };
      }

      const { frontmatter, body } = parseFrontmatter(text);
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              { ...agent, frontmatter, body },
              null,
              2,
            ),
          },
        ],
      };
    },
  );

  // -------------------------------------------------------- render_skill

  server.registerTool(
    "render_skill",
    {
      title: "Render a skill for a client dialect",
      description:
        "Render a skill into a specific dialect and return it as a string. " +
        "Formats: markdown, claude-frontmatter, openai-yaml, agentsmd, " +
        "cursor-rules. This is the harness-agnostic path — a non-Claude " +
        "client calls this and receives a usable skill.",
      inputSchema: {
        id: z.string().describe("Skill id or name"),
        format: z
          .enum(RENDER_FORMATS as [RenderFormat, ...RenderFormat[]])
          .describe("Target dialect"),
      },
    },
    async ({ id, format }) => {
      const skill = findSkill(id);
      if (!skill) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: `Skill not found: ${id}` }],
        };
      }

      const text = readIfExists(skillPath(skill));
      if (text === null) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: `Skill file missing: ${skill.path}` }],
        };
      }

      let rendered: string;
      try {
        const ctx = contextFromFile(text, skill);
        rendered = renderSkill(format, ctx);
      } catch (err) {
        // A malformed frontmatter block is a problem with one skill, not
        // with the request. Reporting it as a tool error keeps the server
        // running and tells the client which skill needs fixing.
        return {
          isError: true,
          content: [
            {
              type: "text" as const,
              text: `Cannot render ${skill.id}: ${(err as Error).message}`,
            },
          ],
        };
      }

      return {
        content: [{ type: "text" as const, text: rendered }],
      };
    },
  );

  // ----------------------------------------------------------- run_agent

  server.registerTool(
    "run_agent",
    {
      title: "Assemble an agent run",
      description:
        "Assemble a runnable agent prompt: the system prompt, the tool list " +
        "the agent needs, and the skills it should consult. MCP has no " +
        "agent-delegation primitive, so the client executes the prompt.",
      inputSchema: {
        id: z.string().describe("Agent id or name"),
        task: z.string().describe("The task to hand the agent"),
        context: z.string().optional().describe("Extra context for the run"),
      },
    },
    async ({ id, task, context }) => {
      const agent = findAgent(id);
      if (!agent) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: `Agent not found: ${id}` }],
        };
      }

      const text = readIfExists(agentPath(agent));
      if (text === null) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: `Agent file missing: ${agent.path}` }],
        };
      }

      let body: string;
      try {
        ({ body } = parseFrontmatter(text));
      } catch (err) {
        return {
          isError: true,
          content: [
            {
              type: "text" as const,
              text: `Cannot read ${agent.id}: ${(err as Error).message}`,
            },
          ],
        };
      }

      const index = loadIndex();
      const run = runAgent(agent, body, task, context, index);

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                agent: run.agent.name,
                tools: run.tools,
                suggested_skills: run.suggested_skills,
                prompt: run.prompt,
              },
              null,
              2,
            ),
          },
        ],
      };
    },
  );

  // ------------------------------------------------------ list_modalities

  server.registerTool(
    "list_modalities",
    {
      title: "List content modalities",
      description:
        "List the content domains with their skill and agent counts, plus " +
        "the available render formats.",
      inputSchema: {},
    },
    async () => {
      const index = loadIndex();
      const modalities = CONTENT_DOMAINS.map((domain) => {
        const skills = index.skills.filter((s) => s.content_domain === domain);
        const agents = index.agents.filter((a) => a.content_domain === domain);
        return {
          modality: domain,
          skills: skills.length,
          agents: agents.length,
          example_skills: skills.slice(0, 5).map((s) => s.id),
          example_agents: agents.map((a) => a.id),
        };
      });

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              { modalities, render_formats: RENDER_FORMATS },
              null,
              2,
            ),
          },
        ],
      };
    },
  );

  // ---------------------------------------------------------- get_stats

  server.registerTool(
    "get_stats",
    {
      title: "Get corpus statistics",
      description:
        "Corpus counts by domain and source, plus index metadata.",
      inputSchema: {},
    },
    async () => {
      const index = loadIndex();

      // Counted over both kinds, so the total matches `by_domain`, which
      // also spans skills and agents. Counting skills alone made the two
      // siblings disagree: `by_source` reported 36 while `by_domain`
      // reported 48, and neither number was labelled.
      const records = [...index.skills, ...index.agents];
      const bySource = {
        authored: records.filter((r) => r.source === "authored").length,
        vendored: records.filter((r) => r.source === "vendored").length,
      };

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                version: index.version,
                generated_at: index.generated_at,
                skills: index.skills.length,
                agents: index.agents.length,
                by_domain: index.counts.by_domain,
                by_source: bySource,
                by_source_basis: "skills and agents",
              },
              null,
              2,
            ),
          },
        ],
      };
    },
  );

  return server;
}
