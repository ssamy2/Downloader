#!/usr/bin/env python3
"""
Quick Start Script - One command setup and run
"""

import sys
import subprocess
import os

def main():
    print("🚀 Telegram Downloader Bot - Quick Start")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('main.py'):
        print("❌ main.py not found. Please run this script from the project directory.")
        sys.exit(1)
    
    # Option 1: Run auto-setup first
    if not os.path.exists('auto_setup.py'):
        print("❌ auto_setup.py not found!")
        sys.exit(1)
    
    print("🔧 Running automatic setup...")
    try:
        result = subprocess.run([sys.executable, 'auto_setup.py'], 
                              capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Setup failed: {e}")
        print(e.stderr)
        sys.exit(1)
    
    print("\n🤖 Starting the bot...")
    print("=" * 30)
    
    # Start the bot
    try:
        subprocess.run([sys.executable, 'main.py'])
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
