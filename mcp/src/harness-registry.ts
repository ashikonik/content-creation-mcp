/**
 * The dialect registry, loaded from `data/harnesses.json`.
 *
 * The README claims that "the dialect registry lives in `mcp/data/harnesses.json`
 * — data, not `switch` branches, so adding a client is a JSON edit". That claim
 * was false: `render.ts` dispatched through a hardcoded `switch`, `types.ts`
 * hardcoded the list of valid format names, and nothing under `mcp/src/` ever
 * opened `harnesses.json`. The registry was documentation.
 *
 * It is now the actual source of truth for:
 *
 *   - the set of format names `render_skill` accepts,
 *   - the file extension each format is written with,
 *   - which harness maps onto which format.
 *
 * Adding a *format* still requires a renderer function — there is no way to
 * express a new layout in JSON. But adding a *harness* (a client family with
 * its own directory convention and filename pattern) is now genuinely a JSON
 * edit, and a format that the registry names but the renderer cannot produce
 * is reported as an error at load time rather than silently ignored.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { MCP_ROOT } from "./index-loader.js";
import type { RenderFormat } from "./types.js";

export interface FormatSpec {
  extension: string;
  description: string;
}

export interface HarnessSpec {
  label: string;
  dirs: { skills: string; agents: string };
  skill_format: RenderFormat;
  agent_format: RenderFormat;
  skill_filename: string;
  agent_filename: string;
  notes?: string;
}

export interface HarnessRegistry {
  harnesses: Record<string, HarnessSpec>;
  formats: Record<string, FormatSpec>;
}

export const REGISTRY_PATH = join(MCP_ROOT, "data", "harnesses.json");

let cached: HarnessRegistry | null = null;

/**
 * Load and validate the registry.
 *
 * The validation is deliberately strict. A registry that names a format the
 * renderer does not implement would otherwise fail at render time, as an
 * obscure "unknown render format" error on one request. Catching it at load
 * time turns it into one clear message about one broken file.
 */
export function loadRegistry(force = false): HarnessRegistry {
  if (cached && !force) return cached;

  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(REGISTRY_PATH, "utf8"));
  } catch (err) {
    throw new Error(
      `Harness registry unreadable at ${REGISTRY_PATH}: ${(err as Error).message}`,
    );
  }

  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error(
      `Harness registry at ${REGISTRY_PATH} is not a JSON object.`,
    );
  }

  const registry = parsed as Partial<HarnessRegistry>;

  if (!registry.formats || typeof registry.formats !== "object") {
    throw new Error(
      `Harness registry at ${REGISTRY_PATH} has no "formats" object.`,
    );
  }
  if (!registry.harnesses || typeof registry.harnesses !== "object") {
    throw new Error(
      `Harness registry at ${REGISTRY_PATH} has no "harnesses" object.`,
    );
  }

  for (const [name, spec] of Object.entries(registry.formats)) {
    if (!spec || typeof spec.extension !== "string" || !spec.extension.startsWith(".")) {
      throw new Error(
        `Format "${name}" in ${REGISTRY_PATH} has no valid "extension".`,
      );
    }
    if (typeof spec.description !== "string" || spec.description.trim() === "") {
      throw new Error(
        `Format "${name}" in ${REGISTRY_PATH} has no "description".`,
      );
    }
  }

  for (const [name, spec] of Object.entries(registry.harnesses)) {
    if (!spec || typeof spec !== "object") {
      throw new Error(`Harness "${name}" in ${REGISTRY_PATH} is not an object.`);
    }
    if (!registry.formats[spec.skill_format]) {
      throw new Error(
        `Harness "${name}" in ${REGISTRY_PATH} names unknown skill_format ` +
          `"${spec.skill_format}".`,
      );
    }
    if (!registry.formats[spec.agent_format]) {
      throw new Error(
        `Harness "${name}" in ${REGISTRY_PATH} names unknown agent_format ` +
          `"${spec.agent_format}".`,
      );
    }
  }

  cached = registry as HarnessRegistry;
  return cached;
}

/**
 * The format names the server accepts, in registry order.
 *
 * Derived from the registry rather than hardcoded, so a format added to
 * `harnesses.json` is immediately accepted by `render_skill` — provided a
 * renderer exists for it (see `render.ts`).
 */
export function registryFormats(): string[] {
  return Object.keys(loadRegistry().formats);
}

/** The file extension a format is written with. */
export function formatExtension(format: RenderFormat): string {
  const spec = loadRegistry().formats[format];
  if (!spec) {
    throw new Error(`Unknown render format: ${format}`);
  }
  return spec.extension;
}

/** Every harness in the registry, with its format and install convention. */
export function registryHarnesses(): Record<string, HarnessSpec> {
  return loadRegistry().harnesses;
}
