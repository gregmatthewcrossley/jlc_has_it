"""MCP tool definitions for JLC Has It component search and integration."""

import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.kicad.project import ProjectConfig
from jlc_has_it.core.library_downloader import LibraryDownloader
from jlc_has_it.core.search import ComponentSearch, QueryParams
from jlc_has_it.core.ultralibrarian_browser import open_ultralibrarian_part
from jlc_has_it.core.ultralibrarian_waiter import wait_for_ultralibrarian_download
from jlc_has_it.core.ultralibrarian_extractor import extract_to_project

logger = logging.getLogger(__name__)


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
        basic_only: bool = False,
        in_stock_only: bool = True,
        max_price: Optional[float] = None,
        package: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
        attribute_ranges: Optional[dict[str, dict[str, Any]]] = None,
        offset: int = 0,
        limit: int = 20,
        validate_libraries: bool = True,
        validation_candidates: int = 20,
    ) -> dict[str, Any]:
        """Search for components matching criteria with pagination support.

        By default, validates that components have complete KiCad libraries
        (symbol, footprint, and 3D model) available from JLCPCB/EasyEDA.

        Args:
            query: Free-text search in description
            category: Component category (e.g., "Capacitors", "Resistors")
            subcategory: Subcategory filter
            manufacturer: Manufacturer name filter
            basic_only: Only return Basic parts (not Extended). Default False to include
                       specialty parts like resettable fuses (which are Extended-only).
                       Results are sorted with Basic parts first regardless.
            in_stock_only: Only return in-stock components
            max_price: Maximum unit price
            package: Package type (e.g., "0603", "0805")
            attributes: Exact attribute matching (e.g., {"Voltage": "50V"})
            attribute_ranges: Range attribute matching (e.g., {"Voltage": {"min": "10V", "max": "100V"}})
            offset: Number of results to skip (for pagination)
            limit: Maximum number of results to return (max 100, default 20)
            validate_libraries: If True, validate that components have complete KiCad
                              libraries (symbol, footprint, 3D model) available
            validation_candidates: Number of top candidates to validate (default 20)

        Returns:
            Dictionary with:
            - results: List of components (filtered to only validated ones if validate_libraries=True)
            - offset: Current offset
            - limit: Results per page
            - has_more: Whether more results are available
            - library_validation_status: Status info about validation (if validate_libraries=True)
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
            attributes=attributes,
            attribute_ranges=attribute_ranges,
            offset=max(0, offset),  # Ensure non-negative offset
            limit=max(1, min(limit, 100)),  # Ensure limit between 1 and 100
        )

        results = search_engine.search(params)

        # Validate libraries for top candidates if requested
        validated_lcsc_ids = set()
        validation_status = None

        if validate_libraries and results:
            # Get top N candidates for validation
            candidates = results[: min(len(results), validation_candidates)]
            candidate_lcsc_ids = [f"C{comp.lcsc}" for comp in candidates]

            # Download and validate libraries in parallel
            validated_libs = self.downloader.get_validated_libraries(
                candidate_lcsc_ids, max_workers=10
            )

            validated_lcsc_ids = set(validated_libs.keys())
            failed_count = len(candidate_lcsc_ids) - len(validated_lcsc_ids)

            validation_status = {
                "total_candidates": len(candidate_lcsc_ids),
                "validated": len(validated_lcsc_ids),
                "failed": failed_count,
                "validation_method": "parallel_download_and_validate",
            }

            # Filter results to only include validated components
            results = [
                comp for comp in results if f"C{comp.lcsc}" in validated_lcsc_ids
            ]

        return {
            "results": [
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
            ],
            "offset": params.offset,
            "limit": params.limit,
            "has_more": len(results) >= params.limit,
            "library_validation_status": validation_status,
        }

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
        """Compare specifications of multiple components side-by-side.

        Provides a detailed comparison table showing how components differ across
        key specifications like voltage, capacitance, price, stock, etc.

        Args:
            lcsc_ids: List of JLCPCB part numbers (e.g., ["C1525", "C307331"])

        Returns:
            Dictionary with success status and comparison data:
            {
                "success": True/False,
                "error": "error message if success=False",
                "comparison": {
                    "count": number of components found,
                    "components": [
                        {
                            "lcsc_id": "C1525",
                            "description": "10uF ±10% 10V X5R 0603",
                            "manufacturer": "Samsung",
                            "category": "Capacitors",
                            "stock": 50000,
                            "price": 0.0012,
                            "basic": True,
                        },
                        ...
                    ],
                    "attributes": {
                        "Voltage": [
                            {"lcsc_id": "C1525", "value": 10, "unit": "V"},
                            {"lcsc_id": "C307331", "value": 16, "unit": "V"},
                        ],
                        "Capacitance": [...],
                        ...
                    }
                }
            }
        """
        if not lcsc_ids:
            return {
                "success": False,
                "error": "No LCSC IDs provided for comparison",
            }

        if len(lcsc_ids) > 10:
            return {
                "success": False,
                "error": "Can only compare up to 10 components at a time",
            }

        conn = self.db_manager.get_connection()
        search_engine = ComponentSearch(conn)

        components = []
        not_found = []

        for lcsc_id in lcsc_ids:
            try:
                comp = search_engine.search_by_lcsc(lcsc_id)
                if comp:
                    components.append(comp)
                else:
                    not_found.append(lcsc_id)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error looking up {lcsc_id}: {str(e)}",
                }

        if not components:
            return {
                "success": False,
                "error": f"No components found for: {', '.join(lcsc_ids)}",
            }

        # Extract common attributes for comparison
        comparison = {
            "count": len(components),
            "not_found": not_found,
            "components": [],
            "attributes": {},
        }

        for comp in components:
            comparison["components"].append(
                {
                    "lcsc_id": comp.lcsc,
                    "description": comp.description,
                    "manufacturer": comp.manufacturer,
                    "category": comp.category,
                    "subcategory": comp.subcategory,
                    "stock": comp.stock,
                    "price": comp.price,
                    "basic": comp.basic,
                    "joints": comp.joints,
                }
            )

            # Collect unique attributes for side-by-side comparison
            for attr_name, attr_value in comp.attributes.items():
                if attr_name not in comparison["attributes"]:
                    comparison["attributes"][attr_name] = []

                # Extract value and unit for consistent formatting
                if isinstance(attr_value, dict):
                    value = attr_value.get("value", attr_value)
                    unit = attr_value.get("unit", "")
                else:
                    value = attr_value
                    unit = ""

                comparison["attributes"][attr_name].append(
                    {
                        "lcsc_id": comp.lcsc,
                        "value": value,
                        "unit": unit,
                    }
                )

        return {"success": True, "comparison": comparison}

    def add_from_ultralibrarian(
        self,
        manufacturer: str,
        mpn: str,
        project_path: Optional[str] = None,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        """Add a component to a KiCad project by downloading from Ultralibrarian.

        This is a user-assisted workflow:
        1. Searches Ultralibrarian for the part
        2. Opens the browser to the part page with export instructions
        3. Waits for the user to manually download and export the files
        4. Extracts the downloaded files to the KiCad project library

        Args:
            manufacturer: Manufacturer name (e.g., "Bourns Electronics")
            mpn: Manufacturer part number (e.g., "SF-0603F300-2")
            project_path: Path to KiCad project directory
                         (auto-detected if not provided)
            timeout_seconds: Maximum time to wait for download (default: 300s = 5 min)

        Returns:
            Dictionary with:
            - success: True if component was added, False otherwise
            - error: Error message if success=False
            - mpn: The MPN that was processed
            - message: Status message for user
            - (additional fields on success)
        """
        try:
            # Move the import inside the function to avoid circular dependencies
            # and to allow the function to work even if Ultralibrarian prototype isn't deployed
            import sys
            import importlib.util

            prototype_path = Path(__file__).parent.parent.parent / "ultralibrarian_scraper_prototype.py"
            if not prototype_path.exists():
                return {
                    "success": False,
                    "error": "Ultralibrarian prototype not found. Cannot search for part.",
                    "mpn": mpn,
                }

            # Load the prototype module
            spec = importlib.util.spec_from_file_location(
                "ultralibrarian_scraper_prototype",
                prototype_path,
            )
            prototype_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(prototype_module)
            scraper = prototype_module.UltraLibrarianScraper()

            # Step 1: Search for the part on Ultralibrarian
            logger.info(f"Searching Ultralibrarian for {manufacturer} {mpn}")
            part_uuid = scraper.search_part(manufacturer, mpn)

            if not part_uuid:
                return {
                    "success": False,
                    "error": f"Part not found on Ultralibrarian: {manufacturer} {mpn}",
                    "mpn": mpn,
                }

            logger.info(f"Found part UUID: {part_uuid}")

            # Step 2: Detect project
            if project_path is None:
                detected = ProjectConfig.find_project_root(Path.cwd())
                if detected is None:
                    return {
                        "success": False,
                        "error": "No KiCad project found. Please specify project_path.",
                        "mpn": mpn,
                    }
                project_path = str(detected)

            project_dir = Path(project_path)

            # Validate project
            try:
                ProjectConfig(project_dir)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "mpn": mpn,
                }

            # Step 3: Open browser and show instructions
            logger.info(f"Opening browser for {mpn}")
            try:
                open_ultralibrarian_part(part_uuid, mpn)
            except ValueError as e:
                return {
                    "success": False,
                    "error": f"Failed to open browser: {e}",
                    "mpn": mpn,
                }

            # Step 4: Wait for download
            logger.info(f"Waiting for download (timeout: {timeout_seconds}s)...")
            ul_folder = wait_for_ultralibrarian_download(
                mpn,
                timeout_seconds=timeout_seconds,
            )

            if ul_folder is None:
                return {
                    "success": False,
                    "error": f"Timeout waiting for download. Please try downloading again.",
                    "mpn": mpn,
                }

            logger.info(f"Download detected: {ul_folder}")

            # Step 5: Extract to project
            logger.info(f"Extracting {mpn} to project...")
            try:
                success = extract_to_project(
                    ul_folder,
                    project_dir,
                    mpn,
                    cleanup=True,
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to extract files: {e}",
                    "mpn": mpn,
                }

            if not success:
                return {
                    "success": False,
                    "error": "Extraction failed. Check logs for details.",
                    "mpn": mpn,
                }

            # Success!
            return {
                "success": True,
                "mpn": mpn,
                "manufacturer": manufacturer,
                "project": str(project_dir),
                "message": (
                    f"Successfully added {mpn} from Ultralibrarian. "
                    "Refresh your KiCad libraries to use this component."
                ),
            }

        except Exception as e:
            logger.error(f"Unexpected error in add_from_ultralibrarian: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
                "mpn": mpn,
            }
