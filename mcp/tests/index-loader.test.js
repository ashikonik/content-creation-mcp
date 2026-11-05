/**
 * Root-resolution tests.
 *
 * The server must find its index and its content regardless of the working
 * directory it was launched from — an MCP client spawns it from somewhere
 * else entirely, a system service runs it from `/`, and the test suite runs
 * it from `mcp/`. Getting this wrong produces a server that starts and then
 * fails on the first tool call, which is a miserable failure to diagnose.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

import {
  MCP_ROOT,
  PROJECT_ROOT,
  indexPath,
  loadIndex,
  recordDir,
} from "../dist/index-loader.js";

const HERE = dirname(fileURLToPath(import.meta.url));

test("MCP_ROOT holds data/index.json", () => {
  assert.ok(existsSync(join(MCP_ROOT, "data", "index.json")));
  assert.equal(indexPath(), join(MCP_ROOT, "data", "index.json"));
});

test("PROJECT_ROOT holds skills/ and agents/, and is above MCP_ROOT", () => {
  assert.ok(existsSync(join(PROJECT_ROOT, "skills")));
  assert.ok(existsSync(join(PROJECT_ROOT, "agents")));
  assert.notEqual(PROJECT_ROOT, MCP_ROOT);
});

test("the two roots are in the expected relationship", () => {
  // PROJECT_ROOT is the repository root; MCP_ROOT is the mcp/ package inside
  // it. This is what makes project-relative index paths resolve.
  assert.equal(basename(MCP_ROOT), "mcp");
  assert.equal(MCP_ROOT, join(PROJECT_ROOT, "mcp"));
});

test("loadIndex returns a populated index", () => {
  const index = loadIndex();
  assert.ok(index.skills.length > 0);
  assert.ok(index.agents.length > 0);
  assert.equal(index.skills.length + index.agents.length, index.counts.skills + index.counts.agents);
});

test("loadIndex caches, and force reloads", () => {
  const first = loadIndex();
  const second = loadIndex();
  assert.equal(first, second, "loadIndex should return the cached object");

  const reloaded = loadIndex(true);
  assert.notEqual(first, reloaded, "force=true should re-read the file");
  assert.deepEqual(first.skills.length, reloaded.skills.length);
});

test("every index path resolves against PROJECT_ROOT", () => {
  const index = loadIndex();
  for (const skill of index.skills) {
    const path = recordDir(skill.path);
    assert.ok(existsSync(path), `${skill.id} path does not resolve: ${path}`);
  }
  for (const agent of index.agents) {
    const path = recordDir(agent.path);
    assert.ok(existsSync(path), `${agent.id} path does not resolve: ${path}`);
  }
});

test("resolution does not depend on the working directory", async () => {
  // Re-import with a different cwd and confirm the roots are unchanged.
  const cwd = process.cwd();
  try {
    process.chdir("/tmp");
    const fresh = await import(
      `../dist/index-loader.js?cwd=${encodeURIComponent(cwd)}`
    );
    assert.equal(fresh.MCP_ROOT, MCP_ROOT);
    assert.equal(fresh.PROJECT_ROOT, PROJECT_ROOT);
  } finally {
    process.chdir(cwd);
  }
});

test("the test suite itself is not the source of truth for the root", () => {
  // A regression guard: the root must be derived from the module location,
  // not from the test file's location. If someone later moves the tests, or
  // runs them from a different directory, this must still hold.
  assert.notEqual(MCP_ROOT, HERE);
});
