"""File management for scanned documents."""

import os
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
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


class FileManager:
    """Manages temporary directories and file operations for scanned documents."""
    
    def __init__(self, config):
        """Initialize file manager.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = Logger()
        
        # Ensure directories exist
        os.makedirs(self.config.temp_dir, exist_ok=True)
        os.makedirs(self.config.failed_dir, exist_ok=True)
    
    def create_scan_directory(self) -> str:
        """Create a timestamped directory for a new scan job.
        
        Runs retention cleanup as a lightweight "periodic" task.
        
        Returns:
            Path to the created directory
        """
        try:
            self.cleanup_old_temp_jobs(self.config.temp_retention_hours)
            self.cleanup_old_failed_jobs(self.config.failed_retention_days)
        except Exception as e:
            self.logger.warning(f"Retention cleanup skipped: {e}")

        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        scan_dir = os.path.join(self.config.temp_dir, timestamp)
        os.makedirs(scan_dir, exist_ok=True)
        
        self.logger.info(f"Created scan directory: {scan_dir}")
        return scan_dir

    def cleanup_old_temp_jobs(self, max_age_hours: int = 168) -> None:
        """Clean up old temp scan directories.

        This removes scan directories under `storage.temp_dir` that match our
        naming patterns and are older than `max_age_hours`.

        Args:
            max_age_hours: Maximum age in hours to keep temp scan jobs
        """
        if not os.path.exists(self.config.temp_dir):
            return

        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        for item in os.listdir(self.config.temp_dir):
            item_path = os.path.join(self.config.temp_dir, item)

            if not os.path.isdir(item_path):
                continue

            # Only touch directories that look like our scan jobs
            # - FileManager style: YYYY-MM-DD-HHMMSS
            # - scanbd style: scan-YYYY-MM-DD-HHMMSS
            is_job_dir = (
                len(item) == 15 and item[4] == '-' and item[7] == '-' and item[10] == '-'
            ) or (
                item.startswith('scan-') and len(item) == 20 and item[9] == '-' and item[12] == '-' and item[15] == '-'
            )

            if not is_job_dir:
                continue

            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                if mtime < cutoff:
                    shutil.rmtree(item_path, ignore_errors=True)
                    self.logger.info(f"Cleaned up old temp job: {item}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp job {item}: {e}")
    
    def generate_doc_id(self, timestamp: Optional[str] = None) -> str:
        """Generate a document ID with timestamp and hash.
        
        Args:
            timestamp: Optional timestamp string
            
        Returns:
            Document ID in format YYYY-MM-DD-HH:MM-XXXXX
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H:%M")
        
        # Generate 5-digit hash from timestamp and random data
        hash_input = timestamp + str(os.urandom(4).hex())
        hash_obj = hashlib.md5(hash_input.encode())
        hash_digits = hash_obj.hexdigest()[:5].upper()
        
        return f"{timestamp}-{hash_digits}"
    
    def move_to_failed(self, scan_dir: str, error_msg: str) -> str:
        """Move failed scan directory to failed directory.
        
        Args:
            scan_dir: Path to scan directory
            error_msg: Error message for logging
            
        Returns:
            Path to failed directory
        """
        if not self.config.keep_failed:
            self.logger.info(f"Removing failed scan directory: {scan_dir}")
            shutil.rmtree(scan_dir, ignore_errors=True)
            return ""
        
        # Create failed subdirectory
        timestamp = os.path.basename(scan_dir)
        failed_dir = os.path.join(self.config.failed_dir, timestamp)
        
        # Move files
        if os.path.exists(scan_dir):
            shutil.move(scan_dir, failed_dir)
            
            # Create error info file
            error_file = os.path.join(failed_dir, "error.txt")
            with open(error_file, 'w') as f:
                f.write(f"Error: {error_msg}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            
            self.logger.info(f"Moved failed scan to: {failed_dir}")
        else:
            self.logger.warning(f"Scan directory not found: {scan_dir}")
        
        return failed_dir
    
    def cleanup_directory(self, scan_dir: str) -> None:
        """Clean up scan directory after successful upload.
        
        Args:
            scan_dir: Path to scan directory
        """
        try:
            if os.path.exists(scan_dir):
                shutil.rmtree(scan_dir)
                self.logger.debug(f"Cleaned up directory: {scan_dir}")
        except Exception as e:
            self.logger.error(f"Failed to cleanup directory {scan_dir}: {e}")
    
    def get_scanned_files(self, scan_dir: str, pattern: str = "*") -> List[str]:
        """Get list of scanned files in directory.
        
        Args:
            scan_dir: Path to scan directory
            pattern: File pattern to match
            
        Returns:
            List of file paths
        """
        import glob
        
        if not os.path.exists(scan_dir):
            return []
        
        search_pattern = os.path.join(scan_dir, pattern)
        files = glob.glob(search_pattern)
        files.sort()  # Ensure consistent order
        
        return [f for f in files if os.path.isfile(f)]
    
    def get_directory_size(self, directory: str) -> int:
        """Get total size of directory in bytes.
        
        Args:
            directory: Path to directory
            
        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.isfile(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            self.logger.error(f"Failed to calculate directory size: {e}")
        
        return total_size
    
    def cleanup_old_failed_jobs(self, max_age_days: int = 30) -> None:
        """Clean up old failed jobs.
        
        Args:
            max_age_days: Maximum age in days to keep failed jobs
        """
        if not os.path.exists(self.config.failed_dir):
            return
        
        current_time = datetime.now()
        
        for item in os.listdir(self.config.failed_dir):
            item_path = os.path.join(self.config.failed_dir, item)
            
            if os.path.isdir(item_path):
                try:
                    # Get directory creation time
                    creation_time = datetime.fromtimestamp(os.path.getctime(item_path))
                    age_days = (current_time - creation_time).days
                    
                    if age_days > max_age_days:
                        shutil.rmtree(item_path)
                        self.logger.info(f"Cleaned up old failed job: {item}")
                except Exception as e:
                    self.logger.error(f"Failed to cleanup old failed job {item}: {e}")
    
    def get_scan_job_info(self, scan_dir: str) -> dict:
        """Get information about a scan job.
        
        Args:
            scan_dir: Path to scan directory
            
        Returns:
            Dictionary with job information
        """
        info = {
            'directory': scan_dir,
            'exists': os.path.exists(scan_dir),
            'files': [],
            'total_size': 0,
            'file_count': 0
        }
        
        if not info['exists']:
            return info
        
        # Get files
        files = self.get_scanned_files(scan_dir)
        info['files'] = [os.path.basename(f) for f in files]
        info['file_count'] = len(files)
        info['total_size'] = self.get_directory_size(scan_dir)
        
        # Check for error file
        error_file = os.path.join(scan_dir, "error.txt")
        if os.path.exists(error_file):
            with open(error_file, 'r') as f:
                info['error'] = f.read().strip()
        
        return info