#!/usr/bin/env node
/**
 * stdio entrypoint.
 *
 * For MCP clients that launch the server as a subprocess. stdout carries
 * protocol traffic, so nothing else may be written to it — all logging goes
 * to stderr.
 */
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const server = createServer();
  const transport = new StdioServerTransport();

  await server.connect(transport);
  process.stderr.write("content-creation-mcp: stdio transport ready\n");
}

main().catch((err) => {
  process.stderr.write(`content-creation-mcp: fatal: ${String(err)}\n`);
  process.exit(1);
});
