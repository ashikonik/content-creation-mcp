#!/usr/bin/env bash
#
# Emit an MCP client configuration snippet for this server.
#
# The server is harness-agnostic: it speaks MCP over stdio or Streamable HTTP,
# so any MCP client can consume it. This script just prints the right JSON
# block for whichever client you are wiring up.
#
# Usage:
#   ./register.sh                 # generic stdio config
#   ./register.sh --mcp-url       # generic HTTP config
#   ./register.sh --mcp-url URL   # generic HTTP config for a specific URL
#   ./register.sh --claude        # Claude Desktop / Claude Code stdio block
#   ./register.sh --codex         # Codex (TOML) block
#   ./register.sh --opencode      # OpenCode (JSON) block
#   ./register.sh --mcp-url --port 8787
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_ROOT="$(cd "$HERE/.." && pwd)"
PROJECT_ROOT="$(cd "$MCP_ROOT/.." && pwd)"

# Prefer the compiled entrypoint; fall back to the source if it has not been
# built yet (a tsx/ts-node runner would also work here).
if [[ -f "$MCP_ROOT/dist/index.js" ]]; then
  ENTRY="$MCP_ROOT/dist/index.js"
elif [[ -f "$MCP_ROOT/src/index.ts" ]]; then
  ENTRY="$MCP_ROOT/src/index.ts"
else
  echo "error: neither dist/index.js nor src/index.ts found in $MCP_ROOT" >&2
  exit 1
fi

MODE="generic"
PORT="${PORT:-8787}"
HOST="${HOST:-127.0.0.1}"
URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mcp-url)
      MODE="url"
      if [[ "${2:-}" =~ ^https?:// ]]; then
        URL="$2"; shift 2
      else
        shift
      fi
      ;;
    --claude)  MODE="claude"; shift ;;
    --codex)   MODE="codex"; shift ;;
    --opencode) MODE="opencode"; shift ;;
    --port)    PORT="$2"; shift 2 ;;
    --host)    HOST="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$URL" ]]; then
  URL="http://${HOST}:${PORT}/mcp"
fi

case "$MODE" in
  url)
    cat <<EOF
Add this to your MCP client config:

{
  "mcpServers": {
    "content-creation": {
      "type": "http",
      "url": "${URL}"
    }
  }
}

Or, for clients that use the Streamable HTTP key:

{
  "mcpServers": {
    "content-creation": {
      "url": "${URL}"
    }
  }
}
EOF
    ;;
  claude)
    cat <<EOF
Claude Desktop / Claude Code (~/.claude_desktop_config.json or .mcp.json):

{
  "mcpServers": {
    "content-creation": {
      "command": "node",
      "args": ["${ENTRY}"],
      "env": {}
    }
  }
}
EOF
    ;;
  codex)
    cat <<EOF
Codex (~/.codex/config.toml):

[mcp_servers.content-creation]
command = "node"
args = ["${ENTRY}"]
EOF
    ;;
  opencode)
    cat <<EOF
OpenCode (opencode.json):

{
  "\$schema": "https://opencode.ai/config.json",
  "mcp": {
    "content-creation": {
      "type": "local",
      "command": ["node", "${ENTRY}"],
      "enabled": true
    }
  }
}
EOF
    ;;
  generic)
    cat <<EOF
Generic MCP client config (stdio):

{
  "mcpServers": {
    "content-creation": {
      "command": "node",
      "args": ["${ENTRY}"],
      "env": {}
    }
  }
}

Generic MCP client config (Streamable HTTP, recommended for multi-client use):

{
  "mcpServers": {
    "content-creation": {
      "type": "http",
      "url": "${URL}"
    }
  }
}

Start the HTTP server with:

  node ${MCP_ROOT}/dist/http.js

then set PORT=${PORT} HOST=${HOST} if the defaults do not suit.
EOF
    ;;
esac
