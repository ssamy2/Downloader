#!/usr/bin/env python3
"""
Automatic Setup Module for Telegram Downloader Bot
Checks dependencies, installs FFmpeg, and updates configuration
"""

import os
import sys
import subprocess
import platform
import shutil
import importlib.util
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} detected")
        print("📋 Requires Python 3.8 or higher")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def check_package(package_name):
    """Check if a Python package is installed"""
    spec = importlib.util.find_spec(package_name)
    return spec is not None

def install_package(package_name):
    """Install Python package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        return False

def install_dependencies():
    """Install required Python packages"""
    print("📦 Checking Python dependencies...")
    
    required_packages = [
        'aiogram>=3.13.0',
        'aiosqlite>=0.20.0', 
        'aiohttp>=3.10.0',
        'aiofiles>=24.1.0',
        'yt-dlp>=2024.11.18',
        'psutil>=6.1.0'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        package_name = package.split('>=')[0].split('==')[0]
        if not check_package(package_name):
            missing_packages.append(package)
        else:
            print(f"✅ {package_name} - OK")
    
    if missing_packages:
        print(f"📥 Installing missing packages: {', '.join(missing_packages)}")
        for package in missing_packages:
            if install_package(package):
                print(f"✅ {package} installed")
            else:
                print(f"❌ Failed to install {package}")
                return False
    
    return True

def check_ffmpeg():
    """Check if FFmpeg is installed and accessible"""
    return shutil.which('ffmpeg') is not None

def install_ffmpeg_windows():
    """Install FFmpeg on Windows (download if needed)"""
    print("🪟 Windows detected - checking for FFmpeg...")
    
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        print(f"✅ FFmpeg found at: {ffmpeg_path}")
        return ffmpeg_path
    
    # Check if FFmpeg directory exists in project
    ffmpeg_dir = Path('ffmpeg-8.0.1-essentials_build')
    if ffmpeg_dir.exists():
        ffmpeg_exe = ffmpeg_dir / 'bin' / 'ffmpeg.exe'
        if ffmpeg_exe.exists():
            print(f"✅ FFmpeg found in project: {ffmpeg_exe}")
            return str(ffmpeg_exe.absolute())
    
    print("❌ FFmpeg not found. Please download and extract FFmpeg to the project folder.")
    print("🔗 Download from: https://www.gyan.dev/ffmpeg/builds/")
    return None

def install_ffmpeg_linux():
    """Install FFmpeg on Linux"""
    print("🐧 Linux detected - installing FFmpeg...")
    
    try:
        # Try different package managers
        commands = [
            ['sudo', 'apt', 'install', '-y', 'ffmpeg'],  # Ubuntu/Debian
            ['sudo', 'yum', 'install', '-y', 'ffmpeg'],  # CentOS/RHEL
            ['sudo', 'dnf', 'install', '-y', 'ffmpeg'],  # Fedora
            ['sudo', 'pacman', '-S', '--noconfirm', 'ffmpeg'],  # Arch
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                print("✅ FFmpeg installed successfully")
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        else:
            print("❌ Could not install FFmpeg automatically")
            return None
        
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path
        
    except Exception as e:
        print(f"❌ Error installing FFmpeg: {e}")
        return None

def update_config_ffmpeg_path(ffmpeg_path):
    """Update FFmpeg path in config.py"""
    try:
        config_file = Path('config.py')
        if not config_file.exists():
            print("❌ config.py not found!")
            return False
        
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update FFmpeg path
        old_pattern = r'FFMPEG_PATH:\s*str\s*=\s*["\'][^"\']*["\']'
        new_line = f'FFMPEG_PATH: str = r"{ffmpeg_path}"'
        
        import re
        content = re.sub(old_pattern, new_line, content)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Updated FFmpeg path in config.py")
        return True
    except Exception as e:
        print(f"❌ Error updating config.py: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['downloads', 'logs']
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Created directory: {dir_name}")
        else:
            print(f"✅ Directory exists: {dir_name}")

def run_setup():
    """Run complete setup process"""
    print("🚀 Telegram Downloader Bot - Auto Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Install FFmpeg based on OS
    ffmpeg_path = None
    system = platform.system().lower()
    
    if system == 'windows':
        ffmpeg_path = install_ffmpeg_windows()
    elif system == 'linux':
        ffmpeg_path = install_ffmpeg_linux()
    else:
        print(f"⚠️  Unsupported OS: {system}")
        return False
    
    if not ffmpeg_path:
        print("❌ FFmpeg setup failed")
        return False
    
    # Update configuration
    if not update_config_ffmpeg_path(ffmpeg_path):
        print("⚠️  Could not update config.py automatically")
        print("🔧 Please manually set FFMPEG_PATH in config.py")
    
    # Create directories
    create_directories()
    
    print("\n🎉 Setup completed successfully!")
    print("=" * 30)
    print(f"📍 FFmpeg: {ffmpeg_path}")
    print("📚 Dependencies: Installed")
    print("📁 Directories: Created")
    print("🚀 Ready to start the bot!")
    
    return True

if __name__ == "__main__":
    success = run_setup()
    if not success:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ Setup completed! You can now run: python main.py")
