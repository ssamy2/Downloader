"""
Telegram Downloader Bot - Main Entry Point
High-performance media downloader with Cobalt API and yt-dlp
"""
import sys
import os
import subprocess
import re
import traceback
import importlib.util
from datetime import datetime
from typing import Dict, Optional
import json

# ==========================================
# 1. INTERACTIVE SETUP & DEPENDENCIES
# ==========================================
def initial_setup():
    """Interactive setup, dependency check and Node.js installation"""
    # Only prompt if running interactively
    if sys.stdin.isatty():
        print("="*50)
        print("🤖 Bot Initial Setup")
        print("="*50)
        token = input("Enter Bot Token (Press Enter to skip): ").strip()
        admin_id = input("Enter Admin ID (Press Enter to skip): ").strip()
        
        if token or admin_id:
            try:
                with open('config.py', 'r', encoding='utf-8') as f:
                    cfg = f.read()
                if token:
                    cfg = re.sub(r'TOKEN:\s*str\s*=\s*["\'][^"\']*["\']', f'TOKEN: str = "{token}"', cfg)
                if admin_id:
                    cfg = re.sub(r'PRIMARY_OWNER_ID:\s*int\s*=\s*\d+', f'PRIMARY_OWNER_ID: int = {admin_id}', cfg)
                with open('config.py', 'w', encoding='utf-8') as f:
                    f.write(cfg)
                print("✅ Config updated successfully.")
            except Exception as e:
                print(f"⚠️ Could not update config: {e}")

    # Check/Install Python dependencies
    print("\n📚 Checking Python dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'docs/requirements_linux.txt'])
        print("✅ Python dependencies are ready.")
    except Exception as e:
        print(f"⚠️ Failed to install python dependencies: {e}")

    # Check/Install Node.js
    print("\n🟢 Checking Node.js (Required for yt-dlp YouTube extraction)...")
    try:
        subprocess.run(['node', '-v'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Node.js is already installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("📦 Node.js not found. Attempting to install...")
        if sys.platform.startswith('linux'):
            try:
                subprocess.run('sudo apt update && sudo apt install -y nodejs', shell=True)
            except:
                try:
                    subprocess.run('sudo yum install -y nodejs || sudo dnf install -y nodejs', shell=True)
                except Exception as e:
                    print(f"⚠️ Could not install Node.js automatically: {e}")
        else:
            print("🔧 Please install Node.js manually from https://nodejs.org/")
            
    # Check FFmpeg
    import shutil
    if not shutil.which('ffmpeg'):
        print("\n🎬 FFmpeg not found! Attempting to install...")
        if sys.platform.startswith('linux'):
            subprocess.run('sudo apt install -y ffmpeg || sudo yum install -y ffmpeg || sudo dnf install -y ffmpeg', shell=True)
            
    # Create directories
    from pathlib import Path
    for dir_name in ['downloads', 'logs', 'data']:
        Path(dir_name).mkdir(exist_ok=True)
        
    print("\n✅ Initial setup complete! Starting the bot...\n")

# Run it immediately before any third-party imports
initial_setup()

# ==========================================
# 2. IMPORTS & CONFIGURATION
# ==========================================
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, FSInputFile
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus

from config import config, messages, emojis, build_btn
from core.database import db
from core.downloader import downloader, cleanup_scheduler, DownloadResult
from core.anonstories import anon_stories
from admin.admin_panel import admin_router, is_admin, notify_admins_error, IsAdminFilter, HasFullAccessFilter
from admin.broadcast_system import broadcast_router
from admin.settings_system import settings_router
from admin.channels_system import channels_router
from admin.ui_editor import ui_editor_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# User cooldown tracking (in-memory for speed)
user_cooldowns: Dict[int, datetime] = {}
# Pending downloads tracking
pending_downloads: Dict[int, Dict] = {}


class AudioSettingsStates(StatesGroup):
    """States for audio settings"""
    waiting_artist_name = State()
    waiting_file_name = State()
    waiting_file_description = State()
    waiting_thumbnail = State()


def create_progress_bar(percent: int, length: int = 10) -> str:
    """Create a visual progress bar"""
    filled = int(length * percent / 100)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {percent}%"


# Create main router for message handlers
main_router = Router()

# Helper functions for notifications
async def is_new_user_notification_enabled() -> bool:
    """Check if new user notifications are enabled"""
    settings = await db.get_bot_settings()
    return settings.get('notify_new_users', False)

async def is_download_notification_enabled() -> bool:
    """Check if download notifications are enabled"""
    settings = await db.get_bot_settings()
    return settings.get('notify_downloads', False)

async def get_notification_chat_id() -> Optional[int]:
    """Get notification chat ID (channel/group or owner)"""
    settings = await db.get_bot_settings()
    return settings.get('notification_chat_id', config.PRIMARY_OWNER_ID)

async def notify_new_user(bot: Bot, user) -> None:
    """Notify about new user"""
    try:
        chat_id = await get_notification_chat_id()
        if not chat_id:
            return
        
        text = messages.NEW_USER_NOTIFY.format(
            name=user.first_name,
            id=user.id,
            username=user.username or 'لا يوجد',
            time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        await bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error notifying new user: {e}")

async def notify_download(bot: Bot, user_id: int, url: str, platform: str) -> None:
    """Notify about download"""
    try:
        if not await is_download_notification_enabled():
            return
        
        chat_id = await get_notification_chat_id()
        if not chat_id:
            return
        
        text = messages.NEW_DOWNLOAD_NOTIFY.format(
            user=user_id,
            platform=platform,
            url=url[:50],
            time=datetime.now().strftime('%H:%M:%S')
        )
        await bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error notifying download: {e}")


def get_quality_keyboard(url: str) -> InlineKeyboardMarkup:
    """Create quality selection keyboard with detailed options"""
    from config import emojis
    
    # Check if Instagram URL
    is_instagram = 'instagram.com' in url.lower()
    
    # Instagram: فيديو وصوت فقط (بدون خيارات جودة)
    if is_instagram:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                build_btn('DL_VIDEO',  callback_data=f"dl:original"),
                build_btn('DL_AUDIO',  callback_data=f"dl:audio")
            ],
            [
                build_btn('CANCEL',  callback_data="dl:cancel")
            ]
        ])
    
    # Other platforms: جميع خيارات الجودة
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            build_btn('Q_144',  callback_data="dl:144p"),
            build_btn('Q_240',  callback_data="dl:240p"),
            build_btn('Q_360',  callback_data="dl:360p")
        ],
        [
            build_btn('Q_480',  callback_data="dl:480p"),
            build_btn('Q_720',  callback_data=f"dl:720p"),
            build_btn('Q_1080',  callback_data=f"dl:1080p")
        ],
        [
            build_btn('Q_1440',  callback_data=f"dl:1440p"),
            build_btn('Q_2160',  callback_data=f"dl:4k")
        ],
        [
            build_btn('ORIGINAL', callback_data=f"dl:original")
        ],
        [
            build_btn('DL_AUDIO_ONLY',  callback_data=f"dl:audio")
        ],
        [
            build_btn('DL_AUDIO_CUSTOM',  callback_data=f"dl:audio_custom")
        ],
        [
            build_btn('CANCEL',  callback_data="dl:cancel")
        ]
    ])


async def get_subscribe_keyboard(channels: list, bot: Bot = None) -> InlineKeyboardMarkup:
    """Create subscription check keyboard with support for private channels"""
    btn_list = []
    for ch in channels:
        try:
            url = None
            
            # أولاً: استخدم رابط الدعوة المحفوظ إذا كان موجوداً
            if ch.get('invite_link'):
                url = ch['invite_link']
            # ثانياً: للقنوات الخاصة بدون رابط محفوظ، أنشئ رابط جديد
            elif (ch.get('is_private') or not ch.get('username')) and bot and ch.get('channel_id'):
                try:
                    invite_link = await bot.create_chat_invite_link(ch['channel_id'])
                    url = invite_link.invite_link
                except Exception as e:
                    logger.warning(f"Could not create invite link for {ch.get('channel_id')}: {e}")
            # ثالثاً: للقنوات العامة بـ username صالح
            elif ch.get('username') and ch['username'] != 'None' and not ch['username'].startswith('channel_'):
                url = f"https://t.me/{ch['username']}"
            
            if url:
                channel_name = ch.get('title') or buttons.CHANNEL
                btn_list.append([
                    InlineKeyboardButton(
                        text=f"📢 {channel_name}", 
                        url=url,
                        style="primary"
                    )
                ])
        except Exception as e:
            logger.warning(f"Error creating button for channel {ch.get('channel_id')}: {e}")
            continue
    
    btn_list.append([
        build_btn('VERIFY',  callback_data="check_sub")
    ])
    return InlineKeyboardMarkup(inline_keyboard=btn_list)


async def check_subscription(bot: Bot, user_id: int) -> tuple[bool, list, list]:
    """Check if user is subscribed to all required channels
    
    Returns:
        tuple: (is_subscribed, not_subscribed_channels, invalid_channels)
    """
    channels = await db.get_required_channels()
    if not channels:
        return True, [], []
    
    not_subscribed = []
    invalid_channels = []
    
    for channel in channels:
        # تجاهل القنوات بدون channel_id (لا يمكن التحقق منها)
        if not channel.get('channel_id'):
            invalid_channels.append(channel)
            logger.warning(f"Channel without ID in database: {channel}")
            continue
        
        try:
            chat_id = channel['channel_id']
            
            # محاولة الوصول للقناة - استخدم channel_id مباشرة
            try:
                chat = await bot.get_chat(chat_id)
            except Exception as e:
                logger.warning(f"Cannot access channel {chat_id}: {e}")
                invalid_channels.append(channel)
                continue
            
            # التحقق من أن البوت أدمن في القناة
            try:
                bot_member = await bot.get_chat_member(chat_id, bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    logger.warning(f"Bot is not admin in channel {chat_id}")
                    invalid_channels.append(channel)
                    continue
            except Exception as e:
                logger.warning(f"Cannot check bot admin status: {e}")
                invalid_channels.append(channel)
                continue
            
            # التحقق من اشتراك المستخدم
            try:
                member = await bot.get_chat_member(chat_id, user_id)
                if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                    not_subscribed.append(channel)
            except Exception as e:
                logger.warning(f"Error checking subscription: {e}")
                not_subscribed.append(channel)
                
        except Exception as e:
            logger.error(f"Error checking channel {channel.get('channel_id')}: {e}")
            not_subscribed.append(channel)
    
    # إذا كانت كل القنوات غير صالحة، نسمح للمستخدم بالمرور
    if len(invalid_channels) == len(channels):
        logger.info("All channels are invalid, allowing user access")
        return True, [], invalid_channels
    
    return len(not_subscribed) == 0, not_subscribed, invalid_channels


async def check_user_access(message: Message, bot: Bot) -> bool:
    """Check if user can use the bot (not banned, subscribed, within limits)"""
    user_id = message.from_user.id
    
    # Get or create user
    user = await db.get_user(user_id)
    if not user:
        await db.add_user(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            language_code=message.from_user.language_code or 'en'
        )
        user = await db.get_user(user_id)
    
    # Check if banned
    if user and user.is_banned:
        await message.answer(messages.ERROR_BANNED, parse_mode="HTML")
        return False
    
    # Check subscription
    is_subscribed, not_subbed, invalid_channels = await check_subscription(bot, user_id)
    
    # عرض القنوات التي لم يشترك فيها المستخدم (لها channel_id)
    valid_not_subbed = [ch for ch in not_subbed if ch.get('channel_id')]
    
    if not is_subscribed and valid_not_subbed:
        # بناء نص القنوات - استخدم العنوان بدلاً من username
        channels_text = "\n".join([f"• {ch.get('title') or 'قناة'}" for ch in valid_not_subbed])
        await message.answer(
            messages.ERROR_SUBSCRIBE.format(channels=channels_text),
            reply_markup=await get_subscribe_keyboard(valid_not_subbed, bot),
            parse_mode="HTML"
        )
        return False
    
    # Check cooldown (in-memory for speed)
    if user_id in user_cooldowns:
        elapsed = (datetime.now() - user_cooldowns[user_id]).total_seconds()
        if elapsed < config.COOLDOWN_SECONDS:
            remaining = int(config.COOLDOWN_SECONDS - elapsed)
            await message.answer(
                messages.ERROR_COOLDOWN.format(seconds=remaining),
                parse_mode="HTML"
            )
            return False
    
    # Check daily limit
    limit_info = await db.check_daily_limit(user_id, config.DAILY_DOWNLOAD_LIMIT)
    if not limit_info['allowed']:
        await message.answer(
            messages.ERROR_LIMIT.format(
                limit=config.DAILY_DOWNLOAD_LIMIT,
                reset=limit_info['reset_time']
            ),
            parse_mode="HTML"
        )
        return False
    
    return True


async def process_download(
    bot: Bot, 
    chat_id: int, 
    user_id: int,
    url: str, 
    quality: str,
    status_message: Message,
    download_audio: bool = False,
    platform: str = None
) -> None:
    """Process a download request"""
    start_time = datetime.now()
    result: Optional[DownloadResult] = None
    
    try:
        # Progress callback
        async def update_progress(stage: str, percent: int):
            try:
                bar = create_progress_bar(percent)
                if stage == 'downloading':
                    text = messages.DOWNLOADING.format(progress=bar)
                elif stage == 'uploading':
                    text = messages.UPLOADING.format(progress=bar)
                elif stage == 'compressing':
                    text = messages.COMPRESSING + f"\n\n<blockquote>{bar}</blockquote>"
                else:
                    stage_text = {
                        'connecting': "<tg-emoji emoji-id='5197288647275071607'>🔗</tg-emoji> <b>جاري الاتصال...</b>",
                        'downloaded': "<tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> <b>تم التحميل</b>",
                        'compressed': "<tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> <b>تم الضغط</b>",
                    }.get(stage, stage)
                    text = f"{stage_text}\n\n<blockquote>{bar}</blockquote>"
                
                await status_message.edit_text(text, parse_mode="HTML")
            except:
                pass
        
        # Download
        result = await downloader.download(url, quality, update_progress, download_audio)
        
        if not result.success:
            raise Exception(result.error or "Download failed")
        
        # Update progress for upload
        await update_progress('uploading', 90)
        
        # Check file size
        file_size_mb = result.file_size / (1024 * 1024)
        if file_size_mb > 50:
            raise Exception(f"File too large: {file_size_mb:.1f}MB (max 50MB)")
        
        # Send file (audio or video)
        file_obj = FSInputFile(result.file_path)
        
        duration = (datetime.now() - start_time).total_seconds()
        caption = messages.SUCCESS.format(
            size=downloader.format_file_size(result.file_size),
            time=f"{duration:.1f}"
        )
        
        # Check if Twitter - add warning message
        is_twitter = platform and 'twitter' in platform.lower()
        if is_twitter:
            caption += "\n\n⚠️ <b>تنبيه:</b> هذه الرسالة ستُحذف بعد 30 ثانية\n💾 يرجى حفظها في السيفد مسدجس"
        
        if download_audio:
            # Send as audio file
            sent_msg = await bot.send_audio(
                chat_id=chat_id,
                audio=file_obj,
                caption=caption,
                parse_mode="HTML"
            )
        else:
            # Send as video
            sent_msg = await bot.send_video(
                chat_id=chat_id,
                video=file_obj,
                caption=caption,
                parse_mode="HTML",
                supports_streaming=True
            )
        
        # Delete status message
        await status_message.delete()
        
        # Schedule deletion for Twitter videos after 30 seconds
        if is_twitter:
            async def delete_twitter_message():
                try:
                    await asyncio.sleep(30)
                    await bot.delete_message(chat_id, sent_msg.message_id)
                except:
                    pass
            
            asyncio.create_task(delete_twitter_message())
        
        # Update user stats
        await db.increment_download(user_id)
        user_cooldowns[user_id] = datetime.now()
        
        # Log download
        await db.log_download(
            user_id=user_id,
            url=url,
            platform=result.platform,
            quality=quality,
            file_size=result.file_size,
            status='success'
        )
        
        # Schedule file cleanup
        await cleanup_scheduler.schedule_deletion(
            result.file_path, 
            config.FILE_DELETION_MINUTES
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Download error for {url}: {error_msg}")
        
        # Update status message with error
        try:
            if "private" in error_msg.lower() or "unavailable" in error_msg.lower():
                await status_message.edit_text(messages.ERROR_PRIVATE, parse_mode="HTML")
            else:
                await status_message.edit_text(
                    messages.ERROR_GENERIC.format(error=error_msg[:200]),
                    parse_mode="HTML"
                )
        except:
            pass
        
        # Log error
        await db.log_download(
            user_id=user_id,
            url=url,
            platform=result.platform if result else 'unknown',
            quality=quality,
            status='failed',
            error_message=error_msg
        )
        
        # Notify admins (except for file size limit errors)
        is_file_size_error = (
            result and result.file_size and 
            result.file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024
        )
        
        if not is_file_size_error:
            await notify_admins_error(
                bot=bot,
                user_id=user_id,
                url=url,
                error_type=type(e).__name__,
                error_message=error_msg
            )
        
        # Cleanup on error
        if result and result.file_path:
            await downloader.cleanup_file(result.file_path)


# ==================== Handlers ====================

@main_router.message(CommandStart())
async def start_command(message: Message, bot: Bot):
    """Handle /start command"""
    user_id = message.from_user.id
    
    # Add user to database
    await db.add_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        language_code=message.from_user.language_code or 'en'
    )
    
    # Notify admins about new user
    if await is_new_user_notification_enabled():
        await notify_new_user(bot, message.from_user)
    
    await message.answer(messages.WELCOME, parse_mode="HTML")


async def process_instagram_stories(message: Message, bot: Bot, username: str):
    """Handle downloading instagram stories and info via username"""
    status_msg = await message.answer("🔄 <b>جاري جلب بيانات الحساب والقصص...</b>", parse_mode="HTML")
    
    data = await anon_stories.get_stories(username)
    if not data:
        await status_msg.edit_text("❌ عذراً، لم أتمكن من جلب بيانات هذا الحساب. قد يكون الحساب خاص (Private) أو غير موجود.")
        return
        
    user_info = data.get("user_info", {})
    stories = data.get("stories", [])
    
    if not user_info:
        await status_msg.edit_text("❌ لم يتم العثور على هذا اليوزر نيم.")
        return
        
    # Send user info
    info_text = f"""
<b><tg-emoji emoji-id='5332724926216428039'>👤</tg-emoji> معلومات الحساب:</b>

<blockquote><b>الاسم:</b> {user_info.get('full_name', '')}
<b>اليوزر:</b> @{user_info.get('username', username)}
<b>المتابعين:</b> {user_info.get('followers', 0)}
<b>يتابع:</b> {user_info.get('following', 0)}
<b>المنشورات:</b> {user_info.get('posts', 0)}
<b>القصص الحالية:</b> {len(stories)}</blockquote>
"""
    
    profile_pic = anon_stories.fix_url(user_info.get("profile_pic_url", ""))
    
    try:
        await status_msg.delete()
        if profile_pic:
            await bot.send_photo(message.chat.id, profile_pic, caption=info_text, parse_mode="HTML")
        else:
            await message.answer(info_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending profile info: {e}")
        await message.answer(info_text, parse_mode="HTML")
        
    if not stories:
        await message.answer("ℹ️ هذا الحساب لا يملك أي قصص (Stories) نشطة حالياً.")
        return
        
    await message.answer(f"⏳ <b>جاري إرسال {len(stories)} قصص...</b>", parse_mode="HTML")
    
    for idx, story in enumerate(stories, 1):
        media_url = anon_stories.fix_url(story.get("source", ""))
        if not media_url:
            continue
            
        media_type = story.get("media_type", "image")
        caption = f"📖 <b>القصة ({idx}/{len(stories)})</b>\\n👤 @{user_info.get('username', username)}"
        
        try:
            if media_type == "image":
                await bot.send_photo(message.chat.id, media_url, caption=caption, parse_mode="HTML")
            else:
                await bot.send_video(message.chat.id, media_url, caption=caption, parse_mode="HTML")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending story {idx}: {e}")



@main_router.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command"""
    help_text = """
<b>📖 دليل الاستخدام</b>

1️⃣ أرسل رابط من أي منصة مدعومة
2️⃣ اختر جودة التحميل
3️⃣ انتظر حتى يتم التحميل والإرسال

<b>المنصات المدعومة:</b>
• Instagram (Reels, Stories, Posts)
• TikTok
• YouTube (Shorts/Videos)
• Twitter/X
• Kwai

<b>الحدود:</b>
• {limit} تحميل يومياً
• انتظار {cooldown} ثواني بين كل طلب

<b>الجودات:</b>
• <b>Standard</b> - 480p (سريع، حجم صغير)
• <b>HD</b> - 720p (جودة عالية)
• <b>Original</b> - الجودة الأصلية
""".format(limit=config.DAILY_DOWNLOAD_LIMIT, cooldown=config.COOLDOWN_SECONDS)
    
    await message.answer(help_text, parse_mode="HTML")


@main_router.message(F.text)
async def handle_url_message(message: Message, bot: Bot):
    """Handle messages containing URLs"""
    # Check user access
    if not await check_user_access(message, bot):
        return
        
    text = message.text.strip()
    
    # --- Intercept Instagram Stories & Usernames ---
    is_ig_username = False
    username = ""
    
    # 1. Pure username starting with @ or just a username
    if len(text.split()) == 1 and not ('http' in text.lower() or 'www.' in text.lower()):
        is_ig_username = True
        username = text.lstrip('@')
    # 2. Instagram Profile Link or Story Link
    elif 'instagram.com/' in text.lower():
        if '/stories/' in text.lower():
            parts = text.lower().split('/stories/')
            if len(parts) > 1:
                username = parts[1].split('/')[0]
                is_ig_username = True
        elif not any(x in text.lower() for x in ['/p/', '/reel/', '/reels/', '/tv/']):
            parts = text.lower().split('instagram.com/')
            if len(parts) > 1:
                username = parts[1].split('/')[0].split('?')[0]
                if username and username not in ['stories', 'p', 'reel', 'reels', 'tv', 'explore']:
                    is_ig_username = True
                    
    if is_ig_username and username:
        await process_instagram_stories(message, bot, username)
        return
    # -----------------------------------------------
    
    # Extract URLs
    urls = downloader.extract_urls(text)
    
    if not urls:
        # Check if it looks like a URL but unsupported
        if 'http' in text.lower() or 'www.' in text.lower():
            await message.answer(messages.ERROR_UNSUPPORTED, parse_mode="HTML")
        return
    
    # Handle single URL
    if len(urls) == 1:
        url = urls[0]
        platform = downloader.detect_platform(url)
        
        # Store URL for quality selection
        pending_downloads[message.from_user.id] = {
            'url': url,
            'platform': platform,
            'message_id': message.message_id
        }
        
        await message.answer(
            messages.QUALITY_SELECT,
            reply_markup=get_quality_keyboard(url),
            parse_mode="HTML"
        )
    else:
        # Handle multiple URLs - ask for quality once
        pending_downloads[message.from_user.id] = {
            'urls': urls,
            'message_id': message.message_id
        }
        
        await message.answer(
            f"🔗 تم اكتشاف <b>{len(urls)}</b> روابط\n\n" + messages.QUALITY_SELECT,
            reply_markup=get_quality_keyboard("batch"),
            parse_mode="HTML"
        )


def get_audio_settings_keyboard() -> InlineKeyboardMarkup:
    """Create audio settings keyboard"""
    from config import emojis
    return InlineKeyboardMarkup(inline_keyboard=[
        [build_btn('EDIT_ARTIST',  callback_data="audio_set:artist")],
        [build_btn('EDIT_THUMB',  callback_data="audio_set:thumbnail")],
        [build_btn('EDIT_FILENAME',  callback_data="audio_set:filename")],
        [build_btn('EDIT_DESC',  callback_data="audio_set:description")],
        [build_btn('DL_CURRENT_SETTING',  callback_data="audio_set:download")],
        [build_btn('SKIP_SETTINGS',  callback_data="audio_set:skip")],
        [build_btn('CANCEL',  callback_data="dl:cancel")]
    ])


def get_audio_settings_text(settings: dict) -> str:
    """Generate audio settings display text"""
    artist = settings.get('artist', 'غير محدد')
    filename = settings.get('filename', 'غير محدد')
    description = settings.get('description', 'غير محدد')
    has_thumbnail = '✅' if settings.get('thumbnail') else '❌'
    
    return f"""
🎵 <b>إعدادات الصوت (بصمة)</b>

<b>الإعدادات الحالية:</b>
🎤 <b>اسم الفنان:</b> {artist}
📝 <b>اسم الملف:</b> {filename}
📄 <b>الوصف:</b> {description}
🖼 <b>صورة مصغرة:</b> {has_thumbnail}

<i>اختر الإعداد لتعديله أو تابع التحميل:</i>
"""


@main_router.callback_query(F.data.startswith("dl:"))
async def quality_callback(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Handle quality selection"""
    user_id = callback.from_user.id
    action = callback.data.split(":")[1]
    
    if action == "cancel":
        pending_downloads.pop(user_id, None)
        await state.clear()
        await callback.message.delete()
        return
    
    # Get pending download - don't pop for audio_custom
    if action == "audio_custom":
        pending = pending_downloads.get(user_id, None)
    else:
        pending = pending_downloads.pop(user_id, None)
    
    if not pending:
        await callback.answer("⏰ انتهت الصلاحية، أرسل الرابط مرة أخرى", show_alert=True)
        await callback.message.delete()
        return
    
    # Handle audio with custom settings
    if action == "audio_custom":
        # Initialize audio settings
        audio_settings = {
            'artist': '',
            'filename': '',
            'description': '',
            'thumbnail': None
        }
        await state.update_data(audio_settings=audio_settings)
        
        await callback.message.edit_text(
            get_audio_settings_text(audio_settings),
            reply_markup=get_audio_settings_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Check if audio download
    download_audio = (action == "audio")
    quality = "hd" if download_audio else action  # Use HD quality for audio extraction
    
    # Handle single URL
    if 'url' in pending:
        url = pending['url']
        platform = pending.get('platform', 'unknown')
        
        # Update message to processing status
        status_text = messages.PROCESSING
        status_msg = await callback.message.edit_text(
            status_text,
            parse_mode="HTML"
        )
        
        # Notify about download
        await notify_download(bot, user_id, url, platform)
        
        # Process download
        await process_download(
            bot=bot,
            chat_id=callback.message.chat.id,
            user_id=user_id,
            url=url,
            quality=quality,
            status_message=status_msg,
            download_audio=download_audio,
            platform=platform
        )
    
    # Handle batch URLs
    elif 'urls' in pending:
        urls = pending['urls']
        await callback.message.edit_text(
            messages.PROCESSING,
            parse_mode="HTML"
        )
        
        for i, url in enumerate(urls):
            # Check limits for each download
            limit_info = await db.check_daily_limit(user_id, config.DAILY_DOWNLOAD_LIMIT)
            if not limit_info['allowed']:
                await callback.message.answer(
                    messages.ERROR_LIMIT.format(
                        limit=config.DAILY_DOWNLOAD_LIMIT,
                        reset=limit_info['reset_time']
                    ),
                    parse_mode="HTML"
                )
                break
            
            status_msg = await callback.message.answer(
                messages.PROCESSING,
                parse_mode="HTML"
            )
            
            await process_download(
                bot=bot,
                chat_id=callback.message.chat.id,
                user_id=user_id,
                url=url,
                quality=quality,
                status_message=status_msg
            )
            
            # Small delay between downloads
            await asyncio.sleep(1)


@main_router.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    """Handle subscription check button"""
    user_id = callback.from_user.id
    
    is_subscribed, not_subbed, invalid_channels = await check_subscription(bot, user_id)
    
    # عرض القنوات التي لها channel_id
    valid_not_subbed = [ch for ch in not_subbed if ch.get('channel_id')]
    
    if is_subscribed or not valid_not_subbed:
        await callback.answer("✅ تم التحقق! يمكنك استخدام البوت الآن", show_alert=True)
        await callback.message.delete()
    else:
        channels_text = "\n".join([f"• {ch.get('title') or 'قناة'}" for ch in valid_not_subbed])
        await callback.answer(
            "❌ لم يتم الاشتراك في جميع القنوات بعد",
            show_alert=True
        )
        await callback.message.edit_text(
            messages.ERROR_SUBSCRIBE.format(channels=channels_text),
            reply_markup=await get_subscribe_keyboard(valid_not_subbed, bot),
            parse_mode="HTML"
        )


# ==================== Audio Settings Handlers ====================

@main_router.callback_query(F.data.startswith("audio_set:"))
async def audio_settings_callback(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Handle audio settings callbacks"""
    user_id = callback.from_user.id
    action = callback.data.split(":")[1]
    
    # Get current state data
    state_data = await state.get_data()
    audio_settings = state_data.get('audio_settings', {})
    
    if action == "artist":
        await callback.message.edit_text(
            "🎤 <b>تغيير اسم الفنان</b>\n\nأرسل اسم الفنان المطلوب:",
            parse_mode="HTML"
        )
        await state.set_state(AudioSettingsStates.waiting_artist_name)
        
    elif action == "filename":
        await callback.message.edit_text(
            "📝 <b>تغيير اسم الملف</b>\n\nأرسل اسم الملف المطلوب (بدون امتداد):",
            parse_mode="HTML"
        )
        await state.set_state(AudioSettingsStates.waiting_file_name)
        
    elif action == "description":
        await callback.message.edit_text(
            "📄 <b>تغيير وصف الملف</b>\n\nأرسل وصف الملف المطلوب:",
            parse_mode="HTML"
        )
        await state.set_state(AudioSettingsStates.waiting_file_description)
        
    elif action == "thumbnail":
        await callback.message.edit_text(
            "🖼 <b>تغيير الصورة المصغرة</b>\n\nأرسل الصورة المطلوبة:",
            parse_mode="HTML"
        )
        await state.set_state(AudioSettingsStates.waiting_thumbnail)
        
    elif action == "download" or action == "skip":
        # Start download with settings
        pending = pending_downloads.pop(user_id, None)
        if not pending:
            await callback.answer("⏰ انتهت الصلاحية، أرسل الرابط مرة أخرى", show_alert=True)
            await state.clear()
            await callback.message.delete()
            return
        
        url = pending.get('url')
        platform = pending.get('platform', 'unknown')
        
        status_msg = await callback.message.edit_text(
            "🎵 <b>جاري تحميل ومعالجة الصوت...</b>",
            parse_mode="HTML"
        )
        
        # Notify about download
        await notify_download(bot, user_id, url, platform)
        
        # Process download with custom settings
        await process_audio_download(
            bot=bot,
            chat_id=callback.message.chat.id,
            user_id=user_id,
            url=url,
            status_message=status_msg,
            audio_settings=audio_settings if action == "download" else {}
        )
        
        await state.clear()


@main_router.message(AudioSettingsStates.waiting_artist_name)
async def process_artist_name(message: Message, state: FSMContext):
    """Process artist name input"""
    state_data = await state.get_data()
    audio_settings = state_data.get('audio_settings', {})
    audio_settings['artist'] = message.text.strip()
    await state.update_data(audio_settings=audio_settings)
    
    await message.answer(
        get_audio_settings_text(audio_settings),
        reply_markup=get_audio_settings_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(None)


@main_router.message(AudioSettingsStates.waiting_file_name)
async def process_file_name(message: Message, state: FSMContext):
    """Process file name input"""
    state_data = await state.get_data()
    audio_settings = state_data.get('audio_settings', {})
    audio_settings['filename'] = message.text.strip()
    await state.update_data(audio_settings=audio_settings)
    
    await message.answer(
        get_audio_settings_text(audio_settings),
        reply_markup=get_audio_settings_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(None)


@main_router.message(AudioSettingsStates.waiting_file_description)
async def process_file_description(message: Message, state: FSMContext):
    """Process file description input"""
    state_data = await state.get_data()
    audio_settings = state_data.get('audio_settings', {})
    audio_settings['description'] = message.text.strip()
    await state.update_data(audio_settings=audio_settings)
    
    await message.answer(
        get_audio_settings_text(audio_settings),
        reply_markup=get_audio_settings_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(None)


@main_router.message(AudioSettingsStates.waiting_thumbnail, F.photo)
async def process_thumbnail(message: Message, state: FSMContext, bot: Bot):
    """Process thumbnail image"""
    try:
        # Get the largest photo
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        
        # Download to temp location
        import tempfile
        import os
        thumbnail_path = os.path.join(tempfile.gettempdir(), f"thumb_{message.from_user.id}.jpg")
        await bot.download_file(file.file_path, thumbnail_path)
        
        state_data = await state.get_data()
        audio_settings = state_data.get('audio_settings', {})
        audio_settings['thumbnail'] = thumbnail_path
        await state.update_data(audio_settings=audio_settings)
        
        await message.answer(
            get_audio_settings_text(audio_settings),
            reply_markup=get_audio_settings_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(None)
        
    except Exception as e:
        logger.error(f"Error processing thumbnail: {e}")
        await message.answer("❌ خطأ في معالجة الصورة، حاول مرة أخرى")


@main_router.message(AudioSettingsStates.waiting_thumbnail)
async def process_thumbnail_invalid(message: Message):
    """Handle invalid thumbnail input"""
    await message.answer("❌ يرجى إرسال صورة فقط!")


async def process_audio_download(
    bot: Bot,
    chat_id: int,
    user_id: int,
    url: str,
    status_message: Message,
    audio_settings: dict = None
) -> None:
    """Process audio download with custom settings"""
    start_time = datetime.now()
    result: Optional[DownloadResult] = None
    
    try:
        # Progress callback
        async def update_progress(stage: str, percent: int):
            try:
                bar = create_progress_bar(percent)
                if stage == 'downloading':
                    text = messages.DOWNLOADING.format(progress=bar)
                elif stage == 'uploading':
                    text = messages.UPLOADING.format(progress=bar)
                else:
                    stage_text = {
                        'connecting': "<tg-emoji emoji-id='5197288647275071607'>🔗</tg-emoji> <b>جاري الاتصال...</b>",
                        'downloaded': "<tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> <b>تم التحميل</b>",
                        'processing': "<tg-emoji emoji-id='5382194935057372936'>⏱</tg-emoji> <b>جاري المعالجة...</b>",
                    }.get(stage, stage)
                    text = f"{stage_text}\n\n<blockquote>{bar}</blockquote>"
                
                await status_message.edit_text(text, parse_mode="HTML")
            except:
                pass
        
        # Download audio
        result = await downloader.download(url, "hd", update_progress, download_audio=True)
        
        if not result.success:
            raise Exception(result.error or "Download failed")
        
        # Apply custom settings if provided
        if audio_settings and any(audio_settings.values()):
            await update_progress('processing', 80)
            result = await downloader.apply_audio_metadata(
                result.file_path,
                artist=audio_settings.get('artist', ''),
                title=audio_settings.get('filename', ''),
                description=audio_settings.get('description', ''),
                thumbnail=audio_settings.get('thumbnail')
            )
        
        await update_progress('uploading', 90)
        
        # Check file size
        file_size_mb = result.file_size / (1024 * 1024)
        if file_size_mb > 50:
            raise Exception(f"File too large: {file_size_mb:.1f}MB (max 50MB)")
        
        # Prepare audio file
        file_obj = FSInputFile(result.file_path)
        
        duration = (datetime.now() - start_time).total_seconds()
        caption = messages.SUCCESS.format(
            size=downloader.format_file_size(result.file_size),
            time=f"{duration:.1f}"
        )
        
        # Build performer and title from settings
        performer = audio_settings.get('artist') if audio_settings else None
        title = audio_settings.get('filename') if audio_settings else None
        
        # Get thumbnail if exists
        thumb = None
        if audio_settings and audio_settings.get('thumbnail'):
            try:
                thumb = FSInputFile(audio_settings['thumbnail'])
            except:
                pass
        
        # Send audio with metadata
        await bot.send_audio(
            chat_id=chat_id,
            audio=file_obj,
            caption=caption,
            performer=performer,
            title=title,
            thumbnail=thumb,
            parse_mode="HTML"
        )
        
        # Delete status message
        await status_message.delete()
        
        # Update user stats
        await db.increment_download(user_id)
        user_cooldowns[user_id] = datetime.now()
        
        # Log download
        await db.log_download(
            user_id=user_id,
            url=url,
            platform=result.platform,
            quality="audio_custom",
            file_size=result.file_size,
            status='success'
        )
        
        # Schedule file cleanup
        await cleanup_scheduler.schedule_deletion(
            result.file_path,
            config.FILE_DELETION_MINUTES
        )
        
        # Clean up thumbnail
        if audio_settings and audio_settings.get('thumbnail'):
            try:
                import os
                os.remove(audio_settings['thumbnail'])
            except:
                pass
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Audio download error for {url}: {error_msg}")
        
        try:
            await status_message.edit_text(
                messages.ERROR_GENERIC.format(error=error_msg[:200]),
                parse_mode="HTML"
            )
        except:
            pass
        
        # Log error
        await db.log_download(
            user_id=user_id,
            url=url,
            platform=result.platform if result else 'unknown',
            quality="audio_custom",
            status='failed',
            error_message=error_msg
        )
        
        # Cleanup on error
        if result and result.file_path:
            await downloader.cleanup_file(result.file_path)


async def on_startup(bot: Bot):
    """Startup tasks"""
    logger.info("Bot starting up...")
    
    # Connect to database
    await db.connect()
    
    # Create download directory
    import os
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    
    logger.info("Bot started successfully!")


async def on_shutdown(bot: Bot):
    """Shutdown tasks"""
    logger.info("Bot shutting down...")
    
    # Cancel all scheduled deletions
    await cleanup_scheduler.cancel_all()
    
    # Close downloader session
    await downloader.close()
    
    # Close database
    await db.close()
    
    logger.info("Bot shutdown complete")


def setup_handlers(dp: Dispatcher):
    """Setup all message and callback handlers"""
    
    # Commands
    dp.message.register(start_command, CommandStart())
    dp.message.register(help_command, Command("help"))
    
    # Include admin router
    dp.include_router(admin_router)
    
    # URL messages (must be after commands)
    dp.message.register(handle_url_message, F.text)
    
    # Callbacks
    dp.callback_query.register(quality_callback, F.data.startswith("dl:"))
    dp.callback_query.register(check_subscription_callback, F.data == "check_sub")


async def main():
    """Main bot function"""
    logger.info("=" * 50)
    logger.info("🚀 Starting bot polling...")
    logger.info("=" * 50)
    
    # Initialize database
    await db.connect()
    logger.info("✅ Bot starting up...")
    
    # Create dispatcher
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Apply Security Filters
    admin_router.message.filter(IsAdminFilter())
    admin_router.callback_query.filter(IsAdminFilter())
    
    broadcast_router.message.filter(HasFullAccessFilter())
    broadcast_router.callback_query.filter(HasFullAccessFilter())
    
    settings_router.message.filter(HasFullAccessFilter())
    settings_router.callback_query.filter(HasFullAccessFilter())
    
    channels_router.message.filter(HasFullAccessFilter())
    channels_router.callback_query.filter(HasFullAccessFilter())
    
    ui_editor_router.message.filter(HasFullAccessFilter())
    ui_editor_router.callback_query.filter(HasFullAccessFilter())

    # Include routers
    dp.include_router(admin_router)
    dp.include_router(broadcast_router)
    dp.include_router(settings_router)
    dp.include_router(channels_router)
    dp.include_router(ui_editor_router)
    dp.include_router(main_router)
    
    # Create bot
    bot = Bot(
        token=config.TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    try:
        # Delete any existing webhook to avoid conflicts
        logger.info("🔧 Cleaning up old webhooks...")
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhooks cleaned")
        except Exception as e:
            logger.warning(f"⚠️  Webhook cleanup: {e}")
        
        # Get bot info
        me = await bot.get_me()
        logger.info(f"✅ Bot info: @{me.username} (ID: {me.id})")
        
        logger.info("✅ Bot started successfully!")
        logger.info("=" * 50)
        logger.info("📡 Polling started - waiting for updates...")
        logger.info("=" * 50)
        
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except KeyboardInterrupt:
        logger.info("⏹️  Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}", exc_info=True)
        try:
            await notify_admins_error(bot, 0, "system", "bot_error", str(e))
        except:
            pass
    finally:
        logger.info("=" * 50)
        logger.info("🛑 Bot shutting down...")
        logger.info("=" * 50)
        await db.close()
        logger.info("✅ Database connection closed")
        await bot.session.close()
        logger.info("✅ Bot shutdown complete")
        logger.info("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        traceback.print_exc()
