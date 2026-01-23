"""
Automatic Cookie Manager for Instagram
Handles cookie refresh and validation
"""
import os
import re
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class CookieManager:
    """Manages Instagram cookies with automatic refresh"""
    
    COOKIES_FILE = "cookies.txt"
    COOKIES_BACKUP = "cookies.txt.backup"
    COOKIE_LOG = "logs/cookie_manager.log"
    
    # Cookie expiry check interval (24 hours)
    CHECK_INTERVAL = 24 * 60 * 60
    
    # Cookie warning threshold (7 days before expiry)
    WARNING_THRESHOLD = 7 * 24 * 60 * 60
    
    def __init__(self):
        self.cookies_path = Path(self.COOKIES_FILE)
        self.backup_path = Path(self.COOKIES_BACKUP)
        self.log_path = Path(self.COOKIE_LOG)
        self.log_path.parent.mkdir(exist_ok=True)
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for cookie manager"""
        handler = logging.FileHandler(self.log_path)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    def load_cookies(self) -> Optional[Dict[str, str]]:
        """Load cookies from file in Netscape format"""
        try:
            if not self.cookies_path.exists():
                logger.warning("Cookies file not found")
                return None
            
            cookies = {}
            with open(self.cookies_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        domain = parts[0]
                        name = parts[5]
                        value = parts[6]
                        expiry = int(parts[4])
                        
                        cookies[name] = {
                            'value': value,
                            'domain': domain,
                            'expiry': expiry
                        }
            
            logger.info(f"Loaded {len(cookies)} cookies")
            return cookies
            
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return None
    
    def save_cookies(self, cookies: Dict[str, Dict]) -> bool:
        """Save cookies to file in Netscape format"""
        try:
            # Backup existing cookies
            if self.cookies_path.exists():
                self.cookies_path.rename(self.backup_path)
            
            # Write new cookies
            with open(self.cookies_path, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This is a generated file!  Do not edit.\n\n")
                
                for name, cookie_data in cookies.items():
                    domain = cookie_data.get('domain', '.instagram.com')
                    value = cookie_data.get('value', '')
                    expiry = cookie_data.get('expiry', 9999999999)
                    
                    # Format: domain flag path secure expiry name value
                    line = f"{domain}\tTRUE\t/\tTRUE\t{expiry}\t{name}\t{value}\n"
                    f.write(line)
            
            logger.info(f"Saved {len(cookies)} cookies")
            return True
            
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")
            # Restore backup
            if self.backup_path.exists():
                self.backup_path.rename(self.cookies_path)
            return False
    
    def get_cookie_status(self) -> Dict[str, any]:
        """Get status of current cookies"""
        cookies = self.load_cookies()
        
        if not cookies:
            return {
                'status': 'no_cookies',
                'message': 'No cookies found',
                'needs_refresh': True
            }
        
        now = datetime.now().timestamp()
        status = {
            'status': 'loaded',
            'total_cookies': len(cookies),
            'cookies': {}
        }
        
        for name, cookie_data in cookies.items():
            expiry = cookie_data.get('expiry', 0)
            expires_in = expiry - now
            
            if expires_in < 0:
                status['cookies'][name] = {
                    'status': 'expired',
                    'expires_in_days': 0
                }
            elif expires_in < self.WARNING_THRESHOLD:
                status['cookies'][name] = {
                    'status': 'warning',
                    'expires_in_days': int(expires_in / 86400)
                }
            else:
                status['cookies'][name] = {
                    'status': 'valid',
                    'expires_in_days': int(expires_in / 86400)
                }
        
        # Check if any cookies are expired
        expired = [c for c in status['cookies'].values() if c['status'] == 'expired']
        status['needs_refresh'] = len(expired) > 0
        
        return status
    
    def validate_cookies(self) -> bool:
        """Validate if cookies are still valid"""
        status = self.get_cookie_status()
        
        if status['status'] == 'no_cookies':
            logger.warning("No cookies available")
            return False
        
        if status.get('needs_refresh'):
            logger.warning("Cookies need refresh - some are expired")
            return False
        
        logger.info("Cookies are valid")
        return True
    
    async def refresh_cookies_async(self) -> bool:
        """Attempt to refresh cookies asynchronously"""
        try:
            import subprocess
            
            logger.info("Attempting to refresh cookies...")
            
            # Try to get new cookies from browser
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [
                        'yt-dlp',
                        '--cookies-from-browser', 'firefox',
                        '--cookies', str(self.cookies_path),
                        'https://www.instagram.com',
                        '--skip-download'
                    ],
                    capture_output=True,
                    timeout=60
                )
            )
            
            if result.returncode == 0:
                logger.info("Cookies refreshed successfully")
                return True
            else:
                logger.error(f"Cookie refresh failed: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing cookies: {e}")
            return False
    
    def get_cookies_dict(self) -> Dict[str, str]:
        """Get cookies as simple dict for requests"""
        cookies = self.load_cookies()
        if not cookies:
            return {}
        
        return {name: data['value'] for name, data in cookies.items()}
    
    def print_status(self):
        """Print cookie status to console"""
        status = self.get_cookie_status()
        
        print("\n" + "="*60)
        print("🍪 Cookie Status")
        print("="*60)
        
        if status['status'] == 'no_cookies':
            print("❌ No cookies found")
            print("\nTo add cookies:")
            print("1. Open Firefox and go to https://www.instagram.com")
            print("2. Log in with your account")
            print("3. Run: yt-dlp --cookies-from-browser firefox --cookies cookies.txt https://www.instagram.com --skip-download")
            return
        
        print(f"✅ Total cookies: {status['total_cookies']}")
        print()
        
        for name, cookie_status in status['cookies'].items():
            status_icon = {
                'valid': '✅',
                'warning': '⚠️',
                'expired': '❌'
            }.get(cookie_status['status'], '❓')
            
            days = cookie_status['expires_in_days']
            print(f"{status_icon} {name}: {days} days remaining")
        
        if status.get('needs_refresh'):
            print("\n⚠️  Some cookies need refresh!")
        
        print("="*60 + "\n")


# Periodic cookie checker
async def cookie_checker_task():
    """Background task to check and refresh cookies"""
    manager = CookieManager()
    
    while True:
        try:
            # Check cookie status
            if not manager.validate_cookies():
                logger.warning("Cookies invalid - attempting refresh")
                await manager.refresh_cookies_async()
            
            # Wait before next check
            await asyncio.sleep(manager.CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Cookie checker error: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = CookieManager()
    manager.print_status()
    
    # Test loading cookies
    cookies = manager.load_cookies()
    if cookies:
        print(f"\n✅ Loaded {len(cookies)} cookies")
    else:
        print("\n❌ No cookies loaded")
