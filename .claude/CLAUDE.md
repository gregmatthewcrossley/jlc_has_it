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

- When Claude makes commits autonomously, use `--author="Claude Code <noreply@anthropic.com>"`
- **IMPORTANT**: Always use `--no-gpg-sign` flag when committing as Claude to avoid triggering user's 1Password SSH signing
- This provides clear attribution in git history
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

### Git Worktrees for Parallel Sessions

**Use git worktrees to run multiple Claude Code sessions in parallel, each working on different tasks simultaneously.**

#### What are Git Worktrees?

Git worktrees allow multiple working directories from the same repository, each checked out to different branches. This enables true parallel development without conflicts.

#### Coordinator Workflow (Main Worktree)

The main repository acts as the coordinator:

```bash
# From main worktree: /Users/gregmatthewcrossley/Developer/jlc_has_it/
# Create worktrees for parallel tasks

git worktree add ../jlc_has_it-task-00-001 -b task/00-001
git worktree add ../jlc_has_it-task-01-001 -b task/01-001
git worktree add ../jlc_has_it-task-02-001 -b task/02-001

# List all worktrees
git worktree list

# Now open Claude Code in each worktree directory:
# - Terminal 1: cd ../jlc_has_it-task-00-001 && claude
# - Terminal 2: cd ../jlc_has_it-task-01-001 && claude
# - Terminal 3: cd ../jlc_has_it-task-02-001 && claude

# Each session works independently on its task
# When tasks complete, return to main worktree and merge

cd /Users/gregmatthewcrossley/Developer/jlc_has_it/
git merge task/00-001
git merge task/01-001
git merge task/02-001

# Clean up worktrees when done
git worktree remove ../jlc_has_it-task-00-001
git worktree remove ../jlc_has_it-task-01-001
git worktree remove ../jlc_has_it-task-02-001

# Optional: delete merged branches
git branch -d task/00-001 task/01-001 task/02-001
```

#### Worker Agent Instructions

When working in a worktree, each Claude session should:

```bash
# Verify you're in the correct worktree and branch
pwd
git branch --show-current

# Complete the assigned task
# Follow acceptance criteria from tasks/XX-YYY-task-name.yaml

# Commit work with Claude authorship
git add .
git commit --author="Claude Code <noreply@anthropic.com>" -m "Complete task XX-YYY

- Change 1
- Change 2
"

# Do NOT push to remote
# Do NOT merge to main (coordinator handles this)
# Report completion status
```

#### Benefits of Worktrees for This Project

- ✅ **True parallelization**: 3-5 Claude sessions work simultaneously without conflicts
- ✅ **Isolated environments**: Each task has its own virtualenv, dependencies, test runs
- ✅ **Clean history**: Each branch has focused commits for one task
- ✅ **Easy rollback**: Abandon a worktree if task goes wrong
- ✅ **No context switching**: Main worktree stays clean as coordinator

#### Recommended Parallel Task Groups

Based on `tasks/DEPENDENCIES.md`, these groups can run in parallel:

**Group 1: Initial Research (3 worktrees)**
- `task/01-001` - Research JLCPCB API
- `task/02-001` - Research KiCad formats
- `task/04-001` - Research library sources

**Group 2: Phase 0 Setup (3 worktrees)**
- `task/00-001` - Init Python project (run first, sequentially)
- `task/00-002` - Setup testing (after 00-001)
- `task/00-003` - Setup linting (after 00-001)

**Group 3: Parsers (2 worktrees)**
- `task/02-003` - Symbol reader
- `task/02-005` - Footprint handler

**Group 4: Search Components (2 worktrees)**
- `task/03-002` - Spec filtering
- `task/03-003` - Ranking algorithm

#### Worktree Naming Convention

Use this pattern for consistency:
```
../jlc_has_it-task-XX-YYY/
```

Where `XX-YYY` matches the task ID (e.g., `00-001`, `02-003`).

#### Important Notes

- Worktrees share the same git object database (commits, branches)
- You cannot check out the same branch in multiple worktrees simultaneously
- Each worktree can have its own `.venv/` and dependencies
- The `.claude/settings.local.json` is local to each worktree

## Task Management

This project uses a structured task system in the `tasks/` directory:
- **27 atomic tasks** organized by phase (00-setup, 01-jlcpcb, 02-kicad, etc.)
- Each task is a YAML file with ID, dependencies, acceptance criteria, and status
- See `tasks/INDEX.md` for task overview
- See `tasks/DEPENDENCIES.md` for execution order and dependency graph
- See `tasks/SUBAGENT-GUIDE.md` for using subagents to complete tasks

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
