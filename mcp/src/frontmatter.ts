/**
 * YAML frontmatter parsing and dialect-aware rendering.
 *
 * The server never writes to the filesystem. `render_skill` returns a string
 * that any MCP client can consume — a Claude client drops it into a skills
 * directory, an OpenAI client reads the YAML, a Cursor user pastes the rules.
 */
import { parse as parseYaml, stringify as stringifyYaml } from "yaml";
import type { SkillFrontmatter } from "./types.js";

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

export interface ParsedDoc {
  frontmatter: SkillFrontmatter;
  body: string;
}

/** Split a SKILL.md into frontmatter and body. */
export function parseFrontmatter(text: string): ParsedDoc {
  const match = FRONTMATTER_RE.exec(text);
  if (!match) {
    return { frontmatter: { name: "", description: "" }, body: text };
  }

  let frontmatter: SkillFrontmatter;
  try {
    const parsed = parseYaml(match[1]);
    // A frontmatter block that parses to a scalar or a sequence is not a
    // mapping, and casting it to SkillFrontmatter would silently produce a
    // record with no name and no description. That renders as
    // "## undefined" rather than failing, so the breakage reaches the
    // client instead of being caught here.
    if (parsed !== null && parsed !== undefined &&
        (typeof parsed !== "object" || Array.isArray(parsed))) {
      throw new Error(
        `Invalid YAML frontmatter: expected a mapping, got ${Array.isArray(parsed) ? "a sequence" : typeof parsed}`,
      );
    }
    frontmatter = (parsed ?? {}) as SkillFrontmatter;
  } catch (err) {
    throw new Error(
      `Invalid YAML frontmatter: ${(err as Error).message}`,
    );
  }

  return { frontmatter, body: text.slice(match[0].length) };
}

/**
 * Normalise a frontmatter description into a single line.
 * Newlines break YAML block scalars in some dialects.
 */
export function oneLine(value: unknown): string {
  if (typeof value !== "string") return "";
  return value.replace(/\s+/g, " ").trim();
}

/**
 * Prompt-trigger phrases, extracted from metadata.promptSignals.phrases.
 */
export function promptSignals(frontmatter: SkillFrontmatter): string[] {
  const phrases = frontmatter.metadata?.promptSignals?.phrases;
  if (!Array.isArray(phrases)) return [];
  return phrases.map((p) => String(p).trim()).filter(Boolean);
}

/**
 * Emit YAML frontmatter with the given key order, skipping empty values.
 */
export function buildFrontmatter(
  entries: Array<[string, unknown]>,
): string {
  const obj: Record<string, unknown> = {};
  for (const [key, value] of entries) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value) && value.length === 0) continue;
    obj[key] = value;
  }
  if (Object.keys(obj).length === 0) return "";
  return `---\n${stringifyYaml(obj, { lineWidth: 0 })}---\n`;
}
