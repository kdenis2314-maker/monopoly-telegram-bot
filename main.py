import asyncio
import logging
import os
import sys
import time
import random
from flask import Flask, render_template_string, request
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКИ ---
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
TOKEN = os.environ.get("TOKEN")
PORT = int(os.environ.get("PORT", 8080))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MonopolyRobot") # Укажите в Environment Variables

# Состояние игры (в памяти)
games = {} # {chat_id: {players: [], status: "waiting/playing", turn: 0}}
site_logs = []

def add_log(msg):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    if len(site_logs) > 30: site_logs.pop(0)

# --- ВЕБ-ИНТЕРФЕЙС (АДМИН-ПАНЕЛЬ) ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Monopoly Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0f172a; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid #334155; border-radius: 15px; padding: 20px; }
        .status-online { color: #10b981; font-weight: bold; }
        .log-container { background: #020617; color: #38bdf8; height: 400px; overflow-y: auto; font-family: 'Courier New', monospace; padding: 15px; border-radius: 10px; border: 1px solid #1e293b; }
        .btn-primary { background: #3b82f6; border: none; }
        .btn-primary:hover { background: #2563eb; }
    </style>
</head>
<body class="container py-5">
    <div class="row g-4">
        <div class="col-md-4">
            <div class="glass shadow">
                <h2 class="text-primary">🏦 Monopoly OS</h2>
                <hr class="text-secondary">
                <p>Статус: <span class="status-online">ACTIVE 🟢</span></p>
                <p>Активных игр: <b>{{ games_count }}</b></p>
                <p>Uptime: <b>{{ uptime }} мин.</b></p>
                <hr class="text-secondary">
                <h5>Управление</h5>
                <form action="/broadcast" method="POST">
                    <textarea name="msg" class="form-control bg-dark text-white mb-2" placeholder="Объявление всем..."></textarea>
                    <button class="btn btn-primary w-100">Разослать</button>
                </form>
            </div>
        </div>
        <div class="col-md-8">
            <div class="glass shadow">
                <h4>📜 Системный лог</h4>
                <div class="log-container">
                    {% for l in logs %} <div><small class="text-secondary">{{ loop.index }}.</small> {{ l }}</div> {% endfor %}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    uptime = int((time.time() - start_time) / 60)
    return render_template_string(HTML_TEMPLATE, logs=site_logs[::-1], uptime=uptime, games_count=len(games))

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
start_time = time.time()

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏢 Добавить в группу", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
    builder.row(InlineKeyboardButton(text="📜 Правила игры", callback_data="rules"),
                InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="dev"))
    builder.row(InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats"))
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type == 'private':
        add_log(f"User {message.from_user.id} started bot")
        welcome_text = (
            f"👋 *Привет, {message.from_user.first_name}!*\n\n"
            "🏦 **Monopoly Bot** — это полноценная экономическая стратегия прямо в Telegram.\n\n"
            "📍 *Как играть?*\n"
            "1. Добавь меня в группу с друзьями.\n"
            "2. Введи команду `/monopoly`.\n"
            "3. Стань самым богатым магнатом!"
        )
        await message.answer(welcome_text, reply_markup=main_menu_kb(), parse_mode="Markdown")
    else:
        await message.answer("🏦 Бот активен! Используйте /monopoly для начала игры.")

@dp.callback_query(F.data == "rules")
async def show_rules(call: types.CallbackQuery):
    rules = (
        "📖 *Краткие правила:*\n"
        "• Игроки ходят по очереди, бросая кубики.\n"
        "• Покупайте свободные предприятия.\n"
        "• Если игрок попадает на чужое поле, он платит ренту.\n"
        "• Цель: обанкротить соперников."
    )
    await call.message.edit_text(rules, reply_markup=main_menu_kb(), parse_mode="Markdown")

@dp.message(Command("monopoly"))
async def start_game(message: types.Message):
    if message.chat.type == 'private':
        return await message.answer("❌ Игру можно запустить только в группе!")
    
    chat_id = message.chat.id
    if chat_id in games:
        return await message.answer("⚠️ Игра в этом чате уже идет или создается.")
    
    games[chat_id] = {"players": [message.from_user.id], "status": "waiting"}
    add_log(f"Game created in {chat_id}")
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Присоединиться ✅", callback_data="join_game"))
    builder.add(InlineKeyboardButton(text="Начать игру 🎲", callback_data="start_match"))
    
    await message.answer(
        f"🎮 *Сбор игроков в Монополию!*\n\n"
        f"Игроков в лобби: 1\n"
        "Нужно минимум 2 человека.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "join_game")
async def join_game(call: types.CallbackQuery):
    cid = call.message.chat.id
    uid = call.from_user.id
    
    if cid not in games: return
    if uid in games[cid]["players"]:
        return await call.answer("Вы уже в игре!", show_alert=True)
    
    games[cid]["players"].append(uid)
    await call.answer("Вы успешно вступили!")
    
    # Обновление счетчика (упрощенно)
    count = len(games[cid]["players"])
    await call.message.edit_text(
        f"🎮 *Сбор игроков в Монополию!*\n\n"
        f"Игроков в лобби: {count}\n"
        "Нажмите кнопку ниже, когда все будут готовы.",
        reply_markup=call.message.reply_markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "start_match")
async def start_match(call: types.CallbackQuery):
    cid = call.message.chat.id
    if len(games.get(cid, {}).get("players", [])) < 2:
        return await call.answer("Нужно минимум 2 игрока!", show_alert=True)
    
    games[cid]["status"] = "playing"
    add_log(f"Match started in {cid}")
    await call.message.answer("🎲 **Игра началась!** Бросаю кубики для первого игрока...")
    # Здесь подключается сложная механика ходов (Dice, Rent, Buy)

# --- ЗАПУСК ---
async def run_bot():
    add_log("Bot engine starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    # Запуск Flask в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
    # Запуск бота в основном потоке
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass
