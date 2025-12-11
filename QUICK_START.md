# Quick Start Guide - Canon DR-F120 Button Scanning

## ✅ Everything Is Ready!

Your Canon DR-F120 scanner is configured for automatic button-triggered scanning.

---

## How To Use

### **Simple: Just Press the Button!**

1. **Load documents** into the ADF (face up, top edge first)
2. **Press the green START button** on the scanner
3. **Wait** for scanning to complete
4. **Done!** Documents are automatically:
   - Scanned (both sides)
   - Blank pages removed
   - Uploaded to your API

---

## Services Status

Check if everything is running:

```bash
sudo systemctl status scanbd piscan
```

Both should show: `Active: active (running)`

---

## Testing

### Quick Test
```bash
# Load paper, then press green button
# Watch what happens:
sudo journalctl -u piscan -f
```

### Manual Test (without button)
```bash
curl -X POST http://localhost:5000/scan \
     -H "Content-Type: application/json" \
     -d '{"source": "ADF Duplex"}'
```

---

## Configuration

- **Scanner Mode**: ADF Duplex (both sides)
- **Resolution**: 300 DPI
- **Color Mode**: Color
- **Format**: PNG
- **Blank Pages**: Automatically removed
- **Upload**: Automatic to API

---

## Common Commands

```bash
# Restart services
sudo systemctl restart scanbd piscan

# View logs
sudo journalctl -u piscan -f
sudo journalctl -u scanbd -f

# Check scanner
scanimage -L

# Test API
curl http://localhost:5000/health
```

---

## Troubleshooting

**Button doesn't work?**
```bash
sudo systemctl restart scanbd piscan
```

**Scanner not found?**
```bash
scanimage -L
# Should show: net:localhost:canon_dr:...
```

**Scan fails?**
- Check paper is loaded in ADF
- Check logs: `tail -f /var/log/piscan.log`

---

## Full Documentation

See `/opt/piscan/BUTTON_SETUP.md` for complete documentation.

---

**Ready to scan? Just press the green button!** 🟢
