"""Pytest configuration and common fixtures."""

from pathlib import Path
from typing import Any

import pytest

from jlc_has_it.core.database import DatabaseManager


@pytest.fixture(scope="session", autouse=True)
def ensure_database_ready() -> None:
    """
    Session-scoped fixture that ensures the jlcparts database is downloaded and ready
    before any tests run. This is a one-time operation for the entire test session.

    Outputs verbose status so we always know what's happening during the download/check.
    """
    db_manager = DatabaseManager()

    print("\n" + "=" * 80)
    print("TEST SESSION: Ensuring jlcparts database is ready...")
    print("=" * 80)

    # Check if database exists and is current
    if not db_manager.get_database_path().exists():
        print("✓ Database file not found - will download on first use")
    else:
        age_hours = db_manager.check_database_age()
        if age_hours is not None:
            print(f"✓ Database exists (age: {age_hours:.1f} hours)")
            if db_manager.needs_update(age_hours):
                print("  WARNING: Database is >24 hours old, consider updating")
        else:
            print("✓ Database file exists")

    # Get connection which will trigger download if needed
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        count = cursor.fetchone()[0]
        print(f"✓ Database is ready with {count:,} components")
        conn.close()
    except Exception as e:
        print(f"✗ ERROR: Failed to initialize database: {e}")
        raise

    print("=" * 80 + "\n")


@pytest.fixture
def sample_component_data() -> dict[str, Any]:
    """Sample component data for testing (using real jlcparts database schema)."""
    return {
        "lcsc": 12345,  # Real database stores as integer
        "mfr": "TEST-PART-001",
        "description": "",  # Empty in real database, full description in extra JSON
        "manufacturer": "Test Manufacturer",
        "category_id": 1,  # Real database uses foreign keys
        "category": "Capacitors",  # These are computed from JOINs in queries
        "subcategory": "Multilayer Ceramic Capacitors MLCC - SMD/SMT",
        "manufacturer_id": 1,  # Real database uses foreign keys
        "joints": 2,
        "basic": True,
        "stock": 5000,
        "price": [
            {"qFrom": 1, "price": 0.0012},  # Real database uses qFrom/qTo format
            {"qFrom": 10, "price": 0.0010},
            {"qFrom": 100, "price": 0.0008},
        ],
        "attributes": None,  # Real database has attributes in extra JSON
        "extra": {
            "description": "Test Component 100nF 50V X7R 0402",
            "attributes": {
                "Capacitance": {"value": 100, "unit": "nF"},
                "Voltage": {"value": 50, "unit": "V"},
                "Tolerance": {"value": 10, "unit": "%"},
                "Package": "0402",
                "Temperature Coefficient": "X7R",
            },
        },
    }


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary KiCad project directory structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create typical KiCad project structure
    (project_dir / "test_project.kicad_pro").touch()
    (project_dir / "test_project.kicad_sch").touch()

    libraries_dir = project_dir / "libraries"
    libraries_dir.mkdir()

    footprints_dir = libraries_dir / "footprints.pretty"
    footprints_dir.mkdir()

    models_dir = libraries_dir / "3d_models"
    models_dir.mkdir()

    return project_dir


@pytest.fixture
def mock_database_connection(mocker: Any) -> Any:
    """Mock database connection for testing."""
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.execute.return_value = mock_cursor
    return mock_conn
