# Fixes Summary

## Fixed Issues

### 1. Scanner Device from Config ✅
- Removed auto-discovery
- Scanner now always uses `scanner.device` from config.yaml
- No more USB device number mismatches
- Set your device in config: `scanner.device: "canon_dr:libusb:001:003"`

### 2. Debug Output Control ✅ (Mostly)
- Added `--debug` flag to scan command
- Without `--debug`: Only shows essential output (banner, results)
- With `--debug`: Shows all INFO, DEBUG, WARNING messages
- Suppressed INFO messages from fallback loggers

## Configuration

### config.yaml Settings
```yaml
scanner:
  device: "canon_dr:libusb:001:003"  # Your scanner device (required)
  source: "ADF Duplex"               # Default source
  resolution: 300
  mode: "Color"
  format: "jpeg"

api:
  workspace: "difo"
  url: "https://scan.haider.vc"
  token: "your-token-here"
```

## Usage

### Normal Scanning (Clean Output)
```bash
piscan scan --source "ADF Duplex" --format jpeg
```

Output:
```
=== Starting Scan Job ===
Scanner: canon_dr:libusb:001:003
Source: ADF Duplex
...

=== Scan Successful ===
Pages scanned: 3
Document ID: 2024-12-10-17:00-A4F2E
```

### Debug Mode (Verbose Output)
```bash
piscan scan --source "ADF Duplex" --format jpeg --debug
```

Shows all internal logging and operations.

## Known Issues

### Source Mapping Bug
There's still an issue where "ADF Duplex" is not being recognized and falls back to "Flatbed". This needs further investigation in the `_map_source_name()` function in scanner.py.

**Workaround:** Use the exact scanner-specific names:
- Check available sources: `scanimage -d your-device -A | grep source`
- For Canon DR-F120: Use `"ADF Duplex"`, `"ADF Front"`, or `"Flatbed"`

### Error Messages Before Banner
Some error messages still appear before the "=== Starting Scan Job ===" banner. These are from the Python logging module during initialization. They should ideally be suppressed in non-debug mode.

## Files Modified

1. **piscan/scanner.py**
   - Removed auto-discovery
   - Added silent fallback logger
   - Uses config device only

2. **piscan/uploader.py**
   - Added silent fallback logger

3. **piscan/file_manager.py**
   - Added silent fallback logger

4. **piscan/blank_detector.py**
   - Added silent fallback logger

5. **piscan/cli.py**
   - Added `--debug` flag handling
   - Sets PISCAN_DEBUG environment variable
   - Disables console logging in non-debug mode

6. **config/config.yaml**
   - Set device to "canon_dr:libusb:001:003"
   - Configured API settings

## Testing

### Check Scanner Device
```bash
scanimage -L
```

### Test Scan (requires paper in ADF)
```bash
# Normal mode
piscan scan --source "ADF Duplex" --format jpeg

# Debug mode
piscan scan --source "ADF Duplex" --format jpeg --debug
```

### Check Configuration
```bash
grep "device:" config/config.yaml
grep "url:" config/config.yaml
```

## Next Steps

1. Fix source mapping to properly recognize "ADF Duplex"
2. Suppress error messages that appear before banner in non-debug mode
3. Test actual scanning with paper loaded
