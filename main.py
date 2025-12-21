import os, asyncio, random, sqlite3, aiohttp, logging
from threading import Thread
from flask import Flask, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГ ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
DEV_TAG = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8083))
IS_ACTIVE = True 
MAINTENANCE_MSG = "Бот обновляется или сломался, простите за неудобства, Темный принц уже исправляет это ♥️♥️"
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly for SHIT DAILY  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- 🗄️ БАЗА ДАННЫХ (С фиксом для многопоточности) ---
def db_query(sql, params=()):
    try:
        # check_same_thread=False нужен, чтобы Flask и Бот не конфликтовали
        with sqlite3.connect('monopoly_final.db', check_same_thread=False) as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            return cur.fetchall()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        return []

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS players 
        (chat_id int, user_id int, name text, balance int, pos int, jail int, turn_order int, PRIMARY KEY(chat_id, user_id))''')
    db_query('''CREATE TABLE IF NOT EXISTS game_state 
        (chat_id int PRIMARY KEY, current_turn_idx int DEFAULT 0, organizer_id int, status text DEFAULT 'lobby')''')

# --- 🧠 ИИ-ВЕДУЩИЙ ---
async def ai_say(text):
    try:
        url = "https://text.pollinations.ai/"
        prompt = f"Ты ведущий Monopoly for SHIT DAILY от {DEV_TAG}. Ответь кратко: {text}"
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}{prompt}", timeout=5) as r:
                return await r.text() if r.status == 200 else "Твой ход!"
    except: return "Бро в деле! ✨"

# --- 🌐 ВЕБ-ИНТЕРФЕЙС ---
@app.route('/')
def index():
    players = db_query("SELECT name, balance FROM players ORDER BY balance DESC LIMIT 5")
    return render_template_string("""
    <body style="background:#0a0a0a; color:white; font-family:sans-serif; text-align:center; padding:20px;">
        <h2>MONOPOLY for SHIT DAILY</h2>
        <p>Статус: <span style="color:#0f0">{{ 'ONLINE' if active else 'OFFLINE' }}</span></p>
        <div style="background:#151515; padding:15px; border-radius:10px; display:inline-block;">
            {% for name, bal in stats %}
                <p>{{ name }}: ${{ bal }}</p>
            {% endfor %}
        </div>
    </body>
    """, active=IS_ACTIVE, stats=players)

# --- 🎯 ОБРАБОТЧИК ОШИБОК ---
@dp.errors()
async def error_handler(event: types.ErrorEvent):
    logging.error(f"Critical error: {event.exception}")
    try:
        await event.update.callback_query.message.answer(MAINTENANCE_MSG)
    except:
        await bot.send_message(event.update.message.chat.id, MAINTENANCE_MSG)

# --- 🚀 ОСНОВНЫЕ ХЕНДЛЕРЫ (Логика сохранена) ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if not IS_ACTIVE:
        return await message.answer(MAINTENANCE_MSG)
    init_db()
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Сбор игроков", callback_data="start_lobby")
    kb.button(text="❌ Скрыть", callback_data="hide_menu")
    kb.adjust(1)
    await message.answer_photo(photo=MONOPOLY_IMG, caption=f"{BANNER}\n\nПогнали?", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "hide_menu")
async def hide(call: types.CallbackQuery):
    await call.message.delete()

@dp.callback_query(F.data == "start_lobby")
async def lobby(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    db_query("INSERT OR IGNORE INTO game_state (chat_id, organizer_id, status) VALUES (?, ?, 'lobby')", (cid, uid))
    players = db_query("SELECT name FROM players WHERE chat_id=?", (cid,))
    players_list = "\n".join([f"👤 {p[0]}" for p in players]) or "Ждем..."
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Вступить", callback_data="join_game")
    if len(players) >= 2: kb.button(text="▶️ Начать", callback_data="go_active")
    kb.button(text="❌ Скрыть", callback_data="hide_menu")
    kb.adjust(2, 1)
    await call.message.edit_caption(caption=f"{BANNER}\n\n**ЛОББИ:**\n{players_list}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "join_game")
async def join(call: types.CallbackQuery):
    db_query("INSERT OR IGNORE INTO players (chat_id, user_id, name, balance, pos, jail) VALUES (?, ?, ?, 1500, 0, 0)", 
             (call.message.chat.id, call.from_user.id, call.from_user.first_name))
    await lobby(call)

@dp.callback_query(F.data == "go_active")
async def start(call: types.CallbackQuery):
    db_query("UPDATE game_state SET status='active' WHERE chat_id=?", (call.message.chat.id,))
    kb = InlineKeyboardBuilder().button(text="🎲 Кубик", callback_data="roll").button(text="❌ Скрыть", callback_data="hide_menu").as_markup()
    await call.message.answer(f"🎉 Игра началась!\n{await ai_say('старт')}", reply_markup=kb)
    await call.message.delete()

# --- ЗАПУСК ---
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

async def main():
    init_db()
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
