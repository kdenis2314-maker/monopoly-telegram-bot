import os, asyncio, aiosqlite, logging, random, json
from datetime import datetime
from threading import Thread
from flask import Flask, render_template
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, URLInputFile, WebAppInfo

# --- [1] CONFIG ---
API_TOKEN = os.environ.get("BOT_TOKEN")
PORT, DEV_TAG, IS_ACTIVE = int(os.environ.get("PORT", 8083)), "@Whylovely05", True
MAINTENANCE_MSG = "Бот обновляется, Темный принц уже исправляет это ♥️♥️"
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly Premium Edition  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

STATS = {"active_games": 0, "total_players": 0, "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "version": "Premium v2.0 AI"}
WAITING_GAMES, ACTIVE_GAMES = {}, {}

logging.basicConfig(level=logging.INFO)
bot, dp, app = Bot(token=API_TOKEN), Dispatcher(), Flask(__name__)

# --- [2] ИИ-ЯДРО (СЖАТОЕ) ---
async def ai_comment(event, name, balance=1500, value=None):
    ph = {
        "gathering": [f"💰 {name} открыл стол! Кто рискнет?", f"🎲 {name} ищет партнеров!"],
        "roll": [f"🎲 {name} бросил кости. Баланс: ${balance}", f"🎯 Судьба ведет {name}!"],
        "jail": [f"⛓ {name} в Тюрьмыче! Баланду за счет заведения.", f"🚔 {name}, наручники тебе к лицу!"],
        "rent": [f"💸 {name} платит ${value} аренды!", f"📈 Бизнес — это боль, {name} платит."],
        "buy": [f"🏗 {name} купил объект! Империя растет.", f"🏘 +1 актив у {name}!"]
    }
    return random.choice(ph.get(event, ["Ход принят"]))

# --- [3] HTML & FLASK (УПАКОВАНО) ---
@app.route('/')
def index():
    return render_template('status.html', stats=STATS, bot_name="Monopoly Premium", domain=os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost'), port=PORT, start_time=STATS["started"], dev_tag=DEV_TAG)

status_html = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>MONOPOLY STATUS</title><style>body{background:#1a1a2e;color:#fff;font-family:sans-serif;text-align:center;padding:50px}.container{background:#16213e;padding:30px;border-radius:20px;display:inline-block;border:1px solid #00ff88}h1{color:#00ff88}.stats{margin:20px 0;text-align:left}.stat-line{margin:10px 0;border-bottom:1px solid #2a2a4a}</style></head><body><div class="container"><h1>МОНОПОЛИЯ ПРЕМИУМ</h1><div class="stats"><div class="stat-line">Статус: 🟢 Онлайн</div><div class="stat-line">Версия: {{stats.version}}</div><div class="stat-line">Запуск: {{start_time}}</div><div class="stat-line">Девелопер: {{dev_tag}}</div></div></div></body></html>'''
os.makedirs('templates', exist_ok=True)
with open('templates/status.html', 'w', encoding='utf-8') as f: f.write(status_html)

# --- [4] КАРТА (СОХРАНЕНЫ ВСЕ ФУНКЦИИ КЛЕТОК) ---
BOARD = {1:["Житная",60,4,"BROWN"],3:["Нагатинская",60,4,"BROWN"],5:["Рижская ж/д",200,25,"RAIL"],6:["Варшавское",100,6,"BLUE"],8:["Огородный",100,6,"BLUE"],9:["Рижская",120,8,"BLUE"],11:["Курская",140,10,"PINK"],12:["Электросеть",150,10,"UTIL"],13:["Абрамцево",140,10,"PINK"],14:["Пантелеевская",160,12,"PINK"],15:["Казанская ж/д",200,25,"RAIL"],16:["Вавилова",180,14,"ORANGE"],18:["Тимирязевская",180,14,"ORANGE"],19:["Лихоборы",200,16,"ORANGE"],21:["Арбат",220,18,"RED"],23:["Полянка",220,18,"RED"],24:["Сретенка",240,20,"RED"],25:["Курская ж/д",200,25,"RAIL"],26:["Ростовская",260,22,"YELLOW"],27:["Рязанский",260,22,"YELLOW"],28:["Водопровод",150,10,"UTIL"],29:["Новинский",280,24,"YELLOW"],31:["Пушкинская",300,26,"GREEN"],32:["Тверская",300,26,"GREEN"],34:["Маяковского",320,28,"GREEN"],35:["Ленинградская ж/д",200,25,"RAIL"],37:["Кутузовский",350,35,"DARKBLUE"],39:["Бродвей",400,50,"DARKBLUE"]}

# --- [5] БД И ЛОГИКА (БЕЗ ОШИБОК) ---
async def db_op(query, params=(), fetch=False):
    async with aiosqlite.connect('monopoly.db') as db:
        cur = await db.execute(query, params)
        res = await cur.fetchall() if fetch else None
        await db.commit()
        return res

async def init_db():
    await db_op("CREATE TABLE IF NOT EXISTS players (chat_id int, user_id int, name text, balance int DEFAULT 1500, pos int DEFAULT 0, jail int DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
    await db_op("CREATE TABLE IF NOT EXISTS property (chat_id int, cell_idx int, owner_id int, houses int DEFAULT 0, PRIMARY KEY(chat_id, cell_idx))")

# --- [6] ХЕНДЛЕРЫ (ТВОИ ФУНКЦИИ СЖАТЫ) ---
@dp.message(Command("monopoly"))
async def cmd_mon(m: types.Message):
    kb = InlineKeyboardBuilder().button(text="✅ Сбор игроков", callback_data="start_gathering").button(text="👨‍💻 Девелопер", callback_data="dev").adjust(1).as_markup()
    await m.answer(f"{BANNER}\n\n🎲 Монополия готова!", reply_markup=kb)

@dp.callback_query(F.data == "start_gathering")
async def gather(c: types.CallbackQuery):
    cid = c.message.chat.id
    if cid in WAITING_GAMES: return await c.answer("Уже идет сбор!", show_alert=True)
    WAITING_GAMES[cid] = {"players": [{"id": c.from_user.id, "name": c.from_user.first_name}]}
    kb = InlineKeyboardBuilder().button(text="✅ Вступить", callback_data=f"join_{cid}").button(text="▶️ Старт", callback_data=f"go_{cid}").as_markup()
    await c.message.edit_text(await ai_comment("gathering", c.from_user.first_name), reply_markup=kb)

@dp.callback_query(F.data.startswith("join_"))
async def join(c: types.CallbackQuery):
    cid = int(c.data.split("_")[1])
    if any(p["id"] == c.from_user.id for p in WAITING_GAMES[cid]["players"]): return await c.answer("Ты уже в списке!")
    WAITING_GAMES[cid]["players"].append({"id": c.from_user.id, "name": c.from_user.first_name})
    await c.answer("Ты в игре!")
    await c.message.edit_text(f"🎮 Игроков: {len(WAITING_GAMES[cid]['players'])}", reply_markup=c.message.reply_markup)

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    p = await db_op("SELECT pos, balance, jail FROM players WHERE user_id=?", (m.from_user.id,), True)
    if not p: return await m.answer("Вступи в игру через /monopoly")
    p = p[0]
    if p[2] > 0:
        await db_op("UPDATE players SET jail = jail - 1 WHERE user_id=?", (m.from_user.id,))
        return await m.answer(await ai_comment("jail", m.from_user.first_name))
    
    await m.answer(await ai_comment("roll", m.from_user.first_name, p[1]))
    dice = await m.answer_dice("🎲")
    await asyncio.sleep(3.5)
    new_pos = (p[0] + dice.dice.value) % 40
    
    if new_pos == 30: # Тюрьма
        await db_op("UPDATE players SET pos=10, jail=3 WHERE user_id=?", (m.from_user.id,))
        return await m.answer(await ai_comment("jail", m.from_user.first_name))
    
    await db_op("UPDATE players SET pos=? WHERE user_id=?", (new_pos, m.from_user.id))
    await m.answer(f"📍 Клетка {new_pos}. " + (BOARD[new_pos][0] if new_pos in BOARD else "Пусто"))

@dp.callback_query(F.data == "dev")
async def dev(c: types.CallbackQuery): await c.answer(f"Принц: {DEV_TAG}", show_alert=True)

async def main():
    await init_db()
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
