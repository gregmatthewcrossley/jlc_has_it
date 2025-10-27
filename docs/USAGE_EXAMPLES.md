# JLC Has It - Conversational Usage Examples

This document shows real-world conversational workflows with Claude Code using the JLC Has It MCP server.

## Getting Started

Before trying these examples, make sure you've:
1. Installed JLC Has It: `pipx install .`
2. Created `.mcp.json` in your KiCad project folder
3. Opened Claude Code in your project: `cd ~/my-project && claude`
4. Approved the 'jlc-has-it' MCP server access

## Example 1: Basic Component Search

**User:** "I need a 100nF ceramic capacitor for 16V operation. What do you have?"

**Claude's Process:**
1. Calls `search_components` with:
   - `query="100nF ceramic"`
   - `category="Capacitors"`
   - `max_price=0.05`
   - `basic_only=true`
   - `in_stock_only=true`

2. Returns top 5 results:
   ```
   C1525   | 10uF ±10% 10V X5R 0603    | Samsung    | Stock: 50000 | $0.0012
   C307331 | 10uF ±10% 16V X7R 0603   | Samsung    | Stock: 30000 | $0.0015
   C307332 | 100nF ±10% 16V X7R 0603  | Samsung    | Stock: 25000 | $0.0018
   C2011   | 100nF ±10% 50V X7R 0603  | Murata     | Stock: 15000 | $0.0025
   C1041   | 100nF ±10% 50V X7R 0402  | Yageo      | Stock: 20000 | $0.0022
   ```

**Claude's Response:**
> "I found 5 ceramic capacitors in stock. For your 16V requirement, I'd recommend **C307332** - it's a Samsung 100nF capacitor rated for 16V with excellent stock (25,000 units) at just $0.0018 each. It's a basic part, so you'll get it quickly from JLCPCB.
>
> Want me to add it to your project?"

## Example 2: Comparing Similar Parts

**User:** "What's the difference between C1525 and C307331?"

**Claude's Process:**
1. Calls `get_component_details` for C1525:
   - Description: "10uF ±10% 10V X5R 0603"
   - Voltage: 10V
   - Capacitance: 10µF
   - Price: $0.0012
   - Stock: 50000

2. Calls `get_component_details` for C307331:
   - Description: "10uF ±10% 16V X7R 0603"
   - Voltage: 16V
   - Capacitance: 10µF
   - Price: $0.0015
   - Stock: 30000

3. Calls `compare_components(["C1525", "C307331"])`:
   ```json
   {
     "comparison": {
       "components": [
         {
           "lcsc_id": "C1525",
           "description": "10uF ±10% 10V X5R 0603",
           "manufacturer": "Samsung",
           "stock": 50000,
           "price": 0.0012,
           "basic": true
         },
         {
           "lcsc_id": "C307331",
           "description": "10uF ±10% 16V X7R 0603",
           "manufacturer": "Samsung",
           "stock": 30000,
           "price": 0.0015,
           "basic": true
         }
       ],
       "attributes": {
         "Voltage": [
           {"lcsc_id": "C1525", "value": 10, "unit": "V"},
           {"lcsc_id": "C307331", "value": 16, "unit": "V"}
         ],
         "Capacitance": [
           {"lcsc_id": "C1525", "value": 10, "unit": "µF"},
           {"lcsc_id": "C307331", "value": 10, "unit": "µF"}
         ],
         "Temperature Coefficient": [
           {"lcsc_id": "C1525", "value": "X5R", "unit": ""},
           {"lcsc_id": "C307331", "value": "X7R", "unit": ""}
         ]
       }
     }
   }
   ```

**Claude's Response:**
> "Here's the comparison:
>
> **C1525** (Samsung 10uF X5R)
> - Voltage: 10V
> - Temperature Range: -55°C to +85°C (X5R)
> - Price: $0.0012 (cheapest)
> - Stock: 50,000 units
>
> **C307331** (Samsung 10uF X7R)
> - Voltage: **16V** (higher rating)
> - Temperature Range: -55°C to +125°C (X7R, better)
> - Price: $0.0015 (slightly more)
> - Stock: 30,000 units
>
> **My recommendation:** If your circuit is 5V or less, C1525 is the better choice. If it's 5-16V, go with **C307331** - the higher voltage rating and better temperature coefficient (X7R) add only $0.0003 per unit and are worth it for a 3.3V/5V rail. The X7R temperature coefficient is also more stable across temperature ranges."

## Example 3: Refining Search Results

**User:** "Find me resistors, but only the cheap ones."

**Claude (1st search):**
```
search_components(
  category="Resistors",
  basic_only=true,
  in_stock_only=true,
  limit=20
)
```

Returns: ~20 resistors from 0.001Ω to 10MΩ, mixed prices

**User:** "Can you narrow that down to ones under 1 cent?"

**Claude (refined search):**
```
search_components(
  category="Resistors",
  basic_only=true,
  in_stock_only=true,
  max_price=0.01,
  limit=20
)
```

Returns: ~20 resistors all under $0.01

**Claude's Response:**
> "Found 20 basic resistors under 1 cent! Here are the most popular (highest stock):
>
> 1. **R1206** (100Ω ±1% 0402) - Stock: 500,000 - $0.0008
> 2. **R1207** (1kΩ ±1% 0402) - Stock: 400,000 - $0.0008
> 3. **R1208** (10kΩ ±1% 0402) - Stock: 450,000 - $0.0008
>
> Most basic resistors are really cheap because they're so common. Which value do you need?"

## Example 4: Adding a Component to Your Project

**User:** "Add C307331 to my project"

**Claude's Process:**
1. Validates project is a valid KiCad project (has .kicad_pro file)
2. Calls `add_to_project` with `lcsc_id="C307331"`
3. MCP server:
   - Downloads library from JLCPCB/EasyEDA via easyeda2kicad
   - Validates symbol, footprint, and 3D model files are present
   - Creates `libraries/` directory in project if needed
   - Copies symbol to `libraries/jlc-components.kicad_sym`
   - Copies footprint to `libraries/footprints.pretty/`
   - Copies 3D model to `libraries/3d_models/`
   - Updates `sym-lib-table` and `fp-lib-table`

**Return value:**
```json
{
  "success": true,
  "lcsc_id": "C307331",
  "project": "/Users/me/my-kicad-project",
  "symbol_file": "/Users/me/my-kicad-project/libraries/jlc-components.kicad_sym",
  "footprints_dir": "/Users/me/my-kicad-project/libraries/footprints.pretty",
  "models_dir": "/Users/me/my-kicad-project/libraries/3d_models",
  "files_copied": {
    "footprints": 1,
    "models": 1
  },
  "message": "Added C307331 to my-kicad-project. Refresh KiCad libraries to use the component."
}
```

**Claude's Response:**
> "✓ Successfully added C307331 to your project!
>
> The library files are now in `./libraries/`:
> - Symbol: `jlc-components.kicad_sym`
> - Footprint: `footprints.pretty/`
> - 3D Model: `3d_models/`
>
> **Next step:** Refresh your KiCad libraries:
> 1. In KiCad, go to **Symbol Editor** or **Footprint Editor**
> 2. Choose **Preferences > Manage Libraries**
> 3. Click **Refresh**
>
> Or just close and reopen KiCad, and the library will be available."

## Example 5: Multi-Step Workflow

**User:** "I'm designing a 5V power supply. I need a capacitor for the input stage."

**Claude (Step 1):**
> "For a 5V input stage, I'd recommend a 100µF capacitor rated for at least 10V (to account for voltage spikes). Would you like SMD or through-hole?"

**User:** "SMD, something cheap with good stock"

**Claude (Step 2):**
```
search_components(
  description_contains="100µF",
  category="Capacitors",
  max_price=0.05,
  basic_only=true,
  in_stock_only=true,
  limit=10
)
```

> "Found 10 options. The best value is **C12345** - a 220µF Electrolytic at $0.15 with 5,000 in stock. Want me to show you alternatives?"

**User:** "Is 220µF okay for a 5V circuit?"

**Claude (Step 3):**
```
get_component_details("C12345")
```

> "Yes, C12345 works great:
> - **Capacitance:** 220µF (more than your 100µF target, gives better filtering)
> - **Voltage rating:** 50V (10x your 5V requirement = very safe margin)
> - **Type:** Electrolytic (perfect for input filtering)
> - **Price:** $0.15 per unit
> - **Stock:** 5,000 available
>
> The higher capacitance actually improves ripple filtering, and the 50V rating gives you plenty of safety margin."

**User:** "Perfect! Add it"

**Claude (Step 4):**
```
add_to_project("C12345")
```

> "✓ Added C12345 to your project. Refresh KiCad libraries to use it."

**User:** "Can I use this for my 3.3V supply too?"

**Claude (Step 5):**
> "Absolutely! C12345 works perfectly for 3.3V—the 50V rating and 220µF capacitance are actually even more generous for a lower voltage. You can use it everywhere in your design where you need power supply filtering."

## Example 6: Understanding Differences in Component Specs

**User:** "Why would I choose between C1525 and C307331 for my design?"

**Claude:**
```
compare_components(["C1525", "C307331"])
```

> "Great question! The main differences:
>
> **C1525 (10V rating)**
> - Best for: 3.3V circuits where every penny counts
> - Advantage: Cheapest at $0.0012
> - Risk: No safety margin if you hit 5V spikes
>
> **C307331 (16V rating)**
> - Best for: 5V circuits or anywhere you want safety margin
> - Advantage: Extra voltage headroom, X7R dielectric (better temp stability)
> - Cost: Only $0.0003 more per unit
>
> **Rule of thumb:** Choose a capacitor rated 2-3x your actual voltage for safety. So for 5V, pick at least 10V-16V rated. C307331 is the safer choice for most applications."

## Tool Parameter Reference

### search_components

```python
search_components(
    query=None,                    # "100nF ceramic", "ESP32", etc.
    category=None,                 # "Capacitors", "Resistors", "ICs"
    subcategory=None,              # "Multilayer Ceramic Capacitors MLCC"
    manufacturer=None,             # "Samsung", "Yageo", "Murata"
    basic_only=True,               # True for basic parts (JLCPCB standard)
    in_stock_only=True,            # True for in-stock only
    max_price=None,                # Float, in USD (e.g., 0.05 for 5 cents)
    package=None,                  # "0402", "0603", "0805", "DIP-8", etc.
    limit=20                       # Max results (1-100, default 20)
)
```

**Returns:** List of dicts with:
- `lcsc_id`: Part number (e.g., "C1525")
- `description`: Component specs
- `manufacturer`: Manufacturer name
- `stock`: Number in stock
- `price`: Unit price in USD
- `basic`: True if basic part

### get_component_details

```python
get_component_details(
    lcsc_id="C1525"                # Required: JLCPCB part number
)
```

**Returns:** Dict with all search fields plus:
- `attributes`: Dict of specs (voltage, capacitance, tolerance, etc.)
- `price_tiers`: List of qty/price breakpoints
- `joints`: Number of pins/pads
- `category` / `subcategory`: Category info

### compare_components

```python
compare_components(
    lcsc_ids=["C1525", "C307331"]  # List of part numbers (2-10)
)
```

**Returns:** Dict with:
- `comparison.components`: Basic info for each part
- `comparison.attributes`: Side-by-side attribute comparison
- `comparison.count`: Number of components found
- `comparison.not_found`: Any IDs that weren't found

### add_to_project

```python
add_to_project(
    lcsc_id="C1525",               # Required: JLCPCB part number
    project_path="/path/to/project" # Optional: auto-detected if not provided
)
```

**Returns:** Dict with:
- `success`: True/False
- `message`: "Added X to project..."
- `symbol_file`: Path to symbol library file
- `footprints_dir`: Path to footprints directory
- `models_dir`: Path to 3D models directory
- `files_copied`: Count of files copied

## Tips for Better Searches

1. **Be specific:** "100nF 16V ceramic SMD" gives better results than "capacitor"

2. **Use categories:** If you know the component type, specify it:
   ```
   category="Capacitors"
   category="Resistors"
   category="Integrated Circuits"
   ```

3. **Check stock:** Always use `in_stock_only=true` (default) to avoid surprises

4. **Basic parts preferred:** Basic parts have:
   - Lower assembly fees at JLCPCB
   - Typically faster delivery
   - Better availability
   - Use `basic_only=true` (default)

5. **Filter by price:** For cost-sensitive designs:
   ```
   max_price=0.01  # Under 1 cent
   ```

6. **Compare before committing:** Always get details and compare similar parts to understand differences

## Common Patterns

### Finding Popular/Common Parts

```
search_components(
    category="Capacitors",
    basic_only=true,
    in_stock_only=true,
    limit=20
)
```

The results will be sorted by:
1. Basic parts first
2. High stock quantity second
3. Lower price third

### Finding Budget Components

```
search_components(
    category="Resistors",
    basic_only=true,
    max_price=0.01,  # Under 1 cent
    limit=50
)
```

### Finding Specific Voltage Components

```
search_components(
    query="16V",  # Includes in description
    category="Capacitors",
    basic_only=true,
    limit=20
)
```

### Finding Parts from Specific Manufacturer

```
search_components(
    manufacturer="Samsung",
    category="Capacitors",
    basic_only=true,
    limit=20
)
```

## Troubleshooting

### "I can't find the component I need"

Try these steps:
1. **Broaden search:** Remove category filter
2. **Be less specific:** "capacitor" instead of "100nF 16V X5R"
3. **Check availability:** Try `in_stock_only=false`
4. **Try alternatives:** Use `compare_components` to find similar parts

### "The component I found doesn't have a library"

Some JLCPCB components don't have complete library packages:
- Newer components may not be in EasyEDA library yet
- Try searching for similar alternatives
- Check https://lcsc.com/search?q=[LCSC_ID] manually

### "Library add failed"

Common issues:
1. **easyeda2kicad not installed:** `pip install easyeda2kicad`
2. **Project not found:** Specify `project_path` explicitly
3. **Invalid project:** Make sure project has `.kicad_pro` file

## Advanced Usage

### Building Complex Filters

Claude can combine multiple parameters:

**Example: "Find cheap ceramic capacitors from Samsung with high stock"**
```
search_components(
    manufacturer="Samsung",
    category="Capacitors",
    query="ceramic",
    max_price=0.05,
    basic_only=true,
    in_stock_only=true,
    limit=20
)
```

### Comparing Entire Product Lines

Compare 3-5 similar parts to understand the tradeoffs:

**Example: "Compare the Samsung and Murata 10µF capacitors"**
```
compare_components([
    "C1525",    # Samsung 10µF 10V
    "C307331",  # Samsung 10µF 16V
    "C1025",    # Murata 10µF 10V
])
```

## Next Steps

Once you're comfortable with these workflows:

1. **Explore Phase 7 optimizations:**
   - FTS5 full-text search for <100ms queries
   - Pagination for large result sets

2. **Consider using the CLI tool:**
   - `jlc-has-it search "100nF capacitor"`
   - Good for scripting and automation

3. **Customize your searches:**
   - Remember your favorite components
   - Build a "parts bin" of trusted components
   - Document why you chose certain parts
