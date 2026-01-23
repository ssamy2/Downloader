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
                      progress_callback=None) -> DownloadResult:
        """
        Main download method - tries Cobalt first, then yt-dlp as fallback
        """
        platform = self.detect_platform(url)
        if not platform:
            return DownloadResult(
                success=False,
                error="Unsupported platform",
                platform="unknown"
            )
        
        logger.info(f"Downloading from {platform}: {url}")
        
        # Use yt-dlp directly (Cobalt v7 API shut down Nov 2024)
        result = await self._download_with_ytdlp(url, quality, platform, progress_callback)
        
        # Compress if needed
        if result.success and quality != "original":
            result = await self._process_video(result, quality, progress_callback)
        
        return result
    
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
                                   platform: str, progress_callback=None) -> DownloadResult:
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
            for ext in ['mp4', 'webm', 'mkv', 'mov', 'avi', 'flv']:
                check_path = f"{base_path}.{ext}"
                if os.path.exists(check_path):
                    actual_path = check_path
                    break
            
            if not actual_path or not os.path.exists(actual_path):
                raise Exception("Downloaded file not found on disk")
            
            # Convert to mp4 if needed
            if not actual_path.endswith('.mp4'):
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
