#!/bin/bash

# Complete Linux Deployment Script for Telegram Downloader Bot

echo "🚀 Telegram Downloader Bot - Linux Deployment"
echo "============================================="

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Please don't run this script as root!"
    echo "   Use a regular user with sudo privileges."
    exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
sudo apt update || sudo yum update || sudo dnf update || echo "⚠️  Could not update packages"

# Install Python and pip if not exists
echo "🐍 Installing Python and pip..."
if ! command -v python3 &> /dev/null; then
    sudo apt install -y python3 python3-pip || \
    sudo yum install -y python3 python3-pip || \
    sudo dnf install -y python3 python3-pip
fi

# Install FFmpeg
echo "🎬 Installing FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg already installed"
else
    sudo apt install -y ffmpeg || \
    sudo yum install -y epel-release && sudo yum install -y ffmpeg || \
    sudo dnf install -y ffmpeg
fi

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip3 install -r requirements_linux.txt

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x setup_linux.py
chmod +x install_ffmpeg.sh

# Run automatic setup
echo "⚙️  Running automatic setup..."
python3 setup_linux.py

# Create systemd service (optional)
read -p "🤖 Create systemd service for auto-start? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_NAME="telegram-downloader"
    SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
    CURRENT_DIR=$(pwd)
    
    echo "🔧 Creating systemd service..."
    sudo tee $SERVICE_PATH > /dev/null <<EOF
[Unit]
Description=Telegram Downloader Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    echo "✅ Service created and enabled!"
    echo "🚀 Start with: sudo systemctl start $SERVICE_NAME"
    echo "📊 Check status: sudo systemctl status $SERVICE_NAME"
fi

echo ""
echo "🎉 Deployment completed!"
echo "========================"
echo "📍 Current directory: $(pwd)"
echo "🐍 Start bot: python3 main.py"
echo "📋 Check logs: tail -f bot.log"
echo ""
echo "🎯 Test the bot:"
echo "   1. Send /start to @XmetaPayRobot"
echo "   2. Try a link: https://www.instagram.com/reel/DTvV6AHiLyK/"
