#!/bin/bash
# Backup SANE and scanbd configuration files

BACKUP_DIR="/opt/piscan/backups/etc"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CURRENT_BACKUP="$BACKUP_DIR/$TIMESTAMP"

echo "Creating config backup in $CURRENT_BACKUP..."
mkdir -p "$CURRENT_BACKUP"

# Backup SANE configs
if [ -d "/etc/sane.d" ]; then
    mkdir -p "$CURRENT_BACKUP/sane.d"
    cp -r /etc/sane.d/* "$CURRENT_BACKUP/sane.d/"
    echo "✓ Backed up /etc/sane.d"
fi

# Backup scanbd configs
if [ -d "/etc/scanbd" ]; then
    mkdir -p "$CURRENT_BACKUP/scanbd"
    cp -r /etc/scanbd/* "$CURRENT_BACKUP/scanbd/"
    echo "✓ Backed up /etc/scanbd"
fi

# Backup default/saned
if [ -f "/etc/default/saned" ]; then
    mkdir -p "$CURRENT_BACKUP/default"
    cp /etc/default/saned "$CURRENT_BACKUP/default/"
    echo "✓ Backed up /etc/default/saned"
fi

# Backup init script if modified
if [ -f "/etc/init.d/scanbd" ]; then
    mkdir -p "$CURRENT_BACKUP/init.d"
    cp /etc/init.d/scanbd "$CURRENT_BACKUP/init.d/"
    echo "✓ Backed up /etc/init.d/scanbd"
fi

# Backup udev rules
if [ -f "/etc/udev/rules.d/99-saned.rules" ]; then
    mkdir -p "$CURRENT_BACKUP/udev"
    cp /etc/udev/rules.d/99-saned.rules "$CURRENT_BACKUP/udev/"
    echo "✓ Backed up udev rules"
fi

echo "Backup complete!"
