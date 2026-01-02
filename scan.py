#!/usr/bin/env python3
"""Simple standalone scanner script."""

import os
import sys
import argparse
from datetime import datetime

# Add piscan module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from piscan.config import Config
from piscan.scanner import Scanner, ScannerError
from piscan.uploader import Uploader, UploadError
from piscan.file_manager import FileManager
from piscan.sound_player import SoundPlayer


def scan_document(config, source=None, format_type=None, debug=False):
    """Scan a document and upload to API."""
    
    # Override config with command-line arguments
    if source:
        config.set('scanner.source', source)
    if format_type:
        config.set('scanner.format', format_type)
    
    # Create temp directory via FileManager (also runs retention cleanup)
    file_manager = FileManager(config)
    scan_dir = file_manager.create_scan_directory()
    
    if debug:
        print(f"Scan directory: {scan_dir}")
        print(f"Color correction: {config.scanner_color_correction}")
        print(f"Upload compression: {config.upload_compression}")
    
    try:
        # Initialize components
        uploader = Uploader(config)
        scanner = Scanner(config, uploader=uploader)
        # file_manager already created above to make scan_dir
        
        if debug:
            print(f"Scanner device: {scanner.device}")
            print(f"Scanner source: {config.scanner_source}")
            print(f"Scanner mode: {config.scanner_mode}")
        
        sound_player = SoundPlayer(config)

        compression_mode = config.upload_compression
        if compression_mode == 'zip':
            print("Scanning pages (ZIP upload at end)...")
        else:
            print("Scanning and uploading pages as they complete...")

        # Track upload progress
        doc_id = None
        uploaded_pages = 0
        
        def page_callback(page_num, file_path):
            """Called when each page is ready."""
            nonlocal doc_id, uploaded_pages
            
            if debug:
                print(f"[Callback] Page {page_num} ready: {file_path}")
            
            try:
                if page_num == 1:
                    # Create document with first page
                    result = uploader.upload_document([file_path])
                    doc_id = result.get('doc_id')
                    uploaded_pages = 1
                    print(f"✓ Page 1 uploaded (Document ID: {doc_id})")
                else:
                    # Append page to existing document
                    if doc_id:
                        result = uploader._append_pages(doc_id, [file_path])
                        uploaded_pages += 1
                        print(f"✓ Page {page_num} uploaded")
                    else:
                        raise Exception("No document ID available for appending pages")
                    
            except Exception as e:
                print(f"Error uploading page {page_num}: {e}")
                raise
        
        # Scan pages
        if compression_mode == 'zip':
            scanned_files = scanner.scan_pages(
                scan_dir,
                source=config.scanner_source,
                page_callback=None
            )
        else:
            scanned_files = scanner.scan_pages(
                scan_dir,
                source=config.scanner_source,
                page_callback=page_callback
            )
        
        if debug:
            print(f"\n[Scan] Total pages scanned: {len(scanned_files)}")
        
        if not scanned_files:
            print("Error: No pages were scanned. Please load paper in the document feeder.")
            sys.exit(1)
        
        # If ZIP mode, upload once at the end
        if compression_mode == 'zip':
            result = uploader.upload_document(scanned_files)
            doc_id = result.get('doc_id')
            print(f"✓ Uploaded ZIP (Document ID: {doc_id})")

        print(f"\n✓ Scan and upload complete - {len(scanned_files)} pages processed")

        # Play success sound after transfer completes
        sound_player.play_success()
        
        # Clean up
        for filepath in scanned_files:
            if os.path.exists(filepath):
                os.remove(filepath)
        if os.path.exists(scan_dir):
            os.rmdir(scan_dir)
            
    except ScannerError as e:
        print(f"Error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        # Clean up
        if os.path.exists(scan_dir):
            for filename in os.listdir(scan_dir):
                os.remove(os.path.join(scan_dir, filename))
            os.rmdir(scan_dir)
        sys.exit(1)
        
    except UploadError as e:
        print(f"Error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        # Clean up
        if os.path.exists(scan_dir):
            for filename in os.listdir(scan_dir):
                os.remove(os.path.join(scan_dir, filename))
            os.rmdir(scan_dir)
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nCancelled")
        # Clean up
        if os.path.exists(scan_dir):
            for filename in os.listdir(scan_dir):
                os.remove(os.path.join(scan_dir, filename))
            os.rmdir(scan_dir)
        sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        # Clean up
        if os.path.exists(scan_dir):
            for filename in os.listdir(scan_dir):
                os.remove(os.path.join(scan_dir, filename))
            os.rmdir(scan_dir)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Scan documents and upload to API')
    parser.add_argument('--source', help='Scan source (e.g., "ADF Duplex", "ADF Front", "Flatbed")')
    parser.add_argument('--format', dest='format_type', help='Output format (jpeg, png, tiff)')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    parser.add_argument('--config', help='Path to config file (default: ./config/config.yaml)')
    
    args = parser.parse_args()
    
    try:
        # Load config
        config_path = args.config or './config/config.yaml'
        config = Config(config_path)
        
        # Run scan
        scan_document(config, args.source, args.format_type, args.debug)
        
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
