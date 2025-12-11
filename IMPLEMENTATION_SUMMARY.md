# Manual Scanning Implementation Summary

## Changes Made

### 1. Configuration Updates

**File: `config/config.yaml`**
- Updated API URL structure to match your endpoint: `https://scan.haider.vc`
- Set workspace to `difo`
- Added your API token
- Increased timeout to 60 seconds for larger uploads

**File: `config/config.example.yaml`**
- Updated with new API URL format
- Added comments explaining the configuration structure

### 2. Uploader Fix

**File: `piscan/uploader.py`**
- Fixed API endpoint URL construction
- Now correctly builds: `{url}/{workspace}/api/document/`
- Example: `https://scan.haider.vc/difo/api/document/`

### 3. CLI Enhancements

**File: `piscan/cli.py`**

#### New `scan` Command
Added a new primary scan command with the following options:
- `--source {Auto,ADF,Flatbed}` - Choose scan source
- `--resolution DPI` - Set scan resolution
- `--mode {Color,Gray,Lineart}` - Set color mode
- `--format {png,jpeg,tiff}` - Set output format
- `--no-skip-blank` - Include blank pages
- `--no-upload` - Scan locally without uploading
- `--keep-files` - Keep scanned files after upload

#### Updated `perform_scan` Method
- Added `upload` parameter to optionally skip API upload
- Added `keep_files` parameter to preserve scanned files
- Returns more detailed results including file paths and upload response

## Usage Examples

### Basic Scan and Upload
```bash
piscan scan
```

### Scan from ADF as JPEG
```bash
piscan scan --source ADF --format jpeg
```

### Scan Locally Without Upload
```bash
piscan scan --no-upload --keep-files
```

### High Quality Scan
```bash
piscan scan --resolution 600 --mode Color --format png
```

## API Integration

The implementation matches your curl examples:

**Single File Upload:**
```bash
curl -X POST "https://scan.haider.vc/difo/api/document/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@scan.pdf"
```

**Multiple Files Upload:**
```bash
curl -X POST "https://scan.haider.vc/difo/api/document/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@scan_Page_1.jpg" \
  -F "files=@scan_Page_2.jpg" \
  -F "files=@scan_Page_3.jpg"
```

The piscan implementation automatically handles multiple files in the same way.

## Configuration Requirements

Edit `config/config.yaml` with your settings:

```yaml
api:
  workspace: "difo"  # Your workspace
  url: "https://scan.haider.vc"  # Your API URL
  token: "YOUR_API_TOKEN_HERE"  # Your Bearer token
  timeout: 60
```

## Testing

You can test the command without a physical scanner using:

```bash
# View help
piscan scan --help

# Test with config (will fail at scanner step if no scanner present)
piscan scan --no-upload --keep-files
```

## Files Modified

1. `config/config.yaml` - API configuration
2. `config/config.example.yaml` - Example configuration
3. `piscan/uploader.py` - API endpoint URL fix
4. `piscan/cli.py` - New scan command and options

## Documentation

Created comprehensive documentation in `SCAN_USAGE.md` covering:
- Configuration setup
- All command line options
- Example commands
- Troubleshooting
