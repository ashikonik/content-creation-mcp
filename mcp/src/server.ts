/**
 * Tool registration — the transport-agnostic core.
 *
 * `createServer()` builds the tool set from the generated index alone. Neither
 * this file nor anything it imports knows whether the server will be reached
 * over stdio or Streamable HTTP; that decision lives entirely in the two
 * entrypoints.
 */
import { readFileSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";
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
  type SkillRecord,
} from "./types.js";

const SERVER_NAME = "content-creation-mcp";
const SERVER_VERSION = "1.0.0";

/** Read a file, returning null when it is missing rather than throwing. */
function readIfExists(path: string): string | null {
  if (!existsSync(path)) return null;
  const stat = statSync(path);
  if (!stat.isFile()) return null;
  return readFileSync(path, "utf8");
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

      const { frontmatter, body } = parseFrontmatter(text);
      const payload = {
        id: skill.id,
        name: skill.name,
        description: skill.description,
        content_domain: skill.content_domain,
        source: skill.source,
        license: skill.license ?? null,
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
        files: z.array(z.string()).optional().describe("Specific relative file paths to fetch"),
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

      const dir = join(PROJECT_ROOT, skill.path, "..");
      const manifest = skill.files.map((f) => {
        const abs = join(dir, f);
        return {
          path: f,
          bytes: existsSync(abs) ? statSync(abs).size : 0,
          exists: existsSync(abs),
        };
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
      const contents: Array<{ path: string; content?: string; truncated: boolean }> = [];

      for (const rel of files) {
        const abs = join(dir, rel);
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
        if (text.length > remaining) {
          contents.push({ path: rel, content: text.slice(0, remaining), truncated: true });
          used += remaining;
        } else {
          contents.push({ path: rel, content: text, truncated: false });
          used += text.length;
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

      const ctx = contextFromFile(text, skill);
      const rendered = renderSkill(format, ctx);

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

      const { body } = parseFrontmatter(text);
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
      const bySource = {
        authored: index.skills.filter((s) => s.source === "authored").length,
        vendored: index.skills.filter((s) => s.source === "vendored").length,
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
