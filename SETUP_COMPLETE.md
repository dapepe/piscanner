# ✅ Piscan Setup & Configuration Complete

## What Was Done

### 1. Local Configuration Directory ✓

**Created:**
- `config/config.example.yaml` - Example configuration with all options documented
- `config/config.yaml` - Your actual config (gitignored, needs to be created)
- `config/README.md` - Configuration documentation

**Config Priority Order:**
1. `./config/config.yaml` ← **RECOMMENDED** (local, gitignored)
2. `~/.piscan/config.yaml` (user home)
3. `/etc/piscan/config.yaml` (system-wide)
4. `./config.yaml` (legacy, deprecated)

### 2. Setup Scripts ✓

**Created executable scripts:**
- `scripts/setup.sh` - Main installation wizard (7.4 KB)
  - Installs dependencies
  - Creates config from example
  - Prompts for API settings
  - Tests scanner
  - Optional button setup
  
- `scripts/setup-button.sh` - Button configuration wizard (11 KB)
  - Installs scanbd
  - Backs up existing configs
  - Configures SANE/scanbd coordination
  - Creates trigger script
  - Tests button detection
  - Enables services

- `scripts/README.md` - Scripts documentation (5.0 KB)

### 3. Git Configuration ✓

**Created `.gitignore`:**
- Excludes `config/config.yaml` (sensitive data)
- Excludes `config/*.local.yaml`
- Excludes log files and test output
- Excludes Python cache

**Security:** Your API token in `config/config.yaml` will never be committed!

### 4. Documentation ✓

**Enhanced:**
- `README.md` - Updated with setup script instructions
- `INSTALL.md` - Added automated setup options
- `QUICKSTART.md` - Quick reference guide (NEW)
- `config/README.md` - Configuration guide (NEW)
- `scripts/README.md` - Setup scripts guide (NEW)
- `SUMMARY.md` - Implementation summary
- `SPEC.md` - Original specification

### 5. Code Updates ✓

**Modified `piscan/config.py`:**
- Changed config priority to check `./config/config.yaml` first
- Maintains backward compatibility with other locations

## Quick Start

### First-Time Setup

```bash
# Run the interactive setup wizard
sudo scripts/setup.sh
```

### Configure Button Support

```bash
# Run the button setup wizard
sudo scripts/setup-button.sh
```

### Manual Configuration

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit with your API details
nano config/config.yaml

# Required fields:
#   api.url - Your API server
#   api.token - Your auth token
#   api.workspace - Your workspace
```

### Start Scanning

```bash
# Start server
piscan server

# Or test first
piscan test-scan --interactive
```

## Setup Script Features

### Main Setup (setup.sh)

✓ **Interactive prompts** - Ask before each step
✓ **Color-coded output** - Green success, yellow warnings, red errors
✓ **Dependency installation** - sane-utils, python3-pip, curl
✓ **Python package setup** - pip install with requirements
✓ **Config creation** - From example with user input
✓ **Scanner testing** - Detect and test scanner
✓ **Log file setup** - Create /var/log/piscan.log
✓ **Optional button setup** - Calls button wizard

### Button Setup (setup-button.sh)

✓ **Root check** - Ensures sudo privileges
✓ **Scanner detection** - Finds device automatically
✓ **scanbd installation** - apt-get install if needed
✓ **Config backup** - Saves to /etc/piscan-backup-*
✓ **SANE configuration** - Sets up network backend
✓ **scanbd configuration** - Creates action script
✓ **Interactive testing** - Press button to verify
✓ **Service enablement** - systemctl enable/start
✓ **Piscan verification** - Checks server running

## Directory Structure

```
piscan/
├── config/
│   ├── config.example.yaml  ← Copy this to config.yaml
│   ├── config.yaml          ← Your config (gitignored)
│   └── README.md            ← Config documentation
├── scripts/
│   ├── setup.sh            ← Main setup wizard
│   ├── setup-button.sh     ← Button setup wizard
│   └── README.md           ← Scripts documentation
├── piscan/                  ← Python package
│   ├── cli.py
│   ├── config.py           ← Updated config paths
│   ├── scanner.py
│   └── ...
├── .gitignore              ← Protects sensitive data
├── README.md               ← Complete documentation
├── QUICKSTART.md           ← Quick reference
└── INSTALL.md              ← Installation guide
```

## Configuration Security

### ✅ Protected Files (gitignored)

- `config/config.yaml` - Contains API token
- `config/*.local.yaml` - Any local configs
- `*.log` - Log files
- `__pycache__/` - Python cache

### ⚠️ Important

**NEVER commit `config/config.yaml` to git!**

It contains your API authentication token. The setup scripts help you create it locally and `.gitignore` ensures it won't be committed.

## Usage Examples

### Using Setup Scripts

```bash
# Complete fresh setup
sudo scripts/setup.sh

# Just button configuration
sudo scripts/setup-button.sh

# Check what setup does
cat scripts/README.md
```

### Running Piscan

```bash
# With local config (automatic)
piscan server

# With specific config
piscan --config config/config.yaml server

# Test mode
piscan test-scan --interactive

# Get scanner info
piscan info
```

### HTTP API

```bash
# Trigger scan
curl -X POST http://localhost:5000/scan

# Check status
curl http://localhost:5000/status

# View logs
curl http://localhost:5000/logs?lines=50
```

## Troubleshooting

### Config not found?

```bash
# Check config exists
ls -l config/config.yaml

# If not, copy from example
cp config/config.example.yaml config/config.yaml
nano config/config.yaml
```

### Scanner not detected?

```bash
# Run scanner detection
scanimage -L

# Check USB
lsusb | grep Canon

# Fix permissions
sudo usermod -a -G scanner $USER
```

### Button not working?

```bash
# Re-run button setup
sudo scripts/setup-button.sh

# Check scanbd
sudo systemctl status scanbd

# Test manually
sudo /etc/scanbd/scan.sh
```

### Setup script fails?

```bash
# Check you have sudo
sudo -v

# Check internet connection
ping -c 3 8.8.8.8

# Run with verbose output
sudo bash -x scripts/setup.sh
```

## Next Steps

1. **Run Setup:** `sudo scripts/setup.sh`
2. **Edit Config:** `nano config/config.yaml`
3. **Test Scanner:** `piscan info`
4. **Configure Button:** `sudo scripts/setup-button.sh`
5. **Start Server:** `piscan server`
6. **Trigger Scan:** Press button or use HTTP API

## Documentation Reference

| Document | Purpose |
|----------|---------|
| `README.md` | Complete documentation with all features |
| `QUICKSTART.md` | Quick reference for common tasks |
| `INSTALL.md` | Detailed installation instructions |
| `config/README.md` | Configuration options explained |
| `scripts/README.md` | Setup scripts usage and troubleshooting |
| `SUMMARY.md` | Implementation details and statistics |
| `SPEC.md` | Original project specification |

## Support

Having issues?

1. **Read the output** - Scripts provide detailed messages
2. **Check logs** - `tail -f /var/log/piscan.log`
3. **Review docs** - Start with `QUICKSTART.md`
4. **Test components** - Use `piscan test-scan --interactive`
5. **Check services** - `systemctl status scanbd`

## What's Different from Original?

### Before (Original)
- Config in `~/.piscan/config.yaml` (home directory)
- Config in root directory `./config.yaml`
- Manual scanbd setup (complex)
- No automated setup

### After (Improved) ✨
- ✅ Config in `./config/` (local, organized)
- ✅ Example config separate from actual config
- ✅ Config properly gitignored
- ✅ Interactive setup wizard (`scripts/setup.sh`)
- ✅ Interactive button wizard (`scripts/setup-button.sh`)
- ✅ Comprehensive setup documentation
- ✅ Color-coded script output
- ✅ Automatic config backups
- ✅ Scanner detection and testing
- ✅ Service enablement

## Summary

You now have:
✅ Local config directory with gitignore protection
✅ Example config separate from actual config
✅ Interactive setup wizard for easy installation
✅ Interactive button setup wizard for scanbd
✅ Comprehensive documentation at every level
✅ Secure configuration (API token protected)
✅ Easy-to-use scripts with detailed output

**Everything is ready for setup!** 🎉

Run `sudo scripts/setup.sh` to begin.
