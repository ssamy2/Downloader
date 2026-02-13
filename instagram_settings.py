"""
Instagram Download Settings Manager
Handles cookie upload, download priority, and testing
"""
import os
import time
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logger = logging.getLogger(__name__)

router = Router()

@dataclass
class InstagramSettings:
    """Instagram download settings"""
    priority: List[str] = None
    
    def __post_init__(self):
        if self.priority is None:
            self.priority = ["yt_dlp", "cobalt"]

class InstagramStates(StatesGroup):
    """States for Instagram settings"""
    waiting_priority = State()
    waiting_test_url = State()

# Global settings instance
settings = InstagramSettings()

def get_settings_menu() -> InlineKeyboardMarkup:
    """Generate Instagram settings menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" تحديد أولوية التحميل", callback_data="instagram:set_priority")],
        [InlineKeyboardButton(text="⏱️ اختبار التحميل", callback_data="instagram:test_download")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:settings")]
    ])


@router.callback_query(F.data == "instagram:set_priority")
async def set_priority_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt to set download priority"""
    text = f"""
🔢 <b>أولوية التحميل الحالية:</b>
1. {settings.priority[0]}
2. {settings.priority[1]}

اختر الترتيب الجديد:
"""
    
    buttons = [
        [InlineKeyboardButton(text="yt_dlp > Cobalt API", callback_data="priority:yt_dlp,cobalt")],
        [InlineKeyboardButton(text="Cobalt API > yt_dlp", callback_data="priority:cobalt,yt_dlp")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:settings")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await state.set_state(InstagramStates.waiting_priority)

@router.callback_query(F.data.startswith("priority:"))
async def process_priority(callback: CallbackQuery, state: FSMContext):
    """Process priority selection"""
    priority = callback.data.split(":")[1].split(",")
    settings.priority = priority
    
    await callback.answer(f"✅ تم تحديد الأولوية: {' > '.join(priority)}")
    await state.clear()
    await callback.message.delete()

@router.callback_query(F.data == "instagram:test_download")
async def test_download_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for test URL"""
    await callback.message.edit_text(
        "🔗 يرجى إرسال رابط Instagram للاختبار",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin_menu:settings")]
        ])
    )
    await state.set_state(InstagramStates.waiting_test_url)

@router.message(InstagramStates.waiting_test_url)
async def process_test_download(message: Message, state: FSMContext, bot: Bot):
    """Process test download with comprehensive error handling"""
    try:
        url = message.text
        if not url or "instagram.com" not in url:
            await message.reply("❌ يرجى إرسال رابط Instagram صالح")
            return
            
        # Start test
        start_time = time.time()
        status_msg = await message.reply("⏳ جاري اختبار التحميل...")
        
        # Call actual download function with timing
        from downloader import MediaDownloader
        
        downloader = MediaDownloader()
        start_download = time.time()
        
        try:
            result = await downloader.download(
                url,
                quality="best",
                download_audio=False
            )
            
            if not result.success:
                raise Exception(result.error or "فشل التحميل")
                
            download_time = time.time() - start_download
            file_size = result.file_size / (1024 * 1024)  # Convert to MB
            
            # Clean up downloaded file
            if os.path.exists(result.file_path):
                os.remove(result.file_path)
            
            # Connection time (time until first response)
            connection_time = result.connect_time - start_download if hasattr(result, 'connect_time') else 0
            
            await status_msg.edit_text(
                f"""
✅ اختبار التحميل بنجاح

📊 النتائج:
- الرابط: {url}
- وقت الاتصال: {connection_time:.2f} ثانية
- وقت التحميل: {download_time:.2f} ثانية
- الحجم: {file_size:.2f} MB
- الطريقة المستخدمة: {result.method}
"""
            )
            
        except Exception as e:
            error_time = time.time() - start_time
            await status_msg.edit_text(
                f"""
❌ فشل اختبار التحميل

📊 النتائج:
- الرابط: {url}
- وقت الفشل: {error_time:.2f} ثانية
- الخطأ: {str(e)}
"""
            )
            logger.error(f"Instagram download test failed: {e}", exc_info=True)
            
    except Exception as e:
        await message.reply(f"❌ خطأ في نظام الاختبار: {str(e)}")
        logger.error(f"Test system error: {e}", exc_info=True)
    finally:
        await state.clear()
