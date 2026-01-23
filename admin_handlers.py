"""
Admin Panel and Broadcast handlers
"""
import asyncio
import logging
import psutil
from typing import Optional, List
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, ContentType
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import config, messages
from database import db

logger = logging.getLogger(__name__)

admin_router = Router()


class BroadcastState(StatesGroup):
    """States for broadcast operation"""
    waiting_content = State()
    confirming = State()


class ChannelState(StatesGroup):
    """States for channel management"""
    waiting_channel = State()


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
    """Check if user has full access (owner or secondary owner)"""
    if is_owner(user_id):
        return True
    return await is_secondary_owner(user_id)


def get_admin_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate admin panel keyboard based on permissions"""
    buttons = []
    
    # Statistics - available to all admins
    buttons.append([
        InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin:stats")
    ])
    
    # User management
    buttons.append([
        InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="admin:ban"),
        InlineKeyboardButton(text="✅ إلغاء الحظر", callback_data="admin:unban")
    ])
    
    # Full access features
    buttons.append([
        InlineKeyboardButton(text="📢 بث رسالة", callback_data="admin:broadcast"),
        InlineKeyboardButton(text="🔄 إعادة تعيين الحد", callback_data="admin:reset_limit")
    ])
    
    # Channel management
    buttons.append([
        InlineKeyboardButton(text="📺 إدارة القنوات", callback_data="admin:channels")
    ])
    
    # Owner only features
    if is_owner(user_id):
        buttons.append([
            InlineKeyboardButton(text="👑 إدارة المسؤولين", callback_data="admin:manage_admins")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="❌ إغلاق", callback_data="admin:close")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_channels_keyboard(channels: List[dict]) -> InlineKeyboardMarkup:
    """Generate channel management keyboard"""
    buttons = []
    
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ {ch['title'] or ch['username']}", 
                callback_data=f"rm_channel:{ch['username']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="➕ إضافة قناة", callback_data="add_channel")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 رجوع", callback_data="admin:back")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_server_stats() -> dict:
    """Get server health statistics"""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent if hasattr(psutil.disk_usage('/'), 'percent') else 0
        
        # Windows compatibility
        try:
            disk = psutil.disk_usage('C:\\').percent
        except:
            pass
        
        return {
            'cpu': round(cpu, 1),
            'ram': round(ram, 1),
            'disk': round(disk, 1),
            'status': '🟢 جيد' if cpu < 80 and ram < 80 else '🟡 متوسط' if cpu < 95 else '🔴 مرتفع'
        }
    except Exception as e:
        logger.error(f"Error getting server stats: {e}")
        return {'cpu': 0, 'ram': 0, 'disk': 0, 'status': '⚪ غير متاح'}


@admin_router.message(Command("admin"))
async def admin_panel_command(message: Message):
    """Show admin panel"""
    if not await is_admin(message.from_user.id):
        return
    
    stats = await db.get_stats()
    server = get_server_stats()
    
    text = messages.ADMIN_PANEL.format(
        users=stats['total_users'],
        downloads=stats['downloads_today'],
        status=server['status']
    )
    
    await message.answer(
        text,
        reply_markup=get_admin_keyboard(message.from_user.id),
        parse_mode="HTML"
    )


@admin_router.message(Command("stats"))
async def stats_command(message: Message):
    """Show detailed statistics"""
    if not await is_admin(message.from_user.id):
        return
    
    stats = await db.get_stats()
    server = get_server_stats()
    
    text = messages.STATS.format(
        total_users=stats['total_users'],
        new_users=stats['new_users_today'],
        downloads_today=stats['downloads_today'],
        total_downloads=stats['total_downloads'],
        cpu=server['cpu'],
        ram=server['ram'],
        disk=server['disk']
    )
    
    await message.answer(text, parse_mode="HTML")


@admin_router.callback_query(F.data == "admin:stats")
async def stats_callback(callback: CallbackQuery):
    """Show statistics via callback"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    stats = await db.get_stats()
    server = get_server_stats()
    
    text = messages.STATS.format(
        total_users=stats['total_users'],
        new_users=stats['new_users_today'],
        downloads_today=stats['downloads_today'],
        total_downloads=stats['total_downloads'],
        cpu=server['cpu'],
        ram=server['ram'],
        disk=server['disk']
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin:back")]
        ]),
        parse_mode="HTML"
    )


@admin_router.callback_query(F.data == "admin:back")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    """Return to admin panel"""
    await state.clear()
    
    stats = await db.get_stats()
    server = get_server_stats()
    
    text = messages.ADMIN_PANEL.format(
        users=stats['total_users'],
        downloads=stats['downloads_today'],
        status=server['status']
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard(callback.from_user.id),
        parse_mode="HTML"
    )


@admin_router.callback_query(F.data == "admin:close")
async def close_admin(callback: CallbackQuery, state: FSMContext):
    """Close admin panel"""
    await state.clear()
    await callback.message.delete()


# ==================== Ban/Unban ====================

@admin_router.callback_query(F.data == "admin:ban")
async def ban_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to ban"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🚫 <b>حظر مستخدم</b>\n\nأرسل معرف المستخدم (User ID):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin:back")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state("waiting_ban_id")


@admin_router.message(StateFilter("waiting_ban_id"))
async def process_ban(message: Message, state: FSMContext):
    """Process ban request"""
    try:
        user_id = int(message.text.strip())
        
        # Can't ban owner
        if is_owner(user_id):
            await message.answer("⛔ لا يمكن حظر المالك الأساسي!")
            await state.clear()
            return
        
        await db.ban_user(user_id)
        await message.answer(
            messages.USER_BANNED.format(user_id=user_id),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ معرف غير صالح!")
    
    await state.clear()


@admin_router.callback_query(F.data == "admin:unban")
async def unban_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to unban"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    await callback.message.edit_text(
        "✅ <b>إلغاء حظر مستخدم</b>\n\nأرسل معرف المستخدم (User ID):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin:back")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state("waiting_unban_id")


@admin_router.message(StateFilter("waiting_unban_id"))
async def process_unban(message: Message, state: FSMContext):
    """Process unban request"""
    try:
        user_id = int(message.text.strip())
        await db.unban_user(user_id)
        await message.answer(
            messages.USER_UNBANNED.format(user_id=user_id),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ معرف غير صالح!")
    
    await state.clear()


@admin_router.message(Command("ban"))
async def ban_command(message: Message):
    """Ban user via command"""
    if not await is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("استخدم: /ban [user_id]")
        return
    
    try:
        user_id = int(args[1])
        if is_owner(user_id):
            await message.answer("⛔ لا يمكن حظر المالك الأساسي!")
            return
        
        await db.ban_user(user_id)
        await message.answer(
            messages.USER_BANNED.format(user_id=user_id),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ معرف غير صالح!")


@admin_router.message(Command("unban"))
async def unban_command(message: Message):
    """Unban user via command"""
    if not await is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("استخدم: /unban [user_id]")
        return
    
    try:
        user_id = int(args[1])
        await db.unban_user(user_id)
        await message.answer(
            messages.USER_UNBANNED.format(user_id=user_id),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ معرف غير صالح!")


# ==================== Reset Limit ====================

@admin_router.callback_query(F.data == "admin:reset_limit")
async def reset_limit_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user ID to reset limit"""
    if not await has_full_access(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔄 <b>إعادة تعيين الحد اليومي</b>\n\nأرسل معرف المستخدم (User ID):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin:back")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state("waiting_reset_id")


@admin_router.message(StateFilter("waiting_reset_id"))
async def process_reset_limit(message: Message, state: FSMContext):
    """Process reset limit request"""
    try:
        user_id = int(message.text.strip())
        await db.reset_user_limit(user_id)
        await message.answer(
            messages.LIMIT_RESET.format(user_id=user_id),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ معرف غير صالح!")
    
    await state.clear()


@admin_router.message(Command("reset_limit"))
async def reset_limit_command(message: Message):
    """Reset user limit via command"""
    if not await has_full_access(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("استخدم: /reset_limit [user_id]")
        return
    
    try:
        user_id = int(args[1])
        await db.reset_user_limit(user_id)
        await message.answer(
            messages.LIMIT_RESET.format(user_id=user_id),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ معرف غير صالح!")


# ==================== Broadcast ====================

@admin_router.callback_query(F.data == "admin:broadcast")
async def broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for broadcast content"""
    if not await has_full_access(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 <b>بث رسالة</b>\n\nأرسل الرسالة التي تريد بثها (نص، صورة، أو فيديو):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin:back")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastState.waiting_content)


@admin_router.message(BroadcastState.waiting_content)
async def receive_broadcast_content(message: Message, state: FSMContext):
    """Receive and confirm broadcast content"""
    await state.update_data(
        broadcast_message_id=message.message_id,
        broadcast_chat_id=message.chat.id,
        content_type=message.content_type
    )
    
    users = await db.get_active_users()
    
    await message.answer(
        f"📢 <b>تأكيد البث</b>\n\nسيتم إرسال الرسالة إلى <b>{len(users)}</b> مستخدم.\n\nهل تريد المتابعة؟",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تأكيد", callback_data="broadcast:confirm"),
                InlineKeyboardButton(text="❌ إلغاء", callback_data="broadcast:cancel")
            ]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastState.confirming)


@admin_router.callback_query(F.data == "broadcast:confirm", BroadcastState.confirming)
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Execute broadcast"""
    data = await state.get_data()
    await state.clear()
    
    users = await db.get_active_users()
    
    status_msg = await callback.message.edit_text(
        messages.BROADCAST_START.format(count=len(users)),
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
        except (TelegramBadRequest, TelegramForbiddenError):
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast error for {user_id}: {e}")
            failed += 1
        
        # Rate limiting - update every 25 users
        if i % 25 == 0:
            await asyncio.sleep(1)
            try:
                await status_msg.edit_text(
                    f"📢 <b>جاري البث...</b>\n\n✓ نجح: {success}\n✗ فشل: {failed}\n📊 المتبقي: {len(users) - i - 1}",
                    parse_mode="HTML"
                )
            except:
                pass
    
    await status_msg.edit_text(
        messages.BROADCAST_DONE.format(success=success, failed=failed),
        parse_mode="HTML"
    )


@admin_router.callback_query(F.data == "broadcast:cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    await state.clear()
    await callback.message.edit_text("❌ تم إلغاء البث")


@admin_router.message(Command("broadcast"))
async def broadcast_command(message: Message, state: FSMContext):
    """Start broadcast via command"""
    if not await has_full_access(message.from_user.id):
        return
    
    await message.answer(
        "📢 <b>بث رسالة</b>\n\nأرسل الرسالة التي تريد بثها:",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastState.waiting_content)


# ==================== Channel Management ====================

@admin_router.callback_query(F.data == "admin:channels")
async def channels_management(callback: CallbackQuery):
    """Show channel management panel"""
    if not await has_full_access(callback.from_user.id):
        await callback.answer("⛔ غير مصرح", show_alert=True)
        return
    
    channels = await db.get_required_channels()
    
    text = "📺 <b>إدارة قنوات الاشتراك الإجباري</b>\n\n"
    if channels:
        text += "القنوات الحالية:\n"
        for ch in channels:
            text += f"• @{ch['username']}\n"
    else:
        text += "<i>لا توجد قنوات مضافة</i>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_channels_keyboard(channels),
        parse_mode="HTML"
    )


@admin_router.callback_query(F.data == "add_channel")
async def add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt to add channel"""
    await callback.message.edit_text(
        "➕ <b>إضافة قناة</b>\n\nأرسل يوزرنيم القناة (مثال: @channel):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin:channels")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(ChannelState.waiting_channel)


@admin_router.message(ChannelState.waiting_channel)
async def process_add_channel(message: Message, state: FSMContext, bot: Bot):
    """Process adding a channel"""
    channel_username = message.text.strip().replace("@", "")
    
    try:
        # Verify channel exists and bot is admin
        chat = await bot.get_chat(f"@{channel_username}")
        
        await db.add_required_channel(
            channel_username=channel_username,
            channel_title=chat.title,
            added_by=message.from_user.id
        )
        
        await message.answer(f"✅ تمت إضافة القناة: @{channel_username}")
    except Exception as e:
        await message.answer(f"❌ فشل إضافة القناة: {e}")
    
    await state.clear()


@admin_router.callback_query(F.data.startswith("rm_channel:"))
async def remove_channel(callback: CallbackQuery):
    """Remove a required channel"""
    channel_username = callback.data.split(":")[1]
    
    await db.remove_required_channel(channel_username)
    await callback.answer(f"✅ تم إزالة @{channel_username}")
    
    # Refresh the list
    channels = await db.get_required_channels()
    
    text = "📺 <b>إدارة قنوات الاشتراك الإجباري</b>\n\n"
    if channels:
        text += "القنوات الحالية:\n"
        for ch in channels:
            text += f"• @{ch['username']}\n"
    else:
        text += "<i>لا توجد قنوات مضافة</i>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_channels_keyboard(channels),
        parse_mode="HTML"
    )


# ==================== Admin Management (Owner Only) ====================

@admin_router.callback_query(F.data == "admin:manage_admins")
async def manage_admins(callback: CallbackQuery):
    """Admin management panel (owner only)"""
    if not is_owner(callback.from_user.id):
        await callback.answer("⛔ خاص بالمالك الأساسي فقط", show_alert=True)
        return
    
    admins = await db.get_admins()
    
    text = "👑 <b>إدارة المسؤولين</b>\n\n"
    text += f"عدد المسؤولين: {len(admins)}\n\n"
    text += "الأوامر:\n"
    text += "• /add_admin [user_id] - إضافة مسؤول\n"
    text += "• /remove_admin [user_id] - إزالة مسؤول\n"
    text += "• /add_owner [user_id] - إضافة مالك ثانوي\n"
    text += "• /remove_owner [user_id] - إزالة مالك ثانوي"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin:back")]
        ]),
        parse_mode="HTML"
    )


@admin_router.message(Command("add_admin"))
async def add_admin_command(message: Message):
    """Add admin via command (owner only)"""
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
    """Remove admin via command (owner only)"""
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
    """Add secondary owner (primary owner only)"""
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
    """Remove secondary owner (primary owner only)"""
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
    """Notify admins about download errors"""
    try:
        # Log to database
        error_id = await db.log_error(user_id, url, error_type, error_message)
        
        admins = await db.get_admins()
        if config.PRIMARY_OWNER_ID and config.PRIMARY_OWNER_ID not in admins:
            admins.append(config.PRIMARY_OWNER_ID)
        
        text = f"""
🚨 <b>خطأ في التحميل</b>

🆔 رقم الخطأ: <code>{error_id}</code>
👤 المستخدم: <code>{user_id}</code>
🔗 الرابط: <code>{url[:100]}...</code>
❌ النوع: <code>{error_type}</code>
📝 الرسالة: <code>{error_message[:200]}</code>
"""
        
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")
