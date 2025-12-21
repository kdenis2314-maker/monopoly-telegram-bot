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

# Хранилище ожидающих игр и активных игр
WAITING_GAMES = {}
ACTIVE_GAMES = {}

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("🚀 Запуск Monopoly Premium бота...")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- [2] FLASK СЕРВЕР И ШАБЛОН ---
app = Flask(__name__)

@app.route('/')
def index():
    # Получаем актуальную статистику
    stats_copy = STATS.copy()
    stats_copy["active_games"] = len(ACTIVE_GAMES)
    stats_copy["waiting_games"] = len(WAITING_GAMES)
    
    # Получаем имя бота если возможно
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

# Создаем папку для шаблонов если её нет
if not os.path.exists('templates'):
    os.makedirs('templates')

# Сохраняем HTML шаблон
status_html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>МОНОПОЛИЯ ПРЕМИУМ - Статус</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(25, 25, 40, 0.9);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            border: 1px solid #2a2a4a;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #00ff88;
        }
        
        .header h1 {
            font-size: 2.8rem;
            background: linear-gradient(90deg, #00ff88, #00ccff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .header h2 {
            color: #a0a0ff;
            font-weight: 300;
            font-size: 1.2rem;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        
        .status-card {
            background: rgba(40, 40, 60, 0.7);
            border-radius: 15px;
            padding: 25px;
            border-left: 5px solid #00ff88;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .status-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0, 255, 136, 0.2);
        }
        
        .status-card.system {
            border-left-color: #ff0088;
        }
        
        .status-card.standard {
            border-left-color: #0088ff;
        }
        
        .status-card.projector {
            border-left-color: #ff8800;
        }
        
        .card-title {
            color: #00ff88;
            font-size: 1.1rem;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card-title i {
            font-size: 1.3rem;
        }
        
        .info-line {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .label {
            color: #a0a0ff;
            font-weight: 500;
        }
        
        .value {
            color: #fff;
            font-weight: 600;
        }
        
        .value.online {
            color: #00ff88;
        }
        
        .value.offline {
            color: #ff5555;
        }
        
        .instructions {
            background: rgba(30, 30, 50, 0.8);
            border-radius: 15px;
            padding: 25px;
            margin-top: 30px;
            border: 1px solid #3a3a6a;
        }
        
        .instructions h3 {
            color: #00ccff;
            margin-bottom: 20px;
            font-size: 1.4rem;
        }
        
        .steps {
            list-style-type: none;
        }
        
        .steps li {
            margin: 15px 0;
            padding-left: 30px;
            position: relative;
            line-height: 1.6;
        }
        
        .steps li:before {
            content: counter(step);
            counter-increment: step;
            position: absolute;
            left: 0;
            top: 0;
            background: #00ff88;
            color: #000;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            font-weight: bold;
        }
        
        .steps {
            counter-reset: step;
        }
        
        .log-button {
            display: inline-block;
            background: linear-gradient(90deg, #ff0088, #ff5500);
            color: white;
            padding: 12px 25px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 15px;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
        }
        
        .log-button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(255, 0, 136, 0.3);
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #888;
            font-size: 0.9rem;
        }
        
        .uptime {
            display: inline-block;
            background: rgba(0, 255, 136, 0.1);
            padding: 5px 15px;
            border-radius: 20px;
            margin-top: 10px;
            color: #00ff88;
            font-weight: 500;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .status-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .refresh-btn {
            background: rgba(0, 136, 255, 0.2);
            color: #00ccff;
            border: 1px solid #00ccff;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 10px;
            transition: all 0.3s;
        }
        
        .refresh-btn:hover {
            background: rgba(0, 136, 255, 0.4);
        }
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
                <div class="info-line">
                    <span class="label">Бот:</span>
                    <span class="value online">🟢 Онлайн</span>
                </div>
                <div class="info-line">
                    <span class="label">Активных игр:</span>
                    <span class="value">{{ stats.active_games }}</span>
                </div>
                <div class="info-line">
                    <span class="label">Ожидающих игр:</span>
                    <span class="value">{{ stats.waiting_games }}</span>
                </div>
                <div class="info-line">
                    <span class="label">Всего игроков:</span>
                    <span class="value">{{ stats.total_players }}</span>
                </div>
            </div>
            
            <div class="status-card standard">
                <div class="card-title">⚙️ Стандарт</div>
                <div class="info-line">
                    <span class="label">Запущен:</span>
                    <span class="value">{{ start_time }}</span>
                </div>
                <div class="info-line">
                    <span class="label">Версия:</span>
                    <span class="value">{{ stats.version }}</span>
                </div>
                <div class="info-line">
                    <span class="label">Порт:</span>
                    <span class="value">{{ port }}</span>
                </div>
                <div class="info-line">
                    <span class="label">Домен:</span>
                    <span class="value">{{ domain }}</span>
                </div>
            </div>
            
            <div class="status-card projector">
                <div class="card-title">👥 Проектор</div>
                <div class="info-line">
                    <span class="label">2024.12.18 17:56:19</span>
                    <span class="value"></span>
                </div>
                <div class="info-line">
                    <span class="label">Ramder Mushirook</span>
                    <span class="value"></span>
                </div>
                <div class="info-line">
                    <span class="label">Разработчик:</span>
                    <span class="value">{{ dev_tag }}</span>
                </div>
            </div>
        </div>
        
        <div class="instructions">
            <h3>📋 Инструкция по использованию</h3>
            <ol class="steps">
                <li>Добавьте бота <strong>{{ bot_name }}</strong> в Telegram группу как администратора</li>
                <li>Напишите в группе команду <code>/monopoly</code> или <code>/monopoly@{{ bot_name }}</code></li>
                <li>Нажмите "Начать сбор игроков" и дождитесь участников</li>
                <li>Когда все готовы, создатель игры нажимает "Начать игру"</li>
                <li>Используйте кнопки "🎲 Бросить кубик" для хода и другие игровые действия</li>
                <li>В любой момент можно скрыть меню кнопкой "Скрыть меню" или командой <code>/hide</code></li>
            </ol>
            
            <button class="log-button" onclick="location.reload()">🔄 Обновить статус</button>
            <a href="/stats" class="log-button" style="margin-left: 10px;">📊 API Статистики</a>
        </div>
        
        <div class="footer">
            <p>Система мониторинга Monopoly Premium Bot</p>
            <div class="uptime">
                ⏱ Uptime: {{ stats.started }}
            </div>
            <p style="margin-top: 15px;">🔧 При возникновении проблем используйте команду /hide для сброса меню</p>
        </div>
    </div>
    
    <script>
        // Авто-обновление каждые 30 секунд
        setInterval(() => {
            fetch('/health')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                        console.log('Bot is healthy');
                    }
                })
                .catch(err => console.log('Health check failed:', err));
        }, 30000);
        
        // Плавное появление элементов
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

# Сохраняем шаблон
with open('templates/status.html', 'w', encoding='utf-8') as f:
    f.write(status_html)

# --- [3] ИГРОВАЯ ДАТА-БАЗА ---
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

# --- [4] ИИ-ГЕНЕРАТОР ФРАЗ ---
async def ai_voice(event, name, value=None):
    phrases = {
        "roll": [f"🎲 {name} кидает кости... Посмотрим на твое везение!", f"🎯 Кубики в воздухе! Что приготовил рандом для {name}?", f"🎰 Ставки сделаны, {name} делает ход!"],
        "jail": [f"⛓ {name}, Тюрьмыч ждет! Принц недоволен твоим поведением.", f"👮‍♂️ Наручники на {name}! 3 хода тишины и баланды.", f"🚔 {name}, следствие окончено. Ты в тюрьме!"],
        "chance": [f"🃏 Шанс! {name}, это может быть твой лучший или худший день.", f"🎰 Судьба играет с {name}... Тяни карту!", f"🎲 Рандомный подарок (или штраф) для {name}!"],
        "rent": [f"💸 {name} попал! ${value} аренды улетают владельцу.", f"💰 Казна {name} пустеет. Кто-то богатеет!", f"📈 Бизнес есть бизнес: {name} платит по счетам."],
        "win_achieve": [f"👑 Опа! {name} теперь настоящий Олигарх!", f"🏆 {name} забирает титул! Капитализм в действии."],
        "join": [f"🎮 {name} присоединился к игре!", f"👤 Новый участник: {name}!", f"💰 {name} готов к финансовым битвам!"],
        "leave": [f"👋 {name} покинул игру.", f"🚶 {name} вышел из-за стола.", f"💨 {name} сбежал с поля боя!"],
        "start": [f"🚀 Игра начинается! Удачи, {name}!", f"🎯 {name} запускает игру! Приготовьтесь!", f"⚡ Поехали! {name} дает старт!"]
    }
    return random.choice(phrases.get(event, ["Ход принят!"]))

# --- [5] БАЗА ДАННЫХ ---
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
            await db.execute("""CREATE TABLE IF NOT EXISTS game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id int,
                started_at timestamp,
                finished_at timestamp,
                winner_id int,
                players_count int)""")
            await db.commit()
        
        # Обновляем статистику
        async with aiosqlite.connect('monopoly_premium.db') as db:
            cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM players")
            result = await cursor.fetchone()
            if result:
                STATS["total_players"] = result[0]
        
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

# --- [6] КЛАВИАТУРЫ И МЕНЮ ---
def main_menu_kb():
    """Главное меню после /monopoly"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎮 Начать сбор игроков", callback_data="start_player_gathering")
    kb.button(text="📖 Правила игры", callback_data="show_rules")
    kb.button(text="👨‍💻 О девелопере", callback_data="show_developer")
    kb.button(text="🌐 Статус системы", web_app=WebAppInfo(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost:' + str(PORT))}"))
    kb.adjust(1)
    return kb.as_markup()

def waiting_room_kb(chat_id, user_id, is_creator=False):
    """Комната ожидания игроков"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🚪 Выйти из игры", callback_data=f"leave_game_{chat_id}")
    
    if is_creator:
        kb.button(text="▶️ Начать игру", callback_data=f"start_real_game_{chat_id}")
    
    kb.adjust(1)
    return kb.as_markup()

def game_main_kb():
    """Основная игровая клавиатура"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик")
    kb.button(text="🏠 Построить")
    kb.button(text="📊 Мои активы")
    kb.button(text="🤝 Торговля")
    kb.button(text="❌ Скрыть меню")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def hide_menu_kb():
    """Клавиатура после скрытия меню"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Показать меню")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

# --- [7] ДЕКОРАТОР ДЛЯ ОТЛОВА ОШИБОК ---
def catch_errors(func):
    """Декоратор для обработки ошибок с красивым сообщением"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Ошибка в {func.__name__}: {e}")
            
            # Определяем тип объекта для ответа
            obj = args[0] if args else None
            
            error_message = (
                "🤖 <b>Бот сломался или находится на перезаливке кода</b>\n\n"
                "Приносим свои извинения, Темный принц уже это чинит ♥️\n\n"
                "Попробуйте позже или используйте к