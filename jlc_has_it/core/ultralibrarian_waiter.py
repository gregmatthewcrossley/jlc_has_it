"""
Ultralibrarian Download Detection and Wait Logic

Monitors the user's Downloads directory for Ultralibrarian exports and waits
for downloads to complete. Provides polling with timeout and progress feedback.
"""

import logging
import time
from pathlib import Path
from typing import Optional
from .ultralibrarian_detector import (
    find_ultralibrarian_folders,
    validate_folder_structure,
    extract_component_files,
)

logger = logging.getLogger(__name__)


def wait_for_ultralibrarian_download(
    mpn: str,
    timeout_seconds: int = 300,
    poll_interval: float = 2.0,
    stability_wait: float = 2.0,
) -> Optional[Path]:
    """
    Wait for an Ultralibrarian download folder to appear and be ready.

    Polls the Downloads directory looking for a folder matching ul_<MPN>/.
    Once found, waits for the folder contents to stabilize before returning.

    Provides progress feedback to stdout so user knows what's happening.

    Args:
        mpn: The MPN to wait for (folder will be ul_<MPN>/)
        timeout_seconds: Maximum time to wait in seconds (default: 300 = 5 min)
        poll_interval: How often to check Downloads folder in seconds (default: 2.0)
        stability_wait: Time to wait for no file changes before considering download
                       complete, in seconds (default: 2.0)

    Returns:
        Path to the Ultralibrarian folder if found and valid, None if timeout

    Raises:
        ValueError: If MPN is empty or None
    """
    if not mpn or not isinstance(mpn, str):
        raise ValueError("MPN must be a non-empty string")

    expected_folder_name = f"ul_{mpn}"
    start_time = time.time()

    logger.info(f"Waiting for Ultralibrarian download: {expected_folder_name}")
    logger.info(f"(timeout: {timeout_seconds}s, will check every {poll_interval}s)")

    # Print user-friendly progress message
    print(f"⏳ Waiting for {expected_folder_name} to download...")
    print(f"   (timeout: {timeout_seconds}s, checking every {poll_interval}s)")

    folder_found_time = None
    last_stable_time = None
    last_folder_mtime = None
    last_progress_print = 0

    while True:
        elapsed = time.time() - start_time

        # Check timeout
        if elapsed > timeout_seconds:
            logger.error(f"Timeout waiting for {expected_folder_name} "
                        f"(waited {elapsed:.1f}s)")
            print(f"⏱ Timeout: No download detected after {timeout_seconds}s")
            print(f"   Please ensure you exported the files from Ultralibrarian")
            return None

        # Print progress every 5 seconds (or at least show at 2-second intervals)
        if elapsed - last_progress_print >= 5.0 or (elapsed - last_progress_print >= 2.0 and folder_found_time is not None):
            remaining = timeout_seconds - elapsed
            print(f"   ⏳ Waiting ({elapsed:.0f}s elapsed, {remaining:.0f}s remaining)...")
            last_progress_print = elapsed

        # Look for the folder
        folders = find_ultralibrarian_folders(max_age_seconds=timeout_seconds)

        # Find the folder matching this MPN
        target_folder = None
        for folder in folders:
            if folder.name == expected_folder_name:
                target_folder = folder
                break

        if target_folder is None:
            # Folder not found yet
            if folder_found_time is None:
                # Haven't found it yet
                logger.debug(f"[{elapsed:.1f}s] Folder not found yet...")
            else:
                # This shouldn't happen but handle it gracefully
                logger.warning(f"Folder disappeared: {expected_folder_name}")
                folder_found_time = None
                last_stable_time = None
                last_folder_mtime = None

            time.sleep(poll_interval)
            continue

        # Folder found!
        if folder_found_time is None:
            folder_found_time = time.time()
            logger.info(f"[{elapsed:.1f}s] ✓ Found {expected_folder_name}")
            print(f"✓ Download detected! ({elapsed:.0f}s)")

        # Check if structure is valid
        if not validate_folder_structure(target_folder):
            logger.debug(f"[{elapsed:.1f}s] Folder structure not yet complete...")
            time.sleep(poll_interval)
            continue

        # Structure is valid. Now check if files are stable.
        current_mtime = target_folder.stat().st_mtime

        if last_folder_mtime is None:
            # First time checking stability
            last_folder_mtime = current_mtime
            last_stable_time = time.time()
            logger.debug(f"[{elapsed:.1f}s] Structure complete, checking stability...")
            time.sleep(poll_interval)
            continue

        if current_mtime != last_folder_mtime:
            # Files are still being modified
            last_folder_mtime = current_mtime
            last_stable_time = time.time()
            logger.debug(f"[{elapsed:.1f}s] Files still being written...")
            time.sleep(poll_interval)
            continue

        # Files haven't changed since last check
        stable_duration = time.time() - last_stable_time

        if stable_duration < stability_wait:
            # Wait longer for stability
            logger.debug(f"[{elapsed:.1f}s] Waiting for stability... "
                        f"({stable_duration:.1f}s/{stability_wait}s)")
            time.sleep(poll_interval)
            continue

        # Folder is complete and stable!
        logger.info(f"[{elapsed:.1f}s] ✓ Download complete and ready")
        print(f"✓ Download complete and stable ({elapsed:.0f}s)")

        # Final validation: extract component files
        component_info = extract_component_files(target_folder)

        if component_info is None:
            logger.error(f"Failed to extract component info from {target_folder}")
            print("✗ Error: Could not extract component info from download")
            return None

        if not component_info['valid']:
            logger.warning(f"Incomplete component library detected:")
            logger.warning(f"  - Symbol: {component_info['symbol_path'] is not None}")
            logger.warning(f"  - Footprints: {len(component_info['footprints'])} file(s)")
            logger.warning(f"  - 3D Model: {component_info['model_path'] is not None}")
            logger.warning(f"Please try downloading again from Ultralibrarian")
            print("✗ Incomplete: Please download all files (Symbol, Footprints, 3D Model)")
            return None

        logger.info(f"✓ Validated: symbol, {len(component_info['footprints'])} "
                   f"footprint(s), and 3D model found")
        print(f"✓ Files validated (symbol, {len(component_info['footprints'])} footprint(s), 3D model)")
        print("   Processing files into project...")

        return target_folder


def check_for_existing_download(mpn: str) -> Optional[Path]:
    """
    Check if a download for the given MPN already exists in Downloads.

    Useful for avoiding re-downloading if the user already has the file.

    Args:
        mpn: The MPN to check for

    Returns:
        Path to the Ultralibrarian folder if found, None otherwise
    """
    expected_folder_name = f"ul_{mpn}"
    folders = find_ultralibrarian_folders(max_age_seconds=86400)  # 24 hours

    for folder in folders:
        if folder.name == expected_folder_name:
            if validate_folder_structure(folder):
                component_info = extract_component_files(folder)
                if component_info and component_info['valid']:
                    logger.info(f"Found existing download: {folder}")
                    return folder

    return None
