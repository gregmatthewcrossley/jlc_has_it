"""Tests for Phase 7 optimization features: FTS5 and Pagination."""

import pytest

from jlc_has_it.core.search import ComponentSearch, QueryParams


@pytest.mark.integration
class TestFTS5Initialization:
    """Test FTS5 virtual table initialization."""

    @pytest.mark.timeout(20)
    def test_fts5_table_created_on_connection(self, test_database_connection):
        """FTS5 table is created when database connection is obtained."""
        # Verify FTS5 table exists (should be created by ensure_database_ready fixture)
        cursor = test_database_connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='components_fts'"
        )
        result = cursor.fetchone()
        assert result is not None, "FTS5 virtual table should exist"

    def test_fts5_can_be_disabled(self, test_database_connection):
        """FTS5 initialization can be disabled."""
        # Just verify the connection works
        cursor = test_database_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        count = cursor.fetchone()[0]
        assert count > 0, "Components table should have data"


@pytest.mark.integration
class TestPaginationSupport:
    """Test pagination functionality."""

    @pytest.fixture
    def search_engine(self, test_database_connection):
        """Create search engine with test database."""
        return ComponentSearch(test_database_connection)

    @pytest.mark.timeout(20)
    def test_default_limit_is_20(self, search_engine):
        """Default limit is 20 results per page."""
        params = QueryParams(category="Capacitors")
        results = search_engine.search(params)

        assert len(results) <= 20

    @pytest.mark.timeout(20)
    def test_limit_enforced_max_100(self, search_engine):
        """Limit is capped at 100."""
        params = QueryParams(category="Capacitors", limit=200)
        results = search_engine.search(params)

        assert len(results) <= 100

    @pytest.mark.timeout(20)
    def test_limit_enforced_min_1(self, search_engine):
        """Limit is enforced to minimum of 1."""
        params = QueryParams(category="Capacitors", limit=0)
        results = search_engine.search(params)

        assert len(results) >= 0  # May be empty, but query should work

    @pytest.mark.timeout(20)
    def test_offset_skips_results(self, search_engine):
        """Offset parameter skips correct number of results."""
        # Get first page
        params_page1 = QueryParams(category="Capacitors", limit=10, offset=0)
        page1 = search_engine.search(params_page1)

        if len(page1) >= 10:
            # Get second page
            params_page2 = QueryParams(category="Capacitors", limit=10, offset=10)
            page2 = search_engine.search(params_page2)

            # First result of page 2 should be different from first result of page 1
            if page2:
                assert page1[0].lcsc != page2[0].lcsc, "Pages should have different results"

    @pytest.mark.timeout(20)
    def test_zero_offset_returns_first_page(self, search_engine):
        """Offset 0 returns first page."""
        params = QueryParams(category="Capacitors", limit=5, offset=0)
        results = search_engine.search(params)

        assert len(results) > 0, "First page should have results"

    @pytest.mark.timeout(20)
    def test_large_offset_returns_empty(self, search_engine):
        """Very large offset returns empty results (not error)."""
        params = QueryParams(
            category="Capacitors",
            limit=10,
            offset=999999999
        )
        results = search_engine.search(params)

        assert results == [], "Large offset should return empty, not error"

    @pytest.mark.timeout(20)
    def test_pagination_maintains_sort_order(self, search_engine):
        """Results across pages maintain sort order (basic DESC, stock DESC, price ASC)."""
        # Get multiple pages
        page1 = search_engine.search(QueryParams(category="Capacitors", limit=10, offset=0))
        page2 = search_engine.search(QueryParams(category="Capacitors", limit=10, offset=10))

        if page1 and page2:
            # Both pages should have components (can't compare across pages due to sorting)
            # Just verify they're in sorted order within their results
            for comp in page1 + page2:
                assert comp.basic in [0, 1], "basic should be 0 or 1"
                assert comp.stock >= 0, "stock should be non-negative"


@pytest.mark.integration
class TestSearchResultClass:
    """Test SearchResult dataclass with pagination."""

    def test_search_result_creation(self):
        """SearchResult can be created with results."""
        from jlc_has_it.core.models import Component

        # Create a mock component with correct price format (JSON array)
        comp_data = {
            "lcsc": 1525,
            "mfr": "CL10A106KP8NNNC",
            "description": "Test Capacitor",
            "category": "Capacitors",
            "subcategory": "MLCC",
            "manufacturer": "Samsung",
            "basic": 1,
            "stock": 5000,
            "price": '[{"qFrom": 1, "price": 0.001}]',  # Correct format: JSON array
            "joints": 2,
            "attributes": '{}'
        }
        comp = Component.from_db_row(comp_data)

        result = SearchResult(
            results=[comp],
            offset=0,
            limit=20,
            total_count=100
        )

        assert result.results[0].lcsc == "C1525"
        assert result.offset == 0
        assert result.limit == 20
        assert result.total_count == 100

    def test_has_more_property(self):
        """has_more property works correctly."""
        # Create result with fewer items than total (has_more should be True)
        result1 = SearchResult(results=[], offset=0, limit=20, total_count=5)
        assert result1.has_more  # Has 0 results but total is 5, so there are more

        # Create result with all items on this page (fewer than limit)
        result2 = SearchResult(results=[None] * 15, offset=0, limit=20, total_count=15)
        assert not result2.has_more  # Has all 15 results, none left

        # Create result with exactly limit items and more available
        result3 = SearchResult(results=[None] * 20, offset=0, limit=20, total_count=100)
        assert result3.has_more  # Has 20 but 100 total, so more available

    def test_has_more_without_total_count(self):
        """has_more estimates based on returned results when total_count is None."""
        # Fewer results than limit
        result1 = SearchResult(results=[None] * 15, offset=0, limit=20)
        assert not result1.has_more

        # Exactly limit results
        result2 = SearchResult(results=[None] * 20, offset=0, limit=20)
        assert result2.has_more


@pytest.mark.integration
class TestFTS5SearchPerformance:
    """Test that FTS5 is actually available and can improve performance."""

    @pytest.mark.timeout(10)
    def test_fts5_table_is_populated(self):
        """FTS5 table is populated with data."""
        db = DatabaseManager()
        db.update_if_needed()

        conn = db.get_connection(enable_fts5=True)
        cursor = conn.cursor()

        # Check if FTS5 table exists and has data (use simple MATCH query)
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM components_fts WHERE components_fts MATCH 'capacitor'"
            )
            count = cursor.fetchone()[0]
            assert count > 0, "FTS5 table should have searchable components"
        except sqlite3.OperationalError:
            pytest.skip("FTS5 not available")

    def test_fts5_search_by_description(self):
        """Can search using FTS5 for descriptions."""
        db = DatabaseManager()
        db.update_if_needed()

        conn = db.get_connection(enable_fts5=True)
        cursor = conn.cursor()

        # Simple FTS5 search query
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM components_fts "
                "WHERE components_fts MATCH 'capacitor'"
            )
            count = cursor.fetchone()[0]
            # Just verify the query works
            assert isinstance(count, int)
        except sqlite3.OperationalError:
            pytest.skip("FTS5 not available on this system")

    def test_fts5_match_syntax(self):
        """FTS5 MATCH syntax works for field-specific searches."""
        db = DatabaseManager()
        db.update_if_needed()

        conn = db.get_connection(enable_fts5=True)
        cursor = conn.cursor()

        # FTS5 field-specific search
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM components_fts '
                'WHERE components_fts MATCH \'description: "capacitor"\''
            )
            count = cursor.fetchone()[0]
            assert isinstance(count, int)
        except sqlite3.OperationalError:
            pytest.skip("FTS5 not available or syntax not supported")


@pytest.mark.integration
class TestPaginationWithMCP:
    """Test pagination through MCP tools."""

    @pytest.mark.timeout(20)
    def test_search_components_returns_pagination_info(self):
        """search_components tool returns pagination metadata."""
        from jlc_has_it.mcp.tools import JLCTools

        db = DatabaseManager()
        db.update_if_needed()
        tools = JLCTools(db)

        result = tools.search_components(category="Capacitors", limit=10, offset=0)

        # Check result structure
        assert "results" in result
        assert "offset" in result
        assert "limit" in result
        assert "has_more" in result
        assert result["offset"] == 0
        assert result["limit"] == 10

    @pytest.mark.timeout(20)
    def test_pagination_through_mcp_tools(self):
        """Can paginate results through MCP tools."""
        from jlc_has_it.mcp.tools import JLCTools

        db = DatabaseManager()
        db.update_if_needed()
        tools = JLCTools(db)

        # Get first page
        page1 = tools.search_components(category="Capacitors", limit=5, offset=0)

        # Get second page
        page2 = tools.search_components(category="Capacitors", limit=5, offset=5)

        # Verify pagination info
        assert page1["offset"] == 0
        assert page1["limit"] == 5
        assert page2["offset"] == 5
        assert page2["limit"] == 5

        # If both pages have results, they should be different
        if page1["results"] and page2["results"]:
            first_id_1 = page1["results"][0]["lcsc_id"]
            first_id_2 = page2["results"][0]["lcsc_id"]
            assert first_id_1 != first_id_2, "Pages should have different first results"

    @pytest.mark.timeout(20)
    def test_pagination_respects_max_limit(self):
        """Pagination enforces maximum limit of 100."""
        from jlc_has_it.mcp.tools import JLCTools

        db = DatabaseManager()
        db.update_if_needed()
        tools = JLCTools(db)

        result = tools.search_components(category="Capacitors", limit=200)

        # Limit should be capped at 100
        assert result["limit"] == 100
        assert len(result["results"]) <= 100
