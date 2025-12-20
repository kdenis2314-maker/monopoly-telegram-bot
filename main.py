import asyncio
import os
import random
import logging
from flask import Flask, render_template_string
from threading import Thread
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramConflictError

# --- 1. ЛОГИРОВАНИЕ ДЛЯ ВЕБ-ПАНЕЛИ ---
logs_list = []

def add_log(text):
    time_str = datetime.now().strftime("%H:%M:%S")
    full_log = f"[{time_str}] {text}"
    logs_list.append(full_log)
    if len(logs_list) > 20:
        logs_list.pop(0)
    print(full_log) # Дублируем в консоль Render

# --- 2. НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU" # ЗАМЕНИ НА НОВЫЙ, ЕСЛИ СДЕЛАЛ REVOKE
PORT = int(os.environ.get("PORT", 10000))

BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "icon": "🚩"},
    {"name": "🏘️ Улица Мира", "price": 100, "icon": "🏘️"},
    {"name": "🎲 ШАНС", "price": 0, "icon": "❓"},
    {"name": "🏢 Пр-т Ленина", "price": 150, "icon": "🏢"},
    {"name": "🛒 Магазин", "price": 200, "icon": "🛒"},
    {"name": "👮 Тюрьма", "price": 0, "icon": "👮"},
    {"name": "🎲 ШАНС", "price": 0, "icon": "❓"},
    {"name": "🏨 Отель 'Гранд'", "price": 300, "icon": "🏨"},
    {"name": "🌳 Парк Культуры", "price": 120, "icon": "🌳"},
    {"name": "🚉 Вокзал", "price": 250, "icon": "🚉"},
    {"name": "💎 Алмазный Фонд", "price": 400, "icon": "💎"},
    {"name": "🎡 Цирк", "price": 140, "icon": "🎡"}
]

players = {}
lobby_players = []
game_active = False

# --- 3. ВЕБ-ИНТЕРФЕЙС (FLASK) ---
app = Flask(__name__)

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monopoly Console</title>
        <meta http-equiv="refresh" content="3">
        <style>
            body { background: #0a0a0a; color: #00ff00; font-family: monospace; padding: 20px; }
            .console { background: #000; border: 1px solid #333; padding: 15px; border-radius: 5px; min-height: 300px; }
            .log-entry { margin-bottom: 5px; border-bottom: 1px solid #111; padding-bottom: 2px; }
            h2 { color: #fff; }
            .stat { color: #aaa; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h2>🎮 Monopoly Bot Admin Panel</h2>
        <div class="stat">Статус: ONLINE | Игроков: {{ count }}</div>
        <div class="console">
            {% for log in logs %}
                <div class="log-entry">{{ log }}</div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, logs=logs_list[::-1], count=len(players))

def run_flask():
    add_log("🌐 Запуск веб-сервера...")
    app.run(host='0.0.0.0', port=PORT)

# --- 4. MIDDLEWARE ДЛЯ МОНИТОРИНГА ---
class MonitorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            add_log(f"📩 Текст: {event.text} (от {event.from_user.first_name})")
        elif isinstance(event, CallbackQuery):
            add_log(f"🔘 Кнопка: {event.data} (от {event.from_user.first_name})")
        return await handler(event, data)

# --- 5. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()
dp.update.outer_middleware(MonitorMiddleware())

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Начать сбор", callback_query_data="l_start")]])
    await m.answer("🏨 **MONOPOLY ONLINE**\nБот активен и готов к игре!", reply_markup=kb)

@dp.callback_query(F.data == "l_start")
async def l_start(call: CallbackQuery):
    global lobby_players, game_active
    lobby_players, game_active = [], False
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Вступить", callback_query_data="l_join")]])
    await call.message.edit_text("📢 **СБОР ИГРОКОВ**\nЖдем участников...", reply_markup=kb)

@dp.callback_query(F.data == "l_join")
async def l_join(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in lobby_players:
        lobby_players.append(uid)
        players[uid] = {"balance": 1500, "pos": 0, "name": call.from_user.first_name}
    
    kb = [[InlineKeyboardButton(text="✅ Вступить", callback_query_data="l_join")]]
    if len(lobby_players) >= 1: # Минимум 1 для теста
        kb.append([InlineKeyboardButton(text="🏁 НАЧАТЬ ИГРУ", callback_query_data="g_start")])
    
    await call.message.edit_text(f"👥 **В лобби:** {len(lobby_players)} чел.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "g_start")
async def g_start(call: CallbackQuery):
    global game_active
    game_active = True
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 Бросить кубик", callback_query_data="roll")]])
    await call.message.answer("🎉 **ИГРА НАЧАЛАСЬ!**", reply_markup=kb)
    await call.message.delete()

@dp.callback_query(F.data == "roll")
async def roll(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in players: return await call.answer("Вы не в игре")
    
    steps = random.randint(1, 6)
    p = players[uid]
    p['pos'] = (p['pos'] + steps) % len(BOARD)
    cell = BOARD[p['pos']]
    
    res = f"🎲 **{p['name']}** выкинул {steps}\n📍 Клетка: {cell['icon']} {cell['name']}"
    if cell['price'] > 0:
        p['balance'] -= cell['price']
        res += f"\n💸 Списано: {cell['price']}$"

    await call.message.answer(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить еще", callback_query_data="roll")]
    ]))
    await call.answer()

# --- 6. ГЛАВНЫЙ ЦИКЛ ЗАПУСКА ---
async def start_bot():
    add_log("🤖 Инициализация бота...")
    
    while True:
        try:
            # Очистка вебхуков
            await bot.delete_webhook(drop_pending_updates=True)
            add_log("🧹 Вебхуки сброшены, начинаем опрос (Polling)...")
            
            # Запуск опроса
            await dp.start_polling(bot)
            
        except TelegramConflictError:
            add_log("⚠️ ОШИБКА: Конфликт токена! Жду 10 секунд...")
            await asyncio.sleep(10)
        except Exception as e:
            add_log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # Запуск Flask в отдельном потоке
    t = Thread(target=run_flask, daemon=True)
    t.start()
    
    # Запуск бота
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        add_log("🛑 Бот остановлен вручную")
