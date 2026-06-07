"""
Configuration settings for the Telegram Downloader Bot
"""
import os
import shutil
from dataclasses import dataclass, field
from typing import List

@dataclass
class BotConfig:
    """Bot configuration settings"""
    TOKEN: str = "7886777701:AAHmF8r-T1aRWJP_5T4seVaQbtKnkDiVQOQ"
    
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
    PRIMARY_OWNER_ID: int = 6213703507  # Set your Telegram ID here
    
    # FFmpeg Settings
    FFMPEG_PATH: str = field(default_factory=lambda: shutil.which("ffmpeg") or "/usr/bin/ffmpeg")
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

import json

def load_ui_settings():
    default_settings = {
        "messages": {
            "WELCOME": "\n<b>🎬 مرحباً بك في بوت التحميل!</b>\n\nأرسل رابط من أي من المنصات التالية:\n• Instagram (Reels, Stories, Posts)\n• TikTok\n• YouTube (Shorts/Videos)\n• Twitter/X\n• Kwai\n\n<i>📥 سيتم تحميل الفيديو بدون علامة مائية!</i>\n",
            "PROCESSING": "⏳ <b>جاري المعالجة...</b>",
            "DOWNLOADING": "📥 <b>جاري التحميل...</b>\n{progress}",
            "COMPRESSING": "🗜 <b>جاري الضغط...</b>",
            "UPLOADING": "📤 <b>جاري الرفع...</b>\n{progress}",
            "SUCCESS": "✅ <b>تم بنجاح!</b>\n\n📁 الحجم: {size}\n⏱ الوقت: {time}s",
            "ERROR_GENERIC": "❌ <b>حدث خطأ!</b>\n<code>{error}</code>",
            "ERROR_PRIVATE": "🔒 <b>المحتوى خاص أو غير متاح</b>",
            "ERROR_UNSUPPORTED": "⚠️ <b>المنصة غير مدعومة</b>\n\nالمنصات المدعومة:\nInstagram, TikTok, YouTube, Twitter, Kwai",
            "ERROR_LIMIT": "🚫 <b>وصلت للحد اليومي ({limit} تحميل)</b>\n⏰ يتجدد بعد: {reset}",
            "ERROR_COOLDOWN": "⏱ <b>انتظر {seconds} ثانية</b>",
            "ERROR_SUBSCRIBE": "\n🔐 <b>يجب الاشتراك في القنوات التالية:</b>\n\n{channels}\n\n<i>بعد الاشتراك، اضغط \"✅ تحقق\"</i>\n",
            "ERROR_BANNED": "🚫 <b>أنت محظور من استخدام البوت</b>",
            "QUALITY_SELECT": "\n🎬 <b>اختر جودة التحميل:</b>\n\n📱 <b>جودة منخفضة:</b> 144p, 240p, 360p (سريع، حجم صغير)\n📺 <b>جودة متوسطة:</b> 480p, 720p (HD), 1080p (FHD)\n🎬 <b>جودة عالية:</b> 1440p (2K), 2160p (4K)\n✨ <b>الجودة الأصلية:</b> أفضل جودة متاحة\n\n<i>💡 نصيحة: اختر جودة أقل للتحميل الأسرع</i>\n",
            "ADMIN_PANEL": "\n⚙️ <b>لوحة التحكم</b>\n\n👤 المستخدمين: {users}\n📥 التحميلات اليوم: {downloads}\n🖥 حالة السيرفر: {status}\n",
            "STATS": "\n📊 <b>إحصائيات البوت</b>\n\n👥 إجمالي المستخدمين: <code>{total_users}</code>\n🆕 مستخدمين جدد اليوم: <code>{new_users}</code>\n📥 تحميلات اليوم: <code>{downloads_today}</code>\n📈 إجمالي التحميلات: <code>{total_downloads}</code>\n\n🖥 <b>حالة السيرفر:</b>\n• CPU: <code>{cpu}%</code>\n• RAM: <code>{ram}%</code>\n• مساحة التخزين: <code>{disk}%</code>\n",
            "BROADCAST_START": "📢 <b>بدء البث...</b>\nالمستلمين: {count}",
            "BROADCAST_DONE": "✅ <b>اكتمل البث!</b>\n\n✓ نجح: {success}\n✗ فشل: {failed}",
            "USER_BANNED": "✅ تم حظر المستخدم <code>{user_id}</code>",
            "USER_UNBANNED": "✅ تم إلغاء حظر المستخدم <code>{user_id}</code>",
            "LIMIT_RESET": "✅ تم إعادة تعيين حد المستخدم <code>{user_id}</code>"
        },
        "emojis": {},
        "buttons_dict": {},
        "button_configs": {}
    }
    
    settings_file = 'data/ui_settings.json'
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Merge loaded settings with defaults
                if 'messages' in data:
                    default_settings['messages'].update(data['messages'])
                if 'emojis' in data:
                    default_settings['emojis'].update(data['emojis'])
                if 'buttons_dict' in data:
                    default_settings['buttons_dict'].update(data['buttons_dict'])
                if 'button_configs' in data:
                    default_settings['button_configs'].update(data['button_configs'])
        except Exception as e:
            print(f"Error loading ui_settings.json: {e}")
    else:
        # Create default file
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    return default_settings

UI_SETTINGS = load_ui_settings()

@dataclass
class Messages:
    WELCOME: str = ""
    PROCESSING: str = ""
    DOWNLOADING: str = ""
    COMPRESSING: str = ""
    UPLOADING: str = ""
    SUCCESS: str = ""
    ERROR_GENERIC: str = ""
    ERROR_PRIVATE: str = ""
    ERROR_UNSUPPORTED: str = ""
    ERROR_LIMIT: str = ""
    ERROR_COOLDOWN: str = ""
    ERROR_SUBSCRIBE: str = ""
    ERROR_BANNED: str = ""
    QUALITY_SELECT: str = ""
    ADMIN_PANEL: str = ""
    STATS: str = ""
    BROADCAST_START: str = ""
    BROADCAST_DONE: str = ""
    USER_BANNED: str = ""
    USER_UNBANNED: str = ""
    LIMIT_RESET: str = ""
    HELP_MENU: str = ""
    SUB_VERIFIED: str = ""
    SUB_NOT_VERIFIED: str = ""
    EXPIRED: str = ""
    AUDIO_SETTINGS: str = ""
    INPUT_ARTIST: str = ""
    INPUT_FILENAME: str = ""
    INPUT_DESC: str = ""
    INPUT_THUMB: str = ""
    INVALID_IMAGE: str = ""
    IMAGE_ERROR: str = ""
    MULTI_LINKS: str = ""
    TEMP_MSG: str = ""
    NEW_USER_NOTIFY: str = ""
    NEW_DOWNLOAD_NOTIFY: str = ""

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
messages = Messages(**{k: v for k, v in UI_SETTINGS.get('messages', {}).items() if hasattr(Messages, k)})
emojis = UI_SETTINGS.get('emojis', {})


class Buttons:
    def __getattr__(self, name):
        return UI_SETTINGS.get('buttons_dict', {}).get(name, name)

buttons = Buttons()



from aiogram.types import InlineKeyboardButton

def build_btn(key: str, **kwargs) -> InlineKeyboardButton:
    configs = UI_SETTINGS.get('button_configs', {})
    btn_config = configs.get(key, {})
    text = btn_config.get('text', UI_SETTINGS.get('buttons_dict', {}).get(key, key))
    style = btn_config.get('style', 'primary')
    emoji = btn_config.get('emoji', None)
    
    if emoji:
        kwargs['icon_custom_emoji_id'] = emoji
    if style:
        kwargs['style'] = style
        
    return InlineKeyboardButton(text=text, **kwargs)
