#!/usr/bin/env python3
"""
Linux/Ubuntu Setup Script for Telegram Downloader Bot
Automatically detects system, installs FFmpeg, and updates config
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def run_command(cmd, check=True):
    """Run shell command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stdout.strip(), e.stderr.strip()

def detect_system():
    """Detect Linux distribution"""
    try:
        with open('/etc/os-release', 'r') as f:
            lines = f.readlines()
        
        os_info = {}
        for line in lines:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                os_info[key.strip().lower()] = value.strip('"')
        
        return os_info.get('name', 'Unknown'), os_info.get('version_id', 'Unknown')
    except:
        return platform.system(), platform.release()

def install_ffmpeg(distro):
    """Install FFmpeg based on distribution"""
    commands = {
        'ubuntu': 'sudo apt update && sudo apt install -y ffmpeg',
        'debian': 'sudo apt update && sudo apt install -y ffmpeg',
        'centos': 'sudo yum install -y epel-release && sudo yum install -y ffmpeg',
        'rhel': 'sudo yum install -y epel-release && sudo yum install -y ffmpeg',
        'fedora': 'sudo dnf install -y ffmpeg',
        'arch': 'sudo pacman -S --noconfirm ffmpeg',
        'opensuse': 'sudo zypper install -y ffmpeg'
    }
    
    distro_lower = distro.lower()
    for key, cmd in commands.items():
        if key in distro_lower:
            print(f"📦 Installing FFmpeg on {distro}...")
            success, stdout, stderr = run_command(cmd)
            return success, stdout, stderr
    
    return False, "", f"Unsupported distribution: {distro}"

def get_ffmpeg_path():
    """Get FFmpeg executable path"""
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    return None

def update_config_ffmpeg_path(ffmpeg_path):
    """Update FFmpeg path in config.py"""
    config_file = Path('config.py')
    if not config_file.exists():
        print("❌ config.py not found!")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update FFmpeg path
        old_line = 'FFMPEG_PATH: str = "ffmpeg"'
        new_line = f'FFMPEG_PATH: str = r"{ffmpeg_path}"'
        
        if old_line in content:
            content = content.replace(old_line, new_line)
        else:
            # Try to find any FFMPEG_PATH line
            import re
            pattern = r'FFMPEG_PATH:\s*str\s*=\s*["\'][^"\']*["\']'
            content = re.sub(pattern, new_line, content)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Updated FFmpeg path in config.py: {ffmpeg_path}")
        return True
    except Exception as e:
        print(f"❌ Error updating config.py: {e}")
        return False

def add_to_path(ffmpeg_dir):
    """Add FFmpeg directory to PATH"""
    bashrc = Path.home() / '.bashrc'
    zshrc = Path.home() / '.zshrc'
    
    path_line = f'export PATH="$PATH:{ffmpeg_dir}"'
    
    # Add to .bashrc
    if bashrc.exists():
        with open(bashrc, 'r') as f:
            bashrc_content = f.read()
        
        if path_line not in bashrc_content:
            with open(bashrc, 'a') as f:
                f.write(f'\n# FFmpeg Auto-Added\n{path_line}\n')
            print("✅ Added to ~/.bashrc")
    
    # Add to .zshrc
    if zshrc.exists():
        with open(zshrc, 'r') as f:
            zshrc_content = f.read()
        
        if path_line not in zshrc_content:
            with open(zshrc, 'a') as f:
                f.write(f'\n# FFmpeg Auto-Added\n{path_line}\n')
            print("✅ Added to ~/.zshrc")
    
    # Add to current session
    os.environ['PATH'] = f"{os.environ.get('PATH', '')}:{ffmpeg_dir}"
    print("✅ Added to current session")

def main():
    print("🎬 Linux/Ubuntu Setup for Telegram Downloader Bot")
    print("=" * 50)
    
    # Detect system
    distro, version = detect_system()
    print(f"🔍 Detected System: {distro} {version}")
    
    if 'linux' not in platform.system().lower():
        print("❌ This script is for Linux systems only!")
        sys.exit(1)
    
    # Install FFmpeg
    print("\n📦 Installing FFmpeg...")
    success, stdout, stderr = install_ffmpeg(distro)
    
    if not success:
        print(f"❌ Failed to install FFmpeg: {stderr}")
        print("🔧 Please install manually:")
        print("   Ubuntu/Debian: sudo apt install ffmpeg")
        print("   CentOS/RHEL: sudo yum install ffmpeg")
        print("   Fedora: sudo dnf install ffmpeg")
        sys.exit(1)
    
    print("✅ FFmpeg installed successfully!")
    
    # Get FFmpeg path
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("❌ FFmpeg not found in PATH!")
        sys.exit(1)
    
    print(f"📍 FFmpeg Location: {ffmpeg_path}")
    
    # Get version
    success, version_out, _ = run_command(f"{ffmpeg_path} -version")
    if success:
        first_line = version_out.split('\n')[0]
        print(f"📋 Version: {first_line}")
    
    # Add to PATH
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    add_to_path(ffmpeg_dir)
    
    # Update config
    print("\n🔧 Updating config.py...")
    if update_config_ffmpeg_path(ffmpeg_path):
        print("✅ Configuration updated!")
    else:
        print("⚠️  Please manually update FFMPEG_PATH in config.py")
    
    print("\n🎉 Setup completed successfully!")
    print("🚀 Please restart your terminal or run: source ~/.bashrc")
    print("🤖 You can now start the bot with: python3 main.py")

if __name__ == "__main__":
    main()
