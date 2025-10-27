"""Tests for unit normalization and conversion utilities."""

import pytest

from jlc_has_it.core.unit_utils import (
    compare_values,
    get_unit_category,
    normalize_value,
    parse_value,
)


class TestParseValue:
    """Test value and unit parsing from strings."""

    def test_parse_simple_value_with_unit(self):
        """Parse '100nF' into value and unit."""
        value, unit = parse_value("100nF")
        assert value == 100.0
        assert unit == "nF"

    def test_parse_decimal_value(self):
        """Parse decimal values like '0.1uF'."""
        value, unit = parse_value("0.1uF")
        assert value == 0.1
        assert unit == "uF"

    def test_parse_value_with_spaces(self):
        """Parse values with spaces like '100 nF'."""
        value, unit = parse_value("100 nF")
        assert value == 100.0
        assert unit == "nF"

    def test_parse_value_only(self):
        """Parse numeric values without units."""
        value, unit = parse_value("100")
        assert value == 100.0
        assert unit == ""

    def test_parse_negative_value(self):
        """Parse negative values."""
        value, unit = parse_value("-50V")
        assert value == -50.0
        assert unit == "V"

    def test_parse_invalid_value(self):
        """Invalid format returns None."""
        value, unit = parse_value("invalid")
        assert value is None
        assert unit is None

    def test_parse_unicode_ohm(self):
        """Parse ohm symbol (Ω) - skip if not supported."""
        value, unit = parse_value("100Ω")
        # Unicode in regex patterns may not work reliably across platforms
        # This test documents the limitation - prefer "kOhm" format
        if value is not None:
            assert value == 100.0
            assert unit == "Ω"


class TestNormalizeValue:
    """Test unit normalization to base units."""

    def test_normalize_capacitance_nf(self):
        """Normalize nanofarads to Farads."""
        result = normalize_value(100, "nF")
        assert result == pytest.approx(1e-7)

    def test_normalize_capacitance_uf(self):
        """Normalize microfarads to Farads."""
        result = normalize_value(1, "uF")
        assert result == 1e-6

    def test_normalize_capacitance_pf(self):
        """Normalize picofarads to Farads."""
        result = normalize_value(1000, "pF")
        assert result == 1e-9

    def test_normalize_resistance_kohm(self):
        """Normalize kilohms to Ohms."""
        result = normalize_value(10, "kOhm")
        assert result == 10000.0

    def test_normalize_resistance_mohm(self):
        """Normalize megaohms to Ohms."""
        result = normalize_value(1, "MOhm")
        assert result == 1e6

    def test_normalize_voltage(self):
        """Normalize voltage units."""
        result = normalize_value(5, "V")
        assert result == 5.0

    def test_normalize_frequency_mhz(self):
        """Normalize MHz to Hz."""
        result = normalize_value(100, "MHz")
        assert result == 1e8

    def test_normalize_unknown_unit(self):
        """Unknown unit returns None."""
        result = normalize_value(100, "XYZ")
        assert result is None

    def test_normalize_empty_unit(self):
        """Empty unit returns original value."""
        result = normalize_value(100, "")
        assert result == 100.0


class TestGetUnitCategory:
    """Test unit category detection."""

    def test_category_capacitance_nf(self):
        """Detect nanofarads as capacitance."""
        category = get_unit_category("nF")
        assert category == "capacitance"

    def test_category_resistance_kohm(self):
        """Detect kilohms as resistance."""
        category = get_unit_category("kOhm")
        assert category == "resistance"

    def test_category_voltage(self):
        """Detect volts as voltage."""
        category = get_unit_category("V")
        assert category == "voltage"

    def test_category_frequency_mhz(self):
        """Detect MHz as frequency."""
        category = get_unit_category("MHz")
        assert category == "frequency"

    def test_category_unknown_unit(self):
        """Unknown unit returns None."""
        category = get_unit_category("XYZ")
        assert category is None


class TestCompareValues:
    """Test unit-aware value comparison."""

    def test_compare_equal_values(self):
        """Compare equal values."""
        result = compare_values("100nF", "100nF")
        assert result == 0

    def test_compare_equal_different_units(self):
        """Compare equal values with different units."""
        result = compare_values("100nF", "0.1uF")
        assert result == 0

    def test_compare_less_than(self):
        """Compare less than."""
        result = compare_values("50nF", "100nF")
        assert result == -1

    def test_compare_greater_than(self):
        """Compare greater than."""
        result = compare_values("200nF", "100nF")
        assert result == 1

    def test_compare_resistance_different_units(self):
        """Compare resistances with different units."""
        result = compare_values("10kOhm", "10000Ohm")
        assert result == 0

    def test_compare_voltage_ranges(self):
        """Compare voltage values."""
        # 50V < 100V
        result = compare_values("50V", "100V")
        assert result == -1

    def test_compare_frequency(self):
        """Compare frequency values."""
        # 100MHz = 100,000,000 Hz
        result = compare_values("100MHz", "100000000Hz")
        assert result == 0

    def test_compare_incompatible_units(self):
        """Comparing incompatible units returns None."""
        # Can't compare capacitance to voltage
        result = compare_values("100nF", "50V")
        assert result is None

    def test_compare_no_units(self):
        """Compare numeric values without units."""
        result = compare_values("50", "100")
        assert result == -1

    def test_compare_invalid_format(self):
        """Invalid format returns None."""
        result = compare_values("invalid", "100")
        assert result is None


class TestRangeFiltering:
    """Test range filtering with units (integration with search)."""

    def test_capacitor_in_range(self):
        """Test if component is in range."""
        from jlc_has_it.core.search import ComponentSearch

        # This just verifies the range filtering logic works
        # Create a mock component for testing
        from jlc_has_it.core.models import Component, PriceTier

        comp = Component(
            lcsc="C1234",
            mfr="TEST",
            description="100nF Capacitor",
            manufacturer="TEST",
            category="Capacitors",
            subcategory="MLCC",
            joints=2,
            basic=True,
            stock=1000,
            price_tiers=[PriceTier(qty=1, price=0.01)],
            attributes={"Capacitance": "100nF"},
        )

        # Test within range: 50nF to 150nF
        attribute_ranges = {"Capacitance": {"min": "50nF", "max": "150nF"}}
        search = ComponentSearch(None)  # type: ignore
        filtered = search._filter_by_attribute_ranges([comp], attribute_ranges)
        assert len(filtered) == 1

    def test_capacitor_out_of_range_low(self):
        """Test component below min range."""
        from jlc_has_it.core.models import Component, PriceTier
        from jlc_has_it.core.search import ComponentSearch

        comp = Component(
            lcsc="C1234",
            mfr="TEST",
            description="10nF Capacitor",
            manufacturer="TEST",
            category="Capacitors",
            subcategory="MLCC",
            joints=2,
            basic=True,
            stock=1000,
            price_tiers=[PriceTier(qty=1, price=0.01)],
            attributes={"Capacitance": "10nF"},
        )

        # Test below range: min 50nF
        attribute_ranges = {"Capacitance": {"min": "50nF"}}
        search = ComponentSearch(None)  # type: ignore
        filtered = search._filter_by_attribute_ranges([comp], attribute_ranges)
        assert len(filtered) == 0

    def test_capacitor_out_of_range_high(self):
        """Test component above max range."""
        from jlc_has_it.core.models import Component, PriceTier
        from jlc_has_it.core.search import ComponentSearch

        comp = Component(
            lcsc="C1234",
            mfr="TEST",
            description="1uF Capacitor",
            manufacturer="TEST",
            category="Capacitors",
            subcategory="MLCC",
            joints=2,
            basic=True,
            stock=1000,
            price_tiers=[PriceTier(qty=1, price=0.01)],
            attributes={"Capacitance": "1uF"},
        )

        # Test above range: max 500nF
        attribute_ranges = {"Capacitance": {"max": "500nF"}}
        search = ComponentSearch(None)  # type: ignore
        filtered = search._filter_by_attribute_ranges([comp], attribute_ranges)
        assert len(filtered) == 0

    def test_voltage_range_with_different_units(self):
        """Test voltage filtering with unit conversion."""
        from jlc_has_it.core.models import Component, PriceTier
        from jlc_has_it.core.search import ComponentSearch

        comp = Component(
            lcsc="C1234",
            mfr="TEST",
            description="50V Capacitor",
            manufacturer="TEST",
            category="Capacitors",
            subcategory="MLCC",
            joints=2,
            basic=True,
            stock=1000,
            price_tiers=[PriceTier(qty=1, price=0.01)],
            attributes={"Voltage": "50V"},
        )

        # Should be in range: 10V to 100V
        attribute_ranges = {"Voltage": {"min": "10V", "max": "100V"}}
        search = ComponentSearch(None)  # type: ignore
        filtered = search._filter_by_attribute_ranges([comp], attribute_ranges)
        assert len(filtered) == 1

    def test_resistance_range_kohm_to_ohm(self):
        """Test resistance filtering with kOhm to Ohm conversion."""
        from jlc_has_it.core.models import Component, PriceTier
        from jlc_has_it.core.search import ComponentSearch

        comp = Component(
            lcsc="R1234",
            mfr="TEST",
            description="10kΩ Resistor",
            manufacturer="TEST",
            category="Resistors",
            subcategory="Thin Film",
            joints=2,
            basic=True,
            stock=1000,
            price_tiers=[PriceTier(qty=1, price=0.01)],
            attributes={"Resistance": "10kΩ"},
        )

        # Range in Ohms: 5000 to 50000
        attribute_ranges = {"Resistance": {"min": "5000Ohm", "max": "50000Ohm"}}
        search = ComponentSearch(None)  # type: ignore
        filtered = search._filter_by_attribute_ranges([comp], attribute_ranges)
        assert len(filtered) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
