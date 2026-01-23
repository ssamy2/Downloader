# دليل الدخول للسيرفر وإدارة الكوكيز

## 1️⃣ الدخول للسيرفر عبر SSH

### على Windows (استخدم PowerShell أو Git Bash):

```bash
# الدخول الأساسي
ssh sami@srv1276359

# إذا كنت تستخدم مفتاح SSH
ssh -i C:\path\to\private_key sami@srv1276359

# إذا كان لديك كلمة مرور
# ستُطلب منك إدخال كلمة المرور بعد الأمر
```

### على macOS/Linux:

```bash
ssh sami@srv1276359
```

---

## 2️⃣ بعد الدخول للسيرفر

```bash
# الانتقال لمجلد المشروع
cd ~/Downloader

# تحديث الكود من GitHub
git pull origin master

# تثبيت المتطلبات
pip install -r requirements.txt

# تشغيل البوت
python main.py
```

---

## 3️⃣ إدارة الكوكيز التلقائية

### الملفات المتعلقة:
- `cookies.txt` - ملف الكوكيز (Netscape format)
- `cookie_manager.py` - مدير الكوكيز التلقائي

### كيفية إضافة الكوكيز:

#### الطريقة 1: من المتصفح (الأسهل)

```bash
# على جهازك المحلي:
# 1. افتح Firefox
# 2. اذهب إلى https://www.instagram.com
# 3. سجل الدخول بحسابك
# 4. استخدم yt-dlp لاستخراج الكوكيز:

yt-dlp --cookies-from-browser firefox --cookies cookies.txt "https://www.instagram.com" --skip-download

# 5. انسخ ملف cookies.txt للسيرفر:
scp cookies.txt sami@srv1276359:~/Downloader/
```

#### الطريقة 2: عبر السيرفر مباشرة

```bash
# على السيرفر:
cd ~/Downloader

# إذا كان لديك Firefox على السيرفر:
yt-dlp --cookies-from-browser firefox --cookies cookies.txt "https://www.instagram.com" --skip-download

# أو إنشاء ملف cookies.txt يدويًا:
cat > cookies.txt << 'EOF'
# Netscape HTTP Cookie File
# This is a generated file!  Do not edit.

.instagram.com	TRUE	/	TRUE	9999999999	sessionid	YOUR_SESSION_ID_HERE
.instagram.com	TRUE	/	TRUE	9999999999	csrftoken	YOUR_CSRF_TOKEN_HERE
EOF
```

---

## 4️⃣ نظام تحديث الكوكيز التلقائي

### كيف يعمل:

```python
# يتحقق تلقائياً من صلاحية الكوكيز
# إذا انتهت الصلاحية، يحاول تحديثها
# يحفظ الكوكيز الجديدة تلقائياً
```

### المراقبة:

```bash
# عرض سجل الكوكيز
tail -f ~/Downloader/logs/cookie_manager.log

# التحقق من صلاحية الكوكيز الحالية
python -c "from cookie_manager import CookieManager; cm = CookieManager(); print(cm.get_cookie_status())"
```

---

## 5️⃣ استكشاف الأخطاء

### المشكلة: "403 Forbidden"

```bash
# تحقق من الكوكيز
ls -la ~/Downloader/cookies.txt

# إذا لم يكن الملف موجوداً:
echo "الكوكيز غير موجود - أضفه من المتصفح"

# إذا كان موجوداً:
# قد تكون الكوكيز منتهية الصلاحية - جدّدها
```

### المشكلة: "Rate Limited"

```bash
# انتظر 30 دقيقة ثم حاول مرة أخرى
# أو استخدم Cobalt API (لا يحتاج كوكيز)
```

---

## 6️⃣ الأوامر المفيدة

```bash
# عرض حالة البوت
ps aux | grep main.py

# إيقاف البوت
pkill -f main.py

# إعادة تشغيل البوت
cd ~/Downloader && python main.py &

# عرض السجلات
tail -f ~/Downloader/logs/bot.log

# تحديث الكود والبوت
cd ~/Downloader && git pull && python main.py &
```

---

## 7️⃣ الخلاصة

| المهمة | الأمر |
|-------|-------|
| الدخول | `ssh sami@srv1276359` |
| تحديث الكود | `cd ~/Downloader && git pull` |
| إضافة كوكيز | `scp cookies.txt sami@srv1276359:~/Downloader/` |
| تشغيل البوت | `python main.py` |
| مراقبة السجلات | `tail -f logs/bot.log` |

---

## ⚠️ ملاحظات أمان

- ✅ لا تشارك كلمة المرور مع أحد
- ✅ لا تضع الكوكيز في GitHub (موجود في .gitignore)
- ✅ استخدم SSH keys بدلاً من كلمات المرور إن أمكن
- ✅ غيّر كلمة المرور بانتظام

---

**تم! الآن أنت جاهز للدخول للسيرفر وإدارة الكوكيز!** 🚀
