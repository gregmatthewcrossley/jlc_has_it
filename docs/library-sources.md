# Component Library Sources

This document describes sources for KiCad symbols, footprints, and 3D models, with a focus on programmatic access capabilities.

## Overview

Our strategy is:
1. **PRIMARY**: JLCPCB/EasyEDA via easyeda2kicad.py (tested and working)
2. **FALLBACK**: Other sources if JLCPCB lacks files
3. **CRITICAL**: Only show parts to users if complete package (symbol + footprint + 3D model) is available

## Primary Source: JLCPCB/EasyEDA

### easyeda2kicad.py

**Status**: ✅ TESTED AND WORKING

**Access Method**: Python package via pip
- **Installation**: `pip install easyeda2kicad`
- **GitHub**: https://github.com/uPesy/easyeda2kicad.py
- **PyPI**: https://pypi.org/project/easyeda2kicad/

**Usage**:
```bash
easyeda2kicad --full --lcsc_id=C1525 --output /path/to/output.kicad_sym
```

**Output**:
- Symbol: `easyeda2kicad.kicad_sym` (KiCad symbol library)
- Footprint: `easyeda2kicad.pretty/{footprint}.kicad_mod`
- 3D Models: `easyeda2kicad.3dshapes/{model}.step` and `.wrl`

**Advantages**:
- ✅ Direct integration with JLCPCB/EasyEDA component database
- ✅ No authentication required
- ✅ Complete packages (symbol + footprint + 3D model)
- ✅ Already tested and verified working
- ✅ Python library available for programmatic use
- ✅ Can be invoked via subprocess or imported as library

**Integration Strategy**:
```python
import subprocess
import os

def download_from_easyeda(lcsc_id: str, output_dir: str) -> Optional[ComponentLibrary]:
    """
    Download component from JLCPCB/EasyEDA using easyeda2kicad.

    Returns ComponentLibrary with file paths if successful, None otherwise.
    """
    output_file = os.path.join(output_dir, "easyeda2kicad.kicad_sym")

    result = subprocess.run([
        "easyeda2kicad",
        "--full",
        f"--lcsc_id={lcsc_id}",
        f"--output={output_file}"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        return None

    # Validate all three files exist
    symbol_file = output_file
    footprint_dir = os.path.join(output_dir, "easyeda2kicad.pretty")
    model_dir = os.path.join(output_dir, "easyeda2kicad.3dshapes")

    if not os.path.exists(symbol_file):
        return None
    if not os.path.exists(footprint_dir) or not os.listdir(footprint_dir):
        return None
    if not os.path.exists(model_dir) or not os.listdir(model_dir):
        return None

    return ComponentLibrary(
        symbol_path=symbol_file,
        footprint_path=footprint_dir,
        model_path=model_dir
    )
```

## Fallback Sources

### Ultra Librarian

**Status**: ❌ NO PUBLIC API

**Website**: https://www.ultralibrarian.com

**Access Methods**:
- **Web Interface**: Manual downloads only
- **CAD Integrations**: Available for OrCAD, eCADSTAR, Quadcept (NOT KiCad)
- **Nexar API**: Integration via Altium Nexar platform (Altium Designer only)

**Content**:
- ✅ Symbols
- ✅ Footprints
- ✅ 3D Models
- ✅ Supports KiCad format (via web export)
- ✅ 14+ million components

**Challenges**:
- ❌ No public API for programmatic access
- ❌ No KiCad plugin or direct integration
- ❌ Manual download required from website
- ❌ Would require web scraping (likely violates ToS)

**Recommendation**:
- Not suitable for automated fallback
- Requires manual intervention or web scraping (not recommended)

## User Workflow

### Phase 1 Approach: Conversational MCP Interface

Since easyeda2kicad does not provide a "check existence" API, we download and validate libraries for top candidates before showing results to the user. The user interacts through a **conversational interface with Claude** via local MCP server.

#### Complete Workflow

1. **Conversational Query** (User talks to Claude):
   - User: "I need a through-hole capacitor rated for 50V and 220uF"
   - Claude understands intent natively (no external API calls needed)
   - Claude calls MCP `search_components` tool with structured parameters
   - Parameters: `{component_type: "capacitor", voltage_min: 50, capacitance: 220, capacitance_unit: "uF", package: "through-hole"}`

2. **Database Query** (MCP server):
   - Query jlcparts SQLite database with extracted parameters
   - Apply filters: in stock, basic parts preferred
   - Rank by score (basic parts, stock level, price)
   - Select top N candidates (e.g., N=20)

3. **Parallel Library Download** (key step):
   - Download libraries for all N candidates **in parallel** using easyeda2kicad
   - Use Python's `concurrent.futures` or `asyncio` for parallelism
   - Each download: `easyeda2kicad --full --lcsc_id={part_number}`
   - Timeout per download: 30 seconds

4. **Validation and Filtering**:
   - Validate each download:
     - ✅ Exit code is 0 (no API error)
     - ✅ Symbol file exists and is non-empty
     - ✅ Footprint directory has `.kicad_mod` file(s)
     - ✅ 3D model directory has `.step` or `.wrl` file(s)
   - **Discard parts with incomplete packages**
   - Cache validated libraries in temp directory

5. **Claude Presents Results Conversationally**:
   - MCP returns **only** parts that passed validation to Claude
   - Claude formats results with context:
     ```
     "I found 12 parts with complete KiCad libraries.

      Top options:
      1. C12345 - 220uF 50V Electrolytic | Stock: 5000 | $0.15
      2. C23456 - 220uF 63V Ceramic X7R  | Stock: 3000 | $0.45

      For power supply filtering, the electrolytic is typical.
      Want me to add it to your project?"
     ```
   - If 0 results → Claude suggests relaxing criteria

6. **Conversational Decision**:
   - User can ask: "What's the difference between them?"
   - Claude explains tradeoffs using component knowledge
   - User can refine: "Show me only ceramic ones"
   - Claude calls search again with refined params

7. **User Selection & Integration**:
   - User: "Add C12345 to my project"
   - Claude calls MCP `add_to_project` tool
   - MCP server:
     - Libraries already downloaded and validated
     - Appends symbol to project `.kicad_sym`
     - Copies footprint to `footprints.pretty/`
     - Copies 3D models to `3d_models/`
     - Updates library tables
   - Claude confirms: "Added C12345. Refresh KiCad to use it."

8. **User Refreshes KiCad**:
   - User manually refreshes libraries in KiCad
   - Component now available for use in schematic

#### Why This Approach?

**Advantages**:
- ✅ **Conversational interface** - ask questions, get advice, refine search
- ✅ **Context retention** - Claude remembers previous queries
- ✅ **Expert guidance** - Claude explains component tradeoffs
- ✅ User only sees parts they can actually use
- ✅ No frustrating "library not available" errors
- ✅ Parallel downloads are fast (20 parts in ~5-10 seconds)
- ✅ Natural workflow - no CLI syntax to memorize

**Trade-offs**:
- ⏱️ Small delay before showing results (5-10 seconds for 20 parts)
- 💾 Temporary disk usage for cached libraries
- 🌐 Network bandwidth for downloading candidates
- 📱 Requires Claude Code/Desktop running

**Performance Considerations**:
- Download top 20-30 candidates (not 100+)
- Use `concurrent.futures.ThreadPoolExecutor` with max_workers=10
- Show progress bar: "Checking library availability... (15/20)"
- Cache validated libraries in `/tmp/jlc_has_it/cache/`

**See also**: `docs/easyeda2kicad-error-handling.md` for detailed validation logic.

## Implementation Priority

### Phase 1 (MVP)
1. ✅ **Local MCP server**: Primary interface through Claude Code/Desktop
2. ✅ **easyeda2kicad only**: Use JLCPCB/EasyEDA as sole source
3. ✅ **Conversational interface**: User talks to Claude, Claude calls MCP tools
4. ✅ **Parallel download**: Download libraries for top N candidates concurrently
5. ✅ **Validation**: Check all four conditions for each download
6. ✅ **Pre-filtering**: Only show parts with complete, validated libraries
7. ✅ **Optional CLI tool**: Simple standalone CLI for scripting/automation

### Phase 2 (Optional Fallback)
1. **Request SnapEDA API access**: Contact SnapEDA for API credentials
2. **Implement SnapEDA fallback**: If easyeda2kicad fails, try SnapEDA
3. **Investigate Component Search Engine**: Test if KiCad loader is automatable

### Phase 3 (Future)
1. **Community contributions**: Allow users to contribute library sources
2. **Custom library support**: Import from user-provided URLs or files

## Coverage Analysis

Based on our research and testing:

| Source | Components | API | KiCad Support | 3D Models | Verified |
|--------|-----------|-----|---------------|-----------|----------|
| **JLCPCB/EasyEDA** | Millions | ✅ Free | ✅ Native | ✅ Yes | ✅ Tested |
| **Ultra Librarian** | 14M+ | ❌ None | ✅ Export | ✅ Yes | ❌ No API |

## Recommendations

### For Phase 1 (Current)
**Use easyeda2kicad exclusively**. This provides:
- ✅ Zero authentication overhead
- ✅ Proven working implementation
- ✅ Complete packages (symbol + footprint + 3D model)
- ✅ Direct JLCPCB integration (matches our database source)
- ✅ No rate limits or API restrictions

### Critical Requirement
**Always validate complete packages**:
```python
def validate_component_library(lib: ComponentLibrary) -> bool:
    """
    Verify that symbol, footprint, AND 3D model all exist.
    Return False if any file is missing.
    """
    return (
        os.path.exists(lib.symbol_path) and
        os.path.exists(lib.footprint_path) and
        os.path.exists(lib.model_path)
    )
```

**Never show parts to users if any file is missing.**

## Attribution Requirements

### easyeda2kicad
- Project: https://github.com/uPesy/easyeda2kicad.py
- License: AGPLv3 (Copyright uPesy)
- Attribution: Include in documentation and generated files

### JLCPCB/EasyEDA Data
- Source: JLCPCB/EasyEDA component database
- License: JLCPCB terms of use apply
- Attribution: Include LCSC part number in component metadata
