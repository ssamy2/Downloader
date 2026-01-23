# 🚀 Auto-Setup Guide

## 🎯 التشغيل التلقائي (موصى به)

### الطريقة الأولى: تشغيل مباشر
```bash
python main.py
```
**البوت سيتحقق تلقائياً من جميع المتطلبات ويقوم بتثبيتها!**

### الطريقة الثانية: إعداد منفصل ثم تشغيل
```bash
python auto_setup.py
python main.py
```

### الطريقة الثالثة: تشغيل سريع
```bash
python quick_start.py
```

## 🔧 ما يقوم به الإعداد التلقائي

### 📦 تثبيت المكتبات
- ✅ aiogram >= 3.13.1
- ✅ aiosqlite >= 0.20.0
- ✅ aiohttp >= 3.10.10
- ✅ aiofiles >= 24.1.0
- ✅ yt-dlp >= 2024.11.18
- ✅ psutil >= 6.1.0

### 🎬 تثبيت FFmpeg
- **🐧 Linux**: `sudo apt install ffmpeg` (تلقائي)
- **🪟 Windows**: يبحث في مجلد المشروع
- **📱 macOS**: `brew install ffmpeg`

### ⚙️ الإعدادات التلقائية
- ✅ تحديث مسار FFmpeg في config.py
- ✅ إنشاء مجلدات downloads و logs
- ✅ التحقق من صلاحيات النظام

## 📋 خطوات التشغيل

### 1. تشغيل البوت (يتم الإعداد تلقائياً)
```bash
python main.py
```

### 2. انتظر الإعداد التلقائي
```
🔍 Checking dependencies...
✅ aiogram - OK
✅ aiosqlite - OK
❌ yt-dlp - Missing
📦 Installing missing packages: yt-dlp
✅ yt-dlp installed
✅ All dependencies ready!
```

### 3. البوت يبدأ العمل
```
2026-01-22 00:52:56,555 - __main__ - INFO - Bot starting up...
2026-01-22 00:52:56,560 - database - INFO - Database connected successfully
2026-01-22 00:52:57,721 - aiogram.dispatcher - INFO - Run polling for bot @XmetaPayRobot
```

## 🛠️ الملفات الجديدة

| الملف | الوصف |
|------|-------|
| **main.py** | محدث بالإعداد التلقائي |
| **auto_setup.py** | إعداد منفصل |
| **quick_start.py** | تشغيل سريع |
| **README_AUTO_SETUP.md** | هذا الدليل |

## ⚠️ ملاحظات مهمة

### Windows
- إذا لم يتم العثور على FFmpeg، سيبحث في `ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe`
- قم بتنزيل FFmpeg من [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

### Linux
- سيحاول تثبيت FFmpeg تلقائياً باستخدام `sudo apt install ffmpeg`
- يتطلب صلاحيات sudo

### macOS
- يجب تثبيت FFmpeg يدوياً: `brew install ffmpeg`

## 🚀 بعد التشغيل

1. **ابحث عن البوت**: `@XmetaPayRobot`
2. **أرسل**: `/start`
3. **جرب رابط**: `https://www.instagram.com/reel/DTvV6AHiLyK/`

## 🔧 استكشاف الأخطاء

### خطأ: ModuleNotFoundError
```bash
# الحل: تشغيل الإعداد التلقائي
python auto_setup.py
```

### خطأ: FFmpeg not found
```bash
# Linux:
sudo apt install ffmpeg

# Windows:
# قم بتنزيل FFmpeg ووضعه في مجلد المشروع
```

### خطأ: Permission denied
```bash
# Linux: استخدم sudo أو صلاحيات مناسبة
sudo python main.py
```

## 🎉 المميزات

- ✅ **إعداد تلقائي** كامل
- ✅ **تثبيت المكتبات** المفقودة
- ✅ **تكوين FFmpeg** تلقائياً
- ✅ **إنشاء المجلدات** اللازمة
- ✅ **دعم جميع الأنظمة**
- ✅ **تشغيل بأمر واحد**

**الآن البوت جاهز للعمل على أي نظام!** 🚀
