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

# --- [1] НАСТРОЙКИ И ПЕРЕМЕННЫЕ (ТВОЙ ОРИГИНАЛ) ---
API_TOKEN = os.environ.get("BOT_TOKEN")
if not API_TOKEN:
    logging.error("❌ BOT_TOKEN не найден в переменных окружения!")
    exit(1)

PORT = int(os.environ.get("PORT", 8083))
DEV_TAG = "@Whylovely05"
IS_ACTIVE = True
MAINTENANCE_MSG = "Бот обновляется, Темный принц уже исправляет это ♥️♥️"
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly Premium Edition  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

STATS = {
    "active_games": 0,
    "total_players": 0,
    "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "version": "Premium v2.0 + AI Core"
}

WAITING_GAMES = {}
ACTIVE_GAMES = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- [НОВОЕ: ИИ-БЛОК КОММЕНТАРИЕВ] ---
async def ai_commentator(event, name, balance=1500, value=None):
    phrases = {
        "gathering": [
            f"💰 {name} открывает бизнес-клуб! Кто готов рискнуть?",
            f"🎲 {name} начинает сбор. Принц следит за вашими ставками!",
            f"⚖️ {name} ищет достойных соперников для раздела империи."
        ],
        "roll": [
            f"🎲 {name} кидает кости! С балансом ${balance} это серьезный ход.",
            f"🎯 Кости брошены, {name}! Посмотрим, что скажет цифровая судьба."
        ],
        "jail": [
            f"⛓ {name}, Тюрьмыч ждал тебя! Присядь на 3 хода, подумай о бизнесе.",
            f"🚔 Наручники на {name}! Капитализм — штука суровая."
        ],
        "buy": [
            f"🏗 {name} расширяет влияние! Конкуренты нервно курят в сторонке.",
            f"🏘 Поздравляю с покупкой, {name}! Твоя империя растет."
        ]
    }
    return random.choice(phrases.get(event, ["Ход принят..."]))

# --- [2] HTML ШАБЛОН (ТВОЙ ПОЛНЫЙ ДИЗАЙН) ---
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ bot_name }}</h1>
            <h2>Панель мониторинга системы</h2>
        </div>
        <div class="status-grid">
            <div class="status-card">
                <div class="card-title">📊 Статистика</div>
                <div class="info-line"><span class="label">Статус:</span><span class="value online">🟢 Онлайн</span></div>
                <div class="info-line"><span class="label">Активных игр:</span><span class="value">{{ stats.active_games }}</span></div>
                <div class="info-line"><span class="label">В ожидании:</span><span class="value">{{ stats.waiting_games }}</span></div>
            </div>
            <div class="status-card">
                <div class="card-title">⚙️ Информация</div>
                <div class="info-line"><span class="label">Запущен:</span><span class="value">{{ start_time }}</span></div>
                <div class="info-line"><span class="label">Версия:</span><span class="value">{{ stats.version }}</span></div>
                <div class="info-line"><span class="label">Разработчик:</span><span class="value">{{ dev_tag }}</span></div>
            </div>
        </div>
        <div class="instructions">
            <h3>📝 Как начать играть?</h3>
            <ul class="steps">
                <li>Найдите бота в Telegram и отправьте команду /monopoly.</li>
                <li>Нажмите кнопку "Сбор игроков" для открытия лобби.</li>
                <li>Дождитесь друзей и начинайте захват империи!</li>
            </ul>
        </div>
        <div class="footer">
            <p>&copy; 2025 Monopoly Premium Edition. All rights reserved.</p>
        </div>
    </div>
</body>
</html>'''

@app.route('/')
def index():
    stats_copy = STATS.copy()
    stats_copy["active_games"] = len(ACTIVE_GAMES)
    stats_copy["waiting_games"] = len(WAITING_GAMES)
    return render_template('status.html', stats=stats_copy, bot_name="Monopoly Premium", 
                         start_time=stats_copy["started"], dev_tag=DEV_TAG, port=PORT)

# Создание папки и файла шаблона при запуске
if not os.path.exists('templates'):
    os.makedirs('templates')
with open('templates/status.html', 'w', encoding='utf-8') as f:
    f.write(status_html)

# --- [3] ПОЛНАЯ ИГРОВАЯ КАРТА (ИЗ ТВОЕГО ФАЙЛА) ---
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

# --- [4] БАЗА ДАННЫХ (БЕЗ ОШИБОК) ---
async def init_db():
    try:
        async with aiosqlite.connect('monopoly_v2.db') as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS players (
                chat_id int, user_id int, name text, 
                balance int DEFAULT 1500, pos int DEFAULT 0, 
                jail int DEFAULT 0, PRIMARY KEY(chat_id, user_id))""")
            await db.execute("""CREATE TABLE IF NOT EXISTS property (
                chat_id int, cell_idx int, owner_id int, houses int DEFAULT 0, 
                PRIMARY KEY(chat_id, cell_idx))""")
            await db.execute("CREATE TABLE IF NOT EXISTS awards (user_id int, title text, chat_id int)")
            await db.commit()
        logger.info("✅ БД инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")

# --- [5] КОМАНДЫ (ТВОЯ ЛОГИКА) ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if not IS_ACTIVE:
        return await message.answer(MAINTENANCE_MSG)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Сбор игроков", callback_data="start_player_gathering")
    builder.button(text="👨‍💻 Девелопер", callback_data="show_dev")
    builder.adjust(1)
    
    await message.answer_photo(
        photo=URLInputFile(MONOPOLY_IMG),
        caption=f"{BANNER}\n\n🎲 <b>Monopoly Premium</b>\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "show_dev")
async def show_dev(c: types.CallbackQuery):
    await c.answer(f"Принц проекта: {DEV_TAG}", show_alert=True)


# --- [6] ЛОГИКА СБОРА ИГРОКОВ (ПОЛНЫЙ ПЕРЕНОС) ---
@dp.callback_query(F.data == "start_player_gathering")
async def start_gathering(c: types.CallbackQuery):
    chat_id = c.message.chat.id
    if chat_id in WAITING_GAMES:
        return await c.answer("⚠️ Сбор уже запущен!", show_alert=True)
    
    ai_txt = await ai_commentator("gathering", c.from_user.first_name)
    WAITING_GAMES[chat_id] = {
        "creator_id": c.from_user.id,
        "players": [{"id": c.from_user.id, "name": c.from_user.first_name, "username": c.from_user.username}]
    }
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Вступить", callback_data=f"join_game_{chat_id}")
    builder.button(text="🚪 Выйти", callback_data=f"leave_game_{chat_id}")
    builder.button(text="▶️ Начать", callback_data=f"run_game_{chat_id}")
    builder.adjust(2, 1)
    
    await c.message.edit_caption(
        caption=f"🎮 <b>{ai_txt}</b>\n\nУчастники:\n1. {c.from_user.first_name}\n\nОжидаем бизнес-партнеров...",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("join_game_"))
async def join_game(c: types.CallbackQuery):
    chat_id = int(c.data.split("_")[2])
    game = WAITING_GAMES.get(chat_id)
    if not game: return await c.answer("Игра не найдена")
    if any(p['id'] == c.from_user.id for p in game['players']):
        return await c.answer("Ты уже в деле!", show_alert=True)
    
    game['players'].append({"id": c.from_user.id, "name": c.from_user.first_name, "username": c.from_user.username})
    
    p_list = "\n".join([f"{i+1}. {p['name']}" for i, p in enumerate(game['players'])])
    await c.message.edit_caption(
        caption=f"🎮 <b>Сбор в разгаре!</b>\n\nУчастники:\n{p_list}",
        parse_mode="HTML",
        reply_markup=c.message.reply_markup
    )
    await c.answer("Ты вступил в игру!")

@dp.callback_query(F.data.startswith("leave_game_"))
async def leave_game(c: types.CallbackQuery):
    chat_id = int(c.data.split("_")[2])
    game = WAITING_GAMES.get(chat_id)
    if not game: return
    
    game['players'] = [p for p in game['players'] if p['id'] != c.from_user.id]
    if not game['players']:
        del WAITING_GAMES[chat_id]
        return await c.message.edit_caption(caption="❌ Сбор отменен, все игроки вышли.")
    
    p_list = "\n".join([f"{i+1}. {p['name']}" for i, p in enumerate(game['players'])])
    await c.message.edit_caption(caption=f"🎮 <b>Сбор игроков:</b>\n\n{p_list}", reply_markup=c.message.reply_markup)
    await c.answer("Вы вышли.")


# --- [7] СТАРТ И БРОСОК КУБИКА ---
@dp.callback_query(F.data.startswith("run_game_"))
async def run_game(c: types.CallbackQuery):
    chat_id = int(c.data.split("_")[2])
    game = WAITING_GAMES.get(chat_id)
    if c.from_user.id != game['creator_id']:
        return await c.answer("Только создатель может начать!", show_alert=True)
    
    async with aiosqlite.connect('monopoly_v2.db') as db:
        for p in game['players']:
            await db.execute("INSERT OR REPLACE INTO players (chat_id, user_id, name) VALUES (?, ?, ?)", 
                             (chat_id, p['id'], p['name']))
        await db.commit()
    
    ACTIVE_GAMES[chat_id] = game
    del WAITING_GAMES[chat_id]
    
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик")
    kb.button(text="📊 Мои активы")
    kb.adjust(1)
    
    await c.message.answer("🚀 <b>Игра началась!</b>\nПора делать деньги.", 
                           reply_markup=kb.as_markup(resize_keyboard=True), parse_mode="HTML")
    await c.message.delete()

@dp.message(F.text == "🎲 Бросить кубик")
async def roll_move(m: types.Message):
    async with aiosqlite.connect('monopoly_v2.db') as db:
        res = await db.execute("SELECT pos, balance, jail FROM players WHERE chat_id=? AND user_id=?", 
                               (m.chat.id, m.from_user.id))
        p = await res.fetchone()
        if not p: return await m.answer("Вы не в игре!")
        
        pos, bal, jail = p
        if jail > 0:
            await db.execute("UPDATE players SET jail = jail - 1 WHERE chat_id=? AND user_id=?", (m.chat.id, m.from_user.id))
            await db.commit()
            return await m.answer(await ai_commentator("jail", m.from_user.first_name))

        msg = await m.answer(await ai_commentator("roll", m.from_user.first_name, bal), parse_mode="HTML")
        dice = await m.answer_dice("🎲")
        await asyncio.sleep(3.5)
        
        new_pos = (pos + dice.dice.value) % 40
        if new_pos < pos: bal += 200 # Проход через старт
        
        # Клетка "В ТЮРЬМУ"
        if new_pos == 30:
            new_pos, jail = 10, 3
            await m.answer("🚔 Полиция! Вы отправляетесь в тюрьму на 3 хода.")

        await db.execute("UPDATE players SET pos=?, balance=?, jail=? WHERE chat_id=? AND user_id=?", 
                         (new_pos, bal, jail, m.chat.id, m.from_user.id))
        await db.commit()
        
        cell = BOARD.get(new_pos)
        await m.answer(f"📍 Клетка {new_pos}: <b>{cell[0]}</b>\nБаланс: ${bal}", parse_mode="HTML")

# --- [8] ЗАПУСК СИСТЕМЫ ---
async def main():
    await init_db()
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())






