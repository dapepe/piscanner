"""HTTP server for piscan control and monitoring."""

import json
import os
import threading
import time
from typing import Dict, Any, Optional

# Simple logger fallback
class Logger:
    def info(self, msg, *args): print(f"INFO: {msg % args}")
    def error(self, msg, *args): print(f"ERROR: {msg % args}")
    def debug(self, msg, *args): print(f"DEBUG: {msg % args}")
    def warning(self, msg, *args): print(f"WARNING: {msg % args}")

Flask: Any = None
request: Any = None
jsonify: Any = None
Response: Any = None

try:
    from flask import Flask, request, jsonify, Response
except ImportError:
    print("Warning: Flask not available. HTTP server will be disabled.")


class ScanServer:
    """HTTP server for scan control and monitoring."""
    
    def __init__(self, config, scan_manager):
        """Initialize scan server.
        
        Args:
            config: Configuration object
            scan_manager: ScanManager instance
        """
        self.config = config
        self.scan_manager = scan_manager
        self.logger = Logger()
        self.enabled = Flask is not None
        
        if not self.enabled:
            self.logger.warning("Flask not available - HTTP server disabled")
            return
        
        self.app = Flask(__name__)
        self.setup_routes()
        self.server_thread = None
        self.running = False
    
    def setup_routes(self):
        """Setup Flask routes."""
        if not self.enabled:
            return
        
        @self.app.route('/scan', methods=['POST'])
        def trigger_scan():
            """Trigger a scan job."""
            try:
                # Check if already scanning
                if self.scan_manager.is_scanning():
                    return jsonify({
                        'error': 'Scanner busy',
                        'status': 'busy'
                    }), 409
                
                # Get optional parameters from request
                data = request.get_json() or {}
                source = data.get('source')
                doc_id = data.get('doc_id')
                metadata = data.get('metadata', {})
                document_type = data.get('document_type')
                properties = data.get('properties', {})
                
                # Start scan in background thread
                def scan_job():
                    try:
                        self.scan_manager.perform_scan(
                            source=source,
                            doc_id=doc_id,
                            metadata=metadata,
                            document_type=document_type,
                            properties=properties
                        )
                    except Exception as e:
                        self.logger.error(f"Background scan job failed: {e}")
                
                thread = threading.Thread(target=scan_job, daemon=True)
                thread.start()
                
                return jsonify({
                    'status': 'started',
                    'message': 'Scan job started'
                })
                
            except Exception as e:
                self.logger.error(f"Error triggering scan: {e}")
                return jsonify({
                    'error': str(e),
                    'status': 'error'
                }), 500
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            """Get current scanner status."""
            try:
                status = {
                    'scanning': self.scan_manager.is_scanning(),
                    'scanner_available': self.scan_manager.scanner_available(),
                    'last_scan': self.scan_manager.get_last_scan_info(),
                    'server_time': time.time()
                }
                
                return jsonify(status)
                
            except Exception as e:
                self.logger.error(f"Error getting status: {e}")
                return jsonify({
                    'error': str(e)
                }), 500
        
        @self.app.route('/logs', methods=['GET'])
        def get_logs():
            """Get recent log entries."""
            try:
                # Get query parameters
                lines = request.args.get('lines', 100, type=int)
                level = request.args.get('level', '').upper()
                
                # Read log file
                log_content = self._read_log_file(lines, level)
                
                if request.args.get('format') == 'json':
                    return jsonify({
                        'logs': log_content.split('\n') if log_content else []
                    })
                else:
                    return Response(log_content or 'No logs available', 
                                  mimetype='text/plain')
                
            except Exception as e:
                self.logger.error(f"Error getting logs: {e}")
                return jsonify({
                    'error': str(e)
                }), 500
        
        @self.app.route('/scanner/info', methods=['GET'])
        def get_scanner_info():
            """Get scanner information."""
            try:
                info = self.scan_manager.get_scanner_info()
                return jsonify(info)
                
            except Exception as e:
                self.logger.error(f"Error getting scanner info: {e}")
                return jsonify({
                    'error': str(e)
                }), 500
        
        @self.app.route('/config', methods=['GET'])
        def get_config():
            """Get current configuration (safe values only)."""
            try:
                safe_config = {
                    'config_path': getattr(self.config, 'config_path', None),
                    'scanner': {
                        'resolution': self.config.scanner_resolution,
                        'mode': self.config.scanner_mode,
                        'source': self.config.scanner_source,
                        'format': self.config.scanner_format,
                        'color_correction': self.config.scanner_color_correction
                    },
                    'api': {
                        'workspace': self.config.api_workspace,
                        'url': self.config.api_url,
                        'timeout': self.config.api_timeout
                    },
                    'processing': {
                        'skip_blank': self.config.skip_blank,
                        'blank_threshold': self.config.blank_threshold
                    },
                    'upload': {
                        'compression': self.config.upload_compression,
                        'image_quality': self.config.upload_image_quality,
                        'optimize_png': self.config.upload_optimize_png,
                        'zip_bundle_size': self.config.upload_zip_bundle_size,
                        'zip_bundle_max_bytes': self.config.upload_zip_bundle_max_bytes,
                        'zip_compression_level': self.config.upload_zip_compression_level,
                        'auto_jpeg_threshold': self.config.upload_auto_jpeg_threshold,
                        'auto_jpeg_page_size_bytes': self.config.upload_auto_jpeg_page_size_bytes,
                        'max_image_dimension': self.config.upload_max_image_dimension,
                    },
                    'server': {
                        'host': self.config.server_host,
                        'port': self.config.server_port
                    }
                }
                return jsonify(safe_config)
                
            except Exception as e:
                self.logger.error(f"Error getting config: {e}")
                return jsonify({
                    'error': str(e)
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time()
            })
    
    def _read_log_file(self, lines: int = 100, level: str = '') -> str:
        """Read recent lines from log file.
        
        Args:
            lines: Number of lines to read
            level: Filter by log level
            
        Returns:
            Log content as string
        """
        try:
            log_file = self.config.log_file
            if not log_file or not os.path.exists(log_file):
                return ""
            
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
            
            # Get last N lines
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            # Filter by level if specified
            if level:
                recent_lines = [line for line in recent_lines if level in line]
            
            return ''.join(recent_lines)
            
        except Exception as e:
            self.logger.error(f"Error reading log file: {e}")
            return f"Error reading logs: {e}"
    
    def start(self):
        """Start HTTP server."""
        if not self.enabled:
            self.logger.warning("HTTP server not available")
            return
        
        if self.running:
            self.logger.warning("HTTP server already running")
            return
        
        def run_server():
            self.app.run(  # type: ignore
                host=self.config.server_host,
                port=self.config.server_port,
                debug=self.config.server_debug,
                use_reloader=False,
                threaded=True
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        
        self.logger.info(f"HTTP server started on {self.config.server_host}:{self.config.server_port}")
    
    def stop(self):
        """Stop the HTTP server."""
        if not self.running:
            return
        
        # Flask doesn't provide a clean way to stop from outside
        # This is a limitation of the simple approach
        self.running = False
        self.logger.info("HTTP server stop requested")
    
    def is_running(self) -> bool:
        """Check if server is running.
        
        Returns:
            True if server is running
        """
        return self.running