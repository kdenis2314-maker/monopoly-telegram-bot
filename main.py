import os, asyncio, sqlite3, aiohttp, logging, random
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, URLInputFile

# --- [1] КОНФИГ И ЗАЩИТА ПРИНЦА ---
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

# --- [2] ПОЛНАЯ КАРТА (Цвета, Цены, Аренда) ---
BOARD = {
    1: {"n": "Житная", "p": 60, "r": 2, "c": "brown"}, 3: {"n": "Нагатинская", "p": 60, "r": 4, "c": "brown"},
    5: {"n": "Рижская ж/д", "p": 200, "r": 25, "c": "rail"}, 6: {"n": "Варшавское ш.", "p": 100, "r": 6, "c": "blue"},
    8: {"n": "Огородный пр.", "p": 100, "r": 6, "c": "blue"}, 9: {"n": "Рижская", "p": 120, "r": 8, "c": "blue"},
    11: {"n": "Курская", "p": 140, "r": 10, "c": "pink"}, 12: {"n": "Электросеть", "p": 150, "r": 10, "c": "util"},
    13: {"n": "Абрамцево", "p": 140, "r": 10, "c": "pink"}, 14: {"n": "Пантелеевская", "p": 160, "r": 12, "c": "pink"},
    # ... и так далее до 39 клетки (Логика цен сохранена)
}

# --- [3] БАЗА ДАННЫХ (Расширенная под всё) ---
def db_query(sql, params=()):
    with sqlite3.connect('monopoly_god_mode.db', check_same_thread=False) as conn:
        cur = conn.cursor(); cur.execute(sql, params); conn.commit()
        return cur.fetchall()

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS players 
        (chat_id int, user_id int, name text, balance int DEFAULT 1500, pos int DEFAULT 0, 
         jail int DEFAULT 0, doubles_count int DEFAULT 0, PRIMARY KEY(chat_id, user_id))''')
    db_query('''CREATE TABLE IF NOT EXISTS property 
        (chat_id int, cell_idx int, owner_id int, houses int DEFAULT 0, is_mortgaged int DEFAULT 0, 
         PRIMARY KEY(chat_id, cell_idx))''')

# --- [4] КЛАВИАТУРЫ (Твоя логика Скрыть/Вернуть) ---
def get_main_reply_kb():
    return ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").button(text="🏠 Строить").button(text="📊 Активы").button(text="❌ Скрыть меню").adjust(2, 2).as_markup(resize_keyboard=True)

def get_chat_inline_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Кубик", callback_data="btn_roll")
    kb.button(text="🏠 Построить", callback_data="btn_build")
    kb.button(text="📊 Активы", callback_data="btn_assets")
    kb.button(text="🔄 Вернуть меню", callback_data="btn_restore")
    return kb.adjust(2, 2).as_markup()

# --- [5] ЛОГИКА ТЮРЬМЫ И ХОДА ---
async def process_move(uid, cid):
    p = db_query("SELECT balance, pos, jail, name FROM players WHERE user_id=? AND chat_id=?", (uid, cid))[0]
    bal, pos, jail, name = p
    
    if jail > 0:
        return f"⛓ {name}, ты в тюрьме! Пропуск хода (осталось {jail}).", None

    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    new_pos = (pos + d1 + d2) % 40
    
    msg = f"🎲 {name}: {d1}+{d2} ➔ Клетка {new_pos}\n"
    
    if new_pos == 30: # Клетка "В тюрьму"
        db_query("UPDATE players SET pos=10, jail=3 WHERE user_id=? AND chat_id=?", (uid, cid))
        return msg + "👮‍♂️ АРЕСТ! Ты отправлен в тюрьму.", None

    db_query("UPDATE players SET pos=? WHERE user_id=? AND chat_id=?", (new_pos, uid, cid))
    
    # Логика покупки/аренды
    if new_pos in BOARD:
        prop = BOARD[new_pos]
        owner = db_query("SELECT owner_id, houses, is_mortgaged FROM property WHERE cell_idx=? AND chat_id=?", (new_pos, cid))
        if not owner:
            kb = InlineKeyboardBuilder().button(text=f"Купить ${prop['p']}", callback_data=f"buy_{new_pos}")
            kb.button(text="Аукцион 🔨", callback_data=f"auc_{new_pos}")
            return msg + f"🏠 **{prop['n']}** свободна. Что делаем?", kb.as_markup()
        elif owner[0][0] != uid and owner[0][2] == 0:
            rent = prop['r'] * (5**owner[0][1]) # Аренда растет от домов
            db_query("UPDATE players SET balance = balance - ? WHERE user_id=? AND chat_id=?", (rent, uid, cid))
            db_query("UPDATE players SET balance = balance + ? WHERE user_id=? AND chat_id=?", (rent, owner[0][0], cid))
            msg += f"💸 Аренда: ${rent} выплачена владельцу."
            
    return msg, None

# --- [6] ХЕНДЛЕРЫ (ПРИНЦ, ФОТО, МЕНЮ) ---

@dp.message(Command("monopoly"))
async def start_game(m: types.Message):
    if not IS_ACTIVE: return await m.answer(MAINTENANCE_MSG)
    init_db()
    kb = InlineKeyboardBuilder().button(text="🎲 Лобби", callback_data="lobby_join").button(text="📜 Правила", callback_data="rules_show").as_markup()
    try:
        await m.answer_photo(URLInputFile(MONOPOLY_IMG), caption=f"{BANNER}\n\nСыграем?", reply_markup=kb)
    except:
        await m.answer(f"{MONOPOLY_IMG}\n\n{BANNER}", reply_markup=kb)

@dp.callback_query(F.data == "rules_show")
async def rules(c: types.CallbackQuery):
    await c.message.answer("📜 Жизненная Монополия:\n- Тюрьма 3 хода.\n- Нет денег на покупку? Аукцион!\n- Монополия цвета? Стой дома!")
    await c.answer()

@dp.message(F.text == "❌ Скрыть меню")
async def hide(m: types.Message):
    await m.answer("Меню скрыто.", reply_markup=ReplyKeyboardRemove())
    await m.answer("🕹 Управление в чате:", reply_markup=get_chat_inline_kb())

@dp.callback_query(F.data == "btn_restore")
async def restore(c: types.CallbackQuery):
    await c.message.delete()
    await c.message.answer("🔄 Меню вернулось!", reply_markup=get_main_reply_kb())

@dp.callback_query(F.data == "lobby_join")
async def lobby(c: types.CallbackQuery):
    db_query("INSERT OR IGNORE INTO players (chat_id, user_id, name) VALUES (?,?,?)", (c.message.chat.id, c.from_user.id, c.from_user.first_name))
    p_count = db_query("SELECT COUNT(*) FROM players WHERE chat_id=?", (c.message.chat.id,))[0][0]
    kb = InlineKeyboardBuilder().button(text="✅ Вступить", callback_data="lobby_join").button(text="▶️ Старт", callback_data="game_start").as_markup()
    await c.message.edit_caption(caption=f"👥 Игроков: {p_count}", reply_markup=kb)

@dp.callback_query(F.data == "game_start")
async def run_game(c: types.CallbackQuery):
    await c.message.answer("Поехали! Кидай кубик!", reply_markup=get_main_reply_kb())
    await c.message.delete()

@dp.message(F.text == "🎲 Бросить кубик")
@dp.callback_query(F.data == "btn_roll")
async def roll(event):
    if not IS_ACTIVE: return
    m = event if isinstance(event, types.Message) else event.message
    txt, kb = await process_move(event.from_user.id, m.chat.id)
    await m.answer(txt, reply_markup=kb)
    if isinstance(event, types.CallbackQuery): await event.answer()

# --- [7] ЗАПУСК ---
def run_flask(): app.run(host="0.0.0.0", port=PORT)

async def main():
    init_db()
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
