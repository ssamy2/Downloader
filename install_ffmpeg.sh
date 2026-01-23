#!/bin/bash

# FFmpeg Auto-Installer for Linux/Ubuntu
# Automatically detects system and adds to PATH

set -e

echo "🎬 FFmpeg Auto-Installer for Linux/Ubuntu"
echo "=========================================="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    OS=$(uname -s)
    VER=$(uname -r)
fi

echo "🔍 Detected OS: $OS $VER"

# Install FFmpeg based on distribution
case "$OS" in
    "Ubuntu"* | "Debian"*)
        echo "📦 Installing FFmpeg on Ubuntu/Debian..."
        sudo apt update
        sudo apt install -y ffmpeg
        ;;
    "CentOS"* | "Red Hat"* | "Fedora"*)
        echo "📦 Installing FFmpeg on CentOS/RHEL/Fedora..."
        if command -v dnf &> /dev/null; then
            sudo dnf install -y epel-release
            sudo dnf install -y ffmpeg
        else
            sudo yum install -y epel-release
            sudo yum install -y ffmpeg
        fi
        ;;
    "Arch Linux"*)
        echo "📦 Installing FFmpeg on Arch Linux..."
        sudo pacman -S --noconfirm ffmpeg
        ;;
    "openSUSE"*)
        echo "📦 Installing FFmpeg on openSUSE..."
        sudo zypper install -y ffmpeg
        ;;
    *)
        echo "❌ Unsupported OS: $OS"
        echo "🔧 Please install FFmpeg manually:"
        echo "   Ubuntu/Debian: sudo apt install ffmpeg"
        echo "   CentOS/RHEL: sudo yum install ffmpeg"
        echo "   Fedora: sudo dnf install ffmpeg"
        exit 1
        ;;
esac

# Verify installation
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg installed successfully!"
    echo "📍 Location: $(which ffmpeg)"
    echo "📋 Version: $(ffmpeg -version | head -n 1)"
else
    echo "❌ FFmpeg installation failed!"
    exit 1
fi

# Add to PATH if not already there
FFMPEG_PATH=$(which ffmpeg)
FFMPEG_DIR=$(dirname "$FFMPEG_PATH")

if [[ ":$PATH:" != *":$FFMPEG_DIR:"* ]]; then
    echo "🔧 Adding FFmpeg to PATH..."
    
    # Add to .bashrc
    if [ -f "$HOME/.bashrc" ]; then
        echo "export PATH=\"\$PATH:$FFMPEG_DIR\"" >> "$HOME/.bashrc"
        echo "✅ Added to ~/.bashrc"
    fi
    
    # Add to .zshrc if exists
    if [ -f "$HOME/.zshrc" ]; then
        echo "export PATH=\"\$PATH:$FFMPEG_DIR\"" >> "$HOME/.zshrc"
        echo "✅ Added to ~/.zshrc"
    fi
    
    # Add to current session
    export PATH="$PATH:$FFMPEG_DIR"
    echo "✅ Added to current session"
else
    echo "✅ FFmpeg already in PATH"
fi

echo ""
echo "🎉 Installation completed!"
echo "🚀 Please restart your terminal or run: source ~/.bashrc"
echo "📍 FFmpeg path for config.py: $FFMPEG_PATH"
