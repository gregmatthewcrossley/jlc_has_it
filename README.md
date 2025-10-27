# JLC Has It

A local MCP server providing conversational component search for KiCad through Claude Code/Desktop.

## Quick Start

### 1. Install System Dependencies (macOS)

```bash
# Install p7zip (required for database extraction)
brew install p7zip

# Optional: install pipx for clean Python package isolation
# (if you want system-wide installation instead of development mode)
brew install pipx
```

### 2. Install JLC Has It

```bash
git clone https://github.com/gcrossley/jlc_has_it.git
cd jlc_has_it

# Install with pipx (clean, isolated installation)
pipx install .
pipx inject jlc-has-it easyeda2kicad
```

### 3. Configure Claude Code

Navigate to your KiCad project folder and run the setup script:

```bash
cd ~/my-kicad-projects/my-project
/path/to/jlc_has_it/setup-mcp.sh
```

This creates a `.mcp.json` file in your project directory that tells Claude Code about the MCP server.

**Important**: After running the setup script:
1. Close any running Claude Code instances (Cmd+Q or click Quit)
2. Reopen Claude Code in your project folder: `claude`
3. When prompted, **approve access to the 'jlc-has-it' MCP server** (Claude Code shows a security prompt)
4. The MCP tools are now available in your Claude Code session

**Manual setup** (if you prefer):
Create `.mcp.json` in your KiCad project root directory:
```json
{
  "mcpServers": {
    "jlc-has-it": {
      "command": "jlc-has-it-mcp",
      "args": []
    }
  }
}
```

### 4. Start Using!

You've already navigated to your KiCad project and opened Claude Code in step 3. Now just ask Claude Code naturally:

```
"I need a 100nF ceramic capacitor for 16V operation"
"What resistors do you have in stock?"
"Add C1525 to my project"
"Compare these two capacitors: C1525 and C307331"
```

Claude will search JLCPCB, show you results, and can add components directly to your project's library.

### Uninstall

If you installed with pipx, uninstall with:

```bash
pipx uninstall jlc-has-it
```

If you installed in development mode, remove the directory and virtualenv:

```bash
cd /path/to/jlc_has_it
deactivate  # if in virtualenv
cd ..
rm -rf jlc_has_it
```

To remove the MCP configuration from a project, delete the `.mcp.json` file from your KiCad project root:

```bash
rm .mcp.json
```

To remove the cached database:

```bash
rm ~/.cache/jlc_has_it/cache.sqlite3
```

---

## Overview

JLC Has It helps hobbyist electronics designers using KiCad 9.0 to quickly find and add JLCPCB components to their projects through a natural conversational interface.

### Problem

Finding suitable components is time-consuming. Components must:
- Be in stock at JLCPCB (preferably "basic" parts)
- Be well-known, commonly used, and relatively inexpensive
- Have a complete KiCad library package (symbol, footprint, and 3D model)

### Solution

**Local MCP server** providing conversational component search through Claude Code/Desktop:

```
User: "I need a through-hole capacitor rated for 50V and 220uF"

Claude: [searches via MCP tools]
        "I found 12 parts with complete KiCad libraries.
         Top options:
         1. C12345 - 220uF 50V Electrolytic | Stock: 5000 | $0.15
         2. C23456 - 220uF 63V Ceramic X7R  | Stock: 3000 | $0.45

         For power supply filtering, the electrolytic is typical.
         Want me to add it to your project?"

User: "Add the electrolytic one"

Claude: [calls add_to_project MCP tool]
        "Added C12345 to ./my-project/libraries/.
         Refresh your KiCad libraries to use it."
```

## Architecture

**Layered Architecture:**
- **Core library** (LLM-agnostic): Component search, database access, library downloading
- **MCP interface** (primary): Conversational interface through Claude Code/Desktop
- **CLI tool** (optional): Simple CLI for scripting/automation

**Key Components:**
- Local MCP server runs on your machine
- Uses jlcparts SQLite database (JLCPCB component data)
- Downloads libraries via easyeda2kicad.py
- Writes to project-specific KiCad libraries

## Installation

```bash
# Clone the repository
git clone https://github.com/gcrossley/jlc_has_it.git
cd jlc_has_it

# Install in development mode
pip install -e .

# Or with CLI support
pip install -e ".[cli]"
```

## Configuration

### MCP Server Setup

Add to your `.claude/mcp_settings.json`:

```json
{
  "mcpServers": {
    "jlc-has-it": {
      "command": "jlc-has-it-mcp",
      "args": []
    }
  }
}
```

Restart Claude Code, and you can now ask Claude to search for components!

## Usage

### Conversational Interface (via MCP)

Just talk to Claude:

```
"I need a 100nF ceramic capacitor rated for 50V in 0402 package"
"Find me an ESP32 module"
"What's the difference between these capacitors?"
"Add C12345 to my project at ./my-kicad-project"
```

### CLI Tool (Optional)

```bash
# Search for components
jlc-has-it search "50v 220uF SMD capacitor"

# Add to KiCad project
jlc-has-it add C12345 --project ./my-kicad-project
```

## Requirements

- **Python**: 3.9+
- **KiCad**: 9.0 (for library format compatibility)
- **System tools**:
  - `7z` for multi-part zip extraction: `brew install p7zip` (macOS) or `apt install p7zip-full` (Linux)
  - `easyeda2kicad` for library downloads: `pip install easyeda2kicad`

## How It Works

### 1. Database Management

JLC Has It maintains a local cache of the jlcparts SQLite database:

```
~/.cache/jlc_has_it/cache.sqlite3
```

- **Auto-update**: Database is automatically refreshed if >1 day old
- **Lazy loading**: Database only downloaded when first needed
- **Multi-part handling**: Handles large multi-part zip files (100MB+)

### 2. Component Search

When you ask Claude for a component, the MCP server:

1. Queries the local jlcparts SQLite database
2. Filters by your criteria (voltage, package, manufacturer, etc.)
3. Ranks results by:
   - Basic parts first (lower assembly fees at JLCPCB)
   - Higher stock quantity
   - Lower price
4. Returns top matches to Claude for presentation

**Search filters available:**
- Category (Capacitors, Resistors, ICs, etc.)
- Subcategory (MLCC, Electrolytic, etc.)
- Manufacturer (Samsung, Yageo, etc.)
- Voltage/Current/Capacitance ranges
- Package type (0402, 0603, 0805, through-hole, etc.)
- Price limits
- Stock availability

### 3. Library Download & Integration

When you select a component to add:

1. **easyeda2kicad** downloads from JLCPCB/EasyEDA:
   - Symbol file (.kicad_sym)
   - Footprint files (.kicad_mod)
   - 3D CAD models (.step or .wrl files)

2. **Validation**: Confirms all files are present and non-empty

3. **Project integration**: Copies files to your KiCad project:
   ```
   my_project/
   ├── libraries/
   │   ├── jlc-components.kicad_sym
   │   ├── footprints.pretty/
   │   │   └── [component footprints]
   │   └── 3d_models/
   │       └── [component 3D models]
   ├── sym-lib-table
   └── fp-lib-table
   ```

4. **Library registration**: Updates KiCad library tables so the project knows where to find the files

### 4. MCP Tools

The MCP server exposes four tools to Claude:

#### `search_components`

Search for components matching your criteria.

```
Parameters:
  query (string): Free-text search (e.g., "100nF ceramic capacitor")
  category (string): Component category (e.g., "Capacitors")
  subcategory (string): More specific category
  manufacturer (string): Filter by manufacturer
  basic_only (bool): Only show Basic parts (default: true)
  in_stock_only (bool): Only show in-stock components (default: true)
  max_price (number): Maximum unit price in USD
  package (string): Package type (e.g., "0603")
  limit (integer): Maximum results to return (default: 20)

Returns:
  - LCSC ID (JLCPCB part number)
  - Description
  - Manufacturer and part number
  - Stock quantity
  - Unit price
  - Whether it's a "basic" part
```

#### `get_component_details`

Get full specifications for a single component.

```
Parameters:
  lcsc_id (string, required): JLCPCB part number (e.g., "C1525")

Returns:
  - All search fields plus:
  - Complete attribute list (voltage, capacitance, tolerance, etc.)
  - Price tiers for bulk quantities
  - Number of pins/joints
```

#### `add_to_project`

Add a component to your KiCad project.

```
Parameters:
  lcsc_id (string, required): JLCPCB part number
  project_path (string): Path to KiCad project (auto-detected if not provided)

Returns:
  - Success status
  - Paths where files were copied
  - Number of footprints and models added
  - Message: "Refresh KiCad libraries to use the component"
```

#### `compare_components`

Compare specifications of multiple parts side-by-side.

```
Parameters:
  lcsc_ids (array of strings, required): List of JLCPCB part numbers

Returns:
  - Component list with basic info
  - Detailed attribute comparison table
```

## Development

### Setting Up Development Environment

**Clone the repository:**

```bash
git clone https://github.com/gcrossley/jlc_has_it.git
cd jlc_has_it
```

**Install for development:**

```bash
# Install package with development and CLI dependencies
pip install -e ".[dev,cli]"
```

### Running Tests

```bash
# Run all unit tests (104 tests, all passing)
pytest

# Run integration tests (with real JLCPCB database)
pytest tests/integration/ -v

# Run tests in parallel
pytest -n auto
```

### Code Quality

```bash
# Format code with black
black .

# Lint with ruff
ruff check .

# Type checking with mypy
mypy jlc_has_it/
```

### Project Structure

```
jlc_has_it/
├── core/                      # Core business logic (LLM-agnostic)
│   ├── database.py           # jlcparts SQLite access & updates
│   ├── search.py             # Component search & ranking
│   ├── models.py             # Data models (Component, PriceTier, etc.)
│   ├── library_downloader.py # easyeda2kicad integration (parallel)
│   └── kicad/
│       └── project.py        # KiCad project file handling
├── mcp/                       # MCP server (primary interface)
│   ├── __main__.py           # MCP server implementation
│   └── tools.py              # Tool implementations
├── cli/                       # CLI tool (optional, for scripting)
│   └── main.py
└── tests/
    ├── core/                 # Unit tests for core modules
    ├── integration/          # Integration tests with live data
    └── conftest.py           # Shared test fixtures
```

### Testing

**Unit Tests** (104 tests, all mocked):
- Database management and downloads
- Component search and filtering
- Library downloading and validation
- KiCad project integration
- Data model parsing

Run with: `pytest tests/core/ tests/test_sample.py -v`

**Integration Tests** (require internet):
- Real JLCPCB database queries
- Live easyeda2kicad downloads
- End-to-end component addition to test projects

Run with: `pytest tests/integration/ -v`

### Common Development Tasks

**Adding a new search filter:**
1. Update `QueryParams` dataclass in `core/search.py`
2. Add SQL condition in `ComponentSearch.search()`
3. Add tests to `tests/core/test_search.py`
4. Update MCP tool schema in `mcp/__main__.py`

**Debugging component searches:**
```python
from jlc_has_it.core.database import DatabaseManager
from jlc_has_it.core.search import ComponentSearch, QueryParams

db = DatabaseManager()
conn = db.get_connection()
search = ComponentSearch(conn)

# Example: Find all 100nF capacitors
results = search.search(QueryParams(
    description_contains="100nF",
    category="Capacitors",
    in_stock_only=True,
    limit=10
))

for comp in results:
    print(f"{comp.lcsc}: {comp.description} - Stock: {comp.stock}, Price: ${comp.price}")
```

**Testing library downloads:**
```python
from jlc_has_it.core.library_downloader import LibraryDownloader

downloader = LibraryDownloader()
lib = downloader.download_component("C1525")  # 100nF Samsung capacitor

if lib and lib.is_valid():
    print(f"Symbol: {lib.symbol_path}")
    print(f"Footprints: {list(lib.footprint_dir.glob('*.kicad_mod'))}")
    print(f"3D Models: {list(lib.model_dir.glob('*.step'))}")
```

## Troubleshooting

### "7z command not found"

Install p7zip for your system:
- **macOS**: `brew install p7zip`
- **Ubuntu/Debian**: `apt install p7zip-full`
- **Fedora/RHEL**: `dnf install p7zip`

### "easyeda2kicad command not found"

Install easyeda2kicad Python package:
```bash
pip install easyeda2kicad
```

### Database download is slow

The first download of the jlcparts database (100MB+) may take several minutes. Subsequent updates only happen if the database is >1 day old. You can check the database age:

```python
from jlc_has_it.core.database import DatabaseManager

db = DatabaseManager()
age = db.check_database_age()
if age:
    print(f"Database age: {age.total_seconds() / 3600:.1f} hours")
```

### Component library downloads fail

This usually means easyeda2kicad couldn't find the component at JLCPCB/EasyEDA:
- Verify the LCSC ID is correct
- Check that the component exists: https://lcsc.com/search?q=[LCSC_ID]
- Some newer components may not have complete libraries yet

See more detailed troubleshooting in [docs/troubleshooting.md](docs/troubleshooting.md)

## Data Sources

**Component data:**
- **jlcparts database** by Jan Mrázek (MIT License)
- GitHub: https://github.com/yaqwsx/jlcparts
- Daily-updated SQLite database with 250,000+ JLCPCB components
- Auto-cached locally at `~/.cache/jlc_has_it/`

**Component libraries:**
- **easyeda2kicad.py** by uPesy (AGPLv3)
- GitHub: https://github.com/uPesy/easyeda2kicad.py
- Downloads symbols, footprints, and 3D models from JLCPCB/EasyEDA
- Requires: `pip install easyeda2kicad`

## License

MIT License - See LICENSE file for details

## Attribution

- Component data provided by jlcparts (https://github.com/yaqwsx/jlcparts), Copyright 2024 Jan Mrázek, Licensed under the MIT License
- Library download functionality uses easyeda2kicad.py (https://github.com/uPesy/easyeda2kicad.py), Licensed under AGPLv3

## Contributing

Contributions welcome! Areas for improvement:
- Additional search filters (power dissipation, frequency response, etc.)
- Better ranking algorithm based on user preferences
- CLI enhancements
- Documentation improvements
- Performance optimizations
