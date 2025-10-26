"""Database manager for jlcparts SQLite database."""

import json
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests


class DatabaseManager:
    """Manages downloading and updating the jlcparts component database."""

    BASE_URL = "https://yaqwsx.github.io/jlcparts/data"
    DATABASE_PARTS = ["cache.z01", "cache.z02", "cache.zip"]
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

        Downloads multi-part zip files, concatenates them, extracts the database,
        and validates it.

        Raises:
            requests.RequestException: If download fails
            zipfile.BadZipFile: If zip file is corrupted
            sqlite3.DatabaseError: If database is invalid
        """
        # Download all parts
        part_files: list[Path] = []
        try:
            for part_name in self.DATABASE_PARTS:
                url = f"{self.BASE_URL}/{part_name}"
                part_path = self.cache_dir / part_name

                print(f"Downloading {part_name}...")
                response = requests.get(url, timeout=60)
                response.raise_for_status()

                part_path.write_bytes(response.content)
                part_files.append(part_path)
                print(f"  Downloaded {len(response.content)} bytes")

            # Concatenate parts into a single zip file
            combined_zip = self.cache_dir / "cache_combined.zip"
            print("Concatenating zip parts...")
            with combined_zip.open("wb") as outfile:
                for part_file in part_files:
                    outfile.write(part_file.read_bytes())

            # Extract the database
            print("Extracting database...")
            with zipfile.ZipFile(combined_zip, "r") as zip_file:
                # The zip should contain cache.sqlite3
                zip_file.extract("cache.sqlite3", self.cache_dir)

            # Validate the database
            self._validate_database()
            print(f"Database downloaded successfully to {self.database_path}")

        finally:
            # Clean up temporary files
            for part_file in part_files:
                part_file.unlink(missing_ok=True)
            combined_zip = self.cache_dir / "cache_combined.zip"
            combined_zip.unlink(missing_ok=True)

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
