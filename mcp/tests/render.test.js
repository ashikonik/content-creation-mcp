/**
 * render_skill output-format assertions.
 *
 * Each dialect has a contract. These tests pin the contract so a future
 * change to the renderer cannot silently break a client.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { parse as parseYaml } from "yaml";
import { connectClient, callTool, callToolText, expectError } from "./helpers/client.mjs";
import { renderSkill } from "../dist/render.js";
import { parseFrontmatter } from "../dist/frontmatter.js";

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

// --------------------------------------------------------------- dialects

test("agentsmd omits the triggers line when a skill has no triggers", async () => {
  // The line used to be emitted as "**Triggers:** " with nothing after it,
  // which reads as a truncation bug to the client. It is now omitted
  // entirely when there is nothing to say.
  const ctx = {
    frontmatter: { name: "no-trigger-skill", description: "A skill." },
    body: "# Body",
    record: { id: "no-trigger-skill", prompt_signals: [], content_domain: "text", source: "authored" },
  };

  const rendered = renderSkill("agentsmd", ctx);
  assert.ok(!rendered.includes("**Triggers:**"), "empty triggers line should be omitted");
  assert.ok(!/^\*\*Triggers:\*\*\s*$/m.test(rendered), "no bare triggers line");
  assert.match(rendered, /## no-trigger-skill/);
});

test("agentsmd uses the index id when the frontmatter has no name", async () => {
  // The marker comment is the documented replace-anchor, so it must never
  // render as "skills-library:name:undefined" — a harness keying on that
  // marker would never find or replace the installed skill.
  const ctx = {
    frontmatter: { description: "A skill with no name." },
    body: "# Body",
    record: { id: "fallback-id", prompt_signals: ["do a thing"], content_domain: "text", source: "authored" },
  };

  const rendered = renderSkill("agentsmd", ctx);
  assert.match(rendered, /<!-- skills-library:name:fallback-id -->/);
  assert.match(rendered, /<!-- skills-library:end:fallback-id -->/);
  assert.match(rendered, /## fallback-id/);
  assert.ok(!rendered.includes("undefined"), "must not render the string 'undefined'");
});

test("cursor-rules keeps the structural blank lines", async () => {
  // The header used to be built by filtering every empty line out of the
  // array, which collapsed the deliberate separators and took the
  // conditional "Apply when:" line with them.
  const ctx = {
    frontmatter: { name: "cursor-skill", description: "A skill." },
    body: "# Body",
    record: { id: "cursor-skill", prompt_signals: ["do a thing"], content_domain: "text", source: "authored" },
  };

  const rendered = renderSkill("cursor-rules", ctx);
  const lines = rendered.split("\n");
  assert.equal(lines[0], "# cursor-skill");
  assert.equal(lines[1], "", "a blank line should follow the heading");
  assert.equal(lines[2], "A skill.");
  assert.equal(lines[3], "", "a blank line should follow the description");
  assert.equal(lines[4], "Apply when: do a thing.");
  assert.equal(lines[5], "", "a blank line should follow the trigger line");
  assert.equal(lines[6], "---");
});

test("cursor-rules omits the trigger line when there are no triggers", async () => {
  const ctx = {
    frontmatter: { name: "cursor-skill", description: "A skill." },
    body: "# Body",
    record: { id: "cursor-skill", prompt_signals: [], content_domain: "text", source: "authored" },
  };

  const rendered = renderSkill("cursor-rules", ctx);
  assert.ok(!rendered.includes("Apply when:"), "the trigger line should be omitted");
  assert.ok(rendered.includes("---"), "the rule separator should remain");
});

test("a frontmatter block that is not a mapping is an error, not empty output", async () => {
  // A YAML sequence or scalar cast to a frontmatter record silently
  // produced "## undefined" and reached the client as broken output. The
  // parser rejects it, and the server reports the failure as a tool
  // error rather than as a render.
  const ctx = {
    frontmatter: { description: "A skill." },
    body: "# Body",
    record: { id: "seq-skill", prompt_signals: [], content_domain: "text", source: "authored" },
  };
  // Sanity: the renderer itself is fine with a valid context.
  assert.ok(renderSkill("markdown", ctx).includes("# Body"));

  assert.throws(
    () => parseFrontmatter("---\n- one\n- two\n---\nbody\n"),
    /expected a mapping/i,
  );
  assert.throws(
    () => parseFrontmatter("---\njust a string\n---\nbody\n"),
    /expected a mapping/i,
  );
});

test("every skill in the corpus has a name and a description", async () => {
  // The renderer's id fallback covers a missing name, but a skill with
  // neither is broken in a way no client can use.
  const { client, server } = await connectClient();
  const listing = await client.callTool({
    name: "list_skills",
    arguments: { limit: 500 },
  });
  const ids = JSON.parse(listing.content[0].text).skills.map((s) => s.id);

  for (const id of ids) {
    const payload = await callTool(client, "get_skill", { id, include_body: false });
    assert.ok(payload.frontmatter.name, `${id} has no frontmatter name`);
    assert.ok(payload.frontmatter.description, `${id} has no frontmatter description`);
  }

  await server.close();
});

test("every skill in the corpus declares trigger phrases", async () => {
  // The search ranker's phrase bonus and the agent ranker's phrase
  // overlap both key on this list. A skill with none can never win a
  // phrase match against a skill that has them.
  const { client, server } = await connectClient();
  const listing = await client.callTool({
    name: "list_skills",
    arguments: { limit: 500 },
  });
  const ids = JSON.parse(listing.content[0].text).skills.map((s) => s.id);

  for (const id of ids) {
    const payload = await callTool(client, "get_skill", { id, include_body: false });
    assert.ok(
      Array.isArray(payload.prompt_signals) && payload.prompt_signals.length >= 3,
      `${id} has fewer than three trigger phrases`,
    );
  }

  await server.close();
});
