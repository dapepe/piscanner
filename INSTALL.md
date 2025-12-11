# Piscan Installation and Usage Guide

## Quick Installation

### Automated Setup (Recommended)

The easiest way to install and configure piscan:

```bash
# Navigate to piscan directory
cd /opt/piscan

# Run the interactive setup wizard
sudo scripts/setup.sh
```

The wizard will guide you through:
- Installing system dependencies
- Installing Python packages
- Creating configuration
- Testing scanner
- Optionally configuring button support

### Manual Installation

If you prefer step-by-step manual installation:

#### 1. Install Dependencies

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y sane-utils python3-pip python3-dev curl

# Install Python dependencies
cd /opt/piscan
pip3 install -r requirements.txt

# Install piscan package
pip3 install -e .
```

#### 2. Configure Scanner

```bash
# Test scanner detection
scanimage -L

# Test scanner functionality
scanimage --test
```

#### 3. Configure Piscan

```bash
# Copy example configuration to local config
cp config/config.example.yaml config/config.yaml

# Edit the configuration to match your setup
nano config/config.yaml
```

**Required settings:**
- `api.url` - Your API server URL
- `api.token` - Your authentication token
- `api.workspace` - Your workspace name

### 4. Set up Button Detection (Optional)

#### Automated Setup (Recommended)

```bash
sudo scripts/setup-button.sh
```

This interactive script will:
- Install scanbd
- Configure SANE for scanbd coordination
- Set up button trigger script
- Test button detection
- Enable scanbd service

#### Manual Setup

For manual button configuration:

```bash
# Configure SANE for scanbd
sudo nano /etc/sane.d/dll.conf
# Comment out all backends except: net

sudo nano /etc/sane.d/net.conf
# Add: localhost

# Copy SANE configs for scanbd
sudo cp -r /etc/sane.d /etc/scanbd/

# Configure scanbd actions
sudo nano /etc/scanbd/scanbd.conf
# Add action for scan button

# Create action script
sudo tee /etc/scanbd/scan.sh > /dev/null << 'EOF'
#!/bin/bash
curl -X POST http://localhost:5000/scan
EOF

sudo chmod +x /etc/scanbd/scan.sh

# Start scanbd
sudo systemctl enable scanbd
sudo systemctl start scanbd
```

## Usage

### Commands

#### Start HTTP Server
```bash
piscan server
```

#### Test Scan (Interactive)
```bash
piscan test-scan --interactive
```

#### Test Scan (CLI)
```bash
piscan test-scan --source ADF --resolution 300 --upload
```

#### Test Button Detection
```bash
piscan test-buttons --duration 60
```

#### Show Scanner Information
```bash
piscan info
```

### HTTP API Endpoints

- `POST /scan` - Trigger a scan job
- `GET /status` - Get scanner status
- `GET /logs` - View recent logs
- `GET /scanner/info` - Get scanner information
- `GET /config` - View current configuration
- `GET /health` - Health check

### Configuration

Key configuration options:

- `scanner.device`: Scanner device (auto-detect if empty)
- `scanner.resolution`: Scan resolution in DPI (default: 300)
- `scanner.source`: Scan source - Auto, ADF, or Flatbed (default: Auto)
- `api.workspace`: API workspace (default: "default")
- `api.url`: API base URL
- `api.token`: Bearer token for authentication
- `processing.skip_blank`: Skip blank pages (default: true)
- `server.port`: HTTP server port (default: 5000)

## Features

- **Automatic Source Detection**: Uses ADF if paper loaded, otherwise Flatbed
- **Blank Page Detection**: Configurable threshold for detecting blank pages
- **Failed Job Storage**: Stores failed scans for later inspection
- **HTTP Control**: REST API for remote scanning and monitoring
- **Button Support**: Integration with scanbd for physical button detection
- **Configurable**: YAML-based configuration with sensible defaults
- **Logging**: Comprehensive logging with configurable levels

## Troubleshooting

### Scanner Not Found
```bash
# Check scanner detection
scanimage -L

# Check USB permissions
ls -l /dev/bus/usb/*/*
sudo usermod -a -G scanner $USER
```

### Button Detection Not Working
```bash
# Test scanbd
sudo scanbd -f -d5

# Check scanbd status
sudo systemctl status scanbd
```

### Upload Failures
```bash
# Test API connection
piscan info

# Check network connectivity
curl -H "Authorization: Bearer YOUR_TOKEN" http://your-api-server/default/api/
```

## Development

For development, you can run piscan directly:

```bash
python3 -m piscan.cli --help
```