import os, asyncio, random, sqlite3, aiohttp, signal, sys
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- КОНФИГ ---
TOKEN = os.getenv("BOT_TOKEN")
DEV_TAG = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8083))
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"
ERROR_MSG = "Бот обновляется или сломался, простите за неудобства, Темный принц их уже исправляет ♥️♥️"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)
is_active = True # Флаг готовности

# --- 🗄️ БАЗА ДАННЫХ ---
def db_query(sql, params=()):
    with sqlite3.connect('monopoly_final.db') as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.fetchall()

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS players 
        (chat_id int, user_id int, name text, balance int, pos int, jail int, PRIMARY KEY(chat_id, user_id))''')
    db_query('''CREATE TABLE IF NOT EXISTS property 
        (chat_id int, cell_idx int, owner_id int, houses int, PRIMARY KEY(chat_id, cell_idx))''')

# --- 🗺️ КАРТА (Индекс: Название, Цена, Аренда) ---
MAP_DATA = {
    1: {"name": "Житная", "p": 60, "r": 2}, 3: {"name": "Нагатинская", "p": 60, "r": 4},
    6: {"name": "Варшавское ш.", "p": 100, "r": 6}, 8: {"name": "Огородный пр.", "p": 100, "r": 6},
    # Можно расширить до 40 по аналогии
}

# --- 🧠 ИИ-ГОЛОС ---
async def ai_say(text):
    try:
        url = "https://text.pollinations.ai/"
        prompt = f"Ты Монопольный Бро, живой ведущий. Создатель {DEV_TAG}. Ответь кратко и весело: {text}"
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}{prompt}") as r:
                return await r.text() if r.status == 200 else "Удачи на кубиках! 🎲"
    except: return "Бро, я в деле! ✨"

# --- ⌨️ КНОПКИ ---
def get_lobby_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="👨‍💻 О девелопере", callback_data="dev")
    kb.button(text="📜 Правила игры", callback_data="rules")
    kb.button(text="🎲 Начать сбор игроков", callback_data="start_lobby")
    kb.adjust(1)
    return kb.as_markup()

def get_game_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Сделать ход")
    kb.button(text="🏠 Мои Активы")
    kb.button(text="🤝 Торговля")
    kb.button(text="❌ Скрыть меню")
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)

# --- 🚀 КОМАНДЫ ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if not is_active: return await message.answer(ERROR_MSG)
    await message.answer_photo(photo=MONOPOLY_IMG, caption=f"🎭 **МОНОПОЛИЯ ОТ {DEV_TAG}**\n\nПривет! Я твой Монопольный Бро. Готов разбогатеть? Выбирай действие ниже! 👇", reply_markup=get_lobby_kb())

@dp.callback_query(F.data == "dev")
async def call_dev(call: types.CallbackQuery):
    await call.answer(f"Создатель: {DEV_TAG}. Темный принц кода! 👑", show_alert=True)

@dp.callback_query(F.data == "rules")
async def call_rules(call: types.CallbackQuery):
    await call.message.answer("📜 **ПРАВИЛА:**\n1. Ходи кубиком.\n2. Покупай улицы.\n3. Плати за аренду (остановку).\n4. Выживи и стань богаче всех! 💰")
    await call.answer()

@dp.callback_query(F.data == "start_lobby")
async def call_lobby(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    db_query("INSERT OR IGNORE INTO players VALUES (?, ?, ?, 1500, 0, 0)", (cid, uid, call.from_user.first_name))
    await call.message.answer("🚀 **СБОР НАЧАТ!** Нижнее меню активировано. Кто первый?", reply_markup=get_game_kb())
    await call.answer()

@dp.message(F.text == "🎲 Сделать ход")
async def roll(message: types.Message):
    if not is_active: return await message.answer(ERROR_MSG)
    cid, uid = message.chat.id, message.from_user.id
    p = db_query("SELECT name, balance, pos FROM players WHERE chat_id=? AND user_id=?", (cid, uid))
    if not p: return await message.answer("Сначала нажми 'Начать сбор'! 😊")
    
    dice = await message.answer_dice("🎲")
    val = dice.dice.value
    await asyncio.sleep(3.5)
    
    new_pos = (p[0][2] + val) % 40
    new_bal = p[0][1] + (200 if new_pos < p[0][2] else 0)
    db_query("UPDATE players SET pos=?, balance=? WHERE chat_id=? AND user_id=?", (new_pos, new_bal, cid, uid))
    
    comment = await ai_say(f"Игрок встал на клетку {new_pos}")
    
    res_text = f"🏃 **{p[0][0]}**, выпало **{val}**!\n📍 Позиция: {new_pos}\n💵 Баланс: ${new_bal}\n\n😊 {comment}"
    
    if new_pos in MAP_DATA:
        cell = MAP_DATA[new_pos]
        prop = db_query("SELECT owner_id FROM property WHERE chat_id=? AND cell_idx=?", (cid, new_pos))
        if not prop:
            ikb = InlineKeyboardBuilder().button(text=f"✅ Купить {cell['name']} (${cell['p']})", callback_data=f"buy_{new_pos}").as_markup()
            await message.answer(f"🏠 Эта улица свободна! Хочешь купить **{cell['name']}**?", reply_markup=ikb)
        elif prop[0][0] != uid:
            db_query("UPDATE players SET balance = balance - ? WHERE chat_id=? AND user_id=?", (cell['r'], cid, uid))
            res_text += f"\n\n💸 Остановка! Ты заплатил ${cell['r']} за аренду."
            
    await message.answer(res_text)

@dp.callback_query(F.data.startswith("buy_"))
async def buy(call: types.CallbackQuery):
    idx = int(call.data.split("_")[1])
    cid, uid = call.message.chat.id, call.from_user.id
    bal = db_query("SELECT balance FROM players WHERE chat_id=? AND user_id=?", (cid, uid))[0][0]
    if bal >= MAP_DATA[idx]['p']:
        db_query("UPDATE players SET balance=balance-? WHERE chat_id=? AND user_id=?", (MAP_DATA[idx]['p'], cid, uid))
        db_query("INSERT INTO property VALUES (?, ?, ?, 0)", (cid, idx, uid))
        await call.message.edit_text(f"🏘 Ты купил {MAP_DATA[idx]['name']}! Поздравляю!")
    else: await call.answer("Маловато денег, бро! ❌", show_alert=True)

@dp.message(F.text == "❌ Скрыть меню")
async def hide(message: types.Message):
    await message.answer("Кнопки скрыты. Жми /monopoly, чтобы вернуть! 👋", reply_markup=types.ReplyKeyboardRemove())

@dp.message(F.text & ~F.text.startswith('/'))
async def chat(message: types.Message):
    if (message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id) or message.chat.type == 'private':
        await message.answer(f"😊 {await ai_say(message.text)}")

# --- 🌐 СЕРВЕР ---
@app.route('/')
def h(): return "OK"

async def main():
    global is_active
    init_db()
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    try: await dp.start_polling(bot)
    except: 
        is_active = False
        print(ERROR_MSG)

if __name__ == "__main__":
    asyncio.run(main())
