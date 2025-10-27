"""Tests for database manager."""

import json
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
import requests

from jlc_has_it.core.database import DatabaseManager


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path: Path) -> Path:
        """Create a temporary cache directory."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def db_manager(self, temp_cache_dir: Path) -> DatabaseManager:
        """Create a DatabaseManager with temporary cache."""
        return DatabaseManager(cache_dir=temp_cache_dir)

    @pytest.fixture
    def mock_database_file(self, temp_cache_dir: Path) -> Path:
        """Create a mock SQLite database file."""
        db_path = temp_cache_dir / "cache.sqlite3"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Create schema matching real database
        cursor.execute("""
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                category TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE manufacturers (
                id INTEGER PRIMARY KEY,
                manufacturer TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE components (
                lcsc INTEGER PRIMARY KEY,
                category_id INTEGER,
                mfr TEXT,
                package TEXT,
                joints INTEGER,
                manufacturer_id INTEGER,
                basic INTEGER,
                description TEXT,
                datasheet TEXT,
                stock INTEGER,
                price TEXT,
                last_update INTEGER,
                extra TEXT,
                flag INTEGER,
                last_on_stock INTEGER,
                preferred INTEGER
            )
        """)
        cursor.execute("INSERT INTO categories VALUES (1, 'Test Category')")
        cursor.execute("INSERT INTO manufacturers VALUES (1, 'Test Mfr')")
        cursor.execute("""
            INSERT INTO components VALUES
            (12345, 1, 'TEST-001', '0603', 2, 1, 1, 'Test part', NULL, 100, '[{"qty":1,"price":0.01}]',
             0, NULL, 0, NULL, 0)
        """)
        conn.commit()
        conn.close()
        return db_path

    def test_init_creates_cache_directory(self, tmp_path: Path) -> None:
        """Test that initialization creates cache directory."""
        cache_dir = tmp_path / "test_cache"
        manager = DatabaseManager(cache_dir=cache_dir)

        assert cache_dir.exists()
        assert manager.cache_dir == cache_dir
        assert manager.database_path == cache_dir / "cache.sqlite3"

    def test_check_database_age_nonexistent(self, db_manager: DatabaseManager) -> None:
        """Test checking age when database doesn't exist."""
        age = db_manager.check_database_age()
        assert age is None

    def test_check_database_age_exists(
        self, db_manager: DatabaseManager, mock_database_file: Path
    ) -> None:
        """Test checking age of existing database."""
        age = db_manager.check_database_age()

        assert age is not None
        assert age < timedelta(minutes=1)  # Just created

    def test_check_database_age_old(
        self, db_manager: DatabaseManager, mock_database_file: Path
    ) -> None:
        """Test checking age of old database."""
        # Set modification time to 2 days ago
        two_days_ago = datetime.now() - timedelta(days=2)
        timestamp = two_days_ago.timestamp()
        mock_database_file.touch()
        import os

        os.utime(mock_database_file, (timestamp, timestamp))

        age = db_manager.check_database_age()
        assert age is not None
        assert age > timedelta(days=1, hours=23)  # ~2 days

    def test_needs_update_nonexistent(self, db_manager: DatabaseManager) -> None:
        """Test that missing database needs update."""
        assert db_manager.needs_update() is True

    def test_needs_update_fresh(
        self, db_manager: DatabaseManager, mock_database_file: Path
    ) -> None:
        """Test that fresh database doesn't need update."""
        assert db_manager.needs_update() is False

    def test_needs_update_old(self, db_manager: DatabaseManager, mock_database_file: Path) -> None:
        """Test that old database needs update."""
        # Set modification time to 2 days ago
        two_days_ago = datetime.now() - timedelta(days=2)
        timestamp = two_days_ago.timestamp()
        import os

        os.utime(mock_database_file, (timestamp, timestamp))

        assert db_manager.needs_update() is True

    def test_download_database(
        self, db_manager: DatabaseManager, mocker: Any, temp_cache_dir: Path
    ) -> None:
        """Test downloading database."""
        # Create mock zip file content
        mock_db_path = temp_cache_dir / "mock_db.sqlite3"
        conn = sqlite3.connect(mock_db_path)
        conn.cursor().execute("CREATE TABLE components (lcsc TEXT)")
        conn.close()

        # Create a zip file containing the mock database
        zip_buffer = temp_cache_dir / "test.zip"
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.write(mock_db_path, arcname="cache.sqlite3")

        zip_content = zip_buffer.read_bytes()

        # Mock requests.get to return zip parts
        mock_response = Mock()
        mock_response.content = zip_content
        mock_response.raise_for_status = Mock()
        mocker.patch("requests.get", return_value=mock_response)

        # Download database
        db_manager.download_database()

        # Verify database was extracted and is valid
        assert db_manager.database_path.exists()

        conn = sqlite3.connect(db_manager.database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "components" in tables

    def test_download_database_network_error(
        self, db_manager: DatabaseManager, mocker: Any
    ) -> None:
        """Test handling of network errors during download."""
        mocker.patch("requests.get", side_effect=requests.RequestException("Network error"))

        with pytest.raises(requests.RequestException):
            db_manager.download_database()

    def test_validate_database_invalid(
        self, db_manager: DatabaseManager, temp_cache_dir: Path
    ) -> None:
        """Test validation fails for invalid database."""
        # Create an invalid (empty) file
        db_manager.database_path.write_text("not a database")

        with pytest.raises(sqlite3.DatabaseError):
            db_manager._validate_database()

    def test_validate_database_empty(
        self, db_manager: DatabaseManager, temp_cache_dir: Path
    ) -> None:
        """Test validation fails for database with no tables."""
        # Create valid SQLite file but with no tables
        conn = sqlite3.connect(db_manager.database_path)
        conn.close()

        with pytest.raises(sqlite3.DatabaseError, match="no tables"):
            db_manager._validate_database()

    def test_update_if_needed_missing(self, db_manager: DatabaseManager, mocker: Any) -> None:
        """Test update when database is missing."""
        mock_download = mocker.patch.object(db_manager, "download_database")

        result = db_manager.update_if_needed()

        assert result is True
        mock_download.assert_called_once()

    def test_update_if_needed_current(
        self, db_manager: DatabaseManager, mock_database_file: Path, mocker: Any
    ) -> None:
        """Test no update when database is current."""
        mock_download = mocker.patch.object(db_manager, "download_database")

        result = db_manager.update_if_needed()

        assert result is False
        mock_download.assert_not_called()

    def test_get_connection(self, db_manager: DatabaseManager, mock_database_file: Path) -> None:
        """Test getting database connection."""
        conn = db_manager.get_connection(enable_fts5=False)

        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row

        # Test that we can query the database
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM components")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["lcsc"] == 12345

        conn.close()

    def test_get_connection_missing_database(
        self, db_manager: DatabaseManager, mocker: Any
    ) -> None:
        """Test get_connection when database can't be downloaded."""
        # Mock update_if_needed to do nothing
        mocker.patch.object(db_manager, "update_if_needed", return_value=False)

        with pytest.raises(FileNotFoundError):
            db_manager.get_connection()

    def test_get_database_info(self, db_manager: DatabaseManager, mocker: Any) -> None:
        """Test fetching database metadata."""
        mock_info = {"created": "2025-01-01T00:00:00+00:00", "categories": {}}

        mock_response = Mock()
        mock_response.text = json.dumps(mock_info)
        mock_response.raise_for_status = Mock()
        mocker.patch("requests.get", return_value=mock_response)

        info = db_manager.get_database_info()

        assert info == mock_info

    def test_get_database_info_network_error(
        self, db_manager: DatabaseManager, mocker: Any
    ) -> None:
        """Test handling network error when fetching database info."""
        mocker.patch("requests.get", side_effect=requests.RequestException("Network error"))

        info = db_manager.get_database_info()

        assert info is None
