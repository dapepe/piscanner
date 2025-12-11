"""Main CLI entry point for piscan."""

import argparse
import os
import sys
import signal
import threading
import time
from typing import Optional

# Import components with fallbacks
Config = None
Logger = None
Scanner = None
ScannerError = Exception
FileManager = None
BlankPageDetector = None
Uploader = None
UploadError = Exception
ScanServer = None
TestScan = None
ButtonDetector = None

try:
    from .config import Config
except ImportError:
    pass

try:
    from .logger import Logger
except ImportError:
    pass

try:
    from .scanner import Scanner, ScannerError
except ImportError:
    pass

try:
    from .file_manager import FileManager
except ImportError:
    pass

try:
    from .blank_detector import BlankPageDetector
except ImportError:
    pass

try:
    from .uploader import Uploader, UploadError
except ImportError:
    pass

try:
    from .server import ScanServer
except ImportError:
    pass

try:
    from .test_scan import TestScan
except ImportError:
    pass

try:
    from .button_detector import ButtonDetector
except ImportError:
    pass


class ScanManager:
    """Main scan manager that coordinates all components."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize scan manager.
        
        Args:
            config_path: Optional path to configuration file
        """
        if Config is None:
            raise ImportError("Config module not available")
        if Logger is None:
            raise ImportError("Logger module not available")
        if Scanner is None:
            raise ImportError("Scanner module not available")
        if FileManager is None:
            raise ImportError("FileManager module not available")
        if BlankPageDetector is None:
            raise ImportError("BlankPageDetector module not available")
        if Uploader is None:
            raise ImportError("Uploader module not available")
        if ScanServer is None:
            raise ImportError("ScanServer module not available")
            
        self.config = Config(config_path)
        self.logger = Logger()
        
        # Initialize components
        self.scanner = Scanner(self.config)
        self.file_manager = FileManager(self.config)
        self.blank_detector = BlankPageDetector(self.config)
        self.uploader = Uploader(self.config)
        self.server = ScanServer(self.config, self)
        
        # State
        self.scanning = False
        self.last_scan_info = {}
        self.shutdown_event = threading.Event()
    
    def is_scanning(self) -> bool:
        """Check if currently scanning.
        
        Returns:
            True if scanning is in progress
        """
        return self.scanning
    
    def scanner_available(self) -> bool:
        """Check if scanner is available.
        
        Returns:
            True if scanner is available
        """
        return self.scanner.test_scanner()
    
    def get_last_scan_info(self) -> dict:
        """Get information about last scan.
        
        Returns:
            Dictionary with last scan info
        """
        return self.last_scan_info.copy()
    
    def perform_scan(self, source: Optional[str] = None, doc_id: Optional[str] = None,
                   metadata: Optional[dict] = None, document_type: Optional[str] = None,
                   properties: Optional[dict] = None, upload: bool = True, 
                   keep_files: bool = False) -> dict:
        """Perform a complete scan and upload workflow.
        
        Args:
            source: Scan source (ADF, Flatbed, Auto)
            doc_id: Optional document ID
            metadata: Optional document metadata
            document_type: Optional document type
            properties: Optional document properties
            upload: Whether to upload to API (default: True)
            keep_files: Whether to keep files after upload (default: False)
            
        Returns:
            Dictionary with scan result
        """
        if self.scanning:
            return {
                'success': False,
                'error': 'Scan already in progress'
            }
        
        self.scanning = True
        scan_start_time = time.time()
        
        try:
            self.logger.info("Starting scan job")
            
            # Create scan directory
            scan_dir = self.file_manager.create_scan_directory()
            
            # Scan pages
            scanned_files = self.scanner.scan_pages(scan_dir, source)
            
            if not scanned_files:
                raise Exception("No pages were scanned")
            
            # Filter blank pages
            if self.config.skip_blank:
                non_blank_files, blank_files = self.blank_detector.filter_blank_pages(scanned_files)
                self.blank_detector.remove_blank_files(blank_files)
                scanned_files = non_blank_files
            
            # Upload to API (if enabled)
            upload_result = {}
            if upload:
                upload_result = self.uploader.upload_document(
                    scanned_files, doc_id, metadata, document_type, properties
                )
            
            # Cleanup on success (unless keep_files is True)
            if not keep_files:
                self.file_manager.cleanup_directory(scan_dir)
            else:
                self.logger.info(f"Files kept in: {scan_dir}")
            
            # Update last scan info
            self.last_scan_info = {
                'timestamp': time.time(),
                'duration': time.time() - scan_start_time,
                'pages_scanned': len(scanned_files),
                'doc_id': upload_result.get('doc_id'),
                'success': True
            }
            
            self.logger.info(f"Scan job completed successfully: {self.last_scan_info}")
            
            result = {
                'success': True,
                'pages': len(scanned_files),
                'duration': time.time() - scan_start_time,
                'files': scanned_files
            }
            
            if upload_result:
                result['doc_id'] = upload_result.get('doc_id')
                result['upload_response'] = upload_result.get('response')
            
            if keep_files:
                result['scan_dir'] = scan_dir
            
            return result
            
        except Exception as e:
            self.logger.error(f"Scan job failed: {e}")
            
            # Move to failed directory
            scan_dir = locals().get('scan_dir')
            if scan_dir:
                self.file_manager.move_to_failed(scan_dir, str(e))
            
            # Update last scan info
            self.last_scan_info = {
                'timestamp': time.time(),
                'duration': time.time() - scan_start_time,
                'error': str(e),
                'success': False
            }
            
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - scan_start_time
            }
            
        finally:
            self.scanning = False
    
    def start_server(self):
        """Start the HTTP server."""
        self.server.start()
    
    def stop_server(self):
        """Stop the HTTP server."""
        self.server.stop()
    
    def shutdown(self):
        """Shutdown the scan manager."""
        self.logger.info("Shutting down piscan")
        self.shutdown_event.set()
        self.stop_server()


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description='Piscan - Raspberry Pi Canon DR-F120 Scanner Automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  piscan --config /etc/piscan/config.yaml
  piscan test-scan --source ADF --resolution 300
  piscan test-buttons --duration 60
  piscan server --debug
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Override log level'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command (main scanning command)
    scan_parser = subparsers.add_parser('scan', help='Perform scan and upload to API')
    scan_parser.add_argument(
        '--source', 
        help='Scan source: Auto, ADF, Flatbed (or scanner-specific: "ADF Front", "ADF Duplex")'
    )
    scan_parser.add_argument(
        '--resolution', type=int,
        help='Scan resolution in DPI (default: from config)'
    )
    scan_parser.add_argument(
        '--mode', choices=['Color', 'Gray', 'Lineart'],
        help='Color mode (default: from config)'
    )
    scan_parser.add_argument(
        '--format', choices=['png', 'jpeg', 'tiff'],
        help='Output format (default: from config)'
    )
    scan_parser.add_argument(
        '--no-skip-blank', action='store_true',
        help='Do not skip blank pages'
    )
    scan_parser.add_argument(
        '--no-upload', action='store_true',
        help='Skip upload to API (just scan locally)'
    )
    scan_parser.add_argument(
        '--keep-files', action='store_true',
        help='Keep scanned files after upload'
    )
    scan_parser.add_argument(
        '--debug', action='store_true',
        help='Enable debug output'
    )
    
    # Server command
    server_parser = subparsers.add_parser('server', help='Start HTTP server')
    server_parser.add_argument(
        '--debug', action='store_true',
        help='Enable debug mode'
    )
    
    # Test scan command
    test_parser = subparsers.add_parser('test-scan', help='Run test scan')
    test_parser.add_argument(
        '--source',
        help='Scan source: Auto, ADF, Flatbed (or scanner-specific names)'
    )
    test_parser.add_argument(
        '--resolution', type=int,
        help='Scan resolution (DPI)'
    )
    test_parser.add_argument(
        '--mode', choices=['Color', 'Gray', 'Lineart'],
        help='Color mode'
    )
    test_parser.add_argument(
        '--format', choices=['png', 'jpeg', 'tiff'],
        help='Output format'
    )
    test_parser.add_argument(
        '--no-skip-blank', action='store_true',
        help='Do not skip blank pages'
    )
    test_parser.add_argument(
        '--upload', action='store_true',
        help='Upload scanned files to API'
    )
    test_parser.add_argument(
        '--interactive', '-i', action='store_true',
        help='Interactive mode with prompts'
    )
    
    # Test buttons command
    buttons_parser = subparsers.add_parser('test-buttons', help='Test button detection')
    buttons_parser.add_argument(
        '--duration', type=int, default=30,
        help='Test duration in seconds (default: 30)'
    )
    
    # Scanner info command
    info_parser = subparsers.add_parser('info', help='Show scanner information')
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set up signal handlers
    def signal_handler(sig, frame):
        print("\nShutting down piscan...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize scan manager
        scan_manager = ScanManager(args.config)
        
        # Override log level if specified
        if args.log_level:
            scan_manager.config.set('logging.level', args.log_level)
        
        # Handle commands
        if args.command == 'scan':
            # Set log level and debug mode based on debug flag
            if hasattr(args, 'debug') and args.debug:
                os.environ['PISCAN_DEBUG'] = '1'
                scan_manager.config.set('logging.level', 'DEBUG')
                scan_manager.logger._setup_logger(scan_manager.config)
            else:
                os.environ.pop('PISCAN_DEBUG', None)
                # Disable console logging - only log to file
                scan_manager.config.set('logging.level', 'ERROR')
                scan_manager.logger._setup_logger(scan_manager.config)
                # Remove console handler to suppress all console output
                logger = scan_manager.logger.get_logger()
                logger.handlers = [h for h in logger.handlers if not isinstance(h, __import__('logging').StreamHandler)]
            
            print("=== Starting Scan Job ===")
            
            # Apply overrides from command line
            if args.source:
                scan_manager.config.set('scanner.source', args.source)
            if args.resolution:
                scan_manager.config.set('scanner.resolution', args.resolution)
            if args.mode:
                scan_manager.config.set('scanner.mode', args.mode)
            if args.format:
                scan_manager.config.set('scanner.format', args.format)
            if args.no_skip_blank:
                scan_manager.config.set('processing.skip_blank', False)
            
            # Show configuration
            print(f"Scanner: {scan_manager.config.scanner_device or 'auto-detect'}")
            print(f"Source: {scan_manager.config.scanner_source}")
            print(f"Resolution: {scan_manager.config.scanner_resolution} DPI")
            print(f"Mode: {scan_manager.config.scanner_mode}")
            print(f"Format: {scan_manager.config.scanner_format}")
            print(f"Skip blank pages: {scan_manager.config.skip_blank}")
            
            if not args.no_upload:
                print(f"API URL: {scan_manager.config.api_url}/{scan_manager.config.api_workspace}/api/document/")
                print(f"API Token: {'*' * 20}...{scan_manager.config.api_token[-8:]}" if scan_manager.config.api_token else "API Token: (not configured)")
            else:
                print("Upload: DISABLED")
            
            print("\nStarting scan...")
            
            # Perform scan
            result = scan_manager.perform_scan(
                source=args.source,
                upload=not args.no_upload,
                keep_files=args.keep_files
            )
            
            if result['success']:
                print(f"\n=== Scan Successful ===")
                print(f"Pages scanned: {result['pages']}")
                print(f"Duration: {result['duration']:.1f}s")
                
                if not args.no_upload and 'doc_id' in result:
                    print(f"Document ID: {result['doc_id']}")
                    print(f"Uploaded to: {scan_manager.config.api_url}/{scan_manager.config.api_workspace}/api/document/")
                
                if args.keep_files and 'scan_dir' in result:
                    print(f"\nFiles saved to: {result['scan_dir']}")
                    print("File list:")
                    for f in result.get('files', []):
                        print(f"  - {f}")
                
                sys.exit(0)
            else:
                print(f"\n=== Scan Failed ===")
                print(f"Error: {result.get('error', 'Unknown error')}")
                print(f"Duration: {result.get('duration', 0):.1f}s")
                sys.exit(1)
        
        elif args.command == 'server':
            print(f"Starting piscan server on {scan_manager.config.server_host}:{scan_manager.config.server_port}")
            if args.debug:
                scan_manager.config.set('server.debug', True)
            
            scan_manager.start_server()
            
            # Keep running until shutdown
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down server...")
                scan_manager.shutdown()
        
        elif args.command == 'test-scan':
            if TestScan is None:
                print("Error: TestScan module not available")
                sys.exit(1)
                
            test_scan = TestScan(args.config)
            
            if args.interactive:
                success = test_scan.interactive_scan()
            else:
                # Prepare CLI args
                class Args:
                    def __init__(self):
                        self.source = args.source
                        self.resolution = args.resolution
                        self.mode = args.mode
                        self.format = args.format
                        self.skip_blank = not args.no_skip_blank
                        self.upload = args.upload
                
                success = test_scan.cli_scan(Args())
            
            sys.exit(0 if success else 1)
        
        elif args.command == 'test-buttons':
            if ButtonDetector is None:
                print("Error: ButtonDetector module not available")
                sys.exit(1)
                
            button_detector = ButtonDetector(scan_manager.config)
            result = button_detector.test_buttons(args.duration)
            
            print("\n=== Button Detection Results ===")
            if result['buttons_detected']:
                print(f"Detected {len(result['buttons_detected'])} button events:")
                for button in result['buttons_detected']:
                    print(f"  - {button}")
            else:
                print("No button events detected")
            
            print("\n=== Recommendations ===")
            for rec in result['recommendations']:
                print(f"  • {rec}")
            
            if 'scanbd_setup' in result:
                print("\n=== scanbd Setup Information ===")
                print("To enable button detection, install and configure scanbd:")
                print(f"  Install: {result['scanbd_setup']['install']}")
                print(f"  Config: {result['scanbd_setup']['config_file']}")
        
        elif args.command == 'info':
            scanner_info = scan_manager.scanner.get_scanner_info()
            
            print("=== Scanner Information ===")
            print(f"Device: {scanner_info.get('device', 'Unknown')}")
            print(f"Status: {scanner_info.get('status', 'Unknown')}")
            
            if 'resolutions' in scanner_info:
                print(f"Resolutions: {scanner_info['resolutions']}")
            if 'modes' in scanner_info:
                print(f"Modes: {scanner_info['modes']}")
            if 'sources' in scanner_info:
                print(f"Sources: {scanner_info['sources']}")
            
            if 'error' in scanner_info:
                print(f"Error: {scanner_info['error']}")
        
        else:
            # No command specified, show help
            parser.print_help()
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()