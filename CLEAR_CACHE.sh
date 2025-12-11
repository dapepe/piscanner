#!/bin/bash
# Clear all Python bytecode cache to ensure fresh config loading

echo "Clearing Python cache..."
cd /opt/piscan

# Remove all __pycache__ directories
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Remove all .pyc files
find . -name "*.pyc" -delete 2>/dev/null

# Remove all .pyo files  
find . -name "*.pyo" -delete 2>/dev/null

# Reinstall package
.venv/bin/pip install -e . --force-reinstall --no-deps > /dev/null 2>&1

echo "✓ Cache cleared and package reinstalled"
echo ""
echo "Now you can run: .venv/bin/piscan scan --source \"ADF Duplex\" --format jpeg"
