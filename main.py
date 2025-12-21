import os, asyncio, random
from threading import Thread
from flask import Flask, request, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from database import init_db, add_player

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("8265158957:AAGZlj47XZ6D6rK6tt0ccWsAZCQYV7UXMoA")
DEV_ID = "@Whylovely05"
START_DATE = "21.12.2025"
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)
init_db()

# Детальная карта в виде списка
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
    kb.row(types.InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"))
    
    text = (f"🤖 **Monopoly Killer Bot**\n\n"
            f"📅 Создан: {START_DATE}\n"
            f"👨‍💻 Девелопер: {DEV_ID}\n"
            f"✅ Статус: РАБОТАЕТ\n\n"
            f"⚠️ *Играть можно только в группе!*")
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if message.chat.type == 'private': return
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 Начать сбор игроков", callback_data="lobby"))
    kb.row(types.InlineKeyboardButton(text="📜 Правила", callback_data="rules"))
    kb.row(types.InlineKeyboardButton(text="👨‍💻 Девелопер", callback_data="dev"))
    
    await message.answer(f"📍 **Меню Монополии в {message.chat.title}**", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "lobby")
async def lobby(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Зайти", callback_data="join"),
           types.InlineKeyboardButton(text="❌ Выйти", callback_data="leave"))
    kb.row(types.InlineKeyboardButton(text="🚀 Начать игру", callback_data="start_game"))
    
    await call.message.edit_text("⏳ **Сбор игроков открыт!**\n\nСписок:\n1. Ожидание игроков...", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_game")
async def start_game(call: types.CallbackQuery):
    # Логика: Порядок ходов + Визуальная карта
    view = "🎲 **Игра началась!**\n\n**Порядок ходов:**\n1. Игрок А\n2. Игрок Б\n\n**КАРТА:**\n"
    for i, name in enumerate(MAP_DATA):
        mark = "📍" if i == 0 else "▫️"
        view += f"{mark} {name}\n"
    
    # Кнопки управления (в чате) + Кнопка "Скрыть"
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 Бросить кубик", callback_data="roll"))
    kb.row(types.InlineKeyboardButton(text="🙈 Скрыть меню", callback_data="hide_ui"))
    
    await call.message.answer(view, reply_markup=kb.as_markup())

# --- МОБИЛЬНЫЙ САЙТ (АДМИНКА) ---

@app.route('/')
def admin():
    return render_template_string('''
    <body style="background:#111; color:white; font-family:sans-serif; padding:20px;">
        <h2>😈 Monopoly Killer Admin</h2>
        <div style="background:#222; padding:15px; border-radius:10px;">
            <p>Статус: <span style="color:#0f0">ACTIVE</span></p>
            <p>Версия: 2.0 Killer Edition</p>
        </div>
        <h3>💬 ТРОЛЛЬ-МЕНЮ</h3>
        <form method="POST" action="/troll">
            <input name="chat_id" placeholder="ID Группы" style="width:100%; padding:10px; margin-bottom:10px;">
            <textarea name="text" placeholder="Текст от имени бота" style="width:100%; height:80px;"></textarea>
            <button style="width:100%; padding:15px; background:red; color:white; border:none; border-radius:5px;">ОТПРАВИТЬ В ЧАТ</button>
        </form>
    </body>
    ''')

@app.route('/troll', methods=['POST'])
def troll():
    cid = request.form.get('chat_id')
    txt = request.form.get('text')
    asyncio.run_coroutine_threadsafe(bot.send_message(cid, f"🤖 {txt}"), asyncio.get_event_loop())
    return "Отправлено! <a href='/'>Назад</a>"

# --- ЗАПУСК ---
def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
