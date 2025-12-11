"""Scanner interface using SANE scanimage."""

import subprocess
import os
import re
from typing import List, Optional, Tuple

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
    
    def scan_pages(self, output_dir: str, source: Optional[str] = None) -> List[str]:
        """Scan pages to output directory.
        
        Args:
            output_dir: Directory to save scanned pages
            output_dir: Source to scan from (ADF, Flatbed, or Auto)
            
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Check for common error conditions in output
            output_text = (result.stdout + result.stderr).lower()
            
            if result.returncode != 0 or "document feeder out of documents" in output_text:
                error_msg = result.stderr or result.stdout or "Unknown scan error"
                
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
            
            # Find scanned files
            # Note: scanimage uses 'jpg' extension for jpeg format
            format_ext = 'jpg' if self.config.scanner_format == 'jpeg' else self.config.scanner_format
            scanned_files = []
            pattern = f"page_.*\\.{format_ext}$"
            for filename in os.listdir(output_dir):
                if re.match(pattern, filename):
                    scanned_files.append(os.path.join(output_dir, filename))
            
            scanned_files.sort()  # Ensure proper order
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