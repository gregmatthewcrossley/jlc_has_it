"""
Unit tests for Ultralibrarian extraction and renaming modules.
"""

import pytest
from pathlib import Path

from jlc_has_it.core.ultralibrarian_renamer import (
    sanitize_mpn_for_filename,
    rename_symbol_file,
)
from jlc_has_it.core.ultralibrarian_extractor import extract_to_project


class TestSanitizeMpnForFilename:
    """Tests for sanitize_mpn_for_filename() function."""

    def test_simple_mpn_unchanged(self):
        """Should leave simple MPNs unchanged."""
        result = sanitize_mpn_for_filename("C1234")
        assert result == "C1234"

    def test_with_dashes_unchanged(self):
        """Should leave dashes unchanged."""
        result = sanitize_mpn_for_filename("SF-0603F300-2")
        assert result == "SF-0603F300-2"

    def test_replaces_forward_slash(self):
        """Should replace forward slashes with underscores."""
        result = sanitize_mpn_for_filename("10k/1%")
        assert "/" not in result
        assert "_" in result

    def test_replaces_backslash(self):
        """Should replace backslashes with underscores."""
        result = sanitize_mpn_for_filename("test\\path")
        assert "\\" not in result

    def test_replaces_colons(self):
        """Should replace colons with underscores."""
        result = sanitize_mpn_for_filename("test:part")
        assert ":" not in result

    def test_replaces_asterisk(self):
        """Should replace asterisks with underscores."""
        result = sanitize_mpn_for_filename("test*part")
        assert "*" not in result

    def test_replaces_question_mark(self):
        """Should replace question marks with underscores."""
        result = sanitize_mpn_for_filename("test?part")
        assert "?" not in result

    def test_replaces_quotes(self):
        """Should replace quotes with underscores."""
        result = sanitize_mpn_for_filename('test"part')
        assert '"' not in result

    def test_replaces_angle_brackets(self):
        """Should replace angle brackets with underscores."""
        result = sanitize_mpn_for_filename("test<part>name")
        assert "<" not in result
        assert ">" not in result

    def test_replaces_pipe(self):
        """Should replace pipe with underscores."""
        result = sanitize_mpn_for_filename("test|part")
        assert "|" not in result

    def test_strips_whitespace(self):
        """Should strip leading and trailing whitespace."""
        result = sanitize_mpn_for_filename("  C1234  ")
        assert result == "C1234"

    def test_multiple_problematic_chars(self):
        """Should handle multiple problematic characters."""
        result = sanitize_mpn_for_filename("test/path:file*name?")
        assert "/" not in result
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result
        assert len(result.replace("_", "").replace("-", "").replace("0", "")) > 0


class TestRenameSymbolFile:
    """Tests for rename_symbol_file() function."""

    def test_renames_timestamp_filename(self, tmp_path):
        """Should rename symbol file from timestamp to MPN-based name."""
        # Create a symbol file with timestamp name
        symbol_file = tmp_path / "2025-10-28_14-26-29.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib)")

        result = rename_symbol_file(symbol_file, "C1234")

        assert result.name == "C1234.kicad_sym"
        assert result.exists()
        assert symbol_file.exists() is False  # Original renamed away

    def test_returns_path_to_renamed_file(self, tmp_path):
        """Should return path to the renamed file."""
        symbol_file = tmp_path / "TIMESTAMP.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib)")

        result = rename_symbol_file(symbol_file, "TEST")

        assert result.name == "TEST.kicad_sym"
        assert result.parent == symbol_file.parent

    def test_handles_mpn_with_special_chars(self, tmp_path):
        """Should sanitize MPN with special characters."""
        symbol_file = tmp_path / "SYMBOL.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib)")

        # MPN with special chars that need sanitizing
        result = rename_symbol_file(symbol_file, "SF-0603/2")

        assert result.name == "SF-0603_2.kicad_sym"

    def test_raises_for_nonexistent_file(self, tmp_path):
        """Should raise FileNotFoundError if file doesn't exist."""
        nonexistent = tmp_path / "missing.kicad_sym"

        with pytest.raises(FileNotFoundError):
            rename_symbol_file(nonexistent, "C1234")

    def test_raises_for_non_sym_file(self, tmp_path):
        """Should raise ValueError for non-.kicad_sym files."""
        other_file = tmp_path / "notasymbol.txt"
        other_file.write_text("content")

        with pytest.raises(ValueError):
            rename_symbol_file(other_file, "C1234")

    def test_raises_for_non_file_path(self, tmp_path):
        """Should raise ValueError if path is a directory."""
        directory = tmp_path / "folder"
        directory.mkdir()

        with pytest.raises(ValueError):
            rename_symbol_file(directory, "C1234")

    def test_handles_already_correctly_named_file(self, tmp_path):
        """Should handle file already with correct name."""
        symbol_file = tmp_path / "C1234.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib)")

        result = rename_symbol_file(symbol_file, "C1234")

        # Should return the existing file without error
        assert result == symbol_file
        assert symbol_file.exists()

    def test_handles_file_exists_conflict(self, tmp_path):
        """Should handle case where target filename already exists."""
        original = tmp_path / "ORIG.kicad_sym"
        original.write_text("original content")

        existing = tmp_path / "C1234.kicad_sym"
        existing.write_text("existing content")

        result = rename_symbol_file(original, "C1234")

        # Should return original path (not renamed due to conflict)
        assert result == original
        assert original.exists()
        assert existing.exists()


class TestExtractToProject:
    """Tests for extract_to_project() function."""

    def create_ul_folder(self, tmp_path, mpn="TEST"):
        """Helper to create a valid Ultralibrarian folder structure."""
        ul_folder = tmp_path / f"ul_{mpn}"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        # Create component files
        symbol = fp_dir / f"{mpn}_symbol.kicad_sym"
        symbol.write_text("(kicad_symbol_lib)")

        footprint = fp_dir / f"{mpn}.kicad_mod"
        footprint.write_text("(footprint)")

        model = fp_dir / f"{mpn}.step"
        model.write_text("STEP content")

        return ul_folder

    def create_kicad_project(self, tmp_path):
        """Helper to create a minimal KiCad project."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        kicad_pro = project_dir / "test_project.kicad_pro"
        kicad_pro.write_text("(kicad_project)")

        return project_dir

    def test_successful_extraction(self, tmp_path):
        """Should successfully extract component to project."""
        ul_folder = self.create_ul_folder(tmp_path, "C1234")
        project_dir = self.create_kicad_project(tmp_path)

        result = extract_to_project(ul_folder, project_dir, "C1234", cleanup=False)

        assert result is True
        assert (project_dir / "libraries" / "C1234.kicad_sym").exists()
        assert (project_dir / "libraries" / "footprints.pretty" / "C1234.kicad_mod").exists()
        assert (project_dir / "libraries" / "3d_models" / "C1234.step").exists()

    def test_creates_library_directories(self, tmp_path):
        """Should create missing library directories."""
        ul_folder = self.create_ul_folder(tmp_path, "TEST")
        project_dir = self.create_kicad_project(tmp_path)

        # Directories don't exist yet
        assert not (project_dir / "libraries").exists()

        extract_to_project(ul_folder, project_dir, "TEST", cleanup=False)

        # Should be created
        assert (project_dir / "libraries").exists()
        assert (project_dir / "libraries" / "footprints.pretty").exists()
        assert (project_dir / "libraries" / "3d_models").exists()

    def test_updates_library_tables(self, tmp_path):
        """Should update sym-lib-table and fp-lib-table files."""
        ul_folder = self.create_ul_folder(tmp_path, "C5678")
        project_dir = self.create_kicad_project(tmp_path)

        extract_to_project(ul_folder, project_dir, "C5678", cleanup=False)

        # Check library tables exist
        sym_table = project_dir / "sym-lib-table"
        fp_table = project_dir / "fp-lib-table"

        assert sym_table.exists()
        assert fp_table.exists()

        # Check content mentions the library
        sym_content = sym_table.read_text()
        fp_content = fp_table.read_text()

        assert "C5678" in sym_content or "jlc-C5678" in sym_content
        assert "C5678" in fp_content or "jlc-C5678" in fp_content

    def test_handles_multiple_footprints(self, tmp_path):
        """Should copy all footprint files."""
        ul_folder = tmp_path / "ul_MULTI"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        # Create multiple footprint variants
        (fp_dir / "SYMBOL.kicad_sym").write_text("(kicad_symbol_lib)")
        (fp_dir / "PART_A.kicad_mod").write_text("(footprint A)")
        (fp_dir / "PART_B.kicad_mod").write_text("(footprint B)")
        (fp_dir / "PART_C.kicad_mod").write_text("(footprint C)")
        (fp_dir / "MODEL.step").write_text("STEP")

        project_dir = self.create_kicad_project(tmp_path)

        result = extract_to_project(ul_folder, project_dir, "MULTI", cleanup=False)

        assert result is True
        fp_target_dir = project_dir / "libraries" / "footprints.pretty"
        assert (fp_target_dir / "PART_A.kicad_mod").exists()
        assert (fp_target_dir / "PART_B.kicad_mod").exists()
        assert (fp_target_dir / "PART_C.kicad_mod").exists()

    def test_cleans_up_source_folder(self, tmp_path):
        """Should delete source folder when cleanup=True."""
        ul_folder = self.create_ul_folder(tmp_path, "C9999")
        project_dir = self.create_kicad_project(tmp_path)

        assert ul_folder.exists()

        extract_to_project(ul_folder, project_dir, "C9999", cleanup=True)

        assert ul_folder.exists() is False

    def test_keeps_source_folder_when_cleanup_false(self, tmp_path):
        """Should keep source folder when cleanup=False."""
        ul_folder = self.create_ul_folder(tmp_path, "C9999")
        project_dir = self.create_kicad_project(tmp_path)

        extract_to_project(ul_folder, project_dir, "C9999", cleanup=False)

        assert ul_folder.exists()

    def test_raises_for_nonexistent_ul_folder(self, tmp_path):
        """Should raise FileNotFoundError if ul_folder doesn't exist."""
        nonexistent = tmp_path / "ul_MISSING"
        project_dir = self.create_kicad_project(tmp_path)

        with pytest.raises(FileNotFoundError):
            extract_to_project(nonexistent, project_dir, "MISSING")

    def test_raises_for_nonexistent_project(self, tmp_path):
        """Should raise FileNotFoundError if project doesn't exist."""
        ul_folder = self.create_ul_folder(tmp_path, "TEST")
        nonexistent_project = tmp_path / "missing_project"

        with pytest.raises(FileNotFoundError):
            extract_to_project(ul_folder, nonexistent_project, "TEST")

    def test_returns_false_for_invalid_project(self, tmp_path):
        """Should return False if project has no .kicad_pro file."""
        ul_folder = self.create_ul_folder(tmp_path, "TEST")
        project_dir = tmp_path / "invalid_project"
        project_dir.mkdir()  # No .kicad_pro file

        result = extract_to_project(ul_folder, project_dir, "TEST")
        assert result is False

    def test_returns_false_for_invalid_ul_folder(self, tmp_path):
        """Should return False if ul_folder has invalid structure."""
        ul_folder = tmp_path / "ul_INVALID"
        ul_folder.mkdir()  # No subfolder structure

        project_dir = self.create_kicad_project(tmp_path)

        result = extract_to_project(ul_folder, project_dir, "INVALID")

        assert result is False

    def test_returns_false_for_incomplete_library(self, tmp_path):
        """Should return False if library is incomplete (missing files)."""
        ul_folder = tmp_path / "ul_INCOMPLETE"
        fp_dir = ul_folder / "KiCADv6" / "footprints.pretty"
        fp_dir.mkdir(parents=True)

        # Only create symbol, missing footprint and model
        (fp_dir / "SYMBOL.kicad_sym").write_text("(kicad_symbol_lib)")

        project_dir = self.create_kicad_project(tmp_path)

        result = extract_to_project(ul_folder, project_dir, "INCOMPLETE")

        assert result is False
