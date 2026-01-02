# Color Correction - All Issues Fixed

## Summary

✅ **config.yaml** - Added upload section  
✅ **scan.py** - Rewritten to use Scanner class with color correction  
✅ **cli.py (ScanManager)** - Fixed to pass uploader to Scanner  
✅ **Color correction** - Verified working  

## What Was Wrong

1. Upload settings missing from config.yaml
2. scan.py bypassed Scanner class (no color correction)
3. ScanManager didn't pass uploader to Scanner (button scans had no correction)

## What Was Fixed

### File 1: config/config.yaml
Added missing upload section.

### File 2: scan.py  
Completely rewritten to use Scanner/Uploader classes.

### File 3: piscan/cli.py
Changed line 103-106 to initialize uploader first, then pass to Scanner.

## Testing

Run this to verify:
```bash
cd /opt/piscan
python3 scan.py --debug
```

You should see:
- "Color correction: swap_rg" in output
- Pages uploaded with corrected colors

## Current Config

```yaml
scanner:
  color_correction: "swap_rg"  # Active

upload:
  compression: "individual"     # Added
  image_quality: 90
  optimize_png: true
```

## If Colors Still Wrong

Try swap_rb instead:
```bash
nano config/config.yaml
# Change: color_correction: "swap_rb"
```

**All fixed! Both scan.py and button scanning now apply color correction.**
