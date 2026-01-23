"""
Advanced Channels Management System
"""
import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db

logger = logging.getLogger(__name__)

channels_router = Router()


class ChannelsStates(StatesGroup):
    """Channels states"""
    waiting_channel_link = State()
    waiting_custom_message = State()


def get_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Get channels management keyboard"""
    buttons = []
    
    if channels:
        buttons.append([InlineKeyboardButton(text="📋 عرض القنوات", callback_data="channels:list")])
    
    buttons.extend([
        [InlineKeyboardButton(text="➕ إضافة قناة", callback_data="channels:add")],
        [InlineKeyboardButton(text="📝 تخصيص رسالة الاشتراك", callback_data="channels:custom_message")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:back")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@channels_router.callback_query(F.data == "channels:add")
async def add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt to add channel"""
    text = """
➕ <b>إضافة قناة إجبارية</b>

يمكنك إضافة القناة بأي من الطرق التالية:

1️⃣ <b>إرسال رابط القناة:</b>
   • https://t.me/channel_name
   • @channel_name
   • t.me/channel_name

2️⃣ <b>إعادة توجيه رسالة من القناة</b>

3️⃣ <b>إرسال معرف القناة (Chat ID)</b>

<b>ملاحظة:</b> يجب أن يكون البوت مضافاً كمسؤول في القناة
"""
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(ChannelsStates.waiting_channel_link)


@channels_router.message(ChannelsStates.waiting_channel_link)
async def process_add_channel(message: Message, state: FSMContext, bot: Bot):
    """Process adding channel"""
    channel_id = None
    channel_username = None
    
    try:
        # Check if forwarded message
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
            channel_username = message.forward_from_chat.username
            channel_title = message.forward_from_chat.title
        
        # Check if text (link or username)
        elif message.text:
            text = message.text.strip()
            
            # Extract username from various formats
            if 'https://t.me/' in text:
                channel_username = text.split('https://t.me/')[-1].split('/')[0].replace('@', '')
            elif 't.me/' in text:
                channel_username = text.split('t.me/')[-1].split('/')[0].replace('@', '')
            elif text.startswith('@'):
                channel_username = text[1:]
            elif text.lstrip('-').isdigit():
                channel_id = int(text)
            else:
                channel_username = text.replace('@', '')
            
            # Get chat info
            if channel_username:
                chat = await bot.get_chat(f"@{channel_username}")
                channel_id = chat.id
                channel_title = chat.title
            else:
                chat = await bot.get_chat(channel_id)
                channel_username = chat.username or str(channel_id)
                channel_title = chat.title
        
        else:
            await message.answer("❌ صيغة غير صحيحة! أرسل رابط أو يوزرنيم أو أعد توجيه رسالة")
            return
        
        # Verify bot is admin
        member = await bot.get_chat_member(channel_id, bot.id)
        if member.status not in ['administrator', 'creator']:
            await message.answer("❌ البوت ليس مسؤولاً في هذه القناة!")
            return
        
        # Add to database
        await db.add_required_channel(channel_username, channel_title, message.from_user.id)
        
        text = f"""
✅ <b>تمت الإضافة بنجاح</b>

📺 القناة: {channel_title}
🔗 الرابط: @{channel_username}
🆔 المعرف: <code>{channel_id}</code>

الآن سيطلب من المستخدمين الاشتراك في هذه القناة قبل استخدام البوت
"""
        
        await message.answer(text, parse_mode="HTML")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        await message.answer(f"❌ خطأ: {str(e)[:150]}")


@channels_router.callback_query(F.data == "channels:custom_message")
async def custom_message_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for custom subscription message"""
    text = """
📝 <b>تخصيص رسالة الاشتراك</b>

أرسل الرسالة المخصصة التي تريد عرضها للمستخدمين عند طلب الاشتراك.

<b>يمكنك استخدام:</b>
  • HTML للتنسيق
  • {channels} - سيتم استبدالها بقائمة القنوات
  • {user} - اسم المستخدم

<b>مثال:</b>
<code>مرحباً {user}!
للاستخدام، اشترك في القنوات التالية:
{channels}</code>
"""
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(ChannelsStates.waiting_custom_message)


@channels_router.message(ChannelsStates.waiting_custom_message)
async def process_custom_message(message: Message, state: FSMContext):
    """Process custom subscription message"""
    custom_message = message.text or message.caption
    
    if not custom_message:
        await message.answer("❌ يجب إرسال نص!")
        return
    
    # Save to database
    await db.set_setting('subscription_message', custom_message)
    
    text = f"""
✅ <b>تم حفظ الرسالة المخصصة</b>

<b>معاينة:</b>
{custom_message.replace('{user}', message.from_user.first_name).replace('{channels}', '• @example_channel')}
"""
    
    await message.answer(text, parse_mode="HTML")
    await state.clear()


@channels_router.callback_query(F.data == "channels:list")
async def list_channels(callback: CallbackQuery):
    """List all required channels"""
    channels = await db.get_required_channels()
    
    if not channels:
        await callback.answer("لا توجد قنوات مضافة", show_alert=True)
        return
    
    text = "<b>📋 القنوات الإجبارية:</b>\n\n"
    
    for i, ch in enumerate(channels, 1):
        text += f"{i}. {ch['title']}\n   🔗 @{ch['username']}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:channels")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
