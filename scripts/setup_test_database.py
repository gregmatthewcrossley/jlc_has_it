#!/usr/bin/env python3
"""
Test Database Setup Script

Downloads and optimizes the jlcparts database for integration tests.
This is a one-time setup step that should be run before running tests.

Usage:
    python scripts/setup_test_database.py

This script:
1. Downloads the jlcparts database (~11GB) to ./test_data/cache.sqlite3
2. Runs schema optimization (denormalized columns + indexes)
3. Initializes FTS5 full-text search indexes
4. Verifies the database is ready for testing

First run: Takes 30-60 minutes (network dependent, CPU-bound optimization)
Subsequent runs: Skip download/optimization (all idempotent), instant
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jlc_has_it.core.database import DatabaseManager


def main() -> None:
    """Download and prepare test database."""
    print("\n" + "=" * 80)
    print("TEST DATABASE SETUP")
    print("=" * 80)
    print("\nThis script downloads and optimizes the jlcparts database for testing.")
    print("First run will take 30-60 minutes. Subsequent runs are instant.\n")

    # Use test-specific database directory
    test_data_dir = Path.cwd() / "test_data"
    db_manager = DatabaseManager(cache_dir=test_data_dir)

    print(f"Database path: {db_manager.database_path}")
    print(f"Database directory: {test_data_dir}\n")

    # Check if already exists
    if db_manager.database_path.exists():
        age = db_manager.check_database_age()
        if age:
            age_hours = age.total_seconds() / 3600
            print(f"✓ Database already exists (age: {age_hours:.1f} hours)")
            if not db_manager.needs_update():
                print("✓ Database is current, skipping download")
            else:
                print("⚠ Database is >24 hours old, updating...")
        else:
            print("✓ Database file already exists")

    # Download if needed
    print("\nInitializing database with FTS5 and schema optimization...")
    start = time.time()

    try:
        conn = db_manager.get_connection(enable_fts5=True)

        # Verify database is ready
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        count = cursor.fetchone()[0]

        # Verify schema optimization
        cursor.execute("PRAGMA table_info(components)")
        columns = {row[1] for row in cursor.fetchall()}
        has_denormalized = "category_name" in columns

        # Verify FTS5
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='components_fts'"
        )
        has_fts5 = cursor.fetchone() is not None

        conn.close()

        elapsed = time.time() - start

        print("\n" + "=" * 80)
        print("SETUP COMPLETE")
        print("=" * 80)
        print(f"\n✓ Database ready with {count:,} components")
        print(f"  Schema optimization: {'✓ yes' if has_denormalized else '✗ no'}")
        print(f"  FTS5 indexing: {'✓ yes' if has_fts5 else '✗ no'}")
        print(f"  Setup time: {elapsed:.1f} seconds")
        print("\nYou can now run tests with: pytest tests/core/test_fts5_and_pagination.py")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print("\nSetup failed. Please check:")
        print("  1. Network connectivity for database download")
        print("  2. 7z is installed: brew install p7zip")
        print("  3. Disk space available for ~12GB database")
        sys.exit(1)


if __name__ == "__main__":
    main()
