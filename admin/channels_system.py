"""
Advanced Channels Management System
"""
import logging
import re
from typing import Optional, Tuple

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

# [تعديل]: تم إزالة استيراد emojis غير المستخدم
from config import build_btn
from core.database import db

logger = logging.getLogger(__name__)

channels_router = Router()


class ChannelsStates(StatesGroup):
    """Channels states"""
    waiting_channel_link = State()
    waiting_custom_message = State()


# [إضافة 1]: دوال مساعدة لإنهاء التكرار العشوائي في عرض أسماء القنوات ومعرفاتها
def get_channel_identifier(ch: dict) -> str:
    """إرجاع معرف القناة للعرض (يوزرنيم أو نص 'قناة خاصة')"""
    username = ch.get('username')
    if username and str(username).lower() != 'none' and not str(username).startswith('channel_'):
        return f"@{username}"
    return "قناة خاصة 🔒"

def get_channel_display_name(ch: dict) -> str:
    """إرجاع اسم القناة المفضل (العنوان، وإن لم يوجد فالمعرف)"""
    title = ch.get('title')
    return title if title else get_channel_identifier(ch)


def get_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Get channels management keyboard"""
    buttons = []
    
    if channels:
        buttons.append([build_btn('VIEW_CHANNELS',  callback_data="channels:list")])
        buttons.append([build_btn('DEL_CHANNEL',  callback_data="channels:delete_menu")])
    
    buttons.extend([
        [build_btn('ADD_CHANNEL',  callback_data="channels:add")],
        [build_btn('CUSTOM_SUB_MSG',  callback_data="channels:custom_message")],
        [build_btn('VALIDATE_CHANNELS',  callback_data="channels:validate")],
        [build_btn('BACK',  callback_data="admin_menu:back")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def check_channel_validity(bot: Bot, ch: dict) -> Tuple[bool, str, str]:
    """
    Check if a channel is valid.
    Returns: (is_valid, status_emoji, reason)
    """
    chat_identifier = ch.get('channel_id')
    
    if not chat_identifier:
        if ch.get('username') and str(ch['username']).lower() != 'none':
            chat_identifier = f"@{ch['username']}"
            
    if not chat_identifier:
        return False, "❌", "معرف القناة مفقود"
        
    try:
        chat = await bot.get_chat(chat_identifier)
        try:
            bot_member = await bot.get_chat_member(chat.id, bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                return False, "⚠️", "البوت ليس أدمن"
            return True, "✅", "صالحة"
        except TelegramAPIError as e:
            logger.error(f"Error checking admin status for {chat_identifier}: {e}")
            return False, "⚠️", "لا يمكن التحقق من الصلاحيات"
    except TelegramAPIError as e:
        logger.error(f"Error getting chat {chat_identifier}: {e}")
        return False, "❌", "القناة غير موجودة أو البوت محظور"
    except Exception as e:
        logger.error(f"Unexpected error checking admin status: {e}")
        return False, "⚠️", "خطأ غير متوقع"


@channels_router.callback_query(F.data == "channels:add")
async def add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt to add channel"""
    await callback.answer()
    text = """
➕ <b>إضافة قناة إجبارية</b>

يمكنك إضافة القناة بأي من الطرق التالية:

1️⃣ <b>إرسال رابط القناة:</b>
   • https://t.me/channel_name
   • @channel_name
   • t.me/channel_name
   • https://t.me/c/123456789/1 (للقنوات الخاصة)

2️⃣ <b>إعادة توجيه رسالة من القناة</b>

3️⃣ <b>إرسال معرف القناة (Chat ID)</b>

<b>ملاحظة:</b> يجب أن يكون البوت مضافاً كمسؤول في القناة
"""
    # [إضافة 2]: زر رجوع لكي لا يظل الأدمن عالقاً في الـ FSM State
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [build_btn('BACK', callback_data="admin_menu:channels")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ChannelsStates.waiting_channel_link)


@channels_router.message(ChannelsStates.waiting_channel_link)
async def process_add_channel(message: Message, state: FSMContext, bot: Bot):
    """Process adding channel"""
    channel_id = None
    channel_username = None
    channel_title = None
    is_private = False
    
    try:
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
            channel_username = message.forward_from_chat.username or f"channel_{channel_id}"
            channel_title = message.forward_from_chat.title
            is_private = message.forward_from_chat.type == 'channel' and not message.forward_from_chat.username
        
        elif message.text:
            text = message.text.strip()
            
            # [تعديل 1]: معالجة روابط الانضمام الخاصة لمنع الكود من اعتبارها كـ يوزرنيم
            if '/+' in text or text.startswith('+') or 'joinchat' in text:
                await message.answer("❌ روابط الانضمام الخاصة غير مدعومة مباشرة.\nيرجى إعادة توجيه رسالة من القناة، أو إرسال الـ (Chat ID)، أو إضافة رابط مباشر.")
                return 

            if 't.me/c/' in text:
                try:
                    parts = text.split('t.me/c/')[-1].split('/')
                    # [تعديل 2]: تأمين المعرف وإضافة -100 بشكل سليم
                    chat_id_str = parts[0]
                    channel_id = int(chat_id_str) if chat_id_str.startswith("-100") else int(f"-100{chat_id_str}")
                    is_private = True
                    channel_username = f"channel_{channel_id}"
                except ValueError:
                    await message.answer("❌ صيغة الرابط الخاص غير صحيحة")
                    return
            elif 't.me/' in text:
                channel_username = text.split('t.me/')[-1].split('/')[0].replace('@', '')
            elif text.startswith('@'):
                channel_username = text[1:]
            elif text.lstrip('-').isdigit():
                channel_id = int(text)
                # [تعديل 3]: تصحيح تلقائي إذا أدخل المستخدم ID قناة بدون بادئة -100
                if channel_id > 0:
                    channel_id = int(f"-100{channel_id}")
            else:
                channel_username = text.replace('@', '')
            
            if channel_username and not is_private:
                try:
                    chat = await bot.get_chat(f"@{channel_username}")
                    channel_id = chat.id
                    channel_title = chat.title
                    is_private = chat.type == 'channel' and not chat.username
                except TelegramAPIError as e:
                    logger.warning(f"Cannot access channel by username: {e}")
                    await message.answer(f"❌ لا يمكن الوصول للقناة @{channel_username}\nقد تكون قناة خاصة أو البوت ليس عضواً فيها.")
                    return
            elif channel_id:
                try:
                    chat = await bot.get_chat(channel_id)
                    channel_username = chat.username or f"channel_{channel_id}"
                    channel_title = chat.title
                    is_private = chat.type == 'channel' and not chat.username
                except TelegramAPIError as e:
                    logger.warning(f"Cannot access channel by ID: {e}")
                    await message.answer(f"❌ لا يمكن الوصول للقناة برقم المعرف {channel_id}")
                    return
        
        else:
            await message.answer("❌ صيغة غير صحيحة! أرسل رابط أو يوزرنيم أو أعد توجيه رسالة")
            return
        
        if not channel_id:
            await message.answer("❌ لم يتم الحصول على معرف القناة")
            return
        
        try:
            member = await bot.get_chat_member(channel_id, bot.id)
            if member.status not in ['administrator', 'creator']:
                await message.answer(
                    "❌ <b>البوت ليس مسؤولاً في هذه القناة!</b>\n\n"
                    "يجب أن يكون البوت مسؤولاً (Admin) في القناة...\nالرجاء المحاولة لاحقاً",
                    parse_mode="HTML"
                )
                return
        except TelegramAPIError as e:
            logger.error(f"Error checking bot admin status: {e}")
            await message.answer("❌ خطأ في التحقق من صلاحيات البوت: تأكد من إضافة البوت كأدمن")
            return
        
        invite_link_url = None
        if is_private or not channel_username or str(channel_username).startswith("channel_"):
            try:
                invite_link = await bot.create_chat_invite_link(channel_id)
                invite_link_url = invite_link.invite_link
            except TelegramAPIError as e:
                logger.warning(f"Could not create invite link: {e}")
                await message.answer("⚠️ تنبيه: لم أتمكن من إنشاء رابط دعوة للقناة. يرجى التأكد من صلاحيات البوت.")
        
        # [تعديل 4]: إضافة Error Handling لتسجيل قاعدة البيانات
        try:
            success = await db.add_required_channel(
                channel_username, 
                channel_title, 
                message.from_user.id,
                channel_id=channel_id,
                is_private=is_private,
                invite_link=invite_link_url
            )
        except Exception as db_err:
            logger.error(f"DB Error adding channel: {db_err}")
            success = False
            
        if not success:
            await message.answer("❌ فشل حفظ القناة في قاعدة البيانات")
            return
        
        channel_link = ""
        if invite_link_url:
            channel_link = f"\n🔗 <a href='{invite_link_url}'>رابط الدعوة</a>"
        elif channel_username and not str(channel_username).startswith("channel_"):
            channel_link = f"\n🔗 @{channel_username}"
        
        text = f"""
✅ <b>تمت الإضافة بنجاح</b>

📺 القناة: {channel_title or "بدون اسم"}
🔒 النوع: {'قناة خاصة 🔐' if is_private else 'قناة عامة 🌐'}{channel_link}
"""
        await message.answer(text, parse_mode="HTML")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        await message.answer("❌ خطأ غير متوقع: يرجى المحاولة لاحقاً")
        await state.clear() # [مهم]: منع تعليق الحالة في حال حدث خطأ جسيم


@channels_router.callback_query(F.data == "channels:custom_message")
async def custom_message_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for custom subscription message"""
    await callback.answer()
    text = """
📝 <b>تخصيص رسالة الاشتراك</b>

أرسل الرسالة المخصصة التي تريد عرضها للمستخدمين عند طلب الاشتراك.

<b>يمكنك استخدام:</b>
  • HTML للتنسيق
  • {channels} - سيتم استبدالها بقائمة القنوات
  • {user} - اسم المستخدم
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[build_btn('BACK', callback_data="admin_menu:channels")]])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ChannelsStates.waiting_custom_message)


@channels_router.message(ChannelsStates.waiting_custom_message)
async def process_custom_message(message: Message, state: FSMContext):
    """Process custom subscription message"""
    custom_message = message.text or message.caption
    
    if not custom_message:
        # [تعديل]: السماح بالإلغاء وعدم تجميد الحالة إذا أرسل ملصق
        await message.answer("❌ يجب إرسال نص! الرجاء المحاولة مرة أخرى أو الإلغاء.")
        return 
    
    # [تعديل]: حماية العملية عبر try...except
    try:
        await db.set_setting('subscription_message', custom_message)
    except Exception as e:
        logger.error(f"Error setting custom message: {e}")
        await message.answer("❌ فشل في الحفظ داخل قاعدة البيانات.")
        return
        
    text = f"""
✅ <b>تم حفظ الرسالة المخصصة</b>

<b>معاينة:</b>
{custom_message.replace('{user}', message.from_user.first_name).replace('{channels}', '• @example_channel')}
"""
    await message.answer(text, parse_mode="HTML")
    await state.clear()


@channels_router.callback_query(F.data == "channels:list")
async def list_channels(callback: CallbackQuery, bot: Bot):
    """List all required channels with status"""
    await callback.answer()
    channels = await db.get_required_channels()
    
    if not channels:
        await callback.answer("لا توجد قنوات مضافة", show_alert=True)
        return
    
    text = "<b>📋 القنوات الإجبارية:</b>\n\n"
    
    for i, ch in enumerate(channels, 1):
        is_valid, status, status_text = await check_channel_validity(bot, ch)
        # [استخدام الدالة المساعدة]
        display_link = get_channel_identifier(ch)
        
        text += f"{i}. {status} <b>{ch.get('title') or 'بدون اسم'}</b>\n"
        text += f"   🔗 {display_link}\n"
        text += f"   📊 الحالة: {status_text}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [build_btn('DEL_CHANNEL',  callback_data="channels:delete_menu")],
        [build_btn('BACK',  callback_data="admin_menu:channels")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@channels_router.callback_query(F.data == "channels:delete_menu")
async def delete_channel_menu(callback: CallbackQuery):
    """Show delete channel menu"""
    await callback.answer()
    channels = await db.get_required_channels()
    
    if not channels:
        await callback.answer("لا توجد قنوات لحذفها", show_alert=True)
        return
    
    text = "<b>🗑️ اختر القناة للحذف:</b>\n\n"
    buttons = []
    
    for i, ch in enumerate(channels, 1):
        display_name = get_channel_display_name(ch)
        text += f"{i}. {display_name}\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ {display_name}",
                callback_data=f"channels:delete:{ch['channel_id']}"
            )
        ])
    
    buttons.append([build_btn('BACK',  callback_data="admin_menu:channels")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@channels_router.callback_query(F.data.startswith("channels:delete:"))
async def delete_channel(callback: CallbackQuery):
    """Delete a channel by channel_id"""
    try:
        # [تعديل]: حماية من خطأ IndexError
        parts = callback.data.split(":")
        if len(parts) < 3:
            raise ValueError("معرف القناة مفقود في البيانات")
        channel_id = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ بيانات الزر غير صالحة", show_alert=True)
        return
    
    try:
        success = await db.remove_required_channel(channel_id)
        
        if success:
            channels = await db.get_required_channels()
            
            if not channels:
                text = "<b>📺 إدارة القنوات الإجبارية</b>\n\n<i>لا توجد قنوات مضافة</i>"
                keyboard = get_channels_keyboard([])
            else:
                text = "<b>🗑️ اختر القناة للحذف:</b>\n\n✅ تم الحذف بنجاح\n\n<b>القنوات المتبقية:</b>\n"
                buttons = []
                for i, ch in enumerate(channels, 1):
                    display_name = get_channel_display_name(ch)
                    text += f"{i}. {display_name}\n"
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"❌ {display_name}",
                            callback_data=f"channels:delete:{ch['channel_id']}"
                        )
                    ])
                buttons.append([build_btn('BACK',  callback_data="admin_menu:channels")])
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            try:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except TelegramBadRequest as e:
                # [تعديل]: تجاهل خطأ عدم التغيير بدل حذف وإعادة إرسال الرسالة
                if "message is not modified" not in str(e).lower():
                    logger.warning(f"Edit text failed: {e}")
            
            await callback.answer("✅ تم حذف القناة بنجاح", show_alert=True if not channels else False)
        else:
            await callback.answer("❌ فشل حذف القناة من قاعدة البيانات", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        await callback.answer("❌ حدث خطأ غير متوقع", show_alert=True)


@channels_router.callback_query(F.data == "channels:validate")
async def validate_channels(callback: CallbackQuery, bot: Bot):
    """Validate all channels and remove invalid ones"""
    await callback.answer()
    channels = await db.get_required_channels()
    
    if not channels:
        await callback.answer("لا توجد قنوات للتحقق", show_alert=True)
        return
    
    await callback.message.edit_text("🔄 <b>جاري التحقق من صلاحية القنوات...</b>", parse_mode="HTML")
    
    valid_count = 0
    invalid_channels = []
    
    for ch in channels:
        is_valid, status, reason = await check_channel_validity(bot, ch)
        if is_valid:
            valid_count += 1
        else:
            invalid_channels.append({'channel': ch, 'reason': reason})
    
    text = f"""<b>📊 نتيجة التحقق:</b>

✅ <b>صالحة:</b> {valid_count}
❌ <b>غير صالحة:</b> {len(invalid_channels)}
"""
    
    if invalid_channels:
        text += "\n<b>القنوات غير الصالحة:</b>\n"
        for item in invalid_channels:
            ch = item['channel']
            display_link = get_channel_identifier(ch)
            text += f"• {display_link} - {item['reason']}\n"
        
        text += "\n<i>هل تريد حذف القنوات غير الصالحة تلقائياً؟</i>"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [build_btn('DEL_INVALID',  callback_data="channels:remove_invalid")],
            [build_btn('BACK',  callback_data="admin_menu:channels")]
        ])
    else:
        text += "\n✨ <i>جميع القنوات صالحة!</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [build_btn('BACK',  callback_data="admin_menu:channels")]
        ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@channels_router.callback_query(F.data == "channels:remove_invalid")
async def remove_invalid_channels(callback: CallbackQuery, bot: Bot):
    """Remove all invalid channels"""
    await callback.answer()
    channels = await db.get_required_channels()
    removed_count = 0
    
    for ch in channels:
        is_valid, _, _ = await check_channel_validity(bot, ch)
        if not is_valid and ch.get('channel_id'):
            try:
                success = await db.remove_required_channel(ch['channel_id'])
                if success:
                    removed_count += 1
            except Exception as e:
                logger.error(f"Error removing invalid channel {ch.get('channel_id')}: {e}")
    
    await callback.answer(f"✅ تم حذف {removed_count} قناة غير صالحة", show_alert=True)
    
    channels = await db.get_required_channels()
    text = "<b>📺 إدارة القنوات الإجبارية</b>\n\n"
    if channels:
        text += f"<b>عدد القنوات:</b> {len(channels)}\n\n"
        for ch in channels:
            display_name = get_channel_display_name(ch)
            text += f"• {display_name}\n"
    else:
        text += "<i>لا توجد قنوات مضافة</i>"
    
    try:
        await callback.message.edit_text(text, reply_markup=get_channels_keyboard(channels), parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            pass
