"""Component search functionality."""

import sqlite3
from dataclasses import dataclass
from typing import Any, Optional

from jlc_has_it.core.models import Component


@dataclass
class QueryParams:
    """Structured parameters for component search."""

    category: Optional[str] = None
    subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    description_contains: Optional[str] = None
    basic_only: bool = False
    in_stock_only: bool = True
    min_stock: int = 0
    max_price: Optional[float] = None
    package: Optional[str] = None
    # Attribute filters (e.g., {"Capacitance": 100, "Voltage": 50})
    attributes: Optional[dict[str, Any]] = None
    # Attribute range filters (e.g., {"Voltage": {"min": 50}})
    attribute_ranges: Optional[dict[str, dict[str, Any]]] = None
    limit: int = 50


class ComponentSearch:
    """Search for components in the jlcparts database."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize search with database connection.

        Args:
            connection: SQLite connection to jlcparts database
        """
        self.conn = connection

    def search(self, params: QueryParams) -> list[Component]:
        """Search for components matching the given parameters.

        Args:
            params: Search parameters

        Returns:
            List of Component objects sorted by relevance
        """
        query_parts = ["SELECT * FROM components WHERE 1=1"]
        query_args: list[Any] = []

        # Category filters
        if params.category:
            query_parts.append("AND category = ?")
            query_args.append(params.category)

        if params.subcategory:
            query_parts.append("AND subcategory = ?")
            query_args.append(params.subcategory)

        if params.manufacturer:
            query_parts.append("AND manufacturer LIKE ?")
            query_args.append(f"%{params.manufacturer}%")

        if params.description_contains:
            query_parts.append("AND description LIKE ?")
            query_args.append(f"%{params.description_contains}%")

        # Availability filters
        if params.basic_only:
            query_parts.append("AND basic = 1")

        if params.in_stock_only:
            query_parts.append("AND stock > 0")

        if params.min_stock > 0:
            query_parts.append("AND stock >= ?")
            query_args.append(params.min_stock)

        # Price filter (check first price tier)
        if params.max_price is not None:
            # Price is stored as JSON array, extract first tier's price
            query_parts.append("AND CAST(json_extract(price, '$[0].price') AS REAL) <= ?")
            query_args.append(params.max_price)

        # Package filter (stored in attributes JSON)
        if params.package:
            query_parts.append(
                "AND (json_extract(attributes, '$.Package') = ? OR "
                "json_extract(attributes, '$.\"Package/Case\"') = ?)"
            )
            query_args.append(params.package)
            query_args.append(params.package)

        # Exact attribute value filters
        if params.attributes:
            for attr_name, attr_value in params.attributes.items():
                # Try to match against value field in nested object
                query_parts.append(f"AND json_extract(attributes, '$.{attr_name}.value') = ?")
                query_args.append(attr_value)

        # Attribute range filters
        if params.attribute_ranges:
            for attr_name, range_spec in params.attribute_ranges.items():
                if "min" in range_spec:
                    query_parts.append(
                        f"AND CAST(json_extract(attributes, '$.{attr_name}.value') AS REAL) >= ?"
                    )
                    query_args.append(range_spec["min"])
                if "max" in range_spec:
                    query_parts.append(
                        f"AND CAST(json_extract(attributes, '$.{attr_name}.value') AS REAL) <= ?"
                    )
                    query_args.append(range_spec["max"])

        # Sorting: basic parts first, then by stock (descending), then by price (ascending)
        query_parts.append(
            "ORDER BY basic DESC, stock DESC, "
            "CAST(json_extract(price, '$[0].price') AS REAL) ASC"
        )

        # Limit results
        query_parts.append("LIMIT ?")
        query_args.append(params.limit)

        # Execute query
        query = " ".join(query_parts)
        cursor = self.conn.execute(query, query_args)

        # Convert rows to Component objects
        components = []
        for row in cursor.fetchall():
            try:
                component = Component.from_db_row(dict(row))
                components.append(component)
            except Exception:
                # Skip malformed components
                continue

        return components

    def search_by_category(
        self, category: str, limit: int = 50, basic_only: bool = False
    ) -> list[Component]:
        """Search for components in a specific category.

        Args:
            category: Component category (e.g., "Capacitors", "Resistors")
            limit: Maximum number of results
            basic_only: Only return basic parts

        Returns:
            List of Component objects
        """
        params = QueryParams(category=category, limit=limit, basic_only=basic_only)
        return self.search(params)

    def search_by_lcsc(self, lcsc_id: str) -> Optional[Component]:
        """Search for a component by LCSC part number.

        Args:
            lcsc_id: LCSC part number (e.g., "C12345")

        Returns:
            Component if found, None otherwise
        """
        cursor = self.conn.execute("SELECT * FROM components WHERE lcsc = ?", [lcsc_id])
        row = cursor.fetchone()

        if row is None:
            return None

        return Component.from_db_row(dict(row))
