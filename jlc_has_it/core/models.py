"""Data models for JLCPCB components."""

from dataclasses import dataclass
from typing import Any, Optional, Union


@dataclass
class PriceTier:
    """Pricing tier for a component."""

    qty: int
    price: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PriceTier":
        """Create from dictionary."""
        return cls(qty=int(data["qty"]), price=float(data["price"]))


@dataclass
class AttributeValue:
    """Normalized attribute value with optional unit."""

    value: Union[float, str]
    unit: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Union[dict[str, Any], float, str]) -> "AttributeValue":
        """Create from dictionary or scalar value."""
        if isinstance(data, dict):
            return cls(value=data["value"], unit=data.get("unit"))
        return cls(value=data, unit=None)


@dataclass
class Component:
    """Represents a component from the jlcparts database."""

    lcsc: str
    mfr: str
    description: str
    manufacturer: str
    category: str
    subcategory: str
    joints: int
    basic: bool
    stock: int
    price_tiers: list[PriceTier]
    attributes: dict[str, Union[AttributeValue, str]]

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Component":
        """Construct Component from SQLite row dictionary.

        Args:
            row: Dictionary from sqlite3.Row (with row_factory = sqlite3.Row)
                 Expected keys: lcsc, mfr, description, manufacturer, category,
                 subcategory, joints, basic, stock, price (JSON string),
                 attributes (JSON string)

        Returns:
            Component instance
        """
        import json

        # Parse price tiers from JSON
        price_data = json.loads(row["price"]) if isinstance(row["price"], str) else row["price"]
        price_tiers = [PriceTier.from_dict(tier) for tier in price_data]

        # Parse attributes from JSON
        attrs_data = (
            json.loads(row["attributes"])
            if isinstance(row["attributes"], str)
            else row["attributes"]
        )

        # Convert attribute values to AttributeValue objects
        attributes: dict[str, Union[AttributeValue, str]] = {}
        for key, value in attrs_data.items():
            if isinstance(value, dict) and "value" in value:
                attributes[key] = AttributeValue.from_dict(value)
            else:
                # Some attributes are just strings (e.g., Package type)
                attributes[key] = value

        return cls(
            lcsc=row["lcsc"],
            mfr=row["mfr"],
            description=row["description"],
            manufacturer=row["manufacturer"],
            category=row["category"],
            subcategory=row["subcategory"],
            joints=int(row["joints"]),
            basic=bool(row["basic"]),
            stock=int(row["stock"]),
            price_tiers=price_tiers,
            attributes=attributes,
        )

    @property
    def price(self) -> float:
        """Get the unit price (price for quantity 1)."""
        if not self.price_tiers:
            return 0.0
        return self.price_tiers[0].price

    def get_attribute(self, name: str) -> Optional[Union[AttributeValue, str]]:
        """Get an attribute value by name.

        Args:
            name: Attribute name (e.g., "Capacitance", "Voltage")

        Returns:
            AttributeValue or string if found, None otherwise
        """
        return self.attributes.get(name)

    def get_attribute_value(self, name: str) -> Optional[Union[float, str]]:
        """Get the raw value of an attribute.

        Args:
            name: Attribute name

        Returns:
            The value (without unit) or None if not found
        """
        attr = self.get_attribute(name)
        if attr is None:
            return None
        if isinstance(attr, AttributeValue):
            return attr.value
        return attr
