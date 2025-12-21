import os, asyncio, sqlite3, logging, random
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove

# --- [1] КОНФИГ И СТАТУС ПРИНЦА ---
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

# --- [2] ГЕНЕРАТОР ЖИВЫХ ФРАЗ ---
def get_phrase(category):
    phrases = {
        "start": ["Стартуем! 🚀", "Начинаем экономическое сражение! ⚔️", "Погнали грабить ближнего своего! 💰", "Битва за капитал объявлена открытой! 🏛"],
        "roll": ["Кубики запущены... 🎲", "Судьба решается прямо сейчас! ✨", "Лети, родной! 🎲", "Что нам скажет рандом? 🤔"],
        "result": ["Ого! Выпало {v}!", "Твоя удача сегодня — это {v}!", "Двигаемся на {v} шагов вперёд!", "{v} на кубиках! Неплохо!"],
        "hide": ["Убираю лишнее с глаз... 🙈", "Меню спрятано, работаем в чате!", "Чистота — залог успеха. Клавиатура скрыта! ✨"],
        "restore": ["Я вернулся! 🔙", "Меню снова в деле!", "Кнопки на базе!", "Продолжаем снизу! 👇"]
    }
    return random.choice(phrases.get(category, ["Действие выполнено!"]))

# --- [3] БАЗА ДАННЫХ ---
def db_query(sql, params=()):
    with sqlite3.connect('monopoly_final.db', timeout=20) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.fetchall()

def init_db():
    db_query("CREATE TABLE IF NOT EXISTS players (chat_id int, user_id int, name text, balance int DEFAULT 1500, pos int DEFAULT 0, jail int DEFAULT 0, PRIMARY KEY(chat_id, user_id))")

# --- [4] ПРОВЕРКА ПРИНЦА ---
@dp.callback_query(lambda c: not IS_ACTIVE)
async def maintenance_call(call: types.CallbackQuery):
    await call.answer(MAINTENANCE_MSG, show_alert=True)

@dp.message(lambda m: not IS_ACTIVE)
async def maintenance_msg(message: types.Message):
    await message.answer(MAINTENANCE_MSG)

# --- [5] КЛАВИАТУРЫ ---
def get_main_reply_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик")
    kb.button(text="🏠 Строить")
    kb.button(text="📊 Активы")
    kb.button(text="🤝 Обмен")
    kb.button(text="❌ Скрыть меню")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def get_chat_inline_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Кубик", callback_data="btn_roll")
    kb.button(text="🏠 Построить", callback_data="btn_build")
    kb.button(text="📊 Активы", callback_data="btn_assets")
    kb.button(text="🔄 Вернуть меню", callback_data="btn_restore")
    kb.adjust(2, 2)
    return kb.as_markup()

# --- [6] ХЕНДЛЕРЫ ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    init_db()
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Сбор игроков", callback_data="start_lobby")
    kb.button(text="📜 Правила", callback_data="show_rules")
    kb.button(text="👨‍💻 Девелопер", callback_data="show_dev")
    kb.adjust(1, 2)
    
    try:
        await bot.send_photo(chat_id=message.chat.id, photo=MONOPOLY_IMG, caption=f"{BANNER}\n\nДобро пожаловать в SHIT DAILY Monopoly!", reply_markup=kb.as_markup())
    except:
        await message.answer(f"🖼 {MONOPOLY_IMG}\n\n{BANNER}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_lobby")
async def call_lobby(call: types.CallbackQuery):
    db_query("INSERT OR IGNORE INTO players (chat_id, user_id, name) VALUES (?, ?, ?)", (call.message.chat.id, call.from_user.id, call.from_user.first_name))
    players = db_query("SELECT name FROM players WHERE chat_id=?", (call.message.chat.id,))
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Вступить", callback_data="start_lobby")
    if len(players) >= 1: kb.button(text="▶️ Начать игру", callback_data="game_start")
    kb.adjust(1)
    try:
        await call.message.edit_caption(caption=f"{BANNER}\n\n👥 Игроков собрано: {len(players)}", reply_markup=kb.as_markup())
    except: pass
    await call.answer()

@dp.callback_query(F.data == "game_start")
async def call_start(call: types.CallbackQuery):
    await call.message.answer(get_phrase("start"), reply_markup=get_main_reply_kb())
    await call.message.delete()
    await call.answer()

@dp.message(F.text == "❌ Скрыть меню")
async def hide_m(m: types.Message):
    await m.answer(get_phrase("hide"), reply_markup=ReplyKeyboardRemove())
    await m.answer("🕹 УПРАВЛЕНИЕ В ЧАТЕ:", reply_markup=get_chat_inline_kb())

@dp.callback_query(F.data == "btn_restore")
async def restore_m(call: types.CallbackQuery):
    await call.message.delete()
    await call.message.answer(get_phrase("restore"), reply_markup=get_main_reply_kb())
    await call.answer()

@dp.message(F.text == "🎲 Бросить кубик")
@dp.callback_query(F.data == "btn_roll")
async def action_roll(event):
    m = event if isinstance(event, types.Message) else event.message
    await m.answer(get_phrase("roll"))
    dice = await m.answer_dice("🎲")
    await asyncio.sleep(3.5)
    await m.answer(get_phrase("result").format(v=dice.dice.value))
    if isinstance(event, types.CallbackQuery): await event.answer()

# --- [7] ЗАПУСК ---
@app.route('/')
def home(): return "OK", 200

def run_f(): app.run(host="0.0.0.0", port=PORT)

async def main():
    init_db()
    Thread(target=run_f, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
