"""HTTP uploader for scanned documents."""

import json
import os
import zipfile
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, cast
from PIL import Image

from .logger import Logger as PiScanLogger

try:
    import requests as _requests
except ImportError:
    print("Warning: requests not available. HTTP upload will be disabled.")
    _requests = None

requests = cast(Any, _requests)


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class Uploader:
    """Handles uploading scanned documents to remote API."""
    
    def __init__(self, config):
        """Initialize uploader.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = PiScanLogger()
        self.enabled = requests is not None
        
        if not self.enabled:
            self.logger.warning("requests library not available - HTTP upload disabled")

    def _guess_mime_type(self, file_path: str) -> str:
        """Best-effort MIME type based on extension."""
        ext = os.path.splitext(file_path.lower())[1]
        if ext in ('.jpg', '.jpeg'):
            return 'image/jpeg'
        if ext == '.png':
            return 'image/png'
        if ext in ('.tif', '.tiff'):
            return 'image/tiff'
        if ext == '.pdf':
            return 'application/pdf'
        if ext == '.zip':
            return 'application/zip'
        return 'application/octet-stream'
    
    def log_error(self, message: str, level: str = "error", details: Optional[Dict[str, Any]] = None) -> None:
        """Log error to API endpoint.
        
        Args:
            message: Error message
            level: Log level (info, warn, error)
            details: Optional additional details
        """
        if not self.enabled:
            self.logger.warning("Cannot log to API - requests library missing")
            return
        
        try:
            log_url = f"{self.config.api_url}/{self.config.api_workspace}/api/log"
            
            payload: Dict[str, Any] = {
                "level": level,
                "message": message,
                "source": "scanner",
                "clientTimestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            if details:
                payload["details"] = details
            
            headers = {
                "Content-Type": "application/json"
            }
            if self.config.api_token:
                headers["Authorization"] = f"Bearer {self.config.api_token}"
            
            response = requests.post(  # type: ignore
                log_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.logger.debug(f"Error logged to API: {message}")
            else:
                self.logger.warning(f"Failed to log error to API: HTTP {response.status_code}")
                
        except Exception as e:
            self.logger.warning(f"Failed to log error to API: {e}")
    
    def _compress_to_zip(self, image_files: List[str], compression_level: int = 6) -> str:
        """Compress image files to a ZIP archive.
        
        Args:
            image_files: List of image file paths
            compression_level: ZIP compression level (1-9)
            
        Returns:
            Path to created ZIP file
        """
        if not image_files:
            raise UploadError("No files to compress")

        temp_zip = tempfile.NamedTemporaryFile(mode='w+b', suffix='.zip', delete=False)
        zip_path = temp_zip.name
        temp_zip.close()
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zipf:
                for image_file in image_files:
                    if os.path.exists(image_file):
                        arcname = os.path.basename(image_file)
                        zipf.write(image_file, arcname=arcname)
                        self.logger.debug(f"Added {arcname} to ZIP")
            
            total_size = os.path.getsize(zip_path)
            self.logger.info(f"Created ZIP: {zip_path} ({len(image_files)} files, {_format_size(total_size)})")
            return zip_path
            
        except Exception as e:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise UploadError(f"Failed to create ZIP archive: {e}")
    
    def _optimize_image(self, file_path: str) -> Optional[str]:
        """Optimize image for size reduction.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Path to optimized file (same as input if no changes made)
        """
        max_dim = self.config.upload_max_image_dimension
        if max_dim <= 0:
            return file_path
        
        try:
            img = Image.open(file_path)
            width, height = img.size
            
            if width <= max_dim and height <= max_dim:
                return file_path
            
            ratio = min(max_dim / width, max_dim / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            self.logger.debug(f"Resizing {file_path} from {width}x{height} to {new_width}x{new_height}")
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            file_ext = os.path.splitext(file_path.lower())[1]
            save_kwargs: Dict[str, Any] = {'optimize': True}
            if file_ext in ('.jpg', '.jpeg'):
                save_kwargs.update({
                    'quality': self.config.upload_image_quality,
                    'progressive': True,
                    'subsampling': 2,
                })

            img.save(file_path, **save_kwargs)
            
            return file_path
            
        except Exception as e:
            self.logger.warning(f"Failed to optimize {file_path}: {e}")
            return file_path
    
    def _convert_to_jpeg(self, file_path: str) -> Optional[str]:
        """Convert image to JPEG for better compression.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Path to JPEG file (same name but .jpg extension)
        """
        try:
            img = Image.open(file_path)
            
            if img.mode in ('RGBA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            jpeg_path = os.path.splitext(file_path)[0] + '.jpg'
            img.save(
                jpeg_path,
                quality=self.config.upload_image_quality,
                optimize=True,
                progressive=True,
                subsampling=2,
            )
            
            self.logger.debug(f"Converted {file_path} to {jpeg_path}")
            
            if file_path != jpeg_path and os.path.exists(file_path):
                os.remove(file_path)
            
            return jpeg_path
            
        except Exception as e:
            self.logger.warning(f"Failed to convert {file_path} to JPEG: {e}")
            return file_path
    
    def _file_size_bytes(self, file_path: str) -> int:
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    def _payload_size_bytes(self, file_paths: List[str]) -> int:
        return sum(self._file_size_bytes(path) for path in file_paths)

    def _prepare_file_for_zip(
        self,
        file_path: str,
        total_pages: int,
        auto_jpeg_threshold: int,
        auto_jpeg_page_size_bytes: int,
    ) -> str:
        """Prepare a single page file for ZIP upload."""
        should_force_jpeg = auto_jpeg_threshold > 0 and total_pages >= auto_jpeg_threshold

        if not should_force_jpeg and auto_jpeg_page_size_bytes > 0:
            try:
                should_force_jpeg = self._file_size_bytes(file_path) >= auto_jpeg_page_size_bytes
            except OSError:
                should_force_jpeg = False

        if should_force_jpeg:
            optimized = self._convert_to_jpeg(file_path)
        else:
            optimized = self._optimize_image(file_path)

        return str(optimized)

    def _build_zip_bundles(
        self,
        prepared_files: List[str],
        bundle_size: int,
        bundle_max_bytes: int,
    ) -> List[List[str]]:
        """Split prepared files into bundles by page count and/or bytes."""
        bundles: List[List[str]] = []
        current_bundle: List[str] = []
        current_bytes = 0

        for file_path in prepared_files:
            file_bytes = self._file_size_bytes(file_path)

            should_split = False
            if current_bundle and bundle_size > 0 and len(current_bundle) >= bundle_size:
                should_split = True
            if current_bundle and bundle_max_bytes > 0 and current_bytes + file_bytes > bundle_max_bytes:
                should_split = True

            if should_split:
                bundles.append(current_bundle)
                current_bundle = []
                current_bytes = 0

            current_bundle.append(file_path)
            current_bytes += file_bytes

        if current_bundle:
            bundles.append(current_bundle)

        return bundles

    def upload_document(self, image_files: List[str], doc_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None,
                       document_type: Optional[str] = None,
                       properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upload scanned document to API.
        
        Strategy: Create document with first page, then append remaining pages one by one.
        When ZIP compression is enabled, supports bundling multiple pages per ZIP.
        
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
        
        compression_mode = self.config.upload_compression
        
        if compression_mode == "zip":
            bundle_size = self.config.upload_zip_bundle_size
            bundle_max_bytes = self.config.upload_zip_bundle_max_bytes
            auto_jpeg_threshold = self.config.upload_auto_jpeg_threshold
            auto_jpeg_page_size_bytes = self.config.upload_auto_jpeg_page_size_bytes

            if auto_jpeg_threshold <= 0 and auto_jpeg_page_size_bytes <= 0:
                if any(path.lower().endswith('.png') for path in image_files):
                    self.logger.info(
                        "PNG pages usually compress poorly in ZIP; consider 'scanner.format: jpeg' "
                        "or set upload.auto_jpeg_threshold / upload.auto_jpeg_page_size_bytes"
                    )

            # If any bundling limit is configured, always go through the bundled
            # code path (it may still produce a single bundle).
            if bundle_size > 0 or bundle_max_bytes > 0:
                return self._upload_bundled_zip(
                    image_files,
                    doc_id,
                    metadata,
                    document_type,
                    properties,
                    bundle_size=bundle_size,
                    bundle_max_bytes=bundle_max_bytes,
                    auto_jpeg_threshold=auto_jpeg_threshold,
                    auto_jpeg_page_size_bytes=auto_jpeg_page_size_bytes,
                )

            return self._upload_single_zip(
                image_files,
                doc_id,
                metadata,
                document_type,
                properties,
                auto_jpeg_threshold=auto_jpeg_threshold,
                auto_jpeg_page_size_bytes=auto_jpeg_page_size_bytes,
            )
        
        return self._upload_incremental(image_files, doc_id, metadata, document_type, properties)
    
    def _upload_single_zip(
        self,
        image_files: List[str],
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        auto_jpeg_threshold: int = 0,
        auto_jpeg_page_size_bytes: int = 0,
    ) -> Dict[str, Any]:
        """Upload files as a single ZIP archive."""
        self.logger.info(f"Creating ZIP archive for {len(image_files)} pages")

        optimized_files: List[str] = []
        try:
            total_pages = len(image_files)
            for filepath in image_files:
                optimized_files.append(
                    self._prepare_file_for_zip(
                        filepath,
                        total_pages=total_pages,
                        auto_jpeg_threshold=auto_jpeg_threshold,
                        auto_jpeg_page_size_bytes=auto_jpeg_page_size_bytes,
                    )
                )

            compression_level = self.config.upload_zip_compression_level
            zip_path = self._compress_to_zip(optimized_files, compression_level)

            zip_size = self._file_size_bytes(zip_path)
            self.logger.info(f"ZIP payload size: {_format_size(zip_size)} ({len(optimized_files)} pages)")

            result = self._create_document(
                [zip_path],
                doc_id=doc_id,
                metadata=metadata,
                document_type=document_type,
                properties=properties,
            )

            result.update({
                'payload_bytes': zip_size,
                'payload_human': _format_size(zip_size),
                'bundles': 1,
            })

            if os.path.exists(zip_path):
                os.remove(zip_path)

            return result

        except Exception as e:
            error_msg = f"Failed to upload ZIP: {e}"
            self.logger.error(error_msg)
            self.log_error(error_msg, level="error", details={"file_count": len(image_files)})
            raise UploadError(error_msg)
    
    def _upload_bundled_zip(
        self,
        image_files: List[str],
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        bundle_size: int = 0,
        bundle_max_bytes: int = 0,
        auto_jpeg_threshold: int = 0,
        auto_jpeg_page_size_bytes: int = 0,
    ) -> Dict[str, Any]:
        """Upload files as one or more ZIP bundles."""
        total_pages = len(image_files)

        limits = []
        if bundle_size > 0:
            limits.append(f"{bundle_size} page(s)")
        if bundle_max_bytes > 0:
            limits.append(f"{_format_size(bundle_max_bytes)}")
        limits_str = ", ".join(limits) if limits else "unlimited"

        self.logger.info(f"ZIP bundling enabled ({limits_str}) for {total_pages} page(s)")

        prepared_files: List[str] = []
        for filepath in image_files:
            prepared_files.append(
                self._prepare_file_for_zip(
                    filepath,
                    total_pages=total_pages,
                    auto_jpeg_threshold=auto_jpeg_threshold,
                    auto_jpeg_page_size_bytes=auto_jpeg_page_size_bytes,
                )
            )

        bundles = self._build_zip_bundles(prepared_files, bundle_size=bundle_size, bundle_max_bytes=bundle_max_bytes)
        compression_level = self.config.upload_zip_compression_level

        created_doc_id: Optional[str] = None
        total_pages_uploaded = 0
        bundle_payload_bytes: List[int] = []

        for bundle_num, bundle_files in enumerate(bundles, start=1):
            self.logger.info(f"Processing bundle {bundle_num}/{len(bundles)} ({len(bundle_files)} pages)")

            zip_path = self._compress_to_zip(bundle_files, compression_level)
            zip_size = self._file_size_bytes(zip_path)
            bundle_payload_bytes.append(zip_size)

            self.logger.info(f"Bundle {bundle_num} payload: {_format_size(zip_size)}")
            if bundle_max_bytes > 0 and zip_size > bundle_max_bytes:
                self.logger.warning(
                    f"Bundle {bundle_num} exceeds zip_bundle_max_bytes ({_format_size(zip_size)} > {_format_size(bundle_max_bytes)})"
                )

            try:
                if bundle_num == 1:
                    result = self._create_document(
                        [zip_path],
                        doc_id=doc_id,
                        metadata=metadata,
                        document_type=document_type,
                        properties=properties,
                    )
                    created_doc_id = result.get('doc_id')
                    if created_doc_id:
                        self.logger.info(f"Document created: {created_doc_id}")
                    pages_added = result.get('pages_added', len(bundle_files))
                else:
                    if not created_doc_id:
                        raise UploadError("Missing document ID for bundle append")
                    result = self._append_pages(str(created_doc_id), [zip_path])
                    pages_added = result.get('pages_added', len(bundle_files))

                total_pages_uploaded += pages_added

            except Exception as e:
                error_msg = f"Failed to upload bundle {bundle_num}: {e}"
                self.logger.error(error_msg)
                self.log_error(error_msg, level="error", details={"bundle": bundle_num, "files": len(bundle_files)})
                raise UploadError(error_msg)
            finally:
                if os.path.exists(zip_path):
                    os.remove(zip_path)

        total_payload = sum(bundle_payload_bytes)
        self.logger.info(
            f"All bundles uploaded: {total_pages_uploaded} pages ({len(bundles)} bundle(s), {_format_size(total_payload)})"
        )

        return {
            'success': True,
            'doc_id': created_doc_id,
            'pages_added': total_pages_uploaded,
            'total_pages': total_pages_uploaded,
            'bundles': len(bundles),
            'bundle_payload_bytes': bundle_payload_bytes,
            'total_payload_bytes': total_payload,
            'payload_bytes': total_payload,
            'payload_human': _format_size(total_payload),
        }
    
    def _upload_incremental(self, image_files: List[str], doc_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None,
                           document_type: Optional[str] = None,
                           properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upload files incrementally page by page."""
        self.logger.info(f"Uploading {len(image_files)} pages incrementally")
        
        first_page = image_files[0]
        first_size = os.path.getsize(first_page)
        self.logger.info(f"First page payload: {_format_size(first_size)}")
        
        result = self._create_document(
            [first_page],
            doc_id=doc_id,
            metadata=metadata,
            document_type=document_type,
            properties=properties
        )
        
        created_doc_id = result.get('doc_id')
        if not created_doc_id:
            raise UploadError("Failed to get document ID from create response")
        
        self.logger.info(f"Document created with ID: {created_doc_id}")
        
        total_pages_added = result.get('pages_added', 1)
        
        if len(image_files) > 1:
            for i, page_file in enumerate(image_files[1:], start=2):
                page_size = os.path.getsize(page_file)
                self.logger.info(f"Appending page {i}/{len(image_files)}: {_format_size(page_size)}")
                
                append_result = self._append_pages(created_doc_id, [page_file])
                total_pages_added += append_result.get('pages_added', 1)
                
                self.logger.info(f"Page {i} appended. Total pages: {append_result.get('total_pages', total_pages_added)}")
        
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
            payload_bytes = 0

            for image_file in image_files:
                if not os.path.exists(image_file):
                    self.logger.warning(f"File not found, skipping: {image_file}")
                    continue

                filename = os.path.basename(image_file)
                content_type = self._guess_mime_type(image_file)
                size_bytes = self._file_size_bytes(image_file)
                payload_bytes += size_bytes

                self.logger.debug(f"Payload file: {filename} ({_format_size(size_bytes)})")
                files.append(('files', (filename, open(image_file, 'rb'), content_type)))
            
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
            
            self.logger.info(
                f"Uploading payload: {len(files)} file(s), {_format_size(payload_bytes)} -> {api_url}"
            )

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
            payload_bytes = 0

            for image_file in image_files:
                if not os.path.exists(image_file):
                    self.logger.warning(f"File not found, skipping: {image_file}")
                    continue

                filename = os.path.basename(image_file)
                content_type = self._guess_mime_type(image_file)
                size_bytes = self._file_size_bytes(image_file)
                payload_bytes += size_bytes

                self.logger.debug(f"Payload file: {filename} ({_format_size(size_bytes)})")
                files.append(('files', (filename, open(image_file, 'rb'), content_type)))
            
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
            
            self.logger.info(
                f"Uploading payload: {len(files)} file(s), {_format_size(payload_bytes)} -> {api_url}"
            )

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