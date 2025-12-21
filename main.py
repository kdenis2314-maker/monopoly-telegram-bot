import os, asyncio, random
from threading import Thread
from flask import Flask, request, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from database import init_db, add_chat, get_all_chats

# --- КОНФИГ ---
TOKEN = os.getenv("BOT_TOKEN")
DEV_TAG = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8083))
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Полная карта Монополии (детальный список)
MAP = [
    "🚀 СТАРТ", "🏠 Житная", "🎁 Казна", "🏠 Нагатинская", "💰 Налог", "🚂 Рижская ж/д",
    "🏠 Варшавское", "❓ Шанс", "🏠 Огородный", "🏠 Парковая", "⚖️ Тюрьма", "🏠 Полянка",
    "⚡ Электро", "🏠 Сретенка", "🏠 Ростовская", "🚂 Курская ж/д", "🏠 Рязанский",
    "🎁 Казна", "🏠 Вавилова", "🏠 Тверская", "🎡 Отдых", "🏠 Щусева", "❓ Шанс",
    "🏠 Гоголевский", "🏠 Кутузовский", "🚂 Казанская", "🏠 Бронная", "🏠 Сивцев",
    "💧 Водоканал", "🏠 Арбат", "👮 В ТЮРЬМУ", "🏠 Новинский", "🏠 Маяковского"
]

# --- ЛОГИКА БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type != 'private': return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"))
    text = (f"🤖 **Monopoly Killer Bot**\n\n"
            f"📅 Создан: 21.12.2025\n"
            f"👨‍💻 Dev: {DEV_TAG}\n"
            f"✅ Статус: Online\n\n"
            f"⚠️ *Играть можно только в группе!*")
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if message.chat.type == 'private': return
    add_chat(message.chat.id, message.chat.title)
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 Сбор игроков", callback_data="lobby"))
    kb.row(types.InlineKeyboardButton(text="👨‍💻 Девелопер", callback_data="dev_info"))
    kb.row(types.InlineKeyboardButton(text="📜 Правила", callback_data="rules"))
    kb.row(types.InlineKeyboardButton(text="❓ Как играть", callback_data="how_to"))
    await message.answer(f"📍 **Меню Монополии в {message.chat.title}**\nНужна админка бота для работы!", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "lobby")
async def lobby(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Зайти", callback_data="join"),
           types.InlineKeyboardButton(text="❌ Выйти", callback_data="leave"))
    kb.row(types.InlineKeyboardButton(text="🚀 Начать игру", callback_data="run_game"))
    await call.message.edit_text("⏳ **Сбор игроков (2+ человека)**\n\nСписок:\n1. @Player1\n2. Ожидание...", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "run_game")
async def start_game(call: types.CallbackQuery):
    # Механика: Порядок ходов
    players = ["Игрок 1", "Игрок 2"]
    random.shuffle(players)
    order = "\n".join([f"{i+1}. {p}" for i, p in enumerate(players)])
    
    # Визуальная карта (список)
    view = f"🎲 **Игра началась!**\n\n**Очередь:**\n{order}\n\n**КАРТА:**\n"
    for i, name in enumerate(MAP[:15]): # Показываем часть карты для краткости
        mark = "📍" if i == 0 else "▫️"
        view += f"{mark} {name}\n"
    
    # Кнопки в чате + кнопка "Скрыть"
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 Бросить куб", callback_data="roll"))
    kb.row(types.InlineKeyboardButton(text="🙈 Скрыть меню", callback_data="hide"))
    
    await call.message.answer(view, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "hide")
async def hide_ui(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer("Клавиатура скрыта. Используйте /monopoly для возврата.")

# --- МОБИЛЬНЫЙ САЙТ (АДМИНКА + ТРОЛЛЬ-МЕНЮ) ---

@app.route('/')
def admin():
    chats = get_all_chats()
    chat_options = "".join([f"<option value='{c[0]}'>{c[1]}</option>" for c in chats])
    return render_template_string('''
    <body style="background:#111; color:white; font-family:sans-serif; padding:20px;">
        <h2 style="color:red;">😈 KILLER PANEL</h2>
        <div style="background:#222; padding:15px; border-radius:10px;">
            <p>Бот: <span style="color:lime;">РАБОТАЕТ ✅</span></p>
            <p>Порт: {{ port }}</p>
        </div>
        <h3>👤 ТРОЛЛЬ-МЕНЮ</h3>
        <form method="POST" action="/troll">
            <select name="chat_id" style="width:100%; padding:10px; margin-bottom:10px; background:#333; color:white;">
                {{ options|safe }}
            </select>
            <textarea name="text" placeholder="Написать от лица бота..." style="width:100%; height:80px; background:#333; color:white; border-radius:5px;"></textarea>
            <button style="width:100%; padding:15px; background:red; color:white; border:none; margin-top:10px; font-weight:bold;">ОТПРАВИТЬ</button>
        </form>
    </body>
    ''', port=PORT, options=chat_options)

@app.route('/troll', methods=['POST'])
def troll_post():
    cid = request.form.get('chat_id')
    txt = request.form.get('text')
    asyncio.run_coroutine_threadsafe(bot.send_message(cid, f"📢 {txt}"), asyncio.get_event_loop())
    return "✅ Улетело! <a href='/'>Назад</a>"

# --- ЗАПУСК ---
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

async def main():
    init_db()
    Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
