"""
End-to-end integration tests for Ultralibrarian workflow.

Tests the complete user workflow:
1. Search for a part on Ultralibrarian
2. Open browser to part page
3. User simulates downloading the export
4. Tool detects download
5. Tool extracts files to project library
"""

import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from jlc_has_it.core.ultralibrarian_browser import open_ultralibrarian_part
from jlc_has_it.core.ultralibrarian_waiter import wait_for_ultralibrarian_download
from jlc_has_it.core.ultralibrarian_extractor import extract_to_project


class TestUltraLibrarianCompleteWorkflow:
    """Integration tests for complete Ultralibrarian workflow."""

    def create_kicad_project(self, tmp_path):
        """Create a minimal KiCad project for testing."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        kicad_pro = project_dir / "test_project.kicad_pro"
        kicad_pro.write_text("(kicad_project)")
        return project_dir

    def simulate_ultralibrarian_download(self, downloads_dir, mpn):
        """Simulate a user downloading from Ultralibrarian."""
        ul_folder = downloads_dir / f"ul_{mpn}"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        # Create component files
        symbol = fp_dir / f"symbol_{mpn}.kicad_sym"
        symbol.write_text("(kicad_symbol_lib)")

        footprint = fp_dir / f"footprint_{mpn}.kicad_mod"
        footprint.write_text("(footprint)")

        model = fp_dir / f"model_{mpn}.step"
        model.write_text("STEP 3D model content")

        return ul_folder

    def test_happy_path_complete_workflow(self, tmp_path, monkeypatch):
        """Test complete happy-path workflow from download to extraction."""
        # Setup
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        project_dir = self.create_kicad_project(tmp_path)

        mpn = "C1234"

        # Mock get_downloads_directory to return our test directory
        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: downloads_dir,
        )

        # Simulate the user downloading the part
        ul_folder = self.simulate_ultralibrarian_download(downloads_dir, mpn)

        # Test the wait function finds the download
        result_folder = wait_for_ultralibrarian_download(mpn, timeout_seconds=10)

        assert result_folder is not None
        assert result_folder.name == f"ul_{mpn}"

        # Test extraction to project
        success = extract_to_project(ul_folder, project_dir, mpn, cleanup=True)

        assert success is True
        # Verify files were copied
        assert (project_dir / "libraries" / "C1234.kicad_sym").exists()
        assert (project_dir / "libraries" / "footprints.pretty" / f"footprint_{mpn}.kicad_mod").exists()
        assert (project_dir / "libraries" / "3d_models" / f"model_{mpn}.step").exists()
        # Verify source was cleaned up
        assert ul_folder.exists() is False

    def test_workflow_handles_timeout(self, tmp_path, monkeypatch):
        """Test workflow handles download timeout gracefully."""
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()

        mpn = "C9999"

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: downloads_dir,
        )

        # Don't simulate any download - should timeout
        result_folder = wait_for_ultralibrarian_download(
            mpn,
            timeout_seconds=2,  # Short timeout
        )

        assert result_folder is None

    def test_workflow_handles_incomplete_download(self, tmp_path, monkeypatch):
        """Test workflow detects and rejects incomplete downloads."""
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()

        mpn = "C5555"

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: downloads_dir,
        )

        # Simulate incomplete download (missing footprint and model)
        ul_folder = downloads_dir / f"ul_{mpn}"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        symbol = fp_dir / "symbol.kicad_sym"
        symbol.write_text("(kicad_symbol_lib)")

        # Wait for download - should detect structure is incomplete
        result_folder = wait_for_ultralibrarian_download(mpn, timeout_seconds=5)

        assert result_folder is None  # Returns None for invalid/incomplete

    def test_workflow_multiple_parts_sequential(self, tmp_path, monkeypatch):
        """Test extracting multiple parts in sequence."""
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        project_dir = self.create_kicad_project(tmp_path)

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: downloads_dir,
        )

        mpn_list = ["C1111", "C2222", "C3333"]
        results = []

        for mpn in mpn_list:
            # Simulate download
            ul_folder = self.simulate_ultralibrarian_download(downloads_dir, mpn)

            # Wait for it
            detected = wait_for_ultralibrarian_download(mpn, timeout_seconds=5)

            # Extract it
            if detected:
                success = extract_to_project(ul_folder, project_dir, mpn, cleanup=True)
                results.append(success)

        # All should succeed
        assert len(results) == 3
        assert all(results)

        # Verify all files are in project
        libs_dir = project_dir / "libraries" / "footprints.pretty"
        assert (libs_dir / "footprint_C1111.kicad_mod").exists()
        assert (libs_dir / "footprint_C2222.kicad_mod").exists()
        assert (libs_dir / "footprint_C3333.kicad_mod").exists()

    def test_workflow_with_special_characters_in_mpn(self, tmp_path, monkeypatch):
        """Test workflow with MPN containing special characters."""
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        project_dir = self.create_kicad_project(tmp_path)

        # MPN with special characters
        mpn = "SF-0603F300-2"

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: downloads_dir,
        )

        ul_folder = self.simulate_ultralibrarian_download(downloads_dir, mpn)

        detected = wait_for_ultralibrarian_download(mpn, timeout_seconds=5)
        assert detected is not None

        success = extract_to_project(ul_folder, project_dir, mpn, cleanup=False)
        assert success is True

        # Symbol should be renamed with sanitized filename
        expected_sym = project_dir / "libraries" / f"{mpn}.kicad_sym"
        assert expected_sym.exists()

    @patch("jlc_has_it.core.ultralibrarian_browser.webbrowser.open")
    def test_browser_opens_correct_url(self, mock_webbrowser, tmp_path):
        """Test that browser is opened with correct Ultralibrarian URL."""
        uuid = "12345678-1234-1234-1234-123456789012"
        mpn = "TEST-123"

        mock_webbrowser.return_value = True

        open_ultralibrarian_part(uuid, mpn)

        # Verify webbrowser.open was called with correct URL
        mock_webbrowser.assert_called_once()
        call_args = mock_webbrowser.call_args[0][0]
        assert "app.ultralibrarian.com/details" in call_args
        assert uuid in call_args

    def test_browser_handles_invalid_uuid(self):
        """Test that browser rejects invalid UUID."""
        with pytest.raises(ValueError):
            open_ultralibrarian_part("not-a-valid-uuid", "C1234")

    def test_workflow_updates_library_tables(self, tmp_path, monkeypatch):
        """Test that library tables are correctly updated during extraction."""
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        project_dir = self.create_kicad_project(tmp_path)

        mpn = "C7777"

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: downloads_dir,
        )

        ul_folder = self.simulate_ultralibrarian_download(downloads_dir, mpn)
        extract_to_project(ul_folder, project_dir, mpn, cleanup=False)

        # Check that library tables were created and contain proper entries
        sym_table = project_dir / "sym-lib-table"
        fp_table = project_dir / "fp-lib-table"

        assert sym_table.exists()
        assert fp_table.exists()

        sym_content = sym_table.read_text()
        fp_content = fp_table.read_text()

        # Both tables should reference the library
        assert "(lib" in sym_content
        assert "(lib" in fp_content
        # And should contain footprints.pretty reference
        assert "footprints.pretty" in fp_content

    def test_workflow_idempotent_on_repeated_extractions(self, tmp_path, monkeypatch):
        """Test that extracting the same part twice doesn't cause errors."""
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        project_dir = self.create_kicad_project(tmp_path)

        mpn = "C8888"

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: downloads_dir,
        )

        # First extraction
        ul_folder1 = self.simulate_ultralibrarian_download(downloads_dir, mpn)
        success1 = extract_to_project(ul_folder1, project_dir, mpn, cleanup=True)
        assert success1 is True

        # Second extraction (simulate re-downloading same part)
        ul_folder2 = self.simulate_ultralibrarian_download(downloads_dir, mpn)
        success2 = extract_to_project(ul_folder2, project_dir, mpn, cleanup=True)
        assert success2 is True

        # Both extractions should have succeeded
        assert (project_dir / "libraries" / f"{mpn}.kicad_sym").exists()
