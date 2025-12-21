import os
import asyncio
import random
import sys
import logging
from threading import Thread
from flask import Flask, request, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import init_db, add_chat, get_all_chats

# --- НАСТРОЙКА ЛОГОВ ДЛЯ RENDER ---
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- КОНФИГ ---
TOKEN = os.getenv("BOT_TOKEN")
DEV_TAG = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8083))

if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в переменных Render!", flush=True)
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Карта Монополии
MAP = [
    "🚀 СТАРТ", "🏠 Житная", "🎁 Казна", "🏠 Нагатинская", "💰 Налог", "🚂 Рижская ж/д",
    "🏠 Варшавское", "❓ Шанс", "🏠 Огородный", "🏠 Парковая", "⚖️ Тюрьма", "🏠 Полянка",
    "⚡ Электро", "🏠 Сретенка", "🏠 Ростовская", "🚂 Курская ж/д", "🏠 Рязанский",
    "🎁 Казна", "🏠 Вавилова", "🏠 Тверская", "🎡 Отдых", "🏠 Щусева", "❓ Шанс",
    "🏠 Гоголевский", "🏠 Кутузовский", "🚂 Казанская", "🏠 Бронная", "🏠 Сивцев",
    "💧 Водоканал", "🏠 Арбат", "👮 В ТЮРЬМУ", "🏠 Новинский", "🏠 Маяковского"
]

lobbies = {}

# --- ЛОГИКА БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type == 'private':
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"))
        text = (f"🤖 **Monopoly Killer Bot**\n\n📅 Дата создания: 21.12.2025\n"
                f"👨‍💻 Девелопер: {DEV_TAG}\n✅ Статус: РАБОТАЕТ\n\n"
                f"⚠️ *Играть можно только в группе!*")
        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
        print(f"Log: Пользователь {message.from_user.id} зашел в ЛС", flush=True)

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if message.chat.type != 'private':
        add_chat(message.chat.id, message.chat.title)
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="🎲 Начать сбор игроков", callback_data="lobby"))
        kb.row(types.InlineKeyboardButton(text="👨‍💻 О девелопере", callback_data="dev_info"))
        kb.row(types.InlineKeyboardButton(text="📜 Правила игры", callback_data="rules"))
        kb.row(types.InlineKeyboardButton(text="❓ Взаимодействие", callback_data="how_to"))
        await message.answer(f"📍 **Меню Монополии: {message.chat.title}**", reply_markup=kb.as_markup())
        print(f"Log: Команда /monopoly вызвана в чате {message.chat.id}", flush=True)

@dp.callback_query(F.data == "lobby")
async def lobby_handler(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    if chat_id not in lobbies: lobbies[chat_id] = []
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Зайти", callback_data="join"),
           types.InlineKeyboardButton(text="❌ Выйти", callback_data="leave"))
    kb.row(types.InlineKeyboardButton(text="🚀 Начать игру", callback_data="start_match"))
    players_list = "\n".join([f"• {p}" for p in lobbies[chat_id]]) if lobbies[chat_id] else "Пусто..."
    await call.message.edit_text(f"⏳ **Сбор игроков**\n\n**Участники:**\n{players_list}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_match")
async def start_match(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    players = lobbies.get(chat_id, [])
    if len(players) < 2:
        await call.answer("❌ Нужно минимум 2 игрока!", show_alert=True)
        return
    random.shuffle(players)
    order = "\n".join([f"{i+1}. {p}" for i, p in enumerate(players)])
    view = f"🎲 **Игра началась!**\n\n**Очередь:**\n{order}\n\n**КАРТА:**\n"
    for i, name in enumerate(MAP[:15]):
        mark = "📍" if i == 0 else "▫️"
        view += f"{mark} {name}\n"
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 Бросить куб", callback_data="roll"),
           types.InlineKeyboardButton(text="🙈 Скрыть меню", callback_data="hide"))
    await call.message.answer(view, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "hide")
async def hide_ui(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer("Скрыто")

# --- САЙТ ---

@app.route('/')
def admin():
    chats = get_all_chats()
    options = "".join([f"<option value='{c[0]}'>{c[1]}</option>" for c in chats])
    return render_template_string('''
    <body style="background:#111; color:white; font-family:sans-serif; padding:20px;">
        <h2 style="color:red;">😈 MONOPOLY ADMIN</h2>
        <p>Статус: <span style="color:lime;">РАБОТАЕТ ✅</span></p>
        <form method="POST" action="/troll">
            <select name="chat_id" style="width:100%; padding:10px;">{{ opts|safe }}</select>
            <textarea name="text" style="width:100%; height:80px; margin-top:10px;"></textarea>
            <button style="width:100%; padding:15px; background:red; color:white; border:none; margin-top:10px;">ОТПРАВИТЬ</button>
        </form>
    </body>
    ''', opts=options)

@app.route('/troll', methods=['POST'])
def troll_post():
    cid = request.form.get('chat_id')
    txt = request.form.get('text')
    asyncio.run_coroutine_threadsafe(bot.send_message(cid, f"📢 {txt}"), asyncio.get_event_loop())
    return "✅ OK! <a href='/'>Back</a>"

# --- ЗАПУСК ---

def run_flask():
    print(f"--- ЗАПУСК FLASK НА ПОРТУ {PORT} ---", flush=True)
    app.run(host="0.0.0.0", port=PORT)

async def main():
    print("--- ИНИЦИАЛИЗАЦИЯ БД ---", flush=True)
    init_db()
    Thread(target=run_flask, daemon=True).start()
    print("--- ПОЛЛИНГ БОТА ЗАПУЩЕН ---", flush=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
