/**
 * Dialect registry wiring.
 *
 * The README claims that `mcp/data/harnesses.json` is the extension point
 * for adding a client. That was documentation only — the renderer dispatched
 * through a hardcoded `switch` and the format list was a literal in
 * `types.ts`. These tests pin the claim to something true: the registry is
 * read at runtime, the accepted format list comes from it, and a registry
 * entry with no renderer is refused at startup rather than at render time.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { connectClient, callTool } from "./helpers/client.mjs";
import {
  loadRegistry,
  registryFormats,
  registryHarnesses,
  formatExtension,
} from "../dist/harness-registry.js";
import { implementedFormats } from "../dist/render.js";

test("the registry loads and its formats are the ones the renderer implements", () => {
  const registry = loadRegistry();
  const formats = registryFormats();

  assert.ok(formats.length > 0, "the registry declares no formats");

  // Every format the server accepts has a renderer behind it.
  const implemented = new Set(implementedFormats());
  for (const format of formats) {
    assert.ok(
      implemented.has(format),
      `format "${format}" is in the registry but has no renderer`,
    );
  }
});

test("every harness in the registry names a registered format", () => {
  const registry = loadRegistry();
  const formats = new Set(registryFormats());

  for (const [name, spec] of Object.entries(registry.harnesses)) {
    assert.ok(
      formats.has(spec.skill_format),
      `harness "${name}" names unknown skill_format "${spec.skill_format}"`,
    );
    assert.ok(
      formats.has(spec.agent_format),
      `harness "${name}" names unknown agent_format "${spec.agent_format}"`,
    );
    assert.ok(spec.skill_filename, `harness "${name}" has no skill_filename`);
    assert.ok(spec.agent_filename, `harness "${name}" has no agent_filename`);
  }
});

test("the registry reports each format's file extension", () => {
  const registry = loadRegistry();

  for (const [name, spec] of Object.entries(registry.formats)) {
    assert.match(spec.extension, /^\.[a-z0-9]+$/i, `format "${name}" has a bad extension`);
    assert.equal(
      formatExtension(name),
      spec.extension,
      `formatExtension("${name}") disagrees with the registry`,
    );
  }
});

test("render_skill accepts exactly the formats the registry declares", async () => {
  const { client, server } = await connectClient();

  const listing = await callTool(client, "list_modalities", {});
  const declared = listing.render_formats;
  const registry = registryFormats();

  assert.deepEqual(
    [...declared].sort(),
    [...registry].sort(),
    "list_modalities reports a different format list than the registry",
  );

  await server.close();
});

test("list_modalities reports the harness install conventions", async () => {
  const { client, server } = await connectClient();

  const listing = await callTool(client, "list_modalities", {});
  const harnesses = listing.harnesses;

  assert.ok(harnesses, "list_modalities does not report harnesses");

  const registry = registryHarnesses();
  assert.deepEqual(
    Object.keys(harnesses).sort(),
    Object.keys(registry).sort(),
    "list_modalities reports a different harness set than the registry",
  );

  for (const [name, spec] of Object.entries(harnesses)) {
    assert.equal(spec.skill_format, registry[name].skill_format);
    assert.equal(spec.skill_filename, registry[name].skill_filename);
    assert.ok(spec.dirs, `harness "${name}" reports no directories`);
  }

  await server.close();
});

test("a format the renderer does not implement is refused at startup", async () => {
  // The registry and the renderer have to agree. When they do not, the
  // server must say so once, at startup, naming the format — rather than
  // accepting the format and failing on every call that uses it.
  const { createServer } = await import("../dist/server.js");
  const registry = loadRegistry();

  // Corrupt the registry in memory. The cached copy is bypassed by
  // writing a format the renderer has no implementation for.
  registry.formats["test-only-unimplemented"] = {
    extension: ".test",
    description: "A format with no renderer, used only by this test.",
  };

  try {
    assert.throws(
      () => createServer(),
      /no renderer|unimplemented/i,
      "the server started with a format it cannot render",
    );
  } finally {
    delete registry.formats["test-only-unimplemented"];
  }
});

test("render_skill rejects a format that is not in the registry", async () => {
  const { client, server } = await connectClient();

  await assert.rejects(
    () => client.callTool({
      name: "render_skill",
      arguments: { id: "comfyui-video-workflows", format: "not-a-format" },
    }),
    "an unregistered format should be rejected",
  );

  await server.close();
});
