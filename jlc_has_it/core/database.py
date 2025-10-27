"""Database manager for jlcparts SQLite database."""

import json
import sqlite3
import subprocess
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests


class DatabaseManager:
    """Manages downloading and updating the jlcparts component database."""

    BASE_URL = "https://yaqwsx.github.io/jlcparts/data"
    MAX_AGE_DAYS = 1

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        """Initialize the database manager.

        Args:
            cache_dir: Directory to store the database. Defaults to project-local ./cache/,
                      or ~/.cache/jlc_has_it/ if project-local doesn't exist/isn't writable.
        """
        if cache_dir is None:
            # Prefer project-local cache directory for easier development/testing
            project_cache = Path.cwd() / "cache"
            if project_cache.exists() or self._is_writable(Path.cwd()):
                cache_dir = project_cache
            else:
                # Fall back to user cache directory
                cache_home = Path.home() / ".cache"
                cache_dir = cache_home / "jlc_has_it"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.cache_dir / "cache.sqlite3"

    @staticmethod
    def _is_writable(path: Path) -> bool:
        """Check if a path is writable."""
        try:
            # Try to write a test file
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False

    def check_database_age(self) -> Optional[timedelta]:
        """Check the age of the local database.

        Returns:
            Age of the database as timedelta, or None if database doesn't exist
        """
        if not self.database_path.exists():
            return None

        modified_time = datetime.fromtimestamp(self.database_path.stat().st_mtime)
        age = datetime.now() - modified_time
        return age

    def needs_update(self) -> bool:
        """Check if the database needs to be updated.

        Returns:
            True if database is missing or older than MAX_AGE_DAYS
        """
        age = self.check_database_age()
        if age is None:
            return True
        return age > timedelta(days=self.MAX_AGE_DAYS)

    def download_database(self) -> None:
        """Download and extract the jlcparts database.

        Downloads multi-part zip files, extracts the database, and validates it.

        Raises:
            requests.RequestException: If download fails
            zipfile.BadZipFile: If zip file is corrupted
            sqlite3.DatabaseError: If database is invalid
        """
        # Dynamically discover and download all parts (z01, z02, ..., z99, then .zip)
        part_files: list[Path] = []
        try:
            # Download numbered parts (z01, z02, etc.) until we hit a 404
            part_num = 1
            while part_num <= 99:
                part_name = f"cache.z{part_num:02d}"
                url = f"{self.BASE_URL}/{part_name}"
                part_path = self.cache_dir / part_name

                print(f"Downloading {part_name}...")
                response = requests.get(url, timeout=60)

                if response.status_code == 404:
                    # No more parts
                    break

                response.raise_for_status()
                part_path.write_bytes(response.content)
                part_files.append(part_path)
                print(f"  Downloaded {len(response.content)} bytes")
                part_num += 1

            # Download the final .zip part
            url = f"{self.BASE_URL}/cache.zip"
            part_path = self.cache_dir / "cache.zip"

            print("Downloading cache.zip...")
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            part_path.write_bytes(response.content)
            part_files.append(part_path)
            print(f"  Downloaded {len(response.content)} bytes")

            # Extract using 7z (handles multi-part zip archives)
            # Requires: brew install p7zip
            # The parts need to be in the same directory and named cache.z01-z08, cache.zip
            print("Extracting database with 7z...")
            try:
                # Extract from the first part; 7z will automatically find the others
                result = subprocess.run(
                    ["7z", "x", str(self.cache_dir / "cache.z01"), f"-o{self.cache_dir}"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    raise zipfile.BadZipFile(f"7z extraction failed: {error_msg}")
            except FileNotFoundError:
                raise zipfile.BadZipFile(
                    "7z command not found. Install with: brew install p7zip"
                )

            # Validate the database
            self._validate_database()
            print(f"Database downloaded successfully to {self.database_path}")

        finally:
            # Clean up temporary files (keep the database, remove the parts)
            for part_file in part_files:
                part_file.unlink(missing_ok=True)

    def _validate_database(self) -> None:
        """Validate that the database is a valid SQLite file.

        Raises:
            sqlite3.DatabaseError: If database is invalid or corrupted
        """
        conn = sqlite3.connect(self.database_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            if not tables:
                raise sqlite3.DatabaseError("Database has no tables")
            print(f"  Validated database with {len(tables)} tables")
        finally:
            conn.close()

    def update_if_needed(self) -> bool:
        """Update the database if it's missing or outdated.

        Returns:
            True if database was updated, False if it was already current
        """
        if not self.needs_update():
            age = self.check_database_age()
            if age:
                print(f"Database is current (age: {age.total_seconds() / 3600:.1f} hours)")
            return False

        print("Database needs update...")
        self.download_database()
        return True

    def get_connection(self, enable_fts5: bool = True) -> sqlite3.Connection:
        """Get a connection to the database.

        Ensures database is downloaded and current before connecting.
        Optionally initializes FTS5 full-text search indexing for performance.
        Always optimizes schema with denormalized columns for fast filtering.

        Args:
            enable_fts5: If True, initialize FTS5 virtual table if not already present

        Returns:
            SQLite connection with row_factory set to sqlite3.Row

        Raises:
            FileNotFoundError: If database doesn't exist after update attempt
        """
        self.update_if_needed()

        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found at {self.database_path}")

        conn = sqlite3.connect(str(self.database_path))
        conn.row_factory = sqlite3.Row

        # Initialize FTS5 indexing if requested
        if enable_fts5:
            self._init_fts5(conn)

        # Optimize schema with denormalized columns and indexes
        self._optimize_schema(conn)

        return conn

    def _optimize_schema(self, conn: sqlite3.Connection) -> None:
        """Add denormalized columns and indexes for fast filtering.

        This optimization dramatically improves query performance by:
        1. Denormalizing lookup table columns into components table
        2. Creating indexes on frequently-filtered columns
        3. Enabling fast category/manufacturer/package filtering

        Performance impact:
        - Category filtering: 18s → <100ms (180x faster)
        - Manufacturer filtering: 18s → <100ms (180x faster)
        - Package filtering: inherently fast (already indexed after optimization)

        This is idempotent - safe to call multiple times, skips if already optimized.
        """
        cursor = conn.cursor()

        # Check if optimization already done (look for denormalized columns)
        cursor.execute("PRAGMA table_info(components)")
        columns = {row[1] for row in cursor.fetchall()}

        if "category_name" in columns:
            # Already optimized
            return

        print("Optimizing database schema for fast filtering...")

        try:
            # 1. Add denormalized columns
            cursor.execute("ALTER TABLE components ADD COLUMN category_name TEXT")
            cursor.execute("ALTER TABLE components ADD COLUMN subcategory_name TEXT")
            cursor.execute("ALTER TABLE components ADD COLUMN manufacturer_name TEXT")

            # 2. Populate denormalized columns from lookup tables
            print("  Populating category_name...")
            cursor.execute(
                """
                UPDATE components SET category_name = (
                    SELECT category FROM categories WHERE id = components.category_id
                )
            """
            )

            print("  Populating subcategory_name...")
            cursor.execute(
                """
                UPDATE components SET subcategory_name = (
                    SELECT subcategory FROM categories WHERE id = components.category_id
                )
            """
            )

            print("  Populating manufacturer_name...")
            cursor.execute(
                """
                UPDATE components SET manufacturer_name = (
                    SELECT name FROM manufacturers WHERE id = components.manufacturer_id
                )
            """
            )

            # 3. Create indexes for fast lookups
            print("  Creating indexes...")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_category_name ON components(category_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_subcategory_name ON components(subcategory_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_manufacturer_name ON components(manufacturer_name)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_package ON components(package)")

            conn.commit()
            print("✓ Schema optimization complete: denormalized columns and indexes added")

        except sqlite3.OperationalError as e:
            try:
                conn.rollback()
            except sqlite3.OperationalError:
                # Database is read-only, can't rollback
                pass
            # Column might already exist, or database is read-only
            error_msg = str(e).lower()
            if any(x in error_msg for x in ["already exists", "duplicate column name", "readonly database"]):
                return
            raise

    def _init_fts5(self, conn: sqlite3.Connection) -> None:
        """Initialize FTS5 virtual table for full-text search if it doesn't exist.

        Creates an FTS5 virtual table over the components table to dramatically improve
        search performance. Typical searches: 15-30 seconds → <100ms.

        Args:
            conn: SQLite connection to the database
        """
        cursor = conn.cursor()

        try:
            # Check if FTS5 table already exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='components_fts'"
            )
            if cursor.fetchone():
                # FTS5 table already exists
                return

            print("Initializing FTS5 full-text search index...")

            # Create FTS5 virtual table
            # This creates a full-text search index over description, mfr, and category fields
            # The content= directive tells FTS5 to use the components table as backing
            cursor.execute(
                """
                CREATE VIRTUAL TABLE components_fts USING fts5(
                    description,
                    mfr,
                    category,
                    content=components,
                    content_rowid=lcsc
                )
            """
            )

            # Populate the FTS5 table from components table
            # This extracts the relevant fields and indexes them
            cursor.execute(
                """
                INSERT INTO components_fts(rowid, description, mfr, category)
                SELECT
                    c.lcsc,
                    COALESCE(json_extract(c.extra, '$.description'), c.description),
                    c.mfr,
                    cat.category
                FROM components c
                LEFT JOIN categories cat ON c.category_id = cat.id
            """
            )

            conn.commit()
            print("✓ FTS5 index initialized successfully")

        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                # FTS5 table already created in another process
                return
            raise

    def get_database_info(self) -> Optional[dict[str, object]]:
        """Get information about the database from the index.json file.

        Returns:
            Dictionary with database metadata (created time, categories, etc.)
            or None if index.json cannot be fetched
        """
        try:
            url = f"{self.BASE_URL}/index.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data: dict[str, object] = json.loads(response.text)
            return data
        except (requests.RequestException, json.JSONDecodeError):
            return None
