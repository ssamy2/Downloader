import json
import logging
import re
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config, UI_SETTINGS, build_btn, buttons

logger = logging.getLogger(__name__)

ui_editor_router = Router()

class UIEditorStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_btn_text = State()
    waiting_for_btn_style = State()
    waiting_for_btn_emoji = State()

def get_ui_editor_menu() -> InlineKeyboardMarkup:
    """Main UI Editor Menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 تعديل الرسائل", callback_data="uiedit:messages")],
        [InlineKeyboardButton(text="🎨 تعديل الأزرار", callback_data="uiedit:buttons")],
        [InlineKeyboardButton(text="💡 أوامر ومساعدة التخصيص", callback_data="uiedit:help")],
        [build_btn('BACK', callback_data="admin_menu:settings")]
    ])

def save_ui_settings():
    """Save UI_SETTINGS back to ui_settings.json"""
    with open('data/ui_settings.json', 'w', encoding='utf-8') as f:
        json.dump(UI_SETTINGS, f, ensure_ascii=False, indent=2)

def generate_messages_page(page: int = 0) -> InlineKeyboardMarkup:
    """Generate pagination for messages"""
    keys = list(UI_SETTINGS['messages'].keys())
    items_per_page = 10
    total_pages = (len(keys) + items_per_page - 1) // items_per_page
    
    start = page * items_per_page
    end = start + items_per_page
    page_keys = keys[start:end]
    
    keyboard = []
    for key in page_keys:
        keyboard.append([InlineKeyboardButton(text=f"📄 {key}", callback_data=f"uiedit:msg:{key}")])
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"uiedit:page_msg:{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="التالي ➡️", callback_data=f"uiedit:page_msg:{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton(text="رجوع للواجهة", callback_data="uiedit:menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def generate_buttons_page(page: int = 0) -> InlineKeyboardMarkup:
    """Generate pagination for buttons"""
    keys = list(UI_SETTINGS['button_configs'].keys())
    items_per_page = 10
    total_pages = (len(keys) + items_per_page - 1) // items_per_page
    
    start = page * items_per_page
    end = start + items_per_page
    page_keys = keys[start:end]
    
    keyboard = []
    for key in page_keys:
        text = UI_SETTINGS['button_configs'][key].get('text', key)
        keyboard.append([InlineKeyboardButton(text=f"🔘 {text} ({key})", callback_data=f"uiedit:btn:{key}")])
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"uiedit:page_btn:{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="التالي ➡️", callback_data=f"uiedit:page_btn:{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton(text="رجوع للواجهة", callback_data="uiedit:menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@ui_editor_router.callback_query(F.data == "uiedit:menu")
async def uiedit_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "<b><tg-emoji emoji-id='5190607263005445520'>⚙️</tg-emoji> محرر الواجهة (UI Editor)</b>\n\n<blockquote>اختر القسم الذي تريد تخصيصه:</blockquote>"
    await callback.message.edit_text(text, reply_markup=get_ui_editor_menu(), parse_mode="HTML")

@ui_editor_router.callback_query(F.data == "uiedit:help")
async def uiedit_help(callback: CallbackQuery, state: FSMContext):
    help_text = """
<b><tg-emoji emoji-id='5267500801240092311'>⭐</tg-emoji> دليل التخصيص:</b>

<blockquote><b>تعديل الرسائل:</b>
• يمكنك استخدام تنسيقات عادية (غامق، مائل).
• أرسل إيموجي بريميوم في الرسالة وسيتم حفظه.
• <b>المتغيرات:</b> استخدم <code>#var</code> وسيقوم البوت بتحويله.

<b>تعديل الأزرار:</b>
• تغيير نص الزر.
• تغيير لونه (أزرق، أخضر، أحمر).
• إضافة إيموجي بريميوم بجانبه.</blockquote>
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="رجوع", callback_data="uiedit:menu", style="primary")]
    ])
    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")

@ui_editor_router.callback_query(F.data.startswith("uiedit:page_msg:"))
@ui_editor_router.callback_query(F.data == "uiedit:messages")
async def uiedit_messages(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[2]) if "page_msg" in callback.data else 0
    text = "<b><tg-emoji emoji-id='5444856076954520455'>📝</tg-emoji> قائمة الرسائل</b>\n\n<blockquote>اختر الرسالة لتعديلها:</blockquote>"
    await callback.message.edit_text(text, reply_markup=generate_messages_page(page), parse_mode="HTML")

@ui_editor_router.callback_query(F.data.startswith("uiedit:page_btn:"))
@ui_editor_router.callback_query(F.data == "uiedit:buttons")
async def uiedit_buttons(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[2]) if "page_btn" in callback.data else 0
    text = "<b><tg-emoji emoji-id='5192715031090858438'>💎</tg-emoji> قائمة الأزرار</b>\n\n<blockquote>اختر الزر لتعديله:</blockquote>"
    await callback.message.edit_text(text, reply_markup=generate_buttons_page(page), parse_mode="HTML")

@ui_editor_router.callback_query(F.data.startswith("uiedit:msg:"))
async def edit_specific_message(callback: CallbackQuery, state: FSMContext):
    msg_key = callback.data.split(":")[2]
    current_text = UI_SETTINGS['messages'].get(msg_key, "")
    vars_found = re.findall(r'\{(\w+)\}', current_text)
    vars_hint = " • ".join([f"#{v}" for v in vars_found]) if vars_found else "لا توجد"
    
    text = f"""
<b><tg-emoji emoji-id='5444856076954520455'>📝</tg-emoji> تعديل الرسالة:</b> <code>{msg_key}</code>

<blockquote>{current_text}</blockquote>

<b>المتغيرات المتاحة:</b> {vars_hint}

<i>أرسل النص الجديد الآن:</i>
"""
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="إلغاء", callback_data="uiedit:messages", style="primary")]
    ]), parse_mode="HTML")
    await state.set_state(UIEditorStates.waiting_for_message)
    await state.update_data(edit_key=msg_key)

@ui_editor_router.message(UIEditorStates.waiting_for_message)
async def process_new_message(message: Message, state: FSMContext):
    data = await state.get_data()
    msg_key = data['edit_key']
    
    html_content = message.html_text
    processed_content = re.sub(r'#(\w+)', r'{\1}', html_content)
    
    UI_SETTINGS['messages'][msg_key] = processed_content
    save_ui_settings()
    import config
    setattr(config.messages, msg_key, processed_content)
    
    await message.answer(
        f"<b><tg-emoji emoji-id='5190836223417028350'>✅</tg-emoji> تم حفظ الرسالة!</b>\n\n<blockquote>{processed_content}</blockquote>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="رجوع للرسائل", callback_data="uiedit:messages", style="primary")]
        ]), parse_mode="HTML"
    )
    await state.clear()

async def send_button_menu(message_or_callback, btn_key: str):
    current_config = UI_SETTINGS['button_configs'].get(btn_key, {})
    current_text = current_config.get('text', btn_key)
    current_style = current_config.get('style', 'primary')
    current_emoji = current_config.get('emoji', 'لا يوجد')
    
    text = f"""
<b><tg-emoji emoji-id='5192715031090858438'>💎</tg-emoji> إعدادات الزر:</b> <code>{btn_key}</code>

<blockquote><b>النص:</b> {current_text}
<b>اللون:</b> {current_style}
<b>الإيموجي:</b> {current_emoji}</blockquote>

<i>اختر ما تريد تعديله:</i>
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 تعديل النص", callback_data=f"uiedit:btn_edit_text:{btn_key}", style="primary")],
        [InlineKeyboardButton(text="🎨 تعديل اللون", callback_data=f"uiedit:btn_edit_style:{btn_key}", style="primary")],
        [InlineKeyboardButton(text="✨ تعديل الإيموجي", callback_data=f"uiedit:btn_edit_emoji:{btn_key}", style="primary")],
        [InlineKeyboardButton(text="🗑 إزالة الإيموجي", callback_data=f"uiedit:btn_rm_emoji:{btn_key}", style="primary")],
        [InlineKeyboardButton(text="🔙 رجوع للأزرار", callback_data="uiedit:buttons", style="primary")]
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@ui_editor_router.callback_query(F.data.startswith("uiedit:btn:"))
async def edit_specific_button(callback: CallbackQuery, state: FSMContext):
    btn_key = callback.data.split(":")[2]
    await send_button_menu(callback, btn_key)
    await state.clear()

@ui_editor_router.callback_query(F.data.startswith("uiedit:btn_edit_text:"))
async def prompt_btn_text(callback: CallbackQuery, state: FSMContext):
    btn_key = callback.data.split(":")[2]
    await callback.message.edit_text(
        f"<b><tg-emoji emoji-id='5444856076954520455'>📝</tg-emoji> أرسل النص الجديد للزر:</b> <code>{btn_key}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="إلغاء", callback_data=f"uiedit:btn:{btn_key}", style="primary")]
        ]), parse_mode="HTML"
    )
    await state.set_state(UIEditorStates.waiting_for_btn_text)
    await state.update_data(edit_key=btn_key)

@ui_editor_router.message(UIEditorStates.waiting_for_btn_text)
async def process_button_text(message: Message, state: FSMContext):
    data = await state.get_data()
    btn_key = data['edit_key']
    
    new_text = message.text.strip()
    if btn_key not in UI_SETTINGS['button_configs']:
        UI_SETTINGS['button_configs'][btn_key] = {}
    UI_SETTINGS['button_configs'][btn_key]['text'] = new_text
    save_ui_settings()
    
    await send_button_menu(message, btn_key)
    await state.clear()

@ui_editor_router.callback_query(F.data.startswith("uiedit:btn_edit_style:"))
async def prompt_btn_style(callback: CallbackQuery):
    btn_key = callback.data.split(":")[2]
    text = f"<b><tg-emoji emoji-id='5190607263005445520'>⚙️</tg-emoji> اختر لون الزر:</b> <code>{btn_key}</code>"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="أزرق (Primary)", callback_data=f"uiedit:btn_set_style:{btn_key}:primary")],
        [InlineKeyboardButton(text="أخضر (Success)", callback_data=f"uiedit:btn_set_style:{btn_key}:success")],
        [InlineKeyboardButton(text="أحمر (Danger)", callback_data=f"uiedit:btn_set_style:{btn_key}:danger")],
        [InlineKeyboardButton(text="إلغاء", callback_data=f"uiedit:btn:{btn_key}", style="primary")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@ui_editor_router.callback_query(F.data.startswith("uiedit:btn_set_style:"))
async def process_btn_style(callback: CallbackQuery):
    _, _, btn_key, style = callback.data.split(":")
    if btn_key not in UI_SETTINGS['button_configs']:
        UI_SETTINGS['button_configs'][btn_key] = {}
    UI_SETTINGS['button_configs'][btn_key]['style'] = style
    save_ui_settings()
    
    await callback.answer("✅ تم تغيير اللون!", show_alert=False)
    await send_button_menu(callback, btn_key)

@ui_editor_router.callback_query(F.data.startswith("uiedit:btn_edit_emoji:"))
async def prompt_btn_emoji(callback: CallbackQuery, state: FSMContext):
    btn_key = callback.data.split(":")[2]
    await callback.message.edit_text(
        f"<b><tg-emoji emoji-id='5267500801240092311'>⭐</tg-emoji> أرسل إيموجي بريميوم واحد للزر:</b> <code>{btn_key}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="إلغاء", callback_data=f"uiedit:btn:{btn_key}", style="primary")]
        ]), parse_mode="HTML"
    )
    await state.set_state(UIEditorStates.waiting_for_btn_emoji)
    await state.update_data(edit_key=btn_key)

@ui_editor_router.message(UIEditorStates.waiting_for_btn_emoji)
async def process_button_emoji(message: Message, state: FSMContext):
    data = await state.get_data()
    btn_key = data['edit_key']
    
    emoji_id = None
    if message.entities and message.entities[0].type == "custom_emoji":
        emoji_id = message.entities[0].custom_emoji_id
    
    if emoji_id:
        if btn_key not in UI_SETTINGS['button_configs']:
            UI_SETTINGS['button_configs'][btn_key] = {}
        UI_SETTINGS['button_configs'][btn_key]['emoji'] = emoji_id
        save_ui_settings()
        
        await send_button_menu(message, btn_key)
        await state.clear()
    else:
        await message.answer(
            "<b><tg-emoji emoji-id='5175115075450570337'>❌</tg-emoji> خطأ: لم تقم بإرسال إيموجي بريميوم صحيح.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="إلغاء", callback_data=f"uiedit:btn:{btn_key}", style="primary")]
            ]), parse_mode="HTML"
        )

@ui_editor_router.callback_query(F.data.startswith("uiedit:btn_rm_emoji:"))
async def remove_btn_emoji(callback: CallbackQuery):
    btn_key = callback.data.split(":")[2]
    if btn_key not in UI_SETTINGS['button_configs']:
        UI_SETTINGS['button_configs'][btn_key] = {}
    UI_SETTINGS['button_configs'][btn_key]['emoji'] = None
    save_ui_settings()
    
    await callback.answer("🗑 تم إزالة الإيموجي!", show_alert=False)
    await send_button_menu(callback, btn_key)
