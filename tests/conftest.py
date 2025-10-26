"""Pytest configuration and common fixtures."""

import pytest
from pathlib import Path
from typing import Any, Dict


@pytest.fixture
def sample_component_data() -> Dict[str, Any]:
    """Sample component data for testing."""
    return {
        "lcsc": "C12345",
        "mfr": "TEST-PART-001",
        "description": "Test Component 100nF 50V X7R 0402",
        "manufacturer": "Test Manufacturer",
        "category": "Capacitors",
        "subcategory": "Multilayer Ceramic Capacitors MLCC - SMD/SMT",
        "joints": 2,
        "basic": True,
        "stock": 5000,
        "price": [
            {"qty": 1, "price": 0.0012},
            {"qty": 10, "price": 0.0010},
            {"qty": 100, "price": 0.0008},
        ],
        "attributes": {
            "Capacitance": {"value": 100, "unit": "nF"},
            "Voltage": {"value": 50, "unit": "V"},
            "Tolerance": {"value": 10, "unit": "%"},
            "Package": "0402",
            "Temperature Coefficient": "X7R",
        },
    }


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary KiCad project directory structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create typical KiCad project structure
    (project_dir / "test_project.kicad_pro").touch()
    (project_dir / "test_project.kicad_sch").touch()

    libraries_dir = project_dir / "libraries"
    libraries_dir.mkdir()

    footprints_dir = libraries_dir / "footprints.pretty"
    footprints_dir.mkdir()

    models_dir = libraries_dir / "3d_models"
    models_dir.mkdir()

    return project_dir


@pytest.fixture
def mock_database_connection(mocker: Any) -> Any:
    """Mock database connection for testing."""
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.execute.return_value = mock_cursor
    return mock_conn
