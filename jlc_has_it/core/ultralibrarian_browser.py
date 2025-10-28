"""
Ultralibrarian Browser Launch

Opens the user's default browser to an Ultralibrarian part details page
with clear instructions for exporting and downloading KiCad libraries.
"""

import logging
import webbrowser
from typing import Optional
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)

ULTRALIBRARIAN_BASE_URL = "https://app.ultralibrarian.com"


def _validate_uuid(uuid_str: str) -> bool:
    """
    Validate that a string looks like a UUID.

    Args:
        uuid_str: String to validate

    Returns:
        True if string matches UUID pattern
    """
    # Standard UUID pattern: 8-4-4-4-12 hexadecimal digits
    uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
    return bool(re.match(uuid_pattern, uuid_str, re.IGNORECASE))


def open_ultralibrarian_part(
    uuid: str,
    mpn: str,
    manufacturer: Optional[str] = None,
    open_exports: bool = True,
) -> bool:
    """
    Open the Ultralibrarian part details page in the user's default browser.

    Displays clear step-by-step instructions for exporting and downloading.

    Args:
        uuid: The Ultralibrarian PartUniqueId (UUID)
        mpn: The MPN (for logging and user messages)
        manufacturer: Optional manufacturer name for complete URL (e.g., "Littelfuse")
        open_exports: If True, add ?open=exports parameters to pre-open export dialog

    Returns:
        True if browser was opened successfully, False otherwise

    Raises:
        ValueError: If UUID format is invalid
    """
    # Validate UUID format
    if not _validate_uuid(uuid):
        raise ValueError(f"Invalid UUID format: {uuid}")

    # Construct the URL with manufacturer and MPN if provided
    if manufacturer and mpn:
        # Replace spaces with dashes and URL-encode for safety
        mfr_encoded = quote(manufacturer.replace(" ", "-"), safe="")
        mpn_encoded = quote(mpn, safe="")

        # Build full URL with manufacturer and MPN
        url = f"{ULTRALIBRARIAN_BASE_URL}/details/{uuid}/{mfr_encoded}/{mpn_encoded}"

        # Optionally add export parameters to pre-open export dialog
        if open_exports:
            url += "?open=exports&exports=21&exports=42"
    else:
        # Fall back to UUID-only URL if manufacturer/MPN not provided
        url = f"{ULTRALIBRARIAN_BASE_URL}/details/{uuid}"

    logger.info(f"Opening Ultralibrarian part page: {mpn}")
    logger.info(f"URL: {url}")

    # Print instructions to user
    instructions = f"""
╔══════════════════════════════════════════════════════════════════╗
║                   ULTRALIBRARIAN EXPORT GUIDE                    ║
╚══════════════════════════════════════════════════════════════════╝

Part: {mpn}

Step 1: Click the "Export" button on the part page
Step 2: Select "KiCad v6+" format
Step 3: Select "3D Model (STEP)" format
Step 4: Wait for "Download" button to appear
Step 5: Click "Download" to save the file

Note: Your browser will automatically unzip the download to:
      ~/Downloads/ul_{mpn}/

Opening browser now...
"""

    print(instructions)

    # Attempt to open browser
    try:
        success = webbrowser.open(url)
        if success:
            logger.info(f"Successfully opened browser for {mpn}")
            return True
        else:
            logger.error("Failed to open browser (webbrowser.open returned False)")
            logger.info(f"You can open this URL manually: {url}")
            return False

    except Exception as e:
        logger.error(f"Exception while opening browser: {e}")
        logger.info(f"You can open this URL manually: {url}")
        return False


def construct_ultralibrarian_url(uuid: str) -> str:
    """
    Construct the Ultralibrarian part details URL from a UUID.

    Args:
        uuid: The Ultralibrarian PartUniqueId

    Returns:
        The full URL to the part details page

    Raises:
        ValueError: If UUID format is invalid
    """
    if not _validate_uuid(uuid):
        raise ValueError(f"Invalid UUID format: {uuid}")

    return f"{ULTRALIBRARIAN_BASE_URL}/details/{uuid}"
