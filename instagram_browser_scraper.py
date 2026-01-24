"""
Instagram Browser Scraper - Using Playwright for reliable downloads
Supports 3 fallback services: sssinstagram.com, snapinsta.to, savefrom.net
"""
import asyncio
import logging
from typing import Optional, Dict
from pathlib import Path
import tempfile
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)


class InstagramBrowserScraper:
    """Instagram scraper using browser automation with multiple fallback services"""
    
    # Service configurations
    SERVICES = {
        'sssinstagram': {
            'url': 'https://sssinstagram.com/reels-downloader',
            'input_selector': 'input[placeholder="Paste link here"]',
            'download_button': 'button:has-text("Download")',
            'download_link': 'a[href*="media.sssinstagram.com"]',
            'wait_time': 3
        },
        'snapinsta': {
            'url': 'https://snapinsta.to/en/instagram-reels-downloader',
            'input_selector': 'input[name="url"]',
            'download_button': 'button:has-text("Download")',
            'download_link': 'a[href*="dl.snapcdn.app"]',
            'wait_time': 5
        },
        'savefrom': {
            'url': 'https://en1.savefrom.net/25-instagram-reels-download-4GZ.html',
            'input_selector': 'input[placeholder*="Paste your video link"]',
            'download_button': 'button:has-text("Download")',
            'download_link': 'a[href*="media.sf-converter.com"]',
            'wait_time': 5
        }
    }
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self._lock = asyncio.Lock()
    
    async def _init_browser(self):
        """Initialize browser with anti-detection settings"""
        try:
            from playwright.async_api import async_playwright
            
            if self.browser is not None:
                return
            
            self.playwright = await async_playwright().start()
            
            # Launch browser with stealth settings
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            # Create context with realistic settings
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # Add anti-detection scripts
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            self.page = await self.context.new_page()
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Browser initialization error: {e}")
            raise
    
    async def _close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Browser close error: {e}")
    
    async def _get_download_link_from_service(self, instagram_url: str, service_name: str) -> Optional[str]:
        """Get download link from a specific service"""
        try:
            service = self.SERVICES[service_name]
            
            # Navigate to service
            await self.page.goto(service['url'], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(1)
            
            # Fill input
            await self.page.fill(service['input_selector'], instagram_url)
            await asyncio.sleep(0.5)
            
            # Click download button
            await self.page.click(service['download_button'])
            
            # Wait for download link
            await asyncio.sleep(service['wait_time'])
            
            # Extract download link
            download_link = await self.page.locator(service['download_link']).first.get_attribute('href', timeout=10000)
            
            if download_link:
                logger.info(f"{service_name}: Successfully got download link")
                return download_link
            
            return None
            
        except Exception as e:
            logger.warning(f"{service_name} failed: {e}")
            return None
    
    async def get_video_url(self, instagram_url: str) -> Optional[Dict[str, str]]:
        """
        Get Instagram video download URL using browser automation
        Tries multiple services with fallback
        """
        async with self._lock:
            try:
                await self._init_browser()
                
                # Try each service in order
                for service_name in ['sssinstagram', 'snapinsta', 'savefrom']:
                    logger.info(f"Trying {service_name}...")
                    
                    download_url = await self._get_download_link_from_service(instagram_url, service_name)
                    
                    if download_url:
                        return {
                            'video_url': download_url,
                            'service': service_name,
                            'thumbnail': None,
                            'title': ''
                        }
                
                logger.error("All services failed")
                return None
                
            except Exception as e:
                logger.error(f"Browser scraper error: {e}")
                return None
            finally:
                # Keep browser open for reuse, but close after timeout
                pass
    
    async def download_video(self, video_url: str, output_path: str, progress_callback=None) -> bool:
        """Download video from URL"""
        try:
            if progress_callback:
                await progress_callback("downloading", 50)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    if response.status != 200:
                        logger.error(f"Download failed: HTTP {response.status}")
                        return False
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    async with aiofiles.open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                progress = 50 + int((downloaded / total_size) * 40)
                                await progress_callback("downloading", progress)
            
            if progress_callback:
                await progress_callback("processing", 95)
            
            logger.info(f"Video downloaded successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup browser resources"""
        await self._close_browser()


class InstagramBrowserManager:
    """Manages multiple browser instances for concurrent downloads"""
    
    def __init__(self, max_browsers: int = 2):
        self.max_browsers = max_browsers
        self.scrapers = []
        self.queue = asyncio.Queue()
        self._lock = asyncio.Lock()
    
    async def get_scraper(self) -> InstagramBrowserScraper:
        """Get or create a scraper instance"""
        async with self._lock:
            # Reuse existing scraper if available
            if self.scrapers:
                return self.scrapers[0]
            
            # Create new scraper
            scraper = InstagramBrowserScraper()
            self.scrapers.append(scraper)
            return scraper
    
    async def download_instagram(self, instagram_url: str, output_path: str, progress_callback=None) -> bool:
        """Download Instagram video with automatic browser management"""
        scraper = await self.get_scraper()
        
        try:
            # Get download URL
            video_data = await scraper.get_video_url(instagram_url)
            
            if not video_data or not video_data.get('video_url'):
                logger.error("Failed to get download URL")
                return False
            
            # Download video
            success = await scraper.download_video(
                video_data['video_url'],
                output_path,
                progress_callback
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    async def cleanup_all(self):
        """Cleanup all browser instances"""
        for scraper in self.scrapers:
            await scraper.cleanup()
        self.scrapers.clear()


# Global manager instance
_browser_manager = None

async def get_browser_manager() -> InstagramBrowserManager:
    """Get global browser manager instance"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = InstagramBrowserManager(max_browsers=2)
    return _browser_manager


# Test function
async def test_instagram_scraper():
    """Test Instagram browser scraper"""
    logging.basicConfig(level=logging.INFO)
    
    url = "https://www.instagram.com/reel/DTxqsPUDZ5x/"
    output = "test_instagram_download.mp4"
    
    print("=" * 60)
    print("Testing Instagram Browser Scraper")
    print("=" * 60)
    print(f"URL: {url}")
    print()
    
    manager = await get_browser_manager()
    
    success = await manager.download_instagram(url, output)
    
    if success:
        print(f"\n✅ Download successful: {output}")
        
        # Check file size
        import os
        size = os.path.getsize(output)
        print(f"File size: {size / 1024 / 1024:.2f} MB")
    else:
        print("\n❌ Download failed")
    
    await manager.cleanup_all()


if __name__ == "__main__":
    asyncio.run(test_instagram_scraper())
