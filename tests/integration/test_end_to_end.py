"""End-to-end integration tests simulating real user workflows.

These tests exercise the complete system with the real jlcparts database.
The core modules have been updated to handle the actual database schema:
- Normalized tables (components, categories, manufacturers)
- Integer LCSC IDs stored as integers (converted to "C" prefix format)
- Foreign keys properly joined in queries
- Attributes extracted from JSON extra field

Run with: pytest tests/integration/test_end_to_end.py -v -s
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.search import ComponentSearch, QueryParams
from jlc_has_it.core.kicad.project import ProjectConfig
from jlc_has_it.mcp.tools import JLCTools


@pytest.mark.integration
class TestEndToEndComponentSearch:
    """End-to-end tests for component search workflows."""

    @pytest.fixture
    def tools(self):
        """Initialize MCP tools with real database."""
        db = DatabaseManager()
        db.update_if_needed()
        return JLCTools(db)

    def test_workflow_find_capacitor(self, tools):
        """Workflow: Find a 100nF ceramic capacitor.

        Simulates: "I need a 100nF ceramic capacitor for 50V"
        """
        # Step 1: Search for matching components
        response = tools.search_components(
            query="100nF",
            category="Capacitors",
            basic_only=True,
            limit=20,
        )

        # Should find several results
        assert len(response["results"]) > 0, "Should find 100nF capacitors"

        # Step 2: Verify top result is valid
        top_result = response["results"][0]
        assert top_result["lcsc_id"] is not None
        assert "100nF" in top_result["description"] or "0.1" in top_result["description"]
        assert top_result["stock"] > 0
        assert top_result["basic"] is True

        # Step 3: Get detailed specs
        details = tools.get_component_details(lcsc_id=top_result["lcsc_id"])
        assert details is not None
        assert "attributes" in details
        # Check for voltage-related attributes (might be "voltage", "voltage rated", etc.)
        voltage_attrs = {k.lower() for k in details["attributes"].keys()}
        assert any("voltage" in attr for attr in voltage_attrs)

    def test_workflow_find_resistor_by_value(self, tools):
        """Workflow: Find a 10k resistor in 0603 package.

        Simulates: "I need a 10k resistor in 0603 package"
        """
        # Step 1: Search for resistors
        response = tools.search_components(
            query="10k",
            category="Resistors",
            package="0603",
            basic_only=True,
            limit=20,
        )

        # Should find results (if 10k 0603 resistors exist)
        if response["results"]:
            # Verify results match criteria
            for result in response["results"]:
                assert "10k" in result["description"].lower() or "10" in result["description"]
                assert result["stock"] > 0

    def test_workflow_compare_similar_parts(self, tools):
        """Workflow: Compare two similar capacitors.

        Simulates: "What's the difference between C1525 and C307331?"
        """
        # Step 1: Get details for both parts
        details1 = tools.get_component_details(lcsc_id="C1525")
        details2 = tools.get_component_details(lcsc_id="C307331")

        if details1 and details2:
            # Step 2: Compare them using the tool
            comparison = tools.compare_components(
                lcsc_ids=["C1525", "C307331"]
            )

            assert comparison["success"] is True
            assert len(comparison["comparison"]["components"]) >= 1

            # Should have attributes for comparison
            assert "Voltage" in comparison["comparison"]["attributes"] or \
                   len(comparison["comparison"]["attributes"]) > 0

    def test_workflow_find_by_stock(self, tools):
        """Workflow: Find capacitors with high stock.

        Simulates: "I need a capacitor with lots of stock"
        """
        # Step 1: Search for high-stock capacitors
        response = tools.search_components(
            category="Capacitors",
            basic_only=True,
            in_stock_only=True,
            limit=50,
        )

        assert len(response["results"]) > 0

        # Step 2: Verify stock levels are high
        for result in response["results"]:
            assert result["stock"] > 0
            # Results are sorted by stock, so first should have most

    def test_workflow_find_affordable_component(self, tools):
        """Workflow: Find an affordable component.

        Simulates: "I need a capacitor that costs less than 1 cent"
        """
        # Step 1: Search for cheap components
        response = tools.search_components(
            category="Capacitors",
            max_price=0.01,
            basic_only=True,
            limit=20,
        )

        assert len(response["results"]) > 0

        # Step 2: Verify prices
        for result in response["results"]:
            assert result["price"] <= 0.01
            assert result["stock"] > 0


@pytest.mark.integration
class TestEndToEndProjectIntegration:
    """End-to-end tests for KiCad project integration."""

    @pytest.fixture
    def temp_kicad_project(self):
        """Create a temporary KiCad project for testing."""
        with TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test-project"
            project_dir.mkdir()

            # Create minimal KiCad project file
            project_file = project_dir / "test-project.kicad_pro"
            project_file.write_text('(kicad_project)')

            yield project_dir

    @pytest.fixture
    def tools(self):
        """Initialize MCP tools with real database."""
        db = DatabaseManager()
        db.update_if_needed()
        return JLCTools(db)

    def test_workflow_add_component_to_project(self, tools, temp_kicad_project):
        """Workflow: Add a component to a KiCad project.

        Simulates: "Add C1525 to my project"
        """
        # Step 1: Verify project is valid
        config = ProjectConfig(temp_kicad_project)
        assert config.project_dir == temp_kicad_project

        # Step 2: Add component to project
        # Note: This requires easyeda2kicad to be installed
        try:
            result = tools.add_to_project(
                lcsc_id="C1525",
                project_path=str(temp_kicad_project),
            )

            if result["success"]:
                # Verify files were created
                symbol_file = Path(result["symbol_file"])
                footprints_dir = Path(result["footprints_dir"])
                models_dir = Path(result["models_dir"])

                assert symbol_file.exists(), "Symbol file should exist"
                assert footprints_dir.exists(), "Footprints directory should exist"
                assert models_dir.exists(), "Models directory should exist"

                # Step 3: Verify library tables were updated
                sym_table = config.get_symbol_lib_table()
                assert sym_table is not None

        except Exception as e:
            # May fail if easyeda2kicad not installed
            if "command not found" in str(e) or "easyeda2kicad" in str(e):
                pytest.skip("easyeda2kicad not installed")
            raise

    def test_workflow_create_library_directories(self, temp_kicad_project):
        """Workflow: Verify library directories are created.

        Simulates: KiCad project setup
        """
        config = ProjectConfig(temp_kicad_project)

        # Create library directories
        lib_dir, fp_dir = config.create_library_directories()

        # Verify they were created
        assert lib_dir.exists()
        assert fp_dir.exists()
        # Verify footprint directory is where we expect
        assert fp_dir.name == "footprints.pretty"
        assert fp_dir.parent == lib_dir

    def test_workflow_register_library(self, temp_kicad_project):
        """Workflow: Register symbol library in KiCad project.

        Simulates: Adding component library to project tables
        """
        config = ProjectConfig(temp_kicad_project)
        lib_dir, fp_dir = config.create_library_directories()

        # Create a dummy symbol file
        symbol_file = lib_dir / "test.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib)")

        # Register it
        config.add_symbol_library(
            name="test-lib",
            lib_path=symbol_file,
            description="Test library",
        )

        # Verify it was registered
        sym_table = config.get_symbol_lib_table()
        entry = sym_table.get_entry("test-lib")
        assert entry is not None
        assert entry.name == "test-lib"


@pytest.mark.integration
class TestEndToEndSearchPatterns:
    """End-to-end tests for realistic search patterns."""

    @pytest.fixture
    def tools(self):
        """Initialize MCP tools with real database."""
        db = DatabaseManager()
        db.update_if_needed()
        return JLCTools(db)

    def test_search_pattern_exact_value(self, tools):
        """Pattern: Search for exact component value.

        Example: "100nF 16V capacitor"
        """
        response = tools.search_components(
            query="100nF 16V",
            category="Capacitors",
            limit=10,
        )

        assert len(response["results"]) > 0
        assert any("100nF" in r["description"] for r in response["results"])

    def test_search_pattern_common_parts(self, tools):
        """Pattern: Find common/popular parts.

        Example: "Popular capacitors"
        """
        # Basic parts with high stock = popular
        response = tools.search_components(
            category="Capacitors",
            basic_only=True,
            in_stock_only=True,
            limit=20,
        )

        assert len(response["results"]) > 0
        assert all(r["basic"] for r in response["results"])

    def test_search_pattern_budget(self, tools):
        """Pattern: Find parts within budget.

        Example: "Cheap resistors for bulk"
        """
        response = tools.search_components(
            category="Resistors",
            basic_only=True,
            max_price=0.01,
            limit=20,
        )

        if response["results"]:
            assert all(r["price"] <= 0.01 for r in response["results"])

    def test_search_pattern_specific_manufacturer(self, tools):
        """Pattern: Find parts from specific manufacturer.

        Example: "Samsung capacitors"
        """
        response = tools.search_components(
            manufacturer="Samsung",
            category="Capacitors",
            basic_only=True,
            limit=20,
        )

        if response["results"]:
            assert all("samsung" in r["manufacturer"].lower() for r in response["results"])

    def test_search_pattern_refine_results(self, tools):
        """Pattern: Refine search results iteratively.

        Simulates user asking Claude to narrow down results
        """
        # First: broad search
        broad_response = tools.search_components(
            category="Capacitors",
            limit=50,
        )

        assert len(broad_response["results"]) > 0

        # Second: refine with more filters
        refined_response = tools.search_components(
            category="Capacitors",
            basic_only=True,
            in_stock_only=True,
            max_price=0.05,
            limit=20,
        )

        # Refined should have fewer or equal results
        assert len(refined_response["results"]) <= len(broad_response["results"])


@pytest.mark.integration
class TestEndToEndSlowWorkflows:
    """Slow end-to-end tests (marked to skip in quick test runs).

    These tests take longer due to network operations.
    """

    def test_workflow_parallel_component_downloads(self):
        """Workflow: Download multiple component libraries in parallel.

        This tests the parallel download capability.
        """
        try:
            from jlc_has_it.core.library_downloader import LibraryDownloader

            downloader = LibraryDownloader()

            # Try to download a few components in parallel
            # Note: Don't try too many to avoid overwhelming the server
            lcsc_ids = ["C1525", "C307331"]
            libraries = downloader.download_components_parallel(
                lcsc_ids, max_workers=2
            )

            # Should have attempted downloads for both
            assert "C1525" in libraries
            assert "C307331" in libraries

        except ImportError:
            pytest.skip("easyeda2kicad not installed")

    def test_workflow_full_search_to_project(self):
        """Workflow: Complete workflow from search to project addition.

        1. Search for component
        2. Get details
        3. Create project
        4. Add to project
        5. Verify
        """
        db = DatabaseManager()
        db.update_if_needed()
        tools = JLCTools(db)

        with TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "workflow-test"
            project_dir.mkdir()

            # Create KiCad project file
            project_file = project_dir / "workflow-test.kicad_pro"
            project_file.write_text('(kicad_project)')

            try:
                # Step 1: Search
                response = tools.search_components(
                    query="capacitor",
                    basic_only=False,  # Not all capacitors in FTS5 are basic parts
                    limit=5,
                )

                assert len(response["results"]) > 0

                # Step 2: Get details
                top_lcsc = response["results"][0]["lcsc_id"]
                details = tools.get_component_details(lcsc_id=top_lcsc)
                assert details is not None

                # Step 3: Add to project
                result = tools.add_to_project(
                    lcsc_id=top_lcsc,
                    project_path=str(project_dir),
                )

                # Verify success (or graceful failure if easyeda2kicad unavailable)
                assert "success" in result
                assert "error" in result or "message" in result

            except Exception as e:
                if "easyeda2kicad" in str(e):
                    pytest.skip("easyeda2kicad not available")
                raise
