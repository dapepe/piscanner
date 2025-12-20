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
    
    print("Scanning and uploading pages as they complete...")
    
    # Run scan in background and monitor for new files
    import threading
    import queue
    
    scan_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Queue to communicate between scanning monitor and uploader
    upload_queue = queue.Queue()
    scan_complete = threading.Event()
    upload_error = []
    scanned_files = []
    
    def monitor_scan_output():
        """Monitor scan directory for new files."""
        seen_files = set()
        scan_failed = False
        
        while not scan_complete.is_set() or scan_process.poll() is None:
            time.sleep(0.5)  # Check every 500ms
            
            # Look for new page files
            try:
                current_files = set()
                for filename in os.listdir(scan_dir):
                    if filename.startswith('page_') and filename.endswith(f'.{format_ext}'):
                        filepath = os.path.join(scan_dir, filename)
                        current_files.add(filepath)
                        
                        # New file detected
                        if filepath not in seen_files:
                            # Wait a bit to ensure file is fully written
                            time.sleep(0.2)
                            seen_files.add(filepath)
                            scanned_files.append(filepath)
                            upload_queue.put(filepath)
                            if debug:
                                print(f"[Scan] Page {len(scanned_files)} ready")
            except Exception as e:
                if debug:
                    print(f"[Scan] Error monitoring: {e}")
        
        # Signal that scanning is done
        upload_queue.put(None)
    
    def upload_pages():
        """Upload pages as they become available."""
        import requests
        headers = {'Authorization': f'Bearer {api_token}'}
        doc_id = None
        page_num = 0
        
        while True:
            filepath = upload_queue.get()
            
            if filepath is None:  # Scanning complete
                break
            
            page_num += 1
            
            try:
                if page_num == 1:
                    # Create document with first page
                    create_endpoint = f"{api_url}/{api_workspace}/api/document/"
                    if debug:
                        print(f"[Upload] Creating document with page 1")
                    
                    with open(filepath, 'rb') as f:
                        files = [('files', (os.path.basename(filepath), f, 'image/jpeg'))]
                        response = requests.post(create_endpoint, files=files, headers=headers, timeout=60)
                    
                    if response.status_code not in [200, 201]:
                        upload_error.append(f"Failed to create document - HTTP {response.status_code}: {response.text}")
                        scan_complete.set()
                        break
                    
                    result = response.json()
                    doc_id = result.get('docId')
                    if not doc_id:
                        upload_error.append("No document ID returned from server")
                        scan_complete.set()
                        break
                    
                    print(f"✓ Page 1 uploaded (Document ID: {doc_id})")
                else:
                    # Append subsequent pages
                    append_endpoint = f"{api_url}/{api_workspace}/api/document/{doc_id}"
                    if debug:
                        print(f"[Upload] Appending page {page_num}")
                    
                    with open(filepath, 'rb') as f:
                        files = [('files', (os.path.basename(filepath), f, 'image/jpeg'))]
                        response = requests.post(append_endpoint, files=files, headers=headers, timeout=60)
                    
                    if response.status_code not in [200, 201]:
                        upload_error.append(f"Failed to append page {page_num} - HTTP {response.status_code}: {response.text}")
                        scan_complete.set()
                        break
                    
                    print(f"✓ Page {page_num} uploaded")
                
            except Exception as e:
                upload_error.append(f"Upload error on page {page_num}: {e}")
                scan_complete.set()
                break
    
    # Start threads
    scan_thread = threading.Thread(target=monitor_scan_output, daemon=True)
    upload_thread = threading.Thread(target=upload_pages, daemon=True)
    
    scan_thread.start()
    upload_thread.start()
    
    # Wait for scan process to complete
    stdout, stderr = scan_process.communicate(timeout=300)
    
    if debug:
        print(f"\n[Scan] Output: {stdout}")
        print(f"[Scan] Errors: {stderr}")
    
    scan_complete.set()
    
    # Wait for upload thread to finish
    upload_thread.join(timeout=120)
    
    # Check for errors
    if upload_error:
        print(f"\nError: {upload_error[0]}")
        # Clean up
        for filepath in scanned_files:
            if os.path.exists(filepath):
                os.remove(filepath)
        if os.path.exists(scan_dir):
            os.rmdir(scan_dir)
        sys.exit(1)
    
    if not scanned_files:
        output = (stdout + stderr).lower()
        if scan_process.returncode != 0:
            print(f"Error: Scan failed - {stderr}")
            sys.exit(1)
        elif 'invalid argument' in output:
            print(f"Error: Scanner configuration error - {stderr}")
            sys.exit(1)
        else:
            print("Error: No pages were scanned. Please load paper in the document feeder.")
            sys.exit(1)
    
    print(f"\n✓ Scan and upload complete - {len(scanned_files)} pages processed")
    
    # Clean up
    for filepath in scanned_files:
        if os.path.exists(filepath):
            os.remove(filepath)
    if os.path.exists(scan_dir):
        os.rmdir(scan_dir)

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
