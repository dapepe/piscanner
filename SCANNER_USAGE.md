# Canon DR-F120 Scanner Usage Guide

## Important: Document Feeder Scanner

The Canon DR-F120 is primarily a **document feeder scanner**. To scan documents:

1. **Load paper into the ADF (Automatic Document Feeder)**
2. Use the ADF source in your scan command

## Quick Start

### Scanning Documents from ADF

```bash
# Load paper into the document feeder, then run:
piscan scan --source "ADF Duplex" --format jpeg
```

This will:
- Scan both sides of the paper (duplex)
- Save as JPEG format
- Upload to your API automatically
- Stop when paper runs out

### Single-Sided Scanning

```bash
piscan scan --source "ADF Front" --format jpeg
```

## Available Sources

The Canon DR-F120 supports these sources:

| Source | Description | Use Case |
|--------|-------------|----------|
| `ADF Duplex` | Scan both sides of paper | Multi-page documents, automatic duplex |
| `ADF Front` | Scan front side only | Single-sided documents |
| `Flatbed` | Limited/no support | May not work on DR-F120 |

### Recommended: ADF Duplex

For most document scanning, use `ADF Duplex`:
```bash
piscan scan --source "ADF Duplex" --format jpeg
```

## Common Usage Patterns

### Scan Multiple Pages

```bash
# Load multiple pages into the feeder
piscan scan --source "ADF Duplex" --format jpeg
```

The scanner will automatically:
- Scan all pages in the feeder
- Stop when paper runs out
- Number pages sequentially (page_001.jpg, page_002.jpg, etc.)

### Scan Without Upload (Local Only)

```bash
piscan scan --source "ADF Duplex" --format jpeg --no-upload --keep-files
```

Files will be saved to `/tmp/YYYY-MM-DD-HHMMSS/`

### Different Resolutions

```bash
# Standard quality (300 DPI)
piscan scan --source "ADF Duplex" --format jpeg --resolution 300

# High quality (600 DPI) - larger files
piscan scan --source "ADF Duplex" --format jpeg --resolution 600

# Draft quality (100 DPI) - faster
piscan scan --source "ADF Duplex" --format jpeg --resolution 100
```

### Different Color Modes

```bash
# Full color (default)
piscan scan --source "ADF Duplex" --format jpeg --mode Color

# Grayscale (smaller files)
piscan scan --source "ADF Duplex" --format jpeg --mode Gray

# Black and white (smallest files)
piscan scan --source "ADF Duplex" --format jpeg --mode Lineart
```

## Error Messages

### "No paper in document feeder"

**Cause:** No paper loaded in the ADF

**Solution:** Load paper into the document feeder and try again

### "Document feeder out of documents"

**Cause:** Scanner finished scanning all pages

**Solution:** This is normal! The scan completed successfully. Check the output for scanned pages.

### "No pages were scanned"

**Cause:** Scanner completed but found no output files

**Possible Reasons:**
1. No paper was loaded in the feeder
2. Paper jam or feed error
3. Scanner hardware issue

**Solution:**
1. Check paper is properly loaded
2. Check for paper jams
3. Try scanning with `--debug` to see detailed output

## Troubleshooting

### Check Scanner Status

```bash
piscan info
```

This shows:
- Scanner device name
- Available sources
- Supported resolutions
- Color modes

### Test Scanner Connection

```bash
scanimage -L
```

Should show:
```
device `canon_dr:libusb:001:003' is a CANON Canon DR-F120 sheetfed scanner
```

### Detailed Debugging

```bash
piscan scan --source "ADF Duplex" --format jpeg --debug
```

Shows:
- Exact scanimage command being run
- Scanner detection process
- File scanning results
- Any error messages

### Manual Test

Test the scanner directly with scanimage:

```bash
# Create test directory
mkdir -p /tmp/test-scan
cd /tmp/test-scan

# Load paper into feeder, then scan:
scanimage -d canon_dr:libusb:001:003 \
  --resolution 300 \
  --mode Color \
  --source "ADF Duplex" \
  --format=jpeg \
  --batch=page_%03d.jpg

# Check results
ls -lh *.jpg
```

## Best Practices

### For Document Scanning

```bash
piscan scan --source "ADF Duplex" --format jpeg --resolution 300
```

- Uses duplex (both sides)
- JPEG format (smaller, faster uploads)
- 300 DPI (good quality/size balance)

### For Archival Quality

```bash
piscan scan --source "ADF Duplex" --format tiff --resolution 600 --no-skip-blank
```

- Uses TIFF (lossless)
- 600 DPI (high quality)
- Keeps blank pages

### For Quick Drafts

```bash
piscan scan --source "ADF Front" --format jpeg --resolution 100 --mode Gray
```

- Single-sided
- Low resolution
- Grayscale (fast)

## Configuration

Edit `config/config.yaml` to set defaults:

```yaml
scanner:
  source: "ADF Duplex"  # Default source
  resolution: 300        # Default DPI
  mode: "Color"         # Default color mode
  format: "jpeg"        # Default format
```

Then you can simply run:
```bash
piscan scan
```

## Summary

The Canon DR-F120 is designed for document feeding:

✅ **DO:** Load paper into the ADF before scanning  
✅ **DO:** Use `ADF Duplex` for most documents  
✅ **DO:** Use JPEG format for uploads  

❌ **DON'T:** Try to use Flatbed (limited support)  
❌ **DON'T:** Start scan without paper loaded  

**Simple workflow:**
1. Load paper into document feeder
2. Run: `piscan scan --source "ADF Duplex" --format jpeg`
3. Wait for scan to complete
4. Documents uploaded automatically!
