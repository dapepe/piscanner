"""Scanner interface using SANE scanimage."""

import subprocess
import os
import re
from typing import List, Optional, Tuple
from PIL import Image

from .logger import Logger as PiScanLogger


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class Scanner:
    """Scanner interface using SANE scanimage utility."""
    
    def __init__(self, config, uploader=None):
        """Initialize scanner interface.
        
        Args:
            config: Configuration object
            uploader: Optional uploader instance for error logging
        """
        self.config = config
        self.logger = PiScanLogger()
        self.device = self._get_device()
        self.uploader = uploader
    
    def _apply_color_correction(self, file_path: str, source: Optional[str] = None) -> None:
        """Apply color correction and optimization to scanned image.

        Args:
            file_path: Path to image file to correct
            source: Source used for scanning (optional, for mirror logic)
        """
        correction_mode = self.config.scanner_color_correction
        optimize_png = self.config.upload_optimize_png
        image_quality = self.config.upload_image_quality
        mirror_simplex = self.config.scanner_mirror_simplex

        # Check if mirror logic is needed
        should_mirror = False
        if mirror_simplex and source and "front" in source.lower():
            should_mirror = True

        # Skip if no correction needed and no optimization
        if (correction_mode == "none" or not correction_mode) and not optimize_png and not should_mirror:
            return

        try:
            # Open image
            img = Image.open(file_path)
            needs_save = False

            # Log initial image details
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()[1:]
            width, height = img.size

            self.logger.info(
                f"Scanned page: {os.path.basename(file_path)} | "
                f"Format: {file_ext.upper()} | Mode: {img.mode} | "
                f"Size: {width}x{height} | File: {_format_size(file_size)} | "
                f"Color correction: {correction_mode or 'none'}"
            )

            # Apply mirror flip if requested for simplex
            if should_mirror:
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                self.logger.info(f"Applied mirror correction to {file_path}")
                needs_save = True

            # Apply color correction to color images
            if correction_mode and correction_mode != "none" and img.mode in ('RGB', 'RGBA'):
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
                    self.logger.info(f"Applied swap_rb correction to {file_path}")
                    needs_save = True
                elif correction_mode == "swap_rg":
                    # Swap red and green channels
                    corrected_channels = (g, r, b)
                    self.logger.info(f"Applied swap_rg correction to {file_path}")
                    needs_save = True
                elif correction_mode == "swap_gb":
                    # Swap green and blue channels
                    corrected_channels = (r, b, g)
                    self.logger.info(f"Applied swap_gb correction to {file_path}")
                    needs_save = True
                elif correction_mode == "rotate_left":
                    # Rotate channels left: RGB -> GBR
                    corrected_channels = (g, b, r)
                    self.logger.info(f"Applied rotate_left correction to {file_path}")
                    needs_save = True
                elif correction_mode == "rotate_right":
                    # Rotate channels right: RGB -> BRG
                    corrected_channels = (b, r, g)
                    self.logger.info(f"Applied rotate_right correction to {file_path}")
                    needs_save = True
                else:
                    self.logger.warning(f"Unknown color correction mode: {correction_mode}")
                    corrected_channels = None

                # Merge channels back
                if corrected_channels:
                    if has_alpha and a is not None:
                        img = Image.merge('RGBA', corrected_channels + (a,))
                    else:
                        img = Image.merge('RGB', corrected_channels)

            # Save with optimization if needed
            if needs_save or optimize_png:
                file_ext = file_path.lower().split('.')[-1]
                save_kwargs = {}

                if file_ext in ['jpg', 'jpeg']:
                    save_kwargs['quality'] = image_quality
                    save_kwargs['optimize'] = True
                    save_kwargs['progressive'] = True
                    save_kwargs['subsampling'] = 2
                    self.logger.info(f"JPEG save settings: quality={image_quality}, optimize=True, progressive=True, subsampling=2")
                elif file_ext == 'png' and optimize_png:
                    save_kwargs['optimize'] = True
                    self.logger.info(f"PNG save settings: optimize=True")

                img.save(file_path, **save_kwargs)
                new_size = os.path.getsize(file_path)
                if new_size != file_size:
                    self.logger.info(f"Saved post-processed image: {_format_size(new_size)}")

        except Exception as e:
            self.logger.error(f"Failed to apply post-processing to {file_path}: {e}")
    
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
        ]

        # Apply paper size / geometry
        paper_size = self.config.scanner_paper_size
        if paper_size:
            ps = paper_size.upper()
            if ps == "A4":
                # Standard A4 height (297mm)
                # Also set page-width/height explicitly for drivers that require it.
                cmd.extend(['--page-width', '210', '--page-height', '297', '-x', '210', '-y', '297'])
            elif ps == "LETTER":
                cmd.extend(['--page-width', '215.9', '--page-height', '279.4', '-x', '215.9', '-y', '279.4'])
            elif ps == "LEGAL":
                cmd.extend(['--page-width', '215.9', '--page-height', '355.6', '-x', '215.9', '-y', '355.6'])
            # "Max" or "Auto" usually implies default driver behavior (no args)

        # Disable swcrop to prevent auto-cropping footer
        cmd.append('--swcrop=no')

        # Output batch format
        cmd.append(f'--batch={os.path.join(output_dir, f"page_%03d.{format_ext}")}')
        
        self.logger.info(f"Starting scan with source: {actual_source}")
        self.logger.debug(f"Scan command: {' '.join(cmd)}")
        
        try:
            # Always monitor output_dir while scanimage runs.
            # This allows per-page post-processing (color correction/optimization)
            # even when callers want to upload at the end (ZIP mode).
            import threading
            import time

            scan_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            scanned_files: List[str] = []
            seen_files = set()
            pattern = re.compile(f"page_.*\\.{re.escape(format_ext)}$")

            def wait_for_file_complete(path: str, timeout_s: float = 10.0) -> None:
                """Wait until the scanned file is fully written."""
                start = time.time()
                last_size = -1
                stable_rounds = 0

                while time.time() - start < timeout_s:
                    try:
                        size = os.path.getsize(path)
                    except OSError:
                        time.sleep(0.1)
                        continue

                    if size > 0 and size == last_size:
                        stable_rounds += 1
                        if stable_rounds >= 2:
                            return
                    else:
                        stable_rounds = 0
                        last_size = size

                    time.sleep(0.1)

            def handle_new_file(filepath: str) -> None:
                if filepath in seen_files:
                    return

                seen_files.add(filepath)
                wait_for_file_complete(filepath)

                # Apply per-page post-processing right away
                self._apply_color_correction(filepath, source=actual_source)

                scanned_files.append(filepath)
                page_num = len(scanned_files)
                self.logger.debug(f"Page {page_num} ready: {filepath}")

                if page_callback:
                    try:
                        page_callback(page_num, filepath)
                    except Exception as e:
                        self.logger.error(f"Callback error: {e}")

            def monitor_pages() -> None:
                """Monitor directory for new page files."""
                while scan_process.poll() is None:
                    time.sleep(0.3)  # Check every 300ms
                    try:
                        for filename in sorted(os.listdir(output_dir)):
                            if pattern.match(filename):
                                handle_new_file(os.path.join(output_dir, filename))
                    except Exception as e:
                        self.logger.warning(f"Error monitoring pages: {e}")

            monitor_thread = threading.Thread(target=monitor_pages, daemon=True)
            monitor_thread.start()

            # Wait for scan to complete
            stdout, stderr = scan_process.communicate(timeout=300)
            monitor_thread.join(timeout=2)

            # Final sweep: scanimage can exit quickly and still leave page files.
            # Make sure we don't miss the last page(s) before evaluating errors.
            try:
                for filename in sorted(os.listdir(output_dir)):
                    if pattern.match(filename):
                        handle_new_file(os.path.join(output_dir, filename))
            except Exception as e:
                self.logger.warning(f"Error during final page sweep: {e}")

            returncode = scan_process.returncode
            output_text = (stdout + stderr).lower()

            feeder_out = (
                "document feeder out of documents" in output_text
                or "feeder out" in output_text
            )

            # scanimage commonly exits non-zero when ADF is empty at the end.
            # Treat this as success *if* we already scanned at least one page.
            if returncode != 0:
                raw_error = (stderr or stdout or "").strip() or "Unknown scan error"

                if feeder_out and scanned_files:
                    self.logger.info(
                        f"Scan finished: ADF out of documents after {len(scanned_files)} page(s)"
                    )
                else:
                    error_msg = raw_error

                    # Provide helpful error messages
                    if feeder_out:
                        if "flatbed" in actual_source.lower():
                            error_msg = (
                                "Flatbed scan failed. Note: The Canon DR-F120 has limited Flatbed support. "
                                "Try using ADF source instead."
                            )
                        else:
                            error_msg = (
                                f"No paper in document feeder (source: {actual_source}). "
                                "Please load paper into the ADF and try again."
                            )
                    elif "invalid argument" in output_text:
                        error_msg = f"Scanner configuration error (source: {actual_source}): {raw_error}"

                    self.logger.error(f"Scan failed: {error_msg}")
                    # Log to API if uploader is available
                    if self.uploader:
                        try:
                            self.uploader.log_error(
                                f"Scan failed: {error_msg}",
                                level="error",
                                details={
                                    "source": actual_source,
                                    "device": self.device,
                                    "returncode": returncode,
                                    "raw": raw_error,
                                },
                            )
                        except Exception as log_err:
                            self.logger.warning(f"Failed to log error to API: {log_err}")
                    raise ScannerError(f"Scan failed: {error_msg}")

            self.logger.info(f"Scanned {len(scanned_files)} pages")
            
            # Better error message if no pages found
            if not scanned_files:
                error_msg = "No pages were scanned. Please load paper into the document feeder and try again."
                self.logger.error("No pages were scanned. Check if paper is loaded in the feeder.")
                # Log to API if uploader is available
                if self.uploader:
                    try:
                        self.uploader.log_error(
                            error_msg,
                            level="error",
                            details={"source": actual_source, "device": self.device}
                        )
                    except Exception as log_err:
                        self.logger.warning(f"Failed to log error to API: {log_err}")
                raise ScannerError(error_msg)
            
            return scanned_files
            
        except subprocess.TimeoutExpired:
            error_msg = "Scan timeout"
            self.logger.error(error_msg)
            # Log to API if uploader is available
            if self.uploader:
                try:
                    self.uploader.log_error(
                        error_msg,
                        level="error",
                        details={"source": actual_source, "device": self.device}
                    )
                except Exception as log_err:
                    self.logger.warning(f"Failed to log error to API: {log_err}")
            raise ScannerError(error_msg)
        except ScannerError:
            raise
        except Exception as e:
            error_msg = f"Scan error: {e}"
            self.logger.error(error_msg)
            # Log to API if uploader is available
            if self.uploader:
                try:
                    self.uploader.log_error(
                        error_msg,
                        level="error",
                        details={"source": actual_source, "device": self.device, "exception": str(e)}
                    )
                except Exception as log_err:
                    self.logger.warning(f"Failed to log error to API: {log_err}")
            raise ScannerError(error_msg)
    
    def _map_source_name(self, source: str) -> str:
        """Map generic source name to scanner-specific name.
        
        Args:
            source: Generic source name (Auto, ADF, Flatbed) or specific name (ADF Duplex, ADF Front)
            
        Returns:
            Scanner-specific source name
        """
        # Optimization: If source is specific (not a generic category we need to map),
        # skip the expensive scanimage -A check. This prevents timeouts when the
        # scanner is busy (e.g. triggered by button press via scanbd).
        # We assume specific names provided in config are correct.
        source_upper = source.upper()
        if source_upper not in ["AUTO", "ADF", "FLATBED"]:
            return source

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