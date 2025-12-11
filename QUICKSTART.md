# Piscan Quick Start Guide

## 🚀 Installation (3 Steps)

```bash
# 1. Navigate to piscan directory
cd /opt/piscan

# 2. Run setup wizard
sudo scripts/setup.sh

# 3. Start the server
piscan server
```

That's it! The wizard handles everything else.

## 📋 Essential Commands

### Server Management

```bash
# Start server (foreground)
piscan server

# Start with debug output
piscan --log-level DEBUG server

# Start as background service
sudo systemctl start piscan
```

### Testing

```bash
# Check scanner info
piscan info

# Interactive test scan
piscan test-scan --interactive

# Quick test scan
piscan test-scan --source ADF --resolution 300

# Test scan and upload
piscan test-scan --upload

# Test button detection
piscan test-buttons --duration 60
```

### HTTP API

```bash
# Trigger scan
curl -X POST http://localhost:5000/scan

# Check status
curl http://localhost:5000/status

# View logs
curl http://localhost:5000/logs

# Get scanner info
curl http://localhost:5000/scanner/info

# Health check
curl http://localhost:5000/health
```

## ⚙️ Configuration

Configuration file: `config/config.yaml`

### Minimum Required Settings

```yaml
api:
  url: "http://your-server:8080"
  token: "your-bearer-token"
  workspace: "default"
```

### Quick Edit

```bash
nano config/config.yaml
```

## 🔘 Physical Button Setup

```bash
sudo scripts/setup-button.sh
```

## 📁 Important Locations

- **Config**: `./config/config.yaml`
- **Logs**: `/var/log/piscan.log`
- **Failed scans**: `/tmp/failed/`
- **Temp scans**: `/tmp/`

## 🔍 Troubleshooting

### Scanner not found?

```bash
scanimage -L
lsusb | grep Canon
sudo usermod -a -G scanner $USER
```

### Button not working?

```bash
sudo systemctl status scanbd
sudo /etc/scanbd/scan.sh
journalctl -u scanbd -f
```

### Upload failing?

```bash
tail -f /var/log/piscan.log
curl http://your-api-server/default/api/
```

### Check permissions

```bash
ls -l /var/log/piscan.log
ls -l /tmp/
sudo usermod -a -G scanner,lp $USER
```

## 📖 Full Documentation

- `README.md` - Complete documentation
- `config/README.md` - Configuration help
- `scripts/README.md` - Setup scripts guide
- `INSTALL.md` - Detailed installation

## 🎯 Common Workflows

### Daily Use (Button)

1. Load documents in scanner
2. Press physical scan button
3. Documents automatically uploaded

### Remote Trigger

```bash
curl -X POST http://raspberrypi:5000/scan
```

### Check Last Scan

```bash
curl http://raspberrypi:5000/status | json_pp
```

### View Recent Logs

```bash
curl http://raspberrypi:5000/logs?lines=50
```

## 🔧 Advanced

### Custom Resolution

Edit `config/config.yaml`:
```yaml
scanner:
  resolution: 600  # 150, 300, or 600
```

### Skip Blank Pages

```yaml
processing:
  skip_blank: true
  blank_threshold: 0.03  # Adjust sensitivity
```

### Multiple Configs

```bash
piscan --config /path/to/custom.yaml server
```

### Run as Service

```bash
sudo systemctl enable piscan
sudo systemctl start piscan
sudo systemctl status piscan
```

## 💡 Tips

- Use `Auto` source for automatic ADF/Flatbed detection
- Lower `blank_threshold` for more aggressive blank detection
- Check logs first when troubleshooting
- Keep `config.yaml` secret (contains API token)
- Test with `--interactive` mode first
- Button requires scanbd configuration

## 🆘 Getting Help

1. Check logs: `tail -f /var/log/piscan.log`
2. Test scanner: `piscan info`
3. Run diagnostics: `piscan test-scan --interactive`
4. Check scanbd: `journalctl -u scanbd -n 50`
5. Review documentation in `README.md`

---

**Ready to scan?** → `piscan server` and press your scan button! 📄✨
