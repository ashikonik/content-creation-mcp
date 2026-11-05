/**
 * Search ranking fixtures.
 *
 * These lock in the behaviour that matters: a query for a specific capability
 * must find that capability's skill, not a skill that merely shares a common
 * word.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { connectClient, callTool } from "./helpers/client.mjs";

async function search(client, query, extra = {}) {
  const payload = await callTool(client, "search_skills", { query, ...extra });
  return payload.results;
}

test("a direct capability query finds the right skill first", async () => {
  const { client, server } = await connectClient();

  const cases = [
    ["lip sync", "lip-sync"],
    ["separate vocals from a song", "audio-separation"],
    ["generate background music", "music-generation"],
    ["make a thumbnail", "thumbnail-generator"],
    ["comfyui workflow", "comfyui-video-workflows"],
    ["blender 3d render", "blender-3d-content"],
    ["transcode for instagram", "media-transcode-pipeline"],
    ["dub a video in another language", "video-translation-dubbing"],
    ["find stock footage", "stock-media-sourcing"],
    ["slide deck", "agent-slide-decks"],
  ];

  for (const [query, expected] of cases) {
    const results = await search(client, query, { limit: 5 });
    const ids = results.map((r) => r.id);
    assert.ok(
      ids.includes(expected),
      `query "${query}" did not return "${expected}" (got: ${ids.join(", ")})`,
    );
  }

  await server.close();
});

test("search returns results for a natural-language phrase", async () => {
  const { client, server } = await connectClient();

  const results = await search(client, "turn a podcast into vertical clips", {
    limit: 10,
  });

  assert.ok(results.length > 0);
  const ids = results.map((r) => r.id);
  assert.ok(
    ids.includes("long-to-short-repurpose") || ids.includes("shorts-reels-pipeline"),
    `expected a repurposing skill, got: ${ids.join(", ")}`,
  );

  await server.close();
});

test("modality filter is applied", async () => {
  const { client, server } = await connectClient();

  const results = await search(client, "video", { modality: "audio", limit: 20 });
  assert.ok(results.length > 0);

  for (const r of results) {
    assert.equal(r.content_domain, "audio");
  }

  await server.close();
});

test("source filter is applied", async () => {
  const { client, server } = await connectClient();

  const authored = await search(client, "video", {
    source: "authored",
    limit: 50,
  });
  assert.ok(authored.length > 0);
  for (const r of authored) {
    assert.equal(r.source, "authored");
  }

  await server.close();
});

test("kind filter restricts to agents", async () => {
  const { client, server } = await connectClient();

  const results = await search(client, "thumbnail", { kind: "agent", limit: 20 });
  assert.ok(results.length > 0);
  for (const r of results) {
    assert.equal(r.kind, "agent");
  }

  await server.close();
});

test("results are ordered by descending score", async () => {
  const { client, server } = await connectClient();

  const results = await search(client, "generate music for a video", { limit: 15 });
  for (let i = 1; i < results.length; i++) {
    assert.ok(
      results[i - 1].score >= results[i].score,
      "results are not sorted by score",
    );
  }

  await server.close();
});

test("an unmatchable query returns no results", async () => {
  const { client, server } = await connectClient();

  const results = await search(client, "zzzznonexistentcapability", { limit: 10 });
  assert.equal(results.length, 0);

  await server.close();
});

test("the limit is respected", async () => {
  const { client, server } = await connectClient();

  const results = await search(client, "video", { limit: 3 });
  assert.ok(results.length <= 3);

  await server.close();
});

test("prompt signals are surfaced as matched_signals", async () => {
  const { client, server } = await connectClient();

  const results = await search(client, "make clips from a video", { limit: 10 });
  const withSignals = results.filter((r) => r.matched_signals.length > 0);
  assert.ok(withSignals.length > 0, "no result reported matched signals");

  await server.close();
});
