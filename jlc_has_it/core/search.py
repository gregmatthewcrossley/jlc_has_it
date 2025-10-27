"""Component search functionality."""

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Optional

from jlc_has_it.core.models import Component


@dataclass
class SearchResult:
    """Result of a component search with pagination info."""

    results: list[Component]
    offset: int = 0
    limit: int = 20
    total_count: Optional[int] = None  # Only set if include_total_count=True

    @property
    def has_more(self) -> bool:
        """Check if there are more results available."""
        if self.total_count is None:
            # Can't determine if there are more without total count
            return len(self.results) >= self.limit
        return self.offset + len(self.results) < self.total_count

    def next_page(self) -> Optional["SearchResult"]:
        """Get offset for next page (useful for continued pagination)."""
        if self.has_more:
            return SearchResult(
                results=[],  # Will be filled by caller
                offset=self.offset + self.limit,
                limit=self.limit,
                total_count=self.total_count,
            )
        return None


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
    # Pagination support (Phase 7 optimization)
    offset: int = 0
    limit: int = 20  # Changed default from 50 to 20 for better pagination UX
    include_total_count: bool = False  # If True, compute total matching results


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
        # Build query with JOINs for normalized schema
        # Extract description from extra JSON since main description column is empty
        query_parts = [
            "SELECT c.lcsc, "
            "COALESCE(json_extract(c.extra, '$.description'), c.description) as description, "
            "c.mfr, cat.category as category, "
            "cat.subcategory, man.name as manufacturer, "
            "c.basic, c.stock, c.price, c.joints, "
            "json_extract(c.extra, '$.attributes') as attributes "
            "FROM components c "
            "LEFT JOIN categories cat ON c.category_id = cat.id "
            "LEFT JOIN manufacturers man ON c.manufacturer_id = man.id "
            "WHERE 1=1"
        ]
        query_args: list[Any] = []

        # Category filters
        if params.category:
            query_parts.append("AND cat.category LIKE ?")
            query_args.append(f"%{params.category}%")

        if params.subcategory:
            query_parts.append("AND cat.subcategory LIKE ?")
            query_args.append(f"%{params.subcategory}%")

        if params.manufacturer:
            query_parts.append("AND man.name LIKE ?")
            query_args.append(f"%{params.manufacturer}%")

        if params.description_contains:
            # Search in mfr (manufacturer part number) and description from extra JSON
            # The main description column is empty; full descriptions are in extra JSON
            query_parts.append(
                "AND (c.mfr LIKE ? OR json_extract(c.extra, '$.description') LIKE ?)"
            )
            query_args.append(f"%{params.description_contains}%")
            query_args.append(f"%{params.description_contains}%")

        # Availability filters
        if params.basic_only:
            query_parts.append("AND c.basic = 1")

        if params.in_stock_only:
            query_parts.append("AND c.stock > 0")

        if params.min_stock > 0:
            query_parts.append("AND c.stock >= ?")
            query_args.append(params.min_stock)

        # Price filter (check first price tier)
        if params.max_price is not None:
            # Price is stored as JSON array, extract first tier's price
            query_parts.append("AND CAST(json_extract(c.price, '$[0].price') AS REAL) <= ?")
            query_args.append(params.max_price)

        # Note: Package and attribute filters are not currently supported as they
        # would require complex JSON extraction in WHERE clauses on a 7M+ row table.
        # These could be implemented in the future with indexed copies of the database.

        # Sorting: basic parts first, then by stock (descending), then by price (ascending)
        query_parts.append(
            "ORDER BY c.basic DESC, c.stock DESC, "
            "CAST(json_extract(c.price, '$[0].price') AS REAL) ASC"
        )

        # Limit results with pagination support
        # Validate limit (max 100, min 1)
        limit = max(1, min(params.limit, 100))
        query_parts.append("LIMIT ? OFFSET ?")
        query_args.append(limit)
        query_args.append(params.offset)

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
        # Convert from "C12345" format to integer 12345 for database lookup
        if lcsc_id.startswith("C"):
            lcsc_int = int(lcsc_id[1:])
        else:
            lcsc_int = int(lcsc_id)

        # Use JOINs to get full component data with category and manufacturer names
        query = """
            SELECT c.lcsc,
                   COALESCE(json_extract(c.extra, '$.description'), c.description) as description,
                   c.mfr, cat.category as category,
                   cat.subcategory, man.name as manufacturer,
                   c.basic, c.stock, c.price, c.joints,
                   json_extract(c.extra, '$.attributes') as attributes
            FROM components c
            LEFT JOIN categories cat ON c.category_id = cat.id
            LEFT JOIN manufacturers man ON c.manufacturer_id = man.id
            WHERE c.lcsc = ?
        """
        cursor = self.conn.execute(query, [lcsc_int])
        row = cursor.fetchone()

        if row is None:
            return None

        return Component.from_db_row(dict(row))
