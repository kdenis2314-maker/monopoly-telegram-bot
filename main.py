import os, asyncio, random, sqlite3, aiohttp, logging
from threading import Thread
from flask import Flask, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГ И ПЕРЕМЕННЫЕ ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
DEV_TAG = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8083))

# Статус и кастомные фразы
IS_ACTIVE = True 
MAINTENANCE_MSG = "Бот обновляется или сломался, простите за неудобства, Темный принц уже исправляет это ♥️♥️"
DEV_INFO = f"{DEV_TAG} — создатель бота*, по всем вопросам в личку.\n\n* Бот создан только для чата SHIT DAILY"

# Визуальные ассеты
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly for SHIT DAILY  ┃\n┗━━━━━━━━━━━━━━━━━━┛"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- 🗄️ ЛОГИКА БАЗЫ ДАННЫХ ---
def db_query(sql, params=()):
    with sqlite3.connect('monopoly_final.db') as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.fetchall()

def init_db():
    # Сохраняем всю структуру: игроки, имущество, состояние игры
    db_query('''CREATE TABLE IF NOT EXISTS players 
        (chat_id int, user_id int, name text, balance int, pos int, jail int, turn_order int, PRIMARY KEY(chat_id, user_id))''')
    db_query('''CREATE TABLE IF NOT EXISTS property 
        (chat_id int, cell_idx int, owner_id int, houses int DEFAULT 0, PRIMARY KEY(chat_id, cell_idx))''')
    db_query('''CREATE TABLE IF NOT EXISTS game_state 
        (chat_id int PRIMARY KEY, current_turn_idx int DEFAULT 0, organizer_id int, status text DEFAULT 'lobby')''')

# --- 🧠 ИИ-ВЕДУЩИЙ (Pollinations) ---
async def ai_say(text):
    try:
        url = "https://text.pollinations.ai/"
        prompt = f"Ты Монопольный Бро, дерзкий ведущий игры Monopoly for SHIT DAILY. Создатель {DEV_TAG}. Ответь кратко и весело на событие: {text}"
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}{prompt}", timeout=5) as r:
                return await r.text() if r.status == 200 else "Твой ход, босс! 🎲"
    except: return "Бро в деле! ✨"

# --- 🗺️ ДАННЫЕ КАРТЫ И ВИЗУАЛ ---
MAP_DATA = {
    0: {"name": "СТАРТ 🚩"}, 1: {"name": "Житная", "p": 60, "r": 2, "h_p": 50},
    3: {"name": "Нагатинская", "p": 60, "r": 4, "h_p": 50}, 10: {"name": "Тюрьма ⛓"},
    30: {"name": "ГО В ТЮРЬМУ 👮‍♂️"}, 36: {"name": "ШАНС ❓"}
}

def generate_map_text(chat_id):
    players = db_query("SELECT name, pos FROM players WHERE chat_id=? ORDER BY pos", (chat_id,))
    map_str = "📍 **Карта игроков:**\n"
    for p in players:
        map_str += f"👤 {p[0]}: клетка {p[1]} ({MAP_DATA.get(p[1], {'name': 'Улица'})['name']})\n"
    return map_str

# --- 🌐 МОБИЛЬНЫЙ МИНИ-САЙТ ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SHIT DAILY Status</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0a0a0a; color: white; padding: 20px; }
        .card { background: #151515; border: 1px solid #333; border-radius: 15px; padding: 20px; margin-bottom: 15px; }
        .status-on { color: #00ff88; } .status-off { color: #ff4444; }
    </style>
</head>
<body>
    <div class="card text-center">
        <h4>MONOPOLY</h4><p>for SHIT DAILY</p>
        <hr>
        <h6>Статус: <span class="{{ 'status-on' if active else 'status-off' }}">{{ 'ONLINE' if active else 'MAINTENANCE' }}</span></h6>
    </div>
    <div class="card">
        <h6>🏆 Лидеры:</h6>
        {% for name, bal in stats %}
        <div class="d-flex justify-content-between border-bottom border-secondary py-1">
            <span>{{ name }}</span><span>${{ bal }}</span>
        </div>
        {% endfor %}
    </div>
    <p class="text-center small text-secondary">{{ dev }}</p>
</body>
</html>
"""

@app.route('/')
def index():
    players = db_query("SELECT name, balance FROM players ORDER BY balance DESC LIMIT 5")
    return render_template_string(HTML_TEMPLATE, active=IS_ACTIVE, stats=players, dev=DEV_TAG)

# --- 🎯 ЛОГИКА ОЧЕРЕДИ ---
async def check_turn(cid, uid):
    players = db_query("SELECT user_id FROM players WHERE chat_id=? ORDER BY turn_order", (cid,))
    state = db_query("SELECT current_turn_idx FROM game_state WHERE chat_id=?", (cid,))
    if not players or not state: return False
    return players[state[0][0] % len(players)][0] == uid

# --- 🚀 ХЕНДЛЕРЫ БОТА ---

@dp.callback_query(F.data == "hide_menu")
async def hide_menu(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer("Меню скрыто")

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if not IS_ACTIVE:
        kb = InlineKeyboardBuilder().button(text="❌ Скрыть меню", callback_data="hide_menu").as_markup()
        return await message.answer(MAINTENANCE_MSG, reply_markup=kb)
    
    init_db()
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Начать сбор игроков", callback_data="start_lobby")
    kb.button(text="👨‍💻 О девелопере", callback_data="dev_info")
    kb.button(text="❌ Скрыть меню", callback_data="hide_menu")
    kb.adjust(1)
    
    caption = f"{BANNER}\n\n🎭 **Добро пожаловать!**\n\n{await ai_say('Приветствие участников')}"
    await message.answer_photo(photo=MONOPOLY_IMG, caption=caption, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "dev_info")
async def dev_info(call: types.CallbackQuery):
    await call.message.answer(DEV_INFO)
    await call.answer()

@dp.callback_query(F.data == "start_lobby")
async def lobby(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    db_query("INSERT OR IGNORE INTO game_state (chat_id, organizer_id, status) VALUES (?, ?, 'lobby')", (cid, uid))
    
    players = db_query("SELECT name FROM players WHERE chat_id=?", (cid,))
    players_list = "\n".join([f"👤 {p[0]}" for p in players]) or "Ждем игроков..."
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Вступить", callback_data="join_lobby")
    if len(players) >= 2: kb.button(text="▶️ Начать игру", callback_data="start_game")
    kb.button(text="❌ Скрыть меню", callback_data="hide_menu")
    kb.adjust(2, 1)
    
    await call.message.edit_caption(caption=f"{BANNER}\n\n**ЛОББИ:**\n{players_list}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "join_lobby")
async def join(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    exists = db_query("SELECT user_id FROM players WHERE chat_id=? AND user_id=?", (cid, uid))
    if not exists:
        count = db_query("SELECT COUNT(*) FROM players WHERE chat_id=?", (cid,))[0][0]
        db_query("INSERT INTO players VALUES (?, ?, ?, 1500, 0, 0, ?)", (cid, uid, call.from_user.first_name, count))
    await lobby(call)

@dp.callback_query(F.data == "start_game")
async def start_game(call: types.CallbackQuery):
    db_query("UPDATE game_state SET status='active' WHERE chat_id=?", (call.message.chat.id,))
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик", callback_data="roll_dice")
    kb.button(text="🗺️ Карта", callback_data="view_map")
    kb.button(text="📊 Активы", callback_data="view_assets")
    kb.button(text="❌ Скрыть меню", callback_data="hide_menu")
    kb.adjust(2, 2)
    
    await call.message.answer(f"🎉 **ИГРА НАЧАЛАСЬ!**\n\n{await ai_say('Начало')}", reply_markup=kb.as_markup())
    await call.message.delete()

@dp.callback_query(F.data == "roll_dice")
async def roll(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    if not await check_turn(cid, uid): return await call.answer("⏳ Не твой ход!", show_alert=True)
    
    p = db_query("SELECT name, balance, pos, jail FROM players WHERE chat_id=? AND user_id=?", (cid, uid))
    name, bal, pos, jail = p[0]

    if jail > 0:
        db_query("UPDATE players SET jail=jail-1 WHERE chat_id=? AND user_id=?", (cid, uid))
        db_query("UPDATE game_state SET current_turn_idx = current_turn_idx + 1 WHERE chat_id=?", (cid,))
        return await call.message.answer(f"⛓ {name}, ты в тюрьме! Еще {jail} х.")

    dice = await bot.send_dice(cid)
    val = dice.dice.value
    await asyncio.sleep(3.5)

    new_pos = (pos + val) % 40
    if new_pos == 30:
        db_query("UPDATE players SET pos=10, jail=3 WHERE chat_id=? AND user_id=?", (cid, uid))
        msg = "🚔 Тюрьма!"
    else:
        bal += 200 if new_pos < pos else 0
        db_query("UPDATE players SET pos=?, balance=? WHERE chat_id=? AND user_id=?", (new_pos, bal, cid, uid))
        msg = f"🏃 {name} на клетке {new_pos}. Баланс: ${bal}"

    db_query("UPDATE game_state SET current_turn_idx = current_turn_idx + 1 WHERE chat_id=?", (cid,))
    await call.message.answer(f"{msg}\n\n🤖 {await ai_say('ход игрока')}", reply_markup=call.message.reply_markup)

@dp.callback_query(F.data == "view_map")
async def view_map(call: types.CallbackQuery):
    await call.message.answer(generate_map_text(call.message.chat.id))
    await call.answer()

# --- СЕРВЕР И ЗАПУСК ---
def run_flask(): app.run(host="0.0.0.0", port=PORT)

async def main():
    init_db()
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
