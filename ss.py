import os
import time
import yt_dlp
import telebot
import threading
from telebot import TeleBot

API_TOKEN = '6660174787:AAGbaGF7awASUUFLMJ3NnzKIPr5Kf-ADUkY'
bot = telebot.TeleBot(API_TOKEN)

@bot.callback_query_handler(func=lambda call: call.data == 'Back')
def start_command(call):
    name = f"[{call.from_user.first_name}](tg://user?id={call.from_user.id})"
    text = f'''
🤖 ¦ اهـلا بك عزيزي {name} انا بـوت التحميل
⚡️ ¦ اسـتـطـيـع تـحـمـيـل الفـيـديـوهـات و الـوسـيـقا
🎭 ¦ مـن جـمـيـع مـواقـع الـتـواصـل الاجـتـمـاعـي
    '''
    
    zeco = telebot.types.InlineKeyboardMarkup()
    video = telebot.types.InlineKeyboardButton("• فيديو MP4 •", callback_data="mp4")
    audio = telebot.types.InlineKeyboardButton("• صوت MP3 •", callback_data="mp3")
    zeco.add(video, audio)
    owner_button = telebot.types.InlineKeyboardButton("💼 حساب المالك", url="https://t.me/B_Y_B_Y")
    channel_button = telebot.types.InlineKeyboardButton("📢 قناة المطور", url="https://t.me/VIPCODE3")
    zeco.add(owner_button)
    zeco.add(channel_button)
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=zeco,parse_mode='Markdown')
    bot.clear_step_handler(call.message)
    
@bot.message_handler(commands=['start'])
def start_command(message):
    name = f"[{message.from_user.first_name}](tg://{message.from_user.id})"
    text = f'''
🤖 ¦ اهـلا بك عزيزي {name} انا بـوت التحميل
⚡️ ¦ اسـتـطـيـع تـحـمـيـل الفـيـديـوهـات و الـوسـيـقا
🎭 ¦ مـن جـمـيـع مـواقـع الـتـواصـل الاجـتـمـاعـي
    '''
    zeco = telebot.types.InlineKeyboardMarkup()
    video = telebot.types.InlineKeyboardButton("• فيديو MP4 •", callback_data="mp4")
    audio = telebot.types.InlineKeyboardButton("• صوت MP3 •", callback_data="mp3")
    zeco.add(video, audio)
    owner_button = telebot.types.InlineKeyboardButton("💼 حساب المالك", url="https://t.me/B_Y_B_Y")
    channel_button = telebot.types.InlineKeyboardButton("📢 قناة المطور", url="https://t.me/VIPCODE3")
    zeco.add(owner_button)
    zeco.add(channel_button)
    bot.reply_to(message,text, 
    reply_markup=zeco,
    parse_mode='Markdown'
    )
    
@bot.callback_query_handler(func=lambda call: call.data in ["mp4", "mp3"])
def ask_for_link(call):
    if call.data == 'mp4':
        text = '''
🤖 ¦ يـرجـى أدخـال رابـط الـفـيـديـو للـتـحـمـيـل
⛔️ ¦ لاحظ كلما زاد طول الفيديو زاد وقت انتظارك
        '''
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("• رجوع •", callback_data='Back'))
        zo1 = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)
        bot.register_next_step_handler(zo1, zo, call.data)

    elif call.data == 'mp3':
        text = '''
🤖 ¦ يـرجـى أدخـال رابـط الـصـوت للـتـحـمـيـل
⛔️ ¦ لاحظ كلما زاد طول الصوت زاد وقت انتظارك
        '''
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("• رجوع •", callback_data='Back'))
        zo1 = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)
        bot.register_next_step_handler(zo1, zo, call.data)

def zo(message, download_type):
    link = message.text
    name = f"[{message.from_user.first_name}](tg://{message.from_user.id})"
    
    if download_type == "mp4":
        ydl_opts = {
            'format': 'mp4',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'socket_timeout': 30,
        }
    else:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
        }

    status_message = bot.send_message(message.chat.id, "جاري البحث....")
    current_text = status_message.text

    def download_content():
        attempts = 3
        for attempt in range(attempts):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.add_progress_hook(lambda d: progress_hook(d, message.chat.id, status_message.message_id, current_text))
                    info_dict = ydl.extract_info(link, download=True)
                    
                    video_source = info_dict.get('extractor', 'مصدر غير معروف')
                    total_size = info_dict.get('filesize', None)
                    finished_file = ydl.prepare_filename(info_dict)
                    if total_size is None:
                        total_size = os.path.getsize(finished_file)
                    
                    file_size_kb = total_size / 1024 if total_size else 0
                    file_size = f"{file_size_kb:.0f} كيلوبايت" if file_size_kb < 1024 else f"{file_size_kb / 1024:.2f} ميغابايت" if total_size else "حجم الملف غير معروف"
                    
                    duration = info_dict.get('duration', 'غير معروف')
                    description = info_dict.get('description', 'لا يوجد وصف متاح')
                    extractor = info_dict.get('extractor', 'فيديو')
                    
                    with open(finished_file, 'rb') as file:
                        info_message = f'''عزيزي المستخدم {name} تم التحميل بنجاح
⌯ ⁞ الحجم : {file_size}
⌯ ⁞ الوقت  : {duration} ثانية
⌯ ⁞ المصدر : {video_source}
⌯ ⁞ الوصف : {description}'''

                        link_button = telebot.types.InlineKeyboardButton(text=extractor, url=link)
                        keyboard = telebot.types.InlineKeyboardMarkup().add(link_button)
                        
                        bot.send_document(message.chat.id, file, caption=info_message, reply_markup=keyboard,parse_mode='Markdown')

                    bot.delete_message(chat_id=message.chat.id, message_id=status_message.message_id)
                    
                    threading.Timer(30, os.remove, [finished_file]).start()
                    break
            except Exception as e:
                if attempt < attempts - 1:
                    time.sleep(5)
                else:
                    bot.send_message(message.chat.id, f"فشل التحميل بعد عدة محاولات:\n{str(e)}")
                    return
    download_content()
    threading.Thread(target=download_content).start()

def progress_hook(d, chat_id, message_id, current_text):
    if d['status'] == 'downloading':
        current_progress = d.get('downloaded_bytes', 0)
        total_size = d.get('total_bytes', 1)
        progress_percentage = (current_progress / total_size * 100)

        update_text = f"انتظر عزيزي... يتم التحميل {progress_percentage:.2f}%"

        if update_text != current_text:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=update_text)
            current_text = update_text
bot.polling()