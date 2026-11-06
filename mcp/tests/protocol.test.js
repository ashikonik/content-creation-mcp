/**
 * Protocol conformance — the tool surface and the JSON-RPC contract.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { connectClient, callTool, callToolText, expectError } from "./helpers/client.mjs";

const EXPECTED_TOOLS = [
  "search_skills",
  "get_skill",
  "get_skill_bundle",
  "list_skills",
  "get_agent",
  "render_skill",
  "run_agent",
  "list_modalities",
  "get_stats",
];

test("initialize handshake succeeds", async () => {
  const { client, server } = await connectClient();
  const version = client.getServerVersion();
  assert.equal(version.name, "content-creation-mcp");
  await server.close();
});

test("tools/list exposes exactly the expected tool surface", async () => {
  const { client, server } = await connectClient();
  const { tools } = await client.listTools();

  const names = tools.map((t) => t.name).sort();
  assert.deepEqual(names, [...EXPECTED_TOOLS].sort());

  // Every tool needs a description and an input schema.
  for (const tool of tools) {
    assert.ok(tool.description, `${tool.name} has no description`);
    assert.ok(tool.inputSchema, `${tool.name} has no inputSchema`);
    assert.equal(tool.inputSchema.type, "object");
  }

  await server.close();
});

test("no install_* tools are exposed", async () => {
  const { client, server } = await connectClient();
  const { tools } = await client.listTools();
  const names = tools.map((t) => t.name);
  for (const name of names) {
    assert.ok(!name.startsWith("install_"), `unexpected install tool: ${name}`);
  }
  await server.close();
});

test("get_stats reports the corpus", async () => {
  const { client, server } = await connectClient();
  const stats = await callTool(client, "get_stats");

  assert.ok(stats.skills > 60, `expected 60+ skills, got ${stats.skills}`);
  assert.ok(stats.agents >= 15, `expected 15+ agents, got ${stats.agents}`);
  assert.ok(stats.by_domain.video > 0);
  assert.ok(stats.by_domain.audio > 0);
  assert.ok(stats.by_source.authored > 0);
  assert.ok(stats.by_source.vendored > 0);

  await server.close();
});

test("get_stats counts sources and domains over the same records", async () => {
  // `by_source` counted only skills while its sibling `by_domain` counted
  // skills and agents, so the two siblings reported totals that disagreed
  // and neither said which basis it used.
  const { client, server } = await connectClient();
  const stats = await callTool(client, "get_stats");

  const bySourceTotal = stats.by_source.authored + stats.by_source.vendored;
  const byDomainTotal = Object.values(stats.by_domain).reduce(
    (sum, n) => sum + n,
    0,
  );
  const recordTotal = stats.skills + stats.agents;

  assert.equal(
    bySourceTotal,
    recordTotal,
    `by_source totals ${bySourceTotal}, but the corpus holds ${recordTotal} records`,
  );
  assert.equal(
    byDomainTotal,
    recordTotal,
    `by_domain totals ${byDomainTotal}, but the corpus holds ${recordTotal} records`,
  );

  await server.close();
});

test("get_skill omits an unknown licence rather than reporting null", async () => {
  // `license` was emitted as `null` while `prompt_signals` and `files` were
  // emitted as `[]`. A missing licence is absent, not an empty value.
  const { client, server } = await connectClient();
  const payload = await callTool(client, "get_skill", {
    id: "comfyui-video-workflows",
  });

  assert.ok(
    payload.license === undefined || typeof payload.license === "string",
    `license should be a string or absent, got ${typeof payload.license}`,
  );

  await server.close();
});

test("list_modalities returns every domain with counts", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "list_modalities");

  const domains = payload.modalities.map((m) => m.modality);
  for (const expected of [
    "video", "image", "audio", "text", "3d", "design", "av_pipeline", "writing",
  ]) {
    assert.ok(domains.includes(expected), `missing domain ${expected}`);
  }

  assert.ok(payload.render_formats.includes("openai-yaml"));
  assert.ok(payload.render_formats.includes("cursor-rules"));

  await server.close();
});

test("list_skills filters by modality", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "list_skills", { modality: "audio" });

  assert.ok(payload.skills.length > 0);
  for (const skill of payload.skills) {
    assert.equal(skill.content_domain, "audio");
  }

  await server.close();
});

test("get_skill returns frontmatter and body", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "get_skill", {
    id: "comfyui-video-workflows",
  });

  assert.equal(payload.id, "comfyui-video-workflows");
  assert.equal(payload.content_domain, "video");
  assert.equal(payload.source, "authored");
  assert.ok(payload.prompt_signals.length > 0);
  assert.ok(payload.body.length > 500);

  await server.close();
});

test("get_skill with include_body=false omits the body", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "get_skill", {
    id: "music-generation",
    include_body: false,
  });

  assert.equal(payload.body, undefined);
  assert.ok(payload.description.length > 0);

  await server.close();
});

test("get_skill on an unknown id returns an error", async () => {
  const { client, server } = await connectClient();
  const message = await expectError(client, "get_skill", { id: "no-such-skill" });
  assert.match(message, /not found/i);
  await server.close();
});

test("get_agent returns tools and model", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "get_agent", {
    id: "short-form-producer",
  });

  assert.equal(payload.id, "short-form-producer");
  assert.ok(Array.isArray(payload.tools) && payload.tools.length > 0);
  assert.ok(payload.model.length > 0);
  assert.match(payload.body, /three-second rule/i);

  await server.close();
});

test("get_agent on an unknown id returns an error", async () => {
  const { client, server } = await connectClient();
  const message = await expectError(client, "get_agent", { id: "nope" });
  assert.match(message, /not found/i);
  await server.close();
});

test("get_skill_bundle returns a manifest and file contents", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "get_skill_bundle", {
    id: "subtitle-generation",
  });

  assert.ok(Array.isArray(payload.manifest));
  assert.ok(payload.manifest.length > 0);
  for (const entry of payload.manifest) {
    assert.ok(entry.path, "manifest entry missing path");
    assert.equal(typeof entry.bytes, "number");
  }

  await server.close();
});

test("get_skill_bundle can fetch specific files", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "get_skill_bundle", {
    id: "subtitle-generation",
    files: ["SKILL.md"],
  });

  assert.equal(payload.contents.length, 1);
  assert.match(payload.contents[0].content, /Subtitle Generation/);

  await server.close();
});

test("run_agent assembles a prompt with tools and skills", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "run_agent", {
    id: "comfyui-workflow-builder",
    task: "Build a FLUX text-to-image workflow with ControlNet",
  });

  assert.equal(payload.agent, "comfyui-workflow-builder");
  assert.ok(payload.tools.length > 0);
  assert.ok(payload.suggested_skills.length > 0);
  assert.match(payload.prompt, /Build a FLUX text-to-image workflow/);
  assert.match(payload.prompt, /## Available tools/);
  assert.match(payload.prompt, /## Skills to consult/);

  await server.close();
});

test("run_agent with context includes the context section", async () => {
  const { client, server } = await connectClient();
  const payload = await callTool(client, "run_agent", {
    id: "thumbnail-designer",
    task: "Make a thumbnail",
    context: "The video is a 10-minute tutorial about ffmpeg",
  });

  assert.match(payload.prompt, /## Context/);
  assert.match(payload.prompt, /10-minute tutorial/);

  await server.close();
});

test("render_skill returns a string in every dialect", async () => {
  const { client, server } = await connectClient();

  for (const format of [
    "markdown",
    "claude-frontmatter",
    "openai-yaml",
    "agentsmd",
    "cursor-rules",
  ]) {
    const text = await callToolText(client, "render_skill", {
      id: "thumbnail-generator",
      format,
    });
    assert.equal(typeof text, "string");
    assert.ok(text.length > 100, `${format} render is suspiciously short`);
  }

  await server.close();
});
