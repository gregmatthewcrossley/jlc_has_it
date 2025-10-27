#!/bin/bash
# Setup script for JLC Has It MCP server in Claude Code
# This script creates .mcp.json in your current KiCad project directory

set -e

# Check if we're in a KiCad project directory
if [ ! -f "*.kicad_pro" ] && [ ! -f *.kicad_pro 2>/dev/null ]; then
    echo "⚠ Warning: This doesn't appear to be a KiCad project directory"
    echo ""
    echo "This script should be run from your KiCad project folder (the one containing .kicad_pro files)"
    echo ""
    echo "Usage:"
    echo "  cd ~/my-kicad-project"
    echo "  /path/to/jlc_has_it/setup-mcp.sh"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

MCP_CONFIG_FILE=".mcp.json"

echo "Setting up JLC Has It MCP server for this project..."

# Check if .mcp.json already exists
if [ -f "$MCP_CONFIG_FILE" ]; then
    echo "Found existing .mcp.json in this directory"

    # Check if jlc-has-it is already configured
    if grep -q "jlc-has-it" "$MCP_CONFIG_FILE"; then
        echo "✓ JLC Has It is already configured in this project"
        echo ""
        echo "Next steps:"
        echo "1. Close any running Claude Code instances (Cmd+Q or click Quit)"
        echo "2. Reopen Claude Code in this project folder: claude"
        echo "3. When prompted, approve access to the 'jlc-has-it' MCP server"
        echo "4. Ask Claude Code: 'I need a 100nF capacitor for 16V'"
        exit 0
    else
        echo "⚠ Adding JLC Has It to existing MCP servers in .mcp.json..."
        # For simplicity, we'll just show the user what to add
        cat << 'EOF'

To add JLC Has It to your existing .mcp.json, add this to the mcpServers section:

    "jlc-has-it": {
      "command": "jlc-has-it-mcp",
      "args": []
    }

EOF
        exit 1
    fi
else
    # Create new .mcp.json in current directory
    echo "Creating .mcp.json in this project directory"

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
    echo "1. Close any running Claude Code instances (Cmd+Q or click Quit)"
    echo "2. Reopen Claude Code in this project folder: claude"
    echo "3. When prompted, approve access to the 'jlc-has-it' MCP server"
    echo "4. Ask Claude Code: 'I need a 100nF capacitor for 16V'"
fi
