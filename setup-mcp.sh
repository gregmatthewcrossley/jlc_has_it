#!/bin/bash
# Setup script for JLC Has It MCP server in Claude Code

set -e

MCP_CONFIG_FILE="$HOME/.claude/mcp_settings.json"

echo "Setting up JLC Has It MCP server..."

# Create .claude directory if it doesn't exist
mkdir -p "$HOME/.claude"

# Check if mcp_settings.json already exists
if [ -f "$MCP_CONFIG_FILE" ]; then
    echo "Found existing MCP settings at $MCP_CONFIG_FILE"

    # Check if jlc-has-it is already configured
    if grep -q "jlc-has-it" "$MCP_CONFIG_FILE"; then
        echo "✓ JLC Has It is already configured"
        echo ""
        echo "Next steps:"
        echo "1. If Claude Code is open, completely close and restart it"
        echo "2. Open your KiCad project folder: cd ~/my-kicad-project && claude"
        echo "3. Ask Claude Code: 'I need a 100nF capacitor for 16V'"
        exit 0
    else
        echo "⚠ Adding JLC Has It to existing MCP servers..."
        # For simplicity, we'll just show the user what to add
        cat << 'EOF'

To add JLC Has It to your existing MCP servers, add this to your ~/.claude/mcp_settings.json:

    "jlc-has-it": {
      "command": "jlc-has-it-mcp",
      "args": []
    }

EOF
        exit 1
    fi
else
    # Create new mcp_settings.json
    echo "Creating new MCP settings file at $MCP_CONFIG_FILE"

    cat > "$MCP_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "jlc-has-it": {
      "command": "jlc-has-it-mcp",
      "args": []
    }
  }
}
EOF

    echo "✓ MCP settings configured successfully"
    echo ""
    echo "Next steps:"
    echo "1. Restart Claude Code completely"
    echo "2. Open your KiCad project folder: cd ~/my-kicad-project && claude"
    echo "3. Ask Claude Code: 'I need a 100nF capacitor for 16V'"
fi
