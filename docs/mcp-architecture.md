# MCP Architecture

This document describes the Model Context Protocol (MCP) implementation for JLC Has It.

## Overview

JLC Has It is built as a **local MCP server** that provides conversational component search through Claude Code/Desktop. The user has natural conversations with Claude, which calls MCP tools to search, filter, and add components to KiCad projects.

## Why MCP?

**Conversational interface is perfect for component selection:**
- User can ask questions and get expert advice from Claude
- Natural refinement: "Show me only ceramic capacitors"
- Context retention: Claude remembers what you searched for
- No CLI syntax to memorize

**Simpler architecture:**
- No Claude API calls needed (user already in Claude!)
- Claude handles NLP natively
- MCP server just provides structured tools
- Fewer moving parts than standalone CLI + API integration

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Claude Code / Claude Desktop (User Interface)          │
│                                                          │
│  User: "I need a 50V 220uF through-hole capacitor"     │
│         ↓                                               │
│  Claude: [calls MCP search_components tool]             │
└──────────────────────────────┬──────────────────────────┘
                               │ stdio transport
                               │ (JSON-RPC)
                               ↓
┌─────────────────────────────────────────────────────────┐
│  Local MCP Server (jlc-has-it-mcp)                      │
│                                                          │
│  ┌─────────────────────────────────────────────────┐  │
│  │  MCP Tools Layer                                │  │
│  │  - search_components(params)                     │  │
│  │  - get_component_details(lcsc_id)               │  │
│  │  - add_to_project(lcsc_id, project_path)        │  │
│  │  - compare_components(lcsc_ids)                  │  │
│  └─────────────┬───────────────────────────────────┘  │
│                ↓                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Core Library (LLM-agnostic)                    │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  database.py                             │  │  │
│  │  │  - Download/update jlcparts database     │  │  │
│  │  │  - Query SQLite with structured params   │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  search.py                              │  │  │
│  │  │  - Filter & rank components             │  │  │
│  │  │  - Return top N candidates              │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  library_downloader.py                  │  │  │
│  │  │  - Parallel downloads (easyeda2kicad)   │  │  │
│  │  │  - Validate complete packages           │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  kicad/project.py                       │  │  │
│  │  │  - Integrate into KiCad project         │  │  │
│  │  │  - Update library tables                │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────┐
│  Local Filesystem                                        │
│  - ~/.cache/jlc_has_it/cache.sqlite3                   │
│  - /tmp/jlc_has_it/cache/ (downloaded libraries)        │
│  - ./my-project/ (KiCad project)                        │
└─────────────────────────────────────────────────────────┘
```

## MCP Tools

The MCP server exposes these tools to Claude:

### 1. search_components

**Purpose**: Search for components matching user requirements

**Parameters**:
```json
{
  "component_type": "capacitor",
  "voltage_min": 50,
  "capacitance": 220,
  "capacitance_unit": "uF",
  "package": "through-hole",
  "limit": 20
}
```

**Process**:
1. Query jlcparts database with filters
2. Rank by: basic > extended, high stock, low price
3. Take top N candidates (default 20)
4. Download libraries in parallel for all candidates
5. Validate each (symbol + footprint + 3D model)
6. Return only parts with complete packages

**Returns**:
```json
[
  {
    "lcsc_id": "C12345",
    "description": "220uF 50V Electrolytic Through-hole",
    "manufacturer": "Rubycon",
    "stock": 5000,
    "price": 0.15,
    "basic": true
  },
  ...
]
```

### 2. get_component_details

**Purpose**: Get detailed specifications for a specific component

**Parameters**:
```json
{
  "lcsc_id": "C12345"
}
```

**Returns**:
```json
{
  "lcsc_id": "C12345",
  "mfr": "16ZLH220MEFC6.3X11",
  "description": "220uF ±20% 50V Aluminum Electrolytic Capacitor",
  "manufacturer": "Rubycon",
  "category": "Capacitors",
  "subcategory": "Aluminum Electrolytic Capacitors - Leaded",
  "datasheet_url": "https://lcsc.com/product-detail/...",
  "attributes": {
    "Capacitance": {"value": 220, "unit": "uF"},
    "Voltage": {"value": 50, "unit": "V"},
    "Tolerance": {"value": 20, "unit": "%"},
    "Package": "Radial"
  },
  "stock": 5000,
  "price_tiers": [
    {"qty": 1, "price": 0.15},
    {"qty": 10, "price": 0.13},
    {"qty": 100, "price": 0.11}
  ]
}
```

### 3. add_to_project

**Purpose**: Add component to KiCad project libraries

**Parameters**:
```json
{
  "lcsc_id": "C12345",
  "project_path": "./my-project"
}
```

**Process**:
1. Retrieve validated libraries from cache (already downloaded in search)
2. Append symbol to `{project}/libraries/jlc-components.kicad_sym`
3. Copy footprint to `{project}/libraries/footprints.pretty/`
4. Copy 3D models to `{project}/libraries/3d_models/`
5. Update `sym-lib-table` and `fp-lib-table` if needed

**Returns**:
```json
{
  "success": true,
  "message": "Added C12345 to ./my-project/libraries/. Refresh KiCad to use it.",
  "files_added": {
    "symbol": "jlc-components.kicad_sym",
    "footprint": "footprints.pretty/C0402.kicad_mod",
    "models": ["3d_models/C0402.step", "3d_models/C0402.wrl"]
  }
}
```

### 4. compare_components

**Purpose**: Compare specifications of multiple components

**Parameters**:
```json
{
  "lcsc_ids": ["C12345", "C23456", "C34567"]
}
```

**Returns**:
Comparison table showing key differences in specs, pricing, availability

## Configuration

### User Setup

**1. Install the package:**
```bash
pip install jlc-has-it
```

**2. Configure in Claude Code:**

Edit `.claude/mcp_settings.json`:
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

**3. Restart Claude Code**

Now the user can ask Claude:
```
"I need a through-hole capacitor rated for 50V and 220uF"
```

### Transport

**Protocol**: stdio (standard input/output)
- MCP server reads JSON-RPC messages from stdin
- Writes responses to stdout
- Claude Code manages the subprocess

**Why stdio?**
- Simple and reliable
- No network configuration
- Built-in to MCP SDK
- Works for local servers

## Implementation

### MCP Server Entry Point

```python
# jlc_has_it/mcp/__main__.py
import asyncio
from mcp.server import Server
from .tools import register_tools

async def main():
    server = Server("jlc-has-it")
    register_tools(server)

    # Run stdio transport
    from mcp.server.stdio import stdio_server
    async with stdio_server() as streams:
        await server.run(
            streams[0],  # read stream
            streams[1],  # write stream
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### Tool Implementation

```python
# jlc_has_it/mcp/tools.py
from mcp.server import Server
from mcp.types import Tool, TextContent
from jlc_has_it.core import ComponentSearch, LibraryDownloader

def register_tools(server: Server):
    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="search_components",
                description="Search for JLCPCB components",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_type": {"type": "string"},
                        "voltage_min": {"type": "number"},
                        "capacitance": {"type": "number"},
                        "capacitance_unit": {"type": "string"},
                        "package": {"type": "string"},
                        "limit": {"type": "number", "default": 20}
                    }
                }
            ),
            # ... other tools
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "search_components":
            search = ComponentSearch()
            candidates = search.search(**arguments)

            downloader = LibraryDownloader()
            results = downloader.download_and_filter(candidates)

            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )]
```

## Benefits Over Standalone CLI

**1. No Claude API calls needed:**
- Standalone CLI would need to call Claude API for NLP parsing
- Costs money per query
- Requires API key configuration
- Network latency

**MCP approach:**
- User already in Claude
- Claude handles NLP natively
- Free (part of Claude subscription)
- Instant parsing

**2. Conversational workflow:**
- User can refine search through conversation
- Ask questions about components
- Get advice on selection
- Context retention across queries

**3. Simpler architecture:**
```
Standalone CLI:  User → CLI → Claude API → Parse → Search → Results
MCP:             User → Claude → MCP Tools → Search → Results
```

## Layered Architecture

The core library is **completely LLM-agnostic** and can be used anywhere:

```python
# Direct library usage (no MCP, no LLM)
from jlc_has_it.core import ComponentSearch

search = ComponentSearch()
results = search.search(
    component_type="capacitor",
    voltage_min=50,
    capacitance=220,
    capacitance_unit="uF"
)
```

**MCP is just a thin wrapper:**
```python
# MCP tool wraps core library
@server.call_tool()
async def search_components(args):
    search = ComponentSearch()  # Core library
    return search.search(**args)
```

**This enables:**
- MCP interface (primary)
- CLI interface (optional, for scripts)
- Future: REST API, LangChain integration, etc.
- Testing without MCP/LLM overhead

## Testing Strategy

**1. Core library tests (no MCP):**
```python
def test_search():
    search = ComponentSearch()
    results = search.search(component_type="capacitor")
    assert len(results) > 0
```

**2. MCP tool tests:**
```python
async def test_search_tool():
    server = create_test_server()
    response = await server.call_tool(
        "search_components",
        {"component_type": "capacitor"}
    )
    assert response[0].text is not None
```

**3. Integration tests:**
- Mock MCP client
- Test full workflow
- Verify tool responses

## Error Handling

**MCP server errors:**
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        # ... tool implementation
    except DatabaseError as e:
        return [TextContent(
            type="text",
            text=f"Database error: {e}. Try again later."
        )]
    except LibraryDownloadError as e:
        return [TextContent(
            type="text",
            text=f"Could not download libraries for this component."
        )]
```

**Claude handles gracefully:**
- Shows error message to user
- Suggests alternatives
- Can retry with different parameters

## Performance

**Parallel downloads:**
- Download 20 candidates in ~5-10 seconds
- Use ThreadPoolExecutor with 10 workers
- Show progress in MCP responses

**Caching:**
- Cache jlcparts database locally (~50MB)
- Cache downloaded libraries in /tmp/jlc_has_it/cache/
- Reuse libraries across searches

**Database:**
- SQLite queries are fast (<100ms)
- Indexed on common fields (category, basic, stock)
- JSON extraction for attributes

## Summary

**Local MCP server architecture:**
- ✅ Conversational interface through Claude
- ✅ No Claude API calls needed (simpler, free)
- ✅ Core library is LLM-agnostic (reusable)
- ✅ stdio transport (simple, reliable)
- ✅ Runs on user's local machine
- ✅ Direct filesystem access for KiCad projects
- ✅ Optional CLI for scripting

**Perfect for conversational component selection with Claude's expert guidance!**
