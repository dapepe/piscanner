#!/bin/bash
#
# Piscan Button Setup Script
# Interactive setup for scanner physical button support via scanbd
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

ask_yes_no() {
    while true; do
        read -p "$1 (y/n): " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Main script
print_header "Piscan Physical Button Setup"

echo "This script will configure your scanner's physical button to trigger scans."
echo "It sets up scanbd (Scanner Button Daemon) to detect button presses."
echo ""
print_warning "This script requires root privileges and will modify system files."
echo ""

if ! ask_yes_no "Continue with setup?"; then
    echo "Setup cancelled."
    exit 0
fi

check_root

# Step 1: Check for scanner
print_header "Step 1: Scanner Detection"

print_info "Checking for connected scanner..."
if ! command -v scanimage &> /dev/null; then
    print_error "scanimage not found. Please install sane-utils first:"
    echo "  sudo apt-get install sane-utils"
    exit 1
fi

SCANNER_OUTPUT=$(scanimage -L 2>/dev/null || echo "")
if [ -z "$SCANNER_OUTPUT" ]; then
    print_error "No scanner detected!"
    print_info "Please ensure your scanner is:"
    echo "  - Connected via USB"
    echo "  - Powered on"
    echo "  - Recognized by the system (check with: lsusb)"
    exit 1
fi

print_success "Scanner detected:"
echo "$SCANNER_OUTPUT" | sed 's/^/  /'

# Extract device name
SCANNER_DEVICE=$(echo "$SCANNER_OUTPUT" | grep -oP "device \`\K[^']+")
print_info "Device: $SCANNER_DEVICE"

# Step 2: Install scanbd
print_header "Step 2: Install scanbd"

if command -v scanbd &> /dev/null; then
    print_success "scanbd is already installed"
else
    print_info "Installing scanbd..."
    if apt-get update && apt-get install -y scanbd; then
        print_success "scanbd installed successfully"
    else
        print_error "Failed to install scanbd"
        exit 1
    fi
fi

# Step 3: Backup existing configs
print_header "Step 3: Backup Configuration Files"

BACKUP_DIR="/etc/piscan-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f /etc/sane.d/dll.conf ]; then
    cp /etc/sane.d/dll.conf "$BACKUP_DIR/"
    print_success "Backed up /etc/sane.d/dll.conf"
fi

if [ -f /etc/sane.d/net.conf ]; then
    cp /etc/sane.d/net.conf "$BACKUP_DIR/"
    print_success "Backed up /etc/sane.d/net.conf"
fi

if [ -f /etc/scanbd/scanbd.conf ]; then
    cp /etc/scanbd/scanbd.conf "$BACKUP_DIR/"
    print_success "Backed up /etc/scanbd/scanbd.conf"
fi

print_info "Backups saved to: $BACKUP_DIR"

# Step 4: Configure SANE for scanbd
print_header "Step 4: Configure SANE"

print_info "Configuring /etc/sane.d/dll.conf for scanbd coordination..."

# Comment out all backends except net
cat > /etc/sane.d/dll.conf << 'EOF'
# Piscan: Only use network backend for scanbd coordination
# All other backends are commented out
net

# Original backends are disabled - scanbd will use them directly
# If you need to disable button support, restore from backup
EOF

print_success "Updated /etc/sane.d/dll.conf"

# Configure net backend
print_info "Configuring /etc/sane.d/net.conf..."

cat > /etc/sane.d/net.conf << 'EOF'
# Piscan: Connect to scanbd via localhost
localhost
EOF

print_success "Updated /etc/sane.d/net.conf"

# Step 5: Configure scanbd
print_header "Step 5: Configure scanbd"

print_info "Copying SANE configs for scanbd..."

# Copy SANE configs to scanbd directory
if [ ! -d /etc/scanbd/sane.d ]; then
    mkdir -p /etc/scanbd/sane.d
fi

cp -r /etc/sane.d/* /etc/scanbd/sane.d/ 2>/dev/null || true

    # Restore real backends for scanbd
    print_info "Configuring scanbd to use real scanner backends..."

    # Detect which backend to use
    # scanimage -L might return multiple lines. We want the backend of the *selected*
    # scanner, but if that's empty, we try to guess from the first available non-network scanner.
    
    # Clean up SCANNER_DEVICE (take first word before colon)
    # Example: "canon_dr:libusb:003:002" -> "canon_dr"
    SCANBD_BACKEND="$(echo "${SCANNER_DEVICE:-}" | head -n1 | cut -d':' -f1)"
    
    # Fallback if empty or if it looks like a network prefix
    if [ -z "$SCANBD_BACKEND" ] || [ "$SCANBD_BACKEND" = "net" ] || [ "$SCANBD_BACKEND" = "airscan" ]; then
         SCANBD_BACKEND="canon_dr"
    fi

    print_info "Detected backend for scanbd: $SCANBD_BACKEND"

    cat > /etc/scanbd/sane.d/dll.conf << EOF
# Piscan: scanbd uses real backends directly
$SCANBD_BACKEND

# Do NOT use net backend here - that's for normal applications
EOF

    print_success "Updated /etc/scanbd/sane.d/dll.conf"

    # Configure environment for scanbd service
    print_info "Configuring /etc/default/scanbd..."
    
    # Ensure scanbd uses its own config dir, not system default
    if grep -q "SANE_CONFIG_DIR" /etc/default/scanbd 2>/dev/null; then
        sed -i 's|^.*SANE_CONFIG_DIR=.*|export SANE_CONFIG_DIR=/etc/scanbd/sane.d|' /etc/default/scanbd
    else
        echo 'export SANE_CONFIG_DIR=/etc/scanbd/sane.d' >> /etc/default/scanbd
    fi
    print_success "Updated /etc/default/scanbd"

    # Step 6: Get Piscan server details

print_header "Step 6: Piscan Server Configuration"

PISCAN_PORT=5000
read -p "Enter Piscan server port (default: 5000): " INPUT_PORT
if [ ! -z "$INPUT_PORT" ]; then
    PISCAN_PORT=$INPUT_PORT
fi

PISCAN_URL="http://localhost:$PISCAN_PORT/scan"
print_info "Will trigger scans at: $PISCAN_URL"
print_info "Button action will run /opt/piscan/scan.py and log to /var/log/scanbd-scan.log"

# Step 7: Create scan trigger script
print_header "Step 7: Create Button Trigger Script"

print_info "Creating /etc/scanbd/scan.sh..."

cat > /etc/scanbd/scan.sh << 'EOF'
#!/bin/bash
# Piscan: scanbd action script
# Runs the same piscan Python pipeline used by CLI/service.

set -eo pipefail

PYTHON_BIN="/usr/bin/python3"
LOG_FILE_DEFAULT="/var/log/scanbd-scan.log"
LOG_FILE="${PISCAN_SCANBD_LOG:-$LOG_FILE_DEFAULT}"
CONFIG_PATH="${PISCAN_CONFIG:-/opt/piscan/config/config.yaml}"
SCAN_SCRIPT="/opt/piscan/scan.py"

# If /var/log isn't writable by the scanbd user, fall back
# to /tmp to avoid breaking button scans completely.
if ! touch "$LOG_FILE" 2>/dev/null; then
  LOG_FILE="/tmp/scanbd-scan.log"
  touch "$LOG_FILE" 2>/dev/null || true
fi

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$LOG_FILE" 2>/dev/null || logger -t "scanbd" "$*" || true
}

log "=== Scan button pressed - starting scan ==="
log "Config: $CONFIG_PATH"
log "scanbd: action=${SCANBD_ACTION:-unknown} device=${SCANBD_DEVICE:-unknown}"

if [ ! -x "$SCAN_SCRIPT" ]; then
  log "ERROR: Missing scan script: $SCAN_SCRIPT"
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
  log "ERROR: Missing python binary: $PYTHON_BIN"
  exit 1
fi

# Run scan script (includes ZIP bundling + payload size logs)
# --debug prints key config (no secrets) into the scanbd log.
# -u forces unbuffered binary stdout/stderr so logs appear in real-time.
# We redirect directly to LOG_FILE to avoid bash buffering loop delays.
set +e
"$PYTHON_BIN" -u "$SCAN_SCRIPT" --config "$CONFIG_PATH" --debug >> "$LOG_FILE" 2>&1
rc=$?
set -e

if [ "$rc" -eq 0 ]; then
  log "✓ Scan completed successfully"
else
  log "ERROR: Scan failed (exit=$rc)"
fi

log "=== Scan complete ==="
exit "$rc"
EOF

chmod +x /etc/scanbd/scan.sh

# Make sure the primary scan log exists and is writable.
# scanbd typically runs as a non-root user, so fix this during setup.
touch /var/log/scanbd-scan.log
chmod 666 /var/log/scanbd-scan.log

print_success "Created /etc/scanbd/scan.sh"
print_success "Prepared /var/log/scanbd-scan.log (chmod 666)"

# Step 8: Configure scanbd actions
print_header "Step 8: Configure Button Actions"

print_info "Configuring scanbd.conf..."

# Check if scanbd.conf exists and has our action
if grep -q "# Piscan: Scan button action" /etc/scanbd/scanbd.conf 2>/dev/null; then
    print_warning "scanbd.conf already has Piscan configuration"
    if ask_yes_no "Overwrite existing configuration?"; then
        CONFIGURE_SCANBD=true
    else
        CONFIGURE_SCANBD=false
    fi
else
    CONFIGURE_SCANBD=true
fi

if [ "$CONFIGURE_SCANBD" = true ]; then
    # Backup and create new scanbd.conf.
    # IMPORTANT: scanbd triggers are usually device-specific (option names differ
    # between backends), so we create a dedicated piscan device definition.

    # Determine backend prefix for scanbd device filter.
    # scanimage -L might return multiple lines. We want the backend of the *selected*
    # scanner, but if that's empty, we try to guess from the first available non-network scanner.
    
    # Clean up SCANNER_DEVICE (take first word before colon)
    # Example: "canon_dr:libusb:003:002" -> "canon_dr"
    SCANBD_BACKEND="$(echo "${SCANNER_DEVICE:-}" | head -n1 | cut -d':' -f1)"
    
    # Fallback if empty or if it looks like a network prefix (which scanbd can't use for itself)
    if [ -z "$SCANBD_BACKEND" ] || [ "$SCANBD_BACKEND" = "net" ] || [ "$SCANBD_BACKEND" = "airscan" ]; then
         SCANBD_BACKEND="canon_dr"
    fi


    # Ensure our device definition exists.
    mkdir -p /etc/scanbd/scanner.d

    cat > /etc/scanbd/scanner.d/piscan.conf << EOF
# Piscan scanbd device mapping
# Auto-generated by setup-button.sh

device piscan {
    filter = "^${SCANBD_BACKEND}.*"  # backend prefix (regex)
    desc   = "Piscan button trigger"

    # Trigger on Start button (green/main)
    action scan_start {
        filter = "^start$"
        desc   = "Scan to piscan (start)"
        script = "/etc/scanbd/scan.sh"
    }

    # Trigger on extra function buttons (often labelled 1/2/3)
    action scan_button {
        filter = "^button-.*"
        desc   = "Scan to piscan (function button)"
        script = "/etc/scanbd/scan.sh"
    }
}
EOF

    cat > /etc/scanbd/scanbd.conf << 'EOF'
# Piscan scanbd configuration
# Generated by setup-button.sh

# Keep debug enabled for initial setup; lower later if desired.
global {
    debug   = true
    debug-level = 3

    user    = saned
    group   = scanner

    saned      = "/usr/sbin/saned"
    saned_opt  = {}
    saned_env  = { "SANE_CONFIG_DIR=/etc/scanbd/sane.d" }

    scriptdir = /etc/scanbd
    timeout   = 500
    pidfile   = "/var/run/scanbd.pid"

    environment {
        device = "SCANBD_DEVICE"
        action = "SCANBD_ACTION"
    }

    multiple_actions = true
}

# Device configurations
EOF

    # Always include our piscan mapping first.
    echo "include(scanner.d/piscan.conf)" >> /etc/scanbd/scanbd.conf

    # Append include() lines for other available scanner.d configs.
    for f in /etc/scanbd/scanner.d/*.conf; do
        [ -f "$f" ] || continue
        base="$(basename "$f")"
        if [ "$base" = "piscan.conf" ]; then
            continue
        fi
        echo "include(scanner.d/$base)" >> /etc/scanbd/scanbd.conf
    done

    print_success "Updated /etc/scanbd/scanbd.conf"
    print_success "Created /etc/scanbd/scanner.d/piscan.conf (backend: $SCANBD_BACKEND)"

    # --- Fix: Configure scanbd's private SANE backend ---
    print_info "Configuring scanbd private backends..."
    
    # Write only the real backend to scanbd's dll.conf
    cat > /etc/scanbd/sane.d/dll.conf << EOF
# Piscan: scanbd uses real backends directly
$SCANBD_BACKEND

# Do NOT use net backend here - that's for normal applications
EOF
    print_success "Updated /etc/scanbd/sane.d/dll.conf with '$SCANBD_BACKEND'"

    # Configure environment for scanbd service to use this private config
    if grep -q "SANE_CONFIG_DIR" /etc/default/scanbd 2>/dev/null; then
        sed -i 's|^.*SANE_CONFIG_DIR=.*|export SANE_CONFIG_DIR=/etc/scanbd/sane.d|' /etc/default/scanbd
    else
        echo 'export SANE_CONFIG_DIR=/etc/scanbd/sane.d' >> /etc/default/scanbd
    fi
    print_success "Updated /etc/default/scanbd"
    # ----------------------------------------------------

else
    print_info "Skipped scanbd.conf update"
fi

# Step 9: Test button detection
print_header "Step 9: Test Button Detection"

echo "We'll now test if scanbd can detect your button presses."
echo ""
print_info "This will:"
echo "  1. Stop the scanbd service"
echo "  2. Run scanbd in foreground debug mode"
echo "  3. You press the scan button on your scanner"
echo "  4. We check if the button event was detected"
echo ""

if ask_yes_no "Run button detection test?"; then
    print_info "Stopping scanbd service..."
    systemctl stop scanbd 2>/dev/null || true
    
    echo ""
    print_info "Starting scanbd in debug mode..."
    print_warning "Press your scanner's SCAN button now!"
    echo ""
    echo "Watching for button events (will timeout after 30 seconds)..."
    echo "Press Ctrl+C if you see a button event detected."
    echo ""
    
    # Run scanbd in foreground with timeout
    # IMPORTANT: We must explicitly set SANE_CONFIG_DIR for the test command,
    # because it doesn't read /etc/default/scanbd when run manually!
    timeout 30s env SANE_CONFIG_DIR=/etc/scanbd/sane.d scanbd -f -d7 -c /etc/scanbd/scanbd.conf 2>&1 | tee /tmp/scanbd-test.log || true
    
    echo ""
    if grep -qi "scan" /tmp/scanbd-test.log; then
        print_success "Button event detected in output!"
        print_info "Check the output above for details"
    else
        print_warning "No obvious button event detected"
        print_info "Review /tmp/scanbd-test.log for details"
    fi
    
    rm -f /tmp/scanbd-test.log
else
    print_info "Skipped button detection test"
fi

# Step 10: Enable and start scanbd
print_header "Step 10: Enable scanbd Service"

if ask_yes_no "Enable and start scanbd service?"; then
    print_info "Enabling scanbd service..."
    systemctl enable scanbd
    
    print_info "Starting scanbd service..."
    if systemctl start scanbd; then
        print_success "scanbd service started"
        sleep 2
        
        if systemctl is-active --quiet scanbd; then
            print_success "scanbd is running"
        else
            print_error "scanbd failed to start"
            print_info "Check logs with: journalctl -u scanbd -n 50"
        fi
    else
        print_error "Failed to start scanbd"
        print_info "Check logs with: journalctl -u scanbd -n 50"
    fi
else
    print_info "scanbd service not started"
    print_warning "You'll need to start it manually: sudo systemctl start scanbd"
fi

# Step 11: Verify piscan is running
print_header "Step 11: Verify Piscan"

print_info "Checking if piscan server is running..."
if curl -s "http://localhost:$PISCAN_PORT/health" > /dev/null 2>&1; then
    print_success "Piscan server is running on port $PISCAN_PORT"
else
    print_warning "Piscan server is not responding on port $PISCAN_PORT"
    print_info "Make sure to start piscan with: piscan server"
fi

# Final summary
print_header "Setup Complete!"

echo "Configuration summary:"
echo "  - Scanner device: $SCANNER_DEVICE"
echo "  - Backend: $BACKEND"
echo "  - Piscan URL: $PISCAN_URL"
echo "  - scanbd config: /etc/scanbd/scanbd.conf"
echo "  - Trigger script: /etc/scanbd/scan.sh"
echo "  - Backups: $BACKUP_DIR"
echo ""

print_success "Button support is configured!"
echo ""
echo "Next steps:"
echo "  1. Make sure piscan is running: piscan server"
echo "  2. Press the scan button on your scanner"
echo "  3. Check piscan logs: tail -f /var/log/piscan.log"
echo "  4. Check scanbd logs: journalctl -u scanbd -f"
echo ""

print_info "Troubleshooting:"
echo "  - Test manually: sudo /etc/scanbd/scan.sh"
echo "  - View scanbd debug: sudo scanbd -f -d7"
echo "  - Check scanner: scanimage -d net:localhost:$SCANNER_DEVICE --test"
echo "  - Restore backups from: $BACKUP_DIR"
echo ""

print_success "Setup finished!"
