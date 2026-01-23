# 🔧 إصلاح مشكلة التحميل من YouTube - ملخص نهائي

## 🔍 المشكلة الأصلية
```
ERROR: [youtube] ZRG6e6SZ_NQ: Requested format is not available
WARNING: nsig extraction failed: Some formats may be missing
```

## 🎯 السبب الحقيقي

بعد قراءة **Cobalt source code** والبحث في **yt-dlp GitHub issues**، تم اكتشاف:

### 1. yt-dlp قديم
- **الإصدار القديم:** 2024.11.18
- **الإصدار المطلوب:** 2025.11.12+

### 2. متطلبات جديدة من YouTube
منذ إصدار yt-dlp 2025.11.12، أصبح **JavaScript runtime** مطلوباً لدعم YouTube بالكامل.

المصدر: [yt-dlp Issue #15012](https://github.com/yt-dlp/yt-dlp/issues/15012)

## ✅ الحلول المطبقة

### 1. تحديث yt-dlp
```bash
pip install --upgrade yt-dlp
# تم التحديث إلى: 2025.12.8
```

### 2. إضافة دعم Node.js في downloader.py
```python
ydl_opts = {
    # ... other options ...
    'ffmpeg_location': config.FFMPEG_PATH,
    'postprocessors': [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',
    }],
    # Enable Node.js runtime for YouTube
    'extractor_args': {'youtube': {'js_runtime': ['nodejs']}},
}
```

### 3. Format Selection محسّن
```python
quality_map = {
    '144p': 144, '240p': 240, '360p': 360, '480p': 480,
    'standard': 480, '720p': 720, 'hd': 720, '1080p': 1080,
    '1440p': 1440, '2160p': 2160, '4k': 2160, 'original': 9999
}

# استخدام bestvideo+bestaudio مع fallback
ydl_opts['format'] = f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best'
ydl_opts['merge_output_format'] = 'mp4'
```

## 📋 المتطلبات الجديدة

للتحميل من YouTube، يجب توفر:

| المتطلب | الإصدار المطلوب | الحالة |
|---------|----------------|--------|
| yt-dlp | 2025.11.12+ | ✅ 2025.12.8 |
| Node.js | 20.0.0+ (يفضل 25+) | ✅ v25.2.1 |
| FFmpeg | أي إصدار حديث | ✅ 8.0.1 |

## 🧪 نتيجة الاختبار

```
Testing download with FFmpeg merging...
FFmpeg path: C:\...\ffmpeg.exe
FFmpeg exists: True

[youtube] ZRG6e6SZ_NQ: Downloading webpage 
[info] ZRG6e6SZ_NQ: Downloading 1 format(s): 243+251 
[download] 100% of 1.45MiB
[Merger] Merging formats into "test_video.mp4" 

✅ SUCCESS!
Title: فيه زيادة في اسعار الموبايلات...
Duration: 65s
File: test_video.mp4 (2.29 MB)
```

## 📝 ملاحظات مهمة

### Cobalt API
- **Cobalt v7 API** تم إيقافه في نوفمبر 2024
- يمكن استضافة Cobalt محلياً للاستخدام
- مصدر Cobalt: `C:\Users\Sami\Desktop\cobalt-main`

### JavaScript Runtimes المدعومة (بترتيب الأفضلية)
1. **Deno** (الأفضل) - مفعّل افتراضياً
2. **Node.js** (جيد) - يحتاج تفعيل
3. **QuickJS** (بديل)
4. **Bun** (بديل)

## 🚀 الخطوات للتشغيل

```bash
# 1. تأكد من تحديث yt-dlp
pip install --upgrade yt-dlp

# 2. تأكد من وجود Node.js
node --version  # يجب أن يكون 20.0.0+

# 3. شغّل البوت
py main.py
```

## 📊 الملفات المعدّلة

| الملف | التعديل |
|-------|---------|
| `downloader.py` | إضافة FFmpeg path + Node.js runtime + format selection محسّن |
| `config.py` | تحديث رسائل الجودة |
| `main.py` | تحسين واجهة اختيار الجودة |

---
**تاريخ الإصلاح:** 2026-01-22
**yt-dlp version:** 2025.12.8
**Node.js version:** v25.2.1
