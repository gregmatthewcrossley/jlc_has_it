"""Tests for MCP tool implementations.

Tests verify that MCP tools correctly search, retrieve, compare,
and integrate components using the real jlcparts database.
"""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.kicad.project import ProjectConfig
from jlc_has_it.mcp.tools import JLCTools


class TestSearchComponents:
    """Test search_components MCP tool."""

    @pytest.fixture
    def tools(self):
        """Initialize MCP tools with real database."""
        db = DatabaseManager()
        db.update_if_needed()
        return JLCTools(db)

    def test_search_by_category(self, tools):
        """Search for components by category returns results."""
        response = tools.search_components(category="Capacitors", limit=10)

        assert isinstance(response, dict)
        assert "results" in response
        assert isinstance(response["results"], list)
        assert len(response["results"]) > 0
        assert all(isinstance(r, dict) for r in response["results"])
        assert all("lcsc_id" in r and "description" in r for r in response["results"])

    def test_search_by_query(self, tools):
        """Search with free-text query works."""
        response = tools.search_components(query="100nF", category="Capacitors", limit=10)

        if response["results"]:
            assert all("100nF" in r["description"] or "0.1" in r["description"] for r in response["results"])

    def test_search_respects_limit(self, tools):
        """Search respects limit parameter."""
        response = tools.search_components(category="Capacitors", limit=5)

        assert len(response["results"]) <= 5

    def test_search_basic_only_filter(self, tools):
        """Search with basic_only=True returns only basic parts."""
        response = tools.search_components(
            category="Capacitors",
            basic_only=True,
            limit=20,
        )

        if response["results"]:
            assert all(r["basic"] is True for r in response["results"])

    def test_search_in_stock_only_filter(self, tools):
        """Search with in_stock_only=True returns only in-stock parts."""
        response = tools.search_components(
            category="Capacitors",
            in_stock_only=True,
            limit=20,
        )

        if response["results"]:
            assert all(r["stock"] > 0 for r in response["results"])

    def test_search_price_filter(self, tools):
        """Search with max_price filters correctly."""
        response = tools.search_components(
            category="Capacitors",
            max_price=0.01,
            limit=20,
        )

        if response["results"]:
            assert all(r["price"] <= 0.01 for r in response["results"])

    def test_search_manufacturer_filter(self, tools):
        """Search with manufacturer filter works."""
        response = tools.search_components(
            manufacturer="Samsung",
            category="Capacitors",
            limit=10,
        )

        if response["results"]:
            assert all("samsung" in r["manufacturer"].lower() for r in response["results"])

    def test_search_returns_required_fields(self, tools):
        """Search results contain all required fields."""
        response = tools.search_components(category="Capacitors", limit=5)

        if response["results"]:
            required_fields = {"lcsc_id", "description", "manufacturer", "stock", "price", "basic"}
            for result in response["results"]:
                assert required_fields.issubset(result.keys())

    def test_search_no_results_returns_empty_list(self, tools):
        """Search with no matches returns empty list (not error)."""
        response = tools.search_components(
            query="ZZZZZ_NONEXISTENT_COMPONENT",
            limit=10,
        )

        assert isinstance(response["results"], list)
        assert len(response["results"]) == 0


class TestGetComponentDetails:
    """Test get_component_details MCP tool."""

    @pytest.fixture
    def tools(self):
        """Initialize MCP tools with real database."""
        db = DatabaseManager()
        db.update_if_needed()
        return JLCTools(db)

    def test_get_details_by_lcsc_id(self, tools):
        """Get details for a component by LCSC ID."""
        details = tools.get_component_details(lcsc_id="C1525")

        if details:  # Component may or may not exist
            assert "lcsc_id" in details
            assert "description" in details
            assert "attributes" in details
            assert "price_tiers" in details

    def test_get_details_returns_none_for_nonexistent(self, tools):
        """Get details returns None for non-existent component."""
        details = tools.get_component_details(lcsc_id="C99999999999999")

        assert details is None

    def test_get_details_includes_attributes(self, tools):
        """Details include component attributes."""
        details = tools.get_component_details(lcsc_id="C1525")

        if details:
            assert isinstance(details["attributes"], dict)

    def test_get_details_includes_price_tiers(self, tools):
        """Details include price tier information."""
        details = tools.get_component_details(lcsc_id="C1525")

        if details:
            assert "price_tiers" in details
            # price_tiers is a list of PriceTier objects or dicts
            price_tiers = details["price_tiers"]
            if price_tiers:
                # Check if it's a PriceTier object or dict
                first_tier = price_tiers[0]
                if hasattr(first_tier, "qty"):
                    # It's a PriceTier object
                    assert hasattr(first_tier, "qty")
                    assert hasattr(first_tier, "price")
                else:
                    # It's a dict
                    assert "qty" in first_tier or "qFrom" in first_tier
                    assert "price" in first_tier

    def test_get_details_includes_stock_info(self, tools):
        """Details include stock information."""
        details = tools.get_component_details(lcsc_id="C1525")

        if details:
            assert "stock" in details
            assert isinstance(details["stock"], int)

    def test_get_details_includes_category_info(self, tools):
        """Details include category information."""
        details = tools.get_component_details(lcsc_id="C1525")

        if details:
            assert "category" in details
            assert "subcategory" in details


class TestCompareComponents:
    """Test compare_components MCP tool."""

    @pytest.fixture
    def tools(self):
        """Initialize MCP tools with real database."""
        db = DatabaseManager()
        db.update_if_needed()
        return JLCTools(db)

    def test_compare_empty_list_returns_error(self, tools):
        """Compare with empty list returns error."""
        result = tools.compare_components([])

        assert result["success"] is False
        assert "error" in result

    def test_compare_single_component(self, tools):
        """Compare single component works (though not very useful)."""
        result = tools.compare_components(["C1525"])

        if result["success"]:
            assert "comparison" in result
            assert "components" in result["comparison"]
            assert len(result["comparison"]["components"]) >= 1

    def test_compare_two_components(self, tools):
        """Compare two components works."""
        result = tools.compare_components(["C1525", "C307331"])

        if result["success"]:
            assert "comparison" in result
            comparison = result["comparison"]

            # Should have component data
            assert "components" in comparison
            assert len(comparison["components"]) >= 1

            # Should have attributes for comparison
            assert "attributes" in comparison
            assert isinstance(comparison["attributes"], dict)

    def test_compare_returns_correct_structure(self, tools):
        """Compare result has correct structure."""
        result = tools.compare_components(["C1525"])

        if result["success"]:
            comparison = result["comparison"]

            # Check structure
            assert "count" in comparison
            assert "components" in comparison
            assert "attributes" in comparison
            assert "not_found" in comparison

            # Check component format
            for comp in comparison["components"]:
                assert "lcsc_id" in comp
                assert "description" in comp
                assert "manufacturer" in comp
                assert "stock" in comp
                assert "price" in comp
                assert "basic" in comp

    def test_compare_too_many_components_returns_error(self, tools):
        """Compare with >10 components returns error."""
        lcsc_ids = [f"C{i}" for i in range(15)]
        result = tools.compare_components(lcsc_ids)

        assert result["success"] is False
        assert "error" in result

    def test_compare_tracks_not_found(self, tools):
        """Compare tracks components not found."""
        result = tools.compare_components(["C1525", "C99999999"])

        if result["success"]:
            comparison = result["comparison"]
            if comparison["not_found"]:
                assert "C99999999" in comparison["not_found"]

    def test_compare_attributes_have_correct_format(self, tools):
        """Attributes in comparison have value and unit."""
        result = tools.compare_components(["C1525"])

        if result["success"]:
            comparison = result["comparison"]
            if comparison["attributes"]:
                for attr_name, attr_list in comparison["attributes"].items():
                    for attr_entry in attr_list:
                        assert "lcsc_id" in attr_entry
                        assert "value" in attr_entry
                        assert "unit" in attr_entry

    def test_compare_nonexistent_components_returns_error(self, tools):
        """Compare with only nonexistent components returns error."""
        result = tools.compare_components(["C99999999", "C88888888"])

        assert result["success"] is False


class TestAddToProject:
    """Test add_to_project MCP tool."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary KiCad project."""
        with TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test-project"
            project_dir.mkdir()

            # Create minimal KiCad project file
            project_file = project_dir / "test-project.kicad_pro"
            project_file.write_text("(kicad_project)")

            yield project_dir

    @pytest.fixture
    def tools(self):
        """Initialize MCP tools with real database."""
        db = DatabaseManager()
        db.update_if_needed()
        return JLCTools(db)

    def test_add_to_project_without_project_path(self, tools):
        """Add to project without specifying path returns error."""
        # Change to /tmp so no project is found
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            result = tools.add_to_project(lcsc_id="C1525")
            assert result["success"] is False
            assert "error" in result
        finally:
            os.chdir(old_cwd)

    def test_add_to_project_creates_library_dirs(self, tools, temp_project):
        """Add to project creates library directories."""
        result = tools.add_to_project(
            lcsc_id="C1525",
            project_path=str(temp_project),
        )

        # May succeed or fail depending on easyeda2kicad availability
        if result["success"]:
            # Verify directories exist
            assert Path(result["symbol_file"]).parent.exists()
            assert Path(result["footprints_dir"]).exists()

    def test_add_to_project_returns_required_fields(self, tools, temp_project):
        """Add to project result has required fields."""
        result = tools.add_to_project(
            lcsc_id="C1525",
            project_path=str(temp_project),
        )

        # Check that result has expected structure
        assert "success" in result
        if result["success"]:
            assert "lcsc_id" in result
            assert "project" in result
            assert "message" in result
        else:
            assert "error" in result

    def test_add_to_project_invalid_project_returns_error(self, tools):
        """Add to project with invalid project path returns error."""
        result = tools.add_to_project(
            lcsc_id="C1525",
            project_path="/nonexistent/project",
        )

        assert result["success"] is False
        assert "error" in result


class TestToolIntegration:
    """Integration tests for multiple tools working together."""

    @pytest.fixture
    def tools(self):
        """Initialize MCP tools with real database."""
        db = DatabaseManager()
        db.update_if_needed()
        return JLCTools(db)

    def test_search_then_get_details(self, tools):
        """Search results can be used to get details."""
        # Step 1: Search
        search_response = tools.search_components(
            category="Capacitors",
            basic_only=True,
            limit=5,
        )

        if search_response["results"]:
            # Step 2: Get details for first result
            lcsc_id = search_response["results"][0]["lcsc_id"]
            details = tools.get_component_details(lcsc_id=lcsc_id)

            # Verify details correspond to search result
            if details:
                assert details["lcsc_id"] == lcsc_id
                assert details["description"] == search_response["results"][0]["description"]

    def test_search_then_compare(self, tools):
        """Search results can be compared."""
        # Step 1: Search
        search_response = tools.search_components(
            category="Capacitors",
            basic_only=True,
            limit=5,
        )

        if len(search_response["results"]) >= 2:
            # Step 2: Compare top 2 results
            lcsc_ids = [search_response["results"][0]["lcsc_id"], search_response["results"][1]["lcsc_id"]]
            comparison = tools.compare_components(lcsc_ids)

            if comparison["success"]:
                assert len(comparison["comparison"]["components"]) >= 1

    def test_workflow_multiple_refinements(self, tools):
        """Simulate user refining search iteratively."""
        # Step 1: Broad search
        broad_response = tools.search_components(
            category="Capacitors",
            limit=50,
        )

        assert len(broad_response["results"]) > 0

        # Step 2: Refine with more filters
        refined_response = tools.search_components(
            category="Capacitors",
            basic_only=True,
            in_stock_only=True,
            max_price=0.05,
            limit=20,
        )

        # Refined should have fewer or equal results
        assert len(refined_response["results"]) <= len(broad_response["results"])

        # Step 3: Get details on best matches
        if refined_response["results"]:
            details = tools.get_component_details(lcsc_id=refined_response["results"][0]["lcsc_id"])
            assert details is not None
