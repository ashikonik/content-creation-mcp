/**
 * HTTP transport smoke test and cross-transport parity check.
 *
 * The parity check is the important one: the same tool call over stdio and
 * over HTTP must return identical payloads. If it does not, the transport
 * layer has leaked into the tool layer — which is the bug this whole
 * architecture exists to prevent.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { connectClient, callTool } from "./helpers/client.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const MCP_DIR = join(HERE, "..");
const HTTP_ENTRY = join(MCP_DIR, "dist", "http.js");

const PORT = 18787;
const BASE = `http://127.0.0.1:${PORT}/mcp`;

let serverProcess = null;

async function startHttpServer() {
  serverProcess = spawn(process.execPath, [HTTP_ENTRY], {
    env: { ...process.env, PORT: String(PORT), HOST: "127.0.0.1" },
    stdio: ["ignore", "pipe", "pipe"],
  });

  serverProcess.stderr.on("data", (chunk) => {
    const text = chunk.toString();
    if (process.env.DEBUG_HTTP) process.stderr.write(text);
  });

  // Wait for the port to accept connections.
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(BASE, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "probe", version: "1.0.0" },
          },
        }),
      });
      if (res.ok || res.status === 400) return;
    } catch {
      // Not up yet.
    }
    await sleep(200);
  }

  throw new Error("HTTP server did not start within 15s");
}

function stopHttpServer() {
  if (serverProcess && !serverProcess.killed) {
    serverProcess.kill("SIGTERM");
    serverProcess = null;
  }
}

/** A raw JSON-RPC call over HTTP, returning the parsed result. */
async function httpCall(method, params, id = 1) {
  const res = await fetch(BASE, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
    },
    body: JSON.stringify({ jsonrpc: "2.0", id, method, params }),
  });

  const body = await res.text();
  if (!body) {
    throw new Error(`Empty response for ${method} (HTTP ${res.status})`);
  }

  // The server may answer as JSON or as an SSE frame.
  if (body.startsWith("event:") || body.startsWith("data:")) {
    const dataLine = body
      .split("\n")
      .find((line) => line.startsWith("data:"));
    if (!dataLine) throw new Error(`No data frame in SSE response for ${method}`);
    return JSON.parse(dataLine.slice(5).trim());
  }

  return JSON.parse(body);
}

test("HTTP server starts and answers initialize", async (t) => {
  await startHttpServer();
  t.after(stopHttpServer);

  const result = await httpCall("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "probe", version: "1.0.0" },
  });

  assert.ok(result.result, `no result in response: ${JSON.stringify(result)}`);
  assert.equal(result.result.serverInfo.name, "content-creation-mcp");
  assert.ok(result.result.protocolVersion);
});

test("tools/list works over HTTP", async (t) => {
  await startHttpServer();
  t.after(stopHttpServer);

  const result = await httpCall("tools/list", {});
  assert.ok(result.result);
  const names = result.result.tools.map((tool) => tool.name).sort();
  assert.deepEqual(names, [
    "get_agent",
    "get_skill",
    "get_skill_bundle",
    "get_stats",
    "list_modalities",
    "list_skills",
    "render_skill",
    "run_agent",
    "search_skills",
  ]);
});

test("a full initialize → tools/list → tools/call sequence works over HTTP", async (t) => {
  await startHttpServer();
  t.after(stopHttpServer);

  await httpCall("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "probe", version: "1.0.0" },
  });

  const listed = await httpCall("tools/list", {});
  assert.ok(listed.result.tools.length === 9);

  const called = await httpCall("tools/call", {
    name: "search_skills",
    arguments: { query: "dub a video in another language", limit: 5 },
  });

  assert.ok(called.result);
  const payload = JSON.parse(called.result.content[0].text);
  assert.ok(payload.count > 0);
  assert.ok(payload.results.some((r) => r.id === "video-translation-dubbing"));
});

test("an unknown method returns a JSON-RPC error, not a crash", async (t) => {
  await startHttpServer();
  t.after(stopHttpServer);

  const result = await httpCall("no/such/method", {});
  assert.ok(result.error, "expected a JSON-RPC error");
  assert.ok(result.error.code);
});

test("cross-transport parity: the same call returns identical payloads", async (t) => {
  await startHttpServer();
  t.after(stopHttpServer);

  const { client, server } = await connectClient();

  const calls = [
    ["search_skills", { query: "make a thumbnail", limit: 5 }],
    ["get_skill", { id: "music-generation" }],
    ["get_agent", { id: "short-form-producer" }],
    ["list_modalities", {}],
    ["get_stats", {}],
    ["render_skill", { id: "lip-sync", format: "openai-yaml" }],
    ["run_agent", {
      id: "image-art-director",
      task: "Make a hero image for a launch post",
    }],
  ];

  for (const [name, args] of calls) {
    // render_skill returns a raw string; every other tool returns JSON.
    const wantsText = name === "render_skill";
    const overStdio = wantsText
      ? (await client.callTool({ name, arguments: args })).content[0].text
      : await callTool(client, name, args);

    const httpResult = await httpCall("tools/call", { name, arguments: args });
    const overHttp = wantsText
      ? httpResult.result.content[0].text
      : JSON.parse(httpResult.result.content[0].text);

    assert.deepEqual(
      overHttp,
      overStdio,
      `payload mismatch for ${name} between stdio and HTTP`,
    );
  }

  await server.close();
});

test("the HTTP server rejects an unknown path", async (t) => {
  await startHttpServer();
  t.after(stopHttpServer);

  const res = await fetch(`http://127.0.0.1:${PORT}/not-mcp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });

  assert.equal(res.status, 404);
  const body = await res.json();
  assert.equal(body.error, "not_found");
});

test("the HTTP server rejects a GET on the MCP endpoint", async (t) => {
  await startHttpServer();
  t.after(stopHttpServer);

  const res = await fetch(BASE, { method: "GET" });
  assert.equal(res.status, 405);
  const body = await res.json();
  assert.equal(body.error, "method_not_allowed");
});

test("CORS preflight is answered", async (t) => {
  await startHttpServer();
  t.after(stopHttpServer);

  const res = await fetch(BASE, { method: "OPTIONS" });
  assert.equal(res.status, 204);
  assert.ok(res.headers.get("access-control-allow-origin"));
  assert.ok(res.headers.get("access-control-allow-methods").includes("POST"));
});
