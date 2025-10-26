# JLC Has It

A local MCP server providing conversational component search for KiCad through Claude Code/Desktop.

## Overview

JLC Has It helps hobbyist electronics designers using KiCad 9.0 to quickly find and add JLCPCB components to their projects through a natural conversational interface.

### Problem

Finding suitable components is time-consuming. Components must:
- Be in stock at JLCPCB (preferably "basic" parts)
- Be well-known, commonly used, and relatively inexpensive
- Have a complete KiCad library package (symbol, footprint, and 3D model)

### Solution

**Local MCP server** providing conversational component search through Claude Code/Desktop:

```
User: "I need a through-hole capacitor rated for 50V and 220uF"

Claude: [searches via MCP tools]
        "I found 12 parts with complete KiCad libraries.
         Top options:
         1. C12345 - 220uF 50V Electrolytic | Stock: 5000 | $0.15
         2. C23456 - 220uF 63V Ceramic X7R  | Stock: 3000 | $0.45

         For power supply filtering, the electrolytic is typical.
         Want me to add it to your project?"

User: "Add the electrolytic one"

Claude: [calls add_to_project MCP tool]
        "Added C12345 to ./my-project/libraries/.
         Refresh your KiCad libraries to use it."
```

## Architecture

**Layered Architecture:**
- **Core library** (LLM-agnostic): Component search, database access, library downloading
- **MCP interface** (primary): Conversational interface through Claude Code/Desktop
- **CLI tool** (optional): Simple CLI for scripting/automation

**Key Components:**
- Local MCP server runs on your machine
- Uses jlcparts SQLite database (JLCPCB component data)
- Downloads libraries via easyeda2kicad.py
- Writes to project-specific KiCad libraries

## Installation

```bash
# Clone the repository
git clone https://github.com/gcrossley/jlc_has_it.git
cd jlc_has_it

# Install in development mode
pip install -e .

# Or with CLI support
pip install -e ".[cli]"
```

## Configuration

### MCP Server Setup

Add to your `.claude/mcp_settings.json`:

```json
{
  "mcpServers": {
    "jlc-has-it": {
      "command": "jlc-has-it-mcp",
      "args": []
    }
  }
}
```

Restart Claude Code, and you can now ask Claude to search for components!

## Usage

### Conversational Interface (via MCP)

Just talk to Claude:

```
"I need a 100nF ceramic capacitor rated for 50V in 0402 package"
"Find me an ESP32 module"
"What's the difference between these capacitors?"
"Add C12345 to my project at ./my-kicad-project"
```

### CLI Tool (Optional)

```bash
# Search for components
jlc-has-it search "50v 220uF SMD capacitor"

# Add to KiCad project
jlc-has-it add C12345 --project ./my-kicad-project
```

## Development

```bash
# Install with development dependencies
pip install -e ".[dev,cli]"

# Run tests
pytest

# Format code
black .
ruff check .

# Type checking
mypy jlc_has_it/
```

## Data Sources

**Component data:**
- jlcparts database by Jan Mrázek (MIT License)
- https://github.com/yaqwsx/jlcparts
- Daily-updated SQLite database with all JLCPCB components

**Component libraries:**
- easyeda2kicad.py by uPesy (AGPLv3)
- https://github.com/uPesy/easyeda2kicad.py
- Downloads symbols, footprints, and 3D models from JLCPCB/EasyEDA

## License

MIT License

## Attribution

Component data provided by jlcparts (https://github.com/yaqwsx/jlcparts)
Copyright 2024 Jan Mrázek
Licensed under the MIT License
