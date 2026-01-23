# 🎬 Telegram Media Downloader Bot

بوت تليجرام عالي الأداء لتحميل الفيديوهات من منصات متعددة بدون علامة مائية.

## ✨ المميزات

- **تحميل بدون علامة مائية** من Instagram, TikTok, YouTube, Twitter, Kwai
- **اختيار الجودة** (Standard/HD/Original)
- **دعم الروابط المتعددة** في رسالة واحدة
- **ضغط تلقائي** للفيديوهات الكبيرة
- **نظام حدود يومية** (15 تحميل/يوم)
- **اشتراك إجباري** في قنوات محددة
- **لوحة تحكم للمسؤولين** متكاملة
- **حذف تلقائي** للملفات بعد 15 دقيقة

## 🛠 المتطلبات

- Python 3.10+
- FFmpeg (للضغط وتحويل الصيغ)
- اتصال إنترنت مستقر

## 📦 التثبيت

### 1. استنساخ المشروع
```bash
git clone <repository>
cd Downloader
```

### 2. إنشاء بيئة افتراضية
```bash
py -m venv venv
venv\Scripts\activate  # Windows
# أو
source venv/bin/activate  # Linux/Mac
```

### 3. تثبيت المتطلبات
```bash
pip install -r requirements.txt
```

### 4. تثبيت FFmpeg
- **Windows**: قم بتحميل من [ffmpeg.org](https://ffmpeg.org/download.html) وأضفه إلى PATH
- **Linux**: `sudo apt install ffmpeg`
- **Mac**: `brew install ffmpeg`

### 5. تكوين البوت
افتح `config.py` وقم بتعديل:
```python
TOKEN = "YOUR_BOT_TOKEN"
PRIMARY_OWNER_ID = YOUR_TELEGRAM_ID  # معرفك في تليجرام
```

### 6. تشغيل البوت
```bash
py main.py
```

## 📁 هيكل المشروع

```
Downloader/
├── main.py              # نقطة الدخول الرئيسية
├── config.py            # الإعدادات والرسائل
├── database.py          # معالجات قاعدة البيانات
├── downloader.py        # منطق التحميل (Cobalt + yt-dlp)
├── admin_handlers.py    # لوحة التحكم والبث
├── requirements.txt     # المتطلبات
├── bot_database.db      # قاعدة البيانات (تُنشأ تلقائياً)
├── downloads/           # مجلد التحميلات المؤقتة
└── bot.log             # سجل الأخطاء
```

## 👑 صلاحيات المسؤولين

| الصلاحية | المالك الأساسي | المالك الثانوي | المسؤول |
|----------|---------------|----------------|---------|
| إدارة المسؤولين | ✅ | ❌ | ❌ |
| البث للجميع | ✅ | ✅ | ❌ |
| إعادة تعيين الحدود | ✅ | ✅ | ❌ |
| حظر/إلغاء حظر | ✅ | ✅ | ✅ |
| عرض الإحصائيات | ✅ | ✅ | ✅ |
| إدارة القنوات | ✅ | ✅ | ❌ |

## 🤖 أوامر البوت

### أوامر المستخدم
- `/start` - بدء البوت
- `/help` - دليل الاستخدام

### أوامر المسؤولين
- `/admin` - لوحة التحكم
- `/stats` - الإحصائيات
- `/broadcast` - بث رسالة
- `/ban [user_id]` - حظر مستخدم
- `/unban [user_id]` - إلغاء الحظر
- `/reset_limit [user_id]` - إعادة تعيين الحد

### أوامر المالك فقط
- `/add_admin [user_id]` - إضافة مسؤول
- `/remove_admin [user_id]` - إزالة مسؤول
- `/add_owner [user_id]` - إضافة مالك ثانوي
- `/remove_owner [user_id]` - إزالة مالك ثانوي

## 🔗 المنصات المدعومة

| المنصة | النوع | المحمل |
|--------|-------|--------|
| Instagram | Reels, Stories, Posts | Cobalt |
| TikTok | Videos | Cobalt |
| YouTube | Videos, Shorts | Cobalt |
| Twitter/X | Videos | Cobalt |
| Kwai | Videos | yt-dlp |

## ⚠️ ملاحظات مهمة

1. **حد التحميل**: 15 تحميل يومياً لكل مستخدم
2. **فترة الانتظار**: 5 ثواني بين كل طلب
3. **حجم الملف**: الحد الأقصى 50MB (حد تليجرام)
4. **حذف الملفات**: تُحذف تلقائياً بعد 15 دقيقة
5. **Cobalt API**: يُستخدم كمحمل أساسي، yt-dlp كاحتياطي

## 🐛 استكشاف الأخطاء

### الخطأ: "ffmpeg not found"
تأكد من تثبيت FFmpeg وإضافته إلى متغير PATH

### الخطأ: "Connection timeout"
- تحقق من اتصال الإنترنت
- قد يكون Cobalt API غير متاح مؤقتاً

### الخطأ: "Private content"
المحتوى خاص أو محذوف من المنصة الأصلية

## 📄 الترخيص

MIT License - للاستخدام الشخصي والتجاري

---
تم التطوير بـ ❤️ باستخدام Python & aiogram 3.x
