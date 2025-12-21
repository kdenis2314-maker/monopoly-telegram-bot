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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- [1] НАСТРОЙКИ И ПЕРЕМЕННЫЕ ---
API_TOKEN = os.environ.get("BOT_TOKEN")
if not API_TOKEN:
    logging.error("❌ BOT_TOKEN не найден в переменных окружении!")
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
    try:
        # Пробуем получить имя бота из контекста или переменной
        bot_name = "Monopoly Premium Bot"
    except:
        pass
    
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

# --- [7] КОМАНДЫ БОТА ---
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
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

@dp.message(Command("hide"))
async def cmd_hide_menu(message: types.Message):
    """Команда для скрытия меню - РАБОТАЕТ ВСЕГДА"""
    try:
        await message.answer(
            "✅ Меню скрыто. Чтобы вернуть меню, нажмите кнопку ниже или используйте /monopoly",
            reply_markup=hide_menu_kb()
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_hide: {e}")
        # Даже при ошибке пытаемся отправить простой ответ
        try:
            await message.answer("Меню скрыто. Используйте /monopoly для возврата.")
        except:
            pass

@dp.message(F.text == "❌ Скрыть меню")
async def hide_menu_button(message: types.Message):
    """Обработка кнопки скрытия меню - РАБОТАЕТ ВСЕГДА"""
    try:
        await message.answer(
            "✅ Меню скрыто. Чтобы вернуть меню, нажмите кнопку ниже или используйте /monopoly",
            reply_markup=hide_menu_kb()
        )
    except Exception as e:
        logger.error(f"Ошибка в hide_menu_button: {e}")
        try:
            await message.answer("Меню скрыто. Используйте /monopoly для возврата.")
        except:
            pass

@dp.message(F.text == "📱 Показать меню")
async def show_menu_button(message: types.Message):
    """Показ меню после скрытия"""
    try:
        await cmd_monopoly(message)
    except Exception as e:
        logger.error(f"Ошибка в show_menu_button: {e}")
        await message.answer("Используйте команду /monopoly")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    await message.answer(
        f"👋 Привет! Я бот для игры в Монополию!\n\n"
        f"Используйте команду /monopoly чтобы начать игру в группе.\n"
        f"Используйте /hide чтобы скрыть меню.\n\n"
        f"Разработчик: {DEV_TAG}"
    )

# --- [8] ОБРАБОТКА КНОПОК ГЛАВНОГО МЕНЮ ---
@dp.callback_query(F.data == "start_player_gathering")
async def start_gathering(c: types.CallbackQuery):
    """Начать сбор игроков - МОЖЕТ ЛЮБОЙ"""
    try:
        chat_id = c.message.chat.id
        user_id = c.from_user.id
        
        # Проверяем, не идет ли уже сбор
        if chat_id in WAITING_GAMES:
            await c.answer("⚠️ В этой группе уже идет сбор игроков!", show_alert=True)
            return
        
        # Создаем новую игру - любой может создать
        WAITING_GAMES[chat_id] = {
            "creator_id": user_id,
            "creator_name": c.from_user.first_name,
            "players": [{
                "id": user_id,
                "name": c.from_user.first_name,
                "username": c.from_user.username
            }],
            "message_id": c.message.message_id,
            "created_at": datetime.now()
        }
        
        STATS["active_games"] = len(ACTIVE_GAMES) + len(WAITING_GAMES)
        
        # Отправляем сообщение о начале сбора
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
            reply_markup=InlineKeyboardBuilder()
                .button(text="✅ Присоединиться", callback_data=f"join_game_{chat_id}")
                .button(text="🚪 Выйти", callback_data=f"leave_game_{chat_id}")
                .button(text="▶️ Начать игру", callback_data=f"start_real_game_{chat_id}")
                .adjust(2, 1)
                .as_markup()
        )
        
        await c.answer("🎮 Сбор игроков начат!")
        
    except Exception as e:
        logger.error(f"Ошибка в start_gathering: {e}")
        await c.answer("⚠️ Ошибка при создании игры", show_alert=True)

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
        
        # Проверяем, не присоединился ли уже
        for player in game["players"]:
            if player["id"] == user_id:
                await c.answer("✅ Вы уже в игре!")
                return
        
        # Добавляем игрока
        game["players"].append({
            "id": user_id,
            "name": c.from_user.first_name,
            "username": c.from_user.username
        })
        
        # Обновляем сообщение
        players_text = "👥 <b>Игроки в ожидании:</b>\n"
        for player in game["players"]:
            players_text += f"• {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"
            f"Создатель: {game['creator_name']}\n\n"
            f"{players_text}\n"
            f"✅ Нажмите 'Присоединиться' чтобы войти в игру\n"
            f"🚪 'Выйти из игры' - чтобы покинуть лобби\n"
            f"▶️ Создатель может начать игру когда все готовы",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder()
                .button(text="✅ Присоединиться", callback_data=f"join_game_{chat_id}")
                .button(text="🚪 Выйти", callback_data=f"leave_game_{chat_id}")
                .button(text="▶️ Начать игру", callback_data=f"start_real_game_{chat_id}")
                .adjust(2, 1)
                .as_markup()
        )
        
        await c.answer(f"🎮 Вы присоединились к игре! Игроков: {len(game['players'])}")
        
    except Exception as e:
        logger.error(f"Ошибка в join_game: {e}")
        await c.answer("⚠️ Ошибка при присоединении", show_alert=True)

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
        
        # Если это создатель - удаляем игру
        if user_id == game["creator_id"]:
            del WAITING_GAMES[chat_id]
            await c.message.edit_text(
                "❌ Игра отменена создателем",
                reply_markup=main_menu_kb()
            )
            await c.answer("🎮 Игра отменена")
            return
        
        # Удаляем игрока из списка
        game["players"] = [p for p in game["players"] if p["id"] != user_id]
        
        # Если остался только создатель или никто - удаляем игру
        if len(game["players"]) <= 1:
            del WAITING_GAMES[chat_id]
            await c.message.edit_text(
                "❌ Игра отменена (недостаточно игроков)",
                reply_markup=main_menu_kb()
            )
            await c.answer("🎮 Игра отменена")
            return
        
        # Обновляем сообщение
        players_text = "👥 <b>Игроки в ожидании:</b>\n"
        for player in game["players"]:
            players_text += f"• {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"
            f"Создатель: {game['creator_name']}\n\n"
            f"{players_text}\n"
            f"✅ Нажмите 'Присоединиться' чтобы войти в игру\n"
            f"🚪 'Выйти из игры' - чтобы покинуть лобби\n"
            f"▶️ Создатель может начать игру когда все готовы",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder()
                .button(text="✅ Присоединиться", callback_data=f"join_game_{chat_id}")
                .button(text="🚪 Выйти", callback_data=f"leave_game_{chat_id}")
                .button(text="▶️ Начать игру", callback_data=f"start_real_game_{chat_id}")
                .adjust(2, 1)
                .as_markup()
        )
        
        await c.answer("🚪 Вы вышли из игры")
        
    except Exception as e:
        logger.error(f"Ошибка в leave_game: {e}")
        await c.answer("⚠️ Ошибка при выходе из игры", show_alert=True)

@dp.callback_query(F.data.startswith("start_real_game_"))
async def start_real_game(c: types.CallbackQuery):
    """Начало реальной игры - ТОЛЬКО СОЗДАТЕЛЬ"""
    try:
        chat_id = int(c.data.split("_")[3])
        
        if chat_id not in WAITING_GAMES:
            await c.answer("⚠️ Игра не найдена", show_alert=True)
            return
        
        game = WAITING_GAMES[chat_id]
        
        # Проверяем, что это создатель (ТОЛЬКО СОЗДАТЕЛЬ может начать)
        if c.from_user.id != game["creator_id"]:
            await c.answer("⚠️ Только создатель лобби может начать игру!", show_alert=True)
            return
        
        # Проверяем минимальное количество игроков
        if len(game["players"]) < 2:
            await c.answer("⚠️ Нужно минимум 2 игрока для начала!", show_alert=True)
            return
        
        # Переносим игру в активные
        ACTIVE_GAMES[chat_id] = {
            "players": game["players"].copy(),
            "current_player_index": 0,
            "current_player_id": game["players"][0]["id"],
            "current_player_name": game["players"][0]["name"],
            "turn_order": [p["id"] for p in game["players"]],
            "started_at": datetime.now(),
            "board_state": {},
            "properties": {},
            "balances": {p["id"]: 1500 for p in game["players"]},
            "positions": {p["id"]: 0 for p in game["players"]},
            "jail_status": {p["id"]: 0 for p in game["players"]}
        }
        
        # Удаляем из ожидания
        del WAITING_GAMES[chat_id]
        
        # Обновляем статистику
        STATS["active_games"] = len(ACTIVE_GAMES)
        STATS["total_players"] += len(ACTIVE_GAMES[chat_id]["players"])
        
        # Сообщаем о начале игры
        players_list = "\n".join([f"• {p['name']}" for p in game["players"]])
        
        await c.message.edit_text(
            f"🎉 <b>Игра началась!</b>\n\n"
            f"<b>Игроки:</b>\n{players_list}\n\n"
            f"💵 Стартовый баланс: <b>$1500</b>\n"
            f"🎲 Первый ход: <b>{game['players'][0]['name']}</b>\n\n"
            f"Используйте кнопки ниже для игры:",
            parse_mode="HTML"
        )
        
        # Отправляем игровую клавиатуру всем игрокам
        for player in game["players"]:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🎮 <b>{player['name']}</b>, игра началась!\n"
                         f"Ваш ход начнется, когда подойдет очередь.\n"
                         f"Сейчас ходит: <b>{game['players'][0]['name']}</b>",
                    parse_mode="HTML",
                    reply_markup=game_main_kb()
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение игроку {player['id']}: {e}")
        
        # Объявляем первого игрока
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎯 <b>{game['players'][0]['name']}</b>, ваш ход первый! Нажмите '🎲 Бросить кубик'",
            parse_mode="HTML",
            reply_markup=game_main_kb()
        )
        
        await c.answer("🎮 Игра началась!")
        
    except Exception as e:
        logger.error(f"Ошибка в start_real_game: {e}")
        await c.answer("⚠️ Ошибка при начале игры", show_alert=True)

# --- [8] ФУНКЦИИ ДЛЯ ИГРОВОГО ПРОЦЕССА ---
async def next_player(chat_id: int, message: types.Message = None):
    """Переход хода к следующему игроку"""
    try:
        if chat_id not in ACTIVE_GAMES:
            return
        
        game = ACTIVE_GAMES[chat_id]
        
        # Переходим к следующему игроку
        game["current_player_index"] = (game["current_player_index"] + 1) % len(game["players"])
        next_player_data = game["players"][game["current_player_index"]]
        
        game["current_player_id"] = next_player_data["id"]
        game["current_player_name"] = next_player_data["name"]
        
        # Уведомляем о смене хода
        if message:
            await message.answer(
                f"🔄 Ход переходит к <b>{next_player_data['name']}</b>!\n"
                f"Баланс: ${game['balances'][next_player_data['id']]}\n"
                f"Позиция: {game['positions'][next_player_data['id']]}",
                parse_mode="HTML"
            )
            
            # Персональное уведомление для следующего игрока
            await bot.send_message(
                chat_id=chat_id,
                text=f"🎯 <b>{next_player_data['name']}</b>, ваш ход! Нажмите '🎲 Бросить кубик'",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Ошибка в next_player: {e}")

@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice_in_game(message: types.Message):
    """Бросок кубиков в активной игре"""
    try:
        chat_id = message.chat.id
        
        if chat_id not in ACTIVE_GAMES:
            # Проверяем, может игрок в группе, где нет активной игры
            if chat_id in WAITING_GAMES:
                await message.answer("⚠️ Игра еще не началась. Дождитесь начала!")
            else:
                await message.answer("⚠️ Нет активной игры. Используйте /monopoly чтобы начать")
            return
        
        game = ACTIVE_GAMES[chat_id]
        user_id = message.from_user.id
        
        # Проверяем, чей сейчас ход
        if user_id != game["current_player_id"]:
            current_player_name = game["current_player_name"]
            await message.answer(f"⏳ Сейчас ходит {current_player_name}. Дождитесь своей очереди!")
            return
        
        # Проверяем тюрьму
        if game["jail_status"][user_id] > 0:
            game["jail_status"][user_id] -= 1
            await message.answer(f"⛓ Вы в тюрьме! Осталось сидеть: {game['jail_status'][user_id]} ходов")
            # Переход хода
            await next_player(chat_id, message)
            return
        
        # Бросаем кубики
        await message.answer("🎲 Бросаю кубики...")
        dice_message = await message.answer_dice("🎲")
        await asyncio.sleep(3.5)
        
        dice_value = dice_message.dice.value
        new_position = (game["positions"][user_id] + dice_value) % 40
        
        # Обновляем позицию
        game["positions"][user_id] = new_position
        
        # Проверяем клетку
        if new_position == 30:  # Тюрьма
            game["positions"][user_id] = 10
            game["jail_status"][user_id] = 3
            await message.answer(f"⛓ Вы попали в тюрьму! Пропускаете 3 хода.")
            await next_player(chat_id, message)
            return
        elif new_position in [2, 7, 17, 22, 33, 36]:  # Шанс
            change = random.choice([-200, -100, 50, 100, 150, 200, -150])
            game["balances"][user_id] += change
            change_text = f"+{change}" if change > 0 else str(change)
            await message.answer(f"🎰 Карта шанса: {change_text}$! Новый баланс: ${game['balances'][user_id]}")
            await next_player(chat_id, message)
            return
        elif new_position in BOARD:  # Недвижимость
            prop_name, price, rent, color = BOARD[new_position]
            
            # Проверяем владение
            if new_position not in game["properties"]:
                # Свободная недвижимость
                kb = InlineKeyboardBuilder()
                kb.button(text=f"💸 Купить за ${price}", callback_data=f"buy_prop_{chat_id}_{new_position}")
                kb.button(text="🚫 Пропустить", callback_data=f"skip_buy_{chat_id}")
                kb.adjust(1)
                
                await message.answer(
                    f"🏠 Вы на клетке <b>{prop_name}</b>\n"
                    f"Цена: ${price}, Аренда: ${rent}\n"
                    f"Ваш баланс: ${game['balances'][user_id]}",
                    parse_mode="HTML",
                    reply_markup=kb.as_markup()
                )
                # Не переходим к следующему игроку - ждем решения
                return
            else:
                # Кто-то владеет
                owner_id = game["properties"][new_position]
                if owner_id != user_id:
                    rent_to_pay = rent
                    # Умножаем аренду если есть дома (упрощенная логика)
                    if new_position in game.get("houses", {}):
                        houses = game["houses"][new_position]
                        rent_to_pay *= (houses + 1)
                    
                    game["balances"][user_id] -= rent_to_pay
                    game["balances"][owner_id] += rent_to_pay
                    
                    owner_name = next((p["name"] for p in game["players"] if p["id"] == owner_id), "Неизвестно")
                    await message.answer(
                        f"💸 Вы платите аренду ${rent_to_pay} игроку {owner_name}\n"
                        f"Ваш баланс: ${game['balances'][user_id]}"
                    )
        
        # Если дошли сюда - переходим к следующему игроку
        await next_player(chat_id, message)
        
    except Exception as e:
        logger.error(f"Ошибка в roll_dice_in_game: {e}")
        await message.answer("⚠️ Произошла ошибка при броске кубиков")

@dp.callback_query(F.data.startswith("buy_prop_"))
async def buy_property(c: types.CallbackQuery):
    """Покупка недвижимости"""
    try:
        _, _, chat_id_str, position_str = c.data.split("_")
        chat_id = int(chat_id_str)
        position = int(position_str)
        
        if chat_id not in ACTIVE_GAMES:
            await c.answer("⚠️ Игра не найдена", show_alert=True)
            return
        
        game = ACTIVE_GAMES[chat_id]
        user_id = c.from_user.id
        
        # Проверяем, что это текущий игрок
        if user_id != game["current_player_id"]:
            await c.answer("⚠️ Не ваш ход!", show_alert=True)
            return
        
        if position not in BOARD:
            await c.answer("⚠️ Недвижимость не найдена", show_alert=True)
            return
        
        prop_name, price, rent, color = BOARD[position]
        
        # Проверяем баланс
        if game["balances"][user_id] < price:
            await c.answer(f"⚠️ Недостаточно средств! Нужно ${price}", show_alert=True)
            return
        
        # Покупаем
        game["balances"][user_id] -= price
        game["properties"][position] = user_id
        
        await c.message.edit_text(
            f"✅ <b>{prop_name}</b> куплена за ${price}!\n"
            f"Баланс: ${game['balances'][user_id]}",
            parse_mode="HTML"
        )
        
        # Переходим к следующему игроку
        await next_player(chat_id, c.message)
        await c.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в buy_property: {e}")
        await c.answer("⚠️ Ошибка при покупке", show_alert=True)

@dp.callback_query(F.data.startswith("skip_buy_"))
async def skip_buy(c: types.CallbackQuery):
    """Пропуск покупки"""
    try:
        _, _, chat_id_str = c.data.split("_")
        chat_id = int(chat_id_str)
        
        if chat_id not in ACTIVE_GAMES:
            await c.answer("⚠️ Игра не найдена", show_alert=True)
            return
        
        await c.message.edit_text("🚫 Покупка пропущена")
        await next_player(chat_id, c.message)
        await c.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в skip_buy: {e}")
        await c.answer("⚠️ Ошибка", show_alert=True)

@dp.callback_query(F.data == "show_rules")
async def show_rules(c: types.CallbackQuery):
    """Показать правила игры"""
    rules_text = """
📖 <b>Правила Монополии:</b>

🎲 <b>Цель игры:</b>
Первым разорить всех соперников!

💰 <b>Стартовый капитал:</b>
Каждый игрок получает $1500

🏠 <b>Недвижимость:</b>
• При попадании на свободную клетку можно её купить
• Если на вашей клетке остановился другой игрок - он платит аренду
• Можно строить дома для увеличения аренды

⚖️ <b>Особые клетки:</b>
• 🎰 Шанс - случайный бонус или штраф
• ⛓ Тюрьма - пропуск 3 ходов
• 🏦 Старт - проход через старт +$200

🔄 <b>Очередь хода:</b>
Игроки ходят по очереди по часовой стрелке

❌ <b>Банкротство:</b>
Если баланс уходит в минус - игрок выбывает!

🎮 <b>Удачи в игре!</b>
    """
    await c.message.answer(rules_text, parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "show_developer")
async def show_developer(c: types.CallbackQuery):
    """Показать информацию о разработчике"""
    await c.answer(f"👨‍💻 Разработчик: {DEV_TAG}", show_alert=True)

# --- [9] ОСТАЛЬНЫЕ ИГРОВЫЕ КНОПКИ ---
@dp.message(F.text == "🏠 Построить")
async def build_property(message: types.Message):
    """Постройка домов на недвижимости"""
    await message.answer("🏗 Функция постройки в разработке...")

@dp.message(F.text == "📊 Мои активы")
async def show_assets(message: types.Message):
    """Показать активы игрока"""
    try:
        chat_id = message.chat.id
        
        if chat_id not in ACTIVE_GAMES:
            await message.answer("⚠️ Нет активной игры")
            return
        
        game = ACTIVE_GAMES[chat_id]
        user_id = message.from_user.id
        
        # Находим игрока
        player_name = next((p["name"] for p in game["players"] if p["id"] == user_id), "Неизвестно")
        
        # Собираем информацию
        balance = game["balances"][user_id]
        position = game["positions"][user_id]
        
        # Находим недвижимость игрока
        player_properties = []
        for prop_id, owner_id in game["properties"].items():
            if owner_id == user_id:
                prop_name, price, rent, color = BOARD[prop_id]
                player_properties.append(f"• {prop_name} (${price})")
        
        properties_text = "\n".join(player_properties) if player_properties else "Нет недвижимости"
        
        await message.answer(
            f"📊 <b>Активы игрока {player_name}:</b>\n\n"
            f"💰 Баланс: <b>${balance}</b>\n"
            f"📍 Позиция: <b>{position}</b>\n\n"
            f"🏠 <b>Недвижимость:</b>\n{properties_text}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в show_assets: {e}")
        await message.answer("⚠️ Ошибка при получении активов")

@dp.message(F.text == "🤝 Торговля")
async def trade_property(message: types.Message):
    """Торговля с другими игроками"""
    await message.answer("🤝 Функция торговли в разработке...")

# --- [10] КОМАНДЫ УПРАВЛЕНИЯ ---
@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Показать статус игры"""
    try:
        chat_id = message.chat.id
        
        status_text = f"📊 <b>Статус в этой группе:</b>\n\n"
        
        if chat_id in WAITING_GAMES:
            game = WAITING_GAMES[chat_id]
            players_list = "\n".join([f"• {p['name']}" for p in game["players"]])
            status_text += (
                f"🕒 <b>Сбор игроков:</b>\n"
                f"Создатель: {game['creator_name']}\n"
                f"Игроков: {len(game['players'])}\n\n"
                f"<b>Ожидают:</b>\n{players_list}"
            )
        elif chat_id in ACTIVE_GAMES:
            game = ACTIVE_GAMES[chat_id]
            players_list = "\n".join([f"• {p['name']} (${game['balances'][p['id']]})" for p in game["players"]])
            status_text += (
                f"🎮 <b>Игра идет:</b>\n"
                f"Текущий ход: {game['current_player_name']}\n"
                f"Игроков: {len(game['players'])}\n\n"
                f"<b>Игроки и балансы:</b>\n{players_list}"
            )
        else:
            status_text += "❌ В этой группе нет активной игры.\nИспользуйте /monopoly чтобы начать"
        
        await message.answer(status_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_status: {e}")
        await message.answer("⚠️ Ошибка при получении статуса")

@dp.message(Command("end"))
async def cmd_end_game(message: types.Message):
    """Завершить игру (только создатель)"""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        if chat_id in WAITING_GAMES:
            game = WAITING_GAMES[chat_id]
            if user_id == game["creator_id"]:
                del WAITING_GAMES[chat_id]
                await message.answer("✅ Сбор игроков отменен создателем")
            else:
                await message.answer("⚠️ Только создатель может отменить сбор")
        elif chat_id in ACTIVE_GAMES:
            game = ACTIVE_GAMES[chat_id]
            # В активной игре может завершить любой, если большинство согласны
            # Упрощенная версия - завершает создатель первой игры
            creator_id = game.get("creator_id", game["players"][0]["id"])
            if user_id == creator_id:
                del ACTIVE_GAMES[chat_id]
                await message.answer("✅ Игра завершена создателем")
            else:
                await message.answer("⚠️ Завершить игру может создатель игры")
        else:
            await message.answer("⚠️ В этой группе нет активной игры")
            
    except Exception as e:
        logger.error(f"Ошибка в cmd_end_game: {e}")
        await message.answer("⚠️ Ошибка при завершении игры")

# --- [11] ЗАПУСК СЕРВЕРА ---
async def main():
    logger.info(f"🌐 Бот запускается на порту {PORT}")
    logger.info(f"🔑 Токен получен: {'*' * 10}{API_TOKEN[-5:] if API_TOKEN else 'НЕТ'}")
    
    await init_db()
    
    # Запуск Flask в отдельном потоке
    flask_thread = Thread(target=lambda: app.run(
        host="0.0.0.0", 
        port=PORT,
        debug=False,
        use_reloader=False
    ), daemon=True)
    flask_thread.start()
    logger.info(f"✅ Flask сервер запущен на порту {PORT}")
    
    # Запуск бота
    logger.info("🤖 Запускаю телеграм-бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Остановка бота по запросу пользователя")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
