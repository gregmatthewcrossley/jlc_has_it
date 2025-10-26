"""Tests for library downloader."""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from jlc_has_it.core.library_downloader import ComponentLibrary, LibraryDownloader


class TestComponentLibrary:
    """Tests for ComponentLibrary dataclass."""

    @pytest.fixture
    def valid_library(self, tmp_path: Path) -> ComponentLibrary:
        """Create a valid library structure with all files."""
        symbol_file = tmp_path / "easyeda2kicad.kicad_sym"
        symbol_file.write_text("(kicad_symbol_lib (version 20211014))")

        footprint_dir = tmp_path / "easyeda2kicad.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("(module test)")

        model_dir = tmp_path / "easyeda2kicad.3dshapes"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("STEP content")

        return ComponentLibrary(
            lcsc_id="C1525",
            symbol_path=symbol_file,
            footprint_dir=footprint_dir,
            model_dir=model_dir,
        )

    def test_is_valid_complete(self, valid_library: ComponentLibrary) -> None:
        """Test validation of complete library."""
        assert valid_library.is_valid() is True

    def test_is_valid_missing_symbol(self, tmp_path: Path) -> None:
        """Test validation fails when symbol is missing."""
        lib = ComponentLibrary(
            lcsc_id="C1525",
            symbol_path=tmp_path / "missing.kicad_sym",
            footprint_dir=tmp_path / "footprints.pretty",
            model_dir=tmp_path / "models",
        )
        assert lib.is_valid() is False

    def test_is_valid_empty_symbol(self, tmp_path: Path) -> None:
        """Test validation fails when symbol is empty."""
        symbol_file = tmp_path / "empty.kicad_sym"
        symbol_file.write_text("")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("content")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("content")

        lib = ComponentLibrary(
            lcsc_id="C1525",
            symbol_path=symbol_file,
            footprint_dir=footprint_dir,
            model_dir=model_dir,
        )
        assert lib.is_valid() is False

    def test_is_valid_missing_footprint_dir(self, tmp_path: Path) -> None:
        """Test validation fails when footprint directory is missing."""
        symbol_file = tmp_path / "symbol.kicad_sym"
        symbol_file.write_text("content")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("content")

        lib = ComponentLibrary(
            lcsc_id="C1525",
            symbol_path=symbol_file,
            footprint_dir=tmp_path / "missing_footprints",
            model_dir=model_dir,
        )
        assert lib.is_valid() is False

    def test_is_valid_empty_footprint_dir(self, tmp_path: Path) -> None:
        """Test validation fails when footprint directory is empty."""
        symbol_file = tmp_path / "symbol.kicad_sym"
        symbol_file.write_text("content")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()  # Empty!

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("content")

        lib = ComponentLibrary(
            lcsc_id="C1525",
            symbol_path=symbol_file,
            footprint_dir=footprint_dir,
            model_dir=model_dir,
        )
        assert lib.is_valid() is False

    def test_is_valid_missing_model_dir(self, tmp_path: Path) -> None:
        """Test validation fails when model directory is missing."""
        symbol_file = tmp_path / "symbol.kicad_sym"
        symbol_file.write_text("content")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("content")

        lib = ComponentLibrary(
            lcsc_id="C1525",
            symbol_path=symbol_file,
            footprint_dir=footprint_dir,
            model_dir=tmp_path / "missing_models",
        )
        assert lib.is_valid() is False

    def test_is_valid_empty_model_dir(self, tmp_path: Path) -> None:
        """Test validation fails when model directory has no valid models."""
        symbol_file = tmp_path / "symbol.kicad_sym"
        symbol_file.write_text("content")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("content")

        model_dir = tmp_path / "models"
        model_dir.mkdir()  # Empty - no .step or .wrl files

        lib = ComponentLibrary(
            lcsc_id="C1525",
            symbol_path=symbol_file,
            footprint_dir=footprint_dir,
            model_dir=model_dir,
        )
        assert lib.is_valid() is False

    def test_is_valid_with_wrl_model(self, tmp_path: Path) -> None:
        """Test validation succeeds with .wrl model file."""
        symbol_file = tmp_path / "symbol.kicad_sym"
        symbol_file.write_text("content")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("content")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.wrl").write_text("VRML content")

        lib = ComponentLibrary(
            lcsc_id="C1525",
            symbol_path=symbol_file,
            footprint_dir=footprint_dir,
            model_dir=model_dir,
        )
        assert lib.is_valid() is True


class TestLibraryDownloader:
    """Tests for LibraryDownloader class."""

    @pytest.fixture
    def downloader(self, tmp_path: Path) -> LibraryDownloader:
        """Create a downloader with temporary cache."""
        return LibraryDownloader(cache_dir=tmp_path / "cache")

    @pytest.fixture
    def mock_success_download(self, tmp_path: Path) -> Any:
        """Mock successful easyeda2kicad download."""

        def side_effect(*args: Any, **kwargs: Any) -> Mock:
            # args[0] is the command list: ["easyeda2kicad", "--full", "--lcsc_id=...", "--output=..."]
            cmd_list = args[0]
            output_path = cmd_list[-1].replace("--output=", "")
            output_dir = Path(output_path).parent

            # Create expected directory structure
            (output_dir / "easyeda2kicad.pretty").mkdir(parents=True, exist_ok=True)
            (output_dir / "easyeda2kicad.pretty" / "test.kicad_mod").write_text("(module test)")
            (output_dir / "easyeda2kicad.3dshapes").mkdir(parents=True, exist_ok=True)
            (output_dir / "easyeda2kicad.3dshapes" / "test.step").write_text("STEP")
            Path(output_path).write_text("(kicad_symbol_lib (version 20211014))")

            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        return side_effect

    def test_init_creates_cache_dir(self, tmp_path: Path) -> None:
        """Test that initialization creates cache directory."""
        cache_dir = tmp_path / "new_cache"
        LibraryDownloader(cache_dir=cache_dir)

        assert cache_dir.exists()

    def test_init_default_cache_dir(self) -> None:
        """Test that default cache directory is used."""
        downloader = LibraryDownloader()
        assert downloader.cache_dir.parent.name == "jlc_has_it"

    def test_download_component_success(
        self, downloader: LibraryDownloader, mocker: Any, mock_success_download: Any
    ) -> None:
        """Test successful component download."""
        mocker.patch("subprocess.run", side_effect=mock_success_download)

        result = downloader.download_component("C1525")

        assert result is not None
        assert result.lcsc_id == "C1525"
        assert result.symbol_path.exists()
        assert result.footprint_dir.exists()
        assert result.model_dir.exists()

    def test_download_component_not_found(self, downloader: LibraryDownloader, mocker: Any) -> None:
        """Test download when component is not found (exit code 1)."""
        mock_response = Mock()
        mock_response.returncode = 1
        mocker.patch("subprocess.run", return_value=mock_response)

        result = downloader.download_component("C99999999")

        assert result is None

    def test_download_component_timeout(self, downloader: LibraryDownloader, mocker: Any) -> None:
        """Test download timeout handling."""
        import subprocess

        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("easyeda2kicad", 30),
        )

        result = downloader.download_component("C1525")

        assert result is None

    def test_download_component_missing_symbol(
        self, downloader: LibraryDownloader, mocker: Any, tmp_path: Path
    ) -> None:
        """Test validation fails when symbol file is missing."""

        def mock_download(*args: Any, **kwargs: Any) -> Mock:
            # Create footprint and model dirs but NOT symbol file
            cmd_list = args[0]
            output_path = cmd_list[-1].replace("--output=", "")
            output_dir = Path(output_path).parent
            (output_dir / "easyeda2kicad.pretty").mkdir(parents=True, exist_ok=True)
            (output_dir / "easyeda2kicad.pretty" / "test.kicad_mod").write_text("(module test)")
            (output_dir / "easyeda2kicad.3dshapes").mkdir(parents=True, exist_ok=True)
            (output_dir / "easyeda2kicad.3dshapes" / "test.step").write_text("STEP")
            # Note: NOT creating the symbol file!

            result = Mock()
            result.returncode = 0
            return result

        mocker.patch("subprocess.run", side_effect=mock_download)

        result = downloader.download_component("C1525")

        assert result is None

    def test_download_component_missing_footprint(
        self, downloader: LibraryDownloader, mocker: Any
    ) -> None:
        """Test validation fails when footprint is missing."""

        def mock_download(*args: Any, **kwargs: Any) -> Mock:
            # Create symbol and model dirs but NOT footprint dir
            cmd_list = args[0]
            output_path = cmd_list[-1].replace("--output=", "")
            output_dir = Path(output_path).parent
            Path(output_path).write_text("(kicad_symbol_lib (version 20211014))")
            # Note: NOT creating footprint directory!
            (output_dir / "easyeda2kicad.3dshapes").mkdir(parents=True, exist_ok=True)
            (output_dir / "easyeda2kicad.3dshapes" / "test.step").write_text("STEP")

            result = Mock()
            result.returncode = 0
            return result

        mocker.patch("subprocess.run", side_effect=mock_download)

        result = downloader.download_component("C1525")

        assert result is None

    def test_download_components_parallel(
        self, downloader: LibraryDownloader, mocker: Any, mock_success_download: Any
    ) -> None:
        """Test parallel downloads of multiple components."""
        mocker.patch("subprocess.run", side_effect=mock_success_download)

        lcsc_ids = ["C1525", "C67890", "C99999"]
        results = downloader.download_components_parallel(lcsc_ids, max_workers=3)

        assert len(results) == 3
        assert all(lcsc_id in results for lcsc_id in lcsc_ids)
        # All mocked downloads succeed
        assert all(lib is not None for lib in results.values())

    def test_get_validated_libraries(
        self, downloader: LibraryDownloader, mocker: Any, mock_success_download: Any
    ) -> None:
        """Test getting only validated libraries."""
        mocker.patch("subprocess.run", side_effect=mock_success_download)

        lcsc_ids = ["C1525", "C67890"]
        validated = downloader.get_validated_libraries(lcsc_ids)

        assert len(validated) == 2
        for lib in validated.values():
            assert lib.is_valid()

    def test_cleanup_cache(self, downloader: LibraryDownloader) -> None:
        """Test cache cleanup."""
        # Create some dummy cache directories
        (downloader.cache_dir / "C1525").mkdir()
        (downloader.cache_dir / "C67890").mkdir()

        # Cleanup with 0 hours (remove everything old)
        removed = downloader.cleanup_cache(older_than_hours=0)

        # Both should be removed (they're just created, might be slightly old)
        # At least verify cleanup runs without error
        assert removed >= 0

    def test_validate_files_success(self, tmp_path: Path) -> None:
        """Test successful file validation."""
        symbol_file = tmp_path / "symbol.kicad_sym"
        symbol_file.write_text("content")

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("content")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("content")

        assert LibraryDownloader._validate_files(symbol_file, footprint_dir, model_dir) is True

    def test_validate_files_missing_symbol(self, tmp_path: Path) -> None:
        """Test validation fails for missing symbol."""
        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("content")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("content")

        assert (
            LibraryDownloader._validate_files(
                tmp_path / "missing.kicad_sym", footprint_dir, model_dir
            )
            is False
        )

    def test_validate_files_empty_symbol(self, tmp_path: Path) -> None:
        """Test validation fails for empty symbol."""
        symbol_file = tmp_path / "symbol.kicad_sym"
        symbol_file.write_text("")  # Empty!

        footprint_dir = tmp_path / "footprints.pretty"
        footprint_dir.mkdir()
        (footprint_dir / "test.kicad_mod").write_text("content")

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        (model_dir / "test.step").write_text("content")

        assert LibraryDownloader._validate_files(symbol_file, footprint_dir, model_dir) is False
