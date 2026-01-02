# Color Correction Fixes - Summary

## Issues Found and Fixed

### Issue 1: Missing Upload Section in config.yaml
**Problem:** The `upload` section was only added to `config.example.yaml` but not to the actual `config.yaml` file.

**Fix:** Added upload section to `/opt/piscan/config/config.yaml`:
```yaml
upload:
  compression: "individual"
  image_quality: 90
  optimize_png: true
```

**Status:** ✅ FIXED

---

### Issue 2: scan.py Not Using Scanner/Uploader Classes
**Problem:** The `scan.py` script had its own implementation that bypassed the `Scanner` and `Uploader` classes entirely, so color correction was never applied.

**Fix:** Completely rewrote `/opt/piscan/scan.py` to:
- Import and use `Scanner`, `Uploader`, and `Config` classes
- Initialize Scanner with Uploader for error logging
- Use Scanner's `scan_pages()` method with callback
- Color correction is now applied automatically via `scanner._apply_color_correction()` (line 213 in scanner.py)

**Status:** ✅ FIXED

---

## Verification Tests

### Test 1: Config Loading
```
✓ Config loaded
✓ Color correction mode: swap_rg
✓ Upload compression: individual
✓ Image quality: 90
✓ Optimize PNG: True
```

### Test 2: Color Correction Functionality
```
✓ Created test image (pure red: 255,0,0)
✓ Applied color correction (swap_rg)
✓ Result: Green (0,255,0)
✓ Color correction working correctly!
```

### Test 3: Scanner/Uploader Integration
```
✓ Config loaded
✓ Uploader initialized
✓ Scanner initialized
  - Device: net:localhost:canon_dr
  - Color correction: swap_rg
  - Has uploader: True
✓ All components ready
```

---

## How It Works Now

### Color Correction Flow:

1. **Load config** → Reads `color_correction: "swap_rg"`
2. **Initialize Scanner** → Scanner knows to apply correction
3. **Scan pages** → For each page:
   - scanimage writes file
   - `_apply_color_correction()` swaps channels (line 213)
   - Callback triggered → Upload happens
4. **Upload** → Corrected image sent to API

---

## Testing Your Scans

```bash
cd /opt/piscan
python3 scan.py --debug
```

**Expected output:**
```
Scan directory: /tmp/2026-01-02-HHMMSS
Color correction: swap_rg
Scanner device: net:localhost:canon_dr
Scanning and uploading pages as they complete...
✓ Page 1 uploaded
✓ Scan complete
```

---

## Current Configuration

```yaml
scanner:
  color_correction: "swap_rg"  # ← Active

upload:
  compression: "individual"    # ← Added
  image_quality: 90            # ← Added
  optimize_png: true           # ← Added
```

---

## Next: Check Button Scanning

Let me verify the server/button implementation uses Scanner class...
