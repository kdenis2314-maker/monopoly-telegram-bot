import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# 1. Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# --- ТВОИ ДАННЫЕ ---
TOKEN = "8265158957:AAHuRGxiA3XWFOf2N6Bzehk0L2PFJzYpJHI"  # Вставь свой токен сюда
PORT = 8082  # Порт, который ты выбрал

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- СЕРВЕР-ЗАГЛУШКА ДЛЯ RENDER ---
async def handle_health_check(request):
    return web.Response(text="Бот онлайн!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    logging.info(f"--- Сервер проверки запущен на порту {PORT} ---")
    await site.start()

# --- ХЕНДЛЕРЫ БОТА ---
@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer("Привет! Я бот-монополия. Теперь я работаю стабильно на Render!")

# --- ГЛАВНЫЙ ЗАПУСК ---
async def main():
    # Запускаем веб-сервер в фоновом потоке
    asyncio.create_task(start_web_server())
    
    # Принудительно удаляем старые вебхуки, чтобы работал поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info("--- Бот начинает опрос (polling) ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот выключен")
        
