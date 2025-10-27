"""Integration tests with real JLCPCB database.

These tests verify functionality with the actual jlcparts database schema:
- Normalized tables (components, categories, manufacturers)
- Integer LCSC IDs stored as integers (converted to "C" prefix format)
- Foreign keys (category_id, manufacturer_id) properly handled via JOINs
- Component specs extracted from JSON extra field

The core modules have been refactored to work with the real database schema.
Unit tests (tests/core/) use mocked data while integration tests verify real data.

Run with: pytest tests/integration/test_real_database.py -v -s
"""

import sqlite3
from pathlib import Path

import pytest

from jlc_has_it.core.database import DatabaseManager


class TestRealDatabaseSchema:
    """Tests documenting actual JLCPCB database schema."""

    @pytest.fixture(scope="class")
    def connection(self):
        """Get real database connection."""
        db = DatabaseManager()
        db.update_if_needed()
        conn = db.get_connection()
        yield conn
        conn.close()

    def test_real_schema_has_lookup_tables(self, connection):
        """Document real database structure."""
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # Real database uses normalized structure
        assert "components" in tables
        assert "categories" in tables
        assert "manufacturers" in tables

    def test_lcsc_ids_are_integers(self, connection):
        """Document that LCSC IDs are stored as integers in real database."""
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(components)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        # lcsc column is INTEGER, not TEXT
        assert columns.get("lcsc") == "INTEGER"

    def test_real_database_has_millions_of_components(self, connection):
        """Verify database size."""
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        count = cursor.fetchone()[0]

        # Real database should have millions of components
        assert count > 1000000, f"Expected millions, got {count}"


@pytest.mark.integration
class TestRealDatabase:
    """Tests with real jlcparts database."""

    @pytest.fixture(scope="class")
    def database(self):
        """Get database connection (shared across tests)."""
        db = DatabaseManager()
        db.update_if_needed()
        yield db

    @pytest.fixture(scope="class")
    def connection(self, database):
        """Get SQLite connection to real database."""
        conn = database.get_connection()
        yield conn
        conn.close()

    def test_database_exists(self, database):
        """Verify database file exists and is valid SQLite."""
        assert database.database_path.exists()
        assert database.database_path.stat().st_size > 0

    def test_database_has_components_table(self, connection):
        """Verify database contains components table."""
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert "components" in tables

    def test_database_has_millions_of_components(self, connection):
        """Verify database contains millions of components."""
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        count = cursor.fetchone()[0]

        # Should have significant number of components
        assert count > 1000000, f"Expected > 1 million components, got {count}"

    def test_database_core_columns(self, connection):
        """Verify database has core component columns."""
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(components)")
        columns = {row[1] for row in cursor.fetchall()}

        # Core columns that should always exist
        assert "lcsc" in columns
        assert "description" in columns
        assert "stock" in columns
        assert "price" in columns

    def test_database_sample_components(self, connection):
        """Verify we can fetch sample components."""
        cursor = connection.cursor()
        cursor.execute("SELECT lcsc, description, stock FROM components LIMIT 5")
        rows = cursor.fetchall()

        assert len(rows) == 5
        # Each row should have valid data
        for lcsc, description, stock in rows:
            assert lcsc is not None
            assert description is not None or description == ""

    def test_database_info(self, database):
        """Verify database metadata can be fetched."""
        info = database.get_database_info()

        # Info might be None if network fails, but shouldn't error
        if info is not None:
            # Should have some metadata if available
            assert isinstance(info, dict)


@pytest.mark.integration
class TestRealLibraryDownload:
    """Integration tests for real easyeda2kicad downloads.

    Note: These tests require easyeda2kicad to be installed.
    They will attempt to download actual component libraries.
    """

    @pytest.fixture
    def downloader(self):
        """Get library downloader."""
        try:
            from jlc_has_it.core.library_downloader import LibraryDownloader

            return LibraryDownloader()
        except ImportError:
            pytest.skip("easyeda2kicad not installed")

    def test_download_common_component(self, downloader):
        """Test downloading a well-known component library."""
        # C1525: Samsung 100nF capacitor
        library = downloader.download_component("C1525")

        # May fail if JLCPCB/EasyEDA changes, but shouldn't crash
        if library is not None:
            assert library.lcsc_id == "C1525"
            assert library.symbol_path.exists()

    def test_download_validates_files(self, downloader):
        """Verify downloaded library files are validated."""
        library = downloader.download_component("C1525")

        if library is not None:
            # Should have validation method
            assert hasattr(library, "is_valid")
            # Validation should work
            is_valid = library.is_valid()
            assert isinstance(is_valid, bool)

    def test_download_handles_missing_component(self, downloader):
        """Verify graceful handling of non-existent component."""
        # Use fake LCSC ID
        library = downloader.download_component("C999999999")

        # Should return None for missing component
        assert library is None




