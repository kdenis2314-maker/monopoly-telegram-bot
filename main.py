import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message

# 1. Настройка логирования (DEBUG поможет увидеть, доходят ли сообщения)
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

# ТВОЙ ТОКЕН (лучше брать из env переменных)
TOKEN = "8265158957:AAHuRGxiA3XWFOf2N6Bzehk0L2PFJzYpJHI"

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Пример простого хендлера для проверки
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Бот-Монополия запущен и готов к игре!")

# Если у тебя есть другие файлы с хендлерами (routers), подключай их так:
# from handlers import game_router
# dp.include_router(game_router)

async def main():
    logging.info("Очистка вебхуков и запуск поллинга...")
    
    # ЭТО КЛЮЧЕВОЙ МОМЕНТ:
    # Удаляем вебхук, чтобы он не конфликтовал с поллингом
    # drop_pending_updates=True удаляет сообщения, присланные, пока бот был выключен
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск поллинга
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
            
