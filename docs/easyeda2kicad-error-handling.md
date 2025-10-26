# easyeda2kicad Error Handling

This document describes how easyeda2kicad handles errors and missing files, based on testing and source code analysis.

## Test Results

### Scenario 1: Invalid LCSC ID

**Command**: `easyeda2kicad --full --lcsc_id=C999999999`

**Result**:
- Exit code: `1`
- Error message: `[ERROR] Failed to fetch data from EasyEDA API for part C999999999`
- Files created: None
- Directories: Created but empty

**Conclusion**: When a component doesn't exist in the EasyEDA database, the tool exits with error code 1.

### Scenario 2: Valid Component with Complete Data

**Command**: `easyeda2kicad --full --lcsc_id=C1525`

**Result**:
- Exit code: `0`
- Files created:
  - ✅ Symbol: `easyeda2kicad.kicad_sym`
  - ✅ Footprint: `easyeda2kicad.pretty/C0402.kicad_mod`
  - ✅ 3D Models: `easyeda2kicad.3dshapes/C0402_L1.0-W0.5-H0.6.step` and `.wrl`

**Conclusion**: When all files are available, the tool succeeds with exit code 0.

### Scenario 3: Partial Download (Symbol Only)

**Command**: `easyeda2kicad --symbol --lcsc_id=C17414`

**Result**:
- Exit code: `0`
- Files created:
  - ✅ Symbol: `test.kicad_sym`
  - ❌ Footprint: Directory created but empty
  - ❌ 3D Model: Directory created but empty

**Conclusion**: When using specific flags (--symbol, --footprint, --3d), only requested files are downloaded. Directories are always created.

## Source Code Analysis

Based on review of the easyeda2kicad source code:

### API Data Fetch

```python
if not cad_data:
    logging.error(f"Failed to fetch data from EasyEDA API for part {component_id}")
    return 1
```

If the EasyEDA API returns **no data at all**, the program exits with code 1.

### Partial Data Handling

**CRITICAL FINDING**: The code does **not** validate whether all requested assets were successfully created before returning success.

Each section processes independently:
```python
if arguments["symbol"]:
    # Process symbol
if arguments["footprint"]:
    # Process footprint
if arguments["3d"]:
    # Process 3D model
```

If the API returns partial data (e.g., symbol and footprint but no 3D model), the tool may:
1. Exit with code 0 (success) despite missing files
2. Throw exceptions during processing (depending on data structure)
3. Create empty directories without files

**The tool does NOT guarantee that exit code 0 means all requested files were created.**

## Implications for JLC Has It

### We CANNOT rely on exit code alone

**Bad approach**:
```python
result = subprocess.run(["easyeda2kicad", "--full", f"--lcsc_id={lcsc_id}"])
if result.returncode == 0:
    return True  # ❌ WRONG: May have missing files
```

**Good approach**:
```python
result = subprocess.run(["easyeda2kicad", "--full", f"--lcsc_id={lcsc_id}"])

if result.returncode != 0:
    return None  # API error or component not found

# Validate all three file types exist
symbol_exists = os.path.exists(symbol_path)
footprint_exists = os.path.exists(footprint_dir) and len(os.listdir(footprint_dir)) > 0
model_exists = os.path.exists(model_dir) and len(os.listdir(model_dir)) > 0

if not (symbol_exists and footprint_exists and model_exists):
    return None  # ❌ Incomplete package

return ComponentLibrary(...)  # ✅ Complete package
```

### Validation Requirements

After running easyeda2kicad with `--full` flag, we MUST validate:

1. **Exit code is 0** (no API error)
2. **Symbol file exists** and is non-empty
3. **Footprint directory exists** and contains at least one `.kicad_mod` file
4. **3D model directory exists** and contains at least one `.step` or `.wrl` file

Only show the component to users if **ALL FOUR conditions** are met.

## Error Scenarios

| Scenario | Exit Code | Symbol | Footprint | 3D Model | Show to User? |
|----------|-----------|--------|-----------|----------|---------------|
| Component not in EasyEDA | 1 | ❌ | ❌ | ❌ | ❌ No |
| Complete package | 0 | ✅ | ✅ | ✅ | ✅ Yes |
| Missing 3D model | 0 | ✅ | ✅ | ❌ | ❌ No |
| Missing footprint | 0 | ✅ | ❌ | ❌ | ❌ No |
| Only symbol available | 0 | ✅ | ❌ | ❌ | ❌ No |

## Recommended Implementation

```python
def download_component_library(lcsc_id: str, output_dir: str) -> Optional[ComponentLibrary]:
    """
    Download complete component package from JLCPCB/EasyEDA.

    Returns ComponentLibrary if all files downloaded successfully, None otherwise.
    """
    output_file = os.path.join(output_dir, "easyeda2kicad.kicad_sym")

    # Run easyeda2kicad
    result = subprocess.run([
        "easyeda2kicad",
        "--full",
        f"--lcsc_id={lcsc_id}",
        f"--output={output_file}"
    ], capture_output=True, text=True)

    # Check for API errors
    if result.returncode != 0:
        logging.error(f"easyeda2kicad failed for {lcsc_id}: {result.stderr}")
        return None

    # Validate all three file types exist
    symbol_file = output_file
    footprint_dir = os.path.join(output_dir, "easyeda2kicad.pretty")
    model_dir = os.path.join(output_dir, "easyeda2kicad.3dshapes")

    # Check symbol exists and is non-empty
    if not os.path.exists(symbol_file) or os.path.getsize(symbol_file) == 0:
        logging.warning(f"Symbol file missing or empty for {lcsc_id}")
        return None

    # Check footprint directory has files
    if not os.path.exists(footprint_dir) or not os.listdir(footprint_dir):
        logging.warning(f"Footprint files missing for {lcsc_id}")
        return None

    # Check 3D model directory has files
    if not os.path.exists(model_dir):
        logging.warning(f"3D model directory missing for {lcsc_id}")
        return None

    model_files = [f for f in os.listdir(model_dir)
                   if f.endswith('.step') or f.endswith('.wrl')]
    if not model_files:
        logging.warning(f"3D model files missing for {lcsc_id}")
        return None

    # All validations passed
    return ComponentLibrary(
        symbol_path=symbol_file,
        footprint_path=footprint_dir,
        model_path=model_dir,
        lcsc_id=lcsc_id
    )
```

## Summary

1. **Exit code 1**: Component not found or API error → Do not show to user
2. **Exit code 0**: May or may not have complete files → **MUST VALIDATE FILES**
3. **Always validate** that symbol, footprint, and 3D model files exist
4. **Only show components** with complete packages (all three file types)
5. **Never rely on exit code alone** to determine success

This validation strategy ensures we meet the critical requirement: "Only show parts to users if complete package is available."
