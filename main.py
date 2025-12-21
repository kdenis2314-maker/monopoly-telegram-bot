import os, asyncio, sqlite3, aiohttp, logging, random
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
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly for SHIT DAILY  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- 🗺️ КАРТА ГОРОДА (Название, Цена, Аренда) ---
BOARD = {
    1: ["Житная", 60, 10], 3: ["Нагатинская", 60, 10], 5: ["Рижская ж/д", 200, 25],
    6: ["Варшавское ш.", 100, 15], 8: ["Огородный пр.", 100, 15], 9: ["Рижская", 120, 20],
    11: ["Курская", 140, 25], 13: ["Абрамцево", 140, 25], 14: ["Пантелеевская", 160, 30],
    16: ["Вавилова", 180, 35], 18: ["Тимирязевская", 180, 35], 19: ["Лихоборы", 200, 40],
    21: ["Арбат", 220, 45], 23: ["Полянка", 220, 45], 24: ["Сретенка", 240, 50],
    25: ["Курская ж/д", 200, 25], 26: ["Ростовская", 260, 55], 27: ["Рязанский пр.", 260, 55],
    29: ["Новинский б-р", 280, 60], 31: ["Пушкинская", 300, 70], 32: ["Тверская", 300, 70],
    34: ["Маяковского", 320, 80], 37: ["Кутузовский", 350, 90], 39: ["Бродвей", 400, 100]
}

# --- 🗄️ БАЗА ДАННЫХ ---
def db_query(sql, params=()):
    try:
        with sqlite3.connect('monopoly_final.db', check_same_thread=False) as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            return cur.fetchall()
    except Exception as e:
        logging.error(f"DB Error: {e}"); return []

def init_db():
    db_query("CREATE TABLE IF NOT EXISTS players (chat_id int, user_id int, name text, balance int, pos int, jail int, PRIMARY KEY(chat_id, user_id))")
    db_query("CREATE TABLE IF NOT EXISTS property (chat_id int, cell_idx int, owner_id int, houses int, PRIMARY KEY(chat_id, cell_idx))")
    db_query("CREATE TABLE IF NOT EXISTS game_state (chat_id int PRIMARY KEY, status text DEFAULT 'lobby')")

# --- 🧠 ИИ-ВЕДУЩИЙ ---
async def ai_say(text):
    try:
        url = f"https://text.pollinations.ai/Ты ведущий Монополии от {DEV_TAG}. Ответь кратко и дерзко на событие: {text}"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=5) as r:
                return await r.text() if r.status == 200 else "Твой ход!"
    except: return "Двигайся, бро! ✨"

# --- ⌨️ КЛАВИАТУРЫ ---
def get_reply_kb():
    return ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").button(text="📊 Активы").button(text="❌ Скрыть меню").adjust(2, 1).as_markup(resize_keyboard=True)

def get_inline_game_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик", callback_data="roll_dice")
    kb.button(text="📊 Активы", callback_data="show_assets")
    kb.button(text="🔄 Вернуть меню", callback_data="restore_menu")
    return kb.adjust(2, 1).as_markup()

# --- 🎯 ЛОГИКА ИГРЫ ---
async def handle_move(uid, cid, dice):
    p = db_query("SELECT name, balance, pos, jail FROM players WHERE chat_id=? AND user_id=?", (cid, uid))[0]
    name, bal, pos, jail = p
    
    if jail > 0:
        db_query("UPDATE players SET jail=jail-1 WHERE chat_id=? AND user_id=?", (cid, uid))
        return f"⛓ {name}, ты в тюрьме! Сидеть еще {jail} х.", None

    new_pos = (pos + dice) % 40
    msg = f"🎲 Выпало {dice}! {name} на клетке {new_pos}.\n"
    if new_pos < pos: 
        bal += 200
        msg += "💰 Прошел круг! +$200.\n"

    # Клетки событий
    if new_pos == 30: # Полиция
        db_query("UPDATE players SET pos=10, jail=3 WHERE chat_id=? AND user_id=?", (cid, uid))
        return msg + "👮‍♂️ МУСОРА! Ты в тюрьме на 3 хода.", None
    
    if new_pos in BOARD:
        prop = BOARD[new_pos]
        owner = db_query("SELECT owner_id, houses FROM property WHERE chat_id=? AND cell_idx=?", (cid, new_pos))
        if not owner:
            kb = InlineKeyboardBuilder().button(text=f"Купить {prop[0]} за ${prop[1]}", callback_data=f"buy_{new_pos}").as_markup()
            db_query("UPDATE players SET pos=? WHERE chat_id=? AND user_id=?", (new_pos, cid, uid))
            return msg + f"🏠 **{prop[0]}** свободна! Покупаем?", kb
        else:
            oid, houses = owner[0]
            if oid != uid:
                rent = prop[2] * (houses + 1)
                db_query("UPDATE players SET balance=balance-? WHERE chat_id=? AND user_id=?", (rent, cid, uid))
                db_query("UPDATE players SET balance=balance+? WHERE chat_id=? AND user_id=?", (rent, cid, oid))
                msg += f"💸 Попал к конкуренту! Заплатил ${rent} аренды."
    
    db_query("UPDATE players SET pos=?, balance=? WHERE chat_id=? AND user_id=?", (new_pos, bal, cid, uid))
    return msg + await ai_say(f"игрок стал на {new_pos}"), None

# --- 🚀 ХЕНДЛЕРЫ ---
@dp.message(Command("monopoly"))
async def start(m: types.Message):
    init_db()
    kb = InlineKeyboardBuilder().button(text="🎲 Сбор", callback_data="lobby").button(text="📜 Правила", callback_data="rules").as_markup()
    await m.answer_photo(MONOPOLY_IMG, caption=f"{BANNER}\n\nГотовы?", reply_markup=kb)

@dp.callback_query(F.data == "lobby")
async def lobby(c: types.CallbackQuery):
    db_query("INSERT OR IGNORE INTO game_state (chat_id) VALUES (?)", (c.message.chat.id,))
    players = db_query("SELECT name FROM players WHERE chat_id=?", (c.message.chat.id,))
    kb = InlineKeyboardBuilder().button(text="✅ Вступить", callback_data="join").button(text="▶️ Старт", callback_data="go").adjust(1).as_markup()
    await c.message.edit_caption(caption=f"👥 Игроков: {len(players)}", reply_markup=kb)

@dp.callback_query(F.data == "join")
async def join(c: types.CallbackQuery):
    db_query("INSERT OR IGNORE INTO players VALUES (?,?,?,1500,0,0)", (c.message.chat.id, c.from_user.id, c.from_user.first_name))
    await lobby(c)

@dp.callback_query(F.data == "go")
async def go(c: types.CallbackQuery):
    await c.message.answer("🎉 Погнали! Кнопки снизу.", reply_markup=get_reply_kb())
    await c.message.delete()

# --- ПЕРЕКЛЮЧЕНИЕ МЕНЮ ---
@dp.message(F.text == "❌ Скрыть меню")
async def hide(m: types.Message):
    await m.answer("Клавиатура скрыта. Управление здесь:", reply_markup=ReplyKeyboardRemove())
    await m.answer("🕹️ МЕНЮ:", reply_markup=get_inline_game_kb())

@dp.callback_query(F.data == "restore_menu")
async def restore(c: types.CallbackQuery):
    await c.message.delete()
    await c.message.answer("🔄 Меню вернулось!", reply_markup=get_reply_kb())

# --- ДЕЙСТВИЯ ---
@dp.message(F.text == "🎲 Бросить кубик")
@dp.callback_query(F.data == "roll_dice")
async def roll(event):
    m = event if isinstance(event, types.Message) else event.message
    d = await m.answer_dice("🎲")
    await asyncio.sleep(3.5)
    text, kb = await handle_move(event.from_user.id, m.chat.id, d.dice.value)
    await m.answer(text, reply_markup=kb)
    if isinstance(event, types.CallbackQuery): await event.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    uid, cid = c.from_user.id, c.message.chat.id
    bal = db_query("SELECT balance FROM players WHERE chat_id=? AND user_id=?", (cid, uid))[0][0]
    if bal >= BOARD[idx][1]:
        db_query("UPDATE players SET balance=balance-? WHERE chat_id=? AND user_id=?", (BOARD[idx][1], cid, uid))
        db_query("INSERT INTO property VALUES (?,?,?,0)", (cid, idx, uid))
        await c.message.answer(f"✅ Ты купил {BOARD[idx][0]}!")
    else: await c.answer("Денег нет, бро!", show_alert=True)
    await c.message.delete()

@dp.message(F.text == "📊 Активы")
@dp.callback_query(F.data == "show_assets")
async def assets(event):
    m = event if isinstance(event, types.Message) else event.message
    res = db_query("SELECT balance FROM players WHERE user_id=?", (event.from_user.id,))
    await m.answer(f"💰 Твой баланс: ${res[0][0] if res else 0}")

# --- САЙТ ---
@app.route('/')
def web(): return "<h1>SHIT DAILY MONOPOLY ONLINE</h1>", 200

def run_flask(): app.run(host="0.0.0.0", port=PORT)

async def main():
    init_db()
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
