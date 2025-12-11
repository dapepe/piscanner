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
        
        Strategy: Create document with first page, then append remaining pages one by one.
        
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
        
        self.logger.info(f"Uploading {len(image_files)} pages incrementally")
        
        # Step 1: Create document with first page
        first_page = image_files[0]
        self.logger.info(f"Creating document with first page: {first_page}")
        
        result = self._create_document(
            [first_page],
            doc_id=doc_id,
            metadata=metadata,
            document_type=document_type,
            properties=properties
        )
        
        # Extract document ID from response
        created_doc_id = result.get('doc_id')
        if not created_doc_id:
            raise UploadError("Failed to get document ID from create response")
        
        self.logger.info(f"Document created with ID: {created_doc_id}")
        
        total_pages_added = result.get('pages_added', 1)
        
        # Step 2: Append remaining pages one by one
        if len(image_files) > 1:
            for i, page_file in enumerate(image_files[1:], start=2):
                self.logger.info(f"Appending page {i}/{len(image_files)}: {page_file}")
                
                append_result = self._append_pages(created_doc_id, [page_file])
                total_pages_added += append_result.get('pages_added', 1)
                
                self.logger.info(f"Page {i} appended successfully. Total pages: {append_result.get('total_pages', total_pages_added)}")
        
        # Return final result
        return {
            'success': True,
            'response': result.get('response'),
            'doc_id': created_doc_id,
            'pages_added': total_pages_added,
            'total_pages': total_pages_added
        }
    
    def _create_document(self, image_files: List[str], doc_id: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None,
                        document_type: Optional[str] = None,
                        properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new document with initial page(s).
        
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
        # Build API URL
        # Format: {base_url}/{workspace}/api/document/
        api_url = f"{self.config.api_url}/{self.config.api_workspace}/api/document/"
        
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
                    self.logger.info(f"Document created successfully: {result}")
                    return {
                        'success': True,
                        'response': result,
                        'doc_id': result.get('docId'),
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
                self.logger.error(f"Document creation failed: {error_msg}")
                raise UploadError(error_msg)
                
        except Exception as e:
            self.logger.error(f"Document creation error: {e}")
            raise UploadError(f"Document creation error: {e}")
    
    def _append_pages(self, doc_id: str, image_files: List[str],
                     metadata: Optional[Dict[str, Any]] = None,
                     document_type: Optional[str] = None,
                     properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Append page(s) to an existing document.
        
        Args:
            doc_id: Document ID to append pages to
            image_files: List of image file paths to upload
            metadata: Optional document metadata
            document_type: Optional document type ID
            properties: Optional document properties
            
        Returns:
            Dictionary with upload result
            
        Raises:
            UploadError: If upload fails
        """
        # Build API URL
        # Format: {base_url}/{workspace}/api/document/{docId}
        api_url = f"{self.config.api_url}/{self.config.api_workspace}/api/document/{doc_id}"
        
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
                    self.logger.info(f"Pages appended successfully: {result}")
                    return {
                        'success': True,
                        'response': result,
                        'doc_id': result.get('docId', doc_id),
                        'pages_added': result.get('pagesAdded', len(image_files)),
                        'total_pages': result.get('totalPages')
                    }
                except json.JSONDecodeError:
                    self.logger.warning("Response was not valid JSON")
                    return {
                        'success': True,
                        'response': response.text,
                        'doc_id': doc_id,
                        'pages_added': len(image_files),
                        'total_pages': None
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.logger.error(f"Page append failed: {error_msg}")
                raise UploadError(error_msg)
                
        except Exception as e:
            self.logger.error(f"Page append error: {e}")
            raise UploadError(f"Page append error: {e}")
    
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