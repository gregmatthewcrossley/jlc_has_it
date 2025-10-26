"""Tests for component data models."""

import json

import pytest

from jlc_has_it.core.models import AttributeValue, Component, PriceTier


class TestPriceTier:
    """Tests for PriceTier model."""

    def test_from_dict(self) -> None:
        """Test creating PriceTier from dictionary."""
        tier = PriceTier.from_dict({"qty": 10, "price": 0.0012})
        assert tier.qty == 10
        assert tier.price == 0.0012

    def test_from_dict_with_string_values(self) -> None:
        """Test creating PriceTier with string values."""
        tier = PriceTier.from_dict({"qty": "100", "price": "0.0008"})
        assert tier.qty == 100
        assert tier.price == 0.0008


class TestAttributeValue:
    """Tests for AttributeValue model."""

    def test_from_dict_with_unit(self) -> None:
        """Test creating AttributeValue from dict with unit."""
        attr = AttributeValue.from_dict({"value": 100, "unit": "nF"})
        assert attr.value == 100
        assert attr.unit == "nF"

    def test_from_dict_without_unit(self) -> None:
        """Test creating AttributeValue from dict without unit."""
        attr = AttributeValue.from_dict({"value": "X7R"})
        assert attr.value == "X7R"
        assert attr.unit is None

    def test_from_scalar_number(self) -> None:
        """Test creating AttributeValue from scalar number."""
        attr = AttributeValue.from_dict(50)
        assert attr.value == 50
        assert attr.unit is None

    def test_from_scalar_string(self) -> None:
        """Test creating AttributeValue from scalar string."""
        attr = AttributeValue.from_dict("0402")
        assert attr.value == "0402"
        assert attr.unit is None


class TestComponent:
    """Tests for Component model."""

    @pytest.fixture
    def sample_db_row(self) -> dict[str, object]:
        """Sample database row as dictionary."""
        return {
            "lcsc": "C12345",
            "mfr": "TEST-PART-001",
            "description": "Test Component 100nF 50V X7R 0402",
            "manufacturer": "Test Manufacturer",
            "category": "Capacitors",
            "subcategory": "Multilayer Ceramic Capacitors MLCC - SMD/SMT",
            "joints": 2,
            "basic": 1,
            "stock": 5000,
            "price": json.dumps(
                [
                    {"qty": 1, "price": 0.0012},
                    {"qty": 10, "price": 0.0010},
                    {"qty": 100, "price": 0.0008},
                ]
            ),
            "attributes": json.dumps(
                {
                    "Capacitance": {"value": 100, "unit": "nF"},
                    "Voltage": {"value": 50, "unit": "V"},
                    "Tolerance": {"value": 10, "unit": "%"},
                    "Package": "0402",
                    "Temperature Coefficient": "X7R",
                }
            ),
        }

    def test_from_db_row(self, sample_db_row: dict[str, object]) -> None:
        """Test creating Component from database row."""
        component = Component.from_db_row(sample_db_row)

        assert component.lcsc == "C12345"
        assert component.mfr == "TEST-PART-001"
        assert component.description == "Test Component 100nF 50V X7R 0402"
        assert component.manufacturer == "Test Manufacturer"
        assert component.category == "Capacitors"
        assert component.subcategory == "Multilayer Ceramic Capacitors MLCC - SMD/SMT"
        assert component.joints == 2
        assert component.basic is True
        assert component.stock == 5000

    def test_price_tiers_parsing(self, sample_db_row: dict[str, object]) -> None:
        """Test that price tiers are parsed correctly."""
        component = Component.from_db_row(sample_db_row)

        assert len(component.price_tiers) == 3
        assert component.price_tiers[0].qty == 1
        assert component.price_tiers[0].price == 0.0012
        assert component.price_tiers[1].qty == 10
        assert component.price_tiers[1].price == 0.0010
        assert component.price_tiers[2].qty == 100
        assert component.price_tiers[2].price == 0.0008

    def test_attributes_parsing(self, sample_db_row: dict[str, object]) -> None:
        """Test that attributes are parsed correctly."""
        component = Component.from_db_row(sample_db_row)

        capacitance = component.get_attribute("Capacitance")
        assert isinstance(capacitance, AttributeValue)
        assert capacitance.value == 100
        assert capacitance.unit == "nF"

        voltage = component.get_attribute("Voltage")
        assert isinstance(voltage, AttributeValue)
        assert voltage.value == 50
        assert voltage.unit == "V"

        # Package is a plain string, not an AttributeValue
        package = component.get_attribute("Package")
        assert package == "0402"

    def test_price_property(self, sample_db_row: dict[str, object]) -> None:
        """Test the price property returns unit price."""
        component = Component.from_db_row(sample_db_row)
        assert component.price == 0.0012

    def test_get_attribute_value(self, sample_db_row: dict[str, object]) -> None:
        """Test getting raw attribute values."""
        component = Component.from_db_row(sample_db_row)

        assert component.get_attribute_value("Capacitance") == 100
        assert component.get_attribute_value("Voltage") == 50
        assert component.get_attribute_value("Package") == "0402"
        assert component.get_attribute_value("NonExistent") is None

    def test_empty_price_tiers(self, sample_db_row: dict[str, object]) -> None:
        """Test component with no price tiers."""
        sample_db_row["price"] = json.dumps([])
        component = Component.from_db_row(sample_db_row)

        assert component.price_tiers == []
        assert component.price == 0.0
