# Scanner Format Option Fix

## Problem
Scanner was failing with error:
```
scanimage: argument without option: `/tmp/2025-12-10-152821/page_%03d.jpeg'
```

## Root Cause
The scanimage command-line syntax requires `--format=jpeg` (with equals sign), not `--format jpeg` (separate arguments).

Additionally, scanimage uses `.jpg` extension for JPEG files, not `.jpeg`.

## Solution
Updated `scanner.py` to:

1. **Use correct option syntax**: Changed from separate arguments to combined format:
   ```python
   # Before:
   '--format', self.config.scanner_format,
   '--batch', batch_pattern
   
   # After:
   f'--format={self.config.scanner_format}',
   f'--batch={batch_pattern}'
   ```

2. **Handle JPEG extension correctly**: Map `jpeg` format to `.jpg` extension:
   ```python
   format_ext = 'jpg' if self.config.scanner_format == 'jpeg' else self.config.scanner_format
   ```

3. **Update file pattern matching**: Use the correct extension when finding scanned files.

## How scanimage Works

When you specify `--format=jpeg`:
- scanimage automatically uses `.jpg` extension in batch mode
- The batch pattern should use `.jpg`, not `.jpeg`
- Output files: `page_001.jpg`, `page_002.jpg`, etc.

When you specify `--format=png`:
- scanimage uses `.png` extension
- Output files: `page_001.png`, `page_002.png`, etc.

## Command Line Examples

### Correct Commands (After Fix)
```bash
# JPEG format
piscan scan --source Flatbed --format jpeg

# PNG format  
piscan scan --source Flatbed --format png

# TIFF format
piscan scan --source Flatbed --format tiff
```

### Generated scanimage Commands
```bash
# JPEG
scanimage -d canon_dr:libusb:001:003 --resolution 300 --mode Color \
  --source Flatbed --format=jpeg --batch=/tmp/scan/page_%03d.jpg

# PNG
scanimage -d canon_dr:libusb:001:003 --resolution 300 --mode Color \
  --source Flatbed --format=png --batch=/tmp/scan/page_%03d.png
```

## Files Modified

**piscan/scanner.py:**
- Changed `--format` and `--batch` to use `=` syntax
- Added extension mapping for JPEG (jpeg → jpg)
- Updated file pattern matching to use correct extensions

## Testing

Test different formats:

```bash
# Test JPEG (most common for document scanning)
piscan scan --source Flatbed --format jpeg --debug

# Test PNG (lossless, larger files)
piscan scan --source Flatbed --format png --debug

# Test TIFF (archival quality)
piscan scan --source Flatbed --format tiff --debug
```

With `--debug`, you'll see the exact scanimage command being executed.

## Recommended Format

For document scanning and API upload, **JPEG is recommended**:
- Smaller file sizes
- Faster uploads
- Good quality for documents
- Widely supported

Example:
```bash
piscan scan --source "ADF Duplex" --format jpeg
```
