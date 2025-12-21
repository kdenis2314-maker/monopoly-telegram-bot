import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher
import aiosqlite

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получение токена
API_TOKEN = os.environ.get("BOT_TOKEN")
if not API_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    exit(1)

# Инициализация Flask
app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8083))

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Простые маршруты Flask
@app.route('/')
def home():
    return "✅ Monopoly Premium Bot is running!"

@app.route('/health')
def health():
    return {"status": "ok", "bot": "running"}, 200

@app.route('/stats')
def stats():
    return {"active": True, "version": "Premium v2.0"}

# Простая команда бота
from aiogram.filters import Command
from aiogram.types import Message

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🎮 Monopoly Premium Bot запущен!\nИспользуйте /monopoly для начала игры.")

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: Message):
    await message.answer("🎲 Начинаем игру в Монополию!")

# Функция запуска бота в отдельном потоке
async def start_bot():
    try:
        logger.info("🚀 Запуск Telegram бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}")

def run_bot_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

# Основная функция запуска
def main():
    logger.info(f"🌐 Запуск Flask сервера на порту {PORT}")
    
    # Запуск бота в отдельном потоке
    bot_thread = Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()
    logger.info("🤖 Telegram бот запущен в отдельном потоке")
    
    # Запуск Flask
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == "__main__":
    main()