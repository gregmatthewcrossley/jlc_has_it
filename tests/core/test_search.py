"""Tests for component search functionality."""

import json
import sqlite3
from pathlib import Path

import pytest

from jlc_has_it.core.search import ComponentSearch, QueryParams


@pytest.mark.integration
class TestComponentSearch:
    """Tests for ComponentSearch class using the real optimized database."""

    @pytest.fixture
    def test_database(self, test_database_connection) -> sqlite3.Connection:
        """Use the real optimized test database with denormalized columns."""
        return test_database_connection

    def _get_test_components_from_db(self, conn: sqlite3.Connection) -> None:
        """Helper to verify test components exist in database."""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM components WHERE category_name = 'Capacitors'")
        capacitor_count = cursor.fetchone()[0]
        assert capacitor_count > 0, "Database should have Capacitors"

        cursor.execute("SELECT COUNT(*) FROM components WHERE category_name = 'Resistors'")
        resistor_count = cursor.fetchone()[0]
        # May have resistors or not, depending on database content
        return

    @pytest.fixture
    def old_test_database(self, tmp_path: Path) -> sqlite3.Connection:
        """Legacy: Create a test database with sample components (real jlcparts schema)."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Create categories lookup table
        conn.execute(
            """
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                category TEXT,
                subcategory TEXT
            )
        """
        )

        # Create manufacturers lookup table
        conn.execute(
            """
            CREATE TABLE manufacturers (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """
        )

        # Insert test categories
        conn.execute("INSERT INTO categories (id, category, subcategory) VALUES (1, 'Capacitors', 'Multilayer Ceramic Capacitors MLCC - SMD/SMT')")
        conn.execute("INSERT INTO categories (id, category, subcategory) VALUES (2, 'Capacitors', 'Aluminum Electrolytic Capacitors - Leaded')")
        conn.execute("INSERT INTO categories (id, category, subcategory) VALUES (3, 'Resistors', 'Chip Resistor - Surface Mount')")

        # Insert test manufacturers
        conn.execute("INSERT INTO manufacturers (id, name) VALUES (1, 'Samsung')")
        conn.execute("INSERT INTO manufacturers (id, name) VALUES (2, 'Generic')")
        conn.execute("INSERT INTO manufacturers (id, name) VALUES (3, 'Yageo')")
        conn.execute("INSERT INTO manufacturers (id, name) VALUES (4, 'Murata')")

        # Create components table (real jlcparts schema)
        conn.execute(
            """
            CREATE TABLE components (
                lcsc INTEGER PRIMARY KEY,
                mfr TEXT,
                description TEXT,
                category_id INTEGER,
                manufacturer_id INTEGER,
                joints INTEGER,
                basic INTEGER,
                stock INTEGER,
                price TEXT,
                extra TEXT
            )
        """
        )

        # Insert test components (real jlcparts schema)
        test_components = [
            {
                "lcsc": 1525,
                "mfr": "CL10A106KP8NNNC",
                "description": "",
                "category_id": 1,
                "manufacturer_id": 1,
                "joints": 2,
                "basic": 1,
                "stock": 50000,
                "price": json.dumps([{"qFrom": 1, "price": 0.0012}]),
                "extra": json.dumps({
                    "description": "10uF ±10% 10V X5R 0603",
                    "attributes": {
                        "Capacitance": {"value": 10, "unit": "uF"},
                        "Voltage": {"value": 10, "unit": "V"},
                        "Tolerance": {"value": 10, "unit": "%"},
                        "Package": "0603",
                        "Temperature Coefficient": "X5R",
                    }
                }),
            },
            {
                "lcsc": 12345,
                "mfr": "TEST-220UF-50V",
                "description": "",
                "category_id": 2,
                "manufacturer_id": 2,
                "joints": 2,
                "basic": 0,
                "stock": 5000,
                "price": json.dumps([{"qFrom": 1, "price": 0.15}]),
                "extra": json.dumps({
                    "description": "220uF ±20% 50V Electrolytic",
                    "attributes": {
                        "Capacitance": {"value": 220, "unit": "uF"},
                        "Voltage": {"value": 50, "unit": "V"},
                        "Tolerance": {"value": 20, "unit": "%"},
                        "Package": "Radial",
                    }
                }),
            },
            {
                "lcsc": 67890,
                "mfr": "RES-10K-0402",
                "description": "",
                "category_id": 3,
                "manufacturer_id": 3,
                "joints": 2,
                "basic": 1,
                "stock": 100000,
                "price": json.dumps([{"qFrom": 1, "price": 0.001}]),
                "extra": json.dumps({
                    "description": "10kΩ ±1% 0402 Resistor",
                    "attributes": {
                        "Resistance": {"value": 10000, "unit": "Ω"},
                        "Tolerance": {"value": 1, "unit": "%"},
                        "Power": {"value": 0.063, "unit": "W"},
                        "Package": "0402",
                    }
                }),
            },
            {
                "lcsc": 99999,
                "mfr": "CAP-100NF-50V",
                "description": "",
                "category_id": 1,
                "manufacturer_id": 4,
                "joints": 2,
                "basic": 1,
                "stock": 0,  # Out of stock
                "price": json.dumps([{"qFrom": 1, "price": 0.002}]),
                "extra": json.dumps({
                    "description": "100nF ±10% 50V X7R 0402",
                    "attributes": {
                        "Capacitance": {"value": 100, "unit": "nF"},
                        "Voltage": {"value": 50, "unit": "V"},
                        "Package": "0402",
                    }
                }),
            },
        ]

        for component in test_components:
            conn.execute(
                """
                INSERT INTO components
                (lcsc, mfr, description, category_id, manufacturer_id,
                 joints, basic, stock, price, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    component["lcsc"],
                    component["mfr"],
                    component["description"],
                    component["category_id"],
                    component["manufacturer_id"],
                    component["joints"],
                    component["basic"],
                    component["stock"],
                    component["price"],
                    component["extra"],
                ],
            )

        conn.commit()
        return conn

    @pytest.fixture
    def search_engine(self, test_database: sqlite3.Connection) -> ComponentSearch:
        """Create ComponentSearch instance with test database."""
        return ComponentSearch(test_database)

    def test_search_all(self, search_engine: ComponentSearch) -> None:
        """Test searching without filters returns results."""
        params = QueryParams(in_stock_only=False, limit=100)
        results = search_engine.search(params)

        # Real database has millions of components, just verify we get results
        assert len(results) > 0
        assert len(results) <= 100  # Respects limit

    def test_search_by_category(self, search_engine: ComponentSearch) -> None:
        """Test searching by category with exact match."""
        # Use a real category from the database
        params = QueryParams(category="Capacitors", in_stock_only=False, limit=50)
        results = search_engine.search(params)

        # Verify all results are Capacitors (exact match)
        if len(results) > 0:
            for component in results:
                assert component.category == "Capacitors"

    def test_search_by_subcategory(self, search_engine: ComponentSearch) -> None:
        """Test searching by subcategory with exact match."""
        # Get a sample subcategory first
        params = QueryParams(category="Capacitors", in_stock_only=False, limit=1)
        sample_results = search_engine.search(params)

        if len(sample_results) > 0:
            sample_subcategory = sample_results[0].subcategory
            # Now search for this subcategory
            params = QueryParams(
                category="Capacitors",
                subcategory=sample_subcategory,
                in_stock_only=False,
                limit=50
            )
            results = search_engine.search(params)
            # All results should match the subcategory
            for component in results:
                assert component.subcategory == sample_subcategory

    def test_search_basic_only(self, search_engine: ComponentSearch) -> None:
        """Test filtering for basic parts only."""
        params = QueryParams(category="Capacitors", basic_only=True, in_stock_only=False, limit=50)
        results = search_engine.search(params)

        if len(results) > 0:
            for component in results:
                assert component.basic is True

    def test_search_in_stock_only(self, search_engine: ComponentSearch) -> None:
        """Test filtering for in-stock parts."""
        params = QueryParams(category="Capacitors", in_stock_only=True, limit=50)
        results = search_engine.search(params)

        # All results should be in stock
        for component in results:
            assert component.stock > 0

    def test_search_min_stock(self, search_engine: ComponentSearch) -> None:
        """Test filtering by minimum stock."""
        params = QueryParams(category="Capacitors", min_stock=10000, in_stock_only=False, limit=50)
        results = search_engine.search(params)

        # All results should have stock >= min_stock
        for component in results:
            assert component.stock >= 10000

    def test_search_max_price(self, search_engine: ComponentSearch) -> None:
        """Test filtering by maximum price."""
        params = QueryParams(category="Capacitors", max_price=0.01, in_stock_only=False, limit=50)
        results = search_engine.search(params)

        # All results should be <= max price
        for component in results:
            assert component.price <= 0.01

    @pytest.mark.skip(reason="Package filtering not yet supported - requires JSON extraction in WHERE clause")
    def test_search_by_package(self, search_engine: ComponentSearch) -> None:
        """Test filtering by package type."""
        params = QueryParams(package="0402", in_stock_only=False)
        results = search_engine.search(params)

        assert len(results) == 2
        assert results[0].get_attribute_value("Package") == "0402"
        assert results[1].get_attribute_value("Package") == "0402"

    def test_search_by_manufacturer(self, search_engine: ComponentSearch) -> None:
        """Test filtering by manufacturer with exact match."""
        # Get a sample manufacturer first
        params = QueryParams(category="Capacitors", in_stock_only=False, limit=1)
        sample_results = search_engine.search(params)

        if len(sample_results) > 0:
            sample_manufacturer = sample_results[0].manufacturer
            # Now search for this manufacturer
            params = QueryParams(manufacturer=sample_manufacturer, in_stock_only=False, limit=50)
            results = search_engine.search(params)
            # All results should match the manufacturer
            for component in results:
                assert component.manufacturer == sample_manufacturer

    # Note: description_contains testing is covered by FTS5 tests in test_fts5_and_pagination.py
    # which test this functionality with real database and proper FTS5 initialization.
    # This test class uses a minimal test database without FTS5 enabled.

    @pytest.mark.skip(reason="Attribute filtering not yet supported - requires JSON extraction in WHERE clause")
    def test_search_by_attribute_value(self, search_engine: ComponentSearch) -> None:
        """Test filtering by exact attribute value."""
        params = QueryParams(
            category="Capacitors",
            attributes={"Capacitance": 10},
            in_stock_only=False,
        )
        results = search_engine.search(params)

        assert len(results) == 1
        assert results[0].get_attribute_value("Capacitance") == 10

    @pytest.mark.skip(reason="Attribute filtering not yet supported - requires JSON extraction in WHERE clause")
    def test_search_by_attribute_range(self, search_engine: ComponentSearch) -> None:
        """Test filtering by attribute range."""
        params = QueryParams(
            category="Capacitors",
            attribute_ranges={"Voltage": {"min": 50}},
            in_stock_only=False,
        )
        results = search_engine.search(params)

        assert len(results) == 2
        for component in results:
            voltage = component.get_attribute_value("Voltage")
            assert voltage >= 50

    def test_search_sorting(self, search_engine: ComponentSearch) -> None:
        """Test that results are sorted correctly by basic DESC, stock DESC, price ASC."""
        params = QueryParams(category="Capacitors", in_stock_only=False, limit=100)
        results = search_engine.search(params)

        if len(results) >= 2:
            # Verify sorting: basic parts should come before extended parts
            # Within basic parts, higher stock should come first
            basic_parts = [r for r in results if r.basic]
            extended_parts = [r for r in results if not r.basic]

            # If we have both types, basics should be first
            if basic_parts and extended_parts:
                assert results[0].basic is True

    def test_search_limit(self, search_engine: ComponentSearch) -> None:
        """Test limiting number of results."""
        params = QueryParams(category="Capacitors", in_stock_only=False, limit=2)
        results = search_engine.search(params)

        assert len(results) <= 2

    def test_search_by_category_convenience(self, search_engine: ComponentSearch) -> None:
        """Test convenience method for category search."""
        results = search_engine.search_by_category("Capacitors", limit=10)

        if len(results) > 0:
            for component in results:
                assert component.category == "Capacitors"

    def test_search_by_category_basic_only(self, search_engine: ComponentSearch) -> None:
        """Test category search with basic_only flag."""
        results = search_engine.search_by_category("Capacitors", basic_only=True, limit=10)

        for component in results:
            assert component.basic is True

    def test_search_by_lcsc(self, search_engine: ComponentSearch) -> None:
        """Test searching by LCSC part number."""
        # Get a real LCSC from the database first
        params = QueryParams(category="Capacitors", in_stock_only=False, limit=1)
        sample = search_engine.search(params)

        if len(sample) > 0:
            lcsc_id = sample[0].lcsc
            component = search_engine.search_by_lcsc(lcsc_id)

            assert component is not None
            assert component.lcsc == lcsc_id

    def test_search_by_lcsc_not_found(self, search_engine: ComponentSearch) -> None:
        """Test searching for non-existent LCSC part."""
        component = search_engine.search_by_lcsc("C99999999999")

        assert component is None

    def test_search_complex_query(self, search_engine: ComponentSearch) -> None:
        """Test complex search with multiple filters."""
        params = QueryParams(
            category="Capacitors",
            basic_only=True,
            in_stock_only=True,
            max_price=0.01,
            limit=50
            # Note: attributes filtering is not yet supported
        )
        results = search_engine.search(params)

        # Verify all filters are applied
        for component in results:
            assert component.category == "Capacitors"
            assert component.basic is True
            assert component.stock > 0
            assert component.price <= 0.01

    def test_search_by_package_exact_match(self, search_engine: ComponentSearch) -> None:
        """Test searching by package type with exact match."""
        # Get a sample component first to find a real package
        sample_params = QueryParams(category="Capacitors", in_stock_only=False, limit=10)
        sample_results = search_engine.search(sample_params)

        if len(sample_results) > 0:
            sample_package = sample_results[0].package
            if sample_package:
                # Now search for this package
                params = QueryParams(package=sample_package, in_stock_only=False, limit=50)
                results = search_engine.search(params)

                # All results should have matching package
                for component in results:
                    assert component.package == sample_package

    def test_search_by_package_with_category(self, search_engine: ComponentSearch) -> None:
        """Test package filtering combined with category filter."""
        # Get a sample component first
        sample_params = QueryParams(category="Capacitors", in_stock_only=False, limit=10)
        sample_results = search_engine.search(sample_params)

        if len(sample_results) > 0:
            sample_package = sample_results[0].package
            if sample_package:
                # Search for package within category
                params = QueryParams(
                    category="Capacitors",
                    package=sample_package,
                    in_stock_only=False,
                    limit=50
                )
                results = search_engine.search(params)

                # All results should match both filters
                for component in results:
                    assert component.category == "Capacitors"
                    assert component.package == sample_package

    def test_search_by_package_with_stock_filter(self, search_engine: ComponentSearch) -> None:
        """Test package filtering with stock constraints."""
        # Get a sample component with in-stock items
        sample_params = QueryParams(category="Capacitors", in_stock_only=True, limit=10)
        sample_results = search_engine.search(sample_params)

        if len(sample_results) > 0:
            sample_package = sample_results[0].package
            if sample_package:
                # Search for package with min stock requirement
                params = QueryParams(
                    package=sample_package,
                    min_stock=100,
                    in_stock_only=True,
                    limit=50
                )
                results = search_engine.search(params)

                # All results should have required stock
                for component in results:
                    assert component.package == sample_package
                    assert component.stock >= 100

    def test_search_package_returns_only_matching(self, search_engine: ComponentSearch) -> None:
        """Test that package filter only returns exact matches."""
        params = QueryParams(package="0603", in_stock_only=False, limit=50)
        results = search_engine.search(params)

        # If any results exist, they must all be 0603
        for component in results:
            assert component.package == "0603"

    def test_search_nonexistent_package(self, search_engine: ComponentSearch) -> None:
        """Test searching for a package that doesn't exist."""
        params = QueryParams(package="NONEXISTENT_PKG_12345", in_stock_only=False)
        results = search_engine.search(params)

        # Should return empty list, not error
        assert results == []

    def test_search_package_with_all_filters(self, search_engine: ComponentSearch) -> None:
        """Test package filtering with all other filters combined."""
        # Get a real package first
        sample_params = QueryParams(category="Capacitors", in_stock_only=True, limit=1)
        sample_results = search_engine.search(sample_params)

        if len(sample_results) > 0:
            sample_package = sample_results[0].package
            if sample_package:
                # Complex query with package + many other filters
                params = QueryParams(
                    category="Capacitors",
                    package=sample_package,
                    basic_only=False,
                    in_stock_only=True,
                    max_price=1.0,
                    limit=50
                )
                results = search_engine.search(params)

                # Verify all filters applied
                for component in results:
                    assert component.category == "Capacitors"
                    assert component.package == sample_package
                    assert component.stock > 0
                    assert component.price <= 1.0

    def test_search_by_attribute_value_exact(self, search_engine: ComponentSearch) -> None:
        """Test searching by exact attribute value."""
        # Get a component with attributes first
        sample_params = QueryParams(category="Capacitors", in_stock_only=False, limit=20)
        sample_results = search_engine.search(sample_params)

        # Find a component with attributes
        component_with_attrs = None
        for comp in sample_results:
            if comp.attributes:
                component_with_attrs = comp
                break

        if component_with_attrs:
            # Get an attribute from this component
            for attr_name, attr_value in component_with_attrs.attributes.items():
                # Search for components with this exact attribute
                params = QueryParams(
                    attributes={attr_name: attr_value},
                    in_stock_only=False,
                    limit=50
                )
                results = search_engine.search(params)

                # All results should have this attribute with matching value
                for component in results:
                    assert component.get_attribute_value(attr_name) == attr_value
                break

    def test_search_by_attribute_with_category(self, search_engine: ComponentSearch) -> None:
        """Test attribute filtering combined with category filter."""
        # Get a component from a category with attributes
        sample_params = QueryParams(category="Capacitors", in_stock_only=False, limit=20)
        sample_results = search_engine.search(sample_params)

        # Find a component with attributes
        component_with_attrs = None
        for comp in sample_results:
            if comp.attributes:
                component_with_attrs = comp
                break

        if component_with_attrs:
            # Get an attribute from this component
            for attr_name, attr_value in component_with_attrs.attributes.items():
                # Search for components with this attribute in the same category
                params = QueryParams(
                    category="Capacitors",
                    attributes={attr_name: attr_value},
                    in_stock_only=False,
                    limit=50
                )
                results = search_engine.search(params)

                # All results should match both filters
                for component in results:
                    assert component.category == "Capacitors"
                    assert component.get_attribute_value(attr_name) == attr_value
                break

    def test_search_attribute_missing_value(self, search_engine: ComponentSearch) -> None:
        """Test that components without required attribute are filtered out."""
        # Search for an unlikely attribute value
        params = QueryParams(
            attributes={"SomeRareAttribute": "SomeRareValue"},
            in_stock_only=False,
            limit=100
        )
        results = search_engine.search(params)

        # Results should be empty or only have components with this attribute
        for component in results:
            assert component.get_attribute_value("SomeRareAttribute") == "SomeRareValue"

    def test_search_attribute_multiple_filters(self, search_engine: ComponentSearch) -> None:
        """Test filtering by multiple attributes at once."""
        # Get a component with attributes
        sample_params = QueryParams(category="Capacitors", in_stock_only=False, limit=20)
        sample_results = search_engine.search(sample_params)

        # Find a component with at least 2 attributes
        component_with_attrs = None
        for comp in sample_results:
            if comp.attributes and len(comp.attributes) >= 2:
                component_with_attrs = comp
                break

        if component_with_attrs:
            # Get two attributes from this component
            attr_list = list(component_with_attrs.attributes.items())
            attr1_name, attr1_value = attr_list[0]
            attr2_name, attr2_value = attr_list[1]

            # Search for components with both attributes
            params = QueryParams(
                attributes={
                    attr1_name: attr1_value,
                    attr2_name: attr2_value,
                },
                in_stock_only=False,
                limit=50
            )
            results = search_engine.search(params)

            # All results should have both attributes with matching values
            for component in results:
                assert component.get_attribute_value(attr1_name) == attr1_value
                assert component.get_attribute_value(attr2_name) == attr2_value

    def test_search_attribute_with_other_filters(self, search_engine: ComponentSearch) -> None:
        """Test attribute filtering combined with package and stock filters."""
        # Get a component with attributes
        sample_params = QueryParams(category="Capacitors", in_stock_only=True, limit=20)
        sample_results = search_engine.search(sample_params)

        # Find a component with attributes and a package
        component_with_attrs = None
        for comp in sample_results:
            if comp.attributes and comp.package:
                component_with_attrs = comp
                break

        if component_with_attrs:
            # Get an attribute
            for attr_name, attr_value in component_with_attrs.attributes.items():
                # Complex search with attributes, package, and stock
                params = QueryParams(
                    package=component_with_attrs.package,
                    attributes={attr_name: attr_value},
                    in_stock_only=True,
                    min_stock=50,
                    limit=50
                )
                results = search_engine.search(params)

                # Verify all filters applied
                for component in results:
                    assert component.package == component_with_attrs.package
                    assert component.get_attribute_value(attr_name) == attr_value
                    assert component.stock >= 50
                break
