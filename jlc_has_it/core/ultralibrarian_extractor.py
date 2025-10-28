"""
Ultralibrarian Library Extraction to KiCad Project

Extracts component files from Ultralibrarian downloads and integrates them
into a KiCad project's library structure.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional, Dict
from .ultralibrarian_detector import extract_component_files
from .ultralibrarian_renamer import rename_symbol_file
from .kicad.project import ProjectConfig

logger = logging.getLogger(__name__)


def extract_to_project(
    ul_folder: Path,
    project_dir: Path,
    mpn: str,
    cleanup: bool = True,
) -> bool:
    """
    Extract Ultralibrarian component files to a KiCad project library.

    Performs the following steps:
    1. Validate Ultralibrarian folder structure
    2. Rename symbol file from timestamp to MPN-based name
    3. Copy symbol file to project's libraries/ directory
    4. Copy footprints to project's libraries/footprints.pretty/ directory
    5. Copy 3D model to project's libraries/3d_models/ directory
    6. Update library tables (sym-lib-table, fp-lib-table)
    7. Optionally clean up the original Ultralibrarian folder

    Args:
        ul_folder: Path to the Ultralibrarian download folder (ul_<MPN>/)
        project_dir: Path to the KiCad project directory
        mpn: The MPN (for symbol file naming and library table entries)
        cleanup: If True, delete the Ultralibrarian folder after success (default: True)

    Returns:
        True if extraction was successful, False otherwise

    Raises:
        ValueError: If paths are invalid or folder structure is wrong
        FileNotFoundError: If required files are missing
    """
    ul_folder = Path(ul_folder)
    project_dir = Path(project_dir)

    # Validate inputs
    if not ul_folder.exists():
        raise FileNotFoundError(f"Ultralibrarian folder not found: {ul_folder}")

    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    logger.info(f"Extracting {mpn} to project: {project_dir}")

    # Extract component file info
    component_info = extract_component_files(ul_folder)

    if component_info is None:
        logger.error(f"Invalid Ultralibrarian folder structure: {ul_folder}")
        return False

    if not component_info['valid']:
        logger.error(f"Incomplete component library in {ul_folder.name}")
        logger.error(f"  Symbol: {component_info['symbol_path'] is not None}")
        logger.error(f"  Footprints: {len(component_info['footprints'])} file(s)")
        logger.error(f"  3D Model: {component_info['model_path'] is not None}")
        return False

    # Get project configuration
    try:
        project_config = ProjectConfig(project_dir)
    except ValueError as e:
        logger.error(f"Invalid KiCad project: {e}")
        return False

    # Create library directories
    try:
        symbol_dir, footprint_dir = project_config.create_library_directories()
        model_dir = project_dir / "libraries" / "3d_models"
        model_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created library directories: {symbol_dir}, {footprint_dir}, {model_dir}")
    except Exception as e:
        logger.error(f"Failed to create library directories: {e}")
        return False

    # Step 1: Rename and copy symbol file
    symbol_path = component_info['symbol_path']
    try:
        renamed_symbol_path = rename_symbol_file(symbol_path, mpn)
        target_symbol_path = symbol_dir / renamed_symbol_path.name

        shutil.copy2(renamed_symbol_path, target_symbol_path)
        logger.info(f"✓ Copied symbol: {renamed_symbol_path.name} → {target_symbol_path}")
    except Exception as e:
        logger.error(f"Failed to copy symbol file: {e}")
        return False

    # Step 2: Copy footprints
    footprint_files = component_info['footprints']
    try:
        for footprint_file in footprint_files:
            target_footprint_path = footprint_dir / footprint_file.name
            shutil.copy2(footprint_file, target_footprint_path)
            logger.debug(f"✓ Copied footprint: {footprint_file.name}")

        logger.info(f"✓ Copied {len(footprint_files)} footprint file(s)")
    except Exception as e:
        logger.error(f"Failed to copy footprint files: {e}")
        return False

    # Step 3: Copy 3D model
    model_path = component_info['model_path']
    try:
        target_model_path = model_dir / model_path.name
        shutil.copy2(model_path, target_model_path)
        logger.info(f"✓ Copied 3D model: {model_path.name}")
    except Exception as e:
        logger.error(f"Failed to copy 3D model: {e}")
        return False

    # Step 4: Update library tables
    try:
        # Add symbol library
        symbol_lib_name = f"jlc-{mpn}"
        symbol_lib_path = target_symbol_path.relative_to(project_dir)
        project_config.add_symbol_library(
            name=symbol_lib_name,
            lib_path=symbol_lib_path,
            description=f"JLCPCB component: {mpn}",
        )
        logger.info(f"✓ Updated symbol library table: {symbol_lib_name}")

        # Add footprint library
        fp_lib_name = f"jlc-{mpn}"
        fp_lib_path = footprint_dir.relative_to(project_dir)
        project_config.add_footprint_library(
            name=fp_lib_name,
            lib_path=fp_lib_path,
            description=f"JLCPCB footprints: {mpn}",
        )
        logger.info(f"✓ Updated footprint library table: {fp_lib_name}")
    except Exception as e:
        logger.error(f"Failed to update library tables: {e}")
        return False

    # Step 5: Clean up (optional)
    if cleanup:
        try:
            shutil.rmtree(ul_folder)
            logger.info(f"✓ Cleaned up: {ul_folder}")
        except Exception as e:
            logger.warning(f"Failed to clean up {ul_folder}: {e}")
            # Don't fail the entire operation if cleanup fails

    logger.info(f"✓ Successfully extracted {mpn} to {project_dir}")
    return True


def extract_multiple(
    ul_folders: list[Path],
    project_dir: Path,
    mpn_list: list[str],
    cleanup: bool = True,
) -> Dict[str, bool]:
    """
    Extract multiple Ultralibrarian components to a KiCad project.

    Args:
        ul_folders: List of Ultralibrarian folder paths
        project_dir: Path to the KiCad project directory
        mpn_list: List of MPNs corresponding to ul_folders
        cleanup: If True, delete folders after successful extraction

    Returns:
        Dictionary mapping MPN to success status
    """
    if len(ul_folders) != len(mpn_list):
        raise ValueError("ul_folders and mpn_list must have same length")

    results = {}

    for ul_folder, mpn in zip(ul_folders, mpn_list):
        try:
            success = extract_to_project(ul_folder, project_dir, mpn, cleanup=cleanup)
            results[mpn] = success
        except Exception as e:
            logger.error(f"Failed to extract {mpn}: {e}")
            results[mpn] = False

    return results
