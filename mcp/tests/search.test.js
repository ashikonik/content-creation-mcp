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

test("a capability query ranks the skill ahead of the agent that consults it", async () => {
  // A capability query asks "what does this". The skill is what does it;
  // the agent is the thing that consults the skill. Ranking the agent first
  // points the client at a coordinator instead of at the instructions.
  const { client, server } = await connectClient();

  const cases = [
    ["edit a script", "script-and-story-editing", "script-and-story-editor"],
    ["generate an image", "imagegen", "image-art-director"],
    ["make a thumbnail", "thumbnail-generator", "thumbnail-designer"],
    ["lip sync", "lip-sync", "lip-sync-technician"],
  ];

  for (const [query, skill, agent] of cases) {
    const results = await search(client, query, { limit: 10 });
    const ids = results.map((r) => r.id);
    const skillAt = ids.indexOf(skill);
    const agentAt = ids.indexOf(agent);

    assert.ok(skillAt >= 0, `query "${query}" did not return "${skill}"`);
    assert.ok(agentAt >= 0, `query "${query}" did not return "${agent}"`);
    assert.ok(
      skillAt < agentAt,
      `query "${query}" ranked the agent "${agent}" above the skill "${skill}"`,
    );
  }

  await server.close();
});

test("the prompt-signal phrase bonus is awarded once per document", async () => {
  // The bonus used to be awarded per matching phrase, so a skill that
  // declared six trigger phrases collected six times the bonus of a skill
  // that declared one, for the same single matching word. The image-CDN
  // skill therefore outranked the image-generation skill on "generate an
  // image" even though its trigger phrase is not that phrase.
  const { client, server } = await connectClient();

  const results = await search(client, "generate an image", { limit: 10 });
  const ids = results.map((r) => r.id);

  assert.equal(ids[0], "imagegen", `expected imagegen first, got: ${ids.join(", ")}`);
  assert.ok(
    ids.indexOf("netlify-image-cdn") > ids.indexOf("imagegen"),
    "a skill with many trigger phrases outranked the one whose phrase matches",
  );

  await server.close();
});

test("a filtered search ranks within the filtered corpus", async () => {
  // The idf table described the whole corpus, but the filters selected a
  // subset. A token common across all records but rare inside the
  // filtered set scored as if it were distinctive, so a narrow modality
  // search was weighted against its own corpus.
  const { client, server } = await connectClient();

  const results = await search(client, "transcode", {
    modality: "av_pipeline",
    limit: 20,
  });

  assert.ok(results.length > 0, "the av_pipeline filter returned nothing");
  for (const r of results) {
    assert.equal(r.content_domain, "av_pipeline");
  }

  // The narrow filter must still surface the domain's own skills rather
  // than collapsing to whatever scored well corpus-wide.
  const ids = results.map((r) => r.id);
  assert.ok(
    ids.includes("media-transcode-pipeline"),
    `expected the transcode skill, got: ${ids.join(", ")}`,
  );

  await server.close();
});

test("a filtered search returns the same ordering as an unfiltered one", async () => {
  // The filter changes which documents compete; it must not change how
  // they are compared.
  const { client, server } = await connectClient();

  const unfiltered = await search(client, "video", { limit: 30 });
  const filtered = await search(client, "video", {
    modality: "video",
    limit: 30,
  });

  const unfilteredIds = unfiltered
    .filter((r) => r.content_domain === "video")
    .map((r) => r.id);
  const filteredIds = filtered.map((r) => r.id);

  // The video-domain results must appear in the same relative order in
  // both lists.
  const positions = filteredIds.map((id) => unfilteredIds.indexOf(id));
  const sorted = [...positions].sort((a, b) => a - b);
  assert.deepEqual(
    positions,
    sorted,
    "filtering by modality changed the relative order of the results",
  );

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
