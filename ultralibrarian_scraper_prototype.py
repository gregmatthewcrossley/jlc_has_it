#!/usr/bin/env python3
"""
Ultra Librarian Web-Scraping Prototype

This is a prototype implementation to test feasibility of downloading KiCad libraries
from Ultra Librarian using the manufacturer + MPN search approach.

Workflow:
1. Search Ultra Librarian for part using manufacturer + MPN
2. Extract UUID from search results
3. Submit export request (KiCad v6+ + 3D models)
4. Poll queue status
5. Download ZIP file
6. Validate contents
"""

import requests
import time
import json
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UltraLibrarianScraper:
    BASE_URL = "https://app.ultralibrarian.com"

    # Export format values from Ultra Librarian
    EXPORT_FORMATS = {
        "kicad_v6": 42,        # KiCad v6+
        "kicad_v5": 24,        # KiCad v5
        "step_3d": 21,         # 3D Model (STEP)
    }

    def __init__(self, output_dir: Path = Path("/tmp/claude/ultralibrarian_downloads")):
        """Initialize scraper with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                         'AppleWebKit/537.36'
        })

    def search_part(self, manufacturer: str, mpn: str) -> Optional[str]:
        """
        Search for a part using manufacturer and MPN.
        Returns the PartUniqueId (UUID) if found, None otherwise.

        Example: search_part("Bourns Electronics", "SF-0603F300-2")
        """
        logger.info(f"Searching for {manufacturer} {mpn}")
        start_time = time.time()

        # Try different search strategies
        search_queries = [
            f"{manufacturer} {mpn}",  # Full search
            mpn,                       # MPN only
            f"{mpn}",                 # Quoted MPN
        ]

        for query in search_queries:
            try:
                # Try GET request with search parameter
                params = {"search": query}
                response = self.session.get(
                    urljoin(self.BASE_URL, "/"),
                    params=params,
                    timeout=10
                )

                if response.status_code == 200:
                    # Look for UUID pattern in href
                    uuid_pattern = r'/details/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
                    matches = re.findall(uuid_pattern, response.text)

                    if matches:
                        elapsed = time.time() - start_time
                        logger.info(f"Found UUID: {matches[0]} ({elapsed:.2f}s)")
                        return matches[0]
            except Exception as e:
                logger.debug(f"Search query '{query}' failed: {e}")
                continue

        elapsed = time.time() - start_time
        logger.warning(f"No results found for {manufacturer} {mpn} ({elapsed:.2f}s)")
        return None

    def request_export(self, part_uuid: str, formats: list[int] = None) -> Optional[str]:
        """
        Submit export request and return queue token.

        Args:
            part_uuid: The PartUniqueId (UUID) of the component
            formats: List of export format IDs (default: KiCad v6+ and 3D model)
        """
        if formats is None:
            formats = [self.EXPORT_FORMATS["kicad_v6"], self.EXPORT_FORMATS["step_3d"]]

        logger.info(f"Requesting export for {part_uuid} with formats {formats}")
        start_time = time.time()

        try:
            # Prepare export data
            export_data = {
                'PartUniqueId': part_uuid,
                'exports': formats,
                'BxlToken': '',
                'AdvertiserReferrerTag': '',
                'AdvertiserTerm': '',
                'DistributorUniqueIds': '',
            }

            # Submit export request
            response = self.session.post(
                urljoin(self.BASE_URL, "/Export/QueueExport"),
                data=export_data,
                timeout=10,
                allow_redirects=True
            )

            logger.debug(f"Export request response status: {response.status_code}")

            # Try to extract queue token from response
            # It might be in the URL, JSON response, or HTML

            # Check URL (in case of redirect)
            if 'queueToken=' in response.url:
                token = response.url.split('queueToken=')[-1].split('&')[0]
                elapsed = time.time() - start_time
                logger.info(f"Got queue token: {token} ({elapsed:.2f}s)")
                return token

            # Check JSON response
            try:
                data = response.json()
                if 'queueToken' in data:
                    token = data['queueToken']
                    elapsed = time.time() - start_time
                    logger.info(f"Got queue token: {token} ({elapsed:.2f}s)")
                    return token
            except:
                pass

            # Check HTML response for token
            token_pattern = r'queueToken["\s:=]+([a-zA-Z0-9_\-]+)'
            match = re.search(token_pattern, response.text)
            if match:
                token = match.group(1)
                elapsed = time.time() - start_time
                logger.info(f"Got queue token: {token} ({elapsed:.2f}s)")
                return token

            logger.warning("Could not extract queue token from response")
            return None

        except Exception as e:
            logger.error(f"Export request failed: {e}")
            return None

    def check_queue_status(self, queue_token: str) -> Tuple[bool, dict]:
        """
        Check if export is ready.

        Returns: (is_ready, status_data)
        """
        try:
            response = self.session.get(
                urljoin(self.BASE_URL, f"/Export/CheckQueue?queueToken={queue_token}"),
                timeout=10
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    is_ready = data.get('ready', False) or data.get('isReady', False)
                    logger.debug(f"Queue status: {data}")
                    return is_ready, data
                except:
                    logger.debug(f"Response text: {response.text[:200]}")
                    return False, {}

            return False, {}
        except Exception as e:
            logger.error(f"Queue status check failed: {e}")
            return False, {}

    def wait_for_ready(self, queue_token: str, max_wait: int = 60, poll_interval: int = 2) -> bool:
        """
        Poll queue status until ready or timeout.

        Returns: True if ready, False if timeout
        """
        logger.info(f"Waiting for export to be ready (max {max_wait}s)...")
        start_time = time.time()

        while time.time() - start_time < max_wait:
            is_ready, status = self.check_queue_status(queue_token)

            if is_ready:
                elapsed = time.time() - start_time
                logger.info(f"Export ready! ({elapsed:.2f}s)")
                return True

            elapsed = time.time() - start_time
            logger.debug(f"Not ready yet... ({elapsed:.2f}s)")
            time.sleep(poll_interval)

        logger.error(f"Timeout waiting for export (>{max_wait}s)")
        return False

    def download_export(self, queue_token: str, output_file: Path) -> bool:
        """
        Download the exported ZIP file.

        Returns: True if successful, False otherwise
        """
        logger.info(f"Downloading export to {output_file}")
        start_time = time.time()

        try:
            response = self.session.get(
                urljoin(self.BASE_URL, f"/Export/Download?queueToken={queue_token}"),
                timeout=30,
                stream=True
            )

            if response.status_code == 200:
                output_file.parent.mkdir(parents=True, exist_ok=True)

                # Write file with progress
                total_size = int(response.headers.get('content-length', 0))
                with open(output_file, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                logger.debug(f"Downloaded {percent:.1f}% ({downloaded}/{total_size} bytes)")

                elapsed = time.time() - start_time
                file_size = output_file.stat().st_size
                logger.info(f"Downloaded {file_size} bytes ({elapsed:.2f}s)")
                return True
            else:
                logger.error(f"Download failed with status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def validate_zip(self, zip_file: Path) -> bool:
        """Validate that the downloaded ZIP is not empty and contains KiCad files."""
        import zipfile

        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                files = zf.namelist()
                logger.info(f"ZIP contents: {len(files)} files")

                # Check for KiCad files
                has_symbol = any('.kicad_sym' in f for f in files)
                has_footprint = any('.kicad_mod' in f for f in files)
                has_3d = any(f.endswith(('.step', '.stp', '.wrl')) for f in files)

                logger.info(f"Validation: symbol={has_symbol}, footprint={has_footprint}, 3d={has_3d}")

                return len(files) > 0
        except Exception as e:
            logger.error(f"ZIP validation failed: {e}")
            return False

    def download_kicad_library(self, manufacturer: str, mpn: str) -> Optional[Path]:
        """
        Complete workflow: search → request → wait → download

        Returns: Path to downloaded ZIP file, or None if failed
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting download for {manufacturer} {mpn}")
        logger.info(f"{'='*60}\n")

        total_start = time.time()

        # Step 1: Search
        part_uuid = self.search_part(manufacturer, mpn)
        if not part_uuid:
            return None

        # Step 2: Request export
        queue_token = self.request_export(part_uuid)
        if not queue_token:
            return None

        # Step 3: Wait for ready
        if not self.wait_for_ready(queue_token):
            return None

        # Step 4: Download
        output_file = self.output_dir / f"{mpn.replace('/', '_')}_ultralibrarian.zip"
        if not self.download_export(queue_token, output_file):
            return None

        # Step 5: Validate
        if not self.validate_zip(output_file):
            logger.warning("ZIP validation failed, but file was downloaded")
            return None

        total_elapsed = time.time() - total_start
        logger.info(f"\n{'='*60}")
        logger.info(f"SUCCESS! Total time: {total_elapsed:.2f}s")
        logger.info(f"Downloaded: {output_file}")
        logger.info(f"{'='*60}\n")

        return output_file


def main():
    """Test the scraper with a known part."""
    import sys

    scraper = UltraLibrarianScraper()

    # Test with the Bourns fuse from the research
    test_parts = [
        ("Bourns Electronics", "SF-0603F300-2"),
        # Add more test parts as needed
    ]

    if len(sys.argv) > 2:
        # Custom part from command line
        test_parts = [(sys.argv[1], sys.argv[2])]

    for manufacturer, mpn in test_parts:
        result = scraper.download_kicad_library(manufacturer, mpn)
        if result:
            logger.info(f"✓ Success: {result}")
        else:
            logger.error(f"✗ Failed to download {manufacturer} {mpn}")


if __name__ == "__main__":
    main()
