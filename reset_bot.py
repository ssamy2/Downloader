#!/usr/bin/env python3
"""
Reset bot - Delete webhook and restart
"""
import asyncio
from aiogram import Bot

async def reset_bot():
    token = "7824907627:AAGKWiS-fCIYlZPj6JGt3uwv9AD2J1L6meY"
    bot = Bot(token=token)
    
    try:
        # Delete webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ تم حذف webhook القديم")
        
        # Get bot info
        me = await bot.get_me()
        print(f"✅ البوت: @{me.username}")
        print(f"✅ المعرف: {me.id}")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(reset_bot())
