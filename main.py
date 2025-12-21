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

# --- НАСТРОЙКА ВЫВОДА (ДЛЯ RENDER LOGS) ---
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- КОНФИГ ---
TOKEN = os.getenv("BOT_TOKEN")
DEV_TAG = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8083))

if not TOKEN:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN НЕ УСТАНОВЛЕН!", flush=True)
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- ПОЛНАЯ КАРТА КЛАССИЧЕСКОЙ МОНОПОЛИИ (40 КЛЕТОК) ---
MAP = [
    "🚀 СТАРТ", "🏠 Житная", "🎁 Казна", "🏠 Нагатинская", "💰 Налог", "🚂 Рижская ж/д",
    "🏠 Варшавское ш.", "❓ Шанс", "🏠 Огородный пр.", "🏠 Парковая", "⚖️ Тюрьма",
    "🏠 Полянка", "⚡ Электростанция", "🏠 Сретенка", "🏠 Ростовская наб.", "🚂 Курская ж/д",
    "🏠 Рязанский пр.", "🎁 Казна", "🏠 ул. Вавилова", "🏠 Тверская", "🎡 Стоянка",
    "🏠 ул. Щусева", "❓ Шанс", "🏠 Гоголевский б-р", "🏠 Кутузовский пр.", "🚂 Казанская ж/д",
    "🏠 М. Бронная", "🏠 Б. Бронная", "💧 Водоканал", "🏠 Смоленская пл.", "👮 В ТЮРЬМУ",
    "🏠 Новинский б-р", "🏠 ул. Маяковского", "🎁 Казна", "🏠 ул. Кутузова", "🚂 Ленинградская ж/д",
    "❓ Шанс", "🏠 Малая Дмитровка", "💎 Сверхналог", "🏠 УЛИЦА АРБАТ"
]

lobbies = {}

# --- ЛОГИКА БОТА ---

# 1. /START - ТОЛЬКО В ЛИЧКЕ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type != 'private':
        return 

    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить в группу", 
           url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"))
    
    text = (f"⚔️ **MONOPOLY KILLER ELITE** ⚔️\n\n"
            f"👤 **Developer:** {DEV_TAG}\n"
            f"📅 **Created:** 21.12.2025\n"
            f"📡 **Status:** `SYSTEM_READY` 🟢\n\n"
            f"📍 *Для начала игры добавь меня в группу и пропиши /monopoly*")
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    print(f"Log: {message.from_user.id} зашел в визитку", flush=True)

# 2. /MONOPOLY - ЭЛИТНОЕ МЕНЮ В ГРУППЕ
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if message.chat.type == 'private':
        return await message.answer("❌ Команда работает только в группах!")

    add_chat(message.chat.id, message.chat.title) # Регаем чат для сайта
    
    menu_text = (
        f"🔥 **ИГРОВОЙ ХАБ: {message.chat.title}** 🔥\n"
        f"————————————————————\n"
        f"👨‍💻 **Developer:** {DEV_TAG}\n"
        f"📜 **Статус системы:** `Ready for War`\n"
        f"⚙️ **Версия:** `3.5 Full Map`\n\n"
        f"👋 Приветствую! Используй панель управления ниже.\n"
        f"Здесь ты можешь собрать братву, изучить правила или связаться с создателем."
    )

    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 НАЧАТЬ СБОР ИГРОКОВ", callback_data="lobby"))
    kb.row(types.InlineKeyboardButton(text="👨‍💻 О ДЕВЕЛОПЕРЕ", callback_data="dev_info"))
    kb.row(
        types.InlineKeyboardButton(text="📜 ПРАВИЛА", callback_data="rules"),
        types.InlineKeyboardButton(text="❓ ПОМОЩЬ", callback_data="how_to")
    )
    kb.row(types.InlineKeyboardButton(text="🙈 СКРЫТЬ ПАНЕЛЬ", callback_data="hide"))

    await message.answer(menu_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    print(f"Log: Хаб вызван в чате {message.chat.id}", flush=True)

# --- ОБРАБОТКА КНОПОК ---

@dp.callback_query(F.data == "lobby")
async def lobby_handler(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    if chat_id not in lobbies: lobbies[chat_id] = []
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Зайти", callback_data="join"),
           types.InlineKeyboardButton(text="❌ Выйти", callback_data="leave"))
    kb.row(types.InlineKeyboardButton(text="🚀 НАЧАТЬ МАТЧ", callback_data="start_match"))
    
    p_list = "\n".join([f"• {p}" for p in lobbies[chat_id]]) if lobbies[chat_id] else "Никого нет..."
    await call.message.edit_text(f"⏳ **СБОР ИГРОКОВ**\n\n**Участники:**\n{p_list}", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "join")
async def join_handler(call: types.CallbackQuery):
    cid = call.message.chat.id
    user = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    if cid not in lobbies: lobbies[cid] = []
    if user not in lobbies[cid]:
        lobbies[cid].append(user)
        await lobby_handler(call)
    await call.answer()

@dp.callback_query(F.data == "start_match")
async def start_match(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    players = lobbies.get(chat_id, [])
    
    if len(players) < 2:
        await call.answer("❌ Нужно минимум 2 игрока!", show_alert=True)
        return

    random.shuffle(players)
    order = "\n".join([f"👤 {i+1}. {p}" for i, p in enumerate(players)])
    
    view = f"🎲 **ИГРА НАЧАЛАСЬ!**\n\n**Порядок ходов:**\n{order}\n\n**ПОЛНАЯ КАРТА (40):**\n"
    for i, name in enumerate(MAP):
        mark = "📍" if i == 0 else "▫️"
        view += f"{mark} {name}\n"
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎲 БРОСИТЬ КУБ", callback_data="roll"))
    kb.row(types.InlineKeyboardButton(text="🙈 СКРЫТЬ", callback_data="hide"))
    
    await call.message.answer(view, reply_markup=kb.as_markup(), parse_mode="Markdown")
    print(f"Log: Игра запущена в чате {chat_id}", flush=True)

@dp.callback_query(F.data == "dev_info")
async def dev_cb(call: types.CallbackQuery):
    await call.message.answer(f"👑 **Developer:** {DEV_TAG}\nСделано с душой для будущих монополистов.")
    await call.answer()

@dp.callback_query(F.data == "rules")
async def rules_cb(call: types.CallbackQuery):
    await call.message.answer("📖 **ПРАВИЛА:**\n1. Собирай игроков.\n2. Кидай куб.\n3. Покупай улицы.\n4. Выбивай деньги из соперников!")
    await call.answer()

@dp.callback_query(F.data == "how_to")
async def how_cb(call: types.CallbackQuery):
    await call.message.answer("❓ **КАК ИГРАТЬ:**\nИспользуй кнопки под сообщениями бота. Всё управление интуитивно.")
    await call.answer()

@dp.callback_query(F.data == "hide")
async def hide_cb(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer("Скрыто")

# --- САЙТ-АДМИНКА (ТРОЛЛЬ-МЕНЮ) ---

@app.route('/')
def admin():
    chats = get_all_chats()
    options = "".join([f"<option value='{c[0]}'>{c[1]}</option>" for c in chats])
    return render_template_string('''
    <body style="background:#111; color:white; font-family:sans-serif; padding:20px;">
        <h2 style="color:red;">😈 KILLER PANEL</h2>
        <p>Статус: <span style="color:lime;">РАБОТАЕТ ✅</span></p>
        <form method="POST" action="/troll">
            <select name="chat_id" style="width:100%; padding:10px; background:#222; color:white;">{{ opts|safe }}</select><br><br>
            <textarea name="text" placeholder="Троллинг в группу..." style="width:100%; height:80px; background:#222; color:white;"></textarea><br>
            <button style="width:100%; padding:15px; background:red; border:none; color:white; width:100%; margin-top:10px;">ОТПРАВИТЬ</button>
        </form>
    </body>
    ''', opts=options)

@app.route('/troll', methods=['POST'])
def troll_post():
    cid = request.form.get('chat_id')
    txt = request.form.get('text')
    asyncio.run_coroutine_threadsafe(bot.send_message(cid, f"📢 {txt}"), asyncio.get_event_loop())
    return "✅ Отправлено! <a href='/' style='color:white;'>Назад</a>"

# --- ЗАПУСК ---

def run_flask():
    print(f"--- SERVER ON PORT {PORT} ---", flush=True)
    app.run(host="0.0.0.0", port=PORT)

async def main():
    print("--- DB INIT ---", flush=True)
    init_db()
    Thread(target=run_flask, daemon=True).start()
    print("--- BOT POLLING START ---", flush=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)
