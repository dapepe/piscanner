# Piscan - Raspberry Pi Canon DR-F120 Scanner Automation

A Python-based scanning service for Raspberry Pi with Canon imageFORMULA DR-F120 document scanner. Provides automatic scanning, blank page detection, and upload to a remote API with physical button support and HTTP control interface.

## Features

- **Automatic Scanning**: Uses SANE backend for reliable scanner control
- **Multiple Source Support**: Automatic detection between ADF (Auto Document Feeder) and Flatbed
- **Blank Page Detection**: Configurable threshold-based detection to skip empty pages
- **Physical Button Integration**: Support for scanner's physical scan button via scanbd
- **HTTP REST API**: Remote control and monitoring via HTTP endpoints
- **Document Upload**: Multi-file upload to remote API with Bearer token authentication
- **Failed Job Management**: Stores failed scans for later inspection
- **Flexible Configuration**: YAML-based configuration with sensible defaults
- **Comprehensive Logging**: Configurable log levels with rotation support

## Architecture

The application consists of several key components:

- **Scanner Interface** (`scanner.py`): SANE/scanimage integration for hardware control
- **File Manager** (`file_manager.py`): Timestamped directory management and cleanup
- **Blank Page Detector** (`blank_detector.py`): Image analysis using Pillow
- **Uploader** (`uploader.py`): HTTP multipart file upload to remote API
- **HTTP Server** (`server.py`): Flask-based REST API for control and monitoring
- **Configuration Manager** (`config.py`): YAML configuration with property access
- **CLI Interface** (`cli.py`): Command-line interface and main orchestration

## Requirements

### Hardware
- Raspberry Pi (tested on Pi 3/4)
- Canon imageFORMULA DR-F120 scanner (USB connection)

### Software
- Raspberry Pi OS (Debian-based)
- Python 3.8+
- SANE scanner utilities
- scanbd (optional, for physical button support)

## Installation

### Quick Setup (Recommended)

Use the interactive setup wizard:

```bash
# Clone or copy piscan to your Raspberry Pi
cd /opt
sudo git clone <repository-url> piscan
cd piscan

# Run the setup wizard
sudo scripts/setup.sh
```

The wizard will:
- Install system dependencies
- Install Python packages
- Create configuration from example
- Test scanner detection
- Optionally configure button support

### Manual Installation

If you prefer manual setup:

#### 1. Install System Dependencies

```bash
# Update system
sudo apt-get update

# Install SANE and scanning tools
sudo apt-get install -y sane-utils python3-pip python3-dev curl
```

#### 2. Install Python Package

```bash
# Install Python dependencies
cd /opt/piscan
pip3 install -r requirements.txt

# Install piscan in development mode
pip3 install -e .

# Or install system-wide
sudo pip3 install .
```

#### 3. Verify Scanner Detection

```bash
# List connected scanners
scanimage -L

# Should output something like:
# device `canon_dr:libusb:001:002' is a CANON DR-F120 scanner

# Test scanner functionality
scanimage --test
```

#### 4. Configure Piscan

```bash
# Copy example configuration to local config
cp config/config.example.yaml config/config.yaml

# Edit configuration
nano config/config.yaml
```

**Key Configuration Options:**

Edit `config/config.yaml`:

```yaml
scanner:
  device: ""  # Leave empty for auto-detection
  resolution: 300  # DPI
  mode: "Color"  # Color, Gray, or Lineart
  source: "Auto"  # Auto, ADF, or Flatbed
  format: "png"  # png, jpeg, or tiff

api:
  workspace: "default"  # Your API workspace
  url: "http://your-server:8080"  # API base URL
  token: "your-bearer-token-here"  # Authentication token
  timeout: 30  # Request timeout in seconds

processing:
  skip_blank: true  # Skip blank pages
  blank_threshold: 0.03  # 3% non-white pixels = blank

server:
  host: "0.0.0.0"  # Bind address (0.0.0.0 = all interfaces)
  port: 5000  # HTTP server port

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "/var/log/piscan.log"
```

**Important:** The `config/config.yaml` file is gitignored and should not be committed to version control as it contains sensitive tokens.

### 5. Set Up Physical Button Support (Optional)

#### Quick Setup (Recommended)

Use the interactive button setup script:

```bash
sudo scripts/setup-button.sh
```

The script will:
- Install scanbd if needed
- Configure SANE for scanbd coordination
- Set up button trigger script
- Test button detection
- Enable scanbd service

#### Manual Setup

For manual configuration or troubleshooting, follow these steps:

```bash
# 1. Install scanbd
sudo apt-get install scanbd

# 2. Configure SANE to use network backend for scanbd coordination
sudo nano /etc/sane.d/dll.conf
# Comment out all lines and add only:
# net

# 3. Configure network backend
sudo nano /etc/sane.d/net.conf
# Add:
# localhost

# 4. Copy SANE configs for scanbd's use
sudo cp -r /etc/sane.d /etc/scanbd/

# 5. Restore real backend for scanbd
sudo nano /etc/scanbd/sane.d/dll.conf
# Uncomment: canon_dr
# Comment out: net

# 6. Create scan trigger script
sudo tee /etc/scanbd/scan.sh > /dev/null << 'EOF'
#!/bin/bash
logger -t "scanbd" "Scan button pressed - triggering piscan"
curl -X POST -H "Content-Type: application/json" http://localhost:5000/scan
EOF

sudo chmod +x /etc/scanbd/scan.sh

# 7. Configure scanbd action
sudo nano /etc/scanbd/scanbd.conf
# Add or modify the scan action:
# action scan {
#     filter = "^scan.*"
#     numerical-trigger {
#         from-value = 1
#         to-value   = 0
#     }
#     desc = "Scan button pressed"
#     script = "/etc/scanbd/scan.sh"
# }

# 8. Enable and start scanbd
sudo systemctl enable scanbd
sudo systemctl start scanbd
```

**Testing Button Detection:**

```bash
# Test scanbd in foreground with debug output
sudo systemctl stop scanbd
sudo scanbd -f -d5

# Press the scan button and observe output
# Press Ctrl+C to stop

# Start scanbd normally
sudo systemctl start scanbd
```

**Note:** The setup script handles all of this automatically with interactive prompts.

## Usage

### Command Line Interface

#### Start HTTP Server

Run piscan as a service with HTTP API:

```bash
# Start server (foreground)
piscan server

# Start with debug mode
piscan server --debug

# Specify custom config
piscan --config /path/to/config.yaml server
```

#### Test Scan

Perform a test scan without starting the server:

```bash
# Interactive scan with prompts
piscan test-scan --interactive

# Quick scan with defaults
piscan test-scan

# Specify scan parameters
piscan test-scan --source ADF --resolution 300 --mode Color

# Scan and upload to API
piscan test-scan --upload

# Keep blank pages (don't skip)
piscan test-scan --no-skip-blank
```

#### Test Button Detection

Test which scanner buttons can be detected:

```bash
# Run button test for 60 seconds
piscan test-buttons --duration 60

# Press buttons on scanner during the test period
# Results will show detected button events and configuration recommendations
```

#### Show Scanner Information

Display scanner capabilities and status:

```bash
piscan info
```

### HTTP REST API

When running as a server, piscan exposes these endpoints:

#### POST /scan

Trigger a scan job.

```bash
# Basic scan
curl -X POST http://localhost:5000/scan

# Scan with parameters
curl -X POST http://localhost:5000/scan \
  -H "Content-Type: application/json" \
  -d '{
    "source": "ADF",
    "doc_id": "2025-12-08-1234",
    "metadata": {"author": "John Doe"},
    "document_type": "invoice",
    "properties": {"priority": "high"}
  }'
```

**Response:**
```json
{
  "status": "started",
  "message": "Scan job started"
}
```

#### GET /status

Get current scanner status.

```bash
curl http://localhost:5000/status
```

**Response:**
```json
{
  "scanning": false,
  "scanner_available": true,
  "last_scan": {
    "timestamp": 1702040123.45,
    "duration": 12.3,
    "pages_scanned": 5,
    "doc_id": "2025-12-08-12:34-A1B2C",
    "success": true
  },
  "server_time": 1702040200.0
}
```

#### GET /logs

View recent log entries.

```bash
# Get last 100 lines (default)
curl http://localhost:5000/logs

# Get last 50 lines
curl "http://localhost:5000/logs?lines=50"

# Filter by log level
curl "http://localhost:5000/logs?level=ERROR"

# Get as JSON
curl "http://localhost:5000/logs?format=json"
```

#### GET /scanner/info

Get scanner information and capabilities.

```bash
curl http://localhost:5000/scanner/info
```

#### GET /config

View current configuration (safe values only, token hidden).

```bash
curl http://localhost:5000/config
```

#### GET /health

Health check endpoint.

```bash
curl http://localhost:5000/health
```

### Running as a System Service

To run piscan automatically on boot:

```bash
# Create systemd service file
sudo tee /etc/systemd/system/piscan.service > /dev/null << 'EOF'
[Unit]
Description=Piscan - Document Scanner Service
After=network.target scanbd.service
Wants=scanbd.service

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/piscan
ExecStart=/usr/local/bin/piscan --config /home/pi/.piscan/config.yaml server
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable piscan
sudo systemctl start piscan

# Check status
sudo systemctl status piscan

# View logs
sudo journalctl -u piscan -f
```

## Workflow

### Typical Scanning Process

1. **User loads documents** into scanner's ADF or places on flatbed
2. **User presses** physical scan button OR triggers via HTTP API
3. **Piscan receives trigger** (from scanbd or HTTP)
4. **Creates timestamped directory** (e.g., `/tmp/2025-12-08-123456/`)
5. **Scans all pages** using configured settings
6. **Analyzes each page** for blank page detection
7. **Filters out blank pages** (if enabled)
8. **Uploads to API** with authentication
9. **Cleans up** temporary files on success
10. **Moves to failed directory** if upload fails (for retry)

### Document ID Generation

If no document ID is provided, piscan auto-generates one in the format:
```
YYYY-MM-DD-HH:MM-XXXXX
```

Where `XXXXX` is a 5-character hash for uniqueness.

### Failed Job Handling

Failed scans are stored in the configured `failed_dir` (default: `/tmp/failed/`) with:
- Original scanned images
- `error.txt` file with error details and timestamp

These can be manually inspected or retried.

## Configuration Reference

### Scanner Settings

- `device`: Scanner device string (empty for auto-detect)
- `resolution`: Scan resolution in DPI (150, 300, 600)
- `mode`: Color mode (Color, Gray, Lineart)
- `source`: Scan source (Auto, ADF, Flatbed)
- `format`: Output format (png, jpeg, tiff)

### API Settings

- `workspace`: API workspace identifier
- `url`: Base API URL
- `token`: Bearer token for authentication
- `timeout`: HTTP request timeout in seconds

### Storage Settings

- `temp_dir`: Temporary directory for scans
- `failed_dir`: Directory for failed jobs
- `keep_failed`: Whether to keep failed scans (true/false)

### Processing Settings

- `skip_blank`: Enable blank page detection (true/false)
- `blank_threshold`: Non-white pixel ratio threshold (0.0-1.0)
- `white_threshold`: Pixel brightness threshold (0-255)

### Server Settings

- `host`: Server bind address (0.0.0.0 = all interfaces)
- `port`: HTTP server port
- `debug`: Flask debug mode (true/false)

### Logging Settings

- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `file`: Log file path
- `max_size`: Maximum log file size in bytes
- `backup_count`: Number of rotated log files to keep

## Troubleshooting

### Scanner Not Detected

```bash
# Check USB connection
lsusb | grep Canon

# Check SANE detection
scanimage -L

# Check permissions
ls -l /dev/bus/usb/*/*
sudo usermod -a -G scanner $USER

# Reboot or re-login after group change
```

### Scanner Not Working with scanbd

```bash
# Verify SANE configuration
cat /etc/sane.d/dll.conf  # Should only have: net
cat /etc/sane.d/net.conf  # Should have: localhost

# Verify scanbd SANE configuration  
cat /etc/scanbd/sane.d/dll.conf  # Should have: canon_dr

# Test with network backend
scanimage -d net:localhost:canon_dr:libusb:001:002 --test

# Check scanbd status
sudo systemctl status scanbd
sudo journalctl -u scanbd -f
```

### Button Not Triggering Scans

```bash
# Test scanbd in foreground
sudo systemctl stop scanbd
sudo scanbd -f -d7

# Press button and check output
# Should see action triggered

# Verify trigger script
sudo /etc/scanbd/scan.sh

# Check piscan is running
curl http://localhost:5000/health
```

### Upload Failures

```bash
# Check configuration
piscan --config ~/.piscan/config.yaml info

# Test API connectivity
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-api-server/default/api/

# Check logs
tail -f /var/log/piscan.log

# Check failed directory
ls -la /tmp/failed/
```

### Permission Issues

```bash
# Scanner permissions
sudo usermod -a -G scanner,lp $USER

# Log file permissions
sudo touch /var/log/piscan.log
sudo chown $USER:$USER /var/log/piscan.log

# Temp directory permissions
sudo mkdir -p /tmp/piscan
sudo chown $USER:$USER /tmp/piscan
```

## Development

### Project Structure

```
piscan/
├── piscan/
│   ├── __init__.py
│   ├── cli.py              # CLI interface and orchestration
│   ├── config.py           # Configuration management
│   ├── scanner.py          # SANE/scanimage interface
│   ├── file_manager.py     # File and directory management
│   ├── blank_detector.py   # Blank page detection
│   ├── uploader.py         # HTTP upload functionality
│   ├── server.py           # Flask HTTP server
│   ├── logger.py           # Logging configuration
│   ├── button_detector.py  # Button detection testing
│   └── test_scan.py        # Test scan functionality
├── config.yaml             # Example configuration
├── requirements.txt        # Python dependencies
├── setup.py               # Package setup
├── README.md              # This file
├── INSTALL.md             # Installation guide
└── SPEC.md                # Original specification
```

### Running Tests

```bash
# Test scan without upload
python3 -m piscan.cli test-scan --no-upload

# Test with specific parameters
python3 -m piscan.cli test-scan --source ADF --resolution 150

# Test button detection
python3 -m piscan.cli test-buttons --duration 30
```

### Debugging

Enable debug logging in config.yaml:

```yaml
logging:
  level: "DEBUG"
```

Or via command line:

```bash
piscan --log-level DEBUG server
```

Run scanner commands manually:

```bash
# List devices
scanimage -L

# Show all options
scanimage -A

# Test scan
scanimage --test

# Single page scan
scanimage --resolution 300 --mode Color > test.pnm
```

## API Upload Specification

The application uploads scanned documents to the configured API endpoint using HTTP multipart/form-data with the following structure:

**Endpoint:** `POST {api_url}/{workspace}/api/document/{doc_id}`

**Headers:**
- `Authorization: Bearer {token}`

**Form Data:**
- `files`: Multiple image files (field name repeated for each file)
- `meta`: JSON string with document metadata (optional)
- `documentType`: Document type identifier (optional)
- `properties`: JSON string with document properties (optional)

**Example Request:**

```bash
curl -X POST \
  http://api.example.com/default/api/document/2025-12-08-1234-ABC12 \
  -H "Authorization: Bearer your-token-here" \
  -F "files=@page_001.png" \
  -F "files=@page_002.png" \
  -F "files=@page_003.png" \
  -F 'meta={"author":"Scanner","source":"ADF"}' \
  -F "documentType=scanned"
```

**Expected Response:**

```json
{
  "docId": "2025-12-08-1234-ABC12",
  "pagesAdded": 3,
  "totalPages": 3,
  "status": "success"
}
```

## Credits

Piscan was developed based on the comprehensive specification in SPEC.md, implementing a full-featured document scanning automation system for Raspberry Pi with Canon DR-F120 scanner support.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
- Check the Troubleshooting section above
- Review logs: `tail -f /var/log/piscan.log`
- Test scanner: `piscan info`
- Test configuration: `piscan test-scan --interactive`
