"""Download and validate KiCad libraries for components."""

import logging
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DownloadError:
    """Represents a download failure with error details."""

    lcsc_id: str
    error_type: str  # "timeout", "not_found", "validation", "subprocess", "filesystem"
    message: str
    details: Optional[str] = None

    def user_friendly_message(self) -> str:
        """Get a user-friendly error message."""
        if self.error_type == "timeout":
            return f"Download for {self.lcsc_id} timed out (took too long)"
        elif self.error_type == "not_found":
            return f"Component {self.lcsc_id} not found or unavailable for download"
        elif self.error_type == "validation":
            return f"Downloaded files for {self.lcsc_id} are incomplete: {self.message}"
        elif self.error_type == "subprocess":
            return f"Download tool error for {self.lcsc_id}: {self.message}"
        else:
            return f"Failed to download {self.lcsc_id}: {self.message}"


@dataclass
class ComponentLibrary:
    """Represents downloaded library files for a component."""

    lcsc_id: str
    symbol_path: Path
    footprint_dir: Path
    model_dir: Path

    def is_valid(self) -> bool:
        """Check if all library files exist and are accessible."""
        return (
            self.symbol_path.exists()
            and self.symbol_path.stat().st_size > 0
            and self.footprint_dir.exists()
            and len(list(self.footprint_dir.glob("*.kicad_mod"))) > 0
            and self.model_dir.exists()
            and (
                len(list(self.model_dir.glob("*.step"))) > 0
                or len(list(self.model_dir.glob("*.wrl"))) > 0
            )
        )


class LibraryDownloader:
    """Download component libraries from easyeda2kicad."""

    EXPECTED_SYMBOL_FILE = "easyeda2kicad.kicad_sym"
    EXPECTED_FOOTPRINT_DIR = "easyeda2kicad.pretty"
    EXPECTED_MODEL_DIR = "easyeda2kicad.3dshapes"
    TIMEOUT_SECONDS = 30

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        """Initialize downloader.

        Args:
            cache_dir: Directory to cache downloaded libraries.
                      Defaults to /tmp/jlc_has_it/cache/
        """
        if cache_dir is None:
            cache_dir = Path(tempfile.gettempdir()) / "jlc_has_it" / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_component(
        self, lcsc_id: str, output_dir: Optional[Path] = None
    ) -> Optional[ComponentLibrary]:
        """Download libraries for a single component.

        Args:
            lcsc_id: JLCPCB part number (e.g., "C1525")
            output_dir: Directory to download to. Defaults to cache_dir/lcsc_id/

        Returns:
            ComponentLibrary if successful, None if validation fails
        """
        if output_dir is None:
            output_dir = self.cache_dir / lcsc_id

        output_dir.mkdir(parents=True, exist_ok=True)

        # Run easyeda2kicad
        symbol_output = output_dir / self.EXPECTED_SYMBOL_FILE
        try:
            logger.debug(f"Starting download for {lcsc_id}")

            result = subprocess.run(
                [
                    "easyeda2kicad",
                    "--full",
                    f"--lcsc_id={lcsc_id}",
                    f"--output={symbol_output}",
                ],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_SECONDS,
            )

            # Check exit code
            if result.returncode != 0:
                logger.error(
                    f"Download failed for {lcsc_id}: easyeda2kicad exited with code {result.returncode}",
                    extra={
                        "lcsc_id": lcsc_id,
                        "exit_code": result.returncode,
                        "stderr": result.stderr[:200],
                    },
                )
                # Determine if it's "not found" or other error
                if "not found" in result.stderr.lower() or result.returncode == 1:
                    logger.warning(f"Component {lcsc_id} not found on EasyEDA/JLCPCB")
                return None

            # Validate all files exist
            footprint_dir = output_dir / self.EXPECTED_FOOTPRINT_DIR
            model_dir = output_dir / self.EXPECTED_MODEL_DIR

            is_valid, validation_detail = self._validate_files_with_detail(
                symbol_output, footprint_dir, model_dir
            )

            if not is_valid:
                logger.error(
                    f"Validation failed for {lcsc_id}: {validation_detail}",
                    extra={"lcsc_id": lcsc_id, "reason": validation_detail},
                )
                return None

            logger.info(f"Successfully downloaded {lcsc_id}")
            # Return library info
            return ComponentLibrary(
                lcsc_id=lcsc_id,
                symbol_path=symbol_output,
                footprint_dir=footprint_dir,
                model_dir=model_dir,
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Download timeout for {lcsc_id} (exceeded {self.TIMEOUT_SECONDS}s)")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {lcsc_id}: {e}", exc_info=True)
            return None

    def download_components_parallel(
        self, lcsc_ids: list[str], max_workers: int = 10
    ) -> dict[str, Optional[ComponentLibrary]]:
        """Download libraries for multiple components in parallel.

        Args:
            lcsc_ids: List of JLCPCB part numbers
            max_workers: Maximum parallel downloads

        Returns:
            Dictionary mapping lcsc_id to ComponentLibrary (or None if failed)
        """
        results: dict[str, Optional[ComponentLibrary]] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_lcsc = {
                executor.submit(self.download_component, lcsc_id): lcsc_id for lcsc_id in lcsc_ids
            }

            completed = 0
            total = len(lcsc_ids)

            for future in as_completed(future_to_lcsc):
                lcsc_id = future_to_lcsc[future]
                completed += 1

                try:
                    result = future.result()
                    results[lcsc_id] = result
                    status = "✓" if result else "✗"
                    print(f"[{completed}/{total}] {lcsc_id}: {status}")
                except Exception as e:
                    print(f"[{completed}/{total}] {lcsc_id}: ERROR - {e}")
                    results[lcsc_id] = None

        return results

    def get_validated_libraries(
        self, lcsc_ids: list[str], max_workers: int = 10
    ) -> dict[str, ComponentLibrary]:
        """Download and return only validated libraries.

        Args:
            lcsc_ids: List of JLCPCB part numbers
            max_workers: Maximum parallel downloads

        Returns:
            Dictionary with only successfully validated libraries
        """
        all_results = self.download_components_parallel(lcsc_ids, max_workers)
        return {
            lcsc_id: lib
            for lcsc_id, lib in all_results.items()
            if lib is not None and lib.is_valid()
        }

    @staticmethod
    def _validate_files(symbol_path: Path, footprint_dir: Path, model_dir: Path) -> bool:
        """Validate that all library files exist and are accessible.

        CRITICAL: This checks all four validation conditions:
        1. Symbol file exists and is non-empty
        2. Footprint directory exists and has .kicad_mod files
        3. 3D model directory exists and has .step or .wrl files

        Args:
            symbol_path: Path to symbol file
            footprint_dir: Path to footprint directory
            model_dir: Path to 3D model directory

        Returns:
            True if all validations pass, False otherwise
        """
        is_valid, _ = LibraryDownloader._validate_files_with_detail(symbol_path, footprint_dir, model_dir)
        return is_valid

    @staticmethod
    def _validate_files_with_detail(
        symbol_path: Path, footprint_dir: Path, model_dir: Path
    ) -> tuple[bool, str]:
        """Validate that all library files exist and are accessible.

        Returns both validation result and a detail string explaining any failure.

        Args:
            symbol_path: Path to symbol file
            footprint_dir: Path to footprint directory
            model_dir: Path to 3D model directory

        Returns:
            Tuple of (is_valid, detail_string)
            - is_valid: True if all validations pass
            - detail_string: Empty string if valid, error reason if invalid
        """
        # Validation 1: Symbol file exists and non-empty
        if not symbol_path.exists():
            return False, "symbol file missing"
        if symbol_path.stat().st_size == 0:
            return False, "symbol file is empty"

        # Validation 2: Footprint directory exists and has files
        if not footprint_dir.exists():
            return False, "footprint directory missing"
        footprint_files = list(footprint_dir.glob("*.kicad_mod"))
        if not footprint_files:
            return False, "no .kicad_mod files found"

        # Validation 3: 3D model directory exists and has files
        if not model_dir.exists():
            return False, "3D model directory missing"
        model_files = list(model_dir.glob("*.step")) + list(model_dir.glob("*.wrl"))
        if not model_files:
            return False, "no .step or .wrl 3D model files found"

        return True, ""

    def cleanup_cache(self, older_than_hours: int = 24) -> int:
        """Remove cached libraries older than specified time.

        Args:
            older_than_hours: Remove cache older than this many hours

        Returns:
            Number of directories removed
        """
        import shutil
        import time

        if not self.cache_dir.exists():
            return 0

        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)
        removed_count = 0

        for lcsc_dir in self.cache_dir.iterdir():
            if not lcsc_dir.is_dir():
                continue

            # Check if directory is older than cutoff
            mtime = lcsc_dir.stat().st_mtime
            if mtime < cutoff_time:
                shutil.rmtree(lcsc_dir)
                removed_count += 1

        return removed_count
