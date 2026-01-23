"""
Advanced Admin Panel with Professional UI/UX
"""
import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import config, messages
from database import db
from broadcast_system import broadcast_router, BroadcastStates
from settings_system import settings_router, SettingsStates

logger = logging.getLogger(__name__)

admin_router = Router()


class AdminStates(StatesGroup):
    """Admin panel states"""
    waiting_ban_id = State()
    waiting_unban_id = State()
    waiting_reset_id = State()
    waiting_broadcast_content = State()
    waiting_broadcast_type = State()
    waiting_channel = State()
    waiting_channel_link = State()
    waiting_notification_chat = State()


def is_owner(user_id: int) -> bool:
    """Check if user is primary owner"""
    return user_id == config.PRIMARY_OWNER_ID


async def is_secondary_owner(user_id: int) -> bool:
    """Check if user is secondary owner"""
    user = await db.get_user(user_id)
    return user and user.is_secondary_owner


async def is_admin(user_id: int) -> bool:
    """Check if user has admin access"""
    if is_owner(user_id):
        return True
    user = await db.get_user(user_id)
    return user and (user.is_admin or user.is_secondary_owner)


async def has_full_access(user_id: int) -> bool:
    """Check if user has full access"""
    if is_owner(user_id):
        return True
    return await is_secondary_owner(user_id)


def get_main_menu() -> InlineKeyboardMarkup:
    """Main admin menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin_menu:stats")],
        [
            InlineKeyboardButton(text="👥 إدارة المستخدمين", callback_data="admin_menu:users"),
            InlineKeyboardButton(text="📢 البث", callback_data="admin_menu:broadcast")
        ],
        [
            InlineKeyboardButton(text="📺 القنوات", callback_data="admin_menu:channels"),
            InlineKeyboardButton(text="⚙️ الإعدادات", callback_data="admin_menu:settings")
        ],
        [InlineKeyboardButton(text="❌ إغلاق", callback_data="admin_menu:close")]
    ])


def get_users_menu() -> InlineKeyboardMarkup:
    """User management menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="admin_users:ban")],
        [InlineKeyboardButton(text="✅ إلغاء حظر", callback_data="admin_users:unban")],
        [InlineKeyboardButton(text="🔄 إعادة تعيين الحد", callback_data="admin_users:reset")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:back")]
    ])


def get_settings_menu(user_id: int) -> InlineKeyboardMarkup:
    """Settings menu"""
    buttons = [
        [InlineKeyboardButton(text="👑 إدارة المسؤولين", callback_data="admin_settings:admins")]
    ]
    
    if is_owner(user_id):
        buttons.append([InlineKeyboardButton(text="🔐 إعدادات أمان", callback_data="admin_settings:security")])
    
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_button() -> InlineKeyboardMarkup:
    """Simple back button"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu:back")]
    ])


# ==================== Main Admin Panel ====================

@admin_router.message(Command("admin"))
async def admin_panel_command(message: Message):
    """Open admin panel"""
    logger.info(f"Admin panel requested by user {message.from_user.id}")
    
    if not await is_admin(message.from_user.id):
        logger.warning(f"Unauthorized admin access attempt by user {message.from_user.id}")
        await message.answer("❌ أنت لا تملك صلاحيات الإدارة")
        return
    
    logger.info(f"Admin panel opened for user {message.from_user.id}")
    
    stats = await db.get_stats()
    
    text = f"""
╔════════════════════════════════════╗
║     🤖 لوحة التحكم - الأدمن 🤖     ║
╚════════════════════════════════════╝

📊 <b>إحصائيات سريعة:</b>
  👥 المستخدمين: <code>{stats['total_users']}</code>
  📥 التحميلات اليوم: <code>{stats['downloads_today']}</code>
  🟢 نشطين (24س): <code>{stats['active_users_24h']}</code>

<b>اختر من القائمة أدناه:</b>
"""
    
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")


# ==================== Main Menu Navigation ====================

@admin_router.callback_query(F.data == "admin_menu:back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Back to main menu"""
    await state.clear()
    
    stats = await db.get_stats()
    
    text = f"""
╔════════════════════════════════════╗
║     🤖 لوحة التحكم - الأدمن 🤖     ║
╚════════════════════════════════════╝

📊 <b>إحصائيات سريعة:</b>
  👥 المستخدمين: <code>{stats['total_users']}</code>
  📥 التحميلات اليوم: <code>{stats['downloads_today']}</code>
  🟢 نشطين (24س): <code>{stats['active_users_24h']}</code>

<b>اختر من القائمة أدناه:</b>
"""
    
    await callback.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="HTML")


@admin_router.callback_query(F.data == "admin_menu:close")
async def close_panel(callback: CallbackQuery, state: FSMContext):
    """Close admin panel"""
    await state.clear()
    await callback.message.delete()
    await callback.answer("✅ تم إغلاق لوحة التحكم")


# ==================== Statistics ====================

@admin_router.callback_query(F.data == "admin_menu:stats")
async def show_stats(callback: CallbackQuery):
    """Show detailed statistics"""
    stats = await db.get_stats()
    
    text = f"""
╔════════════════════════════════════╗
║        📊 الإحصائيات التفصيلية 📊    ║
╚════════════════════════════════════╝

👥 <b>المستخدمين:</b>
  • الإجمالي: <code>{stats['total_users']}</code>
  • جدد اليوم: <code>{stats['new_users_today']}</code>
  • نشطين (24س): <code>{stats['active_users_24h']}</code>

📥 <b>التحميلات:</b>
  • اليوم: <code>{stats['downloads_today']}</code>
  • الإجمالي: <code>{stats['total_downloads']}</code>

⏰ <b>الوقت:</b>
  • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")


# ==================== User Management ====================

@admin_router.callback_query(F.data == "admin_menu:users")
async def users_menu(callback: CallbackQuery):
    """User management menu"""
    text = """
╔════════════════════════════════════╗
║      👥 إدارة المستخدمين 👥       ║
╚════════════════════════════════════╝

اختر العملية المطلوبة:
"""
    
    await callback.message.edit_text(text, reply_markup=get_users_menu(), parse_mode="HTML")


@admin_router.callback_query(F.data == "admin_users:ban")
async def ban_user_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to ban"""
    text = """
🚫 <b>حظر مستخدم</b>

أرسل معرف المستخدم (User ID):
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")
    await state.set_state(AdminStates.waiting_ban_id)


@admin_router.message(AdminStates.waiting_ban_id)
async def process_ban(message: Message, state: FSMContext):
    """Process ban"""
    try:
        user_id = int(message.text.strip())
        
        if is_owner(user_id):
            await message.answer("❌ لا يمكن حظر المالك الأساسي!")
            return
        
        await db.ban_user(user_id)
        
        text = f"""
✅ <b>تم الحظر بنجاح</b>

🆔 المستخدم: <code>{user_id}</code>
⏰ الوقت: {datetime.now().strftime('%H:%M:%S')}
"""
        
        await message.answer(text, parse_mode="HTML", reply_markup=get_users_menu())
        await state.clear()
        
    except ValueError:
        await message.answer("❌ معرف غير صالح! أرسل رقم صحيح")


@admin_router.callback_query(F.data == "admin_users:unban")
async def unban_user_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to unban"""
    text = """
✅ <b>إلغاء حظر مستخدم</b>

أرسل معرف المستخدم (User ID):
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")
    await state.set_state(AdminStates.waiting_unban_id)


@admin_router.message(AdminStates.waiting_unban_id)
async def process_unban(message: Message, state: FSMContext):
    """Process unban"""
    try:
        user_id = int(message.text.strip())
        await db.unban_user(user_id)
        
        text = f"""
✅ <b>تم إلغاء الحظر بنجاح</b>

🆔 المستخدم: <code>{user_id}</code>
⏰ الوقت: {datetime.now().strftime('%H:%M:%S')}
"""
        
        await message.answer(text, parse_mode="HTML", reply_markup=get_users_menu())
        await state.clear()
        
    except ValueError:
        await message.answer("❌ معرف غير صالح! أرسل رقم صحيح")


@admin_router.callback_query(F.data == "admin_users:reset")
async def reset_limit_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to reset limit"""
    if not await has_full_access(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    text = """
🔄 <b>إعادة تعيين الحد اليومي</b>

أرسل معرف المستخدم (User ID):
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")
    await state.set_state(AdminStates.waiting_reset_id)


@admin_router.message(AdminStates.waiting_reset_id)
async def process_reset_limit(message: Message, state: FSMContext):
    """Process reset limit"""
    try:
        user_id = int(message.text.strip())
        await db.reset_user_limit(user_id)
        
        text = f"""
✅ <b>تم إعادة التعيين بنجاح</b>

🆔 المستخدم: <code>{user_id}</code>
⏰ الوقت: {datetime.now().strftime('%H:%M:%S')}
"""
        
        await message.answer(text, parse_mode="HTML", reply_markup=get_users_menu())
        await state.clear()
        
    except ValueError:
        await message.answer("❌ معرف غير صالح! أرسل رقم صحيح")


# ==================== Broadcast ====================

@admin_router.callback_query(F.data == "admin_menu:broadcast")
async def broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Broadcast menu - redirect to broadcast system"""
    if not await has_full_access(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    # Import and use broadcast system
    from broadcast_system import get_broadcast_menu
    
    stats = await db.get_stats()
    
    text = f"""
🔥 <b>مرحباً بك في قسم الإذاعة</b>

📊 <b>الإحصائيات:</b>
  • عدد المستخدمين الكلي: <code>{stats['total_users']}</code>
  • عدد الرسائل الخاصة: <code>{stats['total_users']}</code>
  • عدد المجموعات والقنوات: <code>0</code>
  • عدد المحظورين: <code>0</code>

<b>اختر نوع الإذاعة:</b>
"""
    
    await callback.message.edit_text(text, reply_markup=get_broadcast_menu(stats), parse_mode="HTML")


@admin_router.message(AdminStates.waiting_broadcast_content)
async def receive_broadcast(message: Message, state: FSMContext, bot: Bot):
    """Receive broadcast content"""
    users = await db.get_active_users()
    
    text = f"""
📢 <b>تأكيد البث</b>

سيتم إرسال الرسالة إلى:
  👥 <code>{len(users)}</code> مستخدم

هل تريد المتابعة؟
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأكيد", callback_data="broadcast:confirm"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data="broadcast:cancel")
        ]
    ])
    
    await state.update_data(
        broadcast_message_id=message.message_id,
        broadcast_chat_id=message.chat.id
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@admin_router.callback_query(F.data == "broadcast:confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Execute broadcast"""
    data = await state.get_data()
    users = await db.get_active_users()
    
    status_msg = await callback.message.edit_text(
        "📢 <b>جاري البث...</b>\n\n⏳ يرجى الانتظار...",
        parse_mode="HTML"
    )
    
    success = 0
    failed = 0
    
    for i, user_id in enumerate(users):
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=data['broadcast_chat_id'],
                message_id=data['broadcast_message_id']
            )
            success += 1
        except:
            failed += 1
        
        if i % 25 == 0:
            await asyncio.sleep(1)
            try:
                progress = f"✓ {success} | ✗ {failed} | ⏳ {len(users) - i - 1}"
                await status_msg.edit_text(
                    f"📢 <b>جاري البث...</b>\n\n{progress}",
                    parse_mode="HTML"
                )
            except:
                pass
    
    text = f"""
✅ <b>اكتمل البث!</b>

✓ نجح: <code>{success}</code>
✗ فشل: <code>{failed}</code>
📊 الإجمالي: <code>{len(users)}</code>
"""
    
    await status_msg.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")
    await state.clear()


@admin_router.callback_query(F.data == "broadcast:cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    await state.clear()
    await callback.message.edit_text(
        "❌ تم إلغاء البث",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )


# ==================== Channels ====================

@admin_router.callback_query(F.data == "admin_menu:channels")
async def channels_menu(callback: CallbackQuery):
    """Channel management menu - redirect to channels system"""
    if not await has_full_access(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    from channels_system import get_channels_keyboard
    
    channels = await db.get_required_channels()
    
    text = """
╔════════════════════════════════════╗
║     📺 إدارة القنوات الإجبارية 📺   ║
╚════════════════════════════════════╝

"""
    
    if channels:
        text += f"<b>عدد القنوات:</b> <code>{len(channels)}</code>\n\n"
        text += "<b>القنوات الحالية:</b>\n"
        for ch in channels:
            text += f"  • {ch['title']} (@{ch['username']})\n"
    else:
        text += "<i>لا توجد قنوات مضافة</i>\n"
    
    text += "\n<b>اختر العملية المطلوبة:</b>"
    
    await callback.message.edit_text(text, reply_markup=get_channels_keyboard(channels), parse_mode="HTML")


@admin_router.callback_query(F.data == "admin_channels:add")
async def add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt to add channel"""
    text = """
➕ <b>إضافة قناة</b>

أرسل يوزرنيم القناة:
(مثال: channel_name)
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")
    await state.set_state(AdminStates.waiting_channel)


@admin_router.message(AdminStates.waiting_channel)
async def process_add_channel(message: Message, state: FSMContext, bot: Bot):
    """Process adding channel"""
    channel_username = message.text.strip().replace("@", "")
    
    try:
        chat = await bot.get_chat(f"@{channel_username}")
        await db.add_required_channel(channel_username, chat.title, message.from_user.id)
        
        text = f"""
✅ <b>تمت الإضافة بنجاح</b>

📺 القناة: @{channel_username}
📝 الاسم: {chat.title}
"""
        
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ خطأ: {str(e)[:100]}")
    
    await state.clear()


# ==================== Settings ====================

@admin_router.callback_query(F.data == "admin_menu:settings")
async def settings_menu(callback: CallbackQuery):
    """Settings menu"""
    text = """
╔════════════════════════════════════╗
║        ⚙️ الإعدادات ⚙️             ║
╚════════════════════════════════════╝

اختر الإعداد المطلوب:
"""
    
    await callback.message.edit_text(text, reply_markup=get_settings_menu(callback.from_user.id), parse_mode="HTML")


@admin_router.callback_query(F.data == "admin_settings:admins")
async def manage_admins(callback: CallbackQuery):
    """Admin management"""
    if not is_owner(callback.from_user.id):
        await callback.answer("⛔ خاص بالمالك الأساسي فقط", show_alert=True)
        return
    
    admins = await db.get_admins()
    
    text = f"""
👑 <b>إدارة المسؤولين</b>

📊 عدد المسؤولين: <code>{len(admins)}</code>

<b>الأوامر:</b>
  /add_admin [user_id]
  /remove_admin [user_id]
  /add_owner [user_id]
  /remove_owner [user_id]
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")


# ==================== Admin Commands ====================

@admin_router.message(Command("add_admin"))
async def add_admin_command(message: Message):
    """Add admin"""
    if not is_owner(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("استخدم: /add_admin [user_id]")
        return
    
    try:
        user_id = int(args[1])
        await db.set_admin(user_id, True)
        await message.answer(f"✅ تم إضافة {user_id} كمسؤول")
    except ValueError:
        await message.answer("❌ معرف غير صالح!")


@admin_router.message(Command("remove_admin"))
async def remove_admin_command(message: Message):
    """Remove admin"""
    if not is_owner(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("استخدم: /remove_admin [user_id]")
        return
    
    try:
        user_id = int(args[1])
        await db.set_admin(user_id, False)
        await message.answer(f"✅ تم إزالة {user_id} من المسؤولين")
    except ValueError:
        await message.answer("❌ معرف غير صالح!")


@admin_router.message(Command("add_owner"))
async def add_owner_command(message: Message):
    """Add secondary owner"""
    if not is_owner(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("استخدم: /add_owner [user_id]")
        return
    
    try:
        user_id = int(args[1])
        await db.set_secondary_owner(user_id, True)
        await message.answer(f"✅ تم إضافة {user_id} كمالك ثانوي")
    except ValueError:
        await message.answer("❌ معرف غير صالح!")


@admin_router.message(Command("remove_owner"))
async def remove_owner_command(message: Message):
    """Remove secondary owner"""
    if not is_owner(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("استخدم: /remove_owner [user_id]")
        return
    
    try:
        user_id = int(args[1])
        await db.set_secondary_owner(user_id, False)
        await message.answer(f"✅ تم إزالة {user_id} من الملاك الثانويين")
    except ValueError:
        await message.answer("❌ معرف غير صالح!")


async def notify_admins_error(bot: Bot, user_id: int, url: str, 
                              error_type: str, error_message: str) -> None:
    """Notify admins about errors"""
    try:
        error_id = await db.log_error(user_id, url, error_type, error_message)
        admins = await db.get_admins()
        
        if config.PRIMARY_OWNER_ID and config.PRIMARY_OWNER_ID not in admins:
            admins.append(config.PRIMARY_OWNER_ID)
        
        text = f"""
🚨 <b>خطأ في التحميل</b>

🆔 رقم الخطأ: <code>{error_id}</code>
👤 المستخدم: <code>{user_id}</code>
🔗 الرابط: <code>{url[:80]}...</code>
❌ النوع: <code>{error_type}</code>
📝 الرسالة: <code>{error_message[:150]}</code>
"""
        
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except:
                pass
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")
