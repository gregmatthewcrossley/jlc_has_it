"""
Tests for Phase 13: LibraryDownloader error handling and validation improvements.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from jlc_has_it.core.library_downloader import (
    LibraryDownloader,
    DownloadError,
    ComponentLibrary,
)


class TestDownloadError:
    """Tests for DownloadError dataclass."""

    def test_timeout_error_message(self):
        """Should format timeout error correctly."""
        error = DownloadError(
            lcsc_id="C1234",
            error_type="timeout",
            message="exceeded 30 seconds",
        )
        msg = error.user_friendly_message()
        assert "timed out" in msg
        assert "C1234" in msg

    def test_not_found_error_message(self):
        """Should format not_found error correctly."""
        error = DownloadError(
            lcsc_id="C9999",
            error_type="not_found",
            message="component not in database",
        )
        msg = error.user_friendly_message()
        assert "not found" in msg
        assert "C9999" in msg

    def test_validation_error_message(self):
        """Should format validation error with reason."""
        error = DownloadError(
            lcsc_id="C5555",
            error_type="validation",
            message="symbol file missing",
        )
        msg = error.user_friendly_message()
        assert "incomplete" in msg
        assert "symbol file missing" in msg
        assert "C5555" in msg

    def test_subprocess_error_message(self):
        """Should format subprocess error correctly."""
        error = DownloadError(
            lcsc_id="C7777",
            error_type="subprocess",
            message="exit code 1",
        )
        msg = error.user_friendly_message()
        assert "Download tool error" in msg
        assert "exit code 1" in msg

    def test_generic_error_message(self):
        """Should format generic error correctly."""
        error = DownloadError(
            lcsc_id="C1111",
            error_type="unknown",
            message="something went wrong",
        )
        msg = error.user_friendly_message()
        assert "Failed to download" in msg
        assert "C1111" in msg


class TestValidateFilesWithDetail:
    """Tests for _validate_files_with_detail() method."""

    def test_valid_structure_returns_true(self, tmp_path):
        """Should return True for complete valid structure."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("(kicad_symbol_lib)")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(footprint)")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP")

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is True
        assert detail == ""

    def test_missing_symbol_file(self, tmp_path):
        """Should detect missing symbol file."""
        symbol_path = tmp_path / "symbol.kicad_sym"  # Not created

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(footprint)")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP")

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is False
        assert "symbol file missing" in detail

    def test_empty_symbol_file(self, tmp_path):
        """Should detect empty symbol file."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("")  # Empty

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(footprint)")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP")

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is False
        assert "empty" in detail

    def test_missing_footprint_directory(self, tmp_path):
        """Should detect missing footprint directory."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("(kicad_symbol_lib)")

        footprint_dir = tmp_path / "footprints.pretty"  # Not created

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP")

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is False
        assert "footprint directory missing" in detail

    def test_no_footprint_files(self, tmp_path):
        """Should detect footprint directory with no .kicad_mod files."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("(kicad_symbol_lib)")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        # No .kicad_mod files

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP")

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is False
        assert "no .kicad_mod files found" in detail

    def test_missing_model_directory(self, tmp_path):
        """Should detect missing 3D model directory."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("(kicad_symbol_lib)")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(footprint)")

        model_dir = tmp_path / "models"  # Not created

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is False
        assert "3D model directory missing" in detail

    def test_no_model_files(self, tmp_path):
        """Should detect model directory with no .step or .wrl files."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("(kicad_symbol_lib)")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(footprint)")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        # No .step or .wrl files

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is False
        assert "no .step or .wrl 3D model files found" in detail

    def test_accepts_wrl_files(self, tmp_path):
        """Should accept .wrl 3D model files."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("(kicad_symbol_lib)")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(footprint)")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.wrl").write_text("WRL")  # .wrl instead of .step

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is True
        assert detail == ""

    def test_multiple_footprint_files(self, tmp_path):
        """Should accept multiple footprint files."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("(kicad_symbol_lib)")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test_a.kicad_mod").write_text("(footprint A)")
        (footprint_dir / "test_b.kicad_mod").write_text("(footprint B)")
        (footprint_dir / "test_c.kicad_mod").write_text("(footprint C)")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP")

        is_valid, detail = LibraryDownloader._validate_files_with_detail(
            symbol_path, footprint_dir, model_dir
        )

        assert is_valid is True
        assert detail == ""


class TestValidateFilesBackwardCompatibility:
    """Tests to ensure _validate_files() still works correctly."""

    def test_validate_files_uses_detail_method(self, tmp_path):
        """Should use _validate_files_with_detail internally."""
        symbol_path = tmp_path / "symbol.kicad_sym"
        symbol_path.write_text("(kicad_symbol_lib)")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(footprint)")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP")

        result = LibraryDownloader._validate_files(
            symbol_path, footprint_dir, model_dir
        )

        assert result is True

    def test_validate_files_returns_false_on_missing_symbol(self, tmp_path):
        """Should return False for missing symbol file."""
        symbol_path = tmp_path / "symbol.kicad_sym"  # Not created

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(footprint)")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP")

        result = LibraryDownloader._validate_files(
            symbol_path, footprint_dir, model_dir
        )

        assert result is False
