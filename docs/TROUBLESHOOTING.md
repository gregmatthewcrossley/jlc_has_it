# Troubleshooting Guide

## Common Issues and Solutions

### Installation & Setup

#### Problem: "ModuleNotFoundError: No module named 'jlc_has_it'"

**Cause**: Package not installed or virtual environment not activated

**Solution**:
```bash
# Ensure you're in the project directory
cd /path/to/jlc_has_it

# Install in development mode
pip install -e .

# Or with all dependencies
pip install -e ".[dev,cli]"
```

#### Problem: "jlc-has-it-mcp: command not found"

**Cause**: Entry point not installed or virtual environment not active

**Solution**:
```bash
# Reinstall the package
pip install -e .

# Verify installation
which jlc-has-it-mcp

# Or run directly with Python
python3 -m jlc_has_it.mcp
```

#### Problem: Claude Code doesn't see the MCP server

**Cause**: Configuration file missing or incorrect

**Solution**:
1. Check `.claude/mcp_settings.json` exists in your project
2. Verify the file contains:
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
3. Restart Claude Code completely (close and reopen)
4. Check the MCP server status in Claude Code's settings

---

### Database Issues

#### Problem: "Database is missing" when running search

**Cause**: jlcparts database not yet downloaded or corrupted

**Solution**:
```bash
# Let the system auto-download on next search
# Or manually trigger download:
python3 -c "from jlc_has_it.core.database import DatabaseManager; DatabaseManager().update_if_needed()"
```

**Troubleshooting steps**:
```bash
# Check cache directory
ls -lah ~/.cache/jlc_has_it/

# Check file size (should be 100MB+)
ls -lh ~/.cache/jlc_has_it/cache.sqlite3

# Validate the database
python3 -c "
import sqlite3
conn = sqlite3.connect(expanduser('~/.cache/jlc_has_it/cache.sqlite3'))
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM components')
print(f'Total components: {cursor.fetchone()[0]}')
conn.close()
"
```

#### Problem: "7z command not found"

**Cause**: p7zip not installed on system

**Solution**:
```bash
# macOS
brew install p7zip

# Ubuntu/Debian
sudo apt install p7zip-full

# Fedora/RHEL
sudo dnf install p7zip

# Arch
sudo pacman -S p7zip
```

**Verify installation**:
```bash
which 7z
7z --version
```

#### Problem: Database download hangs or is very slow

**Cause**: Network issues or JLCPCB server slow

**Solution**:
```bash
# Check network connection
ping github.com

# Check disk space (database is ~200MB when extracted)
df -h

# Try manual download with timeout
timeout 300 python3 -c "
from jlc_has_it.core.database import DatabaseManager
db = DatabaseManager()
db.download_database()
"

# If this fails, wait and try again later
# Database updates only happen if >1 day old
```

#### Problem: "sqlite3.DatabaseError: database disk image is malformed"

**Cause**: Database file was corrupted (usually incomplete download)

**Solution**:
```bash
# Remove corrupted database
rm ~/.cache/jlc_has_it/cache.sqlite3

# Next search will trigger fresh download
```

---

### Component Search Issues

#### Problem: No components found matching criteria

**Causes**:
1. Search filters too restrictive
2. No components match that exact specification
3. Database not updated with latest components

**Solutions**:

```bash
# Relax filters - try broader search
# Instead of: "100nF 16V 0402 ceramic capacitor"
# Try: "100nF ceramic capacitor"

# Check what categories exist
python3 -c "
from jlc_has_it.core.database import DatabaseManager
import sqlite3

db = DatabaseManager()
conn = db.get_connection()
cursor = conn.cursor()

# Get all categories
cursor.execute('SELECT DISTINCT category FROM components LIMIT 20')
for row in cursor.fetchall():
    print(row[0])
"

# Force database update
rm ~/.cache/jlc_has_it/cache.sqlite3
# Then run any search to trigger fresh download
```

#### Problem: Search returns outdated components

**Cause**: Database is older than 1 day and hasn't auto-refreshed

**Solution**:
```bash
# Force database update
python3 -c "
from jlc_has_it.core.database import DatabaseManager
db = DatabaseManager()
db.download_database()
"

# Check database age
python3 -c "
from jlc_has_it.core.database import DatabaseManager
db = DatabaseManager()
age = db.check_database_age()
if age:
    print(f'Database age: {age.total_seconds() / 3600:.1f} hours')
else:
    print('Database does not exist')
"
```

---

### Library Download Issues

#### Problem: "easyeda2kicad command not found"

**Cause**: easyeda2kicad not installed

**Solution**:
```bash
pip install easyeda2kicad
```

**Verify installation**:
```bash
which easyeda2kicad
easyeda2kicad --help
```

#### Problem: "Failed to download valid library for [LCSC_ID]"

**Causes**:
1. Component doesn't exist at JLCPCB/EasyEDA
2. Component exists but lacks complete library (symbol, footprint, or 3D model)
3. easyeda2kicad encountered an error

**Solutions**:

```bash
# Verify component exists
# Go to: https://lcsc.com/search?q=C1525
# (Replace C1525 with your LCSC ID)

# Try downloading manually to see error details
easyeda2kicad --full --lcsc_id=C1525 --output=/tmp/test.kicad_sym

# Check if library files are complete
ls -la /tmp/test*
ls -la /tmp/test.pretty/*.kicad_mod  # Should have at least one footprint
ls -la /tmp/test.3dshapes/*.step     # Should have at least one 3D model

# Some components may not have complete packages
# Try a similar alternative component
```

#### Problem: Downloaded library has incorrect footprint or 3D model

**Cause**: easyeda2kicad downloaded wrong files or JLCPCB data is incomplete

**Solutions**:

```bash
# Inspect the downloaded files
cd /tmp/jlc_has_it/cache/C1525/

# Check symbol file
cat easyeda2kicad.kicad_sym | head -50

# Check footprint files
ls easyeda2kicad.pretty/

# Check 3D models
ls easyeda2kicad.3dshapes/

# If files look wrong, try alternative component
```

#### Problem: "Timeout" when downloading library

**Cause**: easyeda2kicad request took >30 seconds (network issue or JLCPCB slow)

**Solution**:
```bash
# Try again - may be temporary network hiccup
# Increase timeout in code if this persists:

# Edit jlc_has_it/core/library_downloader.py
# Change TIMEOUT_SECONDS = 30 to TIMEOUT_SECONDS = 60
```

---

### KiCad Project Integration Issues

#### Problem: "No KiCad project found"

**Cause**: Not in a KiCad project directory and no project_path specified

**Solution**:
```bash
# Navigate to your KiCad project directory
cd /path/to/my-kicad-project

# Then ask Claude to add component
# Or specify project path in tool call

# Verify it's a valid KiCad project:
ls *.kicad_pro  # Should see at least one .kicad_pro file
```

#### Problem: "KiCad can't find the added component"

**Cause**: KiCad hasn't refreshed its library cache

**Solution**:
1. **Quick fix**: Restart KiCad completely
2. **Alternative**:
   - Go to Preferences → Manage Symbol Libraries
   - Click "Refresh"
   - The component should now appear

**Verify files were added**:
```bash
cd /path/to/my-kicad-project

# Check symbol library exists
ls -l libraries/jlc-components.kicad_sym

# Check footprints were added
ls libraries/footprints.pretty/

# Check 3D models were added
ls libraries/3d_models/

# Check library tables were updated
cat sym-lib-table
cat fp-lib-table
```

#### Problem: "Bad symbol file" error in KiCad

**Cause**: Symbol file is corrupted or malformed S-expression

**Solution**:
```bash
# Validate the symbol file
python3 -c "
from pathlib import Path
sym_path = Path('libraries/jlc-components.kicad_sym')
with open(sym_path) as f:
    content = f.read()
    if content.startswith('('):
        print('Symbol file looks valid (starts with parenthesis)')
    else:
        print('ERROR: Symbol file does not look like valid S-expression')
        print(content[:200])
"

# If corrupted, remove and re-add component
rm libraries/jlc-components.kicad_sym
# Then ask Claude to add component again
```

#### Problem: Relative paths in library tables aren't working

**Cause**: Paths may be absolute instead of relative

**Solution**:
```bash
# Check library table
cat sym-lib-table
cat fp-lib-table

# They should contain relative paths like:
# (lib (name "jlc-components")(type "KiCad")(uri "libraries/jlc-components.kicad_sym")...))

# If they're absolute paths, manually fix them or re-add component
# Relative paths work better for project portability
```

---

### Performance Issues

#### Problem: Searches are very slow

**Cause**:
1. First search triggers database download (100MB+)
2. Database isn't indexed properly
3. Query is too broad

**Solution**:
```bash
# Check if first search finished
# First search can take several minutes due to 100MB download

# Check database size
ls -lh ~/.cache/jlc_has_it/cache.sqlite3  # Should be 100MB+

# Try more specific search with filters
# Instead of: search all resistors
# Try: search 1k resistors from Samsung
```

#### Problem: Library downloads take too long

**Cause**: Network slow, easyeda2kicad server under load, or timeout too short

**Solution**:
```bash
# Try downloading one component at a time
# Parallel downloads may stress network

# If timeouts occur, edit timeout value:
# Edit jlc_has_it/core/library_downloader.py
# TIMEOUT_SECONDS = 30  # Increase to 60 or 90

# Check your internet speed
# easyeda2kicad needs decent bandwidth
```

---

## Getting Help

### Debug Information to Collect

If you encounter an issue, collect this information:

```bash
# System info
python3 --version
pip --version
which 7z

# Package info
pip show jlc-has-it
pip show easyeda2kicad

# Database info
ls -lah ~/.cache/jlc_has_it/
sqlite3 ~/.cache/jlc_has_it/cache.sqlite3 "SELECT COUNT(*) FROM components;"

# Recent error (if applicable)
# Attach any error messages or tracebacks
```

### Reporting Issues

When reporting issues, include:
1. Error message (full traceback if available)
2. What you were trying to do
3. Steps to reproduce
4. Debug information from above
5. Your OS and Python version

### Useful Links

- **JLCPCB Parts Database**: https://github.com/yaqwsx/jlcparts
- **LCSC Component Search**: https://lcsc.com/
- **easyeda2kicad**: https://github.com/uPesy/easyeda2kicad.py
- **KiCad Documentation**: https://docs.kicad.org/
- **KiCad 9.0 File Formats**: https://docs.kicad.org/en/latest/file_formats/

---

## FAQ

**Q: Does JLC Has It send data to external servers?**

A: No. Everything runs locally. The only external connections are:
- Initial database download from yaqwsx.github.io (read-only)
- Component library downloads from JLCPCB/EasyEDA when you explicitly add a component

**Q: Why is the database so large?**

A: The jlcparts SQLite database contains 250,000+ components with specifications, prices, and attributes. It needs ~100MB when extracted.

**Q: Can I use JLC Has It offline?**

A: Mostly. Searches work entirely offline. Library downloads require internet to fetch from JLCPCB/EasyEDA.

**Q: How often is the database updated?**

A: The local cache is refreshed daily (max 1 day old). The source database at yaqwsx.github.io updates daily at 3AM UTC.

**Q: Does it work with KiCad versions other than 9.0?**

A: Probably, but 9.0 is tested. Library formats have been stable across recent versions. YMMV with much older versions.

**Q: Can I manually delete the database cache?**

A: Yes. Deleting `~/.cache/jlc_has_it/cache.sqlite3` will trigger a fresh download on next search. Safe to do.

