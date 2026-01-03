#!/bin/bash
set -e

# Piscan Simple Button Setup
# Replaces scanbd with a lightweight Python monitor

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

echo "Disabling old scanbd service..."
systemctl stop scanbd 2>/dev/null || true
systemctl disable scanbd 2>/dev/null || true

# Restore system default SANE config to be safe
if [ -f /etc/sane.d/dll.conf.bak ]; then
    cp /etc/sane.d/dll.conf.bak /etc/sane.d/dll.conf
else
    # Ensure standard backends are enabled if no backup
    # (Just basic reset, mostly we want to ensure 'canon_dr' is enabled)
    if ! grep -q "^canon_dr" /etc/sane.d/dll.conf; then
        echo "canon_dr" >> /etc/sane.d/dll.conf
    fi
fi

# Create systemd service for our Python monitor
echo "Creating piscan-button.service..."
cat > /etc/systemd/system/piscan-button.service << 'EOF'
[Unit]
Description=Piscan Button Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/piscan
ExecStart=/usr/bin/python3 -u /opt/piscan/scripts/button_monitor.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/piscan-button.log
StandardError=inherit

[Install]
WantedBy=multi-user.target
EOF

# Setup log file
touch /var/log/piscan-button.log
chmod 644 /var/log/piscan-button.log

# Reload and start
echo "Starting new service..."
systemctl daemon-reload
systemctl enable piscan-button
systemctl start piscan-button

echo "Done! Button monitor is running."
echo "Logs: tail -f /var/log/piscan-button.log"
