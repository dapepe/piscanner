#!/usr/bin/env python3
"""Simple standalone scanner script."""

import os
import sys
import subprocess
import yaml
import argparse
import time
import re
from datetime import datetime

def load_config():
    """Load configuration from config.yaml."""
    config_path = "/opt/piscan/config/config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def scan_document(config, source=None, format_type=None, debug=False):
    """Scan a document and upload to API."""
    
    # Get settings
    device = config['scanner']['device']
    resolution = config['scanner']['resolution']
    mode = config['scanner']['mode']
    source = source or config['scanner']['source']
    format_type = format_type or config['scanner']['format']
    
    api_url = config['api']['url']
    api_workspace = config['api']['workspace']
    api_token = config['api']['token']
    
    # Create temp directory
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    scan_dir = f"/tmp/{timestamp}"
    os.makedirs(scan_dir, exist_ok=True)
    
    if debug:
        print(f"Scan directory: {scan_dir}")
    
    # Map format to extension
    format_ext = 'jpg' if format_type == 'jpeg' else format_type
    
    # Build scanimage command
    batch_file = os.path.join(scan_dir, f"page_%03d.{format_ext}")
    
    cmd = [
        'scanimage',
        '-d', device,
        '--resolution', str(resolution),
        '--mode', mode,
        '--source', source,
        f'--format={format_type}',
        f'--batch={batch_file}'
    ]
    
    if debug:
        print(f"Command: {' '.join(cmd)}")
    
    print("Scanning...")
    
    # Run scan
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if debug:
        print(f"Scan output: {result.stdout}")
        print(f"Scan errors: {result.stderr}")
    
    # Find scanned files first - if we have files, the scan worked
    scanned_files = []
    for filename in sorted(os.listdir(scan_dir)):
        if filename.startswith('page_') and filename.endswith(f'.{format_ext}'):
            scanned_files.append(os.path.join(scan_dir, filename))
    
    # Check for actual errors - only fail if no files were created AND there was an error
    if not scanned_files:
        output = (result.stdout + result.stderr).lower()
        if result.returncode != 0:
            print(f"Error: Scan failed - {result.stderr}")
            sys.exit(1)
        elif 'invalid argument' in output:
            print(f"Error: Scanner configuration error - {result.stderr}")
            sys.exit(1)
        else:
            print("Error: No pages were scanned. Please load paper in the document feeder.")
            sys.exit(1)
    
    print(f"Scanned {len(scanned_files)} pages")
    
    # Upload to API
    import requests
    
    endpoint = f"{api_url}/{api_workspace}/api/document/"
    
    if debug:
        print(f"Uploading to: {endpoint}")
    
    files = []
    for filepath in scanned_files:
        filename = os.path.basename(filepath)
        files.append(('files', (filename, open(filepath, 'rb'), 'image/jpeg')))
    
    headers = {'Authorization': f'Bearer {api_token}'}
    
    print("Uploading...")
    response = requests.post(endpoint, files=files, headers=headers, timeout=60)
    
    # Close file handles
    for _, (_, f, _) in files:
        f.close()
    
    # Clean up
    for filepath in scanned_files:
        os.remove(filepath)
    os.rmdir(scan_dir)
    
    if response.status_code in [200, 201]:
        print("✓ Upload successful")
        try:
            result = response.json()
            if 'docId' in result:
                print(f"Document ID: {result['docId']}")
        except:
            pass
    else:
        print(f"Error: Upload failed - HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Scan documents and upload to API')
    parser.add_argument('--source', help='Scan source (e.g., "ADF Duplex", "ADF Front", "Flatbed")')
    parser.add_argument('--format', dest='format_type', help='Output format (jpeg, png, tiff)')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    
    args = parser.parse_args()
    
    try:
        config = load_config()
        scan_document(config, args.source, args.format_type, args.debug)
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
