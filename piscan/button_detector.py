"""Button detection tool for scanner buttons."""

import subprocess
import re
import time
import signal
import sys
from typing import Dict, List, Optional
# Simple logger fallback
class Logger:
    def info(self, msg, *args): print(f"INFO: {msg % args}")
    def error(self, msg, *args): print(f"ERROR: {msg % args}")
    def debug(self, msg, *args): print(f"DEBUG: {msg % args}")
    def warning(self, msg, *args): print(f"WARNING: {msg % args}")


class ButtonDetector:
    """Detects and identifies scanner button presses."""
    
    def __init__(self, config):
        """Initialize button detector.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = Logger()
        self.running = False
        self.detected_buttons = []
    
    def test_buttons(self, duration: int = 30) -> Dict[str, any]:  # type: ignore
        """Test button detection for specified duration.
        
        Args:
            duration: Duration in seconds to monitor for button presses
            
        Returns:
            Dictionary with test results
        """
        self.logger.info(f"Starting button detection test for {duration} seconds")
        self.logger.info("Press buttons on your scanner now...")
        
        self.running = True
        self.detected_buttons = []
        
        # Set up signal handler for early exit
        def signal_handler(sig, frame):
            self.logger.info("Button detection stopped by user")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        start_time = time.time()
        
        try:
            while self.running and (time.time() - start_time) < duration:
                # Method 1: Try scanimage -A to detect button changes
                button_info = self._check_scanimage_buttons()
                if button_info:
                    self.detected_buttons.append(button_info)
                    self.logger.info(f"Button detected via scanimage: {button_info}")
                
                # Method 2: Check if scanbd is available and running
                scanbd_info = self._check_scanbd_status()
                if scanbd_info:
                    self.logger.info(f"scanbd status: {scanbd_info}")
                
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            self.logger.info("Button detection interrupted")
        finally:
            self.running = False
            signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        return self._generate_test_report()
    
    def _check_scanimage_buttons(self) -> Optional[Dict[str, any]]:  # type: ignore
        """Check for button changes using scanimage -A.
        
        Returns:
            Button information if detected, None otherwise
        """
        try:
            result = subprocess.run([
                'scanimage', '-d', self.config.scanner_device, '-A'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Look for button-related options
                button_patterns = [
                    r'button[-\s]*(\w+).*?=\s*(\d+)',
                    r'scan[-\s]*button.*?=\s*(\d+)',
                    r'(\w+)[- \t]*button.*?=\s*(\d+)'
                ]
                
                for pattern in button_patterns:
                    matches = re.findall(pattern, result.stdout, re.IGNORECASE)
                    if matches:
                        for button_name, value in matches:
                            if int(value) == 1:  # Button pressed
                                return {
                                    'method': 'scanimage',
                                    'button': button_name,
                                    'value': value,
                                    'timestamp': time.time()
                                }
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            self.logger.debug(f"scanimage button check failed: {e}")
        
        return None
    
    def _check_scanbd_status(self) -> Optional[Dict[str, any]]:  # type: ignore
        """Check scanbd daemon status.
        
        Returns:
            scanbd status information if available
        """
        try:
            # Check if scanbd is running
            result = subprocess.run([
                'systemctl', 'is-active', 'scanbd'
            ], capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                return {
                    'service': 'scanbd',
                    'status': 'active',
                    'method': 'systemctl'
                }
            else:
                return {
                    'service': 'scanbd',
                    'status': 'inactive',
                    'method': 'systemctl'
                }
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Try alternative method
            try:
                result = subprocess.run([
                    'pgrep', '-f', 'scanbd'
                ], capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0:
                    return {
                        'service': 'scanbd',
                        'status': 'running',
                        'method': 'pgrep'
                    }
                else:
                    return {
                        'service': 'scanbd',
                        'status': 'not running',
                        'method': 'pgrep'
                    }
            except Exception:
                pass
        
        return None
    
    def _generate_test_report(self) -> Dict[str, any]:  # type: ignore
        """Generate a report from button detection test.
        
        Returns:
            Dictionary with test results and recommendations
        """
        report = {
            'test_duration': len(self.detected_buttons),
            'buttons_detected': self.detected_buttons,
            'recommendations': []
        }
        
        if not self.detected_buttons:
            report['recommendations'].extend([
                "No buttons were detected during the test period.",
                "Consider installing and configuring scanbd for button detection.",
                "Check if your scanner supports button events in Linux.",
                "Try running 'scanimage -A' manually to see available options."
            ])
        else:
            report['recommendations'].extend([
                f"Detected {len(self.detected_buttons)} button events.",
                "Configure scanbd to trigger actions when these buttons are pressed.",
                "Use the detected button names in your scanbd configuration."
            ])
        
        # Add scanbd setup instructions
        report['scanbd_setup'] = {
            'install': 'sudo apt-get install scanbd',
            'config_file': '/etc/scanbd/scanbd.conf',
            'example_action': '''
action scan {
    filter = "^scan.*"
    numerical-trigger {
        from-value = 1
        to-value   = 0
    }
    desc = "Scan button pressed"
    script = "/etc/scanbd/scan.sh"
}
''',
            'script_example': '''#!/bin/bash
curl -X POST http://localhost:5000/scan
'''
        }
        
        return report
    
    def list_scanner_options(self) -> Dict[str, any]:  # type: ignore
        """List all available scanner options.
        
        Returns:
            Dictionary with scanner options
        """
        try:
            result = subprocess.run([
                'scanimage', '-d', self.config.scanner_device, '-A'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                options = {
                    'device': self.config.scanner_device,
                    'raw_output': result.stdout,
                    'parsed_options': []
                }
                
                # Parse options
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('--'):
                        continue
                    
                    option_match = re.match(r'\s*--(\w+).*?\[(.*?)\]', line)
                    if option_match:
                        option_name = option_match.group(1)
                        option_values = option_match.group(2)
                        
                        options['parsed_options'].append({
                            'name': option_name,
                            'values': option_values,
                            'line': line.strip()
                        })
                
                return options
            else:
                return {
                    'error': result.stderr,
                    'device': self.config.scanner_device
                }
                
        except Exception as e:
            return {
                'error': str(e),
                'device': self.config.scanner_device
            }
    
    def setup_scanbd_integration(self) -> Dict[str, any]:  # type: ignore
        """Provide instructions for scanbd integration.
        
        Returns:
            Dictionary with setup instructions
        """
        return {
            'description': 'Setup scanbd for button detection',
            'steps': [
                '1. Install scanbd: sudo apt-get install scanbd',
                '2. Configure SANE to use net backend',
                '3. Edit /etc/scanbd/scanbd.conf',
                '4. Create action script for button press',
                '5. Start scanbd service'
            ],
            'sane_config': '''
# /etc/sane.d/dll.conf
# Comment out all backends except:
net
''',
            'net_config': '''
# /etc/sane.d/net.conf
localhost
''',
            'scanbd_config': '''
# /etc/scanbd/scanbd.conf
action scan {
    filter = "^scan.*"
    numerical-trigger {
        from-value = 1
        to-value   = 0
    }
    desc = "Scan button pressed"
    script = "/etc/scanbd/scan.sh"
}
''',
            'action_script': '''
#!/bin/bash
# /etc/scanbd/scan.sh
curl -X POST http://localhost:5000/scan
'''
        }