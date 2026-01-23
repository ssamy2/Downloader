"""
Advanced Broadcast System with Multiple Options
"""
import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database import db

logger = logging.getLogger(__name__)

broadcast_router = Router()


class BroadcastStates(StatesGroup):
    """Broadcast states"""
    waiting_content = State()
    waiting_forward = State()


def get_broadcast_menu(stats: dict) -> InlineKeyboardMarkup:
    """Get broadcast menu keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ تثبيت الإذاعة", callback_data="broadcast:toggle_pin")],
        [
            InlineKeyboardButton(text="إذاعة توجيه للكل", callback_data="broadcast:forward_all"),
            InlineKeyboardButton(text="بث للجميع", callback_data="broadcast:send_all")
        ],
        [
            InlineKeyboardButton(text="إذاعة للخاص", callback_data="broadcast:private"),
            InlineKeyboardButton(text="إذاعة توجيه للخاص", callback_data="broadcast:forward_private")
        ],
        [InlineKeyboardButton(text="إذاعة مجموعات", callback_data="broadcast:groups")],
        [
            InlineKeyboardButton(text="إعادة توجيه إذاعة إلى المجموعات", callback_data="broadcast:forward_groups"),
            InlineKeyboardButton(text="إذاعة توجيه إلى الجميع", callback_data="broadcast:forward_all_groups")
        ],
        [InlineKeyboardButton(text="• رجوع •", callback_data="admin_menu:back")]
    ])


@broadcast_router.callback_query(F.data.startswith("broadcast:"))
async def handle_broadcast_type(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Handle broadcast type selection"""
    action = callback.data.split(":")[1]
    
    if action == "toggle_pin":
        await state.update_data(pin_message=True)
        await callback.answer("✅ سيتم تثبيت الرسالة", show_alert=True)
        return
    
    # Store broadcast type
    await state.update_data(broadcast_type=action)
    
    if action in ["forward_all", "forward_private", "forward_groups", "forward_all_groups"]:
        text = """
📤 <b>إعادة توجيه رسالة</b>

قم بإعادة توجيه الرسالة التي تريد بثها:
(يمكن أن تكون نص، صورة، فيديو، ملف، أو أي نوع)
"""
        await callback.message.edit_text(text, parse_mode="HTML")
        await state.set_state(BroadcastStates.waiting_forward)
    else:
        text = """
📝 <b>أرسل محتوى الإذاعة</b>

يمكنك إرسال:
  • نص (مع دعم HTML/Markdown)
  • صورة مع نص
  • فيديو مع نص
  • ملف مع نص
  • أي نوع محتوى
"""
        await callback.message.edit_text(text, parse_mode="HTML")
        await state.set_state(BroadcastStates.waiting_content)


@broadcast_router.message(BroadcastStates.waiting_content)
async def receive_broadcast_content(message: Message, state: FSMContext, bot: Bot):
    """Receive and process broadcast content"""
    data = await state.get_data()
    broadcast_type = data.get('broadcast_type', 'send_all')
    pin_message = data.get('pin_message', False)
    
    # Get target users based on type
    if broadcast_type == "private":
        users = await db.get_active_users()
    elif broadcast_type == "groups":
        users = []  # TODO: Implement groups
    else:  # send_all
        users = await db.get_active_users()
    
    # Confirm broadcast
    text = f"""
📢 <b>تأكيد الإذاعة</b>

📊 سيتم الإرسال إلى: <code>{len(users)}</code> مستخدم
📌 التثبيت: {'نعم' if pin_message else 'لا'}

هل تريد المتابعة؟
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأكيد", callback_data="broadcast_confirm:yes"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data="broadcast_confirm:no")
        ]
    ])
    
    await state.update_data(
        message_id=message.message_id,
        chat_id=message.chat.id,
        users=users
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@broadcast_router.message(BroadcastStates.waiting_forward)
async def receive_broadcast_forward(message: Message, state: FSMContext, bot: Bot):
    """Receive forwarded message for broadcast"""
    data = await state.get_data()
    broadcast_type = data.get('broadcast_type', 'forward_all')
    
    # Get target users
    if broadcast_type == "forward_private":
        users = await db.get_active_users()
    elif broadcast_type in ["forward_groups", "forward_all_groups"]:
        users = []  # TODO: Implement groups
    else:  # forward_all
        users = await db.get_active_users()
    
    text = f"""
📢 <b>تأكيد الإذاعة</b>

📊 سيتم التوجيه إلى: <code>{len(users)}</code> مستخدم

هل تريد المتابعة؟
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأكيد", callback_data="broadcast_confirm:yes"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data="broadcast_confirm:no")
        ]
    ])
    
    await state.update_data(
        message_id=message.message_id,
        chat_id=message.chat.id,
        users=users,
        is_forward=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@broadcast_router.callback_query(F.data.startswith("broadcast_confirm:"))
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Execute or cancel broadcast"""
    action = callback.data.split(":")[1]
    
    if action == "no":
        await callback.message.edit_text("❌ تم إلغاء الإذاعة", parse_mode="HTML")
        await state.clear()
        return
    
    # Execute broadcast
    data = await state.get_data()
    users = data.get('users', [])
    message_id = data.get('message_id')
    chat_id = data.get('chat_id')
    is_forward = data.get('is_forward', False)
    pin_message = data.get('pin_message', False)
    
    status_msg = await callback.message.edit_text(
        "📢 <b>جاري الإذاعة...</b>\n\n⏳ يرجى الانتظار...",
        parse_mode="HTML"
    )
    
    success = 0
    failed = 0
    blocked = 0
    
    for i, user_id in enumerate(users):
        try:
            if is_forward:
                sent_msg = await bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=chat_id,
                    message_id=message_id
                )
            else:
                sent_msg = await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=chat_id,
                    message_id=message_id
                )
            
            # Pin if requested
            if pin_message:
                try:
                    await bot.pin_chat_message(user_id, sent_msg.message_id, disable_notification=True)
                except:
                    pass
            
            success += 1
        except TelegramForbiddenError:
            blocked += 1
            failed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast error for user {user_id}: {e}")
        
        # Update progress every 25 users
        if i % 25 == 0 and i > 0:
            await asyncio.sleep(1)
            try:
                progress = f"✓ {success} | ✗ {failed} | 🚫 {blocked} | ⏳ {len(users) - i - 1}"
                await status_msg.edit_text(
                    f"📢 <b>جاري الإذاعة...</b>\n\n{progress}",
                    parse_mode="HTML"
                )
            except:
                pass
    
    # Final result
    text = f"""
✅ <b>اكتملت الإذاعة!</b>

✓ نجح: <code>{success}</code>
✗ فشل: <code>{failed}</code>
🚫 محظور: <code>{blocked}</code>
📊 الإجمالي: <code>{len(users)}</code>

⏰ الوقت: {datetime.now().strftime('%H:%M:%S')}
"""
    
    await status_msg.edit_text(text, parse_mode="HTML")
    await state.clear()
