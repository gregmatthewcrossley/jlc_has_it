"""CLI entry point for JLC Has It component search tool."""

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from jlc_has_it import __version__
from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.kicad.project import ProjectConfig
from jlc_has_it.core.library_downloader import LibraryDownloader
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
def add(
    query: str = typer.Argument(..., help="Component search query"),
    project: Optional[Path] = typer.Option(
        None,
        "--project",
        "-p",
        help="Path to KiCad project directory (auto-detected if not provided)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    first: bool = typer.Option(
        False,
        "--first",
        help="Automatically select the first search result",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without actually adding to project",
    ),
) -> None:
    """Search for and add a component to your KiCad project.

    Examples:
        jlc-has-it add "10uF 50V capacitor"
        jlc-has-it add "100k resistor" --project ./my-project --first
        jlc-has-it add "10uF" --dry-run
    """
    try:
        # Initialize database and search
        with console.status("[bold cyan]Initializing database..."):
            db_manager = DatabaseManager()
            db_manager.update_if_needed()
            conn = db_manager.get_connection()
            search_engine = ComponentSearch(conn)

        # Search for components
        with console.status(f"[bold cyan]Searching for '{query}'..."):
            params = QueryParams(
                description_contains=query,
                limit=5,
                in_stock_only=True,
                basic_only=True,
            )
            results = search_engine.search(params)

        if not results:
            console.print(f"[red]No components found matching '{query}'[/red]")
            raise typer.Exit(code=1)

        # Select component
        if first or len(results) == 1:
            selected = results[0]
            console.print(
                f"[green]✓[/green] Selected: " f"{selected.lcsc} - {selected.description[:50]}"
            )
        else:
            # Show options
            console.print("\n[bold]Available components:[/bold]")
            table = Table()
            table.add_column("#", style="cyan")
            table.add_column("LCSC", style="cyan")
            table.add_column("Description", style="magenta")
            table.add_column("Stock", style="yellow")
            table.add_column("Price", style="green")

            for i, comp in enumerate(results, 1):
                table.add_row(
                    str(i),
                    comp.lcsc,
                    comp.description[:40],
                    str(comp.stock),
                    f"${comp.price:.4f}" if comp.price else "N/A",
                )

            console.print(table)
            choice = typer.prompt(
                f"\nEnter component number (1-{len(results)}): ",
                type=int,
            )

            if not 1 <= choice <= len(results):
                console.print("[red]Invalid selection[/red]")
                raise typer.Exit(code=1)

            selected = results[choice - 1]

        # Detect project if not specified
        if project is None:
            detected = ProjectConfig.find_project_root(Path.cwd())
            if detected is None:
                console.print("[red]No KiCad project found. " "Please specify with --project[/red]")
                raise typer.Exit(code=1)
            project = detected

        console.print(f"[cyan]Project: {project}[/cyan]")

        # Download library
        with console.status(f"[bold cyan]Downloading library for {selected.lcsc}..."):
            downloader = LibraryDownloader()
            library = downloader.download_component(selected.lcsc)

        if library is None or not library.is_valid():
            console.print(f"[red]Failed to download valid library for {selected.lcsc}[/red]")
            raise typer.Exit(code=1)

        console.print("[green]✓[/green] Downloaded library")

        if dry_run:
            console.print("[yellow]DRY RUN: Would add component to project[/yellow]")
            console.print(f"  Symbol: {library.symbol_path}")
            console.print(f"  Footprints: {library.footprint_dir}")
            console.print(f"  Models: {library.model_dir}")
            return

        # Add to project
        with console.status("[bold cyan]Adding to project..."):
            config = ProjectConfig(project)

            # Create library directories
            lib_dir, fp_dir = config.create_library_directories()
            model_dir = project / "libraries" / "3d_models"
            model_dir.mkdir(parents=True, exist_ok=True)

            # Copy symbol file
            symbol_dest = lib_dir / "jlc-components.kicad_sym"
            if not symbol_dest.exists():
                shutil.copy2(library.symbol_path, symbol_dest)
            else:
                # Append to existing (would need full implementation)
                console.print(
                    "[yellow]Note: Component library already exists, "
                    "skipping symbol update[/yellow]"
                )

            # Copy footprints
            for fp_file in library.footprint_dir.glob("*.kicad_mod"):
                shutil.copy2(fp_file, fp_dir / fp_file.name)

            # Copy models
            for model_file in library.model_dir.glob("*"):
                if model_file.is_file():
                    shutil.copy2(model_file, model_dir / model_file.name)

            # Update library tables
            config.add_symbol_library(
                name="jlc-components",
                lib_path=symbol_dest,
                description="JLCPCB components added by JLC Has It",
            )

            config.add_footprint_library(
                name="jlc-footprints",
                lib_path=fp_dir,
                description="JLCPCB footprints added by JLC Has It",
            )

        console.print(
            "\n[bold green]✓ Success![/bold green] " f"Added {selected.lcsc} to {project.name}"
        )
        console.print("[cyan]Refresh your KiCad project libraries to use the component.[/cyan]")

    except typer.Exit:
        raise
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
  add         Search for and add a component to your KiCad project
  info        Show this help information

[bold yellow]Basic Usage:[/bold yellow]
  jlc-has-it search "10uF 50V capacitor"
  jlc-has-it add "10uF capacitor" --first
  jlc-has-it add "resistor 0805" --project ./my-project

[bold yellow]Options:[/bold yellow]
  --version           Show version and exit
  --help              Show detailed help for any command

[bold yellow]Features:[/bold yellow]
  • Search JLCPCB components by description or specifications
  • Add components directly to KiCad projects
  • Automatic library downloads and integration
  • Filter by category, manufacturer, stock status
  • Show pricing and stock information

[bold yellow]Note:[/bold yellow]
  This CLI is a simple interface to the core library. For the best experience,
  use the MCP server with Claude Code or Claude Desktop for conversational search.
    """
    console.print(info_text)


if __name__ == "__main__":
    app()
