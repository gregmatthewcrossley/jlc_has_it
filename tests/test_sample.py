"""Sample tests to verify pytest is working correctly."""

from pathlib import Path
from typing import Any


def test_pytest_is_working() -> None:
    """Verify pytest is properly configured."""
    assert True


def test_sample_component_data_fixture(sample_component_data: dict[str, Any]) -> None:
    """Test that sample component data fixture works."""
    # Sample data uses integer LCSC ID (real database format)
    assert sample_component_data["lcsc"] == 12345
    assert sample_component_data["basic"] is True
    assert sample_component_data["stock"] == 5000
    assert "Capacitance" in sample_component_data.get("extra", {}).get("attributes", {})


def test_temp_project_dir_fixture(temp_project_dir: Path) -> None:
    """Test that temp project directory fixture works."""
    assert temp_project_dir.exists()
    assert (temp_project_dir / "test_project.kicad_pro").exists()
    assert (temp_project_dir / "libraries").exists()
    assert (temp_project_dir / "libraries" / "footprints.pretty").exists()
    assert (temp_project_dir / "libraries" / "3d_models").exists()


def test_mock_database_connection_fixture(mock_database_connection: Any) -> None:
    """Test that mock database connection fixture works."""
    cursor = mock_database_connection.cursor()
    assert cursor is not None
    mock_database_connection.cursor.assert_called_once()
