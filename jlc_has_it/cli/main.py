"""CLI entry point for JLC Has It component search tool."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from jlc_has_it import __version__
from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.search import ComponentSearch, QueryParams

# Create Typer app
app = typer.Typer(
    help="JLC Has It - Find JLCPCB components and add them to your KiCad projects",
    no_args_is_help=True,
)
console = Console()


def show_version() -> None:
    """Show version and exit."""
    console.print(f"JLC Has It {__version__}")
    raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=lambda x: show_version() if x else None,
    ),
) -> None:
    """JLC Has It - Conversational component search for KiCad and JLCPCB."""


@app.command()
def search(
    query: str = typer.Argument(..., help="Component search query"),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by component category (e.g., 'Capacitors', 'Resistors')",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Maximum number of results to return",
    ),
    in_stock: bool = typer.Option(
        True,
        "--in-stock/--all",
        help="Only show components in stock",
    ),
    basic_only: bool = typer.Option(
        False,
        "--basic",
        help="Only show basic parts (not extended)",
    ),
) -> None:
    """Search for components by description or specifications.

    Examples:
        jlc-has-it search "10uF capacitor 50V"
        jlc-has-it search "100k resistor 0805" --category Resistors
        jlc-has-it search "220uF" --limit 10 --basic
    """
    try:
        # Initialize database
        db_manager = DatabaseManager()
        db_manager.update_if_needed()
        conn = db_manager.get_connection()
        search_engine = ComponentSearch(conn)

        # For now, just do a simple description search
        params = QueryParams(
            description_contains=query,
            category=category,
            limit=limit,
            in_stock_only=in_stock,
            basic_only=basic_only,
        )

        results = search_engine.search(params)

        if not results:
            console.print(f"[yellow]No components found matching '{query}'[/yellow]")
            return

        # Display results in a table
        table = Table(title=f"Search Results ({len(results)} components)")
        table.add_column("LCSC", style="cyan")
        table.add_column("Description", style="magenta")
        table.add_column("Manufacturer", style="green")
        table.add_column("Stock", style="yellow")
        table.add_column("Price ($)", style="blue")
        table.add_column("Basic", style="white")

        for component in results:
            table.add_row(
                component.lcsc,
                component.description[:50],
                component.manufacturer,
                str(component.stock),
                f"${component.price:.4f}" if component.price else "N/A",
                "✓" if component.basic else "✗",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from e


@app.command()
def info() -> None:
    """Show information about JLC Has It and available commands."""
    info_text = f"""
[bold cyan]JLC Has It {__version__}[/bold cyan]

[bold]Local MCP server for conversational component search in KiCad[/bold]

[bold yellow]Available Commands:[/bold yellow]
  search      Search for components by description or specifications
  info        Show this help information

[bold yellow]Basic Usage:[/bold yellow]
  jlc-has-it search "10uF 50V capacitor"
  jlc-has-it search "100k resistor" --category Resistors

[bold yellow]Options:[/bold yellow]
  --version           Show version and exit
  --help              Show detailed help for any command

[bold yellow]Features:[/bold yellow]
  • Search JLCPCB components by description or specifications
  • Filter by category, manufacturer, stock status
  • Show pricing and stock information
  • Future: Add components to KiCad projects

[bold yellow]Note:[/bold yellow]
  This CLI is a simple interface to the core library. For the best experience,
  use the MCP server with Claude Code or Claude Desktop for conversational search.
    """
    console.print(info_text)


if __name__ == "__main__":
    app()
