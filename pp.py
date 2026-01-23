import telebot
import requests
import json
import os
import io
from threading import Thread
from telebot import types

API_TOKEN = '8547246244:AAGXFJnnESuSCfxK9miJMx93-k14SJ-htkw'
OWNER_ID = 7565750369  
bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=100)

DATA_FILE = 'database.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "admins": [OWNER_ID],
            "users": [],
            "banned_users": {},
            "blocked_by": [],
            "settings": {
                "start_msg": "مرحباً بك في بوت تحميل تيك توك! 🚀",
                "protect_content": True,
                "exclude_media": False,
                "exclude_links": False,
                "exclude_text": False,
                "notify_new_user": True,
                "notify_block": True,
                "notify_unblock": True,
                "channels": []
            },
            "stats": {"total_downloads": 0}
        }
        save_data(data)
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def is_admin(user_id):
    return user_id in load_data()['admins']

def secure_send(chat_id, content_type, **kwargs):
    data = load_data()
    s = data['settings']
    should_protect = s['protect_content']
    
    if content_type == 'text' and s['exclude_text']: should_protect = False
    if content_type in ['video', 'photo', 'document'] and s['exclude_media']: should_protect = False
    
    kwargs['protect_content'] = should_protect
    
    if content_type == 'text': return bot.send_message(chat_id, **kwargs)
    if content_type == 'video': return bot.send_video(chat_id, **kwargs)
    if content_type == 'photo': return bot.send_photo(chat_id, **kwargs)
    if content_type == 'document': return bot.send_document(chat_id, **kwargs)

def check_sub(user_id):
    data = load_data()
    for ch in data['settings']['channels']:
        try:
            res = bot.get_chat_member(ch, user_id).status
            if res in ['left', 'kicked']: return False
        except: continue
    return True

@bot.my_chat_member_handler()
def status_update(message: types.ChatMemberUpdated):
    data = load_data()
    user = message.from_user
    new = message.new_chat_member.status
    if new == "kicked":
        if user.id not in data['blocked_by']:
            data['blocked_by'].append(user.id)
            save_data(data)
            if data['settings']['notify_block']:
                secure_send(OWNER_ID, 'text', text=f"🚫 **مستخدم حظر البوت**\nالاسم: {user.first_name}\nالأيدي: `{user.id}`", parse_mode="Markdown")
    elif new == "member":
        if user.id in data['blocked_by']:
            data['blocked_by'].remove(user.id)
            save_data(data)
            if data['settings']['notify_unblock']:
                secure_send(OWNER_ID, 'text', text=f"🟢 **مستخدم فك الحظر**\nالاسم: {user.first_name}\nالأيدي: `{user.id}`", parse_mode="Markdown")

def main_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛡️ حماية المحتوى", callback_data="ui_protect"),
        types.InlineKeyboardButton("🔔 الإشعارات", callback_data="ui_notify"),
        types.InlineKeyboardButton("👥 المستخدمين", callback_data="ui_users"),
        types.InlineKeyboardButton("🔒 الاشتراك الإجباري", callback_data="ui_sub"),
        types.InlineKeyboardButton("📢 إذاعة", callback_data="ui_broadcast"),
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="ui_stats"),
        types.InlineKeyboardButton("🏠 رسالة الترحيب", callback_data="set_start")
    )
    return markup

def protect_kb():
    s = load_data()['settings']
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(f"حماية محتوى البوت : {'✅' if s['protect_content'] else '❌'}", callback_data="tg_protect_content"),
        types.InlineKeyboardButton(f"استثناء الوسائط : {'✅' if s['exclude_media'] else '❌'}", callback_data="tg_exclude_media"),
        types.InlineKeyboardButton(f"استثناء الروابط : {'✅' if s['exclude_links'] else '❌'}", callback_data="tg_exclude_links"),
        types.InlineKeyboardButton(f"استثناء النصوص : {'✅' if s['exclude_text'] else '❌'}", callback_data="tg_exclude_text"),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
    )
    return kb

def notify_kb():
    s = load_data()['settings']
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(f"إشعار الدخول : {'✅' if s['notify_new_user'] else '❌'}", callback_data="tg_notify_new_user"),
        types.InlineKeyboardButton(f"إشعار الحظر : {'✅' if s['notify_block'] else '❌'}", callback_data="tg_notify_block"),
        types.InlineKeyboardButton(f"إشعار فك الحظر : {'✅' if s['notify_unblock'] else '❌'}", callback_data="tg_notify_unblock"),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
    )
    return kb
@bot.message_handler(commands=['start'])
def cmd_start(message):
    data = load_data()
    uid = message.from_user.id
    if uid not in data['users']:
        data['users'].append(uid)
        save_data(data)
        if data['settings']['notify_new_user']:
            secure_send(OWNER_ID, 'text', text=f"🆕 مستخدم جديد: {message.from_user.first_name} (`{uid}`)")
    
    if not check_sub(uid):
        return secure_send(message.chat.id, 'text', text="⚠️ عذراً، يجب عليك الاشتراك في قنوات البوت أولاً.")
    
    secure_send(message.chat.id, 'text', text=data['settings']['start_msg'])

@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🍀 لوحة الإدارة الرئيسية:", reply_markup=main_kb())

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def tiktok_loader(message):
    data = load_data()
    uid = str(message.from_user.id)
    if uid in data['banned_users']: return
    if not check_sub(message.from_user.id): return

    wait = bot.reply_to(message, "⏳ جاري التحميل...")

    def process():
        try:
            url = [w for w in message.text.split() if 'tiktok.com' in w][0]
            res = requests.get(f"https://www.tikwm.com/api/?url={url}").json()
            if res.get('code') == 0:
                play = res['data']['play']
                v_url = play if play.startswith('http') else "https://www.tikwm.com" + play
                v_content = requests.get(v_url).content
                secure_send(message.chat.id, 'video', video=v_content)
                bot.delete_message(message.chat.id, wait.message_id)
                data['stats']['total_downloads'] += 1
                save_data(data)
            else:
                bot.edit_message_text("❌ فيديو غير صالح.", message.chat.id, wait.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ فني.", message.chat.id, wait.message_id)
    
    Thread(target=process).start()

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(c):
    data = load_data()
    if not is_admin(c.from_user.id): return

    if c.data == "ui_protect":
        bot.edit_message_text("🛡️ حماية المحتوى:", c.message.chat.id, c.message.message_id, reply_markup=protect_kb())
    elif c.data == "ui_notify":
        bot.edit_message_text("🔔 الإشعارات:", c.message.chat.id, c.message.message_id, reply_markup=notify_kb())
    elif c.data == "back_main":
        bot.edit_message_text("🍀 لوحة الإدارة الرئيسية:", c.message.chat.id, c.message.message_id, reply_markup=main_kb())
    
    elif c.data.startswith("tg_"):
        key = c.data.replace("tg_", "")
        data['settings'][key] = not data['settings'][key]
        save_data(data)
        kb = notify_kb() if "notify" in key else protect_kb()
        bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=kb)

    elif c.data == "ui_stats":
        msg = f"📊 الإحصائيات:\n- المستخدمين: {len(data['users'])}\n- التحميلات: {data['stats']['total_downloads']}\n- المحظورين: {len(data['blocked_by'])}"
        bot.answer_callback_query(c.id, msg, show_alert=True)

    elif c.data == "ui_broadcast":
        m = bot.send_message(c.message.chat.id, "📢 أرسل الإذاعة الآن:")
        bot.register_next_step_handler(m, run_broadcast)

    elif c.data == "ui_users":
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("📥 ملف المستخدمين", callback_data="get_user_file"),
            types.InlineKeyboardButton("🚫 حظر مستخدم", callback_data="ban_u"),
            types.InlineKeyboardButton("🟢 إلغاء حظر", callback_data="unban_u"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        )
        bot.edit_message_text("👥 إدارة المستخدمين:", c.message.chat.id, c.message.message_id, reply_markup=kb)

    elif c.data == "get_user_file":
        with open("users.txt", "w") as f: f.write("\n".join(map(str, data['users'])))
        bot.send_document(c.message.chat.id, open("users.txt", "rb"))

    elif c.data == "ui_sub":
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("➕ إضافة قناة", callback_data="add_ch"),
            types.InlineKeyboardButton("🗑️ مسح القنوات", callback_data="clear_ch"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        )
        bot.edit_message_text(f"🔒 الاشتراك الإجباري:\n{data['settings']['channels']}", c.message.chat.id, c.message.message_id, reply_markup=kb)

    elif c.data == "add_ch":
        m = bot.send_message(c.message.chat.id, "أرسل معرف القناة مع @:")
        bot.register_next_step_handler(m, save_channel)

    elif c.data == "set_start":
        m = bot.send_message(c.message.chat.id, "أرسل رسالة الترحيب الجديدة:")
        bot.register_next_step_handler(m, lambda msg: update_set(msg, 'start_msg'))

    elif c.data == "ban_u":
        m = bot.send_message(c.message.chat.id, "أرسل أيدي المستخدم لحظره:")
        bot.register_next_step_handler(m, ban_user_step)

    elif c.data == "unban_u":
        m = bot.send_message(c.message.chat.id, "أرسل أيدي المستخدم لفك حظره:")
        bot.register_next_step_handler(m, unban_user_step)

def save_channel(m):
    data = load_data()
    data['settings']['channels'].append(m.text)
    save_data(data)
    bot.reply_to(m, "✅ تم الإضافة.")

def update_set(m, key):
    data = load_data()
    data['settings'][key] = m.text
    save_data(data)
    bot.reply_to(m, "✅ تم التحديث.")

def ban_user_step(m):
    data = load_data()
    data['banned_users'][str(m.text)] = True
    save_data(data)
    bot.reply_to(m, "✅ تم الحظر.")

def unban_user_step(m):
    data = load_data()
    if str(m.text) in data['banned_users']:
        del data['banned_users'][str(m.text)]
        save_data(data)
        bot.reply_to(m, "✅ تم فك الحظر.")

def run_broadcast(m):
    data = load_data()
    for u in data['users']:
        try: bot.copy_message(u, m.chat.id, m.message_id)
        except: continue
    bot.send_message(m.chat.id, "✅ اكتملت الإذاعة.")

if __name__ == "__main__":
    bot.infinity_polling(allowed_updates=['message', 'callback_query', 'my_chat_member'])
