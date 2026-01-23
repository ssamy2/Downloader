"""
Instagram Online Scrapers - Using external download services
Supports: igram.world, sssinstagram.com via web scraping
"""
import re
import json
import asyncio
import logging
from typing import Optional, Dict
from urllib.parse import quote, urlencode, unquote

logger = logging.getLogger(__name__)


class IgramScraper:
    """Scraper for igram.world using web scraping"""
    
    BASE_URL = "https://igram.world"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://igram.world/',
    }
    
    async def get_video_url(self, instagram_url: str) -> Optional[Dict[str, str]]:
        """Get video download URL from igram.world via web scraping"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            # Step 1: Get the main page to get cookies/tokens
            async with aiohttp.ClientSession() as session:
                # Get main page
                async with session.get(
                    f"{self.BASE_URL}/en1/",
                    headers=self.HEADERS,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        logger.error(f"igram.world main page returned {response.status}")
                        return None
                    
                    html = await response.text()
                
                # Extract CSRF token or other required tokens from page
                # The site uses JavaScript to make API calls, so we need to simulate that
                
                # Try the API endpoint with proper headers
                api_headers = {
                    **self.HEADERS,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': 'https://igram.world',
                    'X-Requested-With': 'XMLHttpRequest',
                }
                
                # Try multiple API endpoints
                api_endpoints = [
                    'https://api.igram.world/api/convert',
                    'https://igram.world/api/convert',
                    'https://v3.igram.world/api/convert',
                ]
                
                for api_url in api_endpoints:
                    try:
                        payload = f'url={quote(instagram_url, safe="")}'
                        
                        async with session.post(
                            api_url,
                            data=payload,
                            headers=api_headers,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as api_response:
                            if api_response.status == 200:
                                data = await api_response.json()
                                
                                # Parse response
                                if isinstance(data, list) and len(data) > 0:
                                    for item in data:
                                        urls = item.get('url', [])
                                        if urls:
                                            video_url = urls[0].get('url') if isinstance(urls, list) else urls
                                            if video_url:
                                                return {
                                                    'video_url': video_url,
                                                    'thumbnail': item.get('thumb'),
                                                    'title': item.get('title', ''),
                                                }
                    except Exception as e:
                        logger.debug(f"API {api_url} failed: {e}")
                        continue
                
                return None
                    
        except Exception as e:
            logger.error(f"igram.world scraper error: {e}")
            return None


class SSSInstagramScraper:
    """Scraper for sssinstagram.com using web scraping"""
    
    BASE_URL = "https://sssinstagram.com"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://sssinstagram.com/',
    }
    
    async def get_video_url(self, instagram_url: str) -> Optional[Dict[str, str]]:
        """Get video download URL from sssinstagram.com via web scraping"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Try the API endpoint
                api_headers = {
                    **self.HEADERS,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': 'https://sssinstagram.com',
                    'X-Requested-With': 'XMLHttpRequest',
                }
                
                api_endpoints = [
                    'https://api.sssinstagram.com/api/convert',
                    'https://sssinstagram.com/api/convert',
                    'https://v3.sssinstagram.com/api/convert',
                ]
                
                for api_url in api_endpoints:
                    try:
                        payload = f'url={quote(instagram_url, safe="")}'
                        
                        async with session.post(
                            api_url,
                            data=payload,
                            headers=api_headers,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as api_response:
                            if api_response.status == 200:
                                data = await api_response.json()
                                
                                # Parse response
                                if isinstance(data, list) and len(data) > 0:
                                    for item in data:
                                        urls = item.get('url', [])
                                        if urls:
                                            video_url = urls[0].get('url') if isinstance(urls, list) else urls
                                            if video_url:
                                                return {
                                                    'video_url': video_url,
                                                    'thumbnail': item.get('thumb'),
                                                    'title': item.get('title', ''),
                                                }
                    except Exception as e:
                        logger.debug(f"API {api_url} failed: {e}")
                        continue
                
                return None
                    
        except Exception as e:
            logger.error(f"sssinstagram.com scraper error: {e}")
            return None


class SaveInstaDownloader:
    """Alternative scraper using saveinsta.app"""
    
    BASE_URL = "https://saveinsta.app"
    API_URL = "https://saveinsta.app/api/ajaxSearch"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://saveinsta.app',
        'Referer': 'https://saveinsta.app/',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    async def get_video_url(self, instagram_url: str) -> Optional[Dict[str, str]]:
        """Get video download URL from saveinsta.app"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # First get the page to get any tokens
                async with session.get(
                    self.BASE_URL,
                    headers=self.HEADERS,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        return None
                    html = await response.text()
                
                # Extract token from page
                token_match = re.search(r'name="token"\s+value="([^"]+)"', html)
                token = token_match.group(1) if token_match else ''
                
                # Make API request
                payload = {
                    'q': instagram_url,
                    't': 'media',
                    'lang': 'en',
                    'token': token,
                }
                
                async with session.post(
                    self.API_URL,
                    data=payload,
                    headers=self.HEADERS,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as api_response:
                    if api_response.status != 200:
                        return None
                    
                    data = await api_response.json()
                    
                    if data.get('status') == 'ok' and data.get('data'):
                        # Parse HTML response
                        html_data = data['data']
                        
                        # Extract video URL from HTML
                        video_match = re.search(r'href="([^"]+\.mp4[^"]*)"', html_data)
                        if video_match:
                            video_url = video_match.group(1)
                            # Decode HTML entities
                            video_url = video_url.replace('&amp;', '&')
                            
                            return {
                                'video_url': video_url,
                                'thumbnail': None,
                                'title': '',
                            }
                
                return None
                    
        except Exception as e:
            logger.error(f"saveinsta.app scraper error: {e}")
            return None


class InstagramOnlineDownloader:
    """Combined Instagram downloader using multiple online services"""
    
    def __init__(self):
        self.igram = IgramScraper()
        self.sssinstagram = SSSInstagramScraper()
        self.saveinsta = SaveInstaDownloader()
    
    async def get_video_url(self, instagram_url: str) -> Optional[Dict[str, str]]:
        """
        Try multiple services to get video URL
        Returns first successful result
        """
        # Try saveinsta.app first (most reliable)
        logger.info("Trying saveinsta.app...")
        result = await self.saveinsta.get_video_url(instagram_url)
        if result and result.get('video_url'):
            logger.info("saveinsta.app succeeded!")
            return result
        
        # Try igram.world
        logger.info("Trying igram.world...")
        result = await self.igram.get_video_url(instagram_url)
        if result and result.get('video_url'):
            logger.info("igram.world succeeded!")
            return result
        
        # Fallback to sssinstagram.com
        logger.info("Trying sssinstagram.com...")
        result = await self.sssinstagram.get_video_url(instagram_url)
        if result and result.get('video_url'):
            logger.info("sssinstagram.com succeeded!")
            return result
        
        logger.error("All online scrapers failed")
        return None


# Test function
async def test_scrapers():
    logging.basicConfig(level=logging.INFO)
    
    url = "https://www.instagram.com/reel/DTvV6AHiLyK/"
    
    print("=" * 60)
    print("Testing Instagram Online Scrapers")
    print("=" * 60)
    print(f"URL: {url}")
    print()
    
    downloader = InstagramOnlineDownloader()
    result = await downloader.get_video_url(url)
    
    if result:
        print(f"✅ Success!")
        print(f"Video URL: {result['video_url'][:100]}...")
        print(f"Thumbnail: {result.get('thumbnail', 'N/A')}")
        print(f"Title: {result.get('title', 'N/A')}")
    else:
        print("❌ All scrapers failed")


if __name__ == "__main__":
    asyncio.run(test_scrapers())
