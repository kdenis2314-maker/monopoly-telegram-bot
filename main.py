import os
import asyncio
import aiosqlite
import logging
import json
import sys
from datetime import datetime
from threading import Thread
from flask import Flask, render_template

# --- НАСТРОЙКИ И ПЕРЕМЕННЫЕ ---
API_TOKEN = os.environ.get("BOT_TOKEN")
if not API_TOKEN:
    logging.error("❌ BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

PORT = int(os.environ.get("PORT", 8083))
DEV_TAG = "@Whylovely05"
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

# Хранилища игр (временное решение)
WAITING_GAMES = {}
ACTIVE_GAMES = {}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- FLASK СЕРВЕР ---
app = Flask(__name__)

@app.route('/')
def index():
    """Главная страница статуса"""
    stats_copy = STATS.copy()
    stats_copy["active_games"] = len(ACTIVE_GAMES)
    stats_copy["waiting_games"] = len(WAITING_GAMES)
    bot_name = "Monopoly Premium"
    
    # Получаем домен
    external_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if external_hostname:
        domain = f"https://{external_hostname}"
    else:
        domain = f"http://localhost:{PORT}"
    
    return render_template('status.html', 
                         stats=stats_copy,
                         bot_name=bot_name,
                         domain=domain,
                         port=PORT,
                         start_time=stats_copy["started"],
                         dev_tag=DEV_TAG)

@app.route('/stats')
def stats_api():
    """API статистики в JSON формате"""
    stats_copy = STATS.copy()
    stats_copy["active_games"] = len(ACTIVE_GAMES)
    stats_copy["waiting_games"] = len(WAITING_GAMES)
    return json.dumps(stats_copy, ensure_ascii=False, indent=2)

@app.route('/health')
def health():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok", 
        "bot": "running", 
        "active_games": len(ACTIVE_GAMES),
        "waiting_games": len(WAITING_GAMES),
        "timestamp": datetime.now().isoformat()
    }, 200

@app.route('/games')
def games_list():
    """Список активных и ожидающих игр"""
    active = {}
    for chat_id, game in ACTIVE_GAMES.items():
        active[chat_id] = {
            "started": game.get("started_at", datetime.now()).isoformat(),
            "players": len(game.get("players", [])),
            "creator": game.get("creator_name", "Unknown")
        }
    
    waiting = {}
    for chat_id, game in WAITING_GAMES.items():
        waiting[chat_id] = {
            "created": game.get("created_at", datetime.now()).isoformat(),
            "players": len(game.get("players", [])),
            "creator": game.get("creator_name", "Unknown")
        }
    
    return {
        "active_games": active,
        "waiting_games": waiting,
        "total_active": len(ACTIVE_GAMES),
        "total_waiting": len(WAITING_GAMES)
    }

# Создаем папку templates если её нет
if not os.path.exists('templates'):
    os.makedirs('templates')

# HTML шаблон для статусной страницы
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
        .games-list { background: rgba(30, 30, 50, 0.6); border-radius: 10px; padding: 15px; margin-top: 10px; }
        .game-item { padding: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
        .game-item:last-child { border-bottom: none; }
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
                <div class="games-list">
                    <div class="game-item">Активные: {{ stats.active_games }}</div>
                    <div class="game-item">В лобби: {{ stats.waiting_games }}</div>
                </div>
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
            <a href="/health" class="log-button" style="margin-left: 10px;">❤️ Health Check</a>
            <a href="/games" class="log-button" style="margin-left: 10px;">🎮 Список игр</a>
        </div>
        
        <div class="footer">
            <p>Система мониторинга Monopoly Premium Bot</p>
            <div class="uptime">⏱ Uptime: {{ stats.started }}</div>
            <p style="margin-top: 15px;">🔧 При возникновении проблем используйте команду /hide для сброса меню</p>
        </div>
    </div>
    
    <script>
        // Автоматическое обновление каждые 30 секунд
        function updateStats() {
            fetch('/stats')
                .then(response => response.json())
                .then(data => {
                    document.querySelectorAll('.status-card')[0].querySelectorAll('.value')[1].textContent = data.active_games;
                    document.querySelectorAll('.status-card')[0].querySelectorAll('.value')[2].textContent = data.waiting_games;
                    document.querySelectorAll('.status-card')[0].querySelectorAll('.value')[3].textContent = data.total_players;
                })
                .catch(err => console.log('Ошибка обновления:', err));
        }
        
        // Проверка здоровья
        setInterval(() => {
            fetch('/health').then(response => response.json()).then(data => {
                if (data.status === 'ok') {
                    console.log('✅ Bot is healthy at', new Date().toLocaleTimeString());
                }
            }).catch(err => console.log('Health check failed:', err));
        }, 30000);
        
        // Анимация при загрузке
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
            
            // Первое обновление
            setTimeout(updateStats, 1000);
            
            // Автообновление каждую минуту
            setInterval(updateStats, 60000);
        });
    </script>
</body>
</html>'''

# Сохраняем HTML шаблон
with open('templates/status.html', 'w', encoding='utf-8') as f:
    f.write(status_html)

# --- БАЗА ДАННЫХ ---
async def init_db():
    """Инициализация базы данных"""
    try:
        async with aiosqlite.connect('monopoly_premium.db') as db:
            # Таблица игроков
            await db.execute("""CREATE TABLE IF NOT EXISTS players (
                chat_id int, 
                user_id int, 
                name text, 
                balance int DEFAULT 1500, 
                pos int DEFAULT 0, 
                jail int DEFAULT 0, 
                PRIMARY KEY(chat_id, user_id)
            )""")
            
            # Таблица собственности
            await db.execute("""CREATE TABLE IF NOT EXISTS property (
                chat_id int, 
                cell_idx int, 
                owner_id int, 
                houses int DEFAULT 0, 
                PRIMARY KEY(chat_id, cell_idx)
            )""")
            
            # Таблица достижений
            await db.execute("""CREATE TABLE IF NOT EXISTS awards (
                user_id int, 
                title text, 
                chat_id int,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            # Таблица истории игр
            await db.execute("""CREATE TABLE IF NOT EXISTS game_history (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id int,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                winner_id int,
                winner_name text,
                players_count int,
                duration_minutes int
            )""")
            
            await db.commit()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

# --- ИГРОВАЯ ДОСКА ---
BOARD = {
    1: ["Житная", 60, 4, "BROWN"],
    3: ["Нагатинская", 60, 4, "BROWN"],
    5: ["Рижская ж/д", 200, 25, "RAIL"],
    6: ["Варшавское ш.", 100, 6, "BLUE"],
    8: ["Огородный пр.", 100, 6, "BLUE"],
    9: ["Рижская", 120, 8, "BLUE"],
    11: ["Курская", 140, 10, "PINK"],
    12: ["Электросеть", 150, 10, "UTIL"],
    13: ["Абрамцево", 140, 10, "PINK"],
    14: ["Пантелеевская", 160, 12, "PINK"],
    15: ["Казанская ж/д", 200, 25, "RAIL"],
    16: ["Вавилова", 180, 14, "ORANGE"],
    18: ["Тимирязевская", 180, 14, "ORANGE"],
    19: ["Лихоборы", 200, 16, "ORANGE"],
    21: ["Арбат", 220, 18, "RED"],
    23: ["Полянка", 220, 18, "RED"],
    24: ["Сретенка", 240, 20, "RED"],
    25: ["Курская ж/д", 200, 25, "RAIL"],
    26: ["Ростовская", 260, 22, "YELLOW"],
    27: ["Рязанский пр.", 260, 22, "YELLOW"],
    28: ["Водопровод", 150, 10, "UTIL"],
    29: ["Новинский б-р", 280, 24, "YELLOW"],
    31: ["Пушкинская", 300, 26, "GREEN"],
    32: ["Тверская", 300, 26, "GREEN"],
    34: ["Маяковского", 320, 28, "GREEN"],
    35: ["Ленинградская ж/д", 200, 25, "RAIL"],
    37: ["Кутузовский", 350, 35, "DARKBLUE"],
    39: ["Бродвей", 400, 50, "DARKBLUE"]
}

# Специальные клетки
SPECIAL_CELLS = {
    0: ["СТАРТ", "Получите 200$ при прохождении"],
    2: ["КАЗНА", "Вытяните карту казны"],
    4: ["ПОДОХОДНЫЙ НАЛОГ", "Заплатите 200$"],
    7: ["ШАНС", "Вытяните карту шанса"],
    10: ["ТЮРЬМА", "Просто посещение"],
    17: ["КАЗНА", "Вытяните карту казны"],
    20: ["БЕСПЛАТНАЯ ПАРКОВКА", "Бесплатный отдых"],
    22: ["ШАНС", "Вытяните карту шанса"],
    30: ["ОТПРАВЛЯЙТЕСЬ В ТЮРЬМУ", "Прямо в тюрьму!"],
    33: ["КАЗНА", "Вытяните карту казны"],
    36: ["ШАНС", "Вытяните карту шанса"],
    38: ["СУПЕРНАЛОГ", "Заплатите 100$"]
}

def get_cell_info(cell_index):
    """Получить информацию о клетке"""
    if cell_index in BOARD:
        name, price, rent, color = BOARD[cell_index]
        return {
            "name": name,
            "price": price,
            "rent": rent,
            "color": color,
            "type": "property"
        }
    elif cell_index in SPECIAL_CELLS:
        name, description = SPECIAL_CELLS[cell_index]
        return {
            "name": name,
            "description": description,
            "type": "special"
        }
    else:
        return {
            "name": f"Клетка {cell_index}",
            "type": "empty"
        }

def calculate_rent(cell_index, houses=0, is_monopoly=False):
    """Рассчитать арендную плату"""
    if cell_index not in BOARD:
        return 0
    
    _, base_price, base_rent, color = BOARD[cell_index]
    
    if houses == 0:
        if is_monopoly:
            return base_rent * 2
        return base_rent
    elif houses == 1:
        return base_rent * 5
    elif houses == 2:
        return base_rent * 15
    elif houses == 3:
        return base_rent * 40
    elif houses == 4:
        return base_rent * 80
    elif houses == 5:  # Отель
        return base_rent * 125
    
    return base_rent

# --- ЗАПУСК СЕРВЕРА ---
def run_flask_server():
    """Запуск Flask сервера"""
    try:
        logger.info(f"🌐 Flask сервер запускается на 0.0.0.0:{PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Ошибка Flask сервера: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Только для тестирования Flask части
    print("🚀 Запуск только Flask части...")
    run_flask_server()

