"""Blank page detection using Pillow."""

import os
from typing import List, Tuple
# Simple logger fallback - silent unless debug enabled
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

try:
    from PIL import Image, ImageStat
except ImportError:
    print("Warning: PIL/Pillow not available. Blank page detection will be disabled.")
    Image = None
    ImageStat = None


class BlankPageDetector:
    """Detects blank pages in scanned images."""
    
    def __init__(self, config):
        """Initialize blank page detector.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = Logger()
        self.enabled = Image is not None and ImageStat is not None
        
        if not self.enabled:
            self.logger.warning("PIL/Pillow not available - blank page detection disabled")
    
    def is_blank(self, image_path: str) -> bool:
        """Check if an image is blank.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if image is considered blank
        """
        if not self.enabled:
            self.logger.debug(f"Blank detection disabled, keeping file: {image_path}")
            return False
        
        if not os.path.exists(image_path):
            self.logger.warning(f"Image file not found: {image_path}")
            return False
        
        try:
            # Open image and convert to grayscale
            with Image.open(image_path) as img:  # type: ignore
                # Convert to grayscale for analysis
                if img.mode != 'L':
                    img = img.convert('L')
                
                # Get image statistics
                stat = ImageStat.Stat(img)  # type: ignore
                
                # Calculate percentage of non-white pixels
                # White threshold is configurable (default 250 out of 255)
                white_threshold = self.config.white_threshold
                
                # Method 1: Mean pixel brightness
                mean_brightness = stat.mean[0]
                white_ratio = mean_brightness / 255.0
                
                # Method 2: Count pixels above threshold
                # This is more accurate but slower
                pixels = list(img.getdata())
                non_white_pixels = sum(1 for pixel in pixels if pixel < white_threshold)
                non_white_ratio = non_white_pixels / len(pixels)
                
                self.logger.debug(f"Image {os.path.basename(image_path)}: "
                                f"mean_brightness={mean_brightness:.1f}, "
                                f"white_ratio={white_ratio:.3f}, "
                                f"non_white_ratio={non_white_ratio:.3f}")
                
                # Use non-white ratio for decision (more reliable)
                is_blank = non_white_ratio <= self.config.blank_threshold
                
                if is_blank:
                    self.logger.info(f"Detected blank page: {os.path.basename(image_path)} "
                                   f"(non-white ratio: {non_white_ratio:.3f})")
                
                return is_blank
                
        except Exception as e:
            self.logger.error(f"Error analyzing image {image_path}: {e}")
            # On error, assume not blank to avoid losing data
            return False
    
    def filter_blank_pages(self, image_files: List[str]) -> Tuple[List[str], List[str]]:
        """Filter out blank pages from a list of image files.
        
        Args:
            image_files: List of image file paths
            
        Returns:
            Tuple of (non_blank_files, blank_files)
        """
        if not self.enabled:
            self.logger.info("Blank detection disabled, keeping all files")
            return image_files, []
        
        non_blank_files = []
        blank_files = []
        
        for image_file in image_files:
            if self.is_blank(image_file):
                blank_files.append(image_file)
            else:
                non_blank_files.append(image_file)
        
        self.logger.info(f"Blank page detection: {len(blank_files)} blank, "
                        f"{len(non_blank_files)} non-blank pages")
        
        return non_blank_files, blank_files
    
    def remove_blank_files(self, blank_files: List[str]) -> None:
        """Remove blank page files.
        
        Args:
            blank_files: List of blank file paths to remove
        """
        for blank_file in blank_files:
            try:
                os.remove(blank_file)
                self.logger.debug(f"Removed blank page: {os.path.basename(blank_file)}")
            except Exception as e:
                self.logger.error(f"Failed to remove blank file {blank_file}: {e}")
    
    def get_image_info(self, image_path: str) -> dict:
        """Get information about an image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with image information
        """
        info = {
            'path': image_path,
            'exists': os.path.exists(image_path),
            'size': 0,
            'dimensions': None,
            'mode': None,
            'format': None
        }
        
        if not info['exists']:
            return info
        
        try:
            info['size'] = os.path.getsize(image_path)
            
            if self.enabled:
                with Image.open(image_path) as img:  # type: ignore
                    info['dimensions'] = img.size  # (width, height)
                    info['mode'] = img.mode
                    info['format'] = img.format
                    
                    # Add blank detection info
                    info['is_blank'] = self.is_blank(image_path)
                    
                    # Calculate statistics
                    if img.mode != 'L':
                        img_gray = img.convert('L')
                    else:
                        img_gray = img
                    
                    stat = ImageStat.Stat(img_gray)  # type: ignore
                    info['mean_brightness'] = stat.mean[0]
                    info['min_brightness'] = stat.extrema[0][0]
                    info['max_brightness'] = stat.extrema[0][1]
                    
        except Exception as e:
            self.logger.error(f"Error getting image info for {image_path}: {e}")
        
        return info