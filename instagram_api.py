"""
Instagram Video Downloader - Based on Instagram-reels-downloader
Uses Instagram's GraphQL API and webpage scraping
"""
import re
import requests
import json
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class InstagramDownloader:
    """Instagram video downloader using GraphQL and webpage methods"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        })
    
    def extract_post_id(self, url: str) -> Optional[str]:
        """Extract post ID from Instagram URL"""
        patterns = [
            r'/p/([a-zA-Z0-9_-]+)',
            r'/reel/([a-zA-Z0-9_-]+)',
            r'/reels/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_video_from_webpage(self, post_id: str) -> Optional[Dict[str, str]]:
        """Extract video URL from Instagram webpage meta tags"""
        try:
            url = f"https://www.instagram.com/p/{post_id}/"
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch page: {response.status_code}")
                return None
            
            html = response.text
            
            # Extract video URL from og:video meta tag
            video_match = re.search(r'<meta property="og:video" content="([^"]+)"', html)
            if not video_match:
                logger.warning("No video found in meta tags")
                return None
            
            video_url = video_match.group(1)
            
            # Extract dimensions
            width_match = re.search(r'<meta property="og:video:width" content="([^"]+)"', html)
            height_match = re.search(r'<meta property="og:video:height" content="([^"]+)"', html)
            
            # Extract thumbnail
            thumb_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            
            return {
                'video_url': video_url,
                'width': width_match.group(1) if width_match else '640',
                'height': height_match.group(1) if height_match else '640',
                'thumbnail': thumb_match.group(1) if thumb_match else None
            }
            
        except Exception as e:
            logger.error(f"Webpage extraction error: {e}")
            return None
    
    def get_video_from_graphql(self, post_id: str) -> Optional[Dict[str, str]]:
        """Extract video URL using Instagram's GraphQL API"""
        try:
            # Prepare GraphQL request
            variables = {
                "shortcode": post_id,
                "fetch_comment_count": None,
                "fetch_related_profile_media_count": None,
                "parent_comment_count": None,
                "child_comment_count": None,
                "fetch_like_count": None,
                "fetch_tagged_user_count": None,
                "fetch_preview_comment_count": None,
                "has_threaded_comments": False,
                "hoisted_comment_id": None,
                "hoisted_reply_id": None,
            }
            
            payload = {
                "av": "0",
                "__d": "www",
                "__user": "0",
                "__a": "1",
                "__req": "3",
                "__hs": "19624.HYP:instagram_web_pkg.2.1..0.0",
                "dpr": "3",
                "__ccg": "UNKNOWN",
                "__rev": "1008824440",
                "__s": "xf44ne:zhh75g:xr51e7",
                "__hsi": "7282217488877343271",
                "__dyn": "7xeUmwlEnwn8K2WnFw9-2i5U4e0yoW3q32360CEbo1nEhw2nVE4W0om78b87C0yE5ufz81s8hwGwQwoEcE7O2l0Fwqo31w9a9x-0z8-U2zxe2GewGwso88cobEaU2eUlwhEe87q7-0iK2S3qazo7u1xwIw8O321LwTwKG1pg661pwr86C1mwraCg",
                "__csr": "gZ3yFmJkillQvV6ybimnG8AmhqujGbLADgjyEOWz49z9XDlAXBJpC7Wy-vQTSvUGWGh5u8KibG44dBiigrgjDxGjU0150Q0848azk48N09C02IR0go4SaR70r8owyg9pU0V23hwiA0LQczA48S0f-x-27o05NG0fkw",
                "__comet_req": "7",
                "lsd": "AVqbxe3J_YA",
                "jazoest": "2957",
                "__spin_r": "1008824440",
                "__spin_b": "trunk",
                "__spin_t": "1695523385",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "PolarisPostActionLoadPostQueryQuery",
                "variables": json.dumps(variables),
                "server_timestamps": "true",
                "doc_id": "10015901848480474",
            }
            
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-FB-Friendly-Name': 'PolarisPostActionLoadPostQueryQuery',
                'X-CSRFToken': 'RVDUooU5MYsBbS1CNN3CzVAuEP8oHB52',
                'X-IG-App-ID': '1217981644879628',
                'X-FB-LSD': 'AVqbxe3J_YA',
                'X-ASBD-ID': '129477',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile Safari/537.36',
            }
            
            response = self.session.post(
                'https://www.instagram.com/api/graphql',
                data=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"GraphQL API returned {response.status_code}")
                return None
            
            data = response.json()
            
            # Extract video data from GraphQL response
            media_data = data.get('data', {}).get('xdt_shortcode_media')
            if not media_data:
                logger.warning("No media data in GraphQL response")
                return None
            
            if not media_data.get('is_video'):
                logger.warning("Post is not a video")
                return None
            
            video_url = media_data.get('video_url')
            if not video_url:
                logger.warning("No video URL in GraphQL response")
                return None
            
            dimensions = media_data.get('dimensions', {})
            
            return {
                'video_url': video_url,
                'width': str(dimensions.get('width', 640)),
                'height': str(dimensions.get('height', 640)),
                'thumbnail': media_data.get('display_url'),
                'duration': media_data.get('video_duration', 0),
                'view_count': media_data.get('video_view_count', 0)
            }
            
        except Exception as e:
            logger.error(f"GraphQL extraction error: {e}")
            return None
    
    def download_video(self, url: str) -> Optional[Dict[str, str]]:
        """
        Download Instagram video
        Tries GraphQL first, then falls back to webpage scraping
        """
        post_id = self.extract_post_id(url)
        if not post_id:
            logger.error("Could not extract post ID from URL")
            return None
        
        logger.info(f"Extracted post ID: {post_id}")
        
        # Try GraphQL first (more reliable)
        result = self.get_video_from_graphql(post_id)
        if result:
            logger.info("Successfully extracted video using GraphQL")
            return result
        
        # Fallback to webpage scraping
        logger.info("GraphQL failed, trying webpage scraping")
        result = self.get_video_from_webpage(post_id)
        if result:
            logger.info("Successfully extracted video from webpage")
            return result
        
        logger.error("All methods failed")
        return None


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    downloader = InstagramDownloader()
    url = "https://www.instagram.com/reel/DTvV6AHiLyK/"
    
    print(f"Testing Instagram downloader with: {url}")
    result = downloader.download_video(url)
    
    if result:
        print(f"✅ Success!")
        print(f"Video URL: {result['video_url'][:100]}...")
        print(f"Dimensions: {result['width']}x{result['height']}")
        print(f"Thumbnail: {result.get('thumbnail', 'N/A')[:100]}...")
    else:
        print("❌ Failed to download video")
