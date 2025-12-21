import os, asyncio, aiosqlite, logging, random
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, URLInputFile

# --- [1] ЦИТАДЕЛЬ И НАСТРОЙКИ ---
API_TOKEN = os.getenv("BOT_TOKEN") or "ТВОЙ_ТОКЕН_ЗДЕСЬ"
PORT = int(os.environ.get("PORT", 8083))
DEV_TAG = "@Whylovely05"
IS_ACTIVE = True  # Глобальный рубильник Принца
MAINTENANCE_MSG = "Бот обновляется, Темный принц уже исправляет это ♥️♥️"
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly AI Edition  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- [2] ИГРОВАЯ ДАТА-БАЗА (40 КЛЕТОК) ---
BOARD = {
    1: ["Житная", 60, 4, "BROWN"], 3: ["Нагатинская", 60, 4, "BROWN"],
    5: ["Рижская ж/д", 200, 25, "RAIL"], 6: ["Варшавское ш.", 100, 6, "BLUE"],
    8: ["Огородный пр.", 100, 6, "BLUE"], 9: ["Рижская", 120, 8, "BLUE"],
    11: ["Курская", 140, 10, "PINK"], 12: ["Электросеть", 150, 10, "UTIL"],
    13: ["Абрамцево", 140, 10, "PINK"], 14: ["Пантелеевская", 160, 12, "PINK"],
    15: ["Казанская ж/д", 200, 25, "RAIL"], 16: ["Вавилова", 180, 14, "ORANGE"],
    18: ["Тимирязевская", 180, 14, "ORANGE"], 19: ["Лихоборы", 200, 16, "ORANGE"],
    21: ["Арбат", 220, 18, "RED"], 23: ["Полянка", 220, 18, "RED"],
    24: ["Сретенка", 240, 20, "RED"], 25: ["Курская ж/д", 200, 25, "RAIL"],
    26: ["Ростовская", 260, 22, "YELLOW"], 27: ["Рязанский пр.", 260, 22, "YELLOW"],
    28: ["Водопровод", 150, 10, "UTIL"], 29: ["Новинский б-р", 280, 24, "YELLOW"],
    31: ["Пушкинская", 300, 26, "GREEN"], 32: ["Тверская", 300, 26, "GREEN"],
    34: ["Маяковского", 320, 28, "GREEN"], 35: ["Ленинградская ж/д", 200, 25, "RAIL"],
    37: ["Кутузовский", 350, 35, "DARKBLUE"], 39: ["Бродвей", 400, 50, "DARKBLUE"]
}

# --- [3] ИИ-ГЕНЕРАТОР ФРАЗ (БЕЗ ШАБЛОНОВ) ---
async def ai_voice(event, name, value=None):
    phrases = {
        "roll": [f"🎲 {name} кидает кости... Посмотрим на твое везение!", f"🎯 Кубики в воздухе! Что приготовил рандом для {name}?", f"🎰 Ставки сделаны, {name} делает ход!"],
        "jail": [f"⛓ {name}, Тюрьмыч ждет! Принц недоволен твоим поведением.", f"👮‍♂️ Наручники на {name}! 3 хода тишины и баланды.", f"🚔 {name}, следствие окончено. Ты в тюрьме!"],
        "chance": [f"🃏 Шанс! {name}, это может быть твой лучший или худший день.", f"🎰 Судьба играет с {name}... Тяни карту!", f"🎲 Рандомный подарок (или штраф) для {name}!"],
        "rent": [f"💸 {name} попал! ${value} аренды улетают владельцу.", f"💰 Казна {name} пустеет. Кто-то богатеет!", f"📈 Бизнес есть бизнес: {name} платит по счетам."],
        "win_achieve": [f"👑 Опа! {name} теперь настоящий Олигарх!", f"🏆 {name} забирает титул! Капитализм в действии."]
    }
    return random.choice(phrases.get(event, ["Ход принят!"]))

# --- [4] БАЗА ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect('monopoly_v100.db') as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS players (
            chat_id int, user_id int, name text, 
            balance int DEFAULT 1500, pos int DEFAULT 0, 
            jail int DEFAULT 0, PRIMARY KEY(chat_id, user_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS property (
            chat_id int, cell_idx int, owner_id int, houses int DEFAULT 0, 
            PRIMARY KEY(chat_id, cell_idx))""")
        await db.execute("CREATE TABLE IF NOT EXISTS awards (user_id int, title text, chat_id int)")
        await db.commit()

# --- [5] ЗАЩИТА ПРИНЦА (Многоуровневая) ---
@dp.message(lambda m: not IS_ACTIVE)
async def maintenance_m(m: types.Message): await m.answer(MAINTENANCE_MSG)

@dp.callback_query(lambda c: not IS_ACTIVE)
async def maintenance_c(c: types.CallbackQuery): await c.answer(MAINTENANCE_MSG, show_alert=True)

# --- [6] КЛАВИАТУРЫ ---
def main_reply_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик")
    kb.button(text="🏠 Построить")
    kb.button(text="📊 Активы")
    kb.button(text="🤝 Обмен")
    kb.button(text="❌ Скрыть меню")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

# --- [7] ЛОГИКА ИГРЫ (ОСНОВНОЙ ЦИКЛ) ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Вступить", callback_data="join")
    kb.button(text="▶️ Старт", callback_data="start")
    kb.button(text="👨‍💻 Девелопер", callback_data="dev")
    await bot.send_photo(message.chat.id, photo=URLInputFile(MONOPOLY_IMG), 
                         caption=f"{BANNER}\n\nДобро пожаловать в мир больших денег под присмотром Темного Принца!", 
                         reply_markup=kb.as_markup())

@dp.callback_query(F.data == "join")
async def join_player(c: types.CallbackQuery):
    await c.answer("Ты в реестре!")
    async with aiosqlite.connect('monopoly_v100.db') as db:
        await db.execute("INSERT OR IGNORE INTO players (chat_id, user_id, name) VALUES (?,?,?)", 
                         (c.message.chat.id, c.from_user.id, c.from_user.first_name))
        await db.commit()

@dp.callback_query(F.data == "start")
async def start_game(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("🚀 Монополия началась! Твой ход.", reply_markup=main_reply_kb())

@dp.message(F.text == "🎲 Бросить кубик")
async def roll_move(m: types.Message):
    async with aiosqlite.connect('monopoly_v100.db') as db:
        res = await db.execute("SELECT pos, balance, jail FROM players WHERE user_id=? AND chat_id=?", (m.from_user.id, m.chat.id))
        p = await res.fetchone()
        if not p: return await m.answer("Сначала /monopoly")

        if p[2] > 0:
            await db.execute("UPDATE players SET jail = jail - 1 WHERE user_id=?", (m.from_user.id,))
            await db.commit()
            return await m.answer(f"⛓ Ты в Тюрьмыче! Ждать еще {p[2]} х.")

        await m.answer(await ai_voice("roll", m.from_user.first_name))
        dice = await m.answer_dice("🎲")
        await asyncio.sleep(3.5)
        
        val = dice.dice.value
        new_pos = (p[0] + val) % 40
        
        # 1. Тюрьма (Клетка 30)
        if new_pos == 30:
            await db.execute("UPDATE players SET pos=10, jail=3 WHERE user_id=?", (m.from_user.id,))
            await db.commit()
            return await m.answer(await ai_voice("jail", m.from_user.first_name))

        # 2. Шанс (Клетки 2, 7, 17, 22, 33, 36)
        if new_pos in [2, 7, 17, 22, 33, 36]:
            change = random.choice([-200, -100, 50, 150, 300])
            await db.execute("UPDATE players SET balance = balance + ?, pos=? WHERE user_id=?", (change, new_pos, m.from_user.id))
            await db.commit()
            await m.answer(await ai_voice("chance", m.from_user.first_name))
            return await m.answer(f"🃏 Карта Шанса: {'+' if change > 0 else ''}{change}$!")

        # 3. Собственность
        await db.execute("UPDATE players SET pos=? WHERE user_id=?", (new_pos, m.from_user.id))
        await db.commit()

        if new_pos in BOARD:
            name, price, rent, color = BOARD[new_pos]
            own_res = await db.execute("SELECT owner_id, houses FROM property WHERE cell_idx=? AND chat_id=?", (new_pos, m.chat.id))
            owner = await own_res.fetchone()

            if not owner:
                kb = InlineKeyboardBuilder().button(text=f"💸 Купить ${price}", callback_data=f"buy_{new_pos}")
                kb.button(text="🔨 Аукцион", callback_data=f"auc_{new_pos}")
                return await m.answer(f"📍 {name} (${price}). Что делаем?", reply_markup=kb.as_markup())
            elif owner[0] != m.from_user.id:
                final_rent = rent * (owner[1] + 1)
                await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (final_rent, m.from_user.id))
                await db.execute("UPDATE players SET balance = balance + ? WHERE user_id=?", (final_rent, owner[0]))
                await db.commit()
                return await m.answer(await ai_voice("rent", m.from_user.first_name, final_rent))
        
        await m.answer(f"📍 Ты на клетке {new_pos}. Тут спокойно.")

# --- [8] ПОКУПКА И АУКЦИОН ---
@dp.callback_query(F.data.startswith("buy_"))
async def buy_prop(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    async with aiosqlite.connect('monopoly_v100.db') as db:
        await db.execute("INSERT INTO property (chat_id, cell_idx, owner_id) VALUES (?,?,?)", (c.message.chat.id, idx, c.from_user.id))
        await db.execute("UPDATE players SET balance = balance - ? WHERE user_id=?", (BOARD[idx][1], c.from_user.id))
        await db.commit()
    await c.message.edit_text(f"🏰 Поздравляю! {BOARD[idx][0]} теперь твоя!")
    await c.answer()

@dp.callback_query(F.data == "dev")
async def show_dev(c: types.CallbackQuery):
    await c.answer(f"Принц Кода: {DEV_TAG}", show_alert=True)

# --- [9] ЗАПУСК СЕРВЕРА ---
@app.route('/')
def home(): return "<h1>Monopoly AI v10.0 is Running</h1>"

async def main():
    await init_db()
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
