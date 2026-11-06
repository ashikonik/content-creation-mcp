/**
 * Index loading, resolved relative to this module rather than the process cwd.
 *
 * The server must work whether it is launched by an MCP client (stdio), run
 * from a system service (HTTP), or imported from a test in a different
 * directory. That means never relying on `process.cwd()`.
 *
 * Two roots matter:
 *
 *   MCP_ROOT    — the directory holding ``data/index.json`` (the ``mcp/`` dir)
 *   PROJECT_ROOT — the repository root, one level up, holding ``skills/`` and
 *                 ``agents/``
 *
 * Index paths are recorded relative to PROJECT_ROOT.
 */
import { readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { LibraryIndex } from "./types.js";

/**
 * Walk up from this module's directory looking for the data/index.json file.
 * Works for both `src/` (compiled via tsc) and `dist/` layouts.
 */
function findMcpRoot(): string {
  let dir = dirname(fileURLToPath(import.meta.url));

  for (let i = 0; i < 8; i++) {
    const candidate = join(dir, "data", "index.json");
    if (existsSync(candidate)) return dir;

    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }

  // Fall back to the layout we know: <root>/mcp/{src,dist}
  return resolve(dirname(fileURLToPath(import.meta.url)), "..");
}

export const MCP_ROOT = findMcpRoot();

/**
 * The repository root. Found by walking up from MCP_ROOT until the skills/
 * and agents/ directories appear.
 *
 * The walk used to fall back to MCP_ROOT's parent when it found nothing,
 * which meant a mis-installed server could serve a *different* project's
 * `skills/` directory — silently, and with no indication that the corpus
 * was not the one it shipped with. It now fails loudly instead: a wrong
 * corpus is a deployment error the operator must see, not something to
 * paper over.
 */
function findProjectRoot(): string {
  let dir = MCP_ROOT;

  for (let i = 0; i < 8; i++) {
    if (existsSync(join(dir, "skills")) && existsSync(join(dir, "agents"))) {
      return dir;
    }
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }

  throw new Error(
    `Could not locate the project root from ${MCP_ROOT}: no directory " +
      "within 8 levels up contains both skills/ and agents/. The server " +
      "refuses to guess, because serving a different project's skills " +
      "directory would be a silent corruption of the corpus.`,
  );
}

export const PROJECT_ROOT = findProjectRoot();

export function indexPath(): string {
  return join(MCP_ROOT, "data", "index.json");
}

let cached: LibraryIndex | null = null;

export function loadIndex(force = false): LibraryIndex {
  if (cached && !force) return cached;

  const path = indexPath();
  if (!existsSync(path)) {
    throw new Error(
      `Index not found at ${path}. Build it with: python3 build/build_index.py`,
    );
  }

  const parsed = JSON.parse(readFileSync(path, "utf8")) as LibraryIndex;
  cached = parsed;
  return parsed;
}

/** Absolute path for a skill/agent file, given a project-relative path. */
export function recordDir(recordPath: string): string {
  return join(PROJECT_ROOT, recordPath);
}
