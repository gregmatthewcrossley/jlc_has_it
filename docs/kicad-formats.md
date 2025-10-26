# KiCad File Formats

This document describes KiCad 9.0 file formats for symbols, footprints, and project integration.

## Overview

KiCad uses S-expression format for all component files:
- **`.kicad_sym`**: Symbol library files (can contain multiple symbols)
- **`.kicad_mod`**: Footprint files (one footprint per file)
- **`.kicad_pro`**: Project files
- **`sym-lib-table`**: Symbol library table (maps library names to paths)
- **`fp-lib-table`**: Footprint library table (maps library names to paths)
- **`.step`/`.wrl`**: 3D models (binary formats)

## S-Expression Syntax

Based on Specctra DSN format:

**Rules:**
- Tokens delimited by `(` and `)`
- All tokens lowercase (except values)
- Tokens cannot contain whitespace or special characters (except `_`)
- Strings quoted with `"` and UTF-8 encoded
- Comments start with `;` or `#`

**Example:**
```lisp
(kicad_symbol_lib
  (version 20211014)
  (generator kicad_symbol_editor)
  (symbol "Resistor_SMD"
    (property "Reference" "R")
    (property "Value" "10k")
  )
)
```

## Symbol Library Format (.kicad_sym)

### File Structure

```lisp
(kicad_symbol_lib
  (version YYYYMMDD)           ;; File format version
  (generator PROGRAM_NAME)     ;; Creating program

  (symbol "SYMBOL_NAME"
    (property "Reference" "REF")
    (property "Value" "VALUE")
    (property "Footprint" "FOOTPRINT_PATH")
    (property "Datasheet" "URL")
    (property "Description" "TEXT")
    (property "Manufacturer" "COMPANY")
    (property "MPN" "PART_NUMBER")

    (symbol "SYMBOL_NAME_0_1"    ;; Graphical representation
      (rectangle ...)
      (polyline ...)
      (pin ...)
    )
  )
)
```

### Key Properties

**Standard Properties:**
- `Reference`: Designator prefix (R, C, U, etc.)
- `Value`: Component value (100k, 10uF, etc.)
- `Footprint`: Path to footprint (LibraryName:FootprintName)
- `Datasheet`: URL to datasheet
- `Description`: Component description

**Custom Properties:**
- `Manufacturer`: Manufacturer name
- `MPN`: Manufacturer Part Number
- `LCSC`: JLCPCB part number (custom for our use)

### Annotated Example

```lisp
(kicad_symbol_lib
  (version 20211014)
  (generator jlc_has_it)

  ;; Capacitor symbol from JLCPCB C1525
  (symbol "C1525_10uF_10V_X5R_0603"
    (property "Reference" "C" (id 0) (at 0 2.54 0))
    (property "Value" "10uF" (id 1) (at 0 -2.54 0))
    (property "Footprint" "jlc-footprints:C_0603_1608Metric" (id 2) (at 0 0 0))
    (property "Datasheet" "~" (id 3) (at 0 0 0))
    (property "Description" "10uF ±10% 10V X5R 0603" (id 4) (at 0 0 0))
    (property "Manufacturer" "Samsung" (id 5) (at 0 0 0))
    (property "MPN" "CL10A106KP8NNNC" (id 6) (at 0 0 0))
    (property "LCSC" "C1525" (id 7) (at 0 0 0))

    ;; Graphical symbol (simplified capacitor)
    (symbol "C1525_10uF_10V_X5R_0603_0_1"
      (polyline
        (pts (xy -1.524 -0.508) (xy 1.524 -0.508))
        (stroke (width 0.3302))
      )
      (polyline
        (pts (xy -1.524 0.508) (xy 1.524 0.508))
        (stroke (width 0.3048))
      )
    )

    ;; Symbol pins
    (symbol "C1525_10uF_10V_X5R_0603_1_1"
      (pin passive line (at 0 2.54 270) (length 2.032)
        (name "~" (effects (font (size 1.27 1.27))))
        (number "1" (effects (font (size 1.27 1.27))))
      )
      (pin passive line (at 0 -2.54 90) (length 2.032)
        (name "~" (effects (font (size 1.27 1.27))))
        (number "2" (effects (font (size 1.27 1.27))))
      )
    )
  )
)
```

## Footprint Format (.kicad_mod)

### File Structure

```lisp
(module FOOTPRINT_NAME
  (layer F.Cu)
  (tedit TIMESTAMP)
  (descr "DESCRIPTION")
  (tags "TAGS")
  (attr smd)

  (fp_text reference REF** (at X Y) (layer F.SilkS))
  (fp_text value VALUE (at X Y) (layer F.Fab))

  (fp_line ...)        ;; Silk screen lines
  (fp_circle ...)      ;; Silk screen circles
  (fp_rect ...)        ;; Courtyard rectangle

  (pad NUMBER TYPE SHAPE (at X Y) (size W H) (layers LAYERS))

  (model "PATH_TO_3D_MODEL.step"
    (offset (xyz 0 0 0))
    (scale (xyz 1 1 1))
    (rotate (xyz 0 0 0))
  )
)
```

### Annotated Example

```lisp
(module C_0603_1608Metric
  (layer F.Cu)
  (tedit 5F68FEEE)
  (descr "Capacitor SMD 0603 (1608 Metric)")
  (tags "capacitor")
  (attr smd)

  ;; Reference designator text
  (fp_text reference REF** (at 0 1.43) (layer F.SilkS)
    (effects (font (size 1 1) (thickness 0.15)))
  )

  ;; Value text
  (fp_text value C_0603_1608Metric (at 0 -1.43) (layer F.Fab)
    (effects (font (size 1 1) (thickness 0.15)))
  )

  ;; Fab layer outline
  (fp_line (start -0.8 0.4) (end -0.8 -0.4) (layer F.Fab) (width 0.1))
  (fp_line (start -0.8 -0.4) (end 0.8 -0.4) (layer F.Fab) (width 0.1))
  (fp_line (start 0.8 -0.4) (end 0.8 0.4) (layer F.Fab) (width 0.1))
  (fp_line (start 0.8 0.4) (end -0.8 0.4) (layer F.Fab) (width 0.1))

  ;; Courtyard
  (fp_rect (start -1.48 0.73) (end 1.48 -0.73) (layer F.CrtYd) (width 0.05))

  ;; Pads
  (pad 1 smd roundrect (at -0.7875 0) (size 0.875 0.95)
    (layers F.Cu F.Paste F.Mask) (roundrect_rratio 0.25))
  (pad 2 smd roundrect (at 0.7875 0) (size 0.875 0.95)
    (layers F.Cu F.Paste F.Mask) (roundrect_rratio 0.25))

  ;; 3D model reference
  (model "${KISYS3DMOD}/Capacitor_SMD.3dshapes/C_0603_1608Metric.wrl"
    (offset (xyz 0 0 0))
    (scale (xyz 1 1 1))
    (rotate (xyz 0 0 0))
  )
)
```

## Library Tables

### Symbol Library Table (sym-lib-table)

Located in project root, maps library names to file paths:

```lisp
(sym_lib_table
  (version 7)
  (lib (name "jlc-components")
       (type "KiCad")
       (uri "${KIPRJMOD}/libraries/jlc-components.kicad_sym")
       (options "")
       (descr "JLCPCB components"))
)
```

### Footprint Library Table (fp-lib-table)

```lisp
(fp_lib_table
  (version 7)
  (lib (name "jlc-footprints")
       (type "KiCad")
       (uri "${KIPRJMOD}/libraries/footprints.pretty")
       (options "")
       (descr "JLCPCB footprints"))
)
```

**Important:**
- Use `${KIPRJMOD}` for project-relative paths (portable)
- Footprint libraries must have `.pretty` suffix
- Each library entry needs a unique name

## Integration Workflow

**For our use case (adding JLCPCB components):**

1. Download symbol/footprint/3D model from easyeda2kicad
2. Parse symbol file with kiutils
3. Extract symbol definition
4. Append to `{project}/libraries/jlc-components.kicad_sym`
5. Copy footprint to `{project}/libraries/footprints.pretty/`
6. Copy 3D model to `{project}/libraries/3d_models/`
7. Update library tables if needed
8. User refreshes libraries in KiCad

## Using kiutils Library

### Installation

```bash
pip install kiutils
```

### Reading a Symbol Library

```python
from kiutils.symbol import SymbolLib

# Load symbol library
lib = SymbolLib.from_file("library.kicad_sym")

# Access symbols
for symbol in lib.symbols:
    print(f"Symbol: {symbol.entryName}")
    for prop in symbol.properties:
        print(f"  {prop.key}: {prop.value}")
```

### Writing a Symbol Library

```python
from kiutils.symbol import SymbolLib, Symbol, Property

# Create new library
lib = SymbolLib()
lib.version = "20211014"
lib.generator = "jlc_has_it"

# Create symbol
symbol = Symbol(entryName="C1525_10uF")
symbol.properties = [
    Property(key="Reference", value="C"),
    Property(key="Value", value="10uF"),
    Property(key="LCSC", value="C1525"),
]

# Add to library
lib.symbols.append(symbol)

# Save
lib.to_file("output.kicad_sym")
```

### Reading a Footprint

```python
from kiutils.footprint import Footprint

# Load footprint
fp = Footprint.from_file("C_0603.kicad_mod")

print(f"Footprint: {fp.entryName}")
print(f"Pads: {len(fp.pads)}")
```

### Appending to Existing Library

```python
from kiutils.symbol import SymbolLib

# Load existing library
lib = SymbolLib.from_file("jlc-components.kicad_sym")

# Add new symbol
new_symbol = Symbol(entryName="C12345_220uF")
# ... configure symbol ...

lib.symbols.append(new_symbol)

# Save back
lib.to_file("jlc-components.kicad_sym")
```

## Validation Requirements

**Symbol Validation:**
- Must have `Reference` and `Value` properties
- Must have at least one pin
- `Footprint` property should reference valid footprint
- All properties should be unique by `id` field

**Footprint Validation:**
- Must have at least one pad
- Pad numbers must be unique
- Courtyard layer should exist
- 3D model path should be valid (or use placeholder)

**File Integrity:**
- Valid S-expression syntax
- Proper nesting of tokens
- Matching parentheses
- Valid UTF-8 encoding

## Best Practices

**For JLC Has It:**
1. Use consistent naming: `{LCSC}_{Description}`
2. Always include LCSC property for traceability
3. Use project-relative paths in library tables
4. Back up library files before modifying
5. Validate after each modification
6. Use kiutils for parsing (don't write custom parser)

**File Organization:**
```
my-project/
├── my-project.kicad_pro
├── my-project.kicad_sch
├── sym-lib-table
├── fp-lib-table
└── libraries/
    ├── jlc-components.kicad_sym
    ├── footprints.pretty/
    │   ├── C_0603.kicad_mod
    │   └── R_0402.kicad_mod
    └── 3d_models/
        ├── C_0603.step
        └── R_0402.step
```

## References

- [KiCad Dev Docs - File Formats](https://dev-docs.kicad.org/en/file-formats/)
- [KiCad Dev Docs - Symbol Library Format](https://dev-docs.kicad.org/en/file-formats/sexpr-symbol-lib/)
- [KiCad Dev Docs - Footprint Format](https://dev-docs.kicad.org/en/file-formats/sexpr-footprint/)
- [kiutils Documentation](https://kiutils.readthedocs.io/)
- [kiutils GitHub](https://github.com/mvnmgrx/kiutils)

## Next Steps

1. Install kiutils library
2. Implement symbol reader using kiutils
3. Implement symbol writer/appender using kiutils
4. Implement footprint handler
5. Implement library table updater
