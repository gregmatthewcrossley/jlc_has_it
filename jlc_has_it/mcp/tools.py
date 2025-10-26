"""MCP tool definitions for JLC Has It component search and integration."""

import shutil
from pathlib import Path
from typing import Any, Optional

from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.kicad.project import ProjectConfig
from jlc_has_it.core.library_downloader import LibraryDownloader
from jlc_has_it.core.search import ComponentSearch, QueryParams


class JLCTools:
    """Tools for JLC Has It MCP server."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize tools with database connection.

        Args:
            db_manager: DatabaseManager instance for component queries
        """
        self.db_manager = db_manager
        self.downloader = LibraryDownloader()

    def search_components(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        manufacturer: Optional[str] = None,
        basic_only: bool = True,
        in_stock_only: bool = True,
        max_price: Optional[float] = None,
        package: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for components matching criteria.

        Args:
            query: Free-text search in description
            category: Component category (e.g., "Capacitors", "Resistors")
            subcategory: Subcategory filter
            manufacturer: Manufacturer name filter
            basic_only: Only return Basic parts (not Extended)
            in_stock_only: Only return in-stock components
            max_price: Maximum unit price
            package: Package type (e.g., "0603", "0805")
            limit: Maximum number of results to return

        Returns:
            List of components with: lcsc, description, manufacturer, stock, price, basic
        """
        conn = self.db_manager.get_connection()
        search_engine = ComponentSearch(conn)

        params = QueryParams(
            category=category,
            subcategory=subcategory,
            manufacturer=manufacturer,
            description_contains=query,
            basic_only=basic_only,
            in_stock_only=in_stock_only,
            max_price=max_price,
            package=package,
            limit=limit,
        )

        results = search_engine.search(params)

        return [
            {
                "lcsc_id": comp.lcsc,
                "description": comp.description,
                "manufacturer": comp.manufacturer,
                "category": comp.category,
                "stock": comp.stock,
                "price": comp.price,
                "basic": comp.basic,
                "mfr_id": comp.mfr,
            }
            for comp in results
        ]

    def get_component_details(self, lcsc_id: str) -> Optional[dict[str, Any]]:
        """Get full details for a single component.

        Args:
            lcsc_id: JLCPCB part number (e.g., "C12345")

        Returns:
            Component details including attributes, or None if not found
        """
        conn = self.db_manager.get_connection()
        search_engine = ComponentSearch(conn)

        component = search_engine.search_by_lcsc(lcsc_id)
        if component is None:
            return None

        return {
            "lcsc_id": component.lcsc,
            "description": component.description,
            "manufacturer": component.manufacturer,
            "mfr_id": component.mfr,
            "category": component.category,
            "subcategory": component.subcategory,
            "stock": component.stock,
            "price": component.price,
            "basic": component.basic,
            "joints": component.joints,
            "attributes": component.attributes,
            "price_tiers": component.price_tiers,
        }

    def add_to_project(self, lcsc_id: str, project_path: Optional[str] = None) -> dict[str, Any]:
        """Add a component to a KiCad project.

        Downloads the component library if needed, copies files to project,
        and updates library tables.

        Args:
            lcsc_id: JLCPCB part number
            project_path: Path to KiCad project directory
                         (auto-detected if not provided)

        Returns:
            Success status with paths and messages
        """
        # Detect project if not specified
        if project_path is None:
            detected = ProjectConfig.find_project_root(Path.cwd())
            if detected is None:
                return {
                    "success": False,
                    "error": "No KiCad project found. Please specify project_path.",
                }
            project_path = str(detected)

        project = Path(project_path)

        try:
            # Validate project
            config = ProjectConfig(project)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # Download library
        library = self.downloader.download_component(lcsc_id)
        if library is None or not library.is_valid():
            return {
                "success": False,
                "error": f"Failed to download valid library for {lcsc_id}",
            }

        try:
            # Create library directories
            lib_dir, fp_dir = config.create_library_directories()
            model_dir = project / "libraries" / "3d_models"
            model_dir.mkdir(parents=True, exist_ok=True)

            # Copy symbol file
            symbol_dest = lib_dir / "jlc-components.kicad_sym"
            if not symbol_dest.exists():
                shutil.copy2(library.symbol_path, symbol_dest)
            else:
                # Component library already exists
                pass

            # Copy footprints
            copied_footprints = 0
            for fp_file in library.footprint_dir.glob("*.kicad_mod"):
                shutil.copy2(fp_file, fp_dir / fp_file.name)
                copied_footprints += 1

            # Copy models
            copied_models = 0
            for model_file in library.model_dir.glob("*"):
                if model_file.is_file():
                    shutil.copy2(model_file, model_dir / model_file.name)
                    copied_models += 1

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

            return {
                "success": True,
                "lcsc_id": lcsc_id,
                "project": str(project),
                "symbol_file": str(symbol_dest),
                "footprints_dir": str(fp_dir),
                "models_dir": str(model_dir),
                "files_copied": {
                    "footprints": copied_footprints,
                    "models": copied_models,
                },
                "message": (
                    f"Added {lcsc_id} to {project.name}. "
                    "Refresh KiCad libraries to use the component."
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add component to project: {str(e)}",
            }

    def compare_components(self, lcsc_ids: list[str]) -> dict[str, Any]:
        """Compare specifications of multiple components.

        Args:
            lcsc_ids: List of JLCPCB part numbers

        Returns:
            Comparison table with component specs
        """
        conn = self.db_manager.get_connection()
        search_engine = ComponentSearch(conn)

        components = []
        for lcsc_id in lcsc_ids:
            comp = search_engine.search_by_lcsc(lcsc_id)
            if comp:
                components.append(comp)

        if not components:
            return {"success": False, "error": "No components found"}

        # Extract common attributes for comparison
        comparison = {
            "components": [],
            "attributes": {},
        }

        for comp in components:
            comparison["components"].append(
                {
                    "lcsc_id": comp.lcsc,
                    "description": comp.description,
                    "manufacturer": comp.manufacturer,
                    "stock": comp.stock,
                    "price": comp.price,
                    "basic": comp.basic,
                }
            )

            # Collect unique attributes
            for attr_name, attr_value in comp.attributes.items():
                if attr_name not in comparison["attributes"]:
                    comparison["attributes"][attr_name] = []
                comparison["attributes"][attr_name].append(
                    {
                        "lcsc_id": comp.lcsc,
                        "value": (
                            attr_value.get("value") if isinstance(attr_value, dict) else attr_value
                        ),
                        "unit": attr_value.get("unit", "") if isinstance(attr_value, dict) else "",
                    }
                )

        return {"success": True, "comparison": comparison}
