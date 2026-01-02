"""Scanner interface using SANE scanimage."""

import subprocess
import os
import re
from typing import List, Optional, Tuple
from PIL import Image

try:
    from .logger import Logger
except ImportError:
    # Simple logger fallback - silent unless debug enabled
    import os
    _debug_enabled = os.environ.get('PISCAN_DEBUG', '').lower() in ('1', 'true', 'yes')
    
    class Logger:
        def info(self, msg, *args):
            if _debug_enabled:
                print(f"INFO: {msg % args if args else msg}")
        def error(self, msg, *args):
            if _debug_enabled:
                print(f"ERROR: {msg % args if args else msg}")
        def debug(self, msg, *args):
            if _debug_enabled:
                print(f"DEBUG: {msg % args if args else msg}")
        def warning(self, msg, *args):
            if _debug_enabled:
                print(f"WARNING: {msg % args if args else msg}")


class Scanner:
    """Scanner interface using SANE scanimage utility."""
    
    def __init__(self, config):
        """Initialize scanner interface.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = Logger()
        self.device = self._get_device()
    
    def _apply_color_correction(self, file_path: str) -> None:
        """Apply color correction to scanned image.
        
        Args:
            file_path: Path to image file to correct
        """
        correction_mode = self.config.scanner_color_correction
        
        if correction_mode == "none" or not correction_mode:
            return
        
        try:
            # Open image
            img = Image.open(file_path)
            
            # Only apply correction to color images
            if img.mode not in ('RGB', 'RGBA'):
                self.logger.debug(f"Skipping color correction for non-RGB image: {img.mode}")
                return
            
            # Split channels
            has_alpha = img.mode == 'RGBA'
            if has_alpha:
                r, g, b, a = img.split()
            else:
                r, g, b = img.split()
                a = None
            
            # Apply correction based on mode
            if correction_mode == "swap_rb" or correction_mode == "bgr_to_rgb":
                # Swap red and blue channels (BGR -> RGB or RGB -> BGR)
                corrected_channels = (b, g, r)
                self.logger.debug(f"Applied swap_rb correction to {file_path}")
            elif correction_mode == "swap_rg":
                # Swap red and green channels
                corrected_channels = (g, r, b)
                self.logger.debug(f"Applied swap_rg correction to {file_path}")
            else:
                self.logger.warning(f"Unknown color correction mode: {correction_mode}")
                return
            
            # Merge channels back
            if has_alpha and a is not None:
                corrected_img = Image.merge('RGBA', corrected_channels + (a,))
            else:
                corrected_img = Image.merge('RGB', corrected_channels)
            
            # Save corrected image (overwrite original)
            corrected_img.save(file_path)
            self.logger.debug(f"Color correction saved to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to apply color correction to {file_path}: {e}")
    
    def _get_device(self) -> str:
        """Get scanner device string.
        
        Returns:
            Device string for scanimage
        """
        if self.config.scanner_device:
            self.logger.debug(f"Using configured device: {self.config.scanner_device}")
            return self.config.scanner_device
        
        raise ScannerError("No scanner device configured. Please set scanner.device in config.yaml")
    
    def test_scanner(self) -> bool:
        """Test if scanner is accessible.
        
        Returns:
            True if scanner is accessible
        """
        try:
            result = subprocess.run([
                'scanimage', 
                '-d', self.device,
                '--test'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info("Scanner test successful")
                return True
            else:
                self.logger.error(f"Scanner test failed: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Scanner test error: {e}")
            return False
    
    def scan_pages(self, output_dir: str, source: Optional[str] = None, 
                   page_callback=None) -> List[str]:
        """Scan pages to output directory.
        
        Args:
            output_dir: Directory to save scanned pages
            source: Source to scan from (ADF, Flatbed, or Auto)
            page_callback: Optional callback function called when each page is ready.
                          Called with (page_number, file_path) as arguments.
            
        Returns:
            List of scanned file paths
            
        Raises:
            ScannerError: If scanning fails
        """
        source = source or self.config.scanner_source
        
        # Determine actual source
        actual_source = self._determine_source(source)
        
        # Build scanimage command
        # Note: scanimage uses 'jpg' extension for jpeg format
        format_ext = 'jpg' if self.config.scanner_format == 'jpeg' else self.config.scanner_format
        
        cmd = [
            'scanimage',
            '-d', self.device,
            '--resolution', str(self.config.scanner_resolution),
            '--mode', self.config.scanner_mode,
            '--source', actual_source,
            f'--format={self.config.scanner_format}',
            f'--batch={os.path.join(output_dir, f"page_%03d.{format_ext}")}'
        ]
        
        self.logger.info(f"Starting scan with source: {actual_source}")
        self.logger.debug(f"Scan command: {' '.join(cmd)}")
        
        try:
            # If callback provided, monitor for pages in real-time
            if page_callback:
                import threading
                import time
                
                scan_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                scanned_files = []
                seen_files = set()
                
                def monitor_pages():
                    """Monitor directory for new page files."""
                    page_num = 0
                    while scan_process.poll() is None:
                        time.sleep(0.3)  # Check every 300ms
                        try:
                            for filename in sorted(os.listdir(output_dir)):
                                pattern = f"page_.*\\.{format_ext}$"
                                if re.match(pattern, filename):
                                    filepath = os.path.join(output_dir, filename)
                                    if filepath not in seen_files:
                                        # Wait briefly to ensure file is fully written
                                        time.sleep(0.2)
                                        seen_files.add(filepath)
                                        
                                        # Apply color correction if configured
                                        self._apply_color_correction(filepath)
                                        
                                        scanned_files.append(filepath)
                                        page_num += 1
                                        self.logger.debug(f"Page {page_num} ready: {filepath}")
                                        try:
                                            page_callback(page_num, filepath)
                                        except Exception as e:
                                            self.logger.error(f"Callback error: {e}")
                        except Exception as e:
                            self.logger.warning(f"Error monitoring pages: {e}")
                
                monitor_thread = threading.Thread(target=monitor_pages, daemon=True)
                monitor_thread.start()
                
                # Wait for scan to complete
                stdout, stderr = scan_process.communicate(timeout=300)
                monitor_thread.join(timeout=2)
                
                # Build result object
                returncode = scan_process.returncode
                output_text = (stdout + stderr).lower()
            else:
                # Original synchronous behavior
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                stdout = result.stdout
                stderr = result.stderr
                returncode = result.returncode
                output_text = (stdout + stderr).lower()
                scanned_files = []  # Will be populated below
            
            # Check for common error conditions in output
            
            if returncode != 0 or "document feeder out of documents" in output_text:
                error_msg = stderr or stdout or "Unknown scan error"
                
                # Provide helpful error messages
                if "document feeder out of documents" in output_text or "feeder out" in output_text:
                    if "flatbed" in actual_source.lower():
                        error_msg = f"Flatbed scan failed. Note: The Canon DR-F120 has limited Flatbed support. Try using ADF source instead."
                    else:
                        error_msg = f"No paper in document feeder (source: {actual_source}). Please load paper into the ADF and try again."
                elif "invalid argument" in output_text:
                    error_msg = f"Scanner configuration error (source: {actual_source}): {error_msg}"
                
                self.logger.error(f"Scan failed: {error_msg}")
                raise ScannerError(f"Scan failed: {error_msg}")
            
            # Find scanned files (only needed if no callback was used)
            if not page_callback:
                # Note: scanimage uses 'jpg' extension for jpeg format
                format_ext = 'jpg' if self.config.scanner_format == 'jpeg' else self.config.scanner_format
                pattern = f"page_.*\\.{format_ext}$"
                for filename in os.listdir(output_dir):
                    if re.match(pattern, filename):
                        scanned_files.append(os.path.join(output_dir, filename))
                
                scanned_files.sort()  # Ensure proper order
                
                # Apply color correction to all scanned files
                for filepath in scanned_files:
                    self._apply_color_correction(filepath)
            
            self.logger.info(f"Scanned {len(scanned_files)} pages")
            
            # Better error message if no pages found
            if not scanned_files:
                self.logger.error("No pages were scanned. Check if paper is loaded in the feeder.")
                raise ScannerError("No pages were scanned. Please load paper into the document feeder and try again.")
            
            return scanned_files
            
        except subprocess.TimeoutExpired:
            self.logger.error("Scan timeout")
            raise ScannerError("Scan timeout")
        except Exception as e:
            self.logger.error(f"Scan error: {e}")
            raise ScannerError(f"Scan error: {e}")
    
    def _map_source_name(self, source: str) -> str:
        """Map generic source name to scanner-specific name.
        
        Args:
            source: Generic source name (Auto, ADF, Flatbed) or specific name (ADF Duplex, ADF Front)
            
        Returns:
            Scanner-specific source name
        """
        # Get scanner's available sources
        try:
            result = subprocess.run([
                'scanimage', '-d', self.device, '-A'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse source line: --source Flatbed|ADF Front|ADF Duplex [Flatbed]
                source_match = re.search(r'--source\s+([^\[]+)', result.stdout)
                if source_match:
                    available_sources = [s.strip() for s in source_match.group(1).split('|')]
                    self.logger.debug(f"Available sources: {available_sources}")
                    
                    # First, check if source exactly matches an available source (case-insensitive)
                    for s in available_sources:
                        if s.lower() == source.lower():
                            self.logger.debug(f"Exact match found for '{source}': {s}")
                            return s
                    
                    # Map generic names to scanner-specific names
                    source_upper = source.upper()
                    if source_upper == "FLATBED":
                        # Look for Flatbed
                        for s in available_sources:
                            if "flatbed" in s.lower():
                                return s
                    elif source_upper == "ADF":
                        # Prefer ADF Duplex if available, otherwise ADF Front
                        for s in available_sources:
                            if "adf duplex" in s.lower():
                                return s
                        for s in available_sources:
                            if "adf" in s.lower():
                                return s
                    
                    # If no match, return first available source
                    if available_sources:
                        self.logger.warning(f"Source '{source}' not found, using: {available_sources[0]}")
                        return available_sources[0]
        except Exception as e:
            self.logger.warning(f"Failed to detect available sources: {e}")
        
        # Fallback: return as-is
        return source
    
    def _determine_source(self, source: str) -> str:
        """Determine actual scanner source.
        
        Args:
            source: Requested source (Auto, ADF, Flatbed)
            
        Returns:
            Actual source to use
        """
        if source.upper() != "AUTO":
            return self._map_source_name(source)
        
        # Try to detect if ADF has paper
        try:
            # Check scanner status for paper in ADF
            result = subprocess.run([
                'scanimage', '-d', self.device, '-A'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Look for ADF status in options
                if "adf" in result.stdout.lower():
                    # Check if ADF reports paper loaded
                    if any(keyword in result.stdout.lower() for keyword in ["loaded", "ready", "paper"]):
                        self.logger.debug("ADF detected with paper, using ADF")
                        return self._map_source_name("ADF")
            
            self.logger.debug("No paper detected in ADF, trying Flatbed")
            return self._map_source_name("Flatbed")
            
        except Exception as e:
            self.logger.warning(f"Failed to auto-detect source: {e}")
            # Default to ADF for auto mode
            return self._map_source_name("ADF")
    
    def get_scanner_info(self) -> dict:
        """Get scanner information.
        
        Returns:
            Dictionary with scanner info
        """
        info = {
            'device': self.device,
            'status': 'unknown'
        }
        
        try:
            # Get scanner options
            result = subprocess.run([
                'scanimage', '-d', self.device, '-A'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                info['status'] = 'available'
                info['options'] = result.stdout
                
                # Parse some common options
                if '--resolution' in result.stdout:
                    resolutions = re.findall(r'--resolution.*?\[(.*?)\]', result.stdout)
                    if resolutions:
                        info['resolutions'] = ', '.join([r.strip() for r in resolutions[0].split('|')])
                
                if '--mode' in result.stdout:
                    modes = re.findall(r'--mode.*?\[(.*?)\]', result.stdout)
                    if modes:
                        info['modes'] = ', '.join([m.strip() for m in modes[0].split('|')])
                        
                if '--source' in result.stdout:
                    sources = re.findall(r'--source.*?\[(.*?)\]', result.stdout)
                    if sources:
                        info['sources'] = ', '.join([s.strip() for s in sources[0].split('|')])
            else:
                info['status'] = 'error'
                info['error'] = result.stderr
                
        except Exception as e:
            info['status'] = 'error'
            info['error'] = str(e)
        
        return info


class ScannerError(Exception):
    """Scanner-related errors."""
    pass