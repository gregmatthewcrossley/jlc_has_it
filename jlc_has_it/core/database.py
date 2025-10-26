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
            cache_dir: Directory to store the database. Defaults to ~/.cache/jlc_has_it/
        """
        if cache_dir is None:
            # Use XDG_CACHE_HOME or fallback to ~/.cache
            cache_home = Path.home() / ".cache"
            cache_dir = cache_home / "jlc_has_it"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.cache_dir / "cache.sqlite3"

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

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection to the database.

        Ensures database is downloaded and current before connecting.

        Returns:
            SQLite connection with row_factory set to sqlite3.Row

        Raises:
            FileNotFoundError: If database doesn't exist after update attempt
        """
        self.update_if_needed()

        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found at {self.database_path}")

        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

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
