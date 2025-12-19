import asyncio, os, time, random
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties

# --- КОНФИГ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))
CORE_ID = random.randint(1000, 9999) 

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)
@app.route('/')
def home():
    return f"СИСТЕМА РАБОТАЕТ | ID ЯДРА: {CORE_ID}"

# --- ЛОГИКА ---
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
    dp = Dispatcher()

    # Очистка очереди сообщений
    await bot.delete_webhook(drop_pending_updates=True)

    @dp.message()
    async def handle(msg: types.Message):
        if msg.text == "/start":
            await msg.answer(f"✅ **НОВАЯ СЕССИЯ ЗАПУЩЕНА**\nID Ядра: `{CORE_ID}`\n\nСтатус: Чистая установка.")

    # Запуск Flask в отдельном потоке
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    
    print(f"--- БОТ ЗАПУЩЕН (ID: {CORE_ID}) ---")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        pass
