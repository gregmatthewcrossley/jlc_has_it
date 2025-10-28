"""
Unit tests for Ultralibrarian downloads detector module.
"""

import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from jlc_has_it.core.ultralibrarian_detector import (
    get_downloads_directory,
    find_ultralibrarian_folders,
    validate_folder_structure,
    extract_component_files,
    find_and_validate_latest,
)


class TestGetDownloadsDirectory:
    """Tests for get_downloads_directory() function."""

    def test_returns_path_object(self):
        """Should return a Path object."""
        result = get_downloads_directory()
        assert isinstance(result, Path)

    def test_returns_existing_directory(self):
        """Should return a directory that exists."""
        result = get_downloads_directory()
        assert result.exists()
        assert result.is_dir()

    def test_returns_downloads_folder(self):
        """Should return the Downloads folder."""
        result = get_downloads_directory()
        assert result.name == "Downloads"

    def test_raises_when_downloads_missing(self, monkeypatch):
        """Should raise RuntimeError if Downloads doesn't exist."""
        # Mock Path.home() to return a non-existent directory
        mock_home = MagicMock()
        mock_home.return_value = Path("/nonexistent/home")

        with patch("jlc_has_it.core.ultralibrarian_detector.Path.home", mock_home):
            with pytest.raises(RuntimeError):
                get_downloads_directory()


class TestFindUltraLibrarianFolders:
    """Tests for find_ultralibrarian_folders() function."""

    def test_returns_empty_list_when_no_folders(self, tmp_path, monkeypatch):
        """Should return empty list when no ul_* folders found."""
        # Mock get_downloads_directory to return tmp_path
        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: tmp_path,
        )

        result = find_ultralibrarian_folders()
        assert result == []

    def test_finds_ul_folder(self, tmp_path, monkeypatch):
        """Should find a ul_* folder."""
        # Create a mock ul_* folder
        ul_folder = tmp_path / "ul_TEST-123"
        ul_folder.mkdir()

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: tmp_path,
        )

        result = find_ultralibrarian_folders()
        assert len(result) == 1
        assert result[0].name == "ul_TEST-123"

    def test_ignores_non_ul_folders(self, tmp_path, monkeypatch):
        """Should ignore folders not matching ul_* pattern."""
        (tmp_path / "regular_folder").mkdir()
        (tmp_path / "ul_TEST").mkdir()
        (tmp_path / "not_ultralib").mkdir()

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: tmp_path,
        )

        result = find_ultralibrarian_folders()
        assert len(result) == 1
        assert result[0].name == "ul_TEST"

    def test_sorts_by_modification_time_newest_first(self, tmp_path, monkeypatch):
        """Should sort folders by modification time, newest first."""
        # Create folders with different modification times
        ul_1 = tmp_path / "ul_OLD"
        ul_1.mkdir()
        old_time = time.time() - 100

        ul_2 = tmp_path / "ul_NEW"
        ul_2.mkdir()

        # Set modification time
        import os
        os.utime(ul_1, (old_time, old_time))

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: tmp_path,
        )

        result = find_ultralibrarian_folders()
        assert len(result) == 2
        assert result[0].name == "ul_NEW"  # Newer first
        assert result[1].name == "ul_OLD"

    def test_filters_by_max_age(self, tmp_path, monkeypatch):
        """Should filter out old folders based on max_age_seconds."""
        ul_old = tmp_path / "ul_OLD"
        ul_old.mkdir()

        ul_new = tmp_path / "ul_NEW"
        ul_new.mkdir()

        # Set old folder's mtime to 200 seconds ago
        import os
        old_time = time.time() - 200
        os.utime(ul_old, (old_time, old_time))

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: tmp_path,
        )

        # With max_age_seconds=100, old folder should be filtered out
        result = find_ultralibrarian_folders(max_age_seconds=100)
        assert len(result) == 1
        assert result[0].name == "ul_NEW"

    def test_handles_missing_downloads_gracefully(self, monkeypatch):
        """Should return empty list if Downloads directory doesn't exist."""
        def raise_runtime_error():
            raise RuntimeError("Downloads not found")

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            raise_runtime_error,
        )

        result = find_ultralibrarian_folders()
        assert result == []


class TestValidateFolderStructure:
    """Tests for validate_folder_structure() function."""

    def test_valid_structure(self, tmp_path):
        """Should validate correct folder structure."""
        ul_folder = tmp_path / "ul_TEST-123"
        kicad_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        kicad_dir.mkdir(parents=True)

        assert validate_folder_structure(ul_folder) is True

    def test_invalid_missing_kicad_dir(self, tmp_path):
        """Should reject folder without KiCADv6 directory."""
        ul_folder = tmp_path / "ul_TEST-123"
        ul_folder.mkdir()

        assert validate_folder_structure(ul_folder) is False

    def test_invalid_missing_footprints_dir(self, tmp_path):
        """Should reject folder without footprints.pretty directory."""
        ul_folder = tmp_path / "ul_TEST-123"
        kicad_dir = ul_folder / "KiCADv6"
        kicad_dir.mkdir(parents=True)

        assert validate_folder_structure(ul_folder) is False

    def test_invalid_nonexistent_folder(self, tmp_path):
        """Should reject nonexistent folder."""
        ul_folder = tmp_path / "nonexistent"

        assert validate_folder_structure(ul_folder) is False

    def test_invalid_file_not_directory(self, tmp_path):
        """Should reject if path is a file not a directory."""
        ul_file = tmp_path / "ul_TEST"
        ul_file.write_text("not a directory")

        assert validate_folder_structure(ul_file) is False


class TestExtractComponentFiles:
    """Tests for extract_component_files() function."""

    def test_extracts_valid_component(self, tmp_path):
        """Should extract component files from valid structure."""
        # Create valid Ultralibrarian folder
        ul_folder = tmp_path / "ul_C1234"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        # Create component files
        symbol_file = fp_dir / "2025-10-28_14-26-29.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib)")

        footprint_file = fp_dir / "TEST_0603.kicad_mod"
        footprint_file.write_text("(footprint TEST_0603)")

        model_file = fp_dir / "TEST_0603.step"
        model_file.write_text("STEP content")

        result = extract_component_files(ul_folder)

        assert result is not None
        assert result['mpn'] == "C1234"
        assert result['symbol_path'] == symbol_file
        assert len(result['footprints']) == 1
        assert result['footprints'][0] == footprint_file
        assert result['model_path'] == model_file
        assert result['valid'] is True

    def test_handles_multiple_footprints(self, tmp_path):
        """Should handle multiple footprint files."""
        ul_folder = tmp_path / "ul_FUSE"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        symbol_file = fp_dir / "SYMBOL.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib)")

        # Create multiple footprint files
        fp1 = fp_dir / "FUSE_0603_A.kicad_mod"
        fp1.write_text("(footprint A)")

        fp2 = fp_dir / "FUSE_0603_B.kicad_mod"
        fp2.write_text("(footprint B)")

        model_file = fp_dir / "MODEL.step"
        model_file.write_text("STEP")

        result = extract_component_files(ul_folder)

        assert len(result['footprints']) == 2
        assert all(fp.suffix == '.kicad_mod' for fp in result['footprints'])

    def test_returns_none_for_invalid_structure(self, tmp_path):
        """Should return None if folder structure is invalid."""
        ul_folder = tmp_path / "ul_TEST"
        ul_folder.mkdir()  # No subfolder structure

        result = extract_component_files(ul_folder)
        assert result is None

    def test_marks_incomplete_as_invalid(self, tmp_path):
        """Should mark as invalid if any required file is missing."""
        ul_folder = tmp_path / "ul_TEST"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        # Missing footprint and model files
        symbol_file = fp_dir / "TEST.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib)")

        result = extract_component_files(ul_folder)

        assert result is not None
        assert result['valid'] is False

    def test_extracts_mfn_from_folder_name(self, tmp_path):
        """Should extract MPN from folder name."""
        # Test with special characters
        ul_folder = tmp_path / "ul_SF-0603F300-2"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        # Create minimal files for validity
        (fp_dir / "S.kicad_sym").write_text("(kicad_symbol_lib)")
        (fp_dir / "F.kicad_mod").write_text("(footprint)")
        (fp_dir / "M.step").write_text("STEP")

        result = extract_component_files(ul_folder)

        assert result['mpn'] == "SF-0603F300-2"


class TestFindAndValidateLatest:
    """Tests for find_and_validate_latest() function."""

    def test_finds_latest_valid_folder(self, tmp_path, monkeypatch):
        """Should find and validate the most recent valid folder."""
        # Create two ul_* folders
        ul_1 = tmp_path / "ul_OLD"
        ul_1.mkdir()

        ul_2 = tmp_path / "ul_NEW"
        fp_dir = ul_2 / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        # Create files in NEW folder
        (fp_dir / "S.kicad_sym").write_text("(kicad_symbol_lib)")
        (fp_dir / "F.kicad_mod").write_text("(footprint)")
        (fp_dir / "M.step").write_text("STEP")

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: tmp_path,
        )

        result = find_and_validate_latest()

        assert result is not None
        assert result['mpn'] == "NEW"
        assert result['valid'] is True

    def test_returns_none_when_no_folders_found(self, tmp_path, monkeypatch):
        """Should return None if no valid folders found."""
        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: tmp_path,
        )

        result = find_and_validate_latest()
        assert result is None

    def test_returns_none_when_latest_invalid(self, tmp_path, monkeypatch):
        """Should return None if latest folder has invalid structure."""
        ul_folder = tmp_path / "ul_TEST"
        ul_folder.mkdir()  # Invalid structure

        monkeypatch.setattr(
            "jlc_has_it.core.ultralibrarian_detector.get_downloads_directory",
            lambda: tmp_path,
        )

        result = find_and_validate_latest()
        assert result is None
