"""Pytest configuration and common fixtures."""

from pathlib import Path
from typing import Any
import sqlite3

import pytest

from jlc_has_it.core.database import DatabaseManager


# Track test progress for verbose output
_test_counter = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "total": 0, "collected": 0}

# Path to test-specific database (isolated from user's cache)
TEST_DB_PATH: Path = Path.cwd() / "test_data" / "cache.sqlite3"


@pytest.fixture(scope="session", autouse=True)
def ensure_database_ready() -> None:
    """
    Session-scoped fixture that verifies the test database is ready.

    This fixture expects the test database to be pre-downloaded and optimized
    using: python scripts/setup_test_database.py

    The separation allows long-running setup (30-60 minutes) to happen outside
    of pytest, avoiding timeout and lock contention issues.
    """
    # Use test-specific database directory
    db_manager = DatabaseManager(cache_dir=TEST_DB_PATH.parent)

    print("\n" + "=" * 80)
    print("TEST SESSION: Verifying test database is ready...")
    print(f"Database: {db_manager.database_path}")
    print("=" * 80)

    # Database must exist - if not, tell user to run setup script
    if not db_manager.database_path.exists():
        print("\n✗ ERROR: Test database not found!")
        print(f"\nPlease set up the test database first by running:")
        print(f"  python scripts/setup_test_database.py")
        print(f"\nThis downloads and optimizes the jlcparts database.")
        print(f"First run takes 30-60 minutes. Subsequent runs skip setup.\n")
        raise FileNotFoundError(
            f"Test database not found at {db_manager.database_path}. "
            "Run 'python scripts/setup_test_database.py' to set it up."
        )

    # Get connection to verify database is ready
    try:
        conn = db_manager.get_connection(enable_fts5=True)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        count = cursor.fetchone()[0]

        # Verify optimization is complete
        cursor.execute("PRAGMA table_info(components)")
        columns = {row[1] for row in cursor.fetchall()}
        has_denormalized = "category_name" in columns

        # Verify FTS5 is initialized
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='components_fts'")
        has_fts5 = cursor.fetchone() is not None

        print(f"✓ Database ready with {count:,} components")
        print(f"  Schema optimization: {'✓ yes' if has_denormalized else '✗ no'}")
        print(f"  FTS5 indexing: {'✓ yes' if has_fts5 else '✗ no'}")
        conn.close()
    except Exception as e:
        print(f"✗ ERROR: Failed to verify database: {e}")
        raise

    print("=" * 80 + "\n")


@pytest.fixture
def test_database_connection() -> sqlite3.Connection:
    """
    Fixture providing a connection to the test database.
    Uses the same database prepared by ensure_database_ready().
    """
    db_manager = DatabaseManager(cache_dir=TEST_DB_PATH.parent)
    conn = db_manager.get_connection(enable_fts5=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def pytest_collection_finish(session: Any) -> None:
  """Hook called after test collection is finished."""
  # Record the total number of collected tests for statusline display
  _test_counter["collected"] = len(session.items)


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


# Pytest hooks for verbose test progress output
def pytest_runtest_logreport(report: Any) -> None:
    """Hook called after a test result is logged."""
    if report.when == "call":  # Only count actual test execution, not setup/teardown
        if report.passed:
            _test_counter["passed"] += 1
            status = "✓ PASS"
        elif report.failed:
            _test_counter["failed"] += 1
            status = "✗ FAIL"
        elif report.skipped:
            _test_counter["skipped"] += 1
            status = "⊘ SKIP"
        else:
            return

        _test_counter["total"] += 1
        test_name = report.nodeid.split("::")[-1]
        total = _test_counter["total"]
        print(f"\n[{total:3d}] {status} {test_name}")

        # Write status file for live statusline monitoring
        cache_dir = Path.cwd() / ".pytest_cache"
        cache_dir.mkdir(exist_ok=True)
        status_file = cache_dir / "test_status.txt"
        status_content = f"PASSED:{_test_counter['passed']} FAILED:{_test_counter['failed']} SKIPPED:{_test_counter['skipped']} COLLECTED:{_test_counter['collected']}"
        try:
            status_file.write_text(status_content)
        except Exception:
            pass  # Silently ignore if we can't write the status file


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Hook called after all tests have been run."""
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✓ Passed:  {_test_counter['passed']}")
    print(f"✗ Failed:  {_test_counter['failed']}")
    print(f"⊘ Skipped: {_test_counter['skipped']}")
    print(f"━━━━━━━━━━")
    print(f"  Total:   {_test_counter['total']}")
    print("=" * 80)

    # Write test stats for statusline monitoring
    from pathlib import Path
    cache_dir = Path.cwd() / ".pytest_cache"
    cache_dir.mkdir(exist_ok=True)
    status_file = cache_dir / "test_status.txt"
    status_content = f"PASSED:{_test_counter['passed']} FAILED:{_test_counter['failed']} SKIPPED:{_test_counter['skipped']} COLLECTED:{_test_counter['collected']}"
    try:
        status_file.write_text(status_content)
    except Exception:
        pass  # Silently ignore if we can't write the status file
