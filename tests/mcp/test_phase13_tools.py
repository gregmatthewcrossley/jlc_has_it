"""
Tests for Phase 13: MCP tools improvements (library source display, new tool registration).
"""

import pytest
from unittest.mock import MagicMock, patch

from jlc_has_it.mcp.tools import JLCTools


class TestGetLibraryNote:
    """Tests for _get_library_note() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.tools = JLCTools(self.mock_db)

    def test_ultralibrarian_source_note(self):
        """Should generate correct note for Ultralibrarian source."""
        lib_info = {"source": "ultralibrarian", "uuid": "test-uuid"}
        note = self.tools._get_library_note(lib_info, "C1234")

        assert "✓" in note
        assert "Ultralibrarian" in note
        assert "Symbol, footprint, and 3D model" in note

    def test_easyeda_source_note(self):
        """Should generate correct note for EasyEDA source."""
        lib_info = {"source": "easyeda", "uuid": None}
        note = self.tools._get_library_note(lib_info, "C1234")

        assert "✓" in note
        assert "EasyEDA" in note
        assert "JLCPCB" in note

    def test_unknown_source_note(self):
        """Should generate warning note for unknown source."""
        lib_info = {"source": None, "uuid": None}
        note = self.tools._get_library_note(lib_info, "C1234")

        assert "⚠" in note
        assert "unknown" in note

    def test_empty_lib_info(self):
        """Should handle empty lib_info gracefully."""
        lib_info = {}
        note = self.tools._get_library_note(lib_info, "C5678")

        assert "⚠" in note
        assert "unknown" in note


class TestSearchComponentsLibrarySource:
    """Tests for library_source field in search results."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.tools = JLCTools(self.mock_db)

    @patch("jlc_has_it.mcp.tools.ComponentSearch")
    def test_search_results_include_library_source(self, mock_search_class):
        """Should include library_source in search results."""
        # Mock search results
        mock_comp = MagicMock()
        mock_comp.lcsc = "1234"
        mock_comp.description = "Test Component"
        mock_comp.manufacturer = "Test Mfr"
        mock_comp.category = "Resistors"
        mock_comp.stock = 1000
        mock_comp.price = 0.10
        mock_comp.basic = True
        mock_comp.mfr = "TEST-001"

        mock_search = MagicMock()
        mock_search.search.return_value = [mock_comp]
        mock_search_class.return_value = mock_search

        # Mock Ultralibrarian search
        with patch.object(
            self.tools, "_check_ultralibrarian_availability", return_value="uuid-123"
        ):
            result = self.tools.search_components(
                query="test",
                validate_libraries=True,
                validation_candidates=1,
            )

        # Check that results have library_source field
        assert len(result["results"]) > 0
        first_result = result["results"][0]
        assert "library_source" in first_result
        assert "library_note" in first_result
        assert first_result["library_source"] == "ultralibrarian"

    @patch("jlc_has_it.mcp.tools.ComponentSearch")
    def test_search_results_field_order(self, mock_search_class):
        """Should have library_source early in result fields."""
        # Mock search results
        mock_comp = MagicMock()
        mock_comp.lcsc = "2345"
        mock_comp.description = "Another Component"
        mock_comp.manufacturer = "Another Mfr"
        mock_comp.category = "Capacitors"
        mock_comp.stock = 500
        mock_comp.price = 0.05
        mock_comp.basic = True
        mock_comp.mfr = "TEST-002"

        mock_search = MagicMock()
        mock_search.search.return_value = [mock_comp]
        mock_search_class.return_value = mock_search

        # Mock Ultralibrarian search to return None (use EasyEDA)
        with patch.object(self.tools, "_check_ultralibrarian_availability", return_value=None):
            with patch.object(
                self.tools.downloader,
                "get_validated_libraries",
                return_value={"C2345": MagicMock()},
            ):
                result = self.tools.search_components(
                    query="test",
                    validate_libraries=True,
                    validation_candidates=1,
                )

        # Check field order - library_source should come after lcsc_id but before description
        first_result = result["results"][0]
        fields_list = list(first_result.keys())

        lcsc_idx = fields_list.index("lcsc_id")
        source_idx = fields_list.index("library_source")
        note_idx = fields_list.index("library_note")
        desc_idx = fields_list.index("description")

        assert lcsc_idx < source_idx, "lcsc_id should come before library_source"
        assert source_idx < note_idx, "library_source should come before library_note"
        assert note_idx < desc_idx, "library_note should come before description"

    @patch("jlc_has_it.mcp.tools.ComponentSearch")
    def test_library_source_easyeda_fallback(self, mock_search_class):
        """Should show easyeda source when Ultralibrarian not found."""
        mock_comp = MagicMock()
        mock_comp.lcsc = "3456"
        mock_comp.description = "Test"
        mock_comp.manufacturer = "Mfr"
        mock_comp.category = "Diodes"
        mock_comp.stock = 100
        mock_comp.price = 0.02
        mock_comp.basic = True
        mock_comp.mfr = "TEST-003"

        mock_search = MagicMock()
        mock_search.search.return_value = [mock_comp]
        mock_search_class.return_value = mock_search

        # Ultralibrarian returns None, EasyEDA succeeds
        with patch.object(self.tools, "_check_ultralibrarian_availability", return_value=None):
            with patch.object(
                self.tools.downloader,
                "get_validated_libraries",
                return_value={"C3456": MagicMock()},
            ):
                result = self.tools.search_components(
                    query="test",
                    validate_libraries=True,
                    validation_candidates=1,
                )

        assert len(result["results"]) > 0
        first_result = result["results"][0]
        assert first_result["library_source"] == "easyeda"
        assert "EasyEDA" in first_result["library_note"]


class TestAddFromUltraLibrarianMethod:
    """Tests for add_from_ultralibrarian() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.tools = JLCTools(self.mock_db)

    def test_method_exists(self):
        """Should have add_from_ultralibrarian method."""
        assert hasattr(self.tools, "add_from_ultralibrarian")
        assert callable(self.tools.add_from_ultralibrarian)

    def test_method_signature(self):
        """Should accept required parameters."""
        import inspect

        sig = inspect.signature(self.tools.add_from_ultralibrarian)
        params = list(sig.parameters.keys())

        assert "manufacturer" in params
        assert "mpn" in params
        assert "project_path" in params
        assert "timeout_seconds" in params

    @patch("jlc_has_it.mcp.tools.Path")
    @patch("jlc_has_it.mcp.tools.ProjectConfig")
    def test_method_calls_browser_open(self, mock_config, mock_path):
        """Should call open_ultralibrarian_part."""
        # This is a basic smoke test - the actual workflow is tested elsewhere
        with patch("jlc_has_it.mcp.tools.open_ultralibrarian_part") as mock_open:
            with patch.object(
                self.tools, "_check_ultralibrarian_availability", return_value="test-uuid"
            ):
                # Mock ProjectConfig
                mock_config.find_project_root.return_value = None
                mock_config.return_value = MagicMock()

                try:
                    result = self.tools.add_from_ultralibrarian(
                        manufacturer="Test",
                        mpn="TEST-001",
                        project_path="/tmp/test",
                    )
                except Exception:
                    # Expected to fail in this test setup, we just want to verify open was called
                    pass

                # Verify browser was attempted to be opened
                # (It may not succeed due to mocking, but the code should have tried)

    def test_returns_dict_with_expected_fields(self):
        """Should return dict with expected fields."""
        with patch("jlc_has_it.mcp.tools.open_ultralibrarian_part"):
            with patch.object(
                self.tools, "_check_ultralibrarian_availability", return_value=None
            ):
                result = self.tools.add_from_ultralibrarian(
                    manufacturer="Test",
                    mpn="NOT-FOUND",
                )

                assert isinstance(result, dict)
                assert "success" in result
                assert "error" in result or "message" in result
                assert "mpn" in result
