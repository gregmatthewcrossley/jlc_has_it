# jlcparts Database Integration

This document describes how we access JLCPCB component data using the [jlcparts](https://github.com/yaqwsx/jlcparts) project.

## Overview

Instead of using the JLCPCB API directly (which requires complex authentication and has unclear documentation), we use the **jlcparts project's publicly available SQLite database** containing all JLCPCB components.

### Why jlcparts?

- ✅ **No authentication required** - publicly accessible data
- ✅ **Daily updates** - database refreshed automatically at 3AM UTC
- ✅ **Complete data** - all JLCPCB components with normalized attributes
- ✅ **MIT licensed** - free to use with attribution
- ✅ **Proven solution** - actively maintained, 770+ successful update runs
- ✅ **Fast queries** - local SQLite database, no API rate limits

## Data Source

**Project**: https://github.com/yaqwsx/jlcparts
**License**: MIT (Copyright 2024 Jan Mrázek)
**Database URL**: https://yaqwsx.github.io/jlcparts/data/

### Database Files

The database is distributed as multi-part zip files:
- `cache.z01` - Part 1 (~50MB)
- `cache.z02` - Part 2 (if needed)
- `cache.zip` - Final part

These must be downloaded and concatenated to extract the complete `cache.sqlite3` file.

## Update Schedule

- **Frequency**: Daily at 3:00 AM UTC
- **Mechanism**: GitHub Actions automated workflow
- **Last updated**: Check `index.json` for timestamp
- **Reliability**: 100% success rate in recent runs

### Index File

Check database freshness:
```bash
curl https://yaqwsx.github.io/jlcparts/data/index.json
```

Response includes:
```json
{
  "created": "2025-10-25T05:18:56+00:00",
  "categories": { ... }
}
```

## Database Schema

The SQLite database contains several tables:

### Components Table (Primary)

Key fields:
- `lcsc` - JLCPCB part number (e.g., "C1525")
- `mfr` - Manufacturer part number
- `description` - Component description
- `manufacturer` - Manufacturer name
- `category` - Top-level category
- `subcategory` - Subcategory
- `joints` - Number of pins/pads
- `basic` - Boolean (1=Basic part, 0=Extended part)
- `stock` - Current stock quantity
- `price` - JSON array of pricing tiers
- `attributes` - JSON object of normalized specifications

### Attributes JSON Structure

Example:
```json
{
  "Capacitance": {"value": 100, "unit": "nF"},
  "Voltage": {"value": 16, "unit": "V"},
  "Tolerance": {"value": 10, "unit": "%"},
  "Package": "0402",
  "Temperature Coefficient": "X7R"
}
```

### Price JSON Structure

Example:
```json
[
  {"qty": 1, "price": 0.0012},
  {"qty": 10, "price": 0.0010},
  {"qty": 100, "price": 0.0008}
]
```

## Integration Strategy

### 1. Database Download & Caching

**Location**: `~/.cache/jlc_has_it/cache.sqlite3`

**Update logic**:
1. Check if local database exists
2. Check age using file modification time
3. If >1 day old or missing, download fresh copy
4. Download multi-part zip files
5. Concatenate and extract SQLite database
6. Validate database integrity

### 2. Component Querying

Use standard SQLite queries:

```python
import sqlite3

conn = sqlite3.connect('~/.cache/jlc_has_it/cache.sqlite3')

# Search for capacitors
cursor = conn.execute("""
    SELECT lcsc, mfr, description, stock, price, attributes
    FROM components
    WHERE category = 'Capacitors'
    AND subcategory = 'Multilayer Ceramic Capacitors MLCC - SMD/SMT'
    AND json_extract(attributes, '$.Capacitance.value') = 100
    AND json_extract(attributes, '$.Capacitance.unit') = 'nF'
    AND json_extract(attributes, '$.Voltage.value') >= 50
    AND stock > 0
    ORDER BY basic DESC, stock DESC
    LIMIT 10
""")
```

### 3. Data Model Mapping

Map database rows to Python dataclasses:

```python
from dataclasses import dataclass
from typing import Optional
import json

@dataclass
class Component:
    lcsc: str                    # JLCPCB part number
    mfr: str                     # Manufacturer part number
    description: str
    manufacturer: str
    category: str
    subcategory: str
    joints: int                  # Pin count
    basic: bool                  # Basic vs Extended
    stock: int
    price_tiers: list[dict]      # Parsed from price JSON
    attributes: dict             # Parsed from attributes JSON

    @classmethod
    def from_db_row(cls, row):
        """Construct from SQLite row"""
        return cls(
            lcsc=row['lcsc'],
            mfr=row['mfr'],
            description=row['description'],
            manufacturer=row['manufacturer'],
            category=row['category'],
            subcategory=row['subcategory'],
            joints=row['joints'],
            basic=bool(row['basic']),
            stock=row['stock'],
            price_tiers=json.loads(row['price']),
            attributes=json.loads(row['attributes'])
        )
```

## Attribution Requirements

Per MIT License, include this notice in our documentation:

```
Component data provided by jlcparts (https://github.com/yaqwsx/jlcparts)
Copyright 2024 Jan Mrázek
Licensed under the MIT License
```

## Implementation Checklist

- [ ] Download multi-part database files
- [ ] Concatenate and extract SQLite database
- [ ] Verify database integrity (valid SQLite file)
- [ ] Cache in `~/.cache/jlc_has_it/`
- [ ] Check database age before queries
- [ ] Refresh if >1 day old
- [ ] Handle download failures gracefully
- [ ] Add MIT license attribution to docs/code

## Benefits Over Direct API Access

1. **No authentication complexity** - no HMAC-SHA256 signatures required
2. **Fast local queries** - no network latency or rate limits
3. **Offline capable** - works without internet after initial download
4. **Normalized data** - attributes already parsed and structured
5. **Proven reliability** - maintained by active open-source project
6. **Simple integration** - just SQLite queries, no API client complexity

## Potential Issues & Mitigations

| Issue | Mitigation |
|-------|-----------|
| Database download fails | Continue using cached database |
| Database becomes stale | User sees warning if >7 days old |
| jlcparts project discontinued | Fork project and run our own updates |
| Database schema changes | Version checking and migration logic |
| Large database size (50MB) | Accept the size - modern systems handle it easily |

## Example Workflow

```python
from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.search import ComponentSearch

# Initialize database (downloads if needed)
db = DatabaseManager()
db.update_if_needed()  # Downloads if >1 day old

# Search for components
search = ComponentSearch(db.get_connection())
results = search.find_capacitor(
    capacitance="220uF",
    voltage_min="50V",
    package="SMD",
    in_stock=True,
    basic_only=True
)

# Results are Component objects ready to use
for component in results[:10]:
    print(f"{component.lcsc}: {component.description}")
    print(f"  Stock: {component.stock}")
    print(f"  Price: ${component.price_tiers[0]['price']}")
```

## Next Steps

1. Implement `DatabaseManager` class (task 01-002)
2. Create `Component` dataclass (task 01-003)
3. Implement search functionality (task 03-001)
4. Add natural language query parsing (task 06-002)
