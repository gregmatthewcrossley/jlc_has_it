"""Tests for component search functionality."""

import json
import sqlite3
from pathlib import Path

import pytest

from jlc_has_it.core.search import ComponentSearch, QueryParams


class TestComponentSearch:
    """Tests for ComponentSearch class."""

    @pytest.fixture
    def test_database(self, tmp_path: Path) -> sqlite3.Connection:
        """Create a test database with sample components."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Create components table
        conn.execute(
            """
            CREATE TABLE components (
                lcsc TEXT PRIMARY KEY,
                mfr TEXT,
                description TEXT,
                manufacturer TEXT,
                category TEXT,
                subcategory TEXT,
                joints INTEGER,
                basic INTEGER,
                stock INTEGER,
                price TEXT,
                attributes TEXT
            )
        """
        )

        # Insert test components
        test_components = [
            {
                "lcsc": "C1525",
                "mfr": "CL10A106KP8NNNC",
                "description": "10uF ±10% 10V X5R 0603",
                "manufacturer": "Samsung",
                "category": "Capacitors",
                "subcategory": "Multilayer Ceramic Capacitors MLCC - SMD/SMT",
                "joints": 2,
                "basic": 1,
                "stock": 50000,
                "price": json.dumps([{"qty": 1, "price": 0.0012}]),
                "attributes": json.dumps(
                    {
                        "Capacitance": {"value": 10, "unit": "uF"},
                        "Voltage": {"value": 10, "unit": "V"},
                        "Tolerance": {"value": 10, "unit": "%"},
                        "Package": "0603",
                        "Temperature Coefficient": "X5R",
                    }
                ),
            },
            {
                "lcsc": "C12345",
                "mfr": "TEST-220UF-50V",
                "description": "220uF ±20% 50V Electrolytic",
                "manufacturer": "Generic",
                "category": "Capacitors",
                "subcategory": "Aluminum Electrolytic Capacitors - Leaded",
                "joints": 2,
                "basic": 0,
                "stock": 5000,
                "price": json.dumps([{"qty": 1, "price": 0.15}]),
                "attributes": json.dumps(
                    {
                        "Capacitance": {"value": 220, "unit": "uF"},
                        "Voltage": {"value": 50, "unit": "V"},
                        "Tolerance": {"value": 20, "unit": "%"},
                        "Package": "Radial",
                    }
                ),
            },
            {
                "lcsc": "C67890",
                "mfr": "RES-10K-0402",
                "description": "10kΩ ±1% 0402 Resistor",
                "manufacturer": "Yageo",
                "category": "Resistors",
                "subcategory": "Chip Resistor - Surface Mount",
                "joints": 2,
                "basic": 1,
                "stock": 100000,
                "price": json.dumps([{"qty": 1, "price": 0.001}]),
                "attributes": json.dumps(
                    {
                        "Resistance": {"value": 10000, "unit": "Ω"},
                        "Tolerance": {"value": 1, "unit": "%"},
                        "Power": {"value": 0.063, "unit": "W"},
                        "Package": "0402",
                    }
                ),
            },
            {
                "lcsc": "C99999",
                "mfr": "CAP-100NF-50V",
                "description": "100nF ±10% 50V X7R 0402",
                "manufacturer": "Murata",
                "category": "Capacitors",
                "subcategory": "Multilayer Ceramic Capacitors MLCC - SMD/SMT",
                "joints": 2,
                "basic": 1,
                "stock": 0,  # Out of stock
                "price": json.dumps([{"qty": 1, "price": 0.002}]),
                "attributes": json.dumps(
                    {
                        "Capacitance": {"value": 100, "unit": "nF"},
                        "Voltage": {"value": 50, "unit": "V"},
                        "Package": "0402",
                    }
                ),
            },
        ]

        for component in test_components:
            conn.execute(
                """
                INSERT INTO components
                (lcsc, mfr, description, manufacturer, category, subcategory,
                 joints, basic, stock, price, attributes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    component["lcsc"],
                    component["mfr"],
                    component["description"],
                    component["manufacturer"],
                    component["category"],
                    component["subcategory"],
                    component["joints"],
                    component["basic"],
                    component["stock"],
                    component["price"],
                    component["attributes"],
                ],
            )

        conn.commit()
        return conn

    @pytest.fixture
    def search_engine(self, test_database: sqlite3.Connection) -> ComponentSearch:
        """Create ComponentSearch instance with test database."""
        return ComponentSearch(test_database)

    def test_search_all(self, search_engine: ComponentSearch) -> None:
        """Test searching without filters returns all components."""
        params = QueryParams(in_stock_only=False, limit=100)
        results = search_engine.search(params)

        assert len(results) == 4

    def test_search_by_category(self, search_engine: ComponentSearch) -> None:
        """Test searching by category."""
        params = QueryParams(category="Capacitors", in_stock_only=False)
        results = search_engine.search(params)

        assert len(results) == 3
        for component in results:
            assert component.category == "Capacitors"

    def test_search_by_subcategory(self, search_engine: ComponentSearch) -> None:
        """Test searching by subcategory."""
        params = QueryParams(
            category="Capacitors",
            subcategory="Multilayer Ceramic Capacitors MLCC - SMD/SMT",
            in_stock_only=False,
        )
        results = search_engine.search(params)

        assert len(results) == 2
        for component in results:
            assert component.subcategory == "Multilayer Ceramic Capacitors MLCC - SMD/SMT"

    def test_search_basic_only(self, search_engine: ComponentSearch) -> None:
        """Test filtering for basic parts only."""
        params = QueryParams(category="Capacitors", basic_only=True, in_stock_only=False)
        results = search_engine.search(params)

        assert len(results) == 2
        for component in results:
            assert component.basic is True

    def test_search_in_stock_only(self, search_engine: ComponentSearch) -> None:
        """Test filtering for in-stock parts."""
        params = QueryParams(category="Capacitors", in_stock_only=True)
        results = search_engine.search(params)

        # Should exclude C99999 which is out of stock
        assert len(results) == 2
        for component in results:
            assert component.stock > 0

    def test_search_min_stock(self, search_engine: ComponentSearch) -> None:
        """Test filtering by minimum stock."""
        params = QueryParams(category="Capacitors", min_stock=10000, in_stock_only=False)
        results = search_engine.search(params)

        assert len(results) == 1
        assert results[0].lcsc == "C1525"
        assert results[0].stock >= 10000

    def test_search_max_price(self, search_engine: ComponentSearch) -> None:
        """Test filtering by maximum price."""
        params = QueryParams(category="Capacitors", max_price=0.01, in_stock_only=False)
        results = search_engine.search(params)

        assert len(results) == 2
        for component in results:
            assert component.price <= 0.01

    def test_search_by_package(self, search_engine: ComponentSearch) -> None:
        """Test filtering by package type."""
        params = QueryParams(package="0402", in_stock_only=False)
        results = search_engine.search(params)

        assert len(results) == 2
        assert results[0].get_attribute_value("Package") == "0402"
        assert results[1].get_attribute_value("Package") == "0402"

    def test_search_by_manufacturer(self, search_engine: ComponentSearch) -> None:
        """Test filtering by manufacturer."""
        params = QueryParams(manufacturer="Samsung", in_stock_only=False)
        results = search_engine.search(params)

        assert len(results) == 1
        assert results[0].manufacturer == "Samsung"

    def test_search_by_description(self, search_engine: ComponentSearch) -> None:
        """Test filtering by description."""
        params = QueryParams(description_contains="10uF", in_stock_only=False)
        results = search_engine.search(params)

        assert len(results) == 1
        assert "10uF" in results[0].description

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
        """Test that results are sorted correctly."""
        params = QueryParams(category="Capacitors", in_stock_only=False)
        results = search_engine.search(params)

        # Should be sorted by: basic DESC, stock DESC, price ASC
        # C1525: basic=1, stock=50000, price=0.0012
        # C99999: basic=1, stock=0, price=0.002
        # C12345: basic=0, stock=5000, price=0.15

        assert results[0].lcsc == "C1525"  # basic, high stock, low price
        assert results[1].lcsc == "C99999"  # basic, low stock
        assert results[2].lcsc == "C12345"  # extended

    def test_search_limit(self, search_engine: ComponentSearch) -> None:
        """Test limiting number of results."""
        params = QueryParams(in_stock_only=False, limit=2)
        results = search_engine.search(params)

        assert len(results) == 2

    def test_search_by_category_convenience(self, search_engine: ComponentSearch) -> None:
        """Test convenience method for category search."""
        results = search_engine.search_by_category("Resistors")

        assert len(results) == 1
        assert results[0].category == "Resistors"

    def test_search_by_category_basic_only(self, search_engine: ComponentSearch) -> None:
        """Test category search with basic_only flag."""
        results = search_engine.search_by_category("Capacitors", basic_only=True, limit=10)

        # Only 1 result: C1525 (C99999 is basic but out of stock, excluded by in_stock_only=True default)
        assert len(results) == 1
        for component in results:
            assert component.basic is True

    def test_search_by_lcsc(self, search_engine: ComponentSearch) -> None:
        """Test searching by LCSC part number."""
        component = search_engine.search_by_lcsc("C1525")

        assert component is not None
        assert component.lcsc == "C1525"
        assert component.manufacturer == "Samsung"

    def test_search_by_lcsc_not_found(self, search_engine: ComponentSearch) -> None:
        """Test searching for non-existent LCSC part."""
        component = search_engine.search_by_lcsc("C99999999")

        assert component is None

    def test_search_complex_query(self, search_engine: ComponentSearch) -> None:
        """Test complex search with multiple filters."""
        params = QueryParams(
            category="Capacitors",
            basic_only=True,
            in_stock_only=True,
            max_price=0.01,
            package="0603",
            attributes={"Capacitance": 10},
        )
        results = search_engine.search(params)

        assert len(results) == 1
        assert results[0].lcsc == "C1525"
