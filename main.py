import os
import asyncio
import random
from threading import Thread
from flask import Flask, request, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import init_db, add_player, add_chat

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN")
# Если BOT_TOKEN не задан в Render, бот выдаст ошибку при запуске
if not TOKEN:
    raise ValueError("ОШИБКА: BOT_TOKEN не установлен в Environment Variables!")

DEV_ID = "@Whylovely05"
START_DATE = "21.12.2025"
PORT = int(os.environ.get("PORT", 8083)) # Тот самый порт 8083

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Детальная карта (список)
MAP_DATA = [
    "🚀 СТАРТ", "🏠 Житная", "🎁 Казна", "🏠 Нагатинская", "💰 Налог",
    "🚂 Рижская ж/д", "🏠 Варшавское", "❓ Шанс", "🏠 Огородный", "🏠 Парковая",
    "⚖️ Тюрьма", "🏠 Полянка", "⚡ Электро", "🏠 Сретенка", "🏠 Ростовская",
    "🚂 Курская ж/д", "🏠 Рязанский", "🎁 Казна", "🏠 Вавилова", "🏠 Тверская",
    "🎡 Отдых", "🏠 Щусева", "❓ Шанс", "🏠 Гоголевский", "🏠 Кутузовский"
]

# --- ЛОГИКА БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type != 'private': return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить в группу", 
           url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"))
    
    text = (f"🤖 **Monopoly Killer Elite**\n\n"
            f"📅 Запуск: {START_DATE}\n"
            f"👨‍💻 Создатель: {DEV_ID}\n"
            f"⚡ Порт сервера: {PORT}\n"
            f"✅ Статус: Online\n\n"
            f"📍 *Добавь меня в чат, чтобы начать разнос!*")
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if message.chat.type == 'private': return
    # Сохраняем чат в базу для тролль-меню
    add_chat(message.chat.id, message.chat.title)
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 Начать сбор", callback_data="lobby"))
    kb.row(types.InlineKeyboardButton(text="🙈 Скрыть меню", callback_data="hide_ui"))
    await message.answer(f"📦 **Хаб управления чатом {message.chat.title}**", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "lobby")
async def lobby(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Вступить", callback_data="join"))
    kb.row(types.InlineKeyboardButton(text="🚀 СТАРТ", callback_data="start_game"))
    await call.message.edit_text("⏳ **Ожидание игроков...**\nМинимум: 2 игрока.", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "hide_ui")
async def hide_ui(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer("Меню скрыто 🙈")

# --- МОБИЛЬНАЯ АДМИНКА (ТРОЛЛЬ-МЕНЮ) ---

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #121212; color: #eee; font-family: sans-serif; padding: 20px; }
        .card { background: #1e1e1e; border: 1px solid #333; padding: 20px; border-radius: 12px; }
        input, textarea { width: 100%; padding: 12px; margin: 10px 0; background: #222; border: 1px solid #444; color: white; border-radius: 6px; }
        button { width: 100%; padding: 15px; background: #ff3b3b; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
        .info { color: #00ff00; font-size: 0.9em; }
    </style>
</head>
<body>
    <h2>😈 KILLER CONTROL</h2>
    <div class="card">
        <p class="info">● Сервер активен на порту {{ port }}</p>
        <p>Разработчик: {{ dev }}</p>
        <hr style="border: 0.5px solid #333">
        <h3>💬 ТРОЛЛЬ-МЕНЮ</h3>
        <form method="POST" action="/troll">
            <input name="chat_id" placeholder="ID Группы (например, -100...)" required>
            <textarea name="msg" placeholder="Текст сообщения от бота..." required></textarea>
            <button type="submit">ОТПРАВИТЬ В ЧАТ</button>
        </form>
    </div>
</body>
</html>
'''

@app.route('/')
def admin_page():
    return render_template_string(HTML_TEMPLATE, port=PORT, dev=DEV_ID)

@app.route('/troll', methods=['POST'])
def troll_action():
    chat_id = request.form.get('chat_id')
    msg = request.form.get('msg')
    # Отправляем сообщение асинхронно через поток бота
    asyncio.run_coroutine_threadsafe(bot.send_message(chat_id, f"📢 {msg}"), asyncio.get_event_loop())
    return "🔥 Послание отправлено! <a href='/' style='color:white;'>Назад</a>"

# --- СИСТЕМА ЗАПУСКА ---

def run_flask():
    # Flask будет слушать порт 8083 (или тот, что в PORT)
    app.run(host="0.0.0.0", port=PORT)

async def main_bot():
    init_db()
    # Запуск веб-сервера в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
    
    print(f"✅ Сервер Flask на порту {PORT} запущен")
    print("✅ Бот активен")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Бот выключен.")
