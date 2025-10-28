"""
Ultralibrarian Downloads Detector

Detects and validates Ultralibrarian component libraries in the user's
Downloads directory. Ultralibrarian exports are auto-unzipped by the browser,
creating folders with the structure: ul_<MPN>/KiCADv6/footprints.pretty/

This module provides utilities to:
- Find newly created Ultralibrarian download folders
- Validate the expected folder structure
- Extract paths to symbol, footprint, and 3D model files
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


def get_downloads_directory() -> Path:
    """
    Get the platform-specific Downloads directory path.

    Returns:
        Path to user's Downloads directory

    Raises:
        RuntimeError: If Downloads directory doesn't exist
    """
    downloads_dir = Path.home() / "Downloads"

    if not downloads_dir.exists():
        raise RuntimeError(f"Downloads directory not found: {downloads_dir}")

    return downloads_dir


def find_ultralibrarian_folders(max_age_seconds: int = 300) -> List[Path]:
    """
    Find Ultralibrarian download folders in the Downloads directory.

    Looks for folders matching the pattern: ul_<MPN>/

    Args:
        max_age_seconds: Only return folders created/modified within this many seconds
                        (default: 300 seconds = 5 minutes)

    Returns:
        List of Path objects to Ultralibrarian folders, sorted by modification time
        (newest first). Returns empty list if no folders found.
    """
    try:
        downloads_dir = get_downloads_directory()
    except RuntimeError:
        return []

    ul_folders = []
    current_time = time.time()

    for folder in downloads_dir.iterdir():
        if not folder.is_dir():
            continue

        # Check if folder matches Ultralibrarian pattern
        if not folder.name.startswith("ul_"):
            continue

        # Check age
        folder_mtime = folder.stat().st_mtime
        age_seconds = current_time - folder_mtime

        if age_seconds > max_age_seconds:
            logger.debug(f"Skipping {folder.name} - too old ({age_seconds:.0f}s)")
            continue

        ul_folders.append(folder)
        logger.debug(f"Found Ultralibrarian folder: {folder.name} ({age_seconds:.1f}s old)")

    # Sort by modification time (newest first)
    ul_folders.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return ul_folders


def validate_folder_structure(folder_path: Path) -> bool:
    """
    Validate that a folder has the expected Ultralibrarian structure.

    Expected structure:
        ul_<MPN>/
        └── KiCADv6/
            └── footprints.pretty/
                ├── *.kicad_mod
                ├── *.kicad_sym
                └── *.step

    Args:
        folder_path: Path to folder to validate

    Returns:
        True if structure is valid, False otherwise
    """
    if not folder_path.exists() or not folder_path.is_dir():
        logger.debug(f"Folder does not exist: {folder_path}")
        return False

    # Check for KiCADv6 subdirectory
    kicad_dir = folder_path / "KiCADv6"
    if not kicad_dir.exists() or not kicad_dir.is_dir():
        logger.debug(f"Missing KiCADv6 directory in {folder_path}")
        return False

    # Check for footprints.pretty subdirectory
    footprints_dir = kicad_dir / "footprints.pretty"
    if not footprints_dir.exists() or not footprints_dir.is_dir():
        logger.debug(f"Missing footprints.pretty directory in {kicad_dir}")
        return False

    logger.debug(f"Folder structure valid: {folder_path}")
    return True


def extract_component_files(folder_path: Path) -> Optional[Dict[str, any]]:
    """
    Extract paths to symbol, footprint, and 3D model files from an Ultralibrarian folder.

    Args:
        folder_path: Path to the Ultralibrarian folder (ul_<MPN>/)

    Returns:
        Dictionary with keys:
        - 'mpn': Extracted MPN from folder name
        - 'symbol_path': Path to .kicad_sym file, or None if not found
        - 'footprints': List of Path objects to .kicad_mod files
        - 'model_path': Path to .step file, or None if not found
        - 'valid': Boolean indicating if all required files were found

        Returns None if folder structure is invalid
    """
    if not validate_folder_structure(folder_path):
        return None

    # Extract MPN from folder name (ul_<MPN>/)
    mpn = folder_path.name[3:]  # Remove "ul_" prefix

    footprints_dir = folder_path / "KiCADv6" / "footprints.pretty"

    # Find symbol file (*.kicad_sym)
    symbol_files = list(footprints_dir.glob("*.kicad_sym"))
    symbol_path = symbol_files[0] if symbol_files else None

    if symbol_path:
        logger.debug(f"Found symbol file: {symbol_path.name}")
    else:
        logger.warning(f"No symbol file found in {footprints_dir}")

    # Find all footprint files (*.kicad_mod)
    footprint_files = sorted(footprints_dir.glob("*.kicad_mod"))

    if footprint_files:
        logger.debug(f"Found {len(footprint_files)} footprint file(s): "
                    f"{[f.name for f in footprint_files]}")
    else:
        logger.warning(f"No footprint files found in {footprints_dir}")

    # Find 3D model file (*.step)
    model_files = list(footprints_dir.glob("*.step"))
    model_path = model_files[0] if model_files else None

    if model_path:
        logger.debug(f"Found 3D model file: {model_path.name}")
    else:
        logger.warning(f"No STEP model file found in {footprints_dir}")

    # Determine if we have all required components
    has_all_components = bool(symbol_path and footprint_files and model_path)

    return {
        'mpn': mpn,
        'folder_path': folder_path,
        'symbol_path': symbol_path,
        'footprints': footprint_files,
        'model_path': model_path,
        'valid': has_all_components,
    }


def find_and_validate_latest() -> Optional[Dict[str, any]]:
    """
    Find the most recently created Ultralibrarian folder and validate it.

    This is a convenience function combining find_ultralibrarian_folders() and
    extract_component_files() for the common case of waiting for a single download.

    Returns:
        Dictionary from extract_component_files() for the latest folder, or None
        if no valid Ultralibrarian folders found
    """
    folders = find_ultralibrarian_folders()

    if not folders:
        logger.debug("No Ultralibrarian folders found")
        return None

    latest = folders[0]  # Already sorted by modification time (newest first)
    logger.info(f"Found latest Ultralibrarian folder: {latest.name}")

    result = extract_component_files(latest)

    if result is None:
        logger.warning(f"Failed to extract components from {latest.name}")
        return None

    if not result['valid']:
        logger.warning(f"Incomplete component library in {latest.name}: "
                      f"symbol={result['symbol_path'] is not None}, "
                      f"footprints={len(result['footprints'])} files, "
                      f"model={result['model_path'] is not None}")

    return result
