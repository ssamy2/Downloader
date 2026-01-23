import asyncio
from aiogram import Bot

async def delete_webhook():
    bot = Bot(token="7824907627:AAGKWiS-fCIYlZPj6JGt3uwv9AD2J1L6meY")
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deleted successfully!")
    await bot.session.close()

asyncio.run(delete_webhook())
