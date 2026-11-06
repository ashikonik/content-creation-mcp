#!/usr/bin/env node
/**
 * Streamable HTTP entrypoint — the primary transport.
 *
 * Stateless: `sessionIdGenerator: undefined` means the server does not keep
 * per-client session state, so any MCP client that speaks the Streamable HTTP
 * protocol can connect without a session handshake first.
 *
 * Security model — this transport exposes a local file-reading API, so it is
 * defended as such:
 *
 *   - Authentication. Every request must carry `Authorization: Bearer <token>`.
 *     The token comes from `MCP_AUTH_TOKEN`, or is generated at startup when
 *     bound to loopback (and printed to stderr). A non-loopback bind with no
 *     token configured refuses to start rather than serving unauthenticated.
 *   - Origin. A request carrying an `Origin` header is rejected unless that
 *     origin is explicitly allowed. This blocks the "any web page the user
 *     visits" attack, where a page in the user's browser posts to localhost.
 *   - Body size. Request bodies are capped, so a single request cannot
 *     exhaust memory.
 *
 * Configure with:
 *   PORT      — listen port (default 8787)
 *   HOST      — bind address (default 127.0.0.1)
 *   MCP_AUTH_TOKEN — bearer token required from clients
 *   ALLOW_ORIGIN — comma-separated origins permitted to make browser requests.
 *                   Defaults to none. "*" opts into any origin.
 *   MCP_MAX_BODY_BYTES — request body cap (default 4 MiB)
 */
import { createServer as createHttpServer } from "node:http";
import { randomBytes, timingSafeEqual } from "node:crypto";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createServer } from "./server.js";

const PORT = Number(process.env.PORT ?? 8787);
const HOST = process.env.HOST ?? "127.0.0.1";
const ALLOW_ORIGIN = process.env.ALLOW_ORIGIN ?? "";
const MAX_BODY_BYTES = Number(process.env.MCP_MAX_BODY_BYTES ?? 4 * 1024 * 1024);

const MCP_PATH = "/mcp";

/** Loopback addresses, where a locally-generated token is acceptable. */
function isLoopback(host: string): boolean {
  return host === "127.0.0.1" || host === "::1" || host === "localhost";
}

/**
 * Resolve the bearer token.
 *
 * A configured token always wins. Otherwise, on loopback, generate one and
 * print it so the operator can paste it into their client config. On any
 * other host there is no safe default, so the server refuses to start.
 */
function resolveAuthToken(): string {
  const configured = process.env.MCP_AUTH_TOKEN?.trim();
  if (configured) return configured;

  if (isLoopback(HOST)) {
    const generated = randomBytes(32).toString("hex");
    process.stderr.write(
      `content-creation-mcp: generated auth token (no MCP_AUTH_TOKEN set):\n` +
        `  ${generated}\n` +
        `Pass it to clients as: Authorization: Bearer ${generated}\n`,
    );
    return generated;
  }

  process.stderr.write(
    `content-creation-mcp: refusing to start.\n` +
      `HOST is "${HOST}" (not loopback) and MCP_AUTH_TOKEN is not set.\n` +
      `Set MCP_AUTH_TOKEN to a secret value before binding to a public interface.\n`,
  );
  process.exit(1);
}

const AUTH_TOKEN = resolveAuthToken();

/** Origins permitted to make browser requests. Empty means none. */
const ALLOWED_ORIGINS = new Set(
  ALLOW_ORIGIN.split(",")
    .map((o) => o.trim())
    .filter(Boolean),
);

/** Whether any origin at all is permitted. */
const ALLOW_ANY_ORIGIN = ALLOWED_ORIGINS.has("*");

function corsHeaders(origin: string | undefined): Record<string, string> {
  const headers: Record<string, string> = {
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers":
      "Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
    Vary: "Origin",
  };

  // Only advertise an allowed origin. A wildcard is emitted only when it has
  // been explicitly opted into.
  if (origin) {
    if (ALLOW_ANY_ORIGIN) {
      headers["Access-Control-Allow-Origin"] = "*";
    } else if (ALLOWED_ORIGINS.has(origin)) {
      headers["Access-Control-Allow-Origin"] = origin;
    }
  }

  return headers;
}

/** Constant-time token comparison, so a mismatch leaks no timing information. */
function tokenMatches(provided: string): boolean {
  const expected = Buffer.from(AUTH_TOKEN, "utf8");
  const actual = Buffer.from(provided, "utf8");
  if (expected.length !== actual.length) return false;
  return timingSafeEqual(expected, actual);
}

/**
 * Check the Authorization header.
 *
 * Returns null when the request is authorised, or an error code otherwise.
 */
function checkAuth(headers: Record<string, unknown>): string | null {
  const raw = headers.authorization;
  if (typeof raw !== "string" || !raw) return "unauthorized";
  const match = /^Bearer\s+(.+)$/i.exec(raw.trim());
  if (!match) return "unauthorized";
  if (!tokenMatches(match[1])) return "unauthorized";
  return null;
}

/**
 * Check the Origin header.
 *
 * A browser attaches Origin to cross-origin requests. Rejecting unexpected
 * origins stops a random web page from driving this local server.
 */
function checkOrigin(headers: Record<string, unknown>): string | null {
  const origin = headers.origin;
  if (origin === undefined) return null; // not a browser request
  if (typeof origin !== "string") return "origin_not_allowed";
  if (ALLOW_ANY_ORIGIN) return null;
  if (ALLOWED_ORIGINS.has(origin)) return null;
  return "origin_not_allowed";
}

/**
 * The shared MCP server.
 *
 * One server instance serves every request. The transport stays per-request
 * — that is what makes the server stateless, and the stateless model is
 * what lets any MCP client connect without a session handshake. But the
 * *server* holds no per-client state: its tools read the generated index
 * and the filesystem, both of which are shared by every caller anyway.
 *
 * Constructing a server per request re-registered all nine tools on every
 * call, which was pure overhead and made the README's "one shared server"
 * claim inaccurate.
 */
const server = createServer();

/** Each request gets its own transport pair: this is the stateless model. */
async function createTransport(): Promise<StreamableHTTPServerTransport> {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });
  return transport;
}

const httpServer = createHttpServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "localhost"}`);
  const origin = req.headers.origin;
  const headers = corsHeaders(origin);

  if (req.method === "OPTIONS") {
    res.writeHead(204, headers);
    res.end();
    return;
  }

  if (url.pathname !== MCP_PATH) {
    res.writeHead(404, { "Content-Type": "application/json", ...headers });
    res.end(
      JSON.stringify({
        error: "not_found",
        message: `MCP endpoint is ${MCP_PATH}`,
      }),
    );
    return;
  }

  // Authenticate before doing any work, including reading the body.
  const authError = checkAuth(req.headers);
  if (authError) {
    res.writeHead(401, { "Content-Type": "application/json", ...headers });
    res.end(JSON.stringify({ error: "unauthorized" }));
    return;
  }

  const originError = checkOrigin(req.headers);
  if (originError) {
    res.writeHead(403, { "Content-Type": "application/json", ...headers });
    res.end(JSON.stringify({ error: "origin_not_allowed" }));
    return;
  }

  try {
    if (req.method === "POST") {
      // Reject an oversized body before reading it.
      const declared = Number(req.headers["content-length"] ?? "0");
      if (Number.isFinite(declared) && declared > MAX_BODY_BYTES) {
        res.writeHead(413, { "Content-Type": "application/json", ...headers });
        res.end(JSON.stringify({ error: "payload_too_large" }));
        return;
      }

      let body: string;
      try {
        body = await readBody(req);
      } catch (err) {
        const code = (err as { code?: string }).code;
        if (code === "BODY_TOO_LARGE") {
          res.writeHead(413, { "Content-Type": "application/json", ...headers });
          res.end(JSON.stringify({ error: "payload_too_large" }));
          return;
        }
        throw err;
      }

      let parsed: unknown;
      try {
        parsed = JSON.parse(body);
      } catch {
        res.writeHead(400, { "Content-Type": "application/json", ...headers });
        res.end(JSON.stringify({ error: "invalid_json" }));
        return;
      }

      const transport = await createTransport();
      await server.connect(transport);

      // The MCP transport writes the response headers itself, so the CORS
      // headers have to be set on the response before it takes over.
      for (const [key, value] of Object.entries(headers)) {
        res.setHeader(key, value);
      }

      // Tear down only when the client aborts. `res.on("close")` also fires on
      // a normal completed response, which would close the server early.
      //
      // Only the transport is closed: the server is shared by every request,
      // so closing it here would take down the whole listener.
      req.on("aborted", () => {
        void transport.close();
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
        ...headers,
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

    res.writeHead(405, { "Content-Type": "application/json", ...headers });
    res.end(JSON.stringify({ error: "method_not_allowed" }));
  } catch (err) {
    // Log the detail, but do not return it to the client — internal error
    // messages can disclose paths and internals.
    process.stderr.write(`http error: ${String(err)}\n`);
    if (!res.headersSent) {
      res.writeHead(500, { "Content-Type": "application/json", ...headers });
    }
    res.end(JSON.stringify({ error: "internal_error" }));
  }
});

/**
 * Read the request body, capped at MAX_BODY_BYTES.
 *
 * The cap is enforced while the stream is read, so an oversized body is
 * abandoned rather than buffered in full.
 */
function readBody(req: NodeJS.ReadableStream & { destroy?: () => void }): Promise<string> {
  return new Promise((resolvePromise, reject) => {
    const chunks: Buffer[] = [];
    let total = 0;

    req.on("data", (c: Buffer) => {
      total += c.length;
      if (total > MAX_BODY_BYTES) {
        const err = new Error("request body too large") as Error & { code: string };
        err.code = "BODY_TOO_LARGE";
        req.destroy?.();
        reject(err);
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolvePromise(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

httpServer.listen(PORT, HOST, () => {
  process.stderr.write(
    `content-creation-mcp: Streamable HTTP listening on http://${HOST}:${PORT}${MCP_PATH}\n`,
  );
});

for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, () => {
    httpServer.close(() => process.exit(0));
  });
}
