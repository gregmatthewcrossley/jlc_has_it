# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**JLC Has It** is a tool for hobbyist electronics designers using KiCad 9.0 to quickly find and add JLCPCB components to their projects.

### Problem Statement

Finding suitable components is time-consuming. Components must meet all these criteria:
- In stock at JLCPCB (preferably "basic" parts, preferably SMD)
- Well-known, commonly used, relatively inexpensive
- Has a complete KiCad library package available from JLCPCB/EasyEDA
  - Symbol, footprint, and 3D CAD model (STEP format)
  - Downloaded via easyeda2kicad.py Python tool
  - Only show parts if complete package is available

### Solution

**Local MCP server** providing conversational component search through Claude Code/Desktop:

**User Experience:**
```
User: "I need a through-hole capacitor rated for 50V and 220uF"

Claude: [searches via MCP tools]
        "I found 12 parts with complete KiCad libraries.
         Top options:
         1. C12345 - 220uF 50V Electrolytic | Stock: 5000 | $0.15
         2. C23456 - 220uF 63V Ceramic X7R  | Stock: 3000 | $0.45

         For power supply filtering, the electrolytic is typical.
         Want me to add it to your project?"

User: "What's the difference between them?"

Claude: "The electrolytic (C12345) is larger but cheaper and common
         for bulk filtering. The ceramic (C23456) is more compact
         with lower ESR but costs more. Which do you prefer?"

User: "Add the electrolytic one"

Claude: [calls add_to_project MCP tool]
        "Added C12345 to ./my-project/libraries/.
         Refresh your KiCad libraries to use it."
```

**Technical Flow:**
1. User has natural conversation with Claude Code/Desktop
2. Claude calls MCP tools (search, compare, add_to_project)
3. MCP server queries jlcparts database
4. Downloads/validates libraries in parallel for top candidates
5. Returns only parts with complete packages
6. User selects via conversation → Claude adds to KiCad project

## Architecture

### Phased Approach

**Phase 1** (MVP): Core library + Local MCP server
- Python-based (easier KiCad integration)
- MCP server runs locally on user's machine
- Conversational interface through Claude Code/Desktop
- Uses jlcparts SQLite database (downloaded locally)
- Writes to project-specific KiCad libraries
- Optional: Simple CLI tool for scripting/automation

**Phase 2** (Optional enhancements):
- Cache downloaded libraries to speed up repeat searches
- Add more MCP tools (compare specs, show datasheets, etc.)
- Improve ranking algorithm with user preferences

**Phase 3** (Future): KiCad Action Plugin
- Direct integration into KiCad (no manual library refresh)
- Add menu item inside KiCad
- Insert components directly into open schematics

### Core Components

**Layered Architecture:** Core library (LLM-agnostic) + MCP interface + optional CLI

```
jlc_has_it/
├── core/                      # Core business logic (LLM-agnostic)
│   ├── database.py           # jlcparts SQLite access & updates
│   ├── search.py             # Component search & ranking
│   ├── library_downloader.py # easyeda2kicad integration (parallel)
│   └── kicad/                # KiCad file handling
│       ├── symbol.py         # .kicad_sym manipulation
│       ├── footprint.py      # .kicad_mod handling
│       └── project.py        # Project library integration
├── mcp/                       # MCP server (primary interface)
│   ├── server.py             # MCP server implementation
│   ├── tools.py              # Tool definitions
│   │   ├── search_components()
│   │   ├── get_component_details()
│   │   ├── add_to_project()
│   │   └── compare_components()
│   └── __main__.py           # Entry point: jlc-has-it-mcp
├── cli/                       # Optional: Simple CLI for scripting
│   └── main.py               # Entry point: jlc-has-it
└── tests/
    ├── core/
    ├── mcp/
    └── integration/
```

### KiCad File Formats

KiCad uses plain-text S-expression formats:
- **`.kicad_sym`**: Symbol library files (one file, multiple symbols)
- **`.kicad_mod`**: Footprint files (one file per footprint)
- **`.kicad_pro`**: Project file (references library locations)
- **`sym-lib-table`**: Symbol library table (S-expression format)
- **`fp-lib-table`**: Footprint library table (S-expression format)
- **`.step`/`.wrl`**: 3D models

Components are added to **project-specific libraries**, typically:
```
my_project/
├── my_project.kicad_pro
├── my_project.kicad_sch
├── sym-lib-table              # Must register symbol library here
├── fp-lib-table               # Must register footprint library here
├── libraries/
│   ├── jlc-components.kicad_sym
│   ├── footprints.pretty/     # .pretty suffix is KiCad convention
│   │   └── *.kicad_mod
│   └── 3d_models/
│       └── *.step
```

**Important**: Library tables must be updated when adding new libraries, or KiCad won't see them. Use relative paths in library tables for portability.

### Integration Points

- **jlcparts Database**: Daily-updated SQLite database with all JLCPCB components
  - URL: https://yaqwsx.github.io/jlcparts/data/
  - License: MIT (Copyright 2024 Jan Mrázek)
  - Update schedule: Daily at 3AM UTC
  - Size: ~50MB compressed
  - No authentication required
- **MCP (Model Context Protocol)**: Primary interface
  - Local MCP server runs on user's machine
  - Claude Code/Desktop connects via stdio transport
  - Provides tools: search_components, get_component_details, add_to_project, compare_components
  - User interacts through natural conversation with Claude
  - **No Claude API calls needed** - user already in Claude!
- **Component Libraries**: JLCPCB/EasyEDA via easyeda2kicad.py (Phase 1 only)
  - GitHub: https://github.com/uPesy/easyeda2kicad.py
  - PyPI: https://pypi.org/project/easyeda2kicad/
  - Downloads symbols, footprints, and 3D models directly from JLCPCB/EasyEDA
  - Downloads run in parallel for top N candidates
  - Only parts with complete packages shown to user
  - Future phases may add SnapEDA API as fallback source
- **KiCad Library Format**: Manipulate valid S-expression files

### Key Workflows

1. **Database Management**:
   - Check local database age (stored in ~/.cache/jlc_has_it/)
   - If >1 day old or missing, download fresh database
   - Download multi-part zip files (cache.z01, cache.z02, cache.zip)
   - Extract and validate SQLite database
   - Use for all subsequent component queries

2. **Conversational Component Search** (via MCP):
   - User asks Claude: "I need a through-hole capacitor rated for 50V and 220uF"
   - Claude calls MCP `search_components` tool with parameters
   - MCP server:
     - Parses parameters from Claude's tool call
     - Queries jlcparts SQLite database for matching parts
     - Filters by availability (basic > extended), stock status
     - Ranks results using scoring algorithm
     - Takes top N candidates (e.g., 20 parts)
     - **Downloads libraries in parallel** using easyeda2kicad for all N candidates
     - **Validates each download** (exit code 0, symbol exists, footprint exists, 3D model exists)
     - **Discards parts with incomplete packages**
     - Returns only parts with complete, validated libraries to Claude
   - Claude presents results conversationally with context and advice
   - **User can ask follow-up questions** before selecting

3. **Library Integration** (via MCP tool):
   - User tells Claude: "Add C12345 to my project"
   - Claude calls MCP `add_to_project` tool
   - MCP server:
     - Libraries already downloaded and validated from search
     - Appends symbol to project's `.kicad_sym` file
     - Copies footprint to project's `footprints.pretty/` directory
     - Copies 3D models to project's `3d_models/` directory
     - Updates library tables if needed
   - Claude confirms: "Added C12345. Refresh KiCad libraries to use it."

4. **KiCad Refresh** (manual, Phase 1):
   - User manually refreshes symbol/footprint libraries in KiCad
   - Or reopens the KiCad project
   - Component now available for use in schematic

## Git Workflow

**Note**: This project uses different git conventions than the global CLAUDE.md (which is Rails-specific).

### Commit Authorship

**CRITICAL: Always use `--no-gpg-sign` flag. Never sign commits.**

- When Claude makes commits autonomously, use both `--author` and set committer identity:
  - `GIT_COMMITTER_NAME="Claude Code" GIT_COMMITTER_EMAIL="noreply@anthropic.com" git commit --author="Claude Code <noreply@anthropic.com>" --no-gpg-sign`
  - Or use environment variables for all git commands in the session
- **DO NOT OMIT `--no-gpg-sign`**: This prevents triggering user's 1Password SSH signing which will block the commit
- **DO NOT use any -S or --gpg-sign flags**: Always explicitly use `--no-gpg-sign`
- This provides clear attribution in git history (both author and committer show as Claude)
- Human-made commits use the user's normal git identity
- For collaborative work, use Co-Authored-By trailer

### Commit Messages

Use standard format:
```
Short summary (50 chars or less)

- Specific change 1
- Specific change 2
- Reasoning if needed
```

### When to Commit

- After completing each task (or logical checkpoint within a task)
- When explicitly requested by user
- Before major refactoring or risky changes


## Task Management

This project uses a structured task system in the `tasks/` directory:
- **21 active tasks** organized by phase (00-setup, 01-jlcpcb, 02-library, etc.)
- Each task is a YAML file with ID, dependencies, acceptance criteria, and status
- See `tasks/README.md` for overview
- See `tasks/INDEX.md` for task summary
- See `tasks/DEPENDENCIES.md` for execution order and dependency graph
- See `tasks/PROJECT_STATUS.md` for comprehensive project status

When working on this project:
1. Check `tasks/INDEX.md` to find relevant tasks
2. Review dependencies before starting a task
3. Follow acceptance criteria strictly
4. Update task status as you progress
5. Run tests to verify completion

## Recommended Python Libraries

Based on task analysis, these libraries will likely be useful:

**KiCad Integration:**
- `kiutils` or `kicad-library-utils` - KiCad file format handling
- `sexpdata` or custom parser - S-expression parsing

**MCP Integration:**
- `mcp` - Model Context Protocol SDK from Anthropic
- `pydantic` - Data validation for tool parameters

**CLI & UI (optional):**
- `typer` or `click` - CLI framework for optional CLI tool
- `rich` - Terminal formatting, tables, progress bars

**HTTP & APIs:**
- `requests` or `httpx` - HTTP client for downloading libraries
- `easyeda2kicad` - Library download tool

**Testing:**
- `pytest` - Test framework
- `pytest-mock` - Mocking utilities
- `pytest-vcr` - Record/replay HTTP interactions

**Development:**
- `black` - Code formatting
- `ruff` - Fast linting
- `mypy` - Type checking

## Development Commands

```bash
# Install dependencies
pip install -e .

# Run MCP server (for development/testing)
jlc-has-it-mcp

# Or run directly with Python
python -m jlc_has_it.mcp

# Configure in Claude Code (.claude/mcp_settings.json):
{
  "mcpServers": {
    "jlc-has-it": {
      "command": "jlc-has-it-mcp",
      "args": []
    }
  }
}

# Run tests
pytest

# Format code
black .
ruff check .

# Type checking
mypy jlc_has_it/

# Optional: Run CLI tool (for scripting/automation)
jlc-has-it search "50v 220uF SMD capacitor"
```

## Development Notes

### Component Data Model

Components should be represented using dataclasses matching the jlcparts database schema:

```python
@dataclass
class Component:
    lcsc: str                    # JLCPCB part number (e.g., "C1525")
    mfr: str                     # Manufacturer part number
    description: str
    manufacturer: str
    category: str                # Top-level category
    subcategory: str             # Subcategory
    joints: int                  # Number of pins/pads
    basic: bool                  # True=Basic part, False=Extended part
    stock: int                   # Current stock quantity
    price_tiers: list[dict]      # [{"qty": 1, "price": 0.0012}, ...]
    attributes: dict             # Normalized specifications (see below)

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

### Attributes JSON Structure (from jlcparts)

The `attributes` field contains normalized component specifications:

```python
{
    "Capacitance": {"value": 100, "unit": "nF"},
    "Voltage": {"value": 16, "unit": "V"},
    "Tolerance": {"value": 10, "unit": "%"},
    "Package": "0402",
    "Temperature Coefficient": "X7R"
}
```

Access using JSON functions in SQLite or parse after retrieval in Python.

### Ranking Algorithm

Components should be ranked using weighted scoring:
- Basic parts: +100 points
- In stock: +50 points
- Common manufacturers: +20 points
- Price: deduct cost value
- Exact spec match: +30 points

Higher scores = better matches. Make weights configurable.

### Testing Strategy

- Mock JLCPCB API responses to avoid hitting live service
- Use `pytest-vcr` to record/replay HTTP interactions
- Test KiCad file generation with known-good reference files
- Validate S-expression syntax (KiCad will fail silently on malformed files)
- Verify generated files by attempting to open them in real KiCad 9.0

### S-Expression Handling

KiCad files use Lisp-like S-expressions: `(key value (nested...))`

**Critical requirements:**
- Parse existing files without losing data or formatting
- Generate syntactically valid output (KiCad fails silently on errors)
- Preserve KiCad-specific formatting conventions
- Support round-trip: read → modify → write → read

**Options:**
- Use existing library (`sexpdata`, `kiutils`)
- Implement custom parser if existing libraries insufficient
- Always validate generated S-expressions before writing

### Error Handling

- JLCPCB availability changes frequently - cache may be stale
- Symbol/footprint downloads may fail - provide graceful degradation
- KiCad library files must be valid S-expressions - validate before writing
- Back up library files before modifying (add `.bak` suffix)
- Handle file locking (KiCad may have files open)

### Performance Considerations

- JLCPCB has thousands of components - implement pagination
- Symbol/footprint downloads can be slow - show progress
- Consider adding SQLite cache when search performance becomes an issue

## Testing and Development

### Virtual Environment
A virtual environment (`.venv`) exists in the project. Always activate it:
```bash
cd /Users/gregmatthewcrossley/Developer/jlc_has_it
source .venv/bin/activate
```

### Running Tests

**Install dev dependencies** (if needed):
```bash
pip install -e ".[dev]"  # Includes pytest, pytest-timeout, pytest-mock, etc.
```

**Run tests** (use background mode for long test runs):
```bash
# All core tests (96 tests, ~0.2s)
pytest tests/core/ -v

# Specific test file
pytest tests/core/test_models.py -v

# Skip slow tests (real database tests)
pytest tests/ -m "not slow"

# With coverage
pytest tests/ --cov=jlc_has_it --cov-report=html
```

**IMPORTANT: For longer test runs, use background mode** to avoid blocking:
```bash
# Run full test suite in background (use BashOutput to check progress)
# From Bash tool: run_in_background: true
pytest tests/ -v 2>&1

# Or manually in terminal:
# Open new terminal and use: pytest tests/ -v
# Or use: nohup pytest tests/ -v > test_results.log 2>&1 &
```

**Note:** Tests now include verbose progress output showing:
- Database status at startup (jlcparts database ready status)
- Live test results as they complete: `[  1] ✓ PASS test_name`
- Final summary with passed/failed/skipped counts

This makes it always clear what tests are running and which have finished.

### Test Organization
- `tests/core/test_models.py` - Data models (12 tests)
- `tests/core/test_project_integration.py` - KiCad integration (31 tests)
- `tests/core/test_library_downloader.py` - Library downloads (21 tests)
- `tests/core/test_database.py` - Database layer (17 tests)
- `tests/core/test_search.py` - Component search (15 tests)
- `tests/core/test_fts5_and_pagination.py` - FTS5 & pagination (18 tests)
- `tests/mcp/test_tools.py` - MCP tools (30 tests, requires real DB)
- `tests/integration/test_end_to_end.py` - Full workflows (15 tests)
- `tests/integration/test_real_database.py` - Real DB tests (12 tests)

**Total**: 197+ tests, 96+ pass with test database, rest require 11.8GB jlcparts database

### Test Timeouts
- **Default**: 30 seconds (via pytest-timeout plugin)
- **Database tests**: 20 seconds (FTS5 operations)
- **Network tests**: 30 seconds (easyeda2kicad downloads)

If tests hang, they'll timeout with clear error message. Increase timeout temporarily if needed:
```bash
pytest tests/ --timeout=60
```

### Key Testing Notes
1. FTS5 table is auto-created when `enable_fts5=True` on first connection (one-time ~10-30s)
2. Test database doesn't include FTS5 to keep it small; FTS5 tested separately with real DB
3. 3 tests intentionally skipped (package filtering, attribute filtering - not yet implemented)
4. Previous failing test removed: `test_search_by_description` was redundant with FTS5 tests

### Code Quality Tools
```bash
# Format code (auto-fixes most issues)
black jlc_has_it/

# Lint check
ruff check jlc_has_it/

# Type checking
mypy jlc_has_it/

# Run all checks
black . && ruff check . && mypy jlc_has_it/ && pytest tests/core/
```
