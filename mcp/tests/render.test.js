/**
 * render_skill output-format assertions.
 *
 * Each dialect has a contract. These tests pin the contract so a future
 * change to the renderer cannot silently break a client.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { parse as parseYaml } from "yaml";
import { connectClient, callToolText, expectError } from "./helpers/client.mjs";

const SKILL = "comfyui-video-workflows";

test("markdown render returns the body with no frontmatter", async () => {
  const { client, server } = await connectClient();
  const text = await callToolText(client, "render_skill", {
    id: SKILL,
    format: "markdown",
  });

  assert.ok(text.startsWith("#") || text.startsWith("\n"), "body should start with a heading");
  assert.ok(!text.startsWith("---"), "markdown render must not include frontmatter");
  assert.match(text, /ComfyUI/i);

  await server.close();
});

test("claude-frontmatter render has name and description frontmatter", async () => {
  const { client, server } = await connectClient();
  const text = await callToolText(client, "render_skill", {
    id: SKILL,
    format: "claude-frontmatter",
  });

  assert.ok(text.startsWith("---\n"));
  const end = text.indexOf("\n---\n", 3);
  assert.ok(end > 0, "frontmatter block is not closed");

  const fm = parseYaml(text.slice(4, end + 1));
  assert.equal(fm.name, "comfyui-video-workflows");
  assert.ok(fm.description.length > 20);
  assert.ok(!fm.description.includes("\n"), "description must be one line");

  await server.close();
});

test("openai-yaml render is valid YAML with interface and policy", async () => {
  const { client, server } = await connectClient();
  const text = await callToolText(client, "render_skill", {
    id: SKILL,
    format: "openai-yaml",
  });

  const doc = parseYaml(text);
  assert.ok(doc.interface, "missing interface key");
  assert.ok(doc.policy, "missing policy key");
  assert.ok(doc.instructions, "missing instructions key");
  assert.equal(doc.interface.name, "comfyui-video-workflows");
  assert.ok(doc.interface.description.length > 20);
  assert.ok(doc.instructions.length > 500);
  assert.equal(doc.metadata.content_domain, "video");

  await server.close();
});

test("agentsmd render carries the name markers", async () => {
  const { client, server } = await connectClient();
  const text = await callToolText(client, "render_skill", {
    id: SKILL,
    format: "agentsmd",
  });

  assert.match(text, /<!-- skills-library:name:comfyui-video-workflows -->/);
  assert.match(text, /<!-- skills-library:end:comfyui-video-workflows -->/);
  assert.match(text, /## comfyui-video-workflows/);
  assert.match(text, /\*\*Domain:\*\* video/);

  await server.close();
});

test("cursor-rules render is prose with a heading and a trigger line", async () => {
  const { client, server } = await connectClient();
  const text = await callToolText(client, "render_skill", {
    id: SKILL,
    format: "cursor-rules",
  });

  assert.match(text, /^# comfyui-video-workflows/m);
  assert.match(text, /Apply when:/);
  assert.ok(!text.startsWith("---"), "cursor rules should not use YAML frontmatter");

  await server.close();
});

test("every dialect renders every skill without error", async () => {
  const { client, server } = await connectClient();

  const listing = await client.callTool({
    name: "list_skills",
    arguments: { limit: 500 },
  });
  const ids = JSON.parse(listing.content[0].text).skills.map((s) => s.id);

  const formats = [
    "markdown",
    "claude-frontmatter",
    "openai-yaml",
    "agentsmd",
    "cursor-rules",
  ];

  for (const id of ids) {
    for (const format of formats) {
      const text = await callToolText(client, "render_skill", { id, format });
      assert.ok(text.length > 100, `${id}/${format} rendered too short`);
    }
  }

  await server.close();
});

test("rendering an unknown skill returns an error", async () => {
  const { client, server } = await connectClient();
  const message = await expectError(client, "render_skill", {
    id: "no-such-skill",
    format: "markdown",
  });
  assert.match(message, /not found/i);
  await server.close();
});

test("rendering by skill name works as well as by id", async () => {
  const { client, server } = await connectClient();

  // The frontmatter name is the directory slug, so lookups must accept it
  // in any casing.
  const byName = await callToolText(client, "render_skill", {
    id: "comfyui-video-workflows",
    format: "markdown",
  });
  const byMixedCase = await callToolText(client, "render_skill", {
    id: "ComfyUI-Video-Workflows",
    format: "markdown",
  });

  assert.ok(byName.length > 100);
  assert.equal(byName, byMixedCase);

  await server.close();
});
