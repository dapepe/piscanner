"""Test scan command with interactive and CLI options."""

import sys
import os
import argparse
from typing import Optional, Dict, Any

# Simple logger fallback
class Logger:
    def info(self, msg, *args): print(f"INFO: {msg % args}")
    def error(self, msg, *args): print(f"ERROR: {msg % args}")
    def debug(self, msg, *args): print(f"DEBUG: {msg % args}")
    def warning(self, msg, *args): print(f"WARNING: {msg % args}")
    def exception(self, msg, *args): 
        print(f"EXCEPTION: {msg % args}")
        import traceback
        traceback.print_exc()

# Import components with fallbacks
Config = None
Scanner = None
ScannerError = Exception
FileManager = None
BlankPageDetector = None
Uploader = None
UploadError = Exception

try:
    from .config import Config
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


class TestScan:
    """Test scan functionality with interactive and CLI options."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize test scan.
        
        Args:
            config_path: Optional path to configuration file
        """
        if Config is None:
            raise ImportError("Config module not available")
        if Scanner is None:
            raise ImportError("Scanner module not available")
        if FileManager is None:
            raise ImportError("FileManager module not available")
        if BlankPageDetector is None:
            raise ImportError("BlankPageDetector module not available")
        if Uploader is None:
            raise ImportError("Uploader module not available")
            
        self.config = Config(config_path)
        self.logger = Logger()
        
        # Initialize components
        self.scanner = Scanner(self.config)
        self.file_manager = FileManager(self.config)
        self.blank_detector = BlankPageDetector(self.config)
        self.uploader = Uploader(self.config)
    
    def interactive_scan(self):
        """Run interactive scan with user prompts."""
        print("=== Piscan Interactive Test Scan ===")
        print()
        
        # Test scanner availability
        print("Testing scanner availability...")
        if not self.scanner.test_scanner():
            print("❌ Scanner not available or not responding")
            return False
        
        print("✅ Scanner is available")
        print()
        
        # Get scanner info
        scanner_info = self.scanner.get_scanner_info()
        print(f"Scanner device: {scanner_info.get('device', 'Unknown')}")
        print(f"Scanner status: {scanner_info.get('status', 'Unknown')}")
        
        if 'resolutions' in scanner_info:
            print(f"Available resolutions: {scanner_info['resolutions']}")
        if 'modes' in scanner_info:
            print(f"Available modes: {scanner_info['modes']}")
        if 'sources' in scanner_info:
            print(f"Available sources: {scanner_info['sources']}")
        print()
        
        # Interactive prompts
        source = self._prompt_source(scanner_info.get('sources', ''))
        resolution = self._prompt_resolution(scanner_info.get('resolutions', ''))
        mode = self._prompt_mode(scanner_info.get('modes', ''))
        format_type = self._prompt_format()
        skip_blank = self._prompt_skip_blank()
        upload = self._prompt_upload()
        
        print()
        print("=== Scan Configuration ===")
        print(f"Source: {source}")
        print(f"Resolution: {resolution}")
        print(f"Mode: {mode}")
        print(f"Format: {format_type}")
        print(f"Skip blank pages: {skip_blank}")
        print(f"Upload to API: {upload}")
        print()
        
        # Confirm scan
        if not self._confirm("Start scan with these settings?"):
            print("Scan cancelled")
            return False
        
        # Override config for this scan
        original_config = {
            'source': self.config.scanner_source,
            'resolution': self.config.scanner_resolution,
            'mode': self.config.scanner_mode,
            'format': self.config.scanner_format,
            'skip_blank': self.config.skip_blank
        }
        
        self.config.scanner_source = source
        self.config.scanner_resolution = resolution
        self.config.scanner_mode = mode
        self.config.scanner_format = format_type
        self.config.skip_blank = skip_blank
        
        try:
            # Perform scan
            result = self.perform_test_scan(upload)
            
            # Restore original config
            self.config.scanner_source = original_config['source']
            self.config.scanner_resolution = original_config['resolution']
            self.config.scanner_mode = original_config['mode']
            self.config.scanner_format = original_config['format']
            self.config.skip_blank = original_config['skip_blank']
            
            return result
            
        except Exception as e:
            # Restore original config on error
            self.config.scanner_source = original_config['source']
            self.config.scanner_resolution = original_config['resolution']
            self.config.scanner_mode = original_config['mode']
            self.config.scanner_format = original_config['format']
            self.config.skip_blank = original_config['skip_blank']
            
            self.logger.error(f"Test scan failed: {e}")
            print(f"❌ Scan failed: {e}")
            return False
    
    def cli_scan(self, args: argparse.Namespace):
        """Run scan with CLI arguments.
        
        Args:
            args: Parsed command line arguments
        """
        # Override config with CLI args
        if args.source:
            self.config.scanner_source = args.source
        if args.resolution:
            self.config.scanner_resolution = args.resolution
        if args.mode:
            self.config.scanner_mode = args.mode
        if args.format:
            self.config.scanner_format = args.format
        if args.skip_blank is not None:
            self.config.skip_blank = args.skip_blank
        
        print("=== Piscan CLI Test Scan ===")
        print(f"Source: {self.config.scanner_source}")
        print(f"Resolution: {self.config.scanner_resolution}")
        print(f"Mode: {self.config.scanner_mode}")
        print(f"Format: {self.config.scanner_format}")
        print(f"Skip blank pages: {self.config.skip_blank}")
        print(f"Upload to API: {args.upload}")
        print()
        
        try:
            return self.perform_test_scan(args.upload)
        except Exception as e:
            self.logger.error(f"CLI test scan failed: {e}")
            print(f"❌ Scan failed: {e}")
            return False
    
    def perform_test_scan(self, upload: bool = False) -> bool:
        """Perform the actual test scan.
        
        Args:
            upload: Whether to upload scanned files
            
        Returns:
            True if scan was successful
        """
        try:
            # Create scan directory
            scan_dir = self.file_manager.create_scan_directory()
            print(f"📁 Scan directory: {scan_dir}")
            
            # Scan pages
            print("📖 Scanning pages...")
            scanned_files = self.scanner.scan_pages(scan_dir)
            print(f"✅ Scanned {len(scanned_files)} pages")
            
            if not scanned_files:
                print("⚠️  No pages were scanned")
                return False
            
            # Detect blank pages
            if self.config.skip_blank:
                print("🔍 Detecting blank pages...")
                non_blank_files, blank_files = self.blank_detector.filter_blank_pages(scanned_files)
                
                if blank_files:
                    print(f"🗑️  Removing {len(blank_files)} blank pages")
                    self.blank_detector.remove_blank_files(blank_files)
                
                scanned_files = non_blank_files
                print(f"📄 {len(scanned_files)} non-blank pages remaining")
            
            # Show file information
            total_size = sum(os.path.getsize(f) for f in scanned_files if os.path.exists(f))
            print(f"📊 Total size: {total_size / 1024:.1f} KB")
            
            for i, file_path in enumerate(scanned_files, 1):
                size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                print(f"  📄 Page {i}: {os.path.basename(file_path)} ({size / 1024:.1f} KB)")
            
            # Upload if requested
            if upload:
                print("📤 Uploading to API...")
                try:
                    upload_result = self.uploader.upload_document(scanned_files)
                    print(f"✅ Upload successful!")
                    print(f"   Document ID: {upload_result.get('doc_id', 'Unknown')}")
                    print(f"   Pages added: {upload_result.get('pages_added', len(scanned_files))}")
                    print(f"   Total pages: {upload_result.get('total_pages', len(scanned_files))}")
                except UploadError as e:
                    print(f"❌ Upload failed: {e}")
                    # Move to failed directory
                    self.file_manager.move_to_failed(scan_dir, str(e))
                    return False
            
            # Cleanup on success
            if upload:
                self.file_manager.cleanup_directory(scan_dir)
                print("🧹 Temporary files cleaned up")
            
            print("✅ Test scan completed successfully!")
            return True
            
        except ScannerError as e:
            print(f"❌ Scanner error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            self.logger.exception("Test scan failed")
            return False
    
    def _prompt_source(self, available_sources: str) -> str:
        """Prompt user for scan source.
        
        Args:
            available_sources: Available scanner sources
            
        Returns:
            Selected source
        """
        sources = ['Auto', 'ADF', 'Flatbed']
        if available_sources:
            available_list = [s.strip() for s in available_sources.split(',')]
            sources = [s for s in sources if s in available_list] or sources
        
        print("Available sources:")
        for i, source in enumerate(sources, 1):
            print(f"  {i}. {source}")
        
        while True:
            try:
                choice = input(f"Select source (1-{len(sources)}) [default: 1]: ").strip()
                if not choice:
                    choice = "1"
                
                index = int(choice) - 1
                if 0 <= index < len(sources):
                    return sources[index]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    def _prompt_resolution(self, available_resolutions: str) -> int:
        """Prompt user for resolution.
        
        Args:
            available_resolutions: Available scanner resolutions
            
        Returns:
            Selected resolution
        """
        resolutions = [150, 300, 600]
        if available_resolutions:
            try:
                available_list = [int(r.strip()) for r in available_resolutions.split(',')]
                resolutions = [r for r in resolutions if r in available_list] or resolutions
            except ValueError:
                pass
        
        print("Available resolutions:")
        for i, res in enumerate(resolutions, 1):
            print(f"  {i}. {res} DPI")
        
        while True:
            try:
                choice = input(f"Select resolution (1-{len(resolutions)}) [default: 2]: ").strip()
                if not choice:
                    choice = "2"
                
                index = int(choice) - 1
                if 0 <= index < len(resolutions):
                    return resolutions[index]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    def _prompt_mode(self, available_modes: str) -> str:
        """Prompt user for color mode.
        
        Args:
            available_modes: Available scanner modes
            
        Returns:
            Selected mode
        """
        modes = ['Color', 'Gray', 'Lineart']
        if available_modes:
            available_list = [m.strip() for m in available_modes.split(',')]
            modes = [m for m in modes if m in available_list] or modes
        
        print("Available color modes:")
        for i, mode in enumerate(modes, 1):
            print(f"  {i}. {mode}")
        
        while True:
            try:
                choice = input(f"Select mode (1-{len(modes)}) [default: 1]: ").strip()
                if not choice:
                    choice = "1"
                
                index = int(choice) - 1
                if 0 <= index < len(modes):
                    return modes[index]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    def _prompt_format(self) -> str:
        """Prompt user for file format.
        
        Returns:
            Selected format
        """
        formats = ['png', 'jpeg', 'tiff']
        
        print("Available file formats:")
        for i, fmt in enumerate(formats, 1):
            print(f"  {i}. {fmt.upper()}")
        
        while True:
            try:
                choice = input(f"Select format (1-{len(formats)}) [default: 1]: ").strip()
                if not choice:
                    choice = "1"
                
                index = int(choice) - 1
                if 0 <= index < len(formats):
                    return formats[index]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    def _prompt_skip_blank(self) -> bool:
        """Prompt user for blank page detection.
        
        Returns:
            True if blank pages should be skipped
        """
        while True:
            choice = input("Skip blank pages? (y/n) [default: y]: ").strip().lower()
            if not choice:
                return True
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'.")
    
    def _prompt_upload(self) -> bool:
        """Prompt user for upload.
        
        Returns:
            True if files should be uploaded
        """
        while True:
            choice = input("Upload scanned files to API? (y/n) [default: n]: ").strip().lower()
            if not choice:
                return False
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'.")
    
    def _confirm(self, message: str) -> bool:
        """Get confirmation from user.
        
        Args:
            message: Confirmation message
            
        Returns:
            True if user confirms
        """
        while True:
            choice = input(f"{message} (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'.")