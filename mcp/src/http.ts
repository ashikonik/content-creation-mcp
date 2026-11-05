#!/usr/bin/env node
/**
 * Streamable HTTP entrypoint — the primary transport.
 *
 * Stateless: `sessionIdGenerator: undefined` means the server does not keep
 * per-client session state, so any MCP client that speaks the Streamable HTTP
 * protocol can connect without a session handshake first.
 *
 * Configure with:
 *   PORT      — listen port (default 8787)
 *   HOST      — bind address (default 127.0.0.1)
 *   ALLOW_ORIGIN — CORS origin (default "*")
 */
import { createServer as createHttpServer } from "node:http";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { createServer } from "./server.js";

const PORT = Number(process.env.PORT ?? 8787);
const HOST = process.env.HOST ?? "127.0.0.1";
const ALLOW_ORIGIN = process.env.ALLOW_ORIGIN ?? "*";

const MCP_PATH = "/mcp";

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": ALLOW_ORIGIN,
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers":
    "Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
  "Access-Control-Expose-Headers": "Mcp-Session-Id",
};

/** Each request gets its own server+transport pair: this is the stateless model. */
async function createTransport(): Promise<StreamableHTTPServerTransport> {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });
  return transport;
}

const httpServer = createHttpServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "localhost"}`);

  if (req.method === "OPTIONS") {
    res.writeHead(204, CORS_HEADERS);
    res.end();
    return;
  }

  if (url.pathname !== MCP_PATH) {
    res.writeHead(404, { "Content-Type": "application/json", ...CORS_HEADERS });
    res.end(
      JSON.stringify({
        error: "not_found",
        message: `MCP endpoint is ${MCP_PATH}`,
      }),
    );
    return;
  }

  try {
    if (req.method === "POST") {
      const body = await readBody(req);

      let parsed: unknown;
      try {
        parsed = JSON.parse(body);
      } catch {
        res.writeHead(400, { "Content-Type": "application/json", ...CORS_HEADERS });
        res.end(JSON.stringify({ error: "invalid_json" }));
        return;
      }

      const transport = await createTransport();
      const server = createServer();
      await server.connect(transport);

      res.on("close", () => {
        void transport.close();
        void server.close();
      });

      await transport.handleRequest(req, res, parsed);
      return;
    }

    if (req.method === "GET" || req.method === "DELETE") {
      // In stateless mode there is no session to open or tear down; a GET is
      // used for server-initiated SSE streams, which this server does not
      // emit. Return 405 rather than hanging the connection.
      res.writeHead(405, {
        "Content-Type": "application/json",
        Allow: "POST",
        ...CORS_HEADERS,
      });
      res.end(
        JSON.stringify({
          error: "method_not_allowed",
          message:
            "This server is stateless. Use POST for requests. " +
            "Session-based GET/SSE requires a stateful server.",
        }),
      );
      return;
    }

    res.writeHead(405, { "Content-Type": "application/json", ...CORS_HEADERS });
    res.end(JSON.stringify({ error: "method_not_allowed" }));
  } catch (err) {
    process.stderr.write(`http error: ${String(err)}\n`);
    if (!res.headersSent) {
      res.writeHead(500, { "Content-Type": "application/json", ...CORS_HEADERS });
    }
    res.end(JSON.stringify({ error: "internal_error", message: String(err) }));
  }
});

function readBody(req: NodeJS.ReadableStream): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

httpServer.listen(PORT, HOST, () => {
  process.stderr.write(
    `content-creation-mcp: Streamable HTTP listening on http://${HOST}:${PORT}${MCP_PATH}\n`,
  );
});

// Keep the import used — isInitializeRequest documents the shape of the
// requests this transport accepts and is useful when adding session support.
void isInitializeRequest;

for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, () => {
    httpServer.close(() => process.exit(0));
  });
}
