"""
Advanced Settings System for Admin Panel
"""
import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from config import config

logger = logging.getLogger(__name__)

settings_router = Router()


class SettingsStates(StatesGroup):
    """Settings states"""
    waiting_notification_chat = State()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Get settings menu keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔔 إعدادات الإشعارات", callback_data="settings:notifications")],
        [InlineKeyboardButton(text="👑 إدارة المسؤولين", callback_data="settings:admins")],
        [InlineKeyboardButton(text="📺 القنوات الإجبارية", callback_data="settings:channels")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:back")]
    ])


def get_notifications_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Get notifications settings keyboard"""
    notify_new = settings.get('notify_new_users', False)
    notify_downloads = settings.get('notify_downloads', False)
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅' if notify_new else '❌'} إشعار المستخدمين الجدد",
            callback_data="settings:toggle_new_users"
        )],
        [InlineKeyboardButton(
            text=f"{'✅' if notify_downloads else '❌'} إشعار التحميلات",
            callback_data="settings:toggle_downloads"
        )],
        [InlineKeyboardButton(
            text="📍 تحديد قناة/جروب للإشعارات",
            callback_data="settings:set_notification_chat"
        )],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="settings:back")]
    ])


@settings_router.callback_query(F.data == "settings:notifications")
async def notifications_settings(callback: CallbackQuery):
    """Show notifications settings"""
    settings = await db.get_bot_settings()
    
    notify_new = settings.get('notify_new_users', False)
    notify_downloads = settings.get('notify_downloads', False)
    notification_chat = settings.get('notification_chat_id', config.PRIMARY_OWNER_ID)
    
    text = f"""
🔔 <b>إعدادات الإشعارات</b>

📊 <b>الحالة الحالية:</b>
  • إشعار المستخدمين الجدد: {'✅ مفعّل' if notify_new else '❌ معطّل'}
  • إشعار التحميلات: {'✅ مفعّل' if notify_downloads else '❌ معطّل'}
  • مكان الإشعارات: <code>{notification_chat}</code>

<b>اختر الإعداد المطلوب:</b>
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_notifications_keyboard(settings),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data == "settings:toggle_new_users")
async def toggle_new_users_notification(callback: CallbackQuery):
    """Toggle new users notification"""
    settings = await db.get_bot_settings()
    current = settings.get('notify_new_users', False)
    
    await db.update_bot_settings({'notify_new_users': not current})
    
    await callback.answer(
        f"✅ إشعار المستخدمين الجدد {'معطّل' if current else 'مفعّل'}",
        show_alert=True
    )
    
    # Refresh menu
    await notifications_settings(callback)


@settings_router.callback_query(F.data == "settings:toggle_downloads")
async def toggle_downloads_notification(callback: CallbackQuery):
    """Toggle downloads notification"""
    settings = await db.get_bot_settings()
    current = settings.get('notify_downloads', False)
    
    await db.update_bot_settings({'notify_downloads': not current})
    
    await callback.answer(
        f"✅ إشعار التحميلات {'معطّل' if current else 'مفعّل'}",
        show_alert=True
    )
    
    # Refresh menu
    await notifications_settings(callback)


@settings_router.callback_query(F.data == "settings:set_notification_chat")
async def set_notification_chat_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for notification chat ID"""
    text = """
📍 <b>تحديد قناة/جروب للإشعارات</b>

أرسل أحد التالي:
  • معرف القناة/الجروب (Chat ID)
  • يوزرنيم القناة (@channel_name)
  • قم بإعادة توجيه رسالة من القناة/الجروب

<b>ملاحظة:</b> يجب أن يكون البوت مضافاً كمسؤول في القناة/الجروب
"""
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(SettingsStates.waiting_notification_chat)


@settings_router.message(SettingsStates.waiting_notification_chat)
async def process_notification_chat(message: Message, state: FSMContext, bot: Bot):
    """Process notification chat setting"""
    chat_id = None
    
    # Check if forwarded message
    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
    # Check if username
    elif message.text and message.text.startswith('@'):
        try:
            chat = await bot.get_chat(message.text)
            chat_id = chat.id
        except Exception as e:
            await message.answer(f"❌ خطأ: {str(e)[:100]}")
            return
    # Check if numeric ID
    elif message.text and message.text.lstrip('-').isdigit():
        chat_id = int(message.text)
    else:
        await message.answer("❌ صيغة غير صحيحة! أرسل معرف أو يوزرنيم أو أعد توجيه رسالة")
        return
    
    # Verify bot is admin
    try:
        chat = await bot.get_chat(chat_id)
        member = await bot.get_chat_member(chat_id, bot.id)
        
        if member.status not in ['administrator', 'creator']:
            await message.answer("❌ البوت ليس مسؤولاً في هذه القناة/الجروب!")
            return
        
        # Save setting
        await db.update_bot_settings({'notification_chat_id': chat_id})
        
        text = f"""
✅ <b>تم التحديث بنجاح</b>

📍 القناة/الجروب: {chat.title or chat.username}
🆔 المعرف: <code>{chat_id}</code>

سيتم إرسال جميع الإشعارات إلى هذا المكان
"""
        
        await message.answer(text, parse_mode="HTML")
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ خطأ في التحقق: {str(e)[:100]}")


@settings_router.callback_query(F.data == "settings:back")
async def back_to_settings(callback: CallbackQuery):
    """Back to settings menu"""
    text = """
⚙️ <b>الإعدادات</b>

اختر القسم المطلوب:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )
