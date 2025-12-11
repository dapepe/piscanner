# Piscan Setup Scripts

This directory contains interactive setup scripts to help configure piscan.

## Scripts

### setup.sh - Main Setup Wizard

Interactive wizard that guides you through the complete piscan installation.

**Usage:**
```bash
sudo scripts/setup.sh
```

**What it does:**
1. Installs system dependencies (sane-utils, python3-pip, etc.)
2. Installs Python packages
3. Creates configuration from example
4. Prompts for API settings (URL, token, workspace)
5. Tests scanner detection
6. Creates log file
7. Optionally runs button setup

**When to use:**
- First time installation
- Setting up on a new Raspberry Pi
- Resetting configuration

### setup-button.sh - Button Configuration

Interactive script specifically for configuring the scanner's physical button support.

**Usage:**
```bash
sudo scripts/setup-button.sh
```

**What it does:**
1. Checks scanner detection
2. Installs scanbd if needed
3. Backs up existing configuration files
4. Configures SANE for scanbd coordination
5. Creates button trigger script
6. Configures scanbd actions
7. Tests button detection interactively
8. Enables and starts scanbd service
9. Verifies piscan is running

**When to use:**
- After initial piscan installation
- When adding button support later
- Troubleshooting button issues
- Reconfiguring after scanner change

## Requirements

Both scripts require root privileges (sudo) to:
- Install system packages
- Modify system configuration files
- Create/edit files in /etc/
- Start/stop system services

## Configuration Backups

The button setup script automatically creates backups before modifying system files:

```
/etc/piscan-backup-YYYYMMDD-HHMMSS/
├── dll.conf           # SANE backend configuration
├── net.conf           # SANE network configuration
└── scanbd.conf        # scanbd configuration
```

**To restore from backup:**
```bash
sudo cp /etc/piscan-backup-*/dll.conf /etc/sane.d/
sudo cp /etc/piscan-backup-*/net.conf /etc/sane.d/
sudo cp /etc/piscan-backup-*/scanbd.conf /etc/scanbd/
sudo systemctl restart scanbd
```

## Troubleshooting

### Setup fails to detect scanner

**Check:**
```bash
# USB connection
lsusb | grep Canon

# SANE detection
scanimage -L

# Permissions
ls -l /dev/bus/usb/*/*
sudo usermod -a -G scanner $USER
```

### Button setup fails

**Check:**
```bash
# scanbd installation
scanbd --version

# Configuration syntax
sudo scanbd -f -d7  # Run in foreground, will show errors

# Trigger script manually
sudo /etc/scanbd/scan.sh

# Piscan is running
curl http://localhost:5000/health
```

### Permissions issues

**Fix:**
```bash
# Add user to scanner group
sudo usermod -a -G scanner,lp $USER

# Log out and back in for group changes to take effect
# Or reboot
```

## Advanced Usage

### Run setup non-interactively

You can modify the scripts to skip prompts:

```bash
# Edit script and change ask_yes_no calls to always return true
# Or set environment variables to control behavior
```

### Custom configuration

After running setup, manually edit:
- `config/config.yaml` - Piscan configuration
- `/etc/scanbd/scanbd.conf` - Button behavior
- `/etc/scanbd/scan.sh` - Button trigger script

### Multiple scanners

The scripts currently configure for a single scanner. For multiple scanners:
1. Identify each scanner: `scanimage -L`
2. Create separate scanbd configurations
3. Use different button scripts for each
4. Modify button scripts to specify scanner device

## Testing

### Test complete workflow

After setup:

```bash
# 1. Start piscan
piscan server &

# 2. Test HTTP API
curl http://localhost:5000/health
curl http://localhost:5000/status

# 3. Test scan manually
curl -X POST http://localhost:5000/scan

# 4. Test button (if configured)
# Press physical button on scanner
# Check logs:
tail -f /var/log/piscan.log
journalctl -u scanbd -f

# 5. Test CLI
piscan info
piscan test-scan --interactive
```

## Getting Help

If setup fails:

1. **Read the output carefully** - Scripts provide detailed error messages
2. **Check the logs**:
   ```bash
   tail -f /var/log/piscan.log
   journalctl -u scanbd -n 50
   ```
3. **Review documentation**:
   - `README.md` - Main documentation
   - `INSTALL.md` - Installation guide
   - `config/README.md` - Configuration help
4. **Check prerequisites**:
   - Scanner is connected and powered on
   - User has sudo privileges
   - Internet connection for package installation

## Script Architecture

Both scripts follow a similar pattern:

1. **Header with metadata** - Description, colors, helper functions
2. **Validation** - Check prerequisites, root access
3. **Interactive prompts** - Ask user preferences
4. **Execution** - Perform setup steps
5. **Verification** - Test configuration
6. **Summary** - Display results and next steps

The scripts are designed to be:
- **Idempotent** - Safe to run multiple times
- **Reversible** - Creates backups before changes
- **Informative** - Detailed output with color coding
- **Interactive** - Prompts for user input
- **Robust** - Error handling and validation
