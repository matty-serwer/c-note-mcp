#!/usr/bin/env bash
# C-Note MCP Setup Script
# Run once: bash setup.sh

set -e

VAULT="$HOME/_Workspace/Docs/C-Note"
SERVER_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER="$SERVER_DIR/cnote-mcp-server.py"

echo "▶ Ensuring vault structure at $VAULT..."
mkdir -p "$VAULT/.cnote"
mkdir -p "$VAULT/_system"
mkdir -p "$VAULT/inbox"
mkdir -p "$VAULT/daily"
mkdir -p "$VAULT/clients"
mkdir -p "$VAULT/projects"
mkdir -p "$VAULT/library"
mkdir -p "$VAULT/life"

echo "▶ Installing Python dependencies..."
pip3 install "mcp[cli]" pydantic --quiet

echo "▶ Verifying server syntax..."
python3 -m py_compile "$SERVER" && echo "   ✓ cnote-mcp-server.py OK"

echo ""
echo "▶ Add this to ~/.claude/claude_desktop_config.json under mcpServers:"
echo ""
cat <<EOF
{
  "mcpServers": {
    "cnote": {
      "command": "python3",
      "args": ["$SERVER"]
    }
  }
}
EOF

echo ""
echo "▶ Optional: override the vault path"
echo "   export CNOTE_VAULT=/path/to/your/vault"
echo "   (or write the path to ~/.config/cnote/vault_path)"
echo ""
echo "▶ Vault root: $VAULT"
echo "✓ Setup complete. Restart Claude Desktop to load the MCP server."
