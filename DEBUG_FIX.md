# Debug Output Fix

## Issues Fixed

### 1. Format String Error
**Problem:** Scanner was crashing with error: "not enough arguments for format string"

**Root Cause:** The fallback Logger classes in `scanner.py` and `uploader.py` were using `msg % args` which fails when `args` is an empty tuple.

**Fix:** Updated the fallback loggers to check if args exist before formatting:
```python
def info(self, msg, *args): 
    print(f"INFO: {msg % args if args else msg}")
```

### 2. Debug Output Always Showing
**Problem:** INFO and DEBUG messages were always displayed, cluttering the output.

**Solution:** 
1. Added `--debug` flag to the `scan` command
2. Updated logger to import from the proper logger module
3. Set log level to WARNING by default (hiding INFO/DEBUG)
4. Set log level to DEBUG when `--debug` flag is used

## Usage

### Normal Mode (Clean Output)
```bash
piscan scan --source ADF --format jpeg
```

Output shows only:
- Starting scan message
- Success/failure result
- Summary information

### Debug Mode (Verbose Output)
```bash
piscan scan --source ADF --format jpeg --debug
```

Output shows:
- All INFO messages (scan progress, file creation, etc.)
- All DEBUG messages (detailed operations)
- All ERROR/WARNING messages
- Complete stack traces on errors

## Files Modified

1. **piscan/scanner.py**
   - Fixed format string error in fallback Logger
   - Imported proper Logger from logger module
   
2. **piscan/uploader.py**
   - Fixed format string error in fallback Logger
   - Imported proper Logger from logger module

3. **piscan/cli.py**
   - Added `--debug` flag to scan command
   - Added log level control based on debug flag
   - Sets WARNING level by default
   - Sets DEBUG level when --debug is used

## Testing

Test without debug (should show minimal output):
```bash
piscan scan --source ADF --format jpeg
```

Test with debug (should show all logging):
```bash
piscan scan --source ADF --format jpeg --debug
```
