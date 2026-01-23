"""Quick test for yt-dlp download"""
import yt_dlp
import os

url = 'https://youtube.com/shorts/ZRG6e6SZ_NQ'
ffmpeg_path = r"C:\Users\Sami\Desktop\Downloader\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
output_dir = 'downloads'
os.makedirs(output_dir, exist_ok=True)

# Clean old test files
for f in os.listdir(output_dir):
    if f.startswith('test_'):
        try:
            os.remove(os.path.join(output_dir, f))
        except:
            pass

print("Testing yt-dlp download...")

ydl_opts = {
    'format': 'best[ext=mp4][height<=720]/best[height<=720]/best[ext=mp4]/best',
    'outtmpl': f'{output_dir}/test_%(id)s.%(ext)s',
    'ffmpeg_location': ffmpeg_path,
    'quiet': False,
    'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        for f in os.listdir(output_dir):
            if f.startswith('test_'):
                path = os.path.join(output_dir, f)
                size = os.path.getsize(path)
                if size > 0:
                    print(f"\n✅ SUCCESS: {f} ({size/1024/1024:.2f} MB)")
                else:
                    print(f"\n❌ EMPTY FILE: {f}")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
