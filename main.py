import asyncio, os, random, logging
from flask import Flask, render_template_string
from threading import Thread
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramConflictError

# --- ЛОГИРОВАНИЕ ДЛЯ САЙТА ---
logs_list = []
def add_log(text):
    time_str = datetime.now().strftime("%H:%M:%S")
    logs_list.append(f"[{time_str}] {text}")
    if len(logs_list) > 15: logs_list.pop(0)

# --- 1. ВСТАВЬ НОВЫЙ ТОКЕН СЮДА ---
TOKEN = "8265158957:AAF47AzlevRoyn7CLOMHkB7HsxQu5MUdpSg"
PORT = int(os.environ.get("PORT", 10000))

# --- 2. ВЕБ-САЙТ ---
app = Flask(__name__)
@app.route('/')
def index():
    # Страница с логами для отладки в реальном времени
    return render_template_string("""
    <html><body style="background:#121212;color:#0f0;font-family:monospace;padding:20px;">
    <h2>🔗 Monopoly Debug Panel</h2>
    <div style="border:1px solid #333;padding:10px;background:#000;">
    {% for log in logs %}<p style="margin:2px;">{{ log }}</p>{% endfor %}
    </div>
    <script>setTimeout(() => { location.reload(); }, 3000);</script>
    </body></html>
    """, logs=logs_list[::-1])

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- 3. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def start_cmd(m: Message):
    add_log(f"✅ Получена команда от {m.from_user.first_name}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Сбор игроков", callback_query_data="l_start")]])
    await m.answer("🏨 **MONOPOLY ONLINE**\nБот работает!", reply_markup=kb)

# --- 4. ЗАПУСК С ЗАЩИТОЙ ---
async def main():
    Thread(target=run_flask, daemon=True).start()
    
    # Цикл для перезапуска при конфликте
    while True:
        try:
            add_log("🔄 Попытка подключения к Telegram...")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        except TelegramConflictError:
            add_log("⚠️ Конфликт! Кто-то еще использует токен. Рестарт через 5 сек...")
            await asyncio.sleep(5)
        except Exception as e:
            add_log(f"❌ Ошибка: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
    
