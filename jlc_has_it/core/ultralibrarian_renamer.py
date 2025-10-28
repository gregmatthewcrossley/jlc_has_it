"""
Ultralibrarian Symbol File Renaming

Ultralibrarian generates symbol files with timestamp-based names like
"2025-10-28_14-26-29.kicad_sym". This module provides utilities to rename
them to MPN-based names for better readability in KiCad library browser.

Example:
    2025-10-28_14-26-29.kicad_sym → SF-0603F300-2.kicad_sym
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def sanitize_mpn_for_filename(mpn: str) -> str:
    """
    Sanitize an MPN string to make it safe for use as a filename.

    JLCPCB part numbers may contain characters that are valid for filenames
    on most systems, but we want to be conservative.

    Args:
        mpn: The MPN string (e.g., "SF-0603F300-2" or with special chars)

    Returns:
        Sanitized MPN suitable for use as filename
    """
    # Replace problematic characters with underscores
    # This includes: / \ : * ? " < > |
    problematic_chars = {
        '/': '_',
        '\\': '_',
        ':': '_',
        '*': '_',
        '?': '_',
        '"': '_',
        '<': '_',
        '>': '_',
        '|': '_',
    }

    sanitized = mpn
    for char, replacement in problematic_chars.items():
        sanitized = sanitized.replace(char, replacement)

    # Remove leading/trailing whitespace
    sanitized = sanitized.strip()

    return sanitized


def rename_symbol_file(symbol_path: Path, mpn: str) -> Path:
    """
    Rename a symbol file from its timestamp-based name to MPN-based name.

    Args:
        symbol_path: Path to the .kicad_sym file to rename
        mpn: The MPN to use in the new filename

    Returns:
        Path to the renamed file

    Raises:
        FileNotFoundError: If the symbol file doesn't exist
        PermissionError: If file cannot be read or written
        ValueError: If the file is not a .kicad_sym file
        OSError: If the rename operation fails
    """
    symbol_path = Path(symbol_path)

    # Validate file exists
    if not symbol_path.exists():
        raise FileNotFoundError(f"Symbol file not found: {symbol_path}")

    # Validate it's a directory
    if not symbol_path.is_file():
        raise ValueError(f"Path is not a file: {symbol_path}")

    # Validate it's a .kicad_sym file
    if symbol_path.suffix != '.kicad_sym':
        raise ValueError(f"File is not a .kicad_sym file: {symbol_path}")

    # Validate file is readable
    if not os.access(symbol_path, os.R_OK):
        raise PermissionError(f"Symbol file is not readable: {symbol_path}")

    # Construct new filename
    sanitized_mpn = sanitize_mpn_for_filename(mpn)
    new_filename = f"{sanitized_mpn}.kicad_sym"
    new_path = symbol_path.parent / new_filename

    # Handle case where file already exists
    if new_path.exists():
        if new_path.samefile(symbol_path):
            # File is already correctly named
            logger.info(f"Symbol file already has correct name: {new_filename}")
            return new_path

        # Different file exists with target name
        logger.warning(f"File already exists with target name: {new_path}")
        logger.warning(f"Keeping original file: {symbol_path}")
        return symbol_path

    # Perform the rename
    try:
        symbol_path.rename(new_path)
        logger.info(f"Renamed symbol file: {symbol_path.name} → {new_filename}")
        return new_path
    except OSError as e:
        logger.error(f"Failed to rename symbol file: {e}")
        raise


# Import os at module level for os.access check
import os
