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
    PRIMARY_OWNER_ID: int = 6213708507  # Set your Telegram ID here
    
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
                    "WELCOME": "<blockquote><b><tg-emoji emoji-id=\"5267500801240092311\">⭐</tg-emoji></b><b> مرحباً بك في بوت التحميل المتميز</b>\n\nنحن ندعم أقوى منصات السوشيال ميديا لنقدم لك أفضل جودة تحميل وبدون علامة مائية.\n\n<b>المنصات المدعومة:</b>\n<code>Instagram</code> - <code>TikTok</code> - <code>YouTube</code>\n<code>Twitter (X)</code> - <code>Kwai</code>\n\n<i>أرسل الرابط الآن</i>!</blockquote>",
                    "PROCESSING": "<tg-emoji emoji-id='5382194935057372936'>⏱</tg-emoji> <b>جاري المعالجة...</b>",
                    "DOWNLOADING": "<tg-emoji emoji-id='5443127283898405358'>📥</tg-emoji> <b>جاري التحميل...</b>\n\n<blockquote>{progress}</blockquote>",
                    "COMPRESSING": "<tg-emoji emoji-id='5190440583914629877'>🗜</tg-emoji> <b>جاري الضغط وتحسين الجودة...</b>",
                    "UPLOADING": "<tg-emoji emoji-id='5445355530111437729'>📤</tg-emoji> <b>جاري الرفع...</b>\n\n<blockquote>{progress}</blockquote>",
                    "SUCCESS": "<blockquote><b><tg-emoji emoji-id=\"5190836223417028350\">✅</tg-emoji></b><b> تمت العملية بنجاح!</b>\n\n<b>الحجم:</b> {size}\n<b>الوقت:</b> {time} ثانية</blockquote>",
                    "ERROR_GENERIC": "<b><tg-emoji emoji-id='5175115075450570337'>❌</tg-emoji> عذراً، حدث خطأ غير متوقع!</b>\n\n<blockquote><code>{error}</code></blockquote>",
                    "ERROR_PRIVATE": "<b><tg-emoji emoji-id='5197288647275071607'>🔒</tg-emoji> المحتوى خاص</b>\n\n<blockquote>لا يمكنني تحميل هذا المحتوى لأنه خاص أو غير متاح للعامة.</blockquote>",
                    "ERROR_UNSUPPORTED": "<b><tg-emoji emoji-id='5172571638767551946'>⚠️</tg-emoji> منصة غير مدعومة</b>\n\n<blockquote>يرجى إرسال رابط من المنصات المدعومة فقط (Instagram, TikTok, YouTube, Twitter, Kwai).</blockquote>",
                    "ERROR_LIMIT": "<b><tg-emoji emoji-id='5175115075450570337'>🚫</tg-emoji> تجاوزت الحد المسموح</b>\n\n<blockquote>لقد استهلكت الحد اليومي للتحميلات ({limit} تحميل).</blockquote>\n<i>يتجدد الرصيد بعد: {reset}</i>",
                    "ERROR_COOLDOWN": "<b><tg-emoji emoji-id='5382194935057372936'>⏱</tg-emoji> مهلاً!</b> يرجى الانتظار <code>{seconds}</code> ثانية قبل المحاولة مجدداً.",
                    "ERROR_SUBSCRIBE": "<b><tg-emoji emoji-id='5197288647275071607'>🔐</tg-emoji> اشتراك إجباري</b>\n\n<blockquote>عذراً، يجب عليك الاشتراك في قنوات البوت أولاً لتتمكن من استخدامه.</blockquote>\n\n{channels}\n\n<i>اضغط على زر التحقق بعد الاشتراك.</i>",
                    "ERROR_BANNED": "<b><tg-emoji emoji-id='5175115075450570337'>🚫</tg-emoji> حساب محظور</b>\n\n<blockquote>تم حظر حسابك من استخدام خدمات البوت.</blockquote>",
                    "QUALITY_SELECT": "<b><tg-emoji emoji-id='5267500801240092311'>🎬</tg-emoji> خيارات التحميل</b>\n\n<blockquote>اختر الجودة أو الصيغة المناسبة لك من الأزرار أدناه:</blockquote>",
                    "ADMIN_PANEL": "<b><tg-emoji emoji-id='5190607263005445520'>⚙️</tg-emoji> لوحة الإدارة</b>\n\n<blockquote><b>المستخدمين:</b> <code>{users}</code>\n<b>التحميلات:</b> <code>{downloads}</code>\n<b>السيرفر:</b> {status}</blockquote>",
                    "STATS": "<b><tg-emoji emoji-id='5190806721286657692'>📊</tg-emoji> إحصائيات النظام</b>\n\n<blockquote><b>المستخدمين:</b> <code>{total_users}</code> (جدد: <code>{new_users}</code>)\n<b>تحميلات اليوم:</b> <code>{downloads_today}</code>\n<b>إجمالي التحميلات:</b> <code>{total_downloads}</code></blockquote>\n\n<b>🖥 الموارد:</b>\n<code>CPU: {cpu}%</code> | <code>RAM: {ram}%</code> | <code>DISK: {disk}%</code>",
                    "BROADCAST_START": "<b><tg-emoji emoji-id='5298609030321691620'>📢</tg-emoji> جاري بدء البث...</b>\n\n<blockquote>العدد المستهدف: <code>{count}</code> مستخدم</blockquote>",
                    "BROADCAST_DONE": "<b><tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> انتهى البث!</b>\n\n<blockquote>نجاح: <code>{success}</code>\nفشل: <code>{failed}</code></blockquote>",
                    "USER_BANNED": "<tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> تم حظر المستخدم بنجاح.",
                    "USER_UNBANNED": "<tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> تم إلغاء حظر المستخدم.",
                    "LIMIT_RESET": "<tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> تم تصفير عداد التحميلات للمستخدم.",
                    "HELP_MENU": "\n<b><tg-emoji emoji-id='5190806721286657692'>📖</tg-emoji> دليل الاستخدام</b>\n\n<blockquote>1️⃣ أرسل رابط من أي منصة مدعومة\n2️⃣ اختر جودة التحميل\n3️⃣ انتظر حتى يتم التحميل والإرسال</blockquote>\n\n<b>المنصات المدعومة:</b>\n<code>Instagram</code> • <code>TikTok</code> • <code>YouTube</code>\n<code>Twitter/X</code> • <code>Kwai</code>\n\n<b>الحدود:</b>\n• {limit} تحميل يومياً\n• انتظار {cooldown} ثواني بين كل طلب\n\n<b>الجودات:</b>\n• <b>Standard</b> - 480p (سريع، حجم صغير)\n• <b>HD</b> - 720p (جودة عالية)\n• <b>Original</b> - الجودة الأصلية",
                    "SUB_VERIFIED": "<b><tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> تم التحقق!</b>\n\n<blockquote>يمكنك استخدام البوت الآن.</blockquote>",
                    "SUB_NOT_VERIFIED": "<b><tg-emoji emoji-id='5175115075450570337'>❌</tg-emoji> فشل التحقق!</b>\n\n<blockquote>لم يتم الاشتراك في جميع القنوات بعد.</blockquote>",
                    "EXPIRED": "<b><tg-emoji emoji-id='5382194935057372936'>⏰</tg-emoji> انتهت الصلاحية!</b>\n\n<blockquote>أرسل الرابط مرة أخرى.</blockquote>",
                    "AUDIO_SETTINGS": "\n<b><tg-emoji emoji-id='5190607263005445520'>🎵</tg-emoji> إعدادات الصوت (بصمة)</b>\n\n<blockquote><b>الاسم:</b> {artist}\n<b>الملف:</b> {filename}\n<b>الوصف:</b> {desc}\n<b>الصورة:</b> {thumb}</blockquote>\n\n<i>اختر الإعداد لتعديله أو تابع التحميل:</i>",
                    "INPUT_ARTIST": "<b><tg-emoji emoji-id='5190607263005445520'>🎤</tg-emoji> تغيير اسم الفنان</b>\n\n<blockquote>أرسل اسم الفنان المطلوب:</blockquote>",
                    "INPUT_FILENAME": "<b><tg-emoji emoji-id='5444856076954520455'>📝</tg-emoji> تغيير اسم الملف</b>\n\n<blockquote>أرسل اسم الملف المطلوب (بدون امتداد):</blockquote>",
                    "INPUT_DESC": "<b><tg-emoji emoji-id='5444856076954520455'>📄</tg-emoji> تغيير وصف الملف</b>\n\n<blockquote>أرسل وصف الملف المطلوب:</blockquote>",
                    "INPUT_THUMB": "<b><tg-emoji emoji-id='5262517101578443800'>🖼</tg-emoji> تغيير الصورة المصغرة</b>\n\n<blockquote>أرسل الصورة المطلوبة:</blockquote>",
                    "INVALID_IMAGE": "<b><tg-emoji emoji-id='5175115075450570337'>❌</tg-emoji> صيغة غير مدعومة!</b>\n\n<blockquote>يرجى إرسال صورة فقط.</blockquote>",
                    "IMAGE_ERROR": "<b><tg-emoji emoji-id='5175115075450570337'>❌</tg-emoji> خطأ في الصورة!</b>\n\n<blockquote>حدث خطأ أثناء معالجة الصورة، يرجى المحاولة مرة أخرى.</blockquote>",
                    "MULTI_LINKS": "<b><tg-emoji emoji-id='5197288647275071607'>🔗</tg-emoji> اكتشاف متعدد!</b>\n\n<blockquote>تم اكتشاف <code>{count}</code> روابط للتحميل.</blockquote>",
                    "TEMP_MSG": "<b><tg-emoji emoji-id='5172571638767551946'>⚠️</tg-emoji> تنبيه!</b>\n\n<blockquote>هذه الرسالة ستُحذف بعد 30 ثانية.\nيرجى حفظها في السيفد مسدجس.</blockquote>",
                    "NEW_USER_NOTIFY": "<b><tg-emoji emoji-id='5195033767969839232'>🆕</tg-emoji> مستخدم جديد</b>\n\n<blockquote><b>الاسم:</b> {name}\n<b>الايدي:</b> <code>{id}</code>\n<b>اليوزر:</b> @{username}\n<b>الوقت:</b> {time}</blockquote>",
                    "NEW_DOWNLOAD_NOTIFY": "<b><tg-emoji emoji-id='5443127283898405358'>📥</tg-emoji> تحميل جديد</b>\n\n<blockquote><b>المستخدم:</b> <code>{user}</code>\n<b>المنصة:</b> {platform}\n<b>الرابط:</b> <code>{url}</code>\n<b>الوقت:</b> {time}</blockquote>"
            },
            "emojis": {
                    "star": "5267500801240092311",
                    "clock": "5382194935057372936",
                    "download": "5443127283898405358",
                    "lightning": "5190440583914629877",
                    "upload": "5445355530111437729",
                    "success": "5190836223417028350",
                    "diamond": "5192715031090858438",
                    "error": "5175115075450570337",
                    "shield": "5197288647275071607",
                    "warning": "5172571638767551946",
                    "fire": "5190401572726675514",
                    "brain": "5190607263005445520",
                    "users": "5332724926216428039",
                    "stats": "5190806721286657692",
                    "rocket": "5195033767969839232",
                    "megaphone": "5298609030321691620",
                    "music": "5192715031090858438",
                    "mic": "5190607263005445520",
                    "pic": "5262517101578443800",
                    "doc": "5444856076954520455",
                    "crown": "5192715031090858438",
                    "back": "5175115075450570337",
                    "tv": "5190401572726675514"
            },
            "buttons_dict": {
                    "Q_144": "144p",
                    "Q_240": "240p",
                    "Q_360": "360p",
                    "Q_480": "480p",
                    "ADMIN_CHANNELS_MGR": "إدارة القنوات",
                    "ADMIN_ADMINS_MGR": "إدارة المسؤولين",
                    "ADMIN_USERS_MGR": "إدارة المستخدمين",
                    "FWD_ALL": "إذاعة توجيه إلى الجميع",
                    "FWD_PRIVATE": "إذاعة توجيه للخاص",
                    "FWD_ALL_2": "إذاعة توجيه للكل",
                    "BCAST_PRIVATE": "إذاعة للخاص",
                    "BCAST_GROUPS": "إذاعة مجموعات",
                    "ADD_CHANNEL": "إضافة قناة",
                    "RESET_LIMIT": "إعادة تعيين الحد",
                    "FWD_GROUPS": "إعادة توجيه إذاعة إلى المجموعات",
                    "SEC_SETTINGS": "إعدادات أمان",
                    "NOTIF_SETTINGS": "إعدادات الإشعارات",
                    "CLOSE": "إغلاق",
                    "CANCEL": "إلغاء",
                    "UNBAN_ALT": "إلغاء الحظر",
                    "UNBAN": "إلغاء حظر",
                    "STATS": "الإحصائيات",
                    "SETTINGS": "الإعدادات",
                    "BROADCAST": "البث",
                    "VALIDATE_CHANNELS": "التحقق من صلاحية القنوات",
                    "ORIGINAL": "الجودة الأصلية",
                    "CHANNELS": "القنوات",
                    "FORCE_CHANNELS": "القنوات الإجبارية",
                    "BCAST_MSG": "بث رسالة",
                    "BCAST_ALL": "بث للجميع",
                    "CONFIRM": "تأكيد",
                    "PIN_BCAST": "تثبيت الإذاعة",
                    "VERIFY": "تحقق",
                    "DL_AUDIO": "تحميل الصوت",
                    "DL_VIDEO": "تحميل الفيديو",
                    "DL_CURRENT_SETTING": "تحميل بالإعدادات الحالية",
                    "DL_AUDIO_ONLY": "تحميل صوتي فقط",
                    "CUSTOM_SUB_MSG": "تخصيص رسالة الاشتراك",
                    "EDIT_ARTIST": "تغيير اسم الفنان",
                    "EDIT_FILENAME": "تغيير اسم الملف",
                    "EDIT_THUMB": "تغيير الصورة المصغرة",
                    "EDIT_DESC": "تغيير وصف الملف",
                    "BAN_USER": "حظر مستخدم",
                    "BACK": "رجوع",
                    "USER_PERMS": "صلاحيات المستخدم",
                    "SKIP_SETTINGS": "متابعة بدون إعدادات",
                    "BACK_ALT": "• رجوع •",
                    "Q_1440": "🎬 1440p (2K)",
                    "Q_2160": "🎬 2160p (4K)",
                    "DL_AUDIO_CUSTOM": "🎵 تحميل صوت (بصمة)",
                    "VIEW_CHANNELS": "📋 عرض القنوات",
                    "SET_NOTIF_CHANNEL": "📍 تحديد قناة/جروب للإشعارات",
                    "Q_1080": "📺 1080p (FHD)",
                    "Q_720": "📺 720p (HD)",
                    "DEL_INVALID": "🗑️ حذف غير الصالحة",
                    "DEL_CHANNEL": "🗑️ حذف قناة",
                    "Q_1080_FHD": "1080p FHD",
                    "Q_1440_2K": "1440p 2K",
                    "Q_2160_4K": "2160p 4K",
                    "Q_720_HD": "720p HD",
                    "AUDIO_CUSTOM_NEW": "صوت (بصمة)",
                    "AUDIO_ONLY_NEW": "صوت فقط"
            },
            "button_configs": {
                    "Q_144": {
                            "text": "144p",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_240": {
                            "text": "240p",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_360": {
                            "text": "360p",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_480": {
                            "text": "460",
                            "style": "danger",
                            "emoji": "5406913184810409829"
                    },
                    "ADMIN_CHANNELS_MGR": {
                            "text": "إدارة القنوات",
                            "style": "primary",
                            "emoji": None
                    },
                    "ADMIN_ADMINS_MGR": {
                            "text": "إدارة المسؤولين",
                            "style": "primary",
                            "emoji": None
                    },
                    "ADMIN_USERS_MGR": {
                            "text": "إدارة المستخدمين",
                            "style": "primary",
                            "emoji": None
                    },
                    "FWD_ALL": {
                            "text": "إذاعة توجيه إلى الجميع",
                            "style": "primary",
                            "emoji": None
                    },
                    "FWD_PRIVATE": {
                            "text": "إذاعة توجيه للخاص",
                            "style": "primary",
                            "emoji": None
                    },
                    "FWD_ALL_2": {
                            "text": "إذاعة توجيه للكل",
                            "style": "primary",
                            "emoji": None
                    },
                    "BCAST_PRIVATE": {
                            "text": "إذاعة للخاص",
                            "style": "primary",
                            "emoji": None
                    },
                    "BCAST_GROUPS": {
                            "text": "إذاعة مجموعات",
                            "style": "primary",
                            "emoji": None
                    },
                    "ADD_CHANNEL": {
                            "text": "إضافة قناة",
                            "style": "primary",
                            "emoji": None
                    },
                    "RESET_LIMIT": {
                            "text": "إعادة تعيين الحد",
                            "style": "primary",
                            "emoji": None
                    },
                    "FWD_GROUPS": {
                            "text": "إعادة توجيه إذاعة إلى المجموعات",
                            "style": "primary",
                            "emoji": None
                    },
                    "SEC_SETTINGS": {
                            "text": "إعدادات أمان",
                            "style": "primary",
                            "emoji": None
                    },
                    "NOTIF_SETTINGS": {
                            "text": "إعدادات الإشعارات",
                            "style": "primary",
                            "emoji": None
                    },
                    "CLOSE": {
                            "text": "إغلاق",
                            "style": "primary",
                            "emoji": None
                    },
                    "CANCEL": {
                            "text": "إلغاء",
                            "style": "primary",
                            "emoji": None
                    },
                    "UNBAN_ALT": {
                            "text": "إلغاء الحظر",
                            "style": "primary",
                            "emoji": None
                    },
                    "UNBAN": {
                            "text": "إلغاء حظر",
                            "style": "primary",
                            "emoji": None
                    },
                    "STATS": {
                            "text": "الإحصائيات",
                            "style": "primary",
                            "emoji": None
                    },
                    "SETTINGS": {
                            "text": "الإعدادات",
                            "style": "primary",
                            "emoji": None
                    },
                    "BROADCAST": {
                            "text": "البث",
                            "style": "primary",
                            "emoji": None
                    },
                    "VALIDATE_CHANNELS": {
                            "text": "التحقق من صلاحية القنوات",
                            "style": "primary",
                            "emoji": None
                    },
                    "ORIGINAL": {
                            "text": "الجودة الأصلية",
                            "style": "primary",
                            "emoji": None
                    },
                    "CHANNELS": {
                            "text": "القنوات",
                            "style": "primary",
                            "emoji": None
                    },
                    "FORCE_CHANNELS": {
                            "text": "القنوات الإجبارية",
                            "style": "primary",
                            "emoji": None
                    },
                    "BCAST_MSG": {
                            "text": "بث رسالة",
                            "style": "primary",
                            "emoji": None
                    },
                    "BCAST_ALL": {
                            "text": "بث للجميع",
                            "style": "primary",
                            "emoji": None
                    },
                    "CONFIRM": {
                            "text": "تأكيد",
                            "style": "primary",
                            "emoji": None
                    },
                    "PIN_BCAST": {
                            "text": "تثبيت الإذاعة",
                            "style": "primary",
                            "emoji": None
                    },
                    "VERIFY": {
                            "text": "تحقق",
                            "style": "primary",
                            "emoji": None
                    },
                    "DL_AUDIO": {
                            "text": "تحميل الصوت",
                            "style": "primary",
                            "emoji": None
                    },
                    "DL_VIDEO": {
                            "text": "تحميل الفيديو",
                            "style": "primary",
                            "emoji": None
                    },
                    "DL_CURRENT_SETTING": {
                            "text": "تحميل بالإعدادات الحالية",
                            "style": "primary",
                            "emoji": None
                    },
                    "DL_AUDIO_ONLY": {
                            "text": "تحميل صوتي فقط",
                            "style": "primary",
                            "emoji": None
                    },
                    "CUSTOM_SUB_MSG": {
                            "text": "تخصيص رسالة الاشتراك",
                            "style": "primary",
                            "emoji": None
                    },
                    "EDIT_ARTIST": {
                            "text": "تغيير اسم الفنان",
                            "style": "primary",
                            "emoji": None
                    },
                    "EDIT_FILENAME": {
                            "text": "تغيير اسم الملف",
                            "style": "primary",
                            "emoji": None
                    },
                    "EDIT_THUMB": {
                            "text": "تغيير الصورة المصغرة",
                            "style": "primary",
                            "emoji": None
                    },
                    "EDIT_DESC": {
                            "text": "تغيير وصف الملف",
                            "style": "primary",
                            "emoji": None
                    },
                    "BAN_USER": {
                            "text": "حظر مستخدم",
                            "style": "primary",
                            "emoji": None
                    },
                    "BACK": {
                            "text": "رجوع",
                            "style": "primary",
                            "emoji": None
                    },
                    "USER_PERMS": {
                            "text": "صلاحيات المستخدم",
                            "style": "primary",
                            "emoji": None
                    },
                    "SKIP_SETTINGS": {
                            "text": "متابعة بدون إعدادات",
                            "style": "primary",
                            "emoji": None
                    },
                    "BACK_ALT": {
                            "text": "• رجوع •",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_1440": {
                            "text": "🎬 1440p (2K)",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_2160": {
                            "text": "🎬 2160p (4K)",
                            "style": "primary",
                            "emoji": None
                    },
                    "DL_AUDIO_CUSTOM": {
                            "text": "🎵 تحميل صوت (بصمة)",
                            "style": "primary",
                            "emoji": None
                    },
                    "VIEW_CHANNELS": {
                            "text": "📋 عرض القنوات",
                            "style": "primary",
                            "emoji": None
                    },
                    "SET_NOTIF_CHANNEL": {
                            "text": "📍 تحديد قناة/جروب للإشعارات",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_1080": {
                            "text": "📺 1080p (FHD)",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_720": {
                            "text": "📺 720p (HD)",
                            "style": "primary",
                            "emoji": None
                    },
                    "DEL_INVALID": {
                            "text": "🗑️ حذف غير الصالحة",
                            "style": "primary",
                            "emoji": None
                    },
                    "DEL_CHANNEL": {
                            "text": "🗑️ حذف قناة",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_1080_FHD": {
                            "text": "1080p FHD",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_1440_2K": {
                            "text": "1440p 2K",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_2160_4K": {
                            "text": "2160p 4K",
                            "style": "primary",
                            "emoji": None
                    },
                    "Q_720_HD": {
                            "text": "720p HD",
                            "style": "primary",
                            "emoji": None
                    },
                    "AUDIO_CUSTOM_NEW": {
                            "text": "صوت (بصمة)",
                            "style": "primary",
                            "emoji": None
                    },
                    "AUDIO_ONLY_NEW": {
                            "text": "صوت فقط",
                            "style": "primary",
                            "emoji": None
                    }
            }
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
        if str(emoji).isdigit():
            # This is a Custom Emoji ID
            kwargs['icon_custom_emoji_id'] = str(emoji)
        else:
            # This is a standard emoji, prepend it to the text
            text = f"{emoji} {text}"
            
    if style:
        kwargs['style'] = style
        
    return InlineKeyboardButton(text=text, **kwargs)
