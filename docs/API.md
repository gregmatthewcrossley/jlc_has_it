# JLC Has It API Documentation

This document describes the MCP tools exposed by the JLC Has It server for use with Claude Code/Desktop.

## Overview

JLC Has It exposes four main tools through the Model Context Protocol (MCP):

1. `search_components` - Search for components matching criteria
2. `get_component_details` - Get full specifications for a component
3. `add_to_project` - Add a component to a KiCad project
4. `compare_components` - Compare multiple components side-by-side

## Tool Reference

### search_components

Search for components matching your criteria.

**Purpose**: Find components in the JLCPCB catalog that match your requirements.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | No | - | Free-text search query (e.g., "100nF ceramic capacitor", "10k resistor") |
| `category` | string | No | - | Component category (e.g., "Capacitors", "Resistors", "Diodes", "ICs") |
| `subcategory` | string | No | - | More specific category (e.g., "Multilayer Ceramic Capacitors MLCC", "Aluminum Electrolytic Capacitors") |
| `manufacturer` | string | No | - | Filter by manufacturer name (e.g., "Samsung", "Yageo", "TE Connectivity") |
| `basic_only` | boolean | No | true | Only return "Basic" parts (lower assembly fees, better availability) |
| `in_stock_only` | boolean | No | true | Only return components currently in stock |
| `max_price` | number | No | - | Maximum unit price in USD (e.g., 0.50 for 50 cents) |
| `package` | string | No | - | Package type (e.g., "0402", "0603", "0805", "1206", "SOT-23", "QFP-100") |
| `limit` | integer | No | 20 | Maximum number of results to return (1-100) |

**Returns:**

Array of components, each with:

```json
{
  "lcsc_id": "C1525",
  "description": "Samsung CL05B104KO5NNNC 100nF 16V X7R Ceramic Capacitor 0402",
  "manufacturer": "Samsung",
  "mfr_id": "CL05B104KO5NNNC",
  "category": "Capacitors",
  "stock": 16800000,
  "price": 0.0011,
  "basic": true
}
```

**Field Definitions:**

- **lcsc_id**: JLCPCB part number (used for ordering and other operations)
- **description**: Human-readable component description
- **manufacturer**: Component manufacturer name
- **mfr_id**: Manufacturer's part number
- **category**: Top-level component category
- **stock**: Current quantity in stock at JLCPCB
- **price**: Unit price in USD for quantity 1
- **basic**: Whether this is a "Basic" part (faster delivery, better availability)

**Sorting:**

Results are sorted by:
1. Basic parts first (better for JLCPCB assembly)
2. Higher stock quantity (more reliable availability)
3. Lower price (cost-effective)

**Examples:**

```
User: "Find a 100nF ceramic capacitor for 50V operation"

Claude calls:
  search_components(
    description_contains="100nF ceramic capacitor",
    attribute_ranges={"Voltage": {"min": 50}},
    limit=10
  )
```

```
User: "What resistors do you have from Yageo?"

Claude calls:
  search_components(
    category="Resistors",
    manufacturer="Yageo",
    basic_only=true,
    limit=20
  )
```

---

### get_component_details

Get complete specifications for a single component.

**Purpose**: Retrieve full details and attributes for a known component.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lcsc_id` | string | Yes | JLCPCB part number (e.g., "C1525", "R12345", "U67890") |

**Returns:**

```json
{
  "lcsc_id": "C1525",
  "description": "Samsung CL05B104KO5NNNC 100nF 16V X7R Ceramic Capacitor 0402",
  "manufacturer": "Samsung",
  "mfr_id": "CL05B104KO5NNNC",
  "category": "Capacitors",
  "subcategory": "Multilayer Ceramic Capacitors MLCC",
  "stock": 16800000,
  "price": 0.0011,
  "basic": true,
  "joints": 2,
  "attributes": {
    "Capacitance": {
      "value": 100,
      "unit": "nF"
    },
    "Voltage": {
      "value": 16,
      "unit": "V"
    },
    "Tolerance": {
      "value": 10,
      "unit": "%"
    },
    "Package": "0402",
    "Temperature Coefficient": "X7R"
  },
  "price_tiers": [
    {"qty": 1, "price": 0.0011},
    {"qty": 10, "price": 0.0008},
    {"qty": 100, "price": 0.0005},
    {"qty": 1000, "price": 0.0004}
  ]
}
```

**Field Definitions:**

- **lcsc_id**, **description**, **manufacturer**, **mfr_id**, **category**, **stock**, **price**, **basic**: Same as search_components
- **subcategory**: More specific component category
- **joints**: Number of pins/pads on the component
- **attributes**: Normalized component specifications with values and units
- **price_tiers**: Price discounts for bulk quantities

**Attributes:**

Attribute names and values vary by component type. Common attributes:

**Capacitors:**
- `Capacitance`: Value and unit (pF, nF, µF)
- `Voltage`: Working voltage and unit (V)
- `Tolerance`: Tolerance percentage
- `Temperature Coefficient`: X7R, C0G, etc.
- `Package`: Package code (0402, 0603, etc.)

**Resistors:**
- `Resistance`: Value and unit (Ω)
- `Tolerance`: Tolerance percentage
- `Power`: Power rating (W)
- `Package`: Package code

**ICs:**
- `Number of Pins`: Pin count
- `Function`: IC purpose/type
- `Logic Family`: CMOS, TTL, etc.

**Examples:**

```
User: "What are the specs for C1525?"

Claude calls:
  get_component_details(lcsc_id="C1525")
```

---

### add_to_project

Add a component to your KiCad project.

**Purpose**: Download component library files and integrate them into a KiCad project.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `lcsc_id` | string | Yes | - | JLCPCB part number to add |
| `project_path` | string | No | Auto-detect | Path to KiCad project directory (auto-detected from current directory) |

**Returns:**

Success case:
```json
{
  "success": true,
  "lcsc_id": "C1525",
  "project": "/Users/user/kicad-projects/power-supply",
  "symbol_file": "/Users/user/kicad-projects/power-supply/libraries/jlc-components.kicad_sym",
  "footprints_dir": "/Users/user/kicad-projects/power-supply/libraries/footprints.pretty",
  "models_dir": "/Users/user/kicad-projects/power-supply/libraries/3d_models",
  "files_copied": {
    "footprints": 1,
    "models": 1
  },
  "message": "Added C1525 to power-supply. Refresh KiCad libraries to use the component."
}
```

Failure case:
```json
{
  "success": false,
  "error": "No KiCad project found. Please specify project_path."
}
```

**What happens internally:**

1. **Download**: Uses `easyeda2kicad` to download from JLCPCB/EasyEDA:
   - Symbol file (.kicad_sym)
   - Footprint files (.kicad_mod)
   - 3D CAD models (.step or .wrl files)

2. **Validate**: Confirms all files are present and non-empty

3. **Copy to project**: Places files in standard locations:
   ```
   project/
   ├── libraries/
   │   ├── jlc-components.kicad_sym
   │   ├── footprints.pretty/
   │   │   └── [footprint files]
   │   └── 3d_models/
   │       └── [3D model files]
   ├── sym-lib-table
   └── fp-lib-table
   ```

4. **Register**: Updates KiCad library tables so the project can find the files

**Next steps for user:**

After this tool completes, the user must:
1. Open the KiCad project
2. Go to Preferences → Manage Symbol Libraries
3. Click "Refresh" or restart KiCad
4. The component will now be available for use in schematics

**Error handling:**

Common errors and causes:

| Error | Cause | Solution |
|-------|-------|----------|
| "No KiCad project found" | Not in project directory and no path specified | Specify `project_path` or navigate to project directory |
| "Failed to download valid library" | easyeda2kicad couldn't find component or it lacks complete library | Component may not have complete library; try alternative part |
| "easyeda2kicad command not found" | Tool not installed | `pip install easyeda2kicad` |

**Examples:**

```
User: "Add C1525 to my project"

Claude calls:
  add_to_project(lcsc_id="C1525")
  // Auto-detects project directory
```

```
User: "Add R1234 to the power-supply project"

Claude calls:
  add_to_project(
    lcsc_id="R1234",
    project_path="/Users/user/projects/power-supply"
  )
```

---

### compare_components

Compare specifications of multiple components side-by-side.

**Purpose**: Help users decide between similar parts by comparing key specs.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lcsc_ids` | array[string] | Yes | List of JLCPCB part numbers to compare (2-20 parts) |

**Returns:**

```json
{
  "success": true,
  "comparison": {
    "components": [
      {
        "lcsc_id": "C1525",
        "description": "Samsung CL05B104KO5NNNC 100nF 16V X7R Ceramic Capacitor 0402",
        "manufacturer": "Samsung",
        "stock": 16800000,
        "price": 0.0011,
        "basic": true
      },
      {
        "lcsc_id": "C307331",
        "description": "Samsung CL05B104KB54PNC 100nF 50V X7R Ceramic Capacitor 0402",
        "manufacturer": "Samsung",
        "stock": 10000000,
        "price": 0.0044,
        "basic": true
      }
    ],
    "attributes": {
      "Voltage": [
        {"lcsc_id": "C1525", "value": 16, "unit": "V"},
        {"lcsc_id": "C307331", "value": 50, "unit": "V"}
      ],
      "Capacitance": [
        {"lcsc_id": "C1525", "value": 100, "unit": "nF"},
        {"lcsc_id": "C307331", "value": 100, "unit": "nF"}
      ],
      "Tolerance": [
        {"lcsc_id": "C1525", "value": 10, "unit": "%"},
        {"lcsc_id": "C307331", "value": 10, "unit": "%"}
      ]
    }
  }
}
```

**Use cases:**

- User wants to understand trade-offs between parts
- Verify specifications match project requirements
- Find the best value option

**Examples:**

```
User: "Compare these three capacitors: C1525, C307331, and C14663"

Claude calls:
  compare_components(lcsc_ids=["C1525", "C307331", "C14663"])
```

---

## Rate Limiting & Performance

**Database queries:**
- Local SQLite queries are fast (< 100ms for typical searches)
- No rate limiting on searches

**Library downloads:**
- Each component download takes 2-10 seconds (via easyeda2kicad)
- Parallel downloads are supported (max 10 concurrent)
- Downloaded libraries are cached locally

**Network requirements:**
- Database updates: ~50-100 MB download (once per day)
- Component searches: No network required (local database)
- Library downloads: Requires internet for easyeda2kicad

## Error Handling

All tools return structured error responses:

```json
{
  "error": "Error description",
  "tool": "tool_name"
}
```

Common errors:

| Error | Cause |
|-------|-------|
| Database not found | jlcparts database not downloaded; first search will trigger download |
| Component not found | LCSC ID doesn't exist in database |
| Failed to download library | Component lacks complete library at JLCPCB/EasyEDA |
| No KiCad project found | Not in project directory and path not specified |
| 7z not installed | Multi-part zip extraction requires p7zip |

## Best Practices

1. **Use basic parts when possible**: They have lower assembly fees and better availability
2. **Search by attributes when you have specs**: More accurate than free-text search
3. **Check stock quantity**: Parts with millions in stock are more reliable
4. **Compare before choosing**: Similar parts may have different specs and prices
5. **Review downloaded files**: Verify the 3D model and footprint look correct in KiCad

## Integration Examples

### Python SDK Usage

```python
from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.search import ComponentSearch, QueryParams
from jlc_has_it.mcp.tools import JLCTools

# Initialize
db = DatabaseManager()
tools = JLCTools(db)

# Search components
results = tools.search_components(
    query="100nF ceramic capacitor",
    basic_only=True,
    limit=10
)

for comp in results:
    print(f"{comp['lcsc_id']}: {comp['description']}")

# Get details
details = tools.get_component_details(lcsc_id="C1525")
print(f"Voltage: {details['attributes']['Voltage']}")

# Add to project
result = tools.add_to_project(
    lcsc_id="C1525",
    project_path="/path/to/kicad/project"
)

if result['success']:
    print(f"Added to: {result['symbol_file']}")
```

### Claude Desktop Integration

Simply ask Claude naturally:

```
"I need a 1M resistor in 0603 package"
"What's the difference between these capacitors?"
"Add this component to my project"
"Show me the most popular op-amps"
```

Claude will automatically use the MCP tools to search and integrate components.

