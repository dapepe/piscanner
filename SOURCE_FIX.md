# Scanner Source Name Fix

## Problem
Scanner was failing with error:
```
scanimage: setting of option --source failed (Invalid argument)
```

## Root Cause
The Canon DR-F120 scanner uses specific source names:
- `Flatbed` - Flatbed scanner
- `ADF Front` - Automatic Document Feeder (single-sided)
- `ADF Duplex` - Automatic Document Feeder (double-sided)

The code was passing generic names like `ADF` which the scanner didn't recognize.

## Solution
Added source name mapping in `scanner.py`:

1. **New `_map_source_name()` method**: Queries the scanner for available sources and maps generic names to scanner-specific names:
   - `ADF` → `ADF Duplex` (or `ADF Front` if Duplex not available)
   - `Flatbed` → `Flatbed`
   - `Auto` → Automatically detects which source to use

2. **Updated `_determine_source()` method**: Now calls `_map_source_name()` to ensure correct source names are used.

3. **Updated CLI**: Removed strict `choices` restriction to allow scanner-specific names to be passed directly.

## Usage

### Generic Names (Recommended)
```bash
# Use ADF (will map to "ADF Duplex")
piscan scan --source ADF

# Use Flatbed
piscan scan --source Flatbed

# Auto-detect based on paper presence
piscan scan --source Auto
```

### Scanner-Specific Names (Advanced)
```bash
# Explicitly use ADF Duplex
piscan scan --source "ADF Duplex"

# Explicitly use ADF Front (single-sided)
piscan scan --source "ADF Front"
```

## How It Works

1. When a source is specified, the scanner queries available sources:
   ```
   scanimage -d canon_dr:libusb:001:003 -A
   ```

2. Parses the output to find available sources:
   ```
   --source Flatbed|ADF Front|ADF Duplex [Flatbed]
   ```

3. Maps the generic name to the appropriate scanner-specific name:
   - `ADF` → Prefers `ADF Duplex`, falls back to `ADF Front`
   - `Flatbed` → Exact match to `Flatbed`

4. Uses the mapped name in the scanimage command.

## Testing

Test the mapping with debug output:
```bash
piscan scan --source Auto --format jpeg --debug
```

You should see in the debug output:
```
DEBUG - Available sources: ['Flatbed', 'ADF Front', 'ADF Duplex']
INFO - Starting scan with source: ADF Duplex
```

## Files Modified

- **piscan/scanner.py**
  - Added `_map_source_name()` method
  - Updated `_determine_source()` to use source mapping
  
- **piscan/cli.py**
  - Updated `--source` argument to accept any string (not just predefined choices)
  - Updated help text to document both generic and scanner-specific names

## Supported Scanners

This approach should work with any SANE-compatible scanner. The code automatically detects available sources and maps generic names appropriately.

For other scanner models, you may see different source names like:
- `ADF`, `Flatbed`
- `Document Feeder`, `Platen`
- `Automatic Document Feeder`, `Scanner Glass`

The mapping function will adapt to whatever the scanner reports.
