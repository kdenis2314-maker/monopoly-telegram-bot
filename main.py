import os, asyncio, aiosqlite, logging, random
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, URLInputFile

# --- [1] ЦИТАДЕЛЬ ПРИНЦА ---
API_TOKEN = os.getenv("BOT_TOKEN") or "ТВОЙ_ТОКЕН_ЗДЕСЬ"
PORT = int(os.environ.get("PORT", 8083))
DEV_TAG = "@Whylovely05"

# ГЛАВНЫЙ РЫЧАГ (True - играем, False - Принц правит код)
IS_ACTIVE = True 
MAINTENANCE_MSG = "Бот обновляется или сломался, простите за неудобства, Темный принц уже исправляет это ♥️♥️"

BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly AI Edition  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- [2] ПРОВЕРКА СТАТУСА ПРИНЦА (ФИЛЬТР) ---
@dp.message(lambda m: not IS_ACTIVE)
@dp.callback_query(lambda c: not IS_ACTIVE)
async def maintenance_handler(event):
    if isinstance(event, types.Message):
        await event.answer(MAINTENANCE_MSG)
    elif isinstance(event, types.CallbackQuery):
        await event.answer(MAINTENANCE_MSG, show_alert=True)

# --- [3] ИИ-ГОЛОС ---
async def ai_say(event, name):
    phrases = {
        "roll": [f"🎲 {name} бросает вызов судьбе!", f"🎯 Кубики летят! Что скажет ИИ для {name}?", f"🎰 Время делать деньги, {name}!"],
        "jail": [f"⛓ {name}, Темный Принц выписал тебе путевку в СИЗО.", f"👮‍♂️ {name} за решеткой. Тишина в камере!", f"🚔 Допрыгался, {name}. Тюрьма!"],
        "start": [f"🚀 Экономическая бойня началась!", f"🔥 Погнали! Кто станет новым королем?", f"💰 Время грабить и богатеть!"]
    }
    return random.choice(phrases.get(event, ["Ход принят."]))

# --- [4] БАЗА ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect('monopoly_v5.db') as db:
        await db.execute("CREATE TABLE IF NOT EXISTS players (chat_id int, user_id int, name text, balance int DEFAULT 1500, pos int DEFAULT 0, jail int DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
        await db.execute("CREATE TABLE IF NOT EXISTS awards (user_id int, title text, chat_id int, PRIMARY KEY(user_id, title))")
        await db.commit()

# --- [5] КЛАВИАТУРЫ ---
def get_main_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик")
    kb.button(text="🏠 Построить дом")
    kb.button(text="📊 Мои активы")
    kb.button(text="❌ Скрыть меню")
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)

# --- [6] ХЕНДЛЕРЫ ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Вступить", callback_data="join")
    kb.button(text="▶️ Старт", callback_data="start")
    kb.button(text="👨‍💻 Девелопер", callback_data="dev")
    kb.adjust(2, 1)
    
    try:
        await bot.send_photo(message.chat.id, photo=URLInputFile(MONOPOLY_IMG), 
                             caption=f"{BANNER}\n\nПод присмотром Темного Принца. Готовы?", reply_markup=kb.as_markup())
    except:
        await message.answer(f"{BANNER}\n\nСтарт игры!", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "join")
async def join(c: types.CallbackQuery):
    await c.answer("Ты в деле! 💰")
    async with aiosqlite.connect('monopoly_v5.db') as db:
        await db.execute("INSERT OR IGNORE INTO players (chat_id, user_id, name) VALUES (?,?,?)", (c.message.chat.id, c.from_user.id, c.from_user.first_name))
        await db.commit()

@dp.callback_query(F.data == "start")
async def start(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer(await ai_say("start", ""), reply_markup=get_main_kb())

@dp.callback_query(F.data == "dev")
async def dev(c: types.CallbackQuery):
    await c.answer(f"Создатель: {DEV_TAG}", show_alert=True)

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    async with aiosqlite.connect('monopoly_v5.db') as db:
        res = await db.execute("SELECT pos, jail FROM players WHERE user_id=? AND chat_id=?", (m.from_user.id, m.chat.id))
        p = await res.fetchone()
        if not p: return await m.answer("Вступи в игру через /monopoly")
        
        await m.answer(await ai_say("roll", m.from_user.first_name))
        dice = await m.answer_dice("🎲")
        await asyncio.sleep(3.5)
        
        new_pos = (p[0] + dice.dice.value) % 40
        await db.execute("UPDATE players SET pos=? WHERE user_id=?", (new_pos, m.from_user.id))
        await db.commit()
        await m.answer(f"📍 Ты на клетке {new_pos}.")

# --- [7] ЗАПУСК ---
@app.route('/')
def home(): return "AI Monopoly Online"

async def main():
    await init_db()
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
