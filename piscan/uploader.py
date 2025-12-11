"""HTTP uploader for scanned documents."""

import json
import os
from typing import List, Dict, Any, Optional

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

try:
    import requests
except ImportError:
    print("Warning: requests not available. HTTP upload will be disabled.")
    requests = None


class Uploader:
    """Handles uploading scanned documents to remote API."""
    
    def __init__(self, config):
        """Initialize uploader.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = Logger()
        self.enabled = requests is not None
        
        if not self.enabled:
            self.logger.warning("requests library not available - HTTP upload disabled")
    
    def upload_document(self, image_files: List[str], doc_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None,
                       document_type: Optional[str] = None,
                       properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upload scanned document to API.
        
        Args:
            image_files: List of image file paths to upload
            doc_id: Optional document ID (will be generated if not provided)
            metadata: Optional document metadata
            document_type: Optional document type ID
            properties: Optional document properties
            
        Returns:
            Dictionary with upload result
            
        Raises:
            UploadError: If upload fails
        """
        if not self.enabled:
            raise UploadError("HTTP upload not available - requests library missing")
        
        if not image_files:
            raise UploadError("No files to upload")
        
        # Generate document ID if not provided
        if doc_id is None:
            # Simple doc ID generation
            import hashlib
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d-%H:%M")
            hash_input = timestamp + str(os.urandom(4).hex())
            hash_obj = hashlib.md5(hash_input.encode())
            hash_digits = hash_obj.hexdigest()[:5].upper()
            doc_id = f"{timestamp}-{hash_digits}"
        
        # Build API URL
        # Format: {base_url}/{workspace}/api/document/
        api_url = f"{self.config.api_url}/{self.config.api_workspace}/api/document/"
        
        self.logger.info(f"Uploading {len(image_files)} files to {api_url}")
        
        # Prepare files for multipart upload
        files = []
        try:
            for image_file in image_files:
                if not os.path.exists(image_file):
                    self.logger.warning(f"File not found, skipping: {image_file}")
                    continue
                
                filename = os.path.basename(image_file)
                files.append(('files', (filename, open(image_file, 'rb'), 'image/jpeg')))
            
            if not files:
                raise UploadError("No valid files to upload")
            
            # Prepare form data
            data = {}
            if metadata:
                data['meta'] = json.dumps(metadata)
            if document_type:
                data['documentType'] = document_type
            if properties:
                data['properties'] = json.dumps(properties)
            
            # Prepare headers
            headers = {}
            if self.config.api_token:
                headers['Authorization'] = f'Bearer {self.config.api_token}'
            
            # Make request
            response = requests.post(  # type: ignore
                api_url,
                files=files,
                data=data,
                headers=headers,
                timeout=self.config.api_timeout
            )
            
            # Close file handles
            for _, (_, file_obj, _) in files:
                file_obj.close()
            
            # Handle response
            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    self.logger.info(f"Upload successful: {result}")
                    return {
                        'success': True,
                        'response': result,
                        'doc_id': result.get('docId', doc_id),
                        'pages_added': result.get('pagesAdded', len(image_files)),
                        'total_pages': result.get('totalPages', len(image_files))
                    }
                except json.JSONDecodeError:
                    self.logger.warning("Response was not valid JSON")
                    return {
                        'success': True,
                        'response': response.text,
                        'doc_id': doc_id,
                        'pages_added': len(image_files),
                        'total_pages': len(image_files)
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.logger.error(f"Upload failed: {error_msg}")
                raise UploadError(error_msg)
                
        except Exception as e:
            self.logger.error(f"Upload error: {e}")
            raise UploadError(f"Upload error: {e}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to API.
        
        Returns:
            Dictionary with test result
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'requests library not available'
            }
        
        try:
            # Test with a simple GET request to the base URL
            test_url = f"{self.config.api_url}/{self.config.api_workspace}/api/"
            
            headers = {}
            if self.config.api_token:
                headers['Authorization'] = f'Bearer {self.config.api_token}'
            
            response = requests.get(  # type: ignore
                test_url,
                headers=headers,
                timeout=self.config.api_timeout
            )
            
            if response.status_code in [200, 404]:  # 404 is OK for API root
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'url': test_url
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_upload_stats(self, image_files: List[str]) -> Dict[str, Any]:
        """Get statistics about files to be uploaded.
        
        Args:
            image_files: List of image file paths
            
        Returns:
            Dictionary with upload statistics
        """
        stats = {
            'file_count': len(image_files),
            'total_size': 0,
            'files': []
        }
        
        for image_file in image_files:
            if os.path.exists(image_file):
                size = os.path.getsize(image_file)
                stats['total_size'] += size
                stats['files'].append({
                    'name': os.path.basename(image_file),
                    'size': size,
                    'path': image_file
                })
            else:
                stats['files'].append({
                    'name': os.path.basename(image_file),
                    'size': 0,
                    'path': image_file,
                    'error': 'File not found'
                })
        
        return stats


class UploadError(Exception):
    """Upload-related errors."""
    pass