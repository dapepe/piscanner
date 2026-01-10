#!/usr/bin/env python3
"""Simple standalone scanner script."""

import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from piscan.config import Config
from piscan.scanner import Scanner, ScannerError
from piscan.uploader import Uploader, UploadError
from piscan.file_manager import FileManager
from piscan.blank_detector import BlankPageDetector
from piscan.sound_player import SoundPlayer


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def scan_document(config, source=None, format_type=None, debug=False, max_pages=None):
    """Scan a document and upload to API."""
    
    sound_player = None
    
    if source:
        config.set('scanner.source', source)
    if format_type:
        config.set('scanner.format', format_type)
    
    file_manager = FileManager(config)
    scan_dir = file_manager.create_scan_directory()
    
    if debug:
        print(f"Scan directory: {scan_dir}")
        print(f"Max pages: {max_pages}")
        print(f"Color correction: {config.scanner_color_correction}")
        print(f"Upload compression: {config.upload_compression}")
        print(f"ZIP bundle size: {config.upload_zip_bundle_size}")
        print(f"ZIP bundle max bytes: {config.upload_zip_bundle_max_bytes}")
        print(f"Auto JPEG threshold: {config.upload_auto_jpeg_threshold}")
        print(f"Auto JPEG page bytes: {config.upload_auto_jpeg_page_size_bytes}")
    
    try:
        uploader = Uploader(config)
        scanner = Scanner(config, uploader=uploader)
        blank_detector = BlankPageDetector(config)
        sound_player = SoundPlayer(config)
        
        if debug:
            print(f"Scanner device: {scanner.device}")
            print(f"Scanner source: {config.scanner_source}")
            print(f"Scanner mode: {config.scanner_mode}")
        
        compression_mode = config.upload_compression
        bundle_size = config.upload_zip_bundle_size
        bundle_max_bytes = config.upload_zip_bundle_max_bytes

        if compression_mode == 'zip':
            if bundle_size > 0 or bundle_max_bytes > 0:
                parts = []
                if bundle_size > 0:
                    parts.append(f"{bundle_size} pages")
                if bundle_max_bytes > 0:
                    parts.append(_format_size(bundle_max_bytes))
                print(f"Scanning with ZIP bundling ({', '.join(parts)})...")
            else:
                print("Scanning pages (ZIP upload at end)...")
        else:
            print("Scanning and uploading pages as they complete...")

        processed_files = []
        doc_id = None
        uploaded_pages = 0

        def page_callback(page_num, file_path):
            """Called when each page is ready."""
            nonlocal doc_id, uploaded_pages

            if debug:
                print(f"[Callback] Page {page_num} ready: {file_path}")

            # Skip blank pages early (also removes the file)
            if config.skip_blank and blank_detector.is_blank(file_path):
                if debug:
                    print(f"[Callback] Page {page_num} is blank, removing")
                blank_detector.remove_blank_files([file_path])
                return

            file_size = os.path.getsize(file_path)
            if debug:
                print(f"[Callback] Page {page_num} size: {_format_size(file_size)}")

            if compression_mode == 'zip':
                processed_files.append(file_path)
                return

            # individual upload: create document with page 1 and append
            try:
                if page_num == 1:
                    result = uploader.upload_document([file_path])
                    doc_id = result.get('doc_id')
                    uploaded_pages = 1
                    print(f"Page 1 uploaded ({_format_size(file_size)}, ID: {doc_id})")
                else:
                    if not doc_id:
                        raise Exception("No document ID for appending")
                    uploader._append_pages(doc_id, [file_path])
                    uploaded_pages += 1
                    print(f"Page {page_num} uploaded ({_format_size(file_size)})")
            except Exception as e:
                print(f"Error uploading page {page_num}: {e}")

        scanned_files = scanner.scan_pages(
            scan_dir,
            source=config.scanner_source,
            page_callback=page_callback,
            max_pages=max_pages
        )

        if debug:
            print(f"[Scan] Total pages scanned: {len(scanned_files)}")

        if not scanned_files:
            print("Error: No pages scanned. Load paper in feeder.")
            sys.exit(1)

        if compression_mode == 'zip':
            final_files = processed_files
            if not final_files:
                print("Error: All pages were blank or removed.")
                sys.exit(1)

            print(f"Uploading {len(final_files)} pages as ZIP...")
            result = uploader.upload_document(final_files)
            doc_id = result.get('doc_id')
            bundles = result.get('bundles', 1)
            payload = result.get('payload_human')
            if payload:
                print(f"ZIP uploaded ({len(final_files)} pages, {bundles} bundle(s), {payload}, ID: {doc_id})")
            else:
                print(f"ZIP uploaded ({len(final_files)} pages, {bundles} bundle(s), ID: {doc_id})")

        print(f"Scan complete - {len(scanned_files)} pages processed")
        sound_player.play_success()
        
        for filepath in scanned_files:
            if os.path.exists(filepath):
                os.remove(filepath)
        if os.path.exists(scan_dir):
            os.rmdir(scan_dir)
            
    except ScannerError as e:
        print(f"Error: {e}")
        if sound_player:
            sound_player.play_error()
        if debug:
            import traceback
            traceback.print_exc()
        if os.path.exists(scan_dir):
            for f in os.listdir(scan_dir):
                os.remove(os.path.join(scan_dir, f))
            os.rmdir(scan_dir)
        sys.exit(1)
        
    except UploadError as e:
        print(f"Error: {e}")
        if sound_player:
            sound_player.play_error()
        if debug:
            import traceback
            traceback.print_exc()
        if os.path.exists(scan_dir):
            for f in os.listdir(scan_dir):
                os.remove(os.path.join(scan_dir, f))
            os.rmdir(scan_dir)
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nCancelled")
        if os.path.exists(scan_dir):
            for f in os.listdir(scan_dir):
                os.remove(os.path.join(scan_dir, f))
            os.rmdir(scan_dir)
        sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}")
        if sound_player:
            sound_player.play_error()
        if debug:
            import traceback
            traceback.print_exc()
        if os.path.exists(scan_dir):
            for f in os.listdir(scan_dir):
                os.remove(os.path.join(scan_dir, f))
            os.rmdir(scan_dir)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Scan documents and upload to API')
    parser.add_argument('--source', help='Scan source (e.g., "ADF Duplex", "ADF Front", "Flatbed")')
    parser.add_argument('--format', dest='format_type', help='Output format (jpeg, png, tiff)')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    parser.add_argument('--config', help='Path to config file (default: ./config/config.yaml)')
    parser.add_argument('--pages', type=int, help='Maximum number of pages to scan')
    
    args = parser.parse_args()
    
    try:
        # Load config
        config_path = args.config or './config/config.yaml'
        config = Config(config_path)
        
        # Run scan
        scan_document(config, args.source, args.format_type, args.debug, args.pages)
        
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
