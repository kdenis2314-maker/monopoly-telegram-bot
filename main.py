import os, asyncio, random
from threading import Thread
from flask import Flask, request, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import init_db, add_chat, get_all_chats

# --- КОНФИГ ---
TOKEN = os.getenv("BOT_TOKEN")
DEV_TAG = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8083))
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Детальная визуальная карта (список)
MAP = [
    "🚀 СТАРТ", "🏠 Житная", "🎁 Казна", "🏠 Нагатинская", "💰 Налог", "🚂 Рижская ж/д",
    "🏠 Варшавское", "❓ Шанс", "🏠 Огородный", "🏠 Парковая", "⚖️ Тюрьма", "🏠 Полянка",
    "⚡ Электро", "🏠 Сретенка", "🏠 Ростовская", "🚂 Курская ж/д", "🏠 Рязанский",
    "🎁 Казна", "🏠 Вавилова", "🏠 Тверская", "🎡 Отдых", "🏠 Щусева", "❓ Шанс",
    "🏠 Гоголевский", "🏠 Кутузовский", "🚂 Казанская", "🏠 Бронная", "🏠 Сивцев",
    "💧 Водоканал", "🏠 Арбат", "👮 В ТЮРЬМУ", "🏠 Новинский", "🏠 Маяковского"
]

# Хранилище лобби (кто зашел в игру)
lobbies = {} 

# --- ЛОГИКА БОТА ---

# 1. /START - ТОЛЬКО В ЛС
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type != 'private': return 
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"))
    text = (f"🤖 **Monopoly Killer Bot**\n\n"
            f"📅 Дата создания: 21.12.2025\n"
            f"👨‍💻 Девелопер: {DEV_TAG}\n"
            f"✅ Статус: РАБОТАЕТ\n\n"
            f"⚠️ *Играть можно только в группе!*")
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

# 2. /MONOPOLY - МЕНЮ В ГРУППЕ
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if message.chat.type == 'private': return
    add_chat(message.chat.id, message.chat.title)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 Начать сбор игроков", callback_data="lobby"))
    kb.row(types.InlineKeyboardButton(text="👨‍💻 О девелопере", callback_data="dev_info"))
    kb.row(types.InlineKeyboardButton(text="📜 Правила игры", callback_data="rules"))
    kb.row(types.InlineKeyboardButton(text="❓ Взаимодействие", callback_data="how_to"))
    await message.answer(f"📍 **Меню Монополии: {message.chat.title}**", reply_markup=kb.as_markup())

# 3. СБОР ИГРОКОВ (ЛОББИ)
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

@dp.callback_query(F.data == "join")
async def join_game(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    user = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    if chat_id not in lobbies: lobbies[chat_id] = []
    if user not in lobbies[chat_id]:
        lobbies[chat_id].append(user)
        await call.answer("Ты в игре!")
        await lobby_handler(call)
    else:
        await call.answer("Ты уже в списке!", show_alert=True)

# 4. НАЧАЛО ИГРЫ (МЕХАНИКА И ВИЗУАЛ)
@dp.callback_query(F.data == "start_match")
async def start_match(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    players = lobbies.get(chat_id, [])
    
    if len(players) < 2:
        await call.answer("❌ Недостаточно игроков (нужно минимум 2)!", show_alert=True)
        return

    random.shuffle(players) # СИСТЕМА ОПРЕДЕЛЯЕТ ПОРЯДОК ХОДОВ
    order = "\n".join([f"{i+1}. {p}" for i, p in enumerate(players)])
    
    # Визуальная карта (Детальный список)
    view = f"🎲 **Игра началась!**\n\n**Очередь:**\n{order}\n\n**КАРТА:**\n"
    for i, name in enumerate(MAP[:15]): # Показываем часть для примера
        mark = "📍" if i == 0 else "▫️"
        view += f"{mark} {name}\n"
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 Бросить куб", callback_data="roll"))
    kb.row(types.InlineKeyboardButton(text="🙈 Скрыть меню", callback_data="hide"))
    await call.message.answer(view, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "hide")
async def hide_ui(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer("Меню скрыто.")

# --- МОБИЛЬНЫЙ САЙТ (АДМИНКА + ТРОЛЛЬ-МЕНЮ) ---

@app.route('/')
def admin():
    chats = get_all_chats()
    options = "".join([f"<option value='{c[0]}'>{c[1]}</option>" for c in chats])
    return render_template_string('''
    <body style="background:#111; color:white; font-family:sans-serif; padding:20px;">
        <h2 style="color:red;">😈 MONOPOLY KILLER PANEL</h2>
        <div style="background:#222; padding:15px; border-radius:10px;">
            <p>Бот: <span style="color:lime;">РАБОТАЕТ ✅</span></p>
            <p>Порт: {{ port }}</p>
        </div>
        <h3>👤 ТРОЛЛЬ-МЕНЮ</h3>
        <form method="POST" action="/troll">
            <select name="chat_id" style="width:100%; padding:10px; margin-bottom:10px; background:#333; color:white;">{{ opts|safe }}</select>
            <textarea name="text" placeholder="Текст в группу..." style="width:100%; height:80px; background:#333; color:white; border-radius:5px;"></textarea>
            <button style="width:100%; padding:15px; background:red; color:white; border:none; margin-top:10px; font-weight:bold; border-radius:5px;">ОТПРАВИТЬ</button>
        </form>
    </body>
    ''', port=PORT, opts=options)

@app.route('/troll', methods=['POST'])
def troll_post():
    cid = request.form.get('chat_id')
    txt = request.form.get('text')
    asyncio.run_coroutine_threadsafe(bot.send_message(cid, f"📢 {txt}"), asyncio.get_event_loop())
    return "✅ Отправлено! <a href='/'>Назад</a>"

# --- ЗАПУСК ---
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

async def main():
    init_db()
    Thread(target=run_flask, daemon=True).start()
    print(f"🚀 Killer Bot {DEV_TAG} запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
