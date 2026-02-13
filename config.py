"""
Configuration settings for the Telegram Downloader Bot
"""
import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class BotConfig:
    """Bot configuration settings"""
    TOKEN: str = "7824907627:AAGqW0hw4Ckysz35hbIwl0HYk3SlnWZpNlM"
    
    # Cobalt API Settings
    COBALT_API_URL: str = "https://api.cobalt.tools/api/json"  # Updated API endpoint
    COBALT_TIMEOUT: int = 60
    
    # yt-dlp Settings
    YTDLP_TIMEOUT: int = 120
    
    # Download Settings
    DOWNLOAD_DIR: str = "downloads"
    MAX_FILE_SIZE_MB: int = 50  # Telegram limit
    FILE_DELETION_MINUTES: int = 15
    
    # User Limits
    DAILY_DOWNLOAD_LIMIT: int = 15
    COOLDOWN_SECONDS: int = 5
    
    # Required Channels for Force Subscribe (add channel usernames without @)
    REQUIRED_CHANNELS: List[str] = field(default_factory=lambda: [])
    
    # Admin Settings
    PRIMARY_OWNER_ID: int = 6213708507  # Set your Telegram ID here
    
    # FFmpeg Settings
    FFMPEG_PATH: str = r"C:\Users\Sami\Desktop\Downloader\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"  # Will be auto-updated by setup script
    VIDEO_BITRATE_STANDARD: str = "800k"
    VIDEO_BITRATE_HD: str = "2000k"
    AUDIO_BITRATE: str = "128k"
    
    # Supported Platforms
    SUPPORTED_PLATFORMS: dict = field(default_factory=lambda: {
        'instagram': ['instagram.com', 'www.instagram.com'],
        'tiktok': ['tiktok.com', 'www.tiktok.com', 'vt.tiktok.com', 'vm.tiktok.com'],
        'youtube': ['youtube.com', 'www.youtube.com', 'youtu.be', 'youtube.com/shorts'],
        'twitter': ['twitter.com', 'www.twitter.com', 'x.com', 'www.x.com'],
        'kwai': ['kwai.com', 'www.kwai.com', 'kw.ai']
    })

@dataclass
class Messages:
    """Bot messages in Arabic and English"""
    WELCOME: str = """
<b>🎬 مرحباً بك في بوت التحميل!</b>

أرسل رابط من أي من المنصات التالية:
• Instagram (Reels, Stories, Posts)
• TikTok
• YouTube (Shorts/Videos)
• Twitter/X
• Kwai

<i>📥 سيتم تحميل الفيديو بدون علامة مائية!</i>
"""
    
    PROCESSING: str = "⏳ <b>جاري المعالجة...</b>"
    DOWNLOADING: str = "📥 <b>جاري التحميل...</b>\n{progress}"
    COMPRESSING: str = "🗜 <b>جاري الضغط...</b>"
    UPLOADING: str = "📤 <b>جاري الرفع...</b>\n{progress}"
    SUCCESS: str = "✅ <b>تم بنجاح!</b>\n\n📁 الحجم: {size}\n⏱ الوقت: {time}s"
    
    ERROR_GENERIC: str = "❌ <b>حدث خطأ!</b>\n<code>{error}</code>"
    ERROR_PRIVATE: str = "🔒 <b>المحتوى خاص أو غير متاح</b>"
    ERROR_UNSUPPORTED: str = "⚠️ <b>المنصة غير مدعومة</b>\n\nالمنصات المدعومة:\nInstagram, TikTok, YouTube, Twitter, Kwai"
    ERROR_LIMIT: str = "🚫 <b>وصلت للحد اليومي ({limit} تحميل)</b>\n⏰ يتجدد بعد: {reset}"
    ERROR_COOLDOWN: str = "⏱ <b>انتظر {seconds} ثانية</b>"
    ERROR_SUBSCRIBE: str = """
🔐 <b>يجب الاشتراك في القنوات التالية:</b>

{channels}

<i>بعد الاشتراك، اضغط "✅ تحقق"</i>
"""
    ERROR_BANNED: str = "🚫 <b>أنت محظور من استخدام البوت</b>"
    
    QUALITY_SELECT: str = """
🎬 <b>اختر جودة التحميل:</b>

📱 <b>جودة منخفضة:</b> 144p, 240p, 360p (سريع، حجم صغير)
📺 <b>جودة متوسطة:</b> 480p, 720p (HD), 1080p (FHD)
🎬 <b>جودة عالية:</b> 1440p (2K), 2160p (4K)
✨ <b>الجودة الأصلية:</b> أفضل جودة متاحة

<i>💡 نصيحة: اختر جودة أقل للتحميل الأسرع</i>
"""
    
    ADMIN_PANEL: str = """
⚙️ <b>لوحة التحكم</b>

👤 المستخدمين: {users}
📥 التحميلات اليوم: {downloads}
🖥 حالة السيرفر: {status}
"""
    
    STATS: str = """
📊 <b>إحصائيات البوت</b>

👥 إجمالي المستخدمين: <code>{total_users}</code>
🆕 مستخدمين جدد اليوم: <code>{new_users}</code>
📥 تحميلات اليوم: <code>{downloads_today}</code>
📈 إجمالي التحميلات: <code>{total_downloads}</code>

🖥 <b>حالة السيرفر:</b>
• CPU: <code>{cpu}%</code>
• RAM: <code>{ram}%</code>
• مساحة التخزين: <code>{disk}%</code>
"""
    
    BROADCAST_START: str = "📢 <b>بدء البث...</b>\nالمستلمين: {count}"
    BROADCAST_DONE: str = "✅ <b>اكتمل البث!</b>\n\n✓ نجح: {success}\n✗ فشل: {failed}"
    
    USER_BANNED: str = "✅ تم حظر المستخدم <code>{user_id}</code>"
    USER_UNBANNED: str = "✅ تم إلغاء حظر المستخدم <code>{user_id}</code>"
    LIMIT_RESET: str = "✅ تم إعادة تعيين حد المستخدم <code>{user_id}</code>"


# Quality settings
QUALITY_SETTINGS = {
    'standard': {
        'video_bitrate': '800k',
        'audio_bitrate': '96k',
        'resolution': '480',
        'compress': True
    },
    'hd': {
        'video_bitrate': '2000k',
        'audio_bitrate': '128k',
        'resolution': '720',
        'compress': True
    },
    'original': {
        'video_bitrate': None,
        'audio_bitrate': None,
        'resolution': None,
        'compress': False
    }
}

# URL Patterns for detection
URL_PATTERNS = {
    'instagram': r'(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|reels|stories|tv)/[\w-]+/?',
    'tiktok': r'(?:https?://)?(?:www\.|vm\.|vt\.)?tiktok\.com/[\w@/.-]+',
    'youtube': r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w-]+',
    'facebook': r'(?:https?://)?(?:www\.)?(?:facebook\.com|fb\.me)/(?:share/|video/|reel/|v/|watch/)[\w-]+/?',
    'twitter': r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+',
    'kwai': r'(?:https?://)?(?:www\.)?(?:kwai\.com|kw\.ai)/[\w@/.-]+'
}

# Initialize config
config = BotConfig()
messages = Messages()
