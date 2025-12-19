import asyncio
from aiogram import Bot

async def kill_zombie():
    # Твой токен
    bot = Bot(token="8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU")
    
    # 1. Принудительно удаляем вебхук и все накопившиеся сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    
    # 2. Сообщаем серверу, что мы закончили
    print("БОТ ПОЛНОСТЬЮ ОЧИЩЕН. ТЕПЕРЬ ОН МОЛЧИТ.")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(kill_zombie())
    
