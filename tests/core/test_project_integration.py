"""Tests for KiCad project integration."""

from pathlib import Path

import pytest

from jlc_has_it.core.kicad.project import LibraryEntry, LibraryTable, ProjectConfig


class TestLibraryEntry:
    """Tests for LibraryEntry dataclass."""

    def test_create_entry(self) -> None:
        """Test creating a library entry."""
        entry = LibraryEntry(
            name="test-lib",
            type_="KiCad",
            uri="libraries/test.kicad_sym",
            options="",
            descr="Test library",
        )

        assert entry.name == "test-lib"
        assert entry.type_ == "KiCad"
        assert entry.uri == "libraries/test.kicad_sym"
        assert entry.descr == "Test library"

    def test_to_sexp(self) -> None:
        """Test S-expression formatting."""
        entry = LibraryEntry(
            name="jlc-components",
            uri="${KIPRJMOD}/libraries/jlc-components.kicad_sym",
            descr="JLCPCB components",
        )

        sexp = entry.to_sexp()

        assert '(name "jlc-components")' in sexp
        assert '(type "KiCad")' in sexp
        assert "${KIPRJMOD}/libraries/jlc-components.kicad_sym" in sexp
        assert '(descr "JLCPCB components")' in sexp

    def test_from_sexp_dict(self) -> None:
        """Test creating from parsed S-expression dict."""
        data = {
            "name": "test-lib",
            "type": "KiCad",
            "uri": "path/to/lib.kicad_sym",
            "options": "",
            "descr": "Test",
        }

        entry = LibraryEntry.from_sexp_dict(data)

        assert entry.name == "test-lib"
        assert entry.type_ == "KiCad"
        assert entry.uri == "path/to/lib.kicad_sym"
        assert entry.descr == "Test"


class TestLibraryTable:
    """Tests for LibraryTable class."""

    def test_create_sym_table(self) -> None:
        """Test creating symbol library table."""
        table = LibraryTable(table_type="sym")

        assert table.table_type == "sym"
        assert table.filename == "sym-lib-table"
        assert table.version == 7
        assert len(table.entries) == 0

    def test_create_fp_table(self) -> None:
        """Test creating footprint library table."""
        table = LibraryTable(table_type="fp")

        assert table.table_type == "fp"
        assert table.filename == "fp-lib-table"

    def test_add_entry(self) -> None:
        """Test adding entry to table."""
        table = LibraryTable()
        entry = LibraryEntry(
            name="test-lib",
            uri="path/to/lib.kicad_sym",
        )

        table.add_entry(entry)

        assert "test-lib" in table.entries
        assert table.entries["test-lib"] == entry

    def test_add_entry_empty_name_raises(self) -> None:
        """Test that adding entry with empty name raises error."""
        table = LibraryTable()
        entry = LibraryEntry(name="", uri="path/to/lib.kicad_sym")

        with pytest.raises(ValueError, match="must have a name"):
            table.add_entry(entry)

    def test_get_entry(self) -> None:
        """Test retrieving entry from table."""
        table = LibraryTable()
        entry = LibraryEntry(name="test-lib", uri="path/to/lib.kicad_sym")
        table.add_entry(entry)

        retrieved = table.get_entry("test-lib")

        assert retrieved == entry
        assert table.get_entry("non-existent") is None

    def test_remove_entry(self) -> None:
        """Test removing entry from table."""
        table = LibraryTable()
        entry = LibraryEntry(name="test-lib", uri="path/to/lib.kicad_sym")
        table.add_entry(entry)

        assert table.remove_entry("test-lib") is True
        assert "test-lib" not in table.entries
        assert table.remove_entry("test-lib") is False

    def test_to_file_sym_table(self, tmp_path: Path) -> None:
        """Test writing symbol library table to file."""
        table = LibraryTable(table_type="sym", version=7)
        table.add_entry(
            LibraryEntry(
                name="jlc-components",
                uri="${KIPRJMOD}/libraries/jlc-components.kicad_sym",
                descr="JLCPCB components",
            )
        )

        table_file = tmp_path / "sym-lib-table"
        table.to_file(table_file)

        assert table_file.exists()
        content = table_file.read_text()

        assert "(sym-lib-table" in content
        assert "(version 7)" in content
        assert '(name "jlc-components")' in content
        assert '(type "KiCad")' in content

    def test_to_file_creates_directory(self, tmp_path: Path) -> None:
        """Test that to_file creates parent directory if needed."""
        table = LibraryTable()
        table.add_entry(LibraryEntry(name="test", uri="path/to/lib"))

        nested_dir = tmp_path / "a" / "b" / "c"
        table_file = nested_dir / "sym-lib-table"

        table.to_file(table_file)

        assert nested_dir.exists()
        assert table_file.exists()

    def test_from_file_empty(self, tmp_path: Path) -> None:
        """Test reading from non-existent file returns empty table."""
        table_file = tmp_path / "sym-lib-table"

        table = LibraryTable.from_file(table_file, table_type="sym")

        assert len(table.entries) == 0
        assert table.version == 7

    def test_from_file_round_trip(self, tmp_path: Path) -> None:
        """Test reading and writing preserves data."""
        original = LibraryTable(table_type="sym")
        original.add_entry(
            LibraryEntry(
                name="lib1",
                uri="${KIPRJMOD}/lib1.kicad_sym",
                descr="Library 1",
            )
        )
        original.add_entry(
            LibraryEntry(
                name="lib2",
                uri="${KIPRJMOD}/lib2.kicad_sym",
                descr="Library 2",
            )
        )

        table_file = tmp_path / "sym-lib-table"
        original.to_file(table_file)

        # Read it back
        restored = LibraryTable.from_file(table_file, table_type="sym")

        assert len(restored.entries) == 2
        assert restored.get_entry("lib1") is not None
        assert restored.get_entry("lib2") is not None
        assert restored.get_entry("lib1").descr == "Library 1"

    def test_from_file_multiple_entries(self, tmp_path: Path) -> None:
        """Test parsing file with multiple entries."""
        table_file = tmp_path / "sym-lib-table"
        content = """(sym-lib-table
  (version 7)
  (lib (name "lib1")
       (type "KiCad")
       (uri "${KIPRJMOD}/lib1.kicad_sym")
       (options "")
       (descr "Library 1"))
  (lib (name "lib2")
       (type "KiCad")
       (uri "${KIPRJMOD}/lib2.kicad_sym")
       (options "")
       (descr "Library 2"))
)
"""
        table_file.write_text(content)

        table = LibraryTable.from_file(table_file, table_type="sym")

        assert len(table.entries) == 2
        assert table.version == 7
        assert table.get_entry("lib1").descr == "Library 1"
        assert table.get_entry("lib2").descr == "Library 2"


class TestProjectConfig:
    """Tests for ProjectConfig class."""

    @pytest.fixture
    def test_project(self, tmp_path: Path) -> Path:
        """Create a test KiCad project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create .kicad_pro file
        (project_dir / "test_project.kicad_pro").write_text("(kicad_pcb (version 20211014))")

        return project_dir

    def test_init_valid_project(self, test_project: Path) -> None:
        """Test initializing with valid project directory."""
        config = ProjectConfig(test_project)

        assert config.project_dir == test_project
        assert config.project_file.name == "test_project.kicad_pro"

    def test_init_invalid_project_raises(self, tmp_path: Path) -> None:
        """Test that initializing with non-project directory raises error."""
        with pytest.raises(ValueError, match="No .kicad_pro"):
            ProjectConfig(tmp_path)

    def test_init_current_directory(self, test_project: Path) -> None:
        """Test initializing with current working directory."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(test_project)
            config = ProjectConfig()
            assert config.project_dir == test_project
        finally:
            os.chdir(original_cwd)

    def test_find_project_root_current_dir(self, test_project: Path) -> None:
        """Test finding project root from current directory."""
        root = ProjectConfig.find_project_root(test_project)

        assert root == test_project

    def test_find_project_root_nested_dir(self, test_project: Path) -> None:
        """Test finding project root from nested subdirectory."""
        nested = test_project / "src" / "components"
        nested.mkdir(parents=True)

        root = ProjectConfig.find_project_root(nested)

        assert root == test_project

    def test_find_project_root_not_found(self, tmp_path: Path) -> None:
        """Test finding project root when none exists."""
        root = ProjectConfig.find_project_root(tmp_path)

        assert root is None

    def test_get_symbol_lib_table_nonexistent(self, test_project: Path) -> None:
        """Test getting symbol table when file doesn't exist."""
        config = ProjectConfig(test_project)

        table = config.get_symbol_lib_table()

        assert len(table.entries) == 0
        assert table.filename == "sym-lib-table"

    def test_get_symbol_lib_table_existing(self, test_project: Path) -> None:
        """Test getting existing symbol library table."""
        table_file = test_project / "sym-lib-table"
        table_file.write_text(
            """(sym-lib-table
  (version 7)
  (lib (name "existing")
       (type "KiCad")
       (uri "path/to/existing.kicad_sym")
       (options "")
       (descr "Existing library"))
)
"""
        )

        config = ProjectConfig(test_project)
        table = config.get_symbol_lib_table()

        assert len(table.entries) == 1
        assert table.get_entry("existing") is not None

    def test_get_footprint_lib_table(self, test_project: Path) -> None:
        """Test getting footprint library table."""
        config = ProjectConfig(test_project)

        table = config.get_footprint_lib_table()

        assert len(table.entries) == 0
        assert table.filename == "fp-lib-table"

    def test_add_symbol_library(self, test_project: Path) -> None:
        """Test adding symbol library to project."""
        config = ProjectConfig(test_project)
        lib_path = Path("libraries/jlc-components.kicad_sym")

        config.add_symbol_library(
            name="jlc-components",
            lib_path=lib_path,
            description="JLCPCB components",
        )

        # Verify table was written
        table_file = test_project / "sym-lib-table"
        assert table_file.exists()

        # Verify entry was added
        table = config.get_symbol_lib_table()
        entry = table.get_entry("jlc-components")
        assert entry is not None
        assert "jlc-components" in entry.uri

    def test_add_symbol_library_absolute_path(self, test_project: Path) -> None:
        """Test adding symbol library with absolute path."""
        config = ProjectConfig(test_project)
        lib_dir = test_project / "libraries"
        lib_dir.mkdir()
        lib_file = lib_dir / "jlc-components.kicad_sym"
        lib_file.touch()

        config.add_symbol_library(
            name="jlc-components",
            lib_path=lib_file,
        )

        table = config.get_symbol_lib_table()
        entry = table.get_entry("jlc-components")
        assert entry is not None
        # Should be relative to project
        assert "libraries" in entry.uri or "${KIPRJMOD}" in entry.uri

    def test_add_footprint_library(self, test_project: Path) -> None:
        """Test adding footprint library to project."""
        config = ProjectConfig(test_project)
        fp_path = Path("libraries/footprints.pretty")

        config.add_footprint_library(
            name="jlc-footprints",
            lib_path=fp_path,
            description="JLCPCB footprints",
        )

        # Verify table was written
        table_file = test_project / "fp-lib-table"
        assert table_file.exists()

        # Verify entry was added
        table = config.get_footprint_lib_table()
        entry = table.get_entry("jlc-footprints")
        assert entry is not None

    def test_add_footprint_library_absolute_path(self, test_project: Path) -> None:
        """Test adding footprint library with absolute path."""
        config = ProjectConfig(test_project)
        lib_dir = test_project / "libraries"
        lib_dir.mkdir()
        fp_dir = lib_dir / "footprints.pretty"
        fp_dir.mkdir()

        config.add_footprint_library(
            name="jlc-footprints",
            lib_path=fp_dir,
        )

        table = config.get_footprint_lib_table()
        entry = table.get_entry("jlc-footprints")
        assert entry is not None

    def test_create_library_directories(self, test_project: Path) -> None:
        """Test creating standard library directories."""
        config = ProjectConfig(test_project)

        symbol_dir, footprint_dir = config.create_library_directories()

        assert symbol_dir == test_project / "libraries"
        assert footprint_dir == test_project / "libraries" / "footprints.pretty"
        assert symbol_dir.exists()
        assert footprint_dir.exists()

    def test_create_library_directories_idempotent(self, test_project: Path) -> None:
        """Test that creating directories multiple times doesn't fail."""
        config = ProjectConfig(test_project)

        # Call twice
        config.create_library_directories()
        config.create_library_directories()

        # Should still work
        assert (test_project / "libraries").exists()

    def test_add_multiple_libraries(self, test_project: Path) -> None:
        """Test adding multiple libraries to a project."""
        config = ProjectConfig(test_project)

        config.add_symbol_library("lib1", Path("path/to/lib1.kicad_sym"))
        config.add_symbol_library("lib2", Path("path/to/lib2.kicad_sym"))
        config.add_footprint_library("fp1", Path("path/to/fp1.pretty"))

        sym_table = config.get_symbol_lib_table()
        fp_table = config.get_footprint_lib_table()

        assert len(sym_table.entries) == 2
        assert len(fp_table.entries) == 1
        assert sym_table.get_entry("lib1") is not None
        assert sym_table.get_entry("lib2") is not None
        assert fp_table.get_entry("fp1") is not None

    def test_library_entry_paths_use_forward_slashes(self, test_project: Path) -> None:
        """Test that library paths use forward slashes (KiCad convention)."""
        config = ProjectConfig(test_project)

        # Add library with relative path
        config.add_symbol_library("test", Path("dir\\with\\backslashes\\lib.kicad_sym"))

        table = config.get_symbol_lib_table()
        entry = table.get_entry("test")

        assert entry is not None
        # Should be converted to forward slashes
        assert "\\" not in entry.uri
        assert "/" in entry.uri
