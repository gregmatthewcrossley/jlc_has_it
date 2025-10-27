# Test Timeout Configuration

## Summary

✅ **All tests have timeout protection configured via `pytest-timeout` plugin.**

## Required Dependency

The timeout feature requires the `pytest-timeout` plugin:

```ini
# In pyproject.toml [project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-timeout>=2.1.0",  # ← Enables timeout functionality
    ...
]
```

**Installation:**
```bash
pip install -e ".[dev]"  # Installs all dev dependencies including pytest-timeout
# OR
pip install pytest-timeout>=2.1.0
```

**Without this plugin**, the `--timeout` option will fail:
```
ERROR: Unknown config option: timeout
```

## Default Timeout

All tests have a **30-second timeout** applied globally:

```ini
# In pyproject.toml
[tool.pytest.ini_options]
addopts = "-v --tb=short --timeout=30"
```

This prevents any test from hanging indefinitely.

## Per-Test Overrides

Some tests that access the database have custom timeout overrides:

### Fast Tests (Use Default 30s)
- Unit tests for models, database queries
- MCP tool tests
- Most integration tests

### Slower Tests (20 seconds)
Database-intensive operations that might take longer:

```python
@pytest.mark.timeout(20)
def test_fts5_table_created_on_connection(self):
    """FTS5 table creation can take longer."""
```

**Tests with 20s timeout:**
- FTS5 full-text search indexing tests
- Pagination tests with large result sets
- Real database queries

### Slow Integration Tests (Marked)
Tests that might take longer are marked for optional skipping:

```python
@pytest.mark.slow
def test_search_with_large_result_set(self):
    """Search across millions of components."""
```

**To skip slow tests:**
```bash
pytest tests/ -m "not slow"
```

## Timeout Values Explained

| Timeout | Usage | Why |
|---------|-------|-----|
| **30s** | Default for all tests | Prevents hangs, catches infinite loops |
| **20s** | Database-heavy tests | FTS5 indexing, large queries can be slower |
| **Marked "slow"** | Large dataset tests | Real JLCPCB database (7M components) |

## Network Timeouts

The library downloader also has its own timeout:

```python
# In jlc_has_it/core/library_downloader.py
TIMEOUT_SECONDS = 30
```

This prevents hanging on network requests to JLCPCB/EasyEDA.

## How Timeouts Work

1. **Global timeout (30s)**: Applied to every test
2. **Per-test override**: Specific tests can use `@pytest.mark.timeout(N)`
3. **Subprocess timeout**: Library downloader uses `subprocess.run(..., timeout=30)`

If a test exceeds its timeout:
```
FAILED tests/core/test_fts5_and_pagination.py::TestFTS5::test_example -
  Timeout of 30 seconds exceeded
```

## Handling Slow Tests

### Option 1: Skip Slow Tests
```bash
pytest tests/ -m "not slow"
```

### Option 2: Run Only Fast Tests
```bash
pytest tests/core/ -m "not integration"
```

### Option 3: Increase Timeout Globally
```bash
pytest tests/ --timeout=60
```

### Option 4: Run Specific Slow Test with Longer Timeout
```bash
pytest tests/integration/test_real_database.py --timeout=120 -v
```

## Why Tests Might Timeout

### Scenario 1: First Time Database Setup
**Symptom**: Test takes 60+ seconds on first run
**Reason**: FTS5 index creation on 7M component database
**Solution**: Expected behavior, only happens once. Run tests again.

### Scenario 2: Network Issues
**Symptom**: Library download tests timeout
**Reason**: Slow internet connection to JLCPCB
**Solution**: Skip download tests: `pytest tests/ -k "not download"`

### Scenario 3: System Under Heavy Load
**Symptom**: Usually fast tests suddenly timeout
**Reason**: System CPU/memory pressure
**Solution**: Close other applications, increase timeout temporarily

### Scenario 4: Infinite Loop (Bug)
**Symptom**: Test consistently times out
**Reason**: Code bug (infinite loop, deadlock, etc.)
**Solution**: Debug with `-s` flag to see print statements: `pytest tests/test_file.py -s -vv`

## Debugging a Timeout

### Step 1: Run with Verbose Output
```bash
pytest tests/path/to/test.py::TestClass::test_name -vv -s
```

### Step 2: Add Debug Output
```python
@pytest.mark.timeout(30)
def test_example(self):
    print("Starting test")  # Will show with -s flag
    # ... test code ...
    print("Completed test")
```

### Step 3: Increase Timeout for Debugging
```bash
pytest tests/path/to/test.py --timeout=120 -vv -s
```

### Step 4: Use Debugger
```bash
pytest tests/path/to/test.py --pdb -s
```

## Database-Specific Timeouts

### First Connection (FTS5 Initialization)
- **Time**: 10-30 seconds (one-time)
- **Reason**: Creating FTS5 virtual table for 7M components
- **When**: Only happens when `enable_fts5=True` and table doesn't exist
- **Subsequent**: <100ms (index already built)

### Query Operations
- **Simple queries**: <1 second
- **Full-text search (FTS5)**: <100ms
- **Large result sets**: 1-5 seconds
- **Pagination**: <100ms per page

## Test Timeout Configuration Summary

| File | Timeout | Notes |
|------|---------|-------|
| `test_models.py` | 30s | Simple dataclass tests |
| `test_database.py` | 30s | Database connection tests |
| `test_search.py` | 30s | Search query tests |
| `test_project_integration.py` | 30s | File I/O tests |
| `test_library_downloader.py` | 30s | Download timeout test mocks |
| `test_tools.py` | 30s | MCP tool tests |
| `test_fts5_and_pagination.py` | 20s | FTS5 and large queries |
| `test_end_to_end.py` | 30s | Integration workflows |
| `test_real_database.py` | 30s | Real database tests |

## Recommended Test Running Strategies

### For CI/CD (Fast, no long operations)
```bash
pytest tests/ -m "not slow" --timeout=30
```

### For Local Development (Normal speed)
```bash
pytest tests/ --timeout=30
```

### For Thorough Testing (Include all tests)
```bash
pytest tests/ --timeout=60
```

### For Debugging (Verbose, no timeout)
```bash
pytest tests/path/to/test.py --timeout=0 -vv -s --pdb
```

## Important Notes

1. **Timeouts are safety features** - They prevent hung tests from blocking CI/CD
2. **First FTS5 test is slow** - Database indexing is a one-time cost
3. **Network tests can be flaky** - Use `-m "not download"` to skip if offline
4. **You can disable timeouts** - Use `--timeout=0`, but not recommended for CI

## Modifying Timeouts

### For a Specific Test
```python
@pytest.mark.timeout(60)  # Override default
def test_slow_operation(self):
    pass
```

### For All Tests in a Class
```python
@pytest.mark.timeout(45)
class TestSlowOperations:
    def test_one(self):
        pass

    def test_two(self):
        pass
```

### Globally in pyproject.toml
```ini
[tool.pytest.ini_options]
addopts = "--timeout=60"
```

## Troubleshooting: "Unknown config option: timeout"

If you get this error:
```
ERROR: Unknown config option: timeout
```

**Solution**: Install the `pytest-timeout` plugin:
```bash
# Option 1: Install with dev dependencies
pip install -e ".[dev]"

# Option 2: Install just the plugin
pip install pytest-timeout
```

Then run tests again:
```bash
pytest tests/ -v
```

## Summary

✅ **All tests are protected against hanging**
- `pytest-timeout` plugin provides timeout functionality
- 30-second default timeout prevents infinite loops
- Database tests have 20-second overrides for FTS5 operations
- Slow tests are marked and can be skipped
- Network operations have their own timeouts
- Complete control over timeout values per test

**Safe to run tests without worrying about hangs.**
