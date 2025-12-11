# Manual Scanning Usage

This document describes how to use the manual scanning feature to scan documents and upload them to the remote API.

## Configuration

Before using the scan command, configure your API settings in `config/config.yaml`:

```yaml
api:
  workspace: "difo"  # Your workspace name
  url: "https://scan.haider.vc"  # API base URL
  token: "your-api-token-here"  # Your Bearer token
  timeout: 60  # Request timeout in seconds
```

## Basic Usage

### Scan and Upload (Default)

Scan documents using the default settings from your config file:

```bash
piscan scan
```

This will:
1. Scan pages using your configured scanner
2. Detect and skip blank pages (if enabled)
3. Upload all scanned pages to the API
4. Clean up temporary files

### Scan Without Upload

To scan documents locally without uploading:

```bash
piscan scan --no-upload --keep-files
```

This saves the scanned files to `/tmp/scan_YYYYMMDD_HHMMSS/` and displays the path.

## Command Line Options

### Source Selection

Specify which scanner source to use:

```bash
# Use Automatic Document Feeder
piscan scan --source ADF

# Use Flatbed scanner
piscan scan --source Flatbed

# Auto-detect (tries ADF first, falls back to Flatbed)
piscan scan --source Auto
```

### Resolution and Quality

Override the default scan resolution:

```bash
# Scan at 300 DPI (good balance of quality/size)
piscan scan --resolution 300

# High quality scan at 600 DPI
piscan scan --resolution 600
```

### Color Mode

Choose the color mode:

```bash
# Full color
piscan scan --mode Color

# Grayscale
piscan scan --mode Gray

# Black and white
piscan scan --mode Lineart
```

### Output Format

Specify the output file format:

```bash
# PNG format (lossless, larger files)
piscan scan --format png

# JPEG format (compressed, smaller files, recommended for uploads)
piscan scan --format jpeg

# TIFF format (high quality, largest files)
piscan scan --format tiff
```

### Blank Page Detection

Control blank page detection:

```bash
# Include all pages, even blank ones
piscan scan --no-skip-blank

# Skip blank pages (default)
piscan scan
```

### File Management

Keep scanned files after upload:

```bash
# Keep files in /tmp after upload
piscan scan --keep-files

# Delete files after successful upload (default)
piscan scan
```

## Example Commands

### Quick Color Scan from ADF

```bash
piscan scan --source ADF --format jpeg
```

### High Quality Document Scan

```bash
piscan scan --source ADF --resolution 600 --mode Color --format png
```

### Scan Locally Without Upload

```bash
piscan scan --no-upload --keep-files --source Flatbed
```

### Scan Everything Including Blanks

```bash
piscan scan --no-skip-blank --source ADF
```

## API Upload

When uploading to the API, the command constructs the following endpoint:

```
{url}/{workspace}/api/document/
```

For example:
```
https://scan.haider.vc/difo/api/document/
```

The scanned files are uploaded as multipart form data with the field name `files`:

```bash
curl -X POST "https://scan.haider.vc/difo/api/document/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@page_001.jpg" \
  -F "files=@page_002.jpg" \
  -F "files=@page_003.jpg"
```

## Output

The command provides detailed output:

```
=== Starting Scan Job ===
Scanner: auto-detect
Source: ADF
Resolution: 300 DPI
Mode: Color
Format: jpeg
Skip blank pages: true
API URL: https://scan.haider.vc/difo/api/document/
API Token: ********************...c8ec3fbf

Starting scan...

=== Scan Successful ===
Pages scanned: 3
Duration: 12.5s
Document ID: 2024-12-10-14:35-A4F2E
Uploaded to: https://scan.haider.vc
```

## Troubleshooting

### Scanner Not Found

If you get "No scanner device found", try:

```bash
# List available scanners
scanimage -L

# Specify device explicitly in config.yaml
scanner:
  device: "canon_dr:libusb:001:002"
```

### Upload Failed

Check your API configuration:

```bash
# Verify API token is set
grep token config/config.yaml

# Test connection manually
curl -H "Authorization: Bearer YOUR_TOKEN" https://scan.haider.vc/difo/api/document/
```

### Permission Denied

Ensure your user has access to the scanner:

```bash
# Add user to scanner group
sudo usermod -a -G scanner $USER

# Or add to lp group
sudo usermod -a -G lp $USER

# Logout and login for changes to take effect
```

## See Also

- `piscan --help` - View all available commands
- `piscan scan --help` - View scan command options
- `piscan info` - Display scanner information
- `piscan test-scan` - Run a test scan with more options
