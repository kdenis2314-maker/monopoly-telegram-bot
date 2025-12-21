import os, asyncio, sqlite3, aiohttp, logging
from threading import Thread
from flask import Flask, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, URLInputFile

# --- КОНФИГ ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
DEV_TAG = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8083))

# Статус и фразы
IS_ACTIVE = True 
MAINTENANCE_MSG = "Бот обновляется или сломался, простите за неудобства, Темный принц уже исправляет это ♥️♥️"
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly for SHIT DAILY  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- 🗄️ БАЗА ДАННЫХ (ВСЯ ЛОГИКА) ---
def db_query(sql, params=()):
    try:
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

# --- 🌐 МОБИЛЬНЫЙ САЙТ (DASHBOARD) ---
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
        <p style="margin-top:20px; font-size:0.8em; color:#555;">{{ dev }}</p>
    </body>
    """, active=IS_ACTIVE, stats=players, dev=DEV_TAG)

# --- ⌨️ КЛАВИАТУРЫ ---

def get_reply_game_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик")
    kb.button(text="🗺️ Карта")
    kb.button(text="📊 Активы")
    kb.button(text="❌ Скрыть меню")
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)

def get_inline_game_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик", callback_data="roll_dice")
    kb.button(text="🗺️ Карта", callback_data="show_map")
    kb.button(text="📊 Активы", callback_data="show_assets")
    kb.button(text="🔄 Вернуть меню", callback_data="restore_reply_menu")
    kb.adjust(2, 1, 1)
    return kb.as_markup()

# --- 🎯 ХЕНДЛЕРЫ ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if not IS_ACTIVE:
        return await message.answer(MAINTENANCE_MSG)
    init_db()
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Сбор игроков", callback_data="start_lobby")
    kb.button(text="👨‍💻 О девелопере", callback_data="dev_info")
    
    caption = f"{BANNER}\n\n🎭 Добро пожаловать!\n{await ai_say('приветствие')}"
    try:
        await message.answer_photo(photo=URLInputFile(MONOPOLY_IMG), caption=caption, reply_markup=kb.as_markup())
    except:
        await message.answer(caption, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_lobby")
async def lobby(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    db_query("INSERT OR IGNORE INTO game_state (chat_id, organizer_id, status) VALUES (?, ?, 'lobby')", (cid, uid))
    players = db_query("SELECT name FROM players WHERE chat_id=?", (cid,))
    players_list = "\n".join([f"👤 {p[0]}" for p in players]) or "Ждем игроков..."
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Вступить", callback_data="join_game")
    if len(players) >= 2:
        kb.button(text="▶️ Начать игру", callback_data="go_active")
    
    await call.message.edit_caption(caption=f"{BANNER}\n\n**ЛОББИ:**\n{players_list}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "go_active")
async def start_game(call: types.CallbackQuery):
    db_query("UPDATE game_state SET status='active' WHERE chat_id=?", (call.message.chat.id,))
    await call.message.answer("🎉 Игра началась! Кнопки теперь внизу.", reply_markup=get_reply_game_kb())
    await call.message.delete()

# --- ЛОГИКА СКРЫТИЯ/ВОЗВРАТА ---

@dp.message(F.text == "❌ Скрыть меню")
async def hide_menu(message: types.Message):
    await message.answer("Клавиатура скрыта. Управление перенесено в чат 👇", reply_markup=ReplyKeyboardRemove())
    await message.answer("🕹️ Меню игры:", reply_markup=get_inline_game_kb())

@dp.callback_query(F.data == "restore_reply_menu")
async def restore_menu(call: types.CallbackQuery):
    await call.message.delete()
    await call.message.answer("✅ Меню вернулось вниз!", reply_markup=get_reply_game_kb())

# --- ИГРОВЫЕ ДЕЙСТВИЯ (ТЕКСТ + КОЛБЭК) ---

@dp.message(F.text == "🎲 Бросить кубик")
@dp.callback_query(F.data == "roll_dice")
async def roll(event):
    msg = event if isinstance(event, types.Message) else event.message
    # (Здесь твоя проверка очереди и логика хода...)
    dice = await msg.answer_dice("🎲")
    await asyncio.sleep(3.5)
    await msg.answer(f"Результат: {dice.dice.value}!")

# --- ЗАПУСК ---
def run_flask(): app.run(host="0.0.0.0", port=PORT)

async def main():
    init_db()
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
