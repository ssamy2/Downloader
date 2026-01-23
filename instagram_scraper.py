"""
Instagram Video Scraper using fastvideosave.net
Bypasses rate limits and bot detection
"""
import requests
import re
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class InstagramScraper:
    """Scraper for Instagram videos using fastvideosave.net"""
    
    def __init__(self):
        self.base_url = "https://fastvideosave.net"
        self.api_url = f"{self.base_url}/download"
        self.session = requests.Session()
        
        # Headers to bypass bot detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        })
    
    def extract_video_url(self, instagram_url: str) -> Optional[Dict[str, str]]:
        """
        Extract direct video URL from Instagram using fastvideosave.net
        
        Args:
            instagram_url: Instagram post/reel URL
            
        Returns:
            Dict with 'video_url' and 'thumbnail' or None if failed
        """
        try:
            # Step 1: Get the main page first to get cookies/session
            self.session.get(self.base_url, timeout=10)
            
            # Step 2: Use the actual API endpoint (discovered from browser inspection)
            api_endpoint = f"{self.base_url}/api/download"
            
            payload = {
                'url': instagram_url
            }
            
            response = self.session.post(
                api_endpoint,
                json=payload,  # Use JSON instead of form data
                timeout=30
            )
            
            if response.status_code != 200:
                logger.warning(f"API returned status {response.status_code}, trying HTML scraping")
                # Fallback: Try direct page scraping
                return self._scrape_from_page(instagram_url)
            
            # Try to parse JSON response
            try:
                data = response.json()
                if data.get('status') == 'success' and data.get('url'):
                    return {
                        'video_url': data['url'],
                        'thumbnail': data.get('thumbnail')
                    }
            except:
                pass
            
            # Step 3: Parse response HTML to extract video URL
            html = response.text
            
            # Method 1: Look for direct download link
            video_pattern = r'href="(https://[^"]*cdninstagram\.com[^"]*\.mp4[^"]*)"'
            matches = re.findall(video_pattern, html)
            
            if matches:
                video_url = matches[0]
                # Clean URL (remove HTML entities)
                video_url = video_url.replace('&amp;', '&')
                
                # Try to extract thumbnail
                thumb_pattern = r'src="(https://[^"]*cdninstagram\.com[^"]*\.jpg[^"]*)"'
                thumb_matches = re.findall(thumb_pattern, html)
                thumbnail = thumb_matches[0] if thumb_matches else None
                
                logger.info(f"Successfully extracted Instagram video URL")
                return {
                    'video_url': video_url,
                    'thumbnail': thumbnail
                }
            
            # Method 2: Look for JSON data in script tags
            json_pattern = r'videoUrl["\']?\s*:\s*["\']([^"\']+)["\']'
            json_matches = re.findall(json_pattern, html)
            
            if json_matches:
                video_url = json_matches[0].replace('\\/', '/')
                return {
                    'video_url': video_url,
                    'thumbnail': None
                }
            
            logger.warning("Could not extract video URL from response")
            return None
            
        except requests.Timeout:
            logger.error("Request timeout")
            return None
        except Exception as e:
            logger.error(f"Instagram scraper error: {e}")
            return None
    
    def _scrape_from_page(self, instagram_url: str) -> Optional[Dict[str, str]]:
        """
        Fallback method: Scrape video URL directly from page HTML
        Simulates browser behavior to bypass bot detection
        """
        try:
            # Use requests-html or selenium-like approach
            import time
            
            # Add delay to simulate human behavior
            time.sleep(1)
            
            # Make request with full browser headers
            response = self.session.get(
                f"{self.base_url}/?url={requests.utils.quote(instagram_url)}",
                timeout=30
            )
            
            if response.status_code == 200:
                html = response.text
                
                # Extract video URL from page
                video_pattern = r'href="(https://[^"]*cdninstagram\.com[^"]*\.mp4[^"]*)"'
                matches = re.findall(video_pattern, html)
                
                if matches:
                    return {
                        'video_url': matches[0].replace('&amp;', '&'),
                        'thumbnail': None
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Page scraping error: {e}")
            return None
    
    def download_video(self, video_url: str, output_path: str) -> bool:
        """
        Download video from direct URL
        
        Args:
            video_url: Direct video URL
            output_path: Path to save video
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(video_url, stream=True, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"Download failed with status {response.status_code}")
                return False
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Video downloaded successfully to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scraper = InstagramScraper()
    url = "https://www.instagram.com/reel/DTvV6AHiLyK/"
    
    print(f"Testing Instagram scraper with: {url}")
    result = scraper.extract_video_url(url)
    
    if result:
        print(f"✅ Success!")
        print(f"Video URL: {result['video_url'][:100]}...")
        print(f"Thumbnail: {result.get('thumbnail', 'N/A')}")
    else:
        print("❌ Failed to extract video URL")
