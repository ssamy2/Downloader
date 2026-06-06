from config import emojis, build_btn
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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import BaseFilter, Command, StateFilter

from config import config, messages
from core.database import db
from admin.broadcast_system import broadcast_router, BroadcastStates
from admin.settings_system import settings_router, SettingsStates

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
    waiting_permission_user_id = State()
    waiting_permission_action = State()


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


class IsAdminFilter(BaseFilter):
    """Filter to allow only admins"""
    async def __call__(self, event, **kwargs) -> bool:
        return await is_admin(event.from_user.id)


class HasFullAccessFilter(BaseFilter):
    """Filter to allow only owners and secondary owners"""
    async def __call__(self, event, **kwargs) -> bool:
        return await has_full_access(event.from_user.id)


def get_main_menu() -> InlineKeyboardMarkup:
    """Main admin menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [build_btn('STATS',  callback_data="admin_menu:stats")],
        [
            build_btn('ADMIN_USERS_MGR',  callback_data="admin_menu:users"),
            build_btn('BROADCAST',  callback_data="admin_menu:broadcast")
        ],
        [
            build_btn('CHANNELS',  callback_data="admin_menu:channels"),
            build_btn('SETTINGS',  callback_data="admin_menu:settings")
        ],
        [InlineKeyboardButton(text="🎨 تعديل الواجهة", callback_data="uiedit:menu")],
        [build_btn('CLOSE',  callback_data="admin_menu:close")]
    ])


def get_users_menu() -> InlineKeyboardMarkup:
    """User management menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [build_btn('BAN_USER',  callback_data="admin_users:ban")],
        [build_btn('UNBAN',  callback_data="admin_users:unban")],
        [build_btn('RESET_LIMIT',  callback_data="admin_users:reset")],
        [build_btn('USER_PERMS',  callback_data="admin_users:permissions")],
        [build_btn('BACK',  callback_data="admin_menu:back")]
    ])


def get_settings_menu(user_id: int) -> InlineKeyboardMarkup:
    """Settings menu"""
    buttons = [
        [build_btn('ADMIN_ADMINS_MGR',  callback_data="admin_settings:admins")]
    ]
    

    buttons.append([build_btn('BACK',  callback_data="admin_menu:back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_button() -> InlineKeyboardMarkup:
    """Simple back button"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [build_btn('BACK',  callback_data="admin_menu:back")]
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
<b><tg-emoji emoji-id='5190607263005445520'>⚙️</tg-emoji> لوحة تحكم الإدارة</b>

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
<b><tg-emoji emoji-id='5190607263005445520'>⚙️</tg-emoji> لوحة تحكم الإدارة</b>

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
<b><tg-emoji emoji-id='5190806721286657692'>📊</tg-emoji> الإحصائيات التفصيلية</b>

<blockquote><b><tg-emoji emoji-id='5332724926216428039'>👥</tg-emoji> المستخدمين:</b>
  • الإجمالي: <code>{stats['total_users']}</code>
  • جدد اليوم: <code>{stats['new_users_today']}</code>
  • نشطين (24س): <code>{stats['active_users_24h']}</code>

<b><tg-emoji emoji-id='5443127283898405358'>📥</tg-emoji> التحميلات:</b>
  • اليوم: <code>{stats['downloads_today']}</code>
  • الإجمالي: <code>{stats['total_downloads']}</code>

<b><tg-emoji emoji-id='5382194935057372936'>⏰</tg-emoji> الوقت:</b>
  • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</blockquote>
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")


# ==================== User Management ====================

@admin_router.callback_query(F.data == "admin_menu:users")
async def users_menu(callback: CallbackQuery):
    """User management menu"""
    text = """
<b><tg-emoji emoji-id='5332724926216428039'>👥</tg-emoji> إدارة المستخدمين</b>

<blockquote>اختر العملية المطلوبة:</blockquote>
"""
    
    await callback.message.edit_text(text, reply_markup=get_users_menu(), parse_mode="HTML")


@admin_router.callback_query(F.data == "admin_users:ban")
async def ban_user_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to ban"""
    text = """
<b><tg-emoji emoji-id='5175115075450570337'>🚫</tg-emoji> حظر مستخدم</b>

<blockquote>أرسل معرف المستخدم (User ID):</blockquote>
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
<b><tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> تم الحظر بنجاح</b>

<blockquote>المستخدم: <code>{user_id}</code>
الوقت: {datetime.now().strftime('%H:%M:%S')}</blockquote>
"""
        
        await message.answer(text, parse_mode="HTML", reply_markup=get_users_menu())
        await state.clear()
        
    except ValueError:
        await message.answer("❌ معرف غير صالح! أرسل رقم صحيح")


@admin_router.callback_query(F.data == "admin_users:unban")
async def unban_user_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to unban"""
    text = """
<b><tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> إلغاء حظر مستخدم</b>

<blockquote>أرسل معرف المستخدم (User ID):</blockquote>
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
<b><tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> تم إلغاء الحظر بنجاح</b>

<blockquote>المستخدم: <code>{user_id}</code>
الوقت: {datetime.now().strftime('%H:%M:%S')}</blockquote>
"""
        
        await message.answer(text, parse_mode="HTML", reply_markup=get_users_menu())
        await state.clear()
        
    except ValueError:
        await message.answer("❌ معرف غير صالح! أرسل رقم صحيح")


@admin_router.callback_query(F.data == "admin_users:permissions")
async def user_permissions_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to manage permissions"""
    if not is_owner(callback.from_user.id):
        await callback.answer("⛔ هذه الميزة للمالك فقط", show_alert=True)
        return
    
    text = """
<b><tg-emoji emoji-id='5197288647275071607'>🔐</tg-emoji> إدارة صلاحيات المستخدم</b>

<blockquote>أرسل معرف المستخدم (User ID):</blockquote>
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")
    await state.set_state(AdminStates.waiting_permission_user_id)


@admin_router.message(AdminStates.waiting_permission_user_id)
async def process_permission_user(message: Message, state: FSMContext):
    """Process permission user ID and show permission menu"""
    try:
        user_id = int(message.text.strip())
        
        # Get current permissions
        perms = await db.get_user_permissions(user_id)
        
        # Store user_id in state
        await state.update_data(target_user_id=user_id)
        
        # Create permission buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"📥 التحميل: {'✅' if perms['can_download'] else '❌'}",
                callback_data=f"perm:toggle:can_download:{user_id}"
            , style="primary")],
            [InlineKeyboardButton(
                text=f"🎬 اختيار الجودة: {'✅' if perms['can_use_quality'] else '❌'}",
                callback_data=f"perm:toggle:can_use_quality:{user_id}"
            , style="primary")],
            [InlineKeyboardButton(
                text=f"🎵 تحميل صوتي: {'✅' if perms['can_download_audio'] else '❌'}",
                callback_data=f"perm:toggle:can_download_audio:{user_id}"
            , style="primary")],
            [build_btn('BACK',  callback_data="admin_menu:users")]
        ])
        
        text = f"""
🔐 <b>صلاحيات المستخدم</b>

🆔 المستخدم: <code>{user_id}</code>

<b>الصلاحيات الحالية:</b>
📥 التحميل: {'✅ مفعّل' if perms['can_download'] else '❌ معطّل'}
🎬 اختيار الجودة: {'✅ مفعّل' if perms['can_use_quality'] else '❌ معطّل'}
🎵 تحميل صوتي: {'✅ مفعّل' if perms['can_download_audio'] else '❌ معطّل'}

<i>اضغط على الصلاحية لتبديلها</i>
"""
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await state.clear()
        
    except ValueError:
        await message.answer("❌ معرف غير صالح! أرسل رقم صحيح")


@admin_router.callback_query(F.data.startswith("perm:toggle:"))
async def toggle_permission(callback: CallbackQuery):
    """Toggle user permission"""
    if not is_owner(callback.from_user.id):
        await callback.answer("⛔ هذه الميزة للمالك فقط", show_alert=True)
        return
    
    try:
        _, _, permission, user_id = callback.data.split(":")
        user_id = int(user_id)
        
        # Get current permissions
        perms = await db.get_user_permissions(user_id)
        
        # Toggle the permission
        new_value = not perms[permission]
        await db.set_user_permission(user_id, permission, new_value)
        
        # Get updated permissions
        perms = await db.get_user_permissions(user_id)
        
        # Update keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"📥 التحميل: {'✅' if perms['can_download'] else '❌'}",
                callback_data=f"perm:toggle:can_download:{user_id}"
            , style="primary")],
            [InlineKeyboardButton(
                text=f"🎬 اختيار الجودة: {'✅' if perms['can_use_quality'] else '❌'}",
                callback_data=f"perm:toggle:can_use_quality:{user_id}"
            , style="primary")],
            [InlineKeyboardButton(
                text=f"🎵 تحميل صوتي: {'✅' if perms['can_download_audio'] else '❌'}",
                callback_data=f"perm:toggle:can_download_audio:{user_id}"
            , style="primary")],
            [build_btn('BACK',  callback_data="admin_menu:users")]
        ])
        
        text = f"""
🔐 <b>صلاحيات المستخدم</b>

🆔 المستخدم: <code>{user_id}</code>

<b>الصلاحيات الحالية:</b>
📥 التحميل: {'✅ مفعّل' if perms['can_download'] else '❌ معطّل'}
🎬 اختيار الجودة: {'✅ مفعّل' if perms['can_use_quality'] else '❌ معطّل'}
🎵 تحميل صوتي: {'✅ مفعّل' if perms['can_download_audio'] else '❌ معطّل'}

<i>اضغط على الصلاحية لتبديلها</i>
"""
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("✅ تم التحديث", show_alert=False)
        
    except Exception as e:
        logger.error(f"Error toggling permission: {e}")
        await callback.answer("❌ حدث خطأ", show_alert=True)


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
<b><tg-emoji emoji-id='5298609030321691620'>📢</tg-emoji> قسم الإذاعة</b>

<blockquote><b>الإحصائيات:</b>
  • عدد المستخدمين الكلي: <code>{stats['total_users']}</code>
  • عدد الرسائل الخاصة: <code>{stats['total_users']}</code>
  • عدد المجموعات والقنوات: <code>0</code>
  • عدد المحظورين: <code>0</code></blockquote>

اختر نوع الإذاعة:
"""
    
    await callback.message.edit_text(text, reply_markup=get_broadcast_menu(stats), parse_mode="HTML")


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
<b><tg-emoji emoji-id='5190401572726675514'>📺</tg-emoji> إدارة القنوات الإجبارية</b>

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
<b><tg-emoji emoji-id='5444856076954520455'>➕</tg-emoji> إضافة قناة</b>

<blockquote>أرسل يوزرنيم القناة:
(مثال: channel_name)</blockquote>
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
<b><tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> تمت الإضافة بنجاح</b>

<blockquote>القناة: @{channel_username}
الاسم: {chat.title}</blockquote>
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
<b><tg-emoji emoji-id='5190607263005445520'>⚙️</tg-emoji> الإعدادات</b>

<blockquote>اختر الإعداد المطلوب من القائمة:</blockquote>
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
<b><tg-emoji emoji-id='5192715031090858438'>👑</tg-emoji> إدارة المسؤولين</b>

<blockquote>عدد المسؤولين: <code>{len(admins)}</code>

<b>الأوامر المتاحة:</b>
  • <code>/add_admin [user_id]</code>
  • <code>/remove_admin [user_id]</code>
  • <code>/add_owner [user_id]</code>
  • <code>/remove_owner [user_id]</code></blockquote>
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
<b><tg-emoji emoji-id='5172571638767551946'>⚠️</tg-emoji> خطأ في التحميل</b>

<blockquote><b>رقم الخطأ:</b> <code>{error_id}</code>
<b>المستخدم:</b> <code>{user_id}</code>
<b>الرابط:</b> <code>{url[:80]}...</code>
<b>النوع:</b> <code>{error_type}</code>
<b>الرسالة:</b> <code>{error_message[:150]}</code></blockquote>
"""
        
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except:
                pass
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")
