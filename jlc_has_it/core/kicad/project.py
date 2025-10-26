"""KiCad project integration for adding component libraries."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LibraryEntry:
    """A single library entry in a library table."""

    name: str
    type_: str = "KiCad"
    uri: str = ""
    options: str = ""
    descr: str = ""

    def to_sexp(self) -> str:
        """Convert to S-expression format."""
        return (
            f'  (lib (name "{self.name}")\n'
            f'       (type "{self.type_}")\n'
            f'       (uri "{self.uri}")\n'
            f'       (options "{self.options}")\n'
            f'       (descr "{self.descr}"))\n'
        )

    @classmethod
    def from_sexp_dict(cls, data: dict) -> "LibraryEntry":
        """Create from S-expression parsed dict."""
        return cls(
            name=data.get("name", ""),
            type_=data.get("type", "KiCad"),
            uri=data.get("uri", ""),
            options=data.get("options", ""),
            descr=data.get("descr", ""),
        )


class LibraryTable:
    """Manages KiCad symbol or footprint library tables."""

    def __init__(self, table_type: str = "sym", version: int = 7) -> None:
        """Initialize library table.

        Args:
            table_type: "sym" for sym-lib-table or "fp" for fp-lib-table
            version: Library table version (default 7 for KiCad 9.0)
        """
        self.table_type = table_type
        self.version = version
        self.entries: dict[str, LibraryEntry] = {}
        self.filename = "sym-lib-table" if table_type == "sym" else "fp-lib-table"

    def add_entry(self, entry: LibraryEntry) -> None:
        """Add or update a library entry.

        Args:
            entry: LibraryEntry to add

        Raises:
            ValueError: If entry name is empty
        """
        if not entry.name:
            raise ValueError("Library entry must have a name")
        self.entries[entry.name] = entry

    def remove_entry(self, name: str) -> bool:
        """Remove a library entry.

        Args:
            name: Name of library to remove

        Returns:
            True if removed, False if not found
        """
        if name in self.entries:
            del self.entries[name]
            return True
        return False

    def get_entry(self, name: str) -> Optional[LibraryEntry]:
        """Get a library entry by name.

        Args:
            name: Name of library

        Returns:
            LibraryEntry or None if not found
        """
        return self.entries.get(name)

    def to_file(self, path: Path) -> None:
        """Write library table to file.

        Args:
            path: Path to sym-lib-table or fp-lib-table file
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create S-expression content
        lines = [f"({self.filename}\n", f"  (version {self.version})\n"]

        for entry in self.entries.values():
            lines.append(entry.to_sexp())

        lines.append(")\n")

        content = "".join(lines)
        path.write_text(content)

    @classmethod
    def from_file(cls, path: Path, table_type: str = "sym") -> "LibraryTable":
        """Read library table from file.

        Args:
            path: Path to sym-lib-table or fp-lib-table file
            table_type: "sym" or "fp"

        Returns:
            LibraryTable instance with parsed entries
        """
        table = cls(table_type=table_type)

        if not path.exists():
            return table

        content = path.read_text()

        # Simple regex-based parsing for library entries
        # Pattern: (lib (name "name") (type "KiCad") (uri "uri") (options "") (descr "descr"))
        entry_pattern = r'\(lib\s+\(name\s+"([^"]*)"\)\s+\(type\s+"([^"]*)"\)\s+\(uri\s+"([^"]*)"\)\s+\(options\s+"([^"]*)"\)\s+\(descr\s+"([^"]*)"\)\)\s*\n'

        for match in re.finditer(entry_pattern, content):
            name, type_, uri, options, descr = match.groups()
            entry = LibraryEntry(name=name, type_=type_, uri=uri, options=options, descr=descr)
            table.add_entry(entry)

        # Extract version
        version_match = re.search(r"\(version\s+(\d+)\)", content)
        if version_match:
            table.version = int(version_match.group(1))

        return table


class ProjectConfig:
    """Manages KiCad project configuration and library integration."""

    def __init__(self, project_dir: Optional[Path] = None) -> None:
        """Initialize project configuration.

        Args:
            project_dir: Path to KiCad project directory
        """
        self.project_dir = project_dir or Path.cwd()
        self._validate_project()

    def _validate_project(self) -> None:
        """Validate that project directory contains .kicad_pro file."""
        kicad_pro = next(self.project_dir.glob("*.kicad_pro"), None)
        if kicad_pro is None:
            raise ValueError(
                f"No .kicad_pro file found in {self.project_dir}. "
                "Not a valid KiCad project directory."
            )
        self.project_file = kicad_pro

    @staticmethod
    def find_project_root(start_path: Path) -> Optional[Path]:
        """Detect KiCad project root from a given path.

        Searches up the directory tree for a .kicad_pro file.

        Args:
            start_path: Starting path to search from

        Returns:
            Path to project root if found, None otherwise
        """
        current = start_path.resolve()

        # Search up the directory tree
        for _ in range(10):  # Reasonable limit to prevent infinite loops
            kicad_pro = next(current.glob("*.kicad_pro"), None)
            if kicad_pro is not None:
                return current
            parent = current.parent
            if parent == current:
                # Reached filesystem root
                break
            current = parent

        return None

    def get_symbol_lib_table(self) -> LibraryTable:
        """Get symbol library table for this project.

        Returns:
            LibraryTable instance (may be empty if file doesn't exist)
        """
        table_path = self.project_dir / "sym-lib-table"
        return LibraryTable.from_file(table_path, table_type="sym")

    def get_footprint_lib_table(self) -> LibraryTable:
        """Get footprint library table for this project.

        Returns:
            LibraryTable instance (may be empty if file doesn't exist)
        """
        table_path = self.project_dir / "fp-lib-table"
        return LibraryTable.from_file(table_path, table_type="fp")

    def add_symbol_library(
        self,
        name: str,
        lib_path: Path,
        description: str = "",
        options: str = "",
    ) -> None:
        """Add a symbol library to the project.

        Args:
            name: Library name (e.g., "jlc-components")
            lib_path: Path to .kicad_sym file (relative or absolute)
            description: Library description
            options: Library options (usually empty)
        """
        table = self.get_symbol_lib_table()

        # Convert to relative path if absolute
        if lib_path.is_absolute():
            try:
                lib_path_rel = lib_path.relative_to(self.project_dir)
                uri = str(lib_path_rel)
            except ValueError:
                # Path is outside project, use absolute with ${KIPRJMOD}
                uri = f"${{KIPRJMOD}}/{lib_path.name}"
        else:
            uri = str(lib_path)

        # Replace forward slashes with correct format for KiCad
        uri = uri.replace("\\", "/")

        entry = LibraryEntry(
            name=name,
            type_="KiCad",
            uri=uri,
            options=options,
            descr=description,
        )

        table.add_entry(entry)
        table_path = self.project_dir / "sym-lib-table"
        table.to_file(table_path)

    def add_footprint_library(
        self,
        name: str,
        lib_path: Path,
        description: str = "",
        options: str = "",
    ) -> None:
        """Add a footprint library to the project.

        Args:
            name: Library name (e.g., "jlc-footprints")
            lib_path: Path to .pretty directory (relative or absolute)
            description: Library description
            options: Library options (usually empty)
        """
        table = self.get_footprint_lib_table()

        # Convert to relative path if absolute
        if lib_path.is_absolute():
            try:
                lib_path_rel = lib_path.relative_to(self.project_dir)
                uri = str(lib_path_rel)
            except ValueError:
                # Path is outside project, use with ${KIPRJMOD}
                uri = f"${{KIPRJMOD}}/{lib_path.name}"
        else:
            uri = str(lib_path)

        # Replace forward slashes with correct format for KiCad
        uri = uri.replace("\\", "/")

        entry = LibraryEntry(
            name=name,
            type_="KiCad",
            uri=uri,
            options=options,
            descr=description,
        )

        table.add_entry(entry)
        table_path = self.project_dir / "fp-lib-table"
        table.to_file(table_path)

    def create_library_directories(self) -> tuple[Path, Path]:
        """Create standard library directories in the project.

        Returns:
            Tuple of (symbol_dir, footprint_dir) paths
        """
        symbol_dir = self.project_dir / "libraries"
        footprint_dir = symbol_dir / "footprints.pretty"

        symbol_dir.mkdir(parents=True, exist_ok=True)
        footprint_dir.mkdir(parents=True, exist_ok=True)

        return symbol_dir, footprint_dir
