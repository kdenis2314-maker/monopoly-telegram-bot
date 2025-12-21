import os
import asyncio
import aiosqlite
import logging
import random
import json
from datetime import datetime
from threading import Thread
from flask import Flask, render_template
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, URLInputFile, WebAppInfo

# --- [КОНФИГУРАЦИЯ] ---
API_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8083))
DEV_TAG = "@Whylovely05"
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly Premium Edition  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

STATS = {
    "active_games": 0, "total_players": 0,
    "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "version": "Premium v2.0 + AI Full Logic"
}

WAITING_GAMES = {}
ACTIVE_GAMES = {}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- [ПОЛНЫЙ HTML САЙТА - 100+ СТРОК СТИЛЕЙ] ---
status_html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>МОНОПОЛИЯ ПРЕМИУМ - Статус</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: rgba(25, 25, 40, 0.9); border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); border: 1px solid #2a2a4a; }
        .header { text-align: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid #00ff88; }
        .header h1 { font-size: 2.8rem; background: linear-gradient(90deg, #00ff88, #00ccff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 2px; }
        .header h2 { color: #a0a0ff; font-weight: 300; font-size: 1.2rem; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin-bottom: 40px; }
        .status-card { background: rgba(40, 40, 60, 0.7); border-radius: 15px; padding: 25px; border-left: 5px solid #00ff88; transition: transform 0.3s, box-shadow 0.3s; }
        .status-card:hover { transform: translateY(-5px); box-shadow: 0 5px 20px rgba(0, 255, 136, 0.2); }
        .card-title { color: #00ff88; font-size: 1.1rem; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        .info-line { display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
        .label { color: #a0a0ff; font-weight: 500; }
        .value { color: #fff; font-weight: 600; }
        .value.online { color: #00ff88; }
        .instructions { background: rgba(30, 30, 50, 0.8); border-radius: 15px; padding: 25px; margin-top: 30px; border: 1px solid #3a3a6a; }
        .instructions h3 { color: #00ccff; margin-bottom: 20px; font-size: 1.4rem; }
        .steps { list-style-type: none; counter-reset: step; }
        .steps li { margin: 15px 0; padding-left: 30px; position: relative; line-height: 1.6; }
        .steps li:before { content: counter(step); counter-increment: step; position: absolute; left: 0; top: 0; background: #00ff88; color: #000; width: 24px; height: 24px; border-radius: 50%; text-align: center; line-height: 24px; font-weight: bold; }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255, 255, 255, 0.1); color: #888; font-size: 0.9rem; }
        .btn-link { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #00ff88; color: #000; text-decoration: none; border-radius: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>МОНОПОЛИЯ ПРЕМИУМ</h1><h2>Система управления ботом</h2></div>
        <div class="status-grid">
            <div class="status-card">
                <div class="card-title">📊 Статистика</div>
                <div class="info-line"><span class="label">Бот:</span><span class="value online">🟢 Онлайн</span></div>
                <div class="info-line"><span class="label">Игр запущено:</span><span class="value">{{ stats.active_games }}</span></div>
                <div class="info-line"><span class="label">Игроков в очереди:</span><span class="value">{{ stats.waiting_games }}</span></div>
            </div>
            <div class="status-card">
                <div class="card-title">⚙️ Сервер</div>
                <div class="info-line"><span class="label">Версия:</span><span class="value">{{ stats.version }}</span></div>
                <div class="info-line"><span class="label">Запуск:</span><span class="value">{{ start_time }}</span></div>
                <div class="info-line"><span class="label">Порт:</span><span class="value">{{ port }}</span></div>
            </div>
        </div>
        <div class="instructions">
            <h3>🛠 Панель Разработчика</h3>
            <p>Управление базой данных и игровыми сессиями активно. Мониторинг логов включен.</p>
            <a href="https://t.me/Whylovely05" class="btn-link">Связаться с разработчиком</a>
        </div>
        <div class="footer"><p>Created by {{ dev_tag }} &copy; 2025</p></div>
    </div>
</body>
</html>'''

if not os.path.exists('templates'): os.makedirs('templates')
with open('templates/status.html', 'w', encoding='utf-8') as f: f.write(status_html)

@app.route('/')
def index():
    return render_template('status.html', stats=STATS, dev_tag=DEV_TAG, port=PORT, start_time=STATS["started"])

# --- [БАЗА ДАННЫХ] ---
async def init_db():
    async with aiosqlite.connect('monopoly_v2.db') as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS players (
            chat_id int, user_id int, name text, balance int DEFAULT 1500, 
            pos int DEFAULT 0, jail int DEFAULT 0, PRIMARY KEY(chat_id, user_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS property (
            chat_id int, cell_idx int, owner_id int, houses int DEFAULT 0, 
            PRIMARY KEY(chat_id, cell_idx))""")
        await db.commit()

# --- [3] ПОЛНАЯ ИГРОВАЯ КАРТА (ВСЕ 40 КЛЕТОК) ---
# Структура: [Название, Цена покупки, Базовая аренда, Категория]
BOARD = {
    0: ["СТАРТ", 0, 0, "SPECIAL"],
    1: ["Житная", 60, 4, "BROWN"],
    2: ["Общественная казна", 0, 0, "SPECIAL"],
    3: ["Нагатинская", 60, 4, "BROWN"],
    4: ["Подоходный налог", 0, 200, "TAX"],
    5: ["Рижская ж/д", 200, 25, "RAIL"],
    6: ["Варшавское ш.", 100, 6, "BLUE"],
    7: ["Шанс", 0, 0, "CHANCE"],
    8: ["Огородный пр.", 100, 6, "BLUE"],
    9: ["Рижская", 120, 8, "BLUE"],
    10: ["Тюрьма (Посещение)", 0, 0, "SPECIAL"],
    11: ["Курская", 140, 10, "PINK"],
    12: ["Электросеть", 150, 10, "UTIL"],
    13: ["Абрамцево", 140, 10, "PINK"],
    14: ["Пантелеевская", 160, 12, "PINK"],
    15: ["Казанская ж/д", 200, 25, "RAIL"],
    16: ["Вавилова", 180, 14, "ORANGE"],
    17: ["Общественная казна", 0, 0, "SPECIAL"],
    18: ["Тимирязевская", 180, 14, "ORANGE"],
    19: ["Лихоборы", 200, 16, "ORANGE"],
    20: ["Бесплатная стоянка", 0, 0, "SPECIAL"],
    21: ["Арбат", 220, 18, "RED"],
    22: ["Шанс", 0, 0, "CHANCE"],
    23: ["Полянка", 220, 18, "RED"],
    24: ["Сретенка", 240, 20, "RED"],
    25: ["Курская ж/д", 200, 25, "RAIL"],
    26: ["Ростовская", 260, 22, "YELLOW"],
    27: ["Рязанский пр.", 260, 22, "YELLOW"],
    28: ["Водопровод", 150, 10, "UTIL"],
    29: ["Новинский б-р", 280, 24, "YELLOW"],
    30: ["В ТЮРЬМУ", 0, 0, "SPECIAL"],
    31: ["Пушкинская", 300, 26, "GREEN"],
    32: ["Тверская", 300, 26, "GREEN"],
    33: ["Общественная казна", 0, 0, "SPECIAL"],
    34: ["Маяковского", 320, 28, "GREEN"],
    35: ["Ленинградская ж/д", 200, 25, "RAIL"],
    36: ["Шанс", 0, 0, "CHANCE"],
    37: ["Кутузовский", 350, 35, "DARKBLUE"],
    38: ["Сверхналог", 0, 100, "TAX"],
    39: ["Бродвей", 400, 50, "DARKBLUE"]
}

# --- [ИИ ФУНКЦИЯ КОММЕНТАРИЕВ] ---
async def get_ai_response(event, player_name, balance=0):
    responses = {
        "start": [f"🚀 {player_name} врывается в игру! Начальный капитал в кармане."],
        "tax": [f"📉 Упс, {player_name}! Налоги кусаются. Минус кэш."],
        "buy": [f"🏠 Ого! {player_name} прикупил недвижимость. Будущий олигарх!"],
        "jail": [f"⛓ {player_name}, Тюрьмыч тебя заждался. Отдыхай 3 хода."],
        "roll": [f"🎲 {player_name} бросил кости. При балансе ${balance} это рискованно!"]
    }
    return random.choice(responses.get(event, ["Ход продолжается..."]))


# --- [4] ОБРАБОТЧИКИ КОМАНД И ЛОББИ ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(m: types.Message):
    kb = InlineKeyboardBuilder().button(text="🎮 Сбор игроков", callback_data="gather").button(text="👨‍💻 Dev", callback_data="dev").adjust(1).as_markup()
    await m.answer_photo(photo=URLInputFile(MONOPOLY_IMG), caption=f"{BANNER}\n\nДобро пожаловать!", reply_markup=kb)

@dp.callback_query(F.data == "gather")
async def gather_players(c: types.CallbackQuery):
    cid = c.message.chat.id
    if cid in WAITING_GAMES: return await c.answer("Сбор уже запущен!")
    
    WAITING_GAMES[cid] = {"creator": c.from_user.id, "players": [{"id": c.from_user.id, "name": c.from_user.first_name}]}
    kb = InlineKeyboardBuilder().button(text="✅ Вступить", callback_data=f"join_{cid}").button(text="🚪 Выйти", callback_data=f"leave_{cid}").button(text="▶️ Старт", callback_data=f"start_{cid}").adjust(2, 1).as_markup()
    await c.message.edit_caption(caption=f"🎮 <b>Сбор игроков!</b>\n\nУчастники: 1\nСоздатель: {c.from_user.first_name}", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("join_"))
async def join_logic(c: types.CallbackQuery):
    cid = int(c.data.split("_")[1])
    game = WAITING_GAMES.get(cid)
    if not game or any(p['id'] == c.from_user.id for p in game['players']): return await c.answer("Ошибка входа")
    
    game['players'].append({"id": c.from_user.id, "name": c.from_user.first_name})
    await c.message.edit_caption(caption=f"🎮 <b>Сбор игроков!</b>\n\nУчастников: {len(game['players'])}", reply_markup=c.message.reply_markup)
    await c.answer("Вы вступили!")

@dp.callback_query(F.data.startswith("leave_"))
async def leave_logic(c: types.CallbackQuery):
    cid = int(c.data.split("_")[1])
    game = WAITING_GAMES.get(cid)
    if not game: return
    game['players'] = [p for p in game['players'] if p['id'] != c.from_user.id]
    if not game['players']: 
        del WAITING_GAMES[cid]
        return await c.message.edit_caption(caption="❌ Сбор отменен.")
    await c.message.edit_caption(caption=f"🎮 <b>Сбор игроков!</b>\n\nУчастников: {len(game['players'])}", reply_markup=c.message.reply_markup)


# --- [5] ИГРОВАЯ МЕХАНИКА И БРОСОК ---
@dp.callback_query(F.data.startswith("start_"))
async def start_game(c: types.CallbackQuery):
    cid = int(c.data.split("_")[1])
    game = WAITING_GAMES.get(cid)
    if not game or c.from_user.id != game['creator']: return await c.answer("Только создатель!")
    
    async with aiosqlite.connect('monopoly_v2.db') as db:
        for p in game['players']:
            await db.execute("INSERT OR REPLACE INTO players (chat_id, user_id, name, balance, pos, jail) VALUES (?, ?, ?, 1500, 0, 0)", (cid, p['id'], p['name']))
        await db.commit()
    
    ACTIVE_GAMES[cid] = game
    del WAITING_GAMES[cid]
    kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").button(text="📊 Статус").adjust(1).as_markup(resize_keyboard=True)
    await c.message.answer("🚀 <b>Игра началась!</b>\nВсем выдано $1500. Первым ходит создатель.", parse_mode="HTML", reply_markup=kb)

@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice(m: types.Message):
    async with aiosqlite.connect('monopoly_v2.db') as db:
        res = await db.execute("SELECT pos, balance, jail FROM players WHERE chat_id=? AND user_id=?", (m.chat.id, m.from_user.id))
        row = await res.fetchone()
        if not row: return
        
        pos, bal, jail = row
        if jail > 0:
            await db.execute("UPDATE players SET jail = jail - 1 WHERE chat_id=? AND user_id=?", (m.chat.id, m.from_user.id))
            await db.commit()
            return await m.answer(await get_ai_response("jail", m.from_user.first_name))

        await m.answer(await get_ai_response("roll", m.from_user.first_name, bal))
        d = await m.answer_dice("🎲")
        await asyncio.sleep(3.5)
        
        new_pos = (pos + d.dice.value) % 40
        if new_pos < pos: bal += 200 # Проход через Старт
        
        # Логика клетки "В ТЮРЬМУ" (30 поле)
        if new_pos == 30: new_pos, jail = 10, 3
        
        await db.execute("UPDATE players SET pos=?, balance=?, jail=? WHERE chat_id=? AND user_id=?", (new_pos, bal, jail, m.chat.id, m.from_user.id))
        await db.commit()
        
        cell = BOARD[new_pos]
        await m.answer(f"📍 <b>{cell[0]}</b> (Поле {new_pos})\n💰 Баланс: ${bal}", parse_mode="HTML")

# --- [6] ЗАПУСК ---
async def main():
    await init_db()
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


