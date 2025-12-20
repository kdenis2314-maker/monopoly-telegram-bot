import asyncio
import logging
import random
import sys
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAHo7ULbtqC5emHz8kt0_8vCAuLg_MTTJGU"
PORT = 8082
ADMIN_PASSWORD = "admin" # Пароль для входа в админку
LOGS = [] # Хранилище логов для сайта

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Данные игры
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "rent": 0},
    {"name": "🏠 Улица Пушкина", "price": 100, "rent": 20},
    {"name": "🏠 Улица Чехова", "price": 120, "rent": 25},
    {"name": "💸 Налоговая", "price": 0, "rent": 50},
    {"name": "🏨 Улица Горького", "price": 200, "rent": 40},
    {"name": "🏨 Проспект Мира", "price": 240, "rent": 50},
    {"name": "⛓ Тюрьма", "price": 0, "rent": 0},
    {"name": "💎 Арбат", "price": 400, "rent": 100},
]

players = {}
game_started = False

def add_log(text):
    time = datetime.now().strftime("%H:%M:%S")
    LOGS.append(f"[{time}] {text}")
    if len(LOGS) > 20: LOGS.pop(0)

# --- WEB АДМИН-ПАНЕЛЬ ---

async def admin_page(request):
    logs_html = "".join([f"<div style='border-bottom:1px solid #444;padding:5px;'>{log}</div>" for log in LOGS])
    html = f"""
    <html>
    <head>
        <title>Monopoly Admin</title>
        <style>
            body {{ background: #1a1a1a; color: #00ff00; font-family: monospace; padding: 20px; }}
            .card {{ background: #222; border: 1px solid #444; padding: 15px; margin-bottom: 20px; border-radius: 8px; }}
            input, button {{ background: #333; color: #fff; border: 1px solid #555; padding: 10px; }}
            button {{ cursor: pointer; background: #005500; }}
            .status {{ color: #00ff00; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>🎮 Monopoly Bot Control Panel</h1>
        <div class="card">
            <h3>Статус систем: <span class="status">ONLINE</span></h3>
            <p>Порт: {PORT} | Игроков в базе: {len(players)}</p>
        </div>
        
        <div class="card">
            <h3>😈 Тролл-меню (Отправить в чат)</h3>
            <form action="/send" method="post">
                <input type="text" name="chat_id" placeholder="Chat ID (например -100...)" required>
                <input type="text" name="text" placeholder="Ваше сообщение..." required>
                <button type="submit">ОТПРАВИТЬ</button>
            </form>
        </div>

        <div class="card">
            <h3>📋 Последние логи:</h3>
            <div style="background:#000; height: 300px; overflow-y: scroll; padding: 10px;">{logs_html}</div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def send_message_web(request):
    data = await request.post()
    try:
        await bot.send_message(data['chat_id'], data['text'])
        add_log(f"WEB: Отправлено сообщение в {data['chat_id']}")
    except Exception as e:
        add_log(f"WEB ERROR: {e}")
    return web.HTTPFound('/')

# --- ЛОГИКА БОТА ---

def draw_visual_map(user_id):
    p = players[user_id]
    res = "┏━━━━━━━━━━━━━━━━━━┓\n"
    for i, f in enumerate(BOARD):
        mark = "📍" if p['position'] == i else "▫️"
        owner = next((pl['name'] for pl in players.values() if i in pl['properties']), "")
        owner_str = f" 🏷 [{owner}]" if owner else ""
        res += f"┃ {mark} {f['name']}{owner_str}\n"
    res += "┗━━━━━━━━━━━━━━━━━━┛"
    return res

@dp.message(Command("monopoly"))
async def start_game(message: types.Message):
    add_log(f"Команда /monopoly от {message.from_user.first_name}")
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Поделиться", switch_inline_query="Го играть!")
    kb.button(text="👨‍💻 Dev", callback_data="dev")
    await message.answer("💎 **M O N O P O L Y** 💎\n\nДобро пожаловать в игру!", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "dev")
async def dev_info(callback: types.CallbackQuery):
    await callback.message.answer("👨‍💻 Разработчик: @Whylovely05\n🎮 Чат: Shit daily")

# --- ЗАПУСК ---

async def main():
    # Настройка Web-сервера
    app = web.Application()
    app.router.add_get('/', admin_page)
    app.router.add_post('/send', send_message_web)
    
    runner = web.AppRunner(app)
    await runner.setup() # КРИТИЧЕСКИЙ МОМЕНТ: Добавляем await
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    add_log("Система инициализирована. Порт 8082 открыт.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
