/**
 * Shared test helpers: an in-process MCP client that talks to the server
 * over an in-memory transport, plus a raw JSON-RPC client for the HTTP
 * transport.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../../dist/server.js";

/** An in-process client connected to the real server implementation. */
export async function connectClient() {
  const server = createServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  const client = new Client(
    { name: "test-client", version: "1.0.0" },
    { capabilities: {} },
  );

  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);

  return { client, server };
}

/** Call a tool and return the parsed JSON payload of its first text block. */
export async function callTool(client, name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  const text = result.content?.[0]?.text;
  if (text === undefined) {
    throw new Error(`Tool ${name} returned no text content`);
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/** Call a tool and return the raw text, for render_skill. */
export async function callToolText(client, name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  const text = result.content?.[0]?.text;
  if (text === undefined) {
    throw new Error(`Tool ${name} returned no text content`);
  }
  return text;
}

/** Assert that a call returned an error. */
export async function expectError(client, name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  if (!result.isError) {
    throw new Error(`Expected ${name} to error, but it succeeded`);
  }
  return result.content?.[0]?.text ?? "";
}
