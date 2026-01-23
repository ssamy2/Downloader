# 🐧 Linux/Ubuntu Setup Guide

## 🚀 التثبيت التلقائي

### الطريقة الأولى: سكريبت Python (موصى به)

```bash
python3 setup_linux.py
```

### الطريقة الثانية: سكريبت Bash

```bash
chmod +x install_ffmpeg.sh
./install_ffmpeg.sh
```

## 📋 ما يقوم به السكريبت

### 🔍 اكتشاف النظام
- Ubuntu/Debian
- CentOS/RHEL
- Fedora
- Arch Linux
- openSUSE
- وتوزيعات Linux الأخرى

### 📦 تثبيت FFmpeg
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **CentOS/RHEL**: `sudo yum install ffmpeg`
- **Fedora**: `sudo dnf install ffmpeg`
- **Arch Linux**: `sudo pacman -S ffmpeg`
- **openSUSE**: `sudo zypper install ffmpeg`

### 🔧 إعدادات تلقائية
- ✅ إضافة FFmpeg إلى PATH
- ✅ تحديث مسار FFmpeg في config.py
- ✅ التحقق من التثبيت
- ✅ عرض معلومات الإصدار

## 🛠️ التثبيت اليدوي

### 1. تثبيت FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL:**
```bash
sudo yum install epel-release
sudo yum install ffmpeg
```

**Fedora:**
```bash
sudo dnf install ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S ffmpeg
```

### 2. تحديث config.py

```python
# ابحث عن هذا السطر
FFMPEG_PATH: str = "ffmpeg"

# واستبدله بالمسار الكامل
FFMPEG_PATH: str = "/usr/bin/ffmpeg"
```

### 3. التحقق من التثبيت

```bash
ffmpeg -version
which ffmpeg
```

## 📁 الملفات المطلوبة

- `setup_linux.py` - سكريبت الإعداد التلقائي (Python)
- `install_ffmpeg.sh` - سكريبت الإعداد (Bash)
- `config.py` - ملف الإعدادات (يتم تحديثه تلقائياً)

## 🎯 تشغيل البوت

بعد التثبيت:

```bash
# تثبيت المتطلبات
pip3 install -r requirements.txt

# تشغيل البوت
python3 main.py
```

## ⚠️ ملاحظات مهمة

1. **صلاحيات**: ستحتاج إلى صلاحيات sudo لتثبيت FFmpeg
2. **إعادة التشغيل**: أعد تشغيل التيرمنال بعد التثبيت
3. **PATH**: إذا لم يعمل، أعد تحميل PATH:
   ```bash
   source ~/.bashrc
   ```

## 🔧 استكشاف الأخطاء

### FFmpeg غير موجود
```bash
# تحقق من التثبيت
which ffmpeg

# إذا لم يوجد، أعد التثبيت
sudo apt install ffmpeg  # Ubuntu/Debian
```

### مشاكل الصلاحيات
```bash
# تأكد من صلاحيات sudo
sudo -v

# إذا لم يكن لديك sudo، استخدم تثبيت من المصدر
```

### مسار FFmpeg خاطئ
```bash
# ابحث عن المسار الصحيح
find / -name ffmpeg 2>/dev/null

# ثم حدث config.py بالمسار الصحيح
```

## 🎉 بعد التثبيت

- ✅ FFmpeg مثبت ومضاف إلى PATH
- ✅ config.py محدث بالمسار الصحيح
- ✅ البوت جاهز للعمل
- ✅ جميع المنصات المدعومة تعمل

**جرب البوت الآن!** 🚀
