#!/bin/bash
#
# Piscan Main Setup Script
# Quick setup wizard for piscan installation and configuration
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

print_header "Piscan Setup Wizard"

echo "Welcome to Piscan setup!"
echo "This wizard will help you:"
echo "  1. Install system dependencies"
echo "  2. Install Python package"
echo "  3. Create configuration"
echo "  4. Test scanner connection"
echo "  5. Optionally configure button support"
echo ""

if ! ask_yes_no "Continue with setup?"; then
    echo "Setup cancelled."
    exit 0
fi

# Check if running as root for system dependencies
NEED_SUDO=""
if [ "$EUID" -ne 0 ]; then
    if command -v sudo &> /dev/null; then
        NEED_SUDO="sudo"
        print_info "Will use sudo for system operations"
    else
        print_warning "Not running as root and sudo not available"
        print_warning "You may need to install system dependencies manually"
    fi
fi

# Step 1: System Dependencies
print_header "Step 1: System Dependencies"

if ask_yes_no "Install system dependencies (sane-utils, python3-pip)?"; then
    print_info "Updating package list..."
    $NEED_SUDO apt-get update
    
    print_info "Installing dependencies..."
    $NEED_SUDO apt-get install -y sane-utils python3-pip python3-dev curl
    
    print_success "System dependencies installed"
else
    print_info "Skipped system dependencies"
    print_warning "Make sure you have: sane-utils, python3-pip, python3-dev"
fi

# Step 2: Python Package
print_header "Step 2: Python Package Installation"

cd "$PROJECT_DIR"

if ask_yes_no "Install Python dependencies?"; then
    print_info "Installing Python packages..."
    pip3 install -r requirements.txt
    print_success "Python dependencies installed"
fi

if ask_yes_no "Install piscan package?"; then
    print_info "Installing piscan in development mode..."
    pip3 install -e .
    print_success "Piscan installed"
    
    # Verify installation
    if command -v piscan &> /dev/null; then
        print_success "piscan command is available"
        VERSION=$(piscan --help | head -1 || echo "installed")
        print_info "Version: $VERSION"
    else
        print_warning "piscan command not found in PATH"
        print_info "You may need to add ~/.local/bin to your PATH"
    fi
fi

# Step 3: Configuration
print_header "Step 3: Configuration"

CONFIG_FILE="$PROJECT_DIR/config/config.yaml"
EXAMPLE_CONFIG="$PROJECT_DIR/config/config.example.yaml"

if [ -f "$CONFIG_FILE" ]; then
    print_warning "Configuration file already exists: $CONFIG_FILE"
    if ! ask_yes_no "Overwrite existing configuration?"; then
        print_info "Keeping existing configuration"
    else
        cp "$EXAMPLE_CONFIG" "$CONFIG_FILE"
        print_success "Configuration reset from example"
    fi
else
    cp "$EXAMPLE_CONFIG" "$CONFIG_FILE"
    print_success "Created configuration from example"
fi

echo ""
print_info "Let's configure the essential settings..."
echo ""

# API URL
read -p "Enter API base URL (e.g., http://your-server:8080): " API_URL
if [ ! -z "$API_URL" ]; then
    # Update config using sed
    sed -i "s|url: .*|url: \"$API_URL\"|" "$CONFIG_FILE"
    print_success "Set API URL: $API_URL"
fi

# API Token
read -p "Enter API authentication token (or leave empty): " API_TOKEN
if [ ! -z "$API_TOKEN" ]; then
    sed -i "s|token: .*|token: \"$API_TOKEN\"|" "$CONFIG_FILE"
    print_success "Set API token"
fi

# Workspace
read -p "Enter API workspace (default: default): " API_WORKSPACE
if [ ! -z "$API_WORKSPACE" ]; then
    sed -i "s|workspace: .*|workspace: \"$API_WORKSPACE\"|" "$CONFIG_FILE"
    print_success "Set workspace: $API_WORKSPACE"
fi

print_info "Configuration saved to: $CONFIG_FILE"
print_info "You can edit it manually: nano $CONFIG_FILE"

# Step 4: Test Scanner
print_header "Step 4: Scanner Detection"

if command -v scanimage &> /dev/null; then
    print_info "Detecting scanners..."
    SCANNER_OUTPUT=$(scanimage -L 2>&1 || echo "")
    
    if echo "$SCANNER_OUTPUT" | grep -q "device"; then
        print_success "Scanner detected!"
        echo "$SCANNER_OUTPUT" | sed 's/^/  /'
        
        # Extract device name
        SCANNER_DEVICE=$(echo "$SCANNER_OUTPUT" | grep -oP "device \`\K[^']+")
        
        if ask_yes_no "Test scan to verify scanner works?"; then
            print_info "Running test scan..."
            if scanimage --test -d "$SCANNER_DEVICE" 2>&1 | grep -q "succeeded"; then
                print_success "Test scan successful!"
            else
                print_warning "Test scan completed with warnings"
                print_info "Scanner may still work, check output above"
            fi
        fi
    else
        print_warning "No scanner detected"
        print_info "Please ensure your scanner is:"
        echo "  - Connected via USB"
        echo "  - Powered on"
        echo "  - Recognized by the system"
        print_info "Check with: lsusb | grep Canon"
    fi
else
    print_error "scanimage not found - please install sane-utils"
fi

# Step 5: Log Directory
print_header "Step 5: Log Directory"

LOG_FILE="/var/log/piscan.log"
if [ ! -f "$LOG_FILE" ]; then
    if ask_yes_no "Create log file at $LOG_FILE?"; then
        $NEED_SUDO touch "$LOG_FILE"
        $NEED_SUDO chown $USER:$USER "$LOG_FILE" 2>/dev/null || true
        print_success "Created log file"
    fi
fi

# Step 6: Button Support
print_header "Step 6: Physical Button Support (Optional)"

echo "The scanner's physical button can be configured to trigger scans."
echo "This requires installing and configuring scanbd."
echo ""

if ask_yes_no "Set up physical button support?"; then
    BUTTON_SCRIPT="$SCRIPT_DIR/setup-button.sh"
    if [ -f "$BUTTON_SCRIPT" ]; then
        print_info "Running button setup script..."
        $NEED_SUDO "$BUTTON_SCRIPT"
    else
        print_error "Button setup script not found: $BUTTON_SCRIPT"
        print_info "You can run it manually later with: sudo scripts/setup-button.sh"
    fi
else
    print_info "Skipped button setup"
    print_info "You can set it up later with: sudo scripts/setup-button.sh"
fi

# Final steps
print_header "Setup Complete!"

echo "Piscan is now configured!"
echo ""
echo "Quick Start:"
echo ""
echo "  1. Start the server:"
echo "     piscan server"
echo ""
echo "  2. Test a scan:"
echo "     piscan test-scan --interactive"
echo ""
echo "  3. View scanner info:"
echo "     piscan info"
echo ""
echo "  4. Check status:"
echo "     curl http://localhost:5000/status"
echo ""

print_info "Configuration file: $CONFIG_FILE"
print_info "Documentation: $PROJECT_DIR/README.md"
print_info "Examples: $PROJECT_DIR/INSTALL.md"

echo ""
print_success "All done! Happy scanning!"
