# Running Tests - Quick Reference

## Prerequisites

Tests require the project dependencies to be installed:

```bash
cd /Users/gregmatthewcrossley/Developer/jlc_has_it

# Install project with dev dependencies (recommended)
pip install -e ".[dev]"

# OR install manually if needed
pip install pytest pytest-cov pytest-mock pytest-timeout
```

**Important**: The `pytest-timeout` plugin is required for timeout protection. It's included in the `[dev]` dependencies.

## Quick Start

```bash
# Change to project directory
cd /Users/gregmatthewcrossley/Developer/jlc_has_it

# Run all tests
pytest tests/ -v

# Run tests with coverage report
pytest tests/ --cov=jlc_has_it --cov-report=html --cov-report=term
```

## Common Commands

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/core/test_search.py -v
pytest tests/mcp/test_tools.py -v
pytest tests/integration/test_end_to_end.py -v
```

### Run Specific Test Class
```bash
pytest tests/core/test_search.py::TestComponentSearch -v
pytest tests/mcp/test_tools.py::TestSearchComponents -v
```

### Run Specific Test Function
```bash
pytest tests/core/test_search.py::TestComponentSearch::test_search_by_category -v
```

### Run Tests Matching Pattern
```bash
pytest tests/ -k "search" -v          # Run all tests with "search" in name
pytest tests/ -k "database" -v        # Run all database tests
pytest tests/ -k "pagination" -v      # Run pagination tests
```

### Run with Coverage Report
```bash
# Generate HTML coverage report
pytest tests/ --cov=jlc_has_it --cov-report=html --cov-report=term

# View HTML report in browser
open htmlcov/index.html
```

### Run Only Fast Tests (Skip Real Database Tests)
```bash
pytest tests/ -v -m "not slow"
```

### Run in Parallel (Faster)
```bash
pip install pytest-xdist
pytest tests/ -n auto
```

### Run with Verbose Output
```bash
pytest tests/ -vv          # Very verbose
pytest tests/ -s           # Show print statements
pytest tests/ -vv -s       # Very verbose + print statements
```

## What Each Test File Covers

| File | Coverage | Tests |
|------|----------|-------|
| `test_models.py` | Data models (Component, PriceTier) | 12 |
| `test_database.py` | Database connection and queries | 17 |
| `test_search.py` | ComponentSearch and QueryParams | 20 |
| `test_project_integration.py` | KiCad project integration | 32 |
| `test_library_downloader.py` | Library downloading | 21 |
| `test_tools.py` | MCP tools (search, compare, add) | 30 |
| `test_fts5_and_pagination.py` | FTS5 indexing and pagination | 18 |
| `test_end_to_end.py` | Full workflows | 15 |
| `test_real_database.py` | Real jlcparts database | 12 |
| **Total** | **All components** | **197+** |

## Test Organization

```
tests/
├── core/
│   ├── test_models.py              # Data models
│   ├── test_database.py            # Database layer
│   ├── test_search.py              # Search engine
│   ├── test_project_integration.py # KiCad integration
│   ├── test_library_downloader.py  # Library downloads
│   └── test_fts5_and_pagination.py # Performance features
├── mcp/
│   └── test_tools.py               # MCP tool implementations
├── integration/
│   ├── test_end_to_end.py          # Complete workflows
│   └── test_real_database.py       # Real database tests
└── conftest.py                     # Fixtures and configuration
```

## Understanding Test Output

```
tests/core/test_search.py::TestComponentSearch::test_search_by_category PASSED
|                         |                   |                         |
|                         |                   |                         +-- Result (PASSED/FAILED)
|                         |                   +-- Test function name
|                         +-- Test class name
+-- Test file path
```

## Debugging Failed Tests

### Get More Details
```bash
pytest tests/core/test_search.py::TestComponentSearch::test_search_by_category -vv
```

### See Print Statements
```bash
pytest tests/core/test_search.py::TestComponentSearch::test_search_by_category -s
```

### Drop into Debugger on Failure
```bash
pytest tests/core/test_search.py::TestComponentSearch::test_search_by_category --pdb
```

## Common Issues

### "pytest: command not found"
```bash
# Install pytest
pip install pytest

# Or with the project
pip install -e .
```

### "ModuleNotFoundError" for jlc_has_it
```bash
# Make sure you're in the project directory
cd /Users/gregmatthewcrossley/Developer/jlc_has_it

# Install in development mode
pip install -e .
```

### Database tests are slow
```bash
# Real database tests take longer. Run only fast tests:
pytest tests/ -m "not slow"

# Or skip real database tests:
pytest tests/ --ignore=tests/integration/test_real_database.py
```

### Network errors in download tests
```bash
# Library download tests require internet. Skip if offline:
pytest tests/ -k "not download"
```

## CI/CD Integration

For automated testing, use this command:

```bash
pytest tests/ -v --tb=short --cov=jlc_has_it --cov-report=xml
```

## Performance Notes

- **Full test suite**: ~30-60 seconds (depends on system and network)
- **Unit tests only**: ~5-10 seconds
- **MCP tests**: ~10-15 seconds
- **Real database tests**: ~20-30 seconds

## Next Steps

If tests fail, check:
1. Is pytest installed? (`pip install pytest`)
2. Is the project installed? (`pip install -e .`)
3. Are you in the correct directory? (`cd /Users/gregmatthewcrossley/Developer/jlc_has_it`)
4. Do you have internet for download tests?
5. Is the jlcparts database available? (~11GB file)
