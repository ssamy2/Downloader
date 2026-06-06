import aiohttp
import base64
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class AnonStoriesDownloader:
    def __init__(self):
        self.sec = "LTE6Om11cmllbGdhbGxlOjpySlAydEJSS2Y2a3RiUnFQVUJ0UkU5a2xnQldiN2Q-"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://anonstories.com",
            "Referer": "https://anonstories.com/",
            "Connection": "keep-alive"
        }
        self.api_url = "https://anonstories.com/api/v1/story"

    def _tokn(self, u: str) -> str:
        """Generate auth token for anonstories API"""
        x = base64.b64encode(f"-1::{u.lower()}::{self.sec}".encode()).decode()
        return x.replace("+", ".").replace("/", "_").replace("=", "-")

    def fix_url(self, u: str) -> str:
        """Fix base64 encoded URLs from anonstories"""
        if not u:
            return ""
        if u.startswith("http"):
            return u
        try:
            t = u.split("/")[-1]
            t = t.replace("-", "=").replace("_", "/").replace(".", "+")
            t += "=" * (-len(t) % 4)
            return base64.b64decode(t).decode()
        except Exception as e:
            logger.error(f"Error fixing URL: {e}")
            return u

    async def get_stories(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user info and active stories.
        Returns dict containing 'user_info' and 'stories'.
        """
        username = username.replace('@', '').strip().lower()
        if not username:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    data={"auth": self._tokn(username)},
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.warning(f"AnonStories API returned status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"AnonStories request failed: {e}")
            return None

anon_stories = AnonStoriesDownloader()
