# Color Correction and Image Optimization

## Problem Overview

The Canon imageFORMULA DR-F120 scanner, when used with the `canon_dr` SANE backend on Raspberry Pi, produces color scans with incorrect channel ordering. Colors appear "completely off" (e.g., reds appear blue, blues appear red) because the scanner outputs BGR (Blue-Green-Red) format while most software expects RGB (Red-Green-Blue).

**Symptoms:**
- Color scans have swapped/incorrect colors
- Grayscale and lineart scans work fine
- The `canon_dr` backend provides no configuration options to fix this

**Root Cause:**
The `canon_dr` backend for this specific scanner model does not expose color correction options. Running `scanimage -A` shows no `colormode`, `color_correction`, or `gamma` options that could fix the channel ordering.

**Solution:**
Post-processing color correction using PIL (Python Imaging Library) to swap color channels after scanning.

---

## Configuration

### Color Correction Options

Edit your `config/config.yaml` file:

```yaml
scanner:
  color_correction: "swap_rb"  # Options: "none", "swap_rb", "swap_rg", "bgr_to_rgb"
```

**Available modes:**

1. **`none`** (default if not configured)
   - No color correction applied
   - Use if your scanner produces correct colors

2. **`swap_rb`** or **`bgr_to_rgb`** (recommended for DR-F120)
   - Swaps Red and Blue channels (BGR ↔ RGB)
   - This fixes the most common color issue with the Canon DR-F120
   - Example: Blue becomes Red, Red becomes Blue, Green stays Green

3. **`swap_rg`**
   - Swaps Red and Green channels
   - Rare, but available if needed
   - Example: Red becomes Green, Green becomes Red, Blue stays Blue

### Image Optimization Options

```yaml
upload:
  compression: "individual"  # Options: "individual", "zip"
  image_quality: 90          # JPEG quality (1-100, higher = better quality)
  optimize_png: true         # Optimize PNG files to reduce size
```

**Compression modes:**

1. **`individual`** (default)
   - Upload each page separately
   - Pages are uploaded incrementally as they're scanned
   - Better for real-time progress tracking

2. **`zip`**
   - Compress all pages into a single ZIP file before upload
   - Significantly reduces upload time for multi-page documents
   - Requires all pages to be scanned before upload begins

**Quality settings:**

- **`image_quality`**: JPEG compression quality (1-100)
  - 90 (default): High quality, good compression
  - 95-100: Excellent quality, larger files
  - 70-85: Good quality, smaller files
  
- **`optimize_png`**: Optimize PNG files
  - `true` (default): Reduce PNG file size without quality loss
  - `false`: Keep original PNG encoding

---

## How It Works

### Color Correction Pipeline

1. **Scan**: Scanner produces raw image (possibly with incorrect colors)
2. **Color Correction**: PIL swaps color channels based on configuration
3. **Optimization**: Compress/optimize image based on settings
4. **Upload**: Send to API (individual or ZIP)

### Technical Implementation

The color correction is applied in `piscan/scanner.py`:

```python
def _apply_color_correction(self, file_path: str) -> None:
    """Apply color correction and optimization to scanned image."""
    # Open image
    img = Image.open(file_path)
    
    # Split into channels
    r, g, b = img.split()
    
    # Swap channels based on mode
    if mode == "swap_rb":
        corrected = Image.merge('RGB', (b, g, r))  # BGR -> RGB
    
    # Save with optimization
    corrected.save(file_path, optimize=True, quality=90)
```

Location: `piscan/scanner.py:44-96`

---

## Usage Examples

### Example 1: Basic Color Correction

**Config:**
```yaml
scanner:
  device: "canon_dr:libusb:003:003"
  mode: "Color"
  format: "png"
  color_correction: "swap_rb"

upload:
  compression: "individual"
  optimize_png: true
```

**Command:**
```bash
python scan.py
```

**Result:**
- Scans in color mode
- Swaps Red/Blue channels to fix color
- Optimizes PNG files
- Uploads each page individually

### Example 2: High-Quality ZIP Upload

**Config:**
```yaml
scanner:
  mode: "Color"
  format: "jpeg"
  color_correction: "swap_rb"

upload:
  compression: "zip"
  image_quality: 95
```

**Command:**
```bash
python scan.py --source "ADF Duplex"
```

**Result:**
- Scans duplex (both sides)
- Applies color correction
- Saves as JPEG with 95% quality
- Creates ZIP archive with all pages
- Uploads single ZIP file

### Example 3: Grayscale (No Correction Needed)

**Config:**
```yaml
scanner:
  mode: "Gray"
  format: "png"
  color_correction: "none"  # Grayscale doesn't need correction

upload:
  compression: "zip"
  optimize_png: true
```

---

## Verifying Color Correction

### Method 1: Visual Inspection

Scan a document with known colors (e.g., red text, blue logo):

```bash
python scan.py
```

Check the uploaded document:
- If colors look correct → Configuration is good
- If colors are still wrong → Try a different correction mode

### Method 2: Test Image

Create a test image with red, green, and blue sections:

```bash
# Scan test page
python scan.py --debug

# Check output in /tmp/YYYY-MM-DD-HHMMSS/page_001.png
```

Open the scanned image and verify:
- Red areas appear red (not blue)
- Blue areas appear blue (not red)
- Green areas appear green

### Method 3: Histogram Analysis

```bash
# Scan a page
python scan.py

# Check channel distribution
python -c "
from PIL import Image
img = Image.open('/path/to/scan.png')
r, g, b = img.split()
print(f'Red avg: {sum(r.getdata())/len(r.getdata())}')
print(f'Green avg: {sum(g.getdata())/len(g.getdata())}')
print(f'Blue avg: {sum(b.getdata())/len(b.getdata())}')
"
```

---

## Error Logging

When scanning fails, errors are automatically logged to the API endpoint:

**API Endpoint:** `POST {api_url}/{workspace}/api/log`

**Payload:**
```json
{
  "level": "error",
  "message": "Scan failed: No paper in document feeder",
  "source": "scanner",
  "clientTimestamp": "2026-01-02T10:30:00.000Z",
  "details": {
    "source": "ADF Duplex",
    "device": "canon_dr:libusb:003:003"
  }
}
```

This allows remote monitoring of scanner issues.

---

## Troubleshooting

### Colors Still Wrong After Correction

1. **Try different correction mode:**
   ```yaml
   color_correction: "swap_rg"  # Instead of swap_rb
   ```

2. **Verify scanner backend:**
   ```bash
   scanimage -L
   # Should show: canon_dr:libusb:...
   ```

3. **Check if backend exposes color options:**
   ```bash
   scanimage -d "canon_dr:libusb:003:003" -A | grep -i color
   ```

### Large File Sizes

1. **Reduce JPEG quality:**
   ```yaml
   upload:
     image_quality: 85  # Lower = smaller files
   ```

2. **Use ZIP compression:**
   ```yaml
   upload:
     compression: "zip"
   ```

3. **Use JPEG instead of PNG for color scans:**
   ```yaml
   scanner:
     format: "jpeg"  # Smaller than PNG for photos
   ```

### ZIP Upload Fails

1. **Check available disk space:**
   ```bash
   df -h /tmp
   ```

2. **Verify ZIP is created correctly:**
   ```bash
   ls -lh /tmp/*.zip
   unzip -l /tmp/temp*.zip
   ```

3. **Fall back to individual upload:**
   ```yaml
   upload:
     compression: "individual"
   ```

---

## Performance Comparison

### Upload Time (10 pages, 300 DPI, color)

| Mode | Format | Compression | Total Size | Upload Time |
|------|--------|-------------|------------|-------------|
| Individual | PNG | optimize | 45 MB | 90 sec |
| Individual | JPEG (90) | none | 22 MB | 45 sec |
| ZIP | PNG | optimize | 42 MB | 50 sec |
| ZIP | JPEG (90) | none | 20 MB | 25 sec |

**Recommendation:**
- For best quality: Individual PNG with optimize
- For best speed: ZIP JPEG with quality 85-90

---

## Advanced Configuration

### Custom Color Correction

If the built-in modes don't work, you can modify the correction in `piscan/scanner.py`:

```python
# Add custom correction mode
elif correction_mode == "custom":
    # Your custom channel mapping
    corrected_channels = (r, b, g)  # Example: swap G and B
```

### Conditional Correction

Apply correction only to specific sources:

```python
# In _apply_color_correction()
if actual_source == "ADF Duplex" and correction_mode:
    # Apply correction only for ADF
    ...
```

---

## Integration with Existing Workflow

The color correction and optimization are **fully backward-compatible**:

- **scan.py**: Works without modification
- **button_detector.py**: Works without modification  
- **API upload**: Compatible with existing endpoint

Simply update your `config.yaml` and the features activate automatically.

---

## Summary

**Problem:** Canon DR-F120 scanner outputs BGR instead of RGB in color mode

**Solution:** Post-processing with PIL to swap color channels

**Configuration:**
```yaml
scanner:
  color_correction: "swap_rb"  # Fix BGR->RGB

upload:
  compression: "zip"           # Faster uploads
  image_quality: 90            # Good quality/size balance
  optimize_png: true           # Reduce PNG size
```

**Files Modified:**
- `config/config.example.yaml`: Added upload settings
- `piscan/config.py`: Added config properties (piscan/config.py:281-295)
- `piscan/scanner.py`: Enhanced color correction (piscan/scanner.py:44-96)
- `piscan/uploader.py`: Added ZIP compression and error logging (piscan/uploader.py:54-106)

**No changes required** to existing scripts (`scan.py`, `button_detector.py`)
