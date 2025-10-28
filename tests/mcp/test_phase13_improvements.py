"""
Tests for Phase 13 improvements: routing, URLs, and progress feedback.
Tests for tasks 13-004, 13-005, 13-006.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from jlc_has_it.mcp.tools import JLCTools


class TestTask13004RouteToUltralibrarian:
    """Tests for task 13-004: Route add_to_project to add_from_ultralibrarian."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.tools = JLCTools(self.mock_db)

    def test_add_to_project_detects_ultralibrarian_only_component(self):
        """Should detect when component is Ultralibrarian-only from cache."""
        # Set up cache to indicate C207003 is Ultralibrarian-only
        self.tools._library_source_cache["C207003"] = {
            "source": "ultralibrarian",
            "uuid": "test-uuid",
            "manufacturer": "Littelfuse",
            "mpn": "0501010.WR1",
        }

        # Mock download to fail (simulating EasyEDA not available)
        self.tools.downloader.download_component = MagicMock(return_value=None)

        # Mock project detection
        with patch("jlc_has_it.mcp.tools.ProjectConfig.find_project_root", return_value=Path("/tmp/test")):
            with patch("jlc_has_it.mcp.tools.ProjectConfig"):
                result = self.tools.add_to_project("C207003")

        # Should return routing suggestion instead of generic error
        assert result["success"] is False
        assert "Ultralibrarian" in result["error"]
        assert result.get("suggestion") == "add_from_ultralibrarian"
        assert result.get("manufacturer") == "Littelfuse"
        assert result.get("mpn") == "0501010.WR1"

    def test_add_to_project_includes_routing_info(self):
        """Should include manufacturer and MPN in routing response."""
        self.tools._library_source_cache["C41367232"] = {
            "source": "ultralibrarian",
            "uuid": "another-uuid",
            "manufacturer": "BHFUSE",
            "mpn": "BSMD1206C-2100T",
        }

        self.tools.downloader.download_component = MagicMock(return_value=None)

        with patch("jlc_has_it.mcp.tools.ProjectConfig.find_project_root", return_value=Path("/tmp/test")):
            with patch("jlc_has_it.mcp.tools.ProjectConfig"):
                result = self.tools.add_to_project("C41367232")

        assert "BHFUSE" in result["error"]
        assert "BSMD1206C-2100T" in result["error"]

    def test_add_to_project_works_normally_without_cache(self):
        """Should work normally if component not in cache (no routing needed)."""
        # No cache entry for this component
        self.tools.downloader.download_component = MagicMock(return_value=None)

        with patch("jlc_has_it.mcp.tools.ProjectConfig.find_project_root", return_value=Path("/tmp/test")):
            with patch("jlc_has_it.mcp.tools.ProjectConfig"):
                result = self.tools.add_to_project("C12345")

        # Should return generic error (no routing info)
        assert result["success"] is False
        assert "Failed to download valid library" in result["error"]
        assert "suggestion" not in result

    def test_search_populates_library_source_cache(self):
        """Should populate cache when search validates libraries."""
        mock_comp = MagicMock()
        mock_comp.lcsc = "207003"
        mock_comp.description = "Littelfuse Fuse"
        mock_comp.manufacturer = "Littelfuse"
        mock_comp.mfr = "0501010.WR1"
        mock_comp.category = "Fuses"
        mock_comp.stock = 1000
        mock_comp.price = 0.11
        mock_comp.basic = True

        with patch("jlc_has_it.mcp.tools.ComponentSearch") as mock_search_class:
            mock_search = MagicMock()
            mock_search.search.return_value = [mock_comp]
            mock_search_class.return_value = mock_search

            # Mock Ultralibrarian check to return UUID
            with patch.object(self.tools, "_check_ultralibrarian_availability", return_value="test-uuid"):
                result = self.tools.search_components(
                    query="fuse",
                    validate_libraries=True,
                    validation_candidates=1,
                )

        # Check that cache was populated
        assert "C207003" in self.tools._library_source_cache
        cached = self.tools._library_source_cache["C207003"]
        assert cached["source"] == "ultralibrarian"
        assert cached["manufacturer"] == "Littelfuse"
        assert cached["mpn"] == "0501010.WR1"
        assert cached["uuid"] == "test-uuid"

    def test_search_results_include_ultralibrarian_fields(self):
        """Search results should include ultralibrarian_manufacturer and ultralibrarian_mpn."""
        mock_comp = MagicMock()
        mock_comp.lcsc = "207003"
        mock_comp.description = "Test Fuse"
        mock_comp.manufacturer = "Littelfuse"
        mock_comp.mfr = "0501010.WR1"
        mock_comp.category = "Fuses"
        mock_comp.stock = 1000
        mock_comp.price = 0.11
        mock_comp.basic = True

        with patch("jlc_has_it.mcp.tools.ComponentSearch") as mock_search_class:
            mock_search = MagicMock()
            mock_search.search.return_value = [mock_comp]
            mock_search_class.return_value = mock_search

            with patch.object(self.tools, "_check_ultralibrarian_availability", return_value="test-uuid"):
                result = self.tools.search_components(
                    query="fuse",
                    validate_libraries=True,
                    validation_candidates=1,
                )

        # Check result fields
        assert len(result["results"]) > 0
        first_result = result["results"][0]
        assert "ultralibrarian_manufacturer" in first_result
        assert "ultralibrarian_mpn" in first_result
        assert first_result["ultralibrarian_manufacturer"] == "Littelfuse"
        assert first_result["ultralibrarian_mpn"] == "0501010.WR1"


class TestTask13005UltraLibrarianURLs:
    """Tests for task 13-005: Build complete Ultralibrarian URLs."""

    def test_open_ultralibrarian_part_builds_complete_url(self):
        """Should build complete URL with manufacturer and MPN."""
        from jlc_has_it.core.ultralibrarian_browser import open_ultralibrarian_part

        with patch("webbrowser.open") as mock_browser:
            mock_browser.return_value = True

            open_ultralibrarian_part(
                uuid="44b282e2-2a18-11ee-9288-0ae0a3b49db5",
                mpn="0501010.WR1",
                manufacturer="Littelfuse",
                open_exports=True,
            )

            # Check that browser was called with complete URL
            mock_browser.assert_called_once()
            url = mock_browser.call_args[0][0]
            assert "44b282e2-2a18-11ee-9288-0ae0a3b49db5" in url
            assert "Littelfuse" in url or "littelfuse" in url.lower()
            assert "0501010" in url
            assert "?open=exports" in url

    def test_url_includes_export_parameters(self):
        """URL should include export dialog parameters."""
        from jlc_has_it.core.ultralibrarian_browser import open_ultralibrarian_part

        with patch("webbrowser.open") as mock_browser:
            mock_browser.return_value = True

            open_ultralibrarian_part(
                uuid="44b282e2-2a18-11ee-9288-0ae0a3b49db5",
                mpn="TEST-001",
                manufacturer="TestMfg",
                open_exports=True,
            )

            url = mock_browser.call_args[0][0]
            assert "?open=exports" in url
            assert "exports=21" in url  # Symbol/schematic
            assert "exports=42" in url  # 3D model

    def test_url_without_open_exports_flag(self):
        """URL should exclude export params when open_exports=False."""
        from jlc_has_it.core.ultralibrarian_browser import open_ultralibrarian_part

        with patch("webbrowser.open") as mock_browser:
            mock_browser.return_value = True

            open_ultralibrarian_part(
                uuid="44b282e2-2a18-11ee-9288-0ae0a3b49db5",
                mpn="TEST-001",
                manufacturer="TestMfg",
                open_exports=False,
            )

            url = mock_browser.call_args[0][0]
            assert "?open=exports" not in url

    def test_url_handles_manufacturer_with_spaces(self):
        """Should properly handle manufacturer names with spaces."""
        from jlc_has_it.core.ultralibrarian_browser import open_ultralibrarian_part

        with patch("webbrowser.open") as mock_browser:
            mock_browser.return_value = True

            open_ultralibrarian_part(
                uuid="44b282e2-2a18-11ee-9288-0ae0a3b49db5",
                mpn="TEST-001",
                manufacturer="Bourns Electronics",
                open_exports=True,
            )

            url = mock_browser.call_args[0][0]
            # Spaces should be converted to dashes or URL-encoded
            assert "Bourns" in url or "bourns" in url.lower()

    def test_fallback_to_uuid_only_url(self):
        """Should fall back to UUID-only URL if manufacturer/MPN not provided."""
        from jlc_has_it.core.ultralibrarian_browser import open_ultralibrarian_part

        with patch("webbrowser.open") as mock_browser:
            mock_browser.return_value = True

            open_ultralibrarian_part(
                uuid="44b282e2-2a18-11ee-9288-0ae0a3b49db5",
                mpn="TEST-001",
            )

            url = mock_browser.call_args[0][0]
            assert "44b282e2-2a18-11ee-9288-0ae0a3b49db5" in url
            assert "?" not in url  # No export parameters

    def test_add_from_ultralibrarian_passes_manufacturer_to_browser(self):
        """add_from_ultralibrarian should pass manufacturer to open_ultralibrarian_part."""
        mock_db = MagicMock()
        tools = JLCTools(mock_db)

        with patch("jlc_has_it.mcp.tools.open_ultralibrarian_part") as mock_open:
            with patch("jlc_has_it.mcp.tools.ProjectConfig.find_project_root", return_value=Path("/tmp")):
                with patch("jlc_has_it.mcp.tools.ProjectConfig"):
                    # Mock the scraper to return a UUID
                    with patch.object(tools, "_get_ultralibrarian_scraper") as mock_scraper_getter:
                        mock_scraper = MagicMock()
                        mock_scraper.search_part.return_value = "test-uuid"
                        mock_scraper_getter.return_value = mock_scraper

                        # Mock the wait and extract to fail (so we only test the browser opening)
                        with patch("jlc_has_it.mcp.tools.wait_for_ultralibrarian_download", return_value=None):
                            tools.add_from_ultralibrarian(
                                manufacturer="Littelfuse",
                                mpn="0501010.WR1",
                            )

        # Check that open_ultralibrarian_part was called with manufacturer
        assert mock_open.called
        call_args = mock_open.call_args
        assert call_args[1]["manufacturer"] == "Littelfuse"
        assert call_args[1]["open_exports"] is True


class TestTask13006ProgressFeedback:
    """Tests for task 13-006: Add progress feedback for download wait."""

    def test_wait_prints_initial_message(self, capsys):
        """Should print initial waiting message to stdout."""
        from jlc_has_it.core.ultralibrarian_waiter import wait_for_ultralibrarian_download

        with patch("jlc_has_it.core.ultralibrarian_waiter.find_ultralibrarian_folders", return_value=[]):
            wait_for_ultralibrarian_download("TEST-001", timeout_seconds=1)

        captured = capsys.readouterr()
        assert "⏳" in captured.out
        assert "Waiting" in captured.out
        assert "ul_TEST-001" in captured.out

    def test_wait_prints_timeout_message(self, capsys):
        """Should print timeout message with helpful info."""
        from jlc_has_it.core.ultralibrarian_waiter import wait_for_ultralibrarian_download

        with patch("jlc_has_it.core.ultralibrarian_waiter.find_ultralibrarian_folders", return_value=[]):
            result = wait_for_ultralibrarian_download("TEST-001", timeout_seconds=1)

        captured = capsys.readouterr()
        assert "⏱" in captured.out or "Timeout" in captured.out
        assert "exported" in captured.out.lower() or "download" in captured.out.lower()
        assert result is None

    def test_wait_prints_download_detected_message(self, capsys, tmp_path):
        """Should print message when download folder is detected."""
        from jlc_has_it.core.ultralibrarian_waiter import wait_for_ultralibrarian_download

        # Create a mock folder structure
        ul_folder = tmp_path / "ul_TEST-001"
        ul_folder.mkdir()
        (ul_folder / "symbol.kicad_sym").write_text("(kicad_symbol_lib)")
        (ul_folder / "footprints.pretty").mkdir()
        (ul_folder / "footprints.pretty" / "test.kicad_mod").write_text("(footprint)")
        (ul_folder / "models").mkdir()
        (ul_folder / "models" / "test.step").write_text("STEP")

        # Mock find function to return our test folder
        def mock_find(max_age_seconds=None):
            return [ul_folder]

        with patch("jlc_has_it.core.ultralibrarian_waiter.find_ultralibrarian_folders", side_effect=mock_find):
            with patch(
                "jlc_has_it.core.ultralibrarian_waiter.validate_folder_structure", return_value=True
            ):
                with patch(
                    "jlc_has_it.core.ultralibrarian_waiter.extract_component_files"
                ) as mock_extract:
                    mock_extract.return_value = {
                        "valid": True,
                        "symbol_path": str(ul_folder / "symbol.kicad_sym"),
                        "footprints": [str(ul_folder / "footprints.pretty" / "test.kicad_mod")],
                        "model_path": str(ul_folder / "models" / "test.step"),
                    }

                    result = wait_for_ultralibrarian_download("TEST-001", timeout_seconds=30)

        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "Download detected" in captured.out or "detected" in captured.out.lower()
        assert result == ul_folder

    def test_wait_polls_at_correct_interval(self):
        """Should use 2-second poll interval by default (not 1 second)."""
        from jlc_has_it.core.ultralibrarian_waiter import wait_for_ultralibrarian_download

        with patch("jlc_has_it.core.ultralibrarian_waiter.find_ultralibrarian_folders", return_value=[]):
            with patch("time.sleep") as mock_sleep:
                wait_for_ultralibrarian_download("TEST-001", timeout_seconds=6, poll_interval=2.0)

        # Should have slept multiple times at 2-second intervals
        assert mock_sleep.called
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert all(interval == 2.0 for interval in sleep_calls)

    def test_wait_shows_validation_messages(self, capsys, tmp_path):
        """Should print validation success message."""
        from jlc_has_it.core.ultralibrarian_waiter import wait_for_ultralibrarian_download

        ul_folder = tmp_path / "ul_TEST-002"
        ul_folder.mkdir()
        (ul_folder / "symbol.kicad_sym").write_text("(kicad_symbol_lib)")
        (ul_folder / "footprints.pretty").mkdir()
        (ul_folder / "footprints.pretty" / "test.kicad_mod").write_text("(footprint)")
        (ul_folder / "models").mkdir()
        (ul_folder / "models" / "test.step").write_text("STEP")

        def mock_find(max_age_seconds=None):
            return [ul_folder]

        with patch("jlc_has_it.core.ultralibrarian_waiter.find_ultralibrarian_folders", side_effect=mock_find):
            with patch(
                "jlc_has_it.core.ultralibrarian_waiter.validate_folder_structure", return_value=True
            ):
                with patch(
                    "jlc_has_it.core.ultralibrarian_waiter.extract_component_files"
                ) as mock_extract:
                    mock_extract.return_value = {
                        "valid": True,
                        "symbol_path": str(ul_folder / "symbol.kicad_sym"),
                        "footprints": [str(ul_folder / "footprints.pretty" / "test.kicad_mod")],
                        "model_path": str(ul_folder / "models" / "test.step"),
                    }

                    wait_for_ultralibrarian_download("TEST-002", timeout_seconds=30)

        captured = capsys.readouterr()
        # Should show validation message
        assert "validated" in captured.out.lower() or "✓" in captured.out
        assert "Processing" in captured.out or "processing" in captured.out.lower()
