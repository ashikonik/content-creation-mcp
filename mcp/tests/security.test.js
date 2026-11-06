/**
 * Security regression tests.
 *
 * These cover the arbitrary-file-read fix in `get_skill_bundle` and the
 * resource limits around it. The bug these guard against was confirmed live
 * against a running server before the fix: passing
 * `files: ["../../../../../../etc/hostname"]` returned the file's contents,
 * because the read path was built with `join()` and no containment check.
 *
 * The traversal cases must fail closed — no content, no existence oracle.
 * The legitimate-path case is just as important: it guards against the fix
 * over-blocking and breaking normal bundle reads.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { connectClient, callTool } from "./helpers/client.mjs";

/** Paths that must never yield file contents. */
const TRAVERSAL_ATTEMPTS = [
  "../../../../../../etc/hostname",
  "../../../../../../etc/passwd",
  "../../../../../../etc/shadow",
  "..",
  "../",
  "../../",
  "../../article-writing/SKILL.md",
  "../article-writing/SKILL.md",
  "/etc/passwd",
  "/etc/hostname",
  "\\\\server\\share",
  "C:\\Windows\\System32\\config\\SAM",
];

test("get_skill_bundle refuses paths that escape the skill directory", async () => {
  const { client, server } = await connectClient();

  for (const path of TRAVERSAL_ATTEMPTS) {
    const payload = await callTool(client, "get_skill_bundle", {
      id: "article-writing",
      files: [path],
    });

    const entry = payload.contents?.find((c) => c.path === path);
    assert.ok(entry, `no entry returned for ${path}`);
    assert.equal(
      entry.content,
      undefined,
      `content was returned for escaping path ${path}`,
    );
    assert.ok(
      entry.error,
      `escaping path ${path} should report an error, not a silent success`,
    );
  }

  await server.close();
});

test("get_skill_bundle does not leak file contents through the manifest", async () => {
  const { client, server } = await connectClient();

  // The manifest is built from the index's own file list, so it must never
  // contain a path outside the skill directory.
  const payload = await callTool(client, "get_skill_bundle", {
    id: "article-writing",
  });

  for (const entry of payload.manifest ?? []) {
    assert.ok(!entry.path.includes(".."), `manifest path escapes: ${entry.path}`);
    assert.ok(
      !entry.path.startsWith("/"),
      `manifest path is absolute: ${entry.path}`,
    );
  }

  await server.close();
});

test("get_skill_bundle still serves legitimate relative paths", async () => {
  const { client, server } = await connectClient();

  const payload = await callTool(client, "get_skill_bundle", {
    id: "article-writing",
    files: ["references/text-reference-tools.md"],
  });

  const entry = payload.contents?.[0];
  assert.ok(entry, "no entry for a legitimate path");
  assert.ok(entry.content, "a legitimate path returned no content");
  assert.ok(entry.content.length > 0, "content was empty");
  assert.equal(entry.error, undefined, "a legitimate path reported an error");

  await server.close();
});

test("get_skill_bundle truncates on a byte boundary, not a character boundary", async () => {
  const { client, server } = await connectClient();

  // The cap is documented in bytes. A multi-byte character must not be
  // counted as one unit, and the returned content must not exceed the cap.
  const payload = await callTool(client, "get_skill_bundle", {
    id: "article-writing",
    files: ["references/text-reference-tools.md"],
    max_bytes: 20,
  });

  const entry = payload.contents?.[0];
  assert.ok(entry, "no entry returned");
  assert.equal(entry.truncated, true, "expected truncation at 20 bytes");
  const bytes = Buffer.byteLength(entry.content ?? "", "utf8");
  assert.ok(
    bytes <= 20,
    `returned ${bytes} bytes for a 20-byte cap`,
  );

  await server.close();
});

test("get_skill_bundle rejects an excessive number of requested files", async () => {
  const { client, server } = await connectClient();

  const files = Array.from({ length: 500 }, (_, i) => `references/file-${i}.md`);

  // The schema caps the list, so the request is rejected either by the
  // schema or by the handler's own guard. Both are a rejection; what must
  // not happen is a successful read of 500 paths.
  let rejected = false;
  try {
    const result = await client.callTool({
      name: "get_skill_bundle",
      arguments: { id: "article-writing", files },
    });
    rejected = result.isError === true;
  } catch (err) {
    // The MCP client surfaces a schema violation as a thrown protocol error.
    rejected = true;
    assert.ok(
      String(err).includes("at most 200"),
      `unexpected error message: ${String(err)}`,
    );
  }

  assert.equal(rejected, true, "an oversized file list should be rejected");

  await server.close();
});

test("a path-shaped skill id resolves to no record", async () => {
  const { client, server } = await connectClient();

  // A skill id that looks like a path must resolve to nothing, not to a file
  // outside the corpus.
  const result = await client.callTool({
    name: "get_skill",
    arguments: { id: "../../../../etc/passwd" },
  });

  assert.equal(result.isError, true, "a path-shaped id should not resolve");
  assert.ok(
    result.content[0].text.includes("not found"),
    `unexpected error message: ${result.content[0].text}`,
  );

  await server.close();
});
