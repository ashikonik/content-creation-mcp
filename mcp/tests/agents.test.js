/**
 * Agent skill-suggestion ranking.
 *
 * The ranker decides which skills a client is told to consult for an
 * agent. A wrong order is not a cosmetic defect: the client follows the
 * suggestion, so a skill that should lead but does not means the agent
 * is pointed at the wrong instructions.
 *
 * These tests pin the leading skill for every agent in the corpus. The
 * list is the reviewable statement of what each agent is for; when the
 * corpus or the ranker changes, a reviewer reads this file to see
 * whether the new answer is the right one.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { runAgent } from "../dist/render.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const index = JSON.parse(
  readFileSync(join(ROOT, "mcp", "data", "index.json"), "utf8"),
);

/**
 * The skill each agent should reach for first.
 *
 * Every entry was checked against the agent's own definition: the
 * leading skill is the one whose subject the agent's name and
 * description describe.
 */
const EXPECTED_LEAD = {
  "cinematic-video-editor": "video-editing",
  "comfyui-workflow-builder": "comfyui-image-workflows",
  "image-art-director": "imagegen",
  "lip-sync-technician": "lip-sync",
  "marketing-agent": "marketing-campaign",
  "media-pipeline-engineer": "media-transcode-pipeline",
  planner: "writing-plans",
  "script-and-story-editor": "script-and-story-editing",
  "seo-content-strategist": "seo",
  "seo-specialist": "seo",
  "short-form-producer": "shorts-reels-pipeline",
  "social-publish-manager": "social-publish-scheduling",
  "stock-media-researcher": "stock-media-sourcing",
  "thumbnail-designer": "thumbnail-generator",
  "voice-and-sound-designer": "voice-cloning-rvc",
};

test("the expected-lead table covers every agent in the corpus", () => {
  const agentIds = index.agents.map((a) => a.id).sort();
  const expected = Object.keys(EXPECTED_LEAD).sort();
  assert.deepEqual(
    expected,
    agentIds,
    "the expected-lead table and the agent corpus have drifted apart",
  );
});

for (const [agentId, expectedSkill] of Object.entries(EXPECTED_LEAD)) {
  test(`${agentId} leads with ${expectedSkill}`, () => {
    const agent = index.agents.find((a) => a.id === agentId);
    assert.ok(agent, `agent ${agentId} is not in the index`);

    const run = runAgent(agent, "agent body", "a task", undefined, index);

    assert.ok(
      run.suggested_skills.length > 0,
      `${agentId} suggested no skills at all`,
    );
    assert.equal(
      run.suggested_skills[0],
      expectedSkill,
      `${agentId} led with ${run.suggested_skills[0]} instead of ${expectedSkill}`,
    );
  });
}

test("every agent's suggestions are in its own content domain where possible", () => {
  // A suggestion from another domain is a strong signal that the ranker
  // matched on vocabulary rather than on subject.
  for (const agent of index.agents) {
    const run = runAgent(agent, "agent body", "a task", undefined, index);
    const sameDomain = run.suggested_skills.filter((id) => {
      const skill = index.skills.find((s) => s.id === id);
      return skill && skill.content_domain === agent.content_domain;
    });
    assert.ok(
      sameDomain.length > 0,
      `${agent.id} (${agent.content_domain}) suggested nothing from its own domain`,
    );
  }
});

test("suggestions are stable across runs", () => {
  for (const agent of index.agents) {
    const first = runAgent(agent, "body", "task", undefined, index).suggested_skills;
    const second = runAgent(agent, "body", "task", undefined, index).suggested_skills;
    assert.deepEqual(first, second, `${agent.id} produced unstable suggestions`);
  }
});

test("the run prompt names the suggested skills", () => {
  const agent = index.agents.find((a) => a.id === "video-editing" || true);
  const run = runAgent(agent, "agent body", "cut this footage", undefined, index);
  for (const id of run.suggested_skills) {
    assert.ok(run.prompt.includes(id), `the prompt omits the suggestion ${id}`);
  }
  assert.ok(run.prompt.includes("## Task"));
  assert.ok(run.prompt.includes("cut this footage"));
});
