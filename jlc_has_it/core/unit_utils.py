"""Unit normalization and conversion utilities for component attributes.

Supports normalizing and comparing component specifications with different units:
- Capacitance: F, mF, μF/uF, nF, pF
- Resistance: Ω/Ohm, kΩ/kOhm, MΩ/MOhm, GΩ/GOhm
- Inductance: H, mH, μH/uH, nH
- Voltage: V, mV, kV
- Current: A, mA, μA/uA, nA
- Frequency: Hz, kHz, MHz, GHz

Example:
    >>> from jlc_has_it.core.unit_utils import parse_value, normalize_value
    >>> # Parse "100nF" into value and unit
    >>> value, unit = parse_value("100nF")
    >>> value
    100
    >>> unit
    'nF'
    >>> # Normalize to base unit (Farads)
    >>> normalized = normalize_value(100, "nF")
    >>> normalized
    1e-07
    >>> # Compare two values with different units
    >>> compare_values("100nF", "0.1uF")  # Both are equal
    0
"""

import re
from typing import Optional, Tuple

# Unit multipliers relative to base units
# Capacitance base: Farads (F)
CAPACITANCE_UNITS = {
    "f": 1.0,
    "mf": 1e-3,
    "μf": 1e-6,
    "uf": 1e-6,
    "nf": 1e-9,
    "pf": 1e-12,
}

# Resistance base: Ohms (Ω)
RESISTANCE_UNITS = {
    "ω": 1.0,
    "ohm": 1.0,
    "ohms": 1.0,
    "kω": 1e3,
    "kohm": 1e3,
    "kohms": 1e3,
    "mω": 1e6,
    "mohm": 1e6,
    "mohms": 1e6,
    "gω": 1e9,
    "gohm": 1e9,
    "gohms": 1e9,
}

# Inductance base: Henries (H)
INDUCTANCE_UNITS = {
    "h": 1.0,
    "mh": 1e-3,
    "μh": 1e-6,
    "uh": 1e-6,
    "nh": 1e-9,
}

# Voltage base: Volts (V)
VOLTAGE_UNITS = {
    "v": 1.0,
    "mv": 1e-3,
    "kv": 1e3,
}

# Current base: Amperes (A)
CURRENT_UNITS = {
    "a": 1.0,
    "ma": 1e-3,
    "μa": 1e-6,
    "ua": 1e-6,
    "na": 1e-9,
}

# Frequency base: Hertz (Hz)
FREQUENCY_UNITS = {
    "hz": 1.0,
    "khz": 1e3,
    "mhz": 1e6,
    "ghz": 1e9,
}

# Map of unit categories (to help detect unit type)
UNIT_CATEGORIES = {
    "capacitance": CAPACITANCE_UNITS,
    "resistance": RESISTANCE_UNITS,
    "inductance": INDUCTANCE_UNITS,
    "voltage": VOLTAGE_UNITS,
    "current": CURRENT_UNITS,
    "frequency": FREQUENCY_UNITS,
}


def parse_value(value_str: str) -> Tuple[Optional[float], Optional[str]]:
    """Parse a string like '100nF' into numeric value and unit.

    Args:
        value_str: String like "100nF", "0.1μF", "50V", etc.

    Returns:
        Tuple of (numeric_value, unit_str) or (None, None) if parsing fails.
        Example: "100nF" -> (100.0, "nF")
    """
    value_str = value_str.strip()

    # Match pattern: optional sign, digits/decimals, optional unit
    match = re.match(r"^([+-]?[\d.]+)\s*([a-zA-Zμ/±%]*)?$", value_str)

    if not match:
        return None, None

    try:
        numeric_value = float(match.group(1))
        unit = match.group(2) or ""
        return numeric_value, unit
    except (ValueError, IndexError):
        return None, None


def normalize_value(value: float, unit: str) -> Optional[float]:
    """Normalize a value to its base unit.

    Args:
        value: Numeric value (e.g., 100)
        unit: Unit string (e.g., "nF", "kΩ", "V")

    Returns:
        Value in base unit, or None if unit is unknown.
        Example: normalize_value(100, "nF") -> 1e-7 (in Farads)
    """
    if not unit:
        return value

    unit_lower = unit.lower().replace(" ", "").replace("Ω", "ohm")

    # Check each category
    for category, units_dict in UNIT_CATEGORIES.items():
        if unit_lower in units_dict:
            multiplier = units_dict[unit_lower]
            return value * multiplier

    # Unknown unit - return None
    return None


def get_unit_category(unit: str) -> Optional[str]:
    """Determine the category of a unit (e.g., 'nF' -> 'capacitance').

    Args:
        unit: Unit string (e.g., "nF", "kΩ", "V")

    Returns:
        Category name or None if unit is unknown.
    """
    unit_lower = unit.lower().replace(" ", "").replace("Ω", "ohm")

    for category, units_dict in UNIT_CATEGORIES.items():
        if unit_lower in units_dict:
            return category

    return None


def compare_values(
    value1_str: str, value2_str: str, tolerance: float = 1e-10
) -> Optional[int]:
    """Compare two values with potentially different units.

    Args:
        value1_str: First value (e.g., "100nF")
        value2_str: Second value (e.g., "0.1μF")
        tolerance: Relative tolerance for floating-point comparison

    Returns:
        -1 if value1 < value2, 0 if equal, 1 if value1 > value2, or None if comparison fails.
    """
    val1, unit1 = parse_value(value1_str)
    val2, unit2 = parse_value(value2_str)

    if val1 is None or val2 is None:
        return None

    # Get categories to ensure they're compatible
    cat1 = get_unit_category(unit1) if unit1 else None
    cat2 = get_unit_category(unit2) if unit2 else None

    # If neither has a unit, do simple comparison
    if not unit1 and not unit2:
        if val1 < val2:
            return -1
        elif val1 > val2:
            return 1
        else:
            return 0

    # If units are different types, can't compare
    if cat1 != cat2:
        return None

    # Normalize both to base unit
    norm1 = normalize_value(val1, unit1) if unit1 else val1
    norm2 = normalize_value(val2, unit2) if unit2 else val2

    if norm1 is None or norm2 is None:
        return None

    # Compare with tolerance for floating-point arithmetic
    diff = abs(norm1 - norm2)
    max_val = max(abs(norm1), abs(norm2))

    if max_val > 0:
        relative_diff = diff / max_val
    else:
        relative_diff = diff

    if relative_diff < tolerance:
        return 0
    elif norm1 < norm2:
        return -1
    else:
        return 1
