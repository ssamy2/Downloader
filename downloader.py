"""
Media Downloader module - Cobalt API and yt-dlp integration
"""
import os
import re
import asyncio
import aiohttp
import aiofiles
import subprocess
import logging
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import yt_dlp

from config import config, URL_PATTERNS, QUALITY_SETTINGS

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a download operation"""
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    duration: float = 0
    platform: str = ""
    title: str = ""
    error: Optional[str] = None
    thumbnail: Optional[str] = None


class MediaDownloader:
    """Handles media downloads from various platforms"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOAD_DIR
        self._session: Optional[aiohttp.ClientSession] = None
        self._ensure_download_dir()
    
    def _ensure_download_dir(self) -> None:
        """Ensure download directory exists"""
        os.makedirs(self.download_dir, exist_ok=True)
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=config.COBALT_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self) -> None:
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def detect_platform(self, url: str) -> Optional[str]:
        """Detect platform from URL"""
        for platform, pattern in URL_PATTERNS.items():
            if re.search(pattern, url, re.IGNORECASE):
                return platform
        return None
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract all supported URLs from text"""
        urls = []
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        found_urls = re.findall(url_pattern, text)
        
        for url in found_urls:
            if self.detect_platform(url):
                urls.append(url)
        
        return list(set(urls))  # Remove duplicates
    
    def _generate_filename(self, url: str, ext: str = "mp4") -> str:
        """Generate unique filename based on URL hash"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{url_hash}.{ext}"
    
    async def download(self, url: str, quality: str = "hd", 
                      progress_callback=None, download_audio: bool = False) -> DownloadResult:
        """
        Main download method - tries platform-specific API first, then yt-dlp as fallback
        """
        platform = self.detect_platform(url)
        if not platform:
            return DownloadResult(
                success=False,
                error="Unsupported platform",
                platform="unknown"
            )
        
        logger.info(f"Downloading from {platform}: {url}")
        
        # Try TikTok API first (faster and supports quality selection)
        if platform == 'tiktok':
            result = await self._download_tiktok_api(url, quality, progress_callback, download_audio)
            if result.success:
                return result
            logger.warning("TikTok API failed, falling back to yt-dlp")
        
        # Try Instagram scraper for Instagram (bypasses rate limits)
        if platform == 'instagram':
            result = await self._download_instagram_scraper(url, quality, progress_callback, download_audio)
            if result.success:
                return result
            logger.warning("Instagram scraper failed, falling back to yt-dlp")
        
        # Fallback to yt-dlp for all platforms
        result = await self._download_with_ytdlp(url, quality, platform, progress_callback, download_audio)
        
        # Compress if needed
        if result.success and quality != "original":
            result = await self._process_video(result, quality, progress_callback)
        
        return result
    
    async def _download_instagram_scraper(self, url: str, quality: str,
                                          progress_callback=None, download_audio: bool = False) -> DownloadResult:
        """Download Instagram video using GraphQL API"""
        try:
            import requests
            
            if progress_callback:
                await progress_callback("connecting", 10)
            
            # Extract post ID
            post_id = self._extract_instagram_post_id(url)
            if not post_id:
                raise Exception("Could not extract post ID from URL")
            
            # Try GraphQL API first
            video_data = await self._get_instagram_graphql(post_id)
            
            if not video_data:
                # Fallback to webpage scraping
                video_data = await self._get_instagram_webpage(post_id)
            
            if not video_data or not video_data.get('video_url'):
                raise Exception("Could not extract video URL")
            
            video_url = video_data['video_url']
            
            if progress_callback:
                await progress_callback("downloading", 30)
            
            # Download video
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(video_url, timeout=60, stream=True)
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to download: HTTP {response.status_code}")
            
            # Save file
            ext = "mp3" if download_audio else "mp4"
            filename = self._generate_filename(url, ext)
            file_path = os.path.join(self.download_dir, filename)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(file_path)
            
            # Convert to audio if requested
            if download_audio:
                audio_path = await self._extract_audio(file_path)
                if audio_path:
                    os.remove(file_path)
                    file_path = audio_path
                    file_size = os.path.getsize(file_path)
            
            if progress_callback:
                await progress_callback("downloaded", 90)
            
            return DownloadResult(
                success=True,
                file_path=file_path,
                file_size=file_size,
                platform='instagram',
                title='',
                thumbnail=video_data.get('thumbnail')
            )
            
        except Exception as e:
            logger.error(f"Instagram download error: {e}")
            return DownloadResult(
                success=False,
                error=str(e),
                platform='instagram'
            )
    
    async def _download_tiktok_api(self, url: str, quality: str, 
                                   progress_callback=None, download_audio: bool = False) -> DownloadResult:
        """Download TikTok video using tikwm.com API"""
        try:
            import requests
            
            if progress_callback:
                await progress_callback("connecting", 10)
            
            # Request with HD parameter
            api_url = f"https://www.tikwm.com/api/?url={url}"
            if quality in ['hd', '1080p', '720p', 'original']:
                api_url += "&hd=1"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(api_url, timeout=30)
            )
            
            data = response.json()
            
            if data.get('code') != 0:
                return DownloadResult(
                    success=False,
                    error="TikTok API: Video not available",
                    platform='tiktok'
                )
            
            video_data = data['data']
            
            # Select video URL based on quality
            if quality in ['hd', '1080p', '720p', 'original'] and 'hdplay' in video_data:
                video_url = video_data['hdplay']
                logger.info("Using HD quality from TikTok API")
            else:
                video_url = video_data['play']
                logger.info("Using standard quality from TikTok API")
            
            # Fix URL if relative
            if not video_url.startswith('http'):
                video_url = "https://www.tikwm.com" + video_url
            
            if progress_callback:
                await progress_callback("downloading", 30)
            
            # Download video
            video_response = await loop.run_in_executor(
                None,
                lambda: requests.get(video_url, timeout=60)
            )
            
            if video_response.status_code != 200:
                return DownloadResult(
                    success=False,
                    error=f"Failed to download video: HTTP {video_response.status_code}",
                    platform='tiktok'
                )
            
            # Save file
            ext = "mp3" if download_audio else "mp4"
            filename = self._generate_filename(url, ext)
            file_path = os.path.join(self.download_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(video_response.content)
            
            file_size = os.path.getsize(file_path)
            
            # Convert to audio if requested
            if download_audio:
                audio_path = await self._extract_audio(file_path)
                if audio_path:
                    os.remove(file_path)
                    file_path = audio_path
                    file_size = os.path.getsize(file_path)
            
            if progress_callback:
                await progress_callback("downloaded", 90)
            
            return DownloadResult(
                success=True,
                file_path=file_path,
                file_size=file_size,
                platform='tiktok',
                title=video_data.get('title', ''),
                thumbnail=video_data.get('cover')
            )
            
        except Exception as e:
            logger.error(f"TikTok API error: {e}")
            return DownloadResult(
                success=False,
                error=str(e),
                platform='tiktok'
            )
    
    async def _download_with_cobalt(self, url: str, quality: str, 
                                    platform: str, progress_callback=None) -> DownloadResult:
        """Download using Cobalt API"""
        try:
            session = await self.get_session()
            
            # Cobalt API request
            cobalt_quality = {
                'standard': '480',
                'hd': '720',
                'original': 'max'
            }.get(quality, '720')
            
            payload = {
                "url": url,
                "vQuality": cobalt_quality,
                "filenamePattern": "basic",
                "isAudioOnly": False,
                "disableMetadata": False
            }
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            if progress_callback:
                await progress_callback("connecting", 10)
            
            async with session.post(
                config.COBALT_API_URL,
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return DownloadResult(
                        success=False,
                        error=f"Cobalt API error: {response.status} - {error_text}",
                        platform=platform
                    )
                
                data = await response.json()
            
            if data.get("status") == "error":
                return DownloadResult(
                    success=False,
                    error=data.get("text", "Unknown Cobalt error"),
                    platform=platform
                )
            
            # Get download URL
            download_url = data.get("url")
            if not download_url:
                # Handle picker (multiple options)
                picker = data.get("picker")
                if picker and len(picker) > 0:
                    download_url = picker[0].get("url")
            
            if not download_url:
                return DownloadResult(
                    success=False,
                    error="No download URL in response",
                    platform=platform
                )
            
            if progress_callback:
                await progress_callback("downloading", 30)
            
            # Download the file
            filename = self._generate_filename(url)
            file_path = os.path.join(self.download_dir, filename)
            
            start_time = datetime.now()
            
            async with session.get(download_url) as dl_response:
                if dl_response.status != 200:
                    return DownloadResult(
                        success=False,
                        error=f"Download failed: {dl_response.status}",
                        platform=platform
                    )
                
                total_size = int(dl_response.headers.get('content-length', 0))
                downloaded = 0
                
                async with aiofiles.open(file_path, 'wb') as f:
                    async for chunk in dl_response.content.iter_chunked(8192):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            percent = 30 + int((downloaded / total_size) * 50)
                            await progress_callback("downloading", min(percent, 80))
            
            duration = (datetime.now() - start_time).total_seconds()
            file_size = os.path.getsize(file_path)
            
            if progress_callback:
                await progress_callback("downloaded", 80)
            
            return DownloadResult(
                success=True,
                file_path=file_path,
                file_size=file_size,
                duration=duration,
                platform=platform,
                title=data.get("filename", ""),
                thumbnail=data.get("thumb")
            )
            
        except asyncio.TimeoutError:
            return DownloadResult(
                success=False,
                error="Connection timeout",
                platform=platform
            )
        except Exception as e:
            logger.error(f"Cobalt download error: {e}")
            return DownloadResult(
                success=False,
                error=str(e),
                platform=platform
            )
    
    async def _download_with_ytdlp(self, url: str, quality: str,
                                   platform: str, progress_callback=None, download_audio: bool = False) -> DownloadResult:
        """Download using yt-dlp (especially for Kwai)"""
        try:
            filename = self._generate_filename(url)
            file_path = os.path.join(self.download_dir, filename)
            
            # Base options with FFmpeg for merging video+audio
            ydl_opts = {
                'outtmpl': file_path.replace('.mp4', '.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'socket_timeout': 30,
                'ffmpeg_location': config.FFMPEG_PATH,
                # Use android+web player clients for better format availability
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            }
            
            # Audio-only download
            if download_audio:
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                # Quality-based format selection - use simple 'best' with ext filter
                quality_map = {
                    '144p': 144, '240p': 240, '360p': 360, '480p': 480,
                    'standard': 480, '720p': 720, 'hd': 720, '1080p': 1080,
                    '1440p': 1440, '2160p': 2160, '4k': 2160, 'original': 9999
                }
                max_height = quality_map.get(quality, 720)
                
                # Use best[ext=mp4] with height filter, fallback to best
                if max_height < 9999:
                    ydl_opts['format'] = f'best[ext=mp4][height<={max_height}]/best[height<={max_height}]/best[ext=mp4]/best'
                else:
                    ydl_opts['format'] = 'best[ext=mp4]/best'
            
            if progress_callback:
                await progress_callback("downloading", 20)
            
            start_time = datetime.now()
            
            # Run yt-dlp in executor to avoid blocking
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, 
                lambda: self._run_ytdlp(url, ydl_opts)
            )
            
            if not info:
                raise Exception("yt-dlp failed to extract video info")
            
            # Find the downloaded file
            actual_path = None
            base_path = file_path.replace('.mp4', '')
            
            # Check for audio files if download_audio is True
            if download_audio:
                for ext in ['mp3', 'opus', 'm4a', 'webm']:
                    check_path = f"{base_path}.{ext}"
                    if os.path.exists(check_path):
                        actual_path = check_path
                        break
            else:
                for ext in ['mp4', 'webm', 'mkv', 'mov', 'avi', 'flv']:
                    check_path = f"{base_path}.{ext}"
                    if os.path.exists(check_path):
                        actual_path = check_path
                        break
            
            if not actual_path or not os.path.exists(actual_path):
                raise Exception("Downloaded file not found on disk")
            
            # Convert to mp4 if needed (video only)
            if not download_audio and not actual_path.endswith('.mp4'):
                new_path = actual_path.rsplit('.', 1)[0] + '.mp4'
                converted = await self._convert_to_mp4(actual_path, new_path)
                if converted:
                    if os.path.exists(actual_path) and actual_path != new_path:
                        os.remove(actual_path)
                    actual_path = new_path
            
            duration = (datetime.now() - start_time).total_seconds()
            file_size = os.path.getsize(actual_path)
            
            if progress_callback:
                await progress_callback("downloaded", 80)
            
            return DownloadResult(
                success=True,
                file_path=actual_path,
                file_size=file_size,
                duration=duration,
                platform=platform,
                title=info.get('title', ''),
                thumbnail=info.get('thumbnail')
            )
            
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return DownloadResult(
                success=False,
                error=str(e),
                platform=platform
            )
    
    def _run_ytdlp(self, url: str, opts: dict) -> Optional[dict]:
        """Run yt-dlp synchronously"""
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info
    
    async def _extract_audio(self, input_path: str) -> Optional[str]:
        """Extract audio from video file"""
        try:
            output_path = input_path.rsplit('.', 1)[0] + '.mp3'
            cmd = [
                config.FFMPEG_PATH,
                '-i', input_path,
                '-vn',
                '-acodec', 'libmp3lame',
                '-ab', '192k',
                '-y',
                output_path
            ]
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, timeout=300)
            )
            
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
            return None
        except Exception as e:
            logger.error(f"Audio extraction error: {e}")
            return None
    
    async def _convert_to_mp4(self, input_path: str, output_path: str) -> bool:
        """Convert video to MP4 format"""
        try:
            cmd = [
                config.FFMPEG_PATH,
                '-i', input_path,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',
                output_path
            ]
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, timeout=300)
            )
            
            return process.returncode == 0
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return False
    
    def _extract_instagram_post_id(self, url: str) -> Optional[str]:
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
    
    async def _get_instagram_graphql(self, post_id: str) -> Optional[Dict[str, str]]:
        """Get Instagram video using GraphQL API"""
        try:
            import requests
            
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
                "dpr": "3",
                "lsd": "AVqbxe3J_YA",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "PolarisPostActionLoadPostQueryQuery",
                "variables": json.dumps(variables),
                "server_timestamps": "true",
                "doc_id": "10015901848480474",
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-IG-App-ID': '1217981644879628',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36',
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    'https://www.instagram.com/api/graphql',
                    data=payload,
                    headers=headers,
                    timeout=30
                )
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            media_data = data.get('data', {}).get('xdt_shortcode_media')
            
            if not media_data or not media_data.get('is_video'):
                return None
            
            video_url = media_data.get('video_url')
            if not video_url:
                return None
            
            dimensions = media_data.get('dimensions', {})
            
            return {
                'video_url': video_url,
                'width': str(dimensions.get('width', 640)),
                'height': str(dimensions.get('height', 640)),
                'thumbnail': media_data.get('display_url')
            }
            
        except Exception as e:
            logger.error(f"GraphQL error: {e}")
            return None
    
    async def _get_instagram_webpage(self, post_id: str) -> Optional[Dict[str, str]]:
        """Get Instagram video from webpage meta tags"""
        try:
            import requests
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    f"https://www.instagram.com/p/{post_id}/",
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
                    timeout=30
                )
            )
            
            if response.status_code != 200:
                return None
            
            html = response.text
            
            # Extract video URL from meta tag
            video_match = re.search(r'<meta property="og:video" content="([^"]+)"', html)
            if not video_match:
                return None
            
            return {
                'video_url': video_match.group(1),
                'width': '640',
                'height': '640',
                'thumbnail': None
            }
            
        except Exception as e:
            logger.error(f"Webpage scraping error: {e}")
            return None
    
    async def _process_video(self, result: DownloadResult, quality: str,
                            progress_callback=None) -> DownloadResult:
        """Process video - compress if needed"""
        if not result.file_path or not os.path.exists(result.file_path):
            return result
        
        file_size_mb = result.file_size / (1024 * 1024)
        settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS['hd'])
        
        # Check if compression is needed
        needs_compression = (
            settings.get('compress', False) or 
            file_size_mb > config.MAX_FILE_SIZE_MB
        )
        
        if not needs_compression:
            return result
        
        if progress_callback:
            await progress_callback("compressing", 85)
        
        try:
            compressed_path = result.file_path.replace('.mp4', '_compressed.mp4')
            
            # Build FFmpeg command
            cmd = [
                config.FFMPEG_PATH,
                '-i', result.file_path,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '28' if quality == 'standard' else '23',
            ]
            
            # Add resolution scaling if specified
            if settings.get('resolution'):
                cmd.extend(['-vf', f"scale=-2:{settings['resolution']}"])
            
            # Add bitrate limits
            if settings.get('video_bitrate'):
                cmd.extend(['-b:v', settings['video_bitrate']])
            
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', settings.get('audio_bitrate', '128k'),
                '-y',
                compressed_path
            ])
            
            # Run compression
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, timeout=600)
            )
            
            if process.returncode == 0 and os.path.exists(compressed_path):
                # Remove original
                os.remove(result.file_path)
                
                new_size = os.path.getsize(compressed_path)
                result.file_path = compressed_path
                result.file_size = new_size
                
                if progress_callback:
                    await progress_callback("compressed", 95)
            
        except Exception as e:
            logger.error(f"Compression error: {e}")
            # Return original if compression fails
        
        return result
    
    async def cleanup_file(self, file_path: str) -> bool:
        """Delete a file after use"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up: {file_path}")
                return True
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        return False
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


class FileCleanupScheduler:
    """Manages scheduled file deletions"""
    
    def __init__(self, downloader: MediaDownloader):
        self.downloader = downloader
        self._scheduled_tasks: Dict[str, asyncio.Task] = {}
    
    async def schedule_deletion(self, file_path: str, delay_minutes: int = 15) -> None:
        """Schedule a file for deletion after specified minutes"""
        if file_path in self._scheduled_tasks:
            # Cancel existing task if any
            self._scheduled_tasks[file_path].cancel()
        
        task = asyncio.create_task(self._delayed_delete(file_path, delay_minutes))
        self._scheduled_tasks[file_path] = task
    
    async def _delayed_delete(self, file_path: str, delay_minutes: int) -> None:
        """Delete file after delay"""
        try:
            await asyncio.sleep(delay_minutes * 60)
            await self.downloader.cleanup_file(file_path)
            self._scheduled_tasks.pop(file_path, None)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Scheduled deletion error: {e}")
    
    async def cancel_all(self) -> None:
        """Cancel all scheduled deletions"""
        for task in self._scheduled_tasks.values():
            task.cancel()
        self._scheduled_tasks.clear()


# Global instances
downloader = MediaDownloader()
cleanup_scheduler = FileCleanupScheduler(downloader)
