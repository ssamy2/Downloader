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
        buttons.append([InlineKeyboardButton(text="🗑️ حذف قناة", callback_data="channels:delete_menu")])
    
    buttons.extend([
        [InlineKeyboardButton(text="➕ إضافة قناة", callback_data="channels:add")],
        [InlineKeyboardButton(text="📝 تخصيص رسالة الاشتراك", callback_data="channels:custom_message")],
        [InlineKeyboardButton(text="🔄 التحقق من صلاحية القنوات", callback_data="channels:validate")],
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
    is_private = False
    
    try:
        # Check if forwarded message
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
            channel_username = message.forward_from_chat.username or f"channel_{channel_id}"
            channel_title = message.forward_from_chat.title
            is_private = message.forward_from_chat.type == 'private' or not message.forward_from_chat.username
        
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
                try:
                    chat = await bot.get_chat(f"@{channel_username}")
                    channel_id = chat.id
                    channel_title = chat.title
                    is_private = chat.type == 'private'
                except Exception as e:
                    logger.warning(f"Cannot access channel by username: {e}")
                    await message.answer(f"❌ لا يمكن الوصول للقناة @{channel_username}\nقد تكون قناة خاصة أو البوت ليس عضواً فيها")
                    return
            else:
                try:
                    chat = await bot.get_chat(channel_id)
                    channel_username = chat.username or f"channel_{channel_id}"
                    channel_title = chat.title
                    is_private = chat.type == 'private' or not chat.username
                except Exception as e:
                    logger.warning(f"Cannot access channel by ID: {e}")
                    await message.answer(f"❌ لا يمكن الوصول للقناة برقم المعرف {channel_id}")
                    return
        
        else:
            await message.answer("❌ صيغة غير صحيحة! أرسل رابط أو يوزرنيم أو أعد توجيه رسالة")
            return
        
        if not channel_id:
            await message.answer("❌ لم يتم الحصول على معرف القناة")
            return
        
        # Verify bot is admin
        try:
            member = await bot.get_chat_member(channel_id, bot.id)
            if member.status not in ['administrator', 'creator']:
                await message.answer(
                    "❌ <b>البوت ليس مسؤولاً في هذه القناة!</b>\n\n"
                    "يجب أن يكون البوت مسؤولاً (Admin) في القناة لكي يتمكن من:\n"
                    "• التحقق من اشتراك المستخدمين\n"
                    "• إنشاء روابط دعوة للقنوات الخاصة\n\n"
                    "الرجاء إضافة البوت كمسؤول في القناة ثم حاول مرة أخرى",
                    parse_mode="HTML"
                )
                return
        except Exception as e:
            logger.error(f"Error checking bot admin status: {e}")
            await message.answer(f"❌ خطأ في التحقق من صلاحيات البوت: {str(e)[:100]}")
            return
        
        # Generate invite link for private channels BEFORE saving to database
        invite_link_url = None
        if is_private or not channel_username:
            try:
                invite_link = await bot.create_chat_invite_link(channel_id)
                invite_link_url = invite_link.invite_link
                logger.info(f"Created invite link for channel {channel_id}: {invite_link_url}")
            except Exception as e:
                logger.warning(f"Could not create invite link: {e}")
        
        # Add to database with channel_id, is_private flag, and invite_link
        success = await db.add_required_channel(
            channel_username, 
            channel_title, 
            message.from_user.id,
            channel_id=channel_id,
            is_private=is_private,
            invite_link=invite_link_url
        )
        
        if not success:
            await message.answer("❌ فشل حفظ القناة في قاعدة البيانات")
            return
        
        # Build success message
        channel_link = ""
        if invite_link_url:
            channel_link = f"\n🔗 <a href='{invite_link_url}'>رابط الدعوة</a>"
        elif channel_username:
            channel_link = f"\n🔗 @{channel_username}"
        
        text = f"""
✅ <b>تمت الإضافة بنجاح</b>

📺 القناة: {channel_title}
🔒 النوع: {'قناة خاصة 🔐' if is_private else 'قناة عامة 🌐'}{channel_link}

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
async def list_channels(callback: CallbackQuery, bot: Bot):
    """List all required channels with status"""
    channels = await db.get_required_channels()
    
    if not channels:
        await callback.answer("لا توجد قنوات مضافة", show_alert=True)
        return
    
    text = "<b>📋 القنوات الإجبارية:</b>\n\n"
    
    for i, ch in enumerate(channels, 1):
        # التحقق من حالة القناة
        status = "✅"
        status_text = "صالحة"
        
        if not ch.get('username') or ch['username'] == 'None':
            status = "❌"
            status_text = "username غير صالح"
        else:
            try:
                chat = await bot.get_chat(f"@{ch['username']}")
                try:
                    bot_member = await bot.get_chat_member(chat.id, bot.id)
                    if bot_member.status not in ['administrator', 'creator']:
                        status = "⚠️"
                        status_text = "البوت ليس أدمن"
                except:
                    status = "⚠️"
                    status_text = "لا يمكن التحقق"
            except:
                status = "❌"
                status_text = "القناة غير موجودة"
        
        text += f"{i}. {status} <b>{ch['title'] or 'بدون اسم'}</b>\n"
        text += f"   🔗 @{ch['username']}\n"
        text += f"   📊 الحالة: {status_text}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ حذف قناة", callback_data="channels:delete_menu")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:channels")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@channels_router.callback_query(F.data == "channels:delete_menu")
async def delete_channel_menu(callback: CallbackQuery):
    """Show delete channel menu"""
    channels = await db.get_required_channels()
    
    if not channels:
        await callback.answer("لا توجد قنوات لحذفها", show_alert=True)
        return
    
    text = "<b>🗑️ اختر القناة للحذف:</b>\n\n"
    
    buttons = []
    for i, ch in enumerate(channels, 1):
        text += f"{i}. {ch['title'] or ch.get('username') or 'قناة خاصة'}\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ {ch['title'] or ch.get('username') or 'قناة خاصة'}",
                callback_data=f"channels:delete:{ch['channel_id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:channels")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@channels_router.callback_query(F.data.startswith("channels:delete:"))
async def delete_channel(callback: CallbackQuery):
    """Delete a channel by channel_id"""
    try:
        channel_id = int(callback.data.split(":")[2])
    except ValueError:
        await callback.answer("❌ معرف القناة غير صالح", show_alert=True)
        return
    
    try:
        # حذف القناة من قاعدة البيانات باستخدام channel_id
        success = await db.remove_required_channel(channel_id)
        
        if success:
            # إعادة عرض القائمة بعد الحذف
            channels = await db.get_required_channels()
            
            if not channels:
                # لا توجد قنوات متبقية
                text = "<b>📺 إدارة القنوات الإجبارية</b>\n\n<i>لا توجد قنوات مضافة</i>"
                keyboard = get_channels_keyboard([])
                try:
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
                except:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                await callback.answer("✅ تم حذف القناة بنجاح", show_alert=True)
            else:
                # ما زالت هناك قنوات - أعد عرض قائمة الحذف
                text = "<b>🗑️ اختر القناة للحذف:</b>\n\n✅ تم الحذف بنجاح\n\n<b>القنوات المتبقية:</b>\n"
                buttons = []
                for i, ch in enumerate(channels, 1):
                    text += f"{i}. {ch['title'] or ch.get('username') or 'قناة خاصة'}\n"
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"❌ {ch['title'] or ch.get('username') or 'قناة خاصة'}",
                            callback_data=f"channels:delete:{ch['channel_id']}"
                        )
                    ])
                
                buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:channels")])
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                
                try:
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
                except:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                
                await callback.answer("✅ تم حذف القناة بنجاح", show_alert=False)
        else:
            await callback.answer("❌ فشل حذف القناة من قاعدة البيانات", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        await callback.answer(f"❌ خطأ: {str(e)[:100]}", show_alert=True)


@channels_router.callback_query(F.data == "channels:validate")
async def validate_channels(callback: CallbackQuery, bot: Bot):
    """Validate all channels and remove invalid ones"""
    channels = await db.get_required_channels()
    
    if not channels:
        await callback.answer("لا توجد قنوات للتحقق", show_alert=True)
        return
    
    await callback.message.edit_text("🔄 <b>جاري التحقق من صلاحية القنوات...</b>", parse_mode="HTML")
    
    valid_count = 0
    invalid_channels = []
    
    for ch in channels:
        is_valid = True
        reason = ""
        
        if not ch.get('username') or ch['username'] == 'None':
            is_valid = False
            reason = "username غير صالح"
        else:
            try:
                chat = await bot.get_chat(f"@{ch['username']}")
                try:
                    bot_member = await bot.get_chat_member(chat.id, bot.id)
                    if bot_member.status not in ['administrator', 'creator']:
                        is_valid = False
                        reason = "البوت ليس أدمن"
                except:
                    is_valid = False
                    reason = "لا يمكن التحقق من صلاحية البوت"
            except:
                is_valid = False
                reason = "القناة غير موجودة أو خاصة"
        
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
            text += f"• @{ch['username']} - {item['reason']}\n"
        text += "\n<i>هل تريد حذف القنوات غير الصالحة تلقائياً؟</i>"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ حذف غير الصالحة", callback_data="channels:remove_invalid")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:channels")]
        ])
    else:
        text += "\n✨ <i>جميع القنوات صالحة!</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:channels")]
        ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@channels_router.callback_query(F.data == "channels:remove_invalid")
async def remove_invalid_channels(callback: CallbackQuery, bot: Bot):
    """Remove all invalid channels"""
    channels = await db.get_required_channels()
    removed_count = 0
    
    for ch in channels:
        is_valid = True
        
        if not ch.get('username') or ch['username'] == 'None':
            is_valid = False
        else:
            try:
                chat = await bot.get_chat(f"@{ch['username']}")
                try:
                    bot_member = await bot.get_chat_member(chat.id, bot.id)
                    if bot_member.status not in ['administrator', 'creator']:
                        is_valid = False
                except:
                    is_valid = False
            except:
                is_valid = False
        
        if not is_valid:
            await db.remove_required_channel(ch['username'])
            removed_count += 1
    
    await callback.answer(f"✅ تم حذف {removed_count} قناة غير صالحة", show_alert=True)
    
    # إعادة عرض قائمة القنوات
    from admin_panel import get_back_button
    channels = await db.get_required_channels()
    
    text = "<b>📺 إدارة القنوات الإجبارية</b>\n\n"
    if channels:
        text += f"<b>عدد القنوات:</b> {len(channels)}\n\n"
        for ch in channels:
            text += f"• {ch['title']} (@{ch['username']})\n"
    else:
        text += "<i>لا توجد قنوات مضافة</i>"
    
    await callback.message.edit_text(text, reply_markup=get_channels_keyboard(channels), parse_mode="HTML")
