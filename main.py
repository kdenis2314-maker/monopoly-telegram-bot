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
import sys

# --- [1] НАСТРОЙКИ И ПЕРЕМЕННЫЕ ---
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

# Статистика для сайта
STATS = {
    "active_games": 0,
    "total_players": 0,
    "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "version": "Premium v2.0"
}

# Хранилища игр
WAITING_GAMES = {}
ACTIVE_GAMES = {}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота и Flask
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- [2] БАЗА ДАННЫХ ---
async def init_db():
    try:
        async with aiosqlite.connect('monopoly_premium.db') as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS players (
                chat_id int, user_id int, name text, 
                balance int DEFAULT 1500, pos int DEFAULT 0, 
                jail int DEFAULT 0, PRIMARY KEY(chat_id, user_id))""")
            await db.execute("""CREATE TABLE IF NOT EXISTS property (
                chat_id int, cell_idx int, owner_id int, houses int DEFAULT 0, 
                PRIMARY KEY(chat_id, cell_idx))""")
            await db.execute("CREATE TABLE IF NOT EXISTS awards (user_id int, title text, chat_id int)")
            await db.commit()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

# --- [3] ИГРОВАЯ ДОСКА ---
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

# --- [4] КЛАВИАТУРЫ ---
def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎮 Начать сбор игроков", callback_data="start_player_gathering")
    kb.button(text="📖 Правила игры", callback_data="show_rules")
    kb.button(text="👨‍💻 О девелопере", callback_data="show_developer")
    kb.button(text="🌐 Статус системы", web_app=WebAppInfo(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost:' + str(PORT))}"))
    kb.adjust(1)
    return kb.as_markup()

def waiting_room_kb(chat_id, user_id, is_creator=False):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Присоединиться", callback_data=f"join_game_{chat_id}")
    kb.button(text="🚪 Выйти", callback_data=f"leave_game_{chat_id}")
    if is_creator:
        kb.button(text="▶️ Начать игру", callback_data=f"start_real_game_{chat_id}")
    kb.adjust(2, 1)
    return kb.as_markup()

def game_main_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик")
    kb.button(text="🏠 Построить")
    kb.button(text="📊 Мои активы")
    kb.button(text="🤝 Торговля")
    kb.button(text="❌ Скрыть меню")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def hide_menu_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Показать меню")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

# --- [5] FLASK СЕРВЕР ---
@app.route('/')
def index():
    stats_copy = STATS.copy()
    stats_copy["active_games"] = len(ACTIVE_GAMES)
    stats_copy["waiting_games"] = len(WAITING_GAMES)
    bot_name = "Monopoly Premium"
    
    return render_template('status.html', 
                         stats=stats_copy,
                         bot_name=bot_name,
                         domain=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost:' + str(PORT))}",
                         port=PORT,
                         start_time=stats_copy["started"],
                         dev_tag=DEV_TAG)

@app.route('/stats')
def stats_api():
    stats_copy = STATS.copy()
    stats_copy["active_games"] = len(ACTIVE_GAMES)
    stats_copy["waiting_games"] = len(WAITING_GAMES)
    return json.dumps(stats_copy, ensure_ascii=False)

@app.route('/health')
def health():
    return {"status": "ok", "bot": "running", "active_games": len(ACTIVE_GAMES)}, 200

# Создаем папку templates если её нет
if not os.path.exists('templates'):
    os.makedirs('templates')

# Создаем HTML шаблон
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
        .log-button { display: inline-block; background: linear-gradient(90deg, #ff0088, #ff5500); color: white; padding: 12px 25px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-top: 15px; transition: all 0.3s; border: none; cursor: pointer; }
        .log-button:hover { transform: scale(1.05); box-shadow: 0 5px 15px rgba(255, 0, 136, 0.3); }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255, 255, 255, 0.1); color: #888; font-size: 0.9rem; }
        .uptime { display: inline-block; background: rgba(0, 255, 136, 0.1); padding: 5px 15px; border-radius: 20px; margin-top: 10px; color: #00ff88; font-weight: 500; }
        @media (max-width: 768px) { .container { padding: 15px; } .header h1 { font-size: 2rem; } .status-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>МОНОПОЛИЯ ПРЕМИУМ</h1>
            <h2>Telegram Bot для игры в группах</h2>
        </div>
        
        <div class="status-grid">
            <div class="status-card">
                <div class="card-title">📊 Статус системы</div>
                <div class="info-line"><span class="label">Бот:</span><span class="value online">🟢 Онлайн</span></div>
                <div class="info-line"><span class="label">Активных игр:</span><span class="value">{{ stats.active_games }}</span></div>
                <div class="info-line"><span class="label">Ожидающих игр:</span><span class="value">{{ stats.waiting_games }}</span></div>
                <div class="info-line"><span class="label">Всего игроков:</span><span class="value">{{ stats.total_players }}</span></div>
            </div>
            
            <div class="status-card">
                <div class="card-title">⚙️ Стандарт</div>
                <div class="info-line"><span class="label">Запущен:</span><span class="value">{{ start_time }}</span></div>
                <div class="info-line"><span class="label">Версия:</span><span class="value">{{ stats.version }}</span></div>
                <div class="info-line"><span class="label">Порт:</span><span class="value">{{ port }}</span></div>
                <div class="info-line"><span class="label">Домен:</span><span class="value">{{ domain }}</span></div>
            </div>
            
            <div class="status-card">
                <div class="card-title">👥 Проектор</div>
                <div class="info-line"><span class="label">2024.12.18 17:56:19</span><span class="value"></span></div>
                <div class="info-line"><span class="label">Ramder Mushirook</span><span class="value"></span></div>
                <div class="info-line"><span class="label">Разработчик:</span><span class="value">{{ dev_tag }}</span></div>
            </div>
        </div>
        
        <div class="instructions">
            <h3>📋 Инструкция по использованию</h3>
            <ol class="steps">
                <li>Добавьте бота <strong>{{ bot_name }}</strong> в Telegram группу как администратора</li>
                <li>Напишите в группе команду <code>/monopoly</code></li>
                <li>Нажмите "Начать сбор игроков" и дождитесь участников</li>
                <li>Когда все готовы, создатель игры нажимает "Начать игру"</li>
                <li>Используйте кнопки "🎲 Бросить кубик" для хода</li>
                <li>В любой момент можно скрыть меню командой <code>/hide</code></li>
            </ol>
            
            <button class="log-button" onclick="location.reload()">🔄 Обновить статус</button>
            <a href="/stats" class="log-button" style="margin-left: 10px;">📊 API Статистики</a>
        </div>
        
        <div class="footer">
            <p>Система мониторинга Monopoly Premium Bot</p>
            <div class="uptime">⏱ Uptime: {{ stats.started }}</div>
            <p style="margin-top: 15px;">🔧 При возникновении проблем используйте команду /hide для сброса меню</p>
        </div>
    </div>
    
    <script>
        setInterval(() => {
            fetch('/health').then(response => response.json()).then(data => {
                if (data.status === 'ok') console.log('Bot is healthy');
            }).catch(err => console.log('Health check failed:', err));
        }, 30000);
        
        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.status-card');
            cards.forEach((card, index) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    card.style.transition = 'opacity 0.5s, transform 0.5s';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, index * 100);
            });
        });
    </script>
</body>
</html>'''

# Сохраняем HTML шаблон
with open('templates/status.html', 'w', encoding='utf-8') as f:
    f.write(status_html)

# --- [6] КОМАНДЫ БОТА ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    """Главная команда для запуска игры"""
    try:
        await message.answer(
            f"{BANNER}\n\n🎲 <b>Monopoly Premium Edition</b>\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_monopoly: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

@dp.message(Command("hide"))
async def cmd_hide_menu(message: types.Message):
    """Команда для скрытия меню"""
    try:
        await message.answer(
            "✅ Меню скрыто. Чтобы вернуть меню, нажмите кнопку ниже или используйте /monopoly",
            reply_markup=hide_menu_kb()
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_hide: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    try:
        await message.answer(
            f"👋 Привет! Я бот для игры в Монополию!\n\n"
            f"Используйте команду /monopoly чтобы начать игру в группе.\n"
            f"Используйте /hide чтобы скрыть меню.\n\n"
            f"Разработчик: {DEV_TAG}"
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

# --- [7] ОБРАБОТКА КНОПОК ---
@dp.callback_query(F.data == "start_player_gathering")
async def start_gathering(c: types.CallbackQuery):
    """Начать сбор игроков"""
    try:
        chat_id = c.message.chat.id
        user_id = c.from_user.id
        
        if chat_id in WAITING_GAMES:
            await c.answer("⚠️ В этой группе уже идет сбор игроков!", show_alert=True)
            return
        
        WAITING_GAMES[chat_id] = {
            "creator_id": user_id,
            "creator_name": c.from_user.first_name,
            "players": [{"id": user_id, "name": c.from_user.first_name, "username": c.from_user.username}],
            "message_id": c.message.message_id,
            "created_at": datetime.now()
        }
        
        STATS["active_games"] = len(ACTIVE_GAMES) + len(WAITING_GAMES)
        
        players_text = "👥 <b>Игроки в ожидании:</b>\n"
        for player in WAITING_GAMES[chat_id]["players"]:
            players_text += f"• {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"
            f"Создатель: {c.from_user.first_name}\n\n"
            f"{players_text}\n"
            f"✅ Нажмите 'Присоединиться' чтобы войти в игру\n"
            f"🚪 'Выйти из игры' - чтобы покинуть лобби\n"
            f"▶️ Создатель может начать игру когда все готовы",
            parse_mode="HTML",
            reply_markup=waiting_room_kb(chat_id, user_id, is_creator=True)
        )
        
        await c.answer("🎮 Сбор игроков начат!")
        
    except Exception as e:
        logger.error(f"Ошибка в start_gathering: {e}")
        await c.answer(f"🤖 {MAINTENANCE_MSG}", show_alert=True)

@dp.callback_query(F.data.startswith("join_game_"))
async def join_game(c: types.CallbackQuery):
    """Присоединение к игре"""
    try:
        chat_id = int(c.data.split("_")[2])
        
        if chat_id not in WAITING_GAMES:
            await c.answer("⚠️ Игра не найдена или уже началась", show_alert=True)
            return
        
        game = WAITING_GAMES[chat_id]
        user_id = c.from_user.id
        
        for player in game["players"]:
            if player["id"] == user_id:
                await c.answer("✅ Вы уже в игре!")
                return
        
        game["players"].append({
            "id": user_id,
            "name": c.from_user.first_name,
            "username": c.from_user.username
        })
        
        players_text = "👥 <b>Игроки в ожидании:</b>\n"
        for player in game["players"]:
            players_text += f"• {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        is_creator = (user_id == game["creator_id"])
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"
            f"Создатель: {game['creator_name']}\n\n"
            f"{players_text}\n"
            f"✅ Нажмите 'Присоединиться' чтобы войти в игру\n"
            f"🚪 'Выйти из игры' - чтобы покинуть лобби\n"
            f"▶️ Создатель может начать игру когда все готовы",
            parse_mode="HTML",
            reply_markup=waiting_room_kb(chat_id, user_id, is_creator=is_creator)
        )
        
        await c.answer(f"🎮 Вы присоединились к игре! Игроков: {len(game['players'])}")
        
    except Exception as e:
        logger.error(f"Ошибка в join_game: {e}")
        await c.answer(f"🤖 {MAINTENANCE_MSG}", show_alert=True)

@dp.callback_query(F.data.startswith("leave_game_"))
async def leave_game(c: types.CallbackQuery):
    """Выход из игры"""
    try:
        chat_id = int(c.data.split("_")[2])
        
        if chat_id not in WAITING_GAMES:
            await c.answer("⚠️ Игра не найдена", show_alert=True)
            return
        
        game = WAITING_GAMES[chat_id]
        user_id = c.from_user.id
        
        # Удаляем игрока из списка
        game["players"] = [p for p in game["players"] if p["id"] != user_id]
        
        # Если игроков не осталось, удаляем игру
        if not game["players"]:
            del WAITING_GAMES[chat_id]
            await c.message.edit_text("❌ Игра отменена - все игроки вышли")
            await c.answer("Игра отменена")
            return
        
        # Если вышел создатель, назначить нового создателя
        if user_id == game["creator_id"]:
            game["creator_id"] = game["players"][0]["id"]
            game["creator_name"] = game["players"][0]["name"]
        
        players_text = "👥 <b>Игроки в ожидании:</b>\n"
        for player in game["players"]:
            players_text += f"• {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        is_creator = (c.from_user.id == game["creator_id"])
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"