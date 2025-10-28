"""MCP server entry point for JLC Has It."""

import asyncio
import json
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from jlc_has_it.core.database import DatabaseManager

from .tools import JLCTools


async def main() -> None:
    """Run the JLC Has It MCP server."""
    # Initialize database manager
    db_manager = DatabaseManager()
    db_manager.update_if_needed()

    # Initialize tools
    tools = JLCTools(db_manager)

    # Create MCP server
    server = Server("jlc-has-it")

    # Print ready message
    print("✓ JLC Has It MCP server initialized and ready for connections", file=sys.stderr)
    print("  Waiting for Claude Code/Desktop to connect...", file=sys.stderr)

    # Define MCP tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Return list of available tools."""
        return [
            Tool(
                name="search_components",
                description=(
                    "Search for JLCPCB components with filters. "
                    "Use this to find components matching user requirements. "
                    "Returns top results sorted by basic parts first, "
                    "then by stock, then by price."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Free-text search query (e.g., "
                                "'10uF 50V capacitor', '100k resistor')"
                            ),
                        },
                        "category": {
                            "type": "string",
                            "description": (
                                "Component category like 'Capacitors', "
                                "'Resistors', 'Diodes', etc."
                            ),
                        },
                        "subcategory": {
                            "type": "string",
                            "description": (
                                "More specific category filter "
                                "(e.g., 'Multilayer Ceramic Capacitors MLCC')"
                            ),
                        },
                        "manufacturer": {
                            "type": "string",
                            "description": (
                                "Filter by manufacturer name " "(e.g., 'Samsung', 'Yageo')"
                            ),
                        },
                        "basic_only": {
                            "type": "boolean",
                            "description": (
                                "Only return Basic parts (not Extended). "
                                "Basic parts are preferred - faster delivery, "
                                "better availability. Default: true"
                            ),
                            "default": True,
                        },
                        "in_stock_only": {
                            "type": "boolean",
                            "description": ("Only return in-stock components. Default: true"),
                            "default": True,
                        },
                        "max_price": {
                            "type": "number",
                            "description": "Maximum unit price in USD",
                        },
                        "package": {
                            "type": "string",
                            "description": (
                                "Package type filter (e.g., '0603', '0805', "
                                "'through-hole', 'SOT-23')"
                            ),
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of results to skip for pagination (default: 0)",
                            "default": 0,
                        },
                        "limit": {
                            "type": "integer",
                            "description": (
                                "Maximum number of results to return (default: 20, max: 100)"
                            ),
                            "default": 20,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_component_details",
                description=(
                    "Get full specifications for a single component. "
                    "Use this after search to show detailed specs to the user."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lcsc_id": {
                            "type": "string",
                            "description": ("JLCPCB part number (e.g., 'C12345', 'R67890')"),
                        },
                    },
                    "required": ["lcsc_id"],
                },
            ),
            Tool(
                name="add_to_project",
                description=(
                    "Add a component to a user's KiCad project. "
                    "This downloads the symbol, footprint, and 3D model files "
                    "from JLCPCB/EasyEDA, copies them to the project, "
                    "and updates the KiCad library tables. "
                    "The user will then need to refresh their KiCad libraries."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lcsc_id": {
                            "type": "string",
                            "description": "JLCPCB part number to add",
                        },
                        "project_path": {
                            "type": "string",
                            "description": (
                                "Path to KiCad project directory " "(auto-detected if not provided)"
                            ),
                        },
                    },
                    "required": ["lcsc_id"],
                },
            ),
            Tool(
                name="compare_components",
                description=(
                    "Compare specifications of multiple components side-by-side. "
                    "Useful for helping users choose between similar parts."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lcsc_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "List of JLCPCB part numbers to compare "
                                "(e.g., ['C12345', 'C23456'])"
                            ),
                        },
                    },
                    "required": ["lcsc_ids"],
                },
            ),
            Tool(
                name="add_from_ultralibrarian",
                description=(
                    "Add a component to a user's KiCad project from Ultralibrarian. "
                    "Use this when search results show a part is available on Ultralibrarian. "
                    "This opens the user's browser to manually download and export the files, "
                    "then automatically detects the download and integrates it into the project. "
                    "The user will then need to refresh their KiCad libraries."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "manufacturer": {
                            "type": "string",
                            "description": (
                                "Component manufacturer name "
                                "(e.g., 'Littelfuse', 'Bourns Electronics')"
                            ),
                        },
                        "mpn": {
                            "type": "string",
                            "description": (
                                "Manufacturer part number "
                                "(e.g., '0501010.WR1', 'SF-0603F300-2')"
                            ),
                        },
                        "project_path": {
                            "type": "string",
                            "description": (
                                "Path to KiCad project directory "
                                "(auto-detected if not provided)"
                            ),
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": (
                                "Maximum time to wait for download in seconds "
                                "(default: 300 = 5 minutes)"
                            ),
                            "default": 300,
                        },
                    },
                    "required": ["manufacturer", "mpn"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Call a tool and return results."""
        try:
            if name == "search_components":
                result = tools.search_components(**arguments)
            elif name == "get_component_details":
                result = tools.get_component_details(**arguments)
            elif name == "add_to_project":
                result = tools.add_to_project(**arguments)
            elif name == "compare_components":
                result = tools.compare_components(**arguments)
            elif name == "add_from_ultralibrarian":
                result = tools.add_from_ultralibrarian(**arguments)
            else:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2),
                    )
                ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str),
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(e), "tool": name}, indent=2),
                )
            ]

    # Run the server on stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run() -> None:
    """Synchronous entry point for MCP server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
