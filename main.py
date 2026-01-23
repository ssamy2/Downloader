"""
Telegram Downloader Bot - Main Entry Point
High-performance media downloader with Cobalt API and yt-dlp
"""
import asyncio
import logging
import sys
import traceback
import importlib.util
from datetime import datetime
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, FSInputFile
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus

# Auto-setup: Check and install dependencies
def run_auto_setup():
    """Run automatic setup if needed"""
    print("🔍 Checking dependencies...")
    
    # Check required packages
    required_packages = [
        ('aiogram', '3.13.1'),
        ('aiosqlite', '0.20.0'),
        ('aiohttp', '3.10.10'),
        ('aiofiles', '24.1.0'),
        ('yt_dlp', '2024.11.18'),
        ('psutil', '6.1.0')
    ]
    
    missing_packages = []
    
    for package, min_version in required_packages:
        try:
            if package == 'yt_dlp':
                spec = importlib.util.find_spec('yt_dlp')
            else:
                spec = importlib.util.find_spec(package)
            
            if spec is None:
                missing_packages.append(package)
                print(f"❌ {package} - Missing")
            else:
                print(f"✅ {package} - OK")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - Missing")
    
    # Install missing packages
    if missing_packages:
        print(f"📦 Installing missing packages: {', '.join(missing_packages)}")
        import subprocess
        
        for package in missing_packages:
            try:
                if package == 'yt_dlp':
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp>=2024.11.18"])
                else:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package}"])
                print(f"✅ {package} installed")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {package}: {e}")
                return False
    
    # Check FFmpeg
    import shutil
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        print("❌ FFmpeg not found!")
        
        # Try to install FFmpeg automatically
        import platform
        system = platform.system().lower()
        
        if system == 'linux':
            print("🐧 Linux detected - attempting to install FFmpeg...")
            try:
                subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], 
                             check=True, capture_output=True)
                ffmpeg_path = shutil.which('ffmpeg')
                if ffmpeg_path:
                    print("✅ FFmpeg installed successfully")
            except:
                print("⚠️  Could not install FFmpeg automatically")
                print("🔧 Please install FFmpeg manually:")
                print("   Ubuntu/Debian: sudo apt install ffmpeg")
                print("   CentOS/RHEL: sudo yum install ffmpeg")
                print("   Windows: Download from https://www.gyan.dev/ffmpeg/builds/")
                return False
        
        elif system == 'windows':
            print("🪟 Windows detected - checking for local FFmpeg...")
            from pathlib import Path
            
            # Check for FFmpeg in project directory
            ffmpeg_dir = Path('ffmpeg-8.0.1-essentials_build')
            if ffmpeg_dir.exists():
                ffmpeg_exe = ffmpeg_dir / 'bin' / 'ffmpeg.exe'
                if ffmpeg_exe.exists():
                    ffmpeg_path = str(ffmpeg_exe.absolute())
                    print(f"✅ Found local FFmpeg: {ffmpeg_path}")
                    
                    # Update config
                    try:
                        with open('config.py', 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        import re
                        # Escape backslashes properly for regex replacement
                        escaped_path = ffmpeg_path.replace('\\', '\\\\')
                        content = re.sub(
                            r'FFMPEG_PATH:\s*str\s*=\s*["\'][^"\']*["\']',
                            f'FFMPEG_PATH: str = r"{escaped_path}"',
                            content
                        )
                        
                        with open('config.py', 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        print("✅ Updated FFmpeg path in config.py")
                    except Exception as e:
                        print(f"⚠️  Could not update config.py: {e}")
                        print(f"🔧 Manual fix: Update this line in config.py:")
                        print(f'   FFMPEG_PATH: str = r"{ffmpeg_path}"')
                else:
                    print("❌ FFmpeg executable not found in project directory")
                    return False
            else:
                print("❌ FFmpeg not found. Please download and extract to project folder")
                return False
    
    # Create necessary directories
    from pathlib import Path
    for dir_name in ['downloads', 'logs']:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
    
    print("✅ All dependencies ready!")
    return True

# Run auto-setup before importing other modules
if not run_auto_setup():
    print("❌ Setup failed. Please install dependencies manually.")
    sys.exit(1)

from config import config, messages
from database import db
from downloader import downloader, cleanup_scheduler, DownloadResult
from admin_panel import admin_router, is_admin, notify_admins_error
from broadcast_system import broadcast_router
from settings_system import settings_router
from channels_system import channels_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# User cooldown tracking (in-memory for speed)
user_cooldowns: Dict[int, datetime] = {}
# Pending downloads tracking
pending_downloads: Dict[int, Dict] = {}


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
        
        text = f"""
🆕 <b>مستخدم جديد</b>

👤 الاسم: {user.first_name}
🆔 المعرف: <code>{user.id}</code>
📝 اليوزر: @{user.username or 'لا يوجد'}
⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
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
        
        text = f"""
📥 <b>تحميل جديد</b>

👤 المستخدم: <code>{user_id}</code>
🌐 المنصة: {platform}
🔗 الرابط: <code>{url[:50]}...</code>
⏰ الوقت: {datetime.now().strftime('%H:%M:%S')}
"""
        await bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error notifying download: {e}")


def get_quality_keyboard(url: str) -> InlineKeyboardMarkup:
    """Create quality selection keyboard with detailed options"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 144p", callback_data=f"dl:144p"),
            InlineKeyboardButton(text="📱 240p", callback_data=f"dl:240p"),
            InlineKeyboardButton(text="📱 360p", callback_data=f"dl:360p")
        ],
        [
            InlineKeyboardButton(text="📺 480p", callback_data=f"dl:480p"),
            InlineKeyboardButton(text="📺 720p (HD)", callback_data=f"dl:720p"),
            InlineKeyboardButton(text="📺 1080p (FHD)", callback_data=f"dl:1080p")
        ],
        [
            InlineKeyboardButton(text="🎬 1440p (2K)", callback_data=f"dl:1440p"),
            InlineKeyboardButton(text="🎬 2160p (4K)", callback_data=f"dl:4k")
        ],
        [
            InlineKeyboardButton(text="✨ الجودة الأصلية", callback_data=f"dl:original")
        ],
        [
            InlineKeyboardButton(text="❌ إلغاء", callback_data="dl:cancel")
        ]
    ])


def get_subscribe_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Create subscription check keyboard"""
    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                text=f"📢 {ch['title'] or ch['username']}", 
                url=f"https://t.me/{ch['username']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="✅ تحقق", callback_data="check_sub")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def check_subscription(bot: Bot, user_id: int) -> tuple[bool, list]:
    """Check if user is subscribed to all required channels"""
    channels = await db.get_required_channels()
    if not channels:
        return True, []
    
    not_subscribed = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(f"@{channel['username']}", user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                not_subscribed.append(channel)
        except Exception as e:
            logger.warning(f"Error checking subscription for {channel['username']}: {e}")
            # If we can't check, assume not subscribed
            not_subscribed.append(channel)
    
    return len(not_subscribed) == 0, not_subscribed


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
    is_subscribed, not_subbed = await check_subscription(bot, user_id)
    if not is_subscribed:
        channels_text = "\n".join([f"• @{ch['username']}" for ch in not_subbed])
        await message.answer(
            messages.ERROR_SUBSCRIBE.format(channels=channels_text),
            reply_markup=get_subscribe_keyboard(not_subbed),
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
    status_message: Message
) -> None:
    """Process a download request"""
    start_time = datetime.now()
    result: Optional[DownloadResult] = None
    
    try:
        # Progress callback
        async def update_progress(stage: str, percent: int):
            try:
                stage_text = {
                    'connecting': '🔗 جاري الاتصال...',
                    'downloading': '📥 جاري التحميل...',
                    'downloaded': '✅ تم التحميل',
                    'compressing': '🗜 جاري الضغط...',
                    'compressed': '✅ تم الضغط',
                    'uploading': '📤 جاري الرفع...'
                }.get(stage, stage)
                
                bar = create_progress_bar(percent)
                await status_message.edit_text(
                    f"<b>{stage_text}</b>\n{bar}",
                    parse_mode="HTML"
                )
            except:
                pass
        
        # Download
        result = await downloader.download(url, quality, update_progress)
        
        if not result.success:
            raise Exception(result.error or "Download failed")
        
        # Update progress for upload
        await update_progress('uploading', 90)
        
        # Check file size
        file_size_mb = result.file_size / (1024 * 1024)
        if file_size_mb > 50:
            raise Exception(f"File too large: {file_size_mb:.1f}MB (max 50MB)")
        
        # Send video
        video_file = FSInputFile(result.file_path)
        
        duration = (datetime.now() - start_time).total_seconds()
        caption = messages.SUCCESS.format(
            size=downloader.format_file_size(result.file_size),
            time=f"{duration:.1f}"
        )
        
        await bot.send_video(
            chat_id=chat_id,
            video=video_file,
            caption=caption,
            parse_mode="HTML",
            supports_streaming=True
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
        
        # Notify admins
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
    
    # Extract URLs
    urls = downloader.extract_urls(message.text)
    
    if not urls:
        # Check if it looks like a URL but unsupported
        if 'http' in message.text.lower() or 'www.' in message.text.lower():
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


@main_router.callback_query(F.data.startswith("dl:"))
async def quality_callback(callback: CallbackQuery, bot: Bot):
    """Handle quality selection"""
    user_id = callback.from_user.id
    action = callback.data.split(":")[1]
    
    if action == "cancel":
        pending_downloads.pop(user_id, None)
        await callback.message.delete()
        return
    
    # Get pending download
    pending = pending_downloads.pop(user_id, None)
    if not pending:
        await callback.answer("⏰ انتهت الصلاحية، أرسل الرابط مرة أخرى", show_alert=True)
        await callback.message.delete()
        return
    
    quality = action  # standard, hd, or original
    
    # Handle single URL
    if 'url' in pending:
        url = pending['url']
        
        # Update message to processing status
        status_msg = await callback.message.edit_text(
            messages.PROCESSING,
            parse_mode="HTML"
        )
        
        # Notify about download
        platform = pending.get('platform', 'unknown')
        await notify_download(bot, user_id, url, platform)
        
        # Process download
        await process_download(
            bot=bot,
            chat_id=callback.message.chat.id,
            user_id=user_id,
            url=url,
            quality=quality,
            status_message=status_msg
        )
    
    # Handle batch URLs
    elif 'urls' in pending:
        urls = pending['urls']
        await callback.message.edit_text(
            f"📥 <b>جاري تحميل {len(urls)} فيديو...</b>",
            parse_mode="HTML"
        )
        
        for i, url in enumerate(urls):
            # Check limits for each download
            limit_info = await db.check_daily_limit(user_id, config.DAILY_DOWNLOAD_LIMIT)
            if not limit_info['allowed']:
                await callback.message.answer(
                    f"⚠️ تم تحميل {i} من {len(urls)} فيديو\n" +
                    messages.ERROR_LIMIT.format(
                        limit=config.DAILY_DOWNLOAD_LIMIT,
                        reset=limit_info['reset_time']
                    ),
                    parse_mode="HTML"
                )
                break
            
            status_msg = await callback.message.answer(
                f"📥 <b>تحميل {i+1}/{len(urls)}</b>\n{messages.PROCESSING}",
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
    
    is_subscribed, not_subbed = await check_subscription(bot, user_id)
    
    if is_subscribed:
        await callback.answer("✅ تم التحقق! يمكنك استخدام البوت الآن", show_alert=True)
        await callback.message.delete()
    else:
        channels_text = "\n".join([f"• @{ch['username']}" for ch in not_subbed])
        await callback.answer(
            "❌ لم يتم الاشتراك في جميع القنوات بعد",
            show_alert=True
        )
        await callback.message.edit_text(
            messages.ERROR_SUBSCRIBE.format(channels=channels_text),
            reply_markup=get_subscribe_keyboard(not_subbed),
            parse_mode="HTML"
        )


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
    
    # Include routers
    dp.include_router(admin_router)
    dp.include_router(broadcast_router)
    dp.include_router(settings_router)
    dp.include_router(channels_router)
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
