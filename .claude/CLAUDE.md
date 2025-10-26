# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**JLC Has It** is a tool for hobbyist electronics designers using KiCad 9.0 to quickly find and add JLCPCB components to their projects.

### Problem Statement

Finding suitable components is time-consuming. Components must meet all these criteria:
- In stock at JLCPCB (preferably "basic" parts, preferably SMD)
- Well-known, commonly used, relatively inexpensive
- Has a KiCad symbol available (from JLCPCB or community libraries like Ultralibrarian)
- Has a 3D CAD model (preferably STEP format)

### Solution

Natural language interface to search for components (e.g., "find me a 50v rated 220uF SMD capacitor"), then automatically download symbol, footprint, and 3D model into a project-specific KiCad library.

## Architecture

### Phased Approach

**Phase 1** (MVP): Core library + CLI tool
- Python-based (easier KiCad integration than Ruby)
- Filesystem-only (no database initially)
- Standalone tool that writes to KiCad project libraries

**Phase 2** (Optional): Add SQLite cache
- Cache JLCPCB component metadata for faster searches
- Track download history
- Enable offline searching

**Phase 3** (Future): KiCad Action Plugin
- Wrap core library in KiCad plugin
- Add menu item inside KiCad
- Insert components directly into open schematics

### Core Components

```
jlc_has_it/
├── core/                      # Core business logic
│   ├── search.py             # Component search logic
│   ├── jlcpcb_client.py      # JLCPCB API/scraping
│   ├── library_sources.py    # Ultralibrarian, SnapEDA integration
│   └── nlp.py                # Natural language query parsing (LLM)
├── kicad/                     # KiCad file format handling
│   ├── symbol.py             # .kicad_sym generation
│   ├── footprint.py          # .kicad_mod generation
│   └── models.py             # .step/.wrl handling
├── cli/                       # CLI interface
│   └── main.py               # Command-line tool
└── plugin/                    # Future: KiCad Action Plugin
    └── jlc_has_it_action.py
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

- **JLCPCB**: Parts catalog API or web scraping for inventory, specs, pricing
- **Component Libraries**: Ultralibrarian, SnapEDA, Component Search Engine
- **LLM Integration**: Parse natural language queries into structured component requirements
- **KiCad Library Format**: Generate valid S-expression files

### Key Workflows

1. **Component Search**:
   - Parse natural language query → extract specs (voltage, capacitance, package type)
   - Query JLCPCB for matching parts
   - Filter by availability (basic > extended), stock status, price
   - Present ranked results to user

2. **Library Addition**:
   - User selects component from search results
   - Download symbol from library source (or generate generic if unavailable)
   - Download footprint and 3D model
   - Append to project's `.kicad_sym` file
   - Add footprint to `footprints.pretty/` directory
   - Add 3D model to `3d_models/` directory
   - Update library table if needed

3. **KiCad Refresh** (Phase 1):
   - If KiCad is open: user must manually refresh libraries or reopen project
   - If KiCad is closed: parts available on next open

## Git Workflow

**Note**: This project uses different git conventions than the global CLAUDE.md (which is Rails-specific).

### Commit Authorship

- When Claude makes commits autonomously, use `--author="Claude Code <noreply@anthropic.com>"`
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

**CLI & UI:**
- `typer` or `click` - CLI framework (Typer is more modern)
- `rich` - Terminal formatting, tables, progress bars
- `questionary` or `InquirerPy` - Interactive prompts

**HTTP & APIs:**
- `requests` or `httpx` - HTTP client for JLCPCB/library sources
- `beautifulsoup4` - Web scraping if needed

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

# Run CLI tool
jlc-has-it search "50v 220uF SMD capacitor"

# Run tests
pytest

# Format code
black .
ruff check .

# Type checking
mypy jlc_has_it/
```

## Development Notes

### Component Data Model

Components should be represented using dataclasses with type hints:

```python
@dataclass
class Component:
    part_number: str          # JLCPCB part number (e.g., "C12345")
    description: str
    manufacturer: str
    category: str            # Resistor, Capacitor, IC, etc.
    is_basic: bool           # Basic vs Extended part
    stock_qty: int
    price: Decimal
    specs: ComponentSpecs    # Electrical specifications
    datasheet_url: str | None

@dataclass
class ComponentSpecs:
    # Component-type specific fields
    voltage: str | None       # e.g., "50V"
    capacitance: str | None   # e.g., "220uF"
    resistance: str | None    # e.g., "10kΩ"
    package: str | None       # e.g., "0805", "SOT-23"
    # ... other specs
```

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
