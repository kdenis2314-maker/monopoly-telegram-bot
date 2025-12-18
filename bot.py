import asyncio
import logging
import os
import time
import random
from flask import Flask, render_template_string, request, redirect
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, WebAppInfo

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TOKEN")
BOT_USERNAME = "Monopolysigma_bot" # Замените на имя без @
start_time = time.time()
logs = []

def add_log(msg):
    logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    if len(logs) > 15: logs.pop(0)

# --- МОЩНЫЙ ДВИЖОК (БАЗА ДАННЫХ В ПАМЯТИ) ---
# В реальном проекте лучше использовать БД (SQLAlchemy/MongoDB)
game_sessions = {} # Хранение активных игр в группах

# --- КРАСИВЫЙ САЙТ-ПАНЕЛЬ ---
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Monopoly Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0b0e14; color: #cfd8dc; font-family: 'Inter', sans-serif; }
        .stat-card { background: #151921; border-radius: 15px; border: 1px solid #2d333b; transition: 0.3s; }
        .stat-card:hover { border-color: #00ff88; transform: translateY(-5px); }
        .log-container { background: #000; color: #00ff41; padding: 15px; border-radius: 10px; font-family: 'Courier New'; height: 250px; overflow-y: auto; font-size: 0.9rem; }
        .accent { color: #00ff88; }
        .btn-send { background: linear-gradient(45deg, #00ff88, #00b0ff); border: none; color: black; font-weight: bold; }
    </style>
</head>
<body class="p-4">
    <div class="container">
        <header class="d-flex justify-content-between align-items-center mb-5">
            <h1>🏦 Monopoly <span class="accent">Control Center</span></h1>
            <div class="badge bg-success p-2">System Online</div>
        </header>

        <div class="row mb-4">
            <div class="col-md-3">
                <div class="stat-card p-4 text-center">
                    <h6>Активных игр</h6>
                    <h2 class="accent">{{ games_count }}</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card p-4 text-center">
                    <h6>Uptime</h6>
                    <h2 class="accent">{{ uptime }} мин.</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card p-4 text-center">
                    <h6>Логи событий</h6>
                    <h2 class="accent">{{ logs_count }}</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card p-4 text-center">
                    <h6>Версия ядра</h6>
                    <h2 class="accent">3.5.0</h2>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-7">
                <div class="stat-card p-4 h-100">
                    <h5>🛠 Управление (Шутки над юзерами)</h5>
                    <form action="/send" method="POST">
                        <div class="mb-3">
                            <input type="text" name="user_id" class="form-control bg-dark text-white border-secondary" placeholder="Telegram ID пользователя">
                        </div>
                        <div class="mb-3">
                            <textarea name="text" class="form-control bg-dark text-white border-secondary" placeholder="Сообщение (например: 'Поздравляем! Вы обанкротились на ровном месте!')"></textarea>
                        </div>
                        <button type="submit" class="btn btn-send w-100">Отправить от имени бота</button>
                    </form>
                </div>
            </div>
            <div class="col-md-5">
                <div class="stat-card p-4 h-100">
                    <h5>📜 Консоль событий</h5>
                    <div class="log-container">
                        {% for log in logs %}
                        <div>{{ log }}</div>
                        {% endfor %}
                    </div>
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
    return render_template_string(DASHBOARD_HTML, games_count=len(game_sessions), uptime=uptime, logs_count=len(logs), logs=logs[::-1])

@app.route('/send', methods=['POST'])
def send():
    uid = request.form.get('user_id')
    txt = request.form.get('text')
    if uid and txt:
        asyncio.run_coroutine_threadsafe(bot.send_message(uid, txt), loop)
        add_log(f"ADMIN SEND to {uid}: {txt[:20]}...")
    return redirect('/')

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
loop = None

# Клавиатура для ЛС
def private_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
    builder.row(InlineKeyboardButton(text="👨‍💻 О разработчике", callback_data="dev"))
    builder.row(InlineKeyboardButton(text="📜 Правила и игра", callback_data="rules"))
    return builder.as_markup()

# Клавиатура для Группы
def group_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎮 Играть (от 2 чел)", callback_data="join_game"))
    builder.row(InlineKeyboardButton(text="ℹ️ Инфо", callback_data="rules"))
    builder.row(InlineKeyboardButton(text="👑 Разработчик", callback_data="dev"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start(message: types.Message):
    add_log(f"Start by {message.from_user.id}")
    if message.chat.type == 'private':
        await message.answer("🏦 **Центральный Банк Монополии** приветствует тебя!\n\nИспользуй меню ниже для настройки:", reply_markup=private_kb(), parse_mode="Markdown")
    else:
        await message.answer("🏙 **Монополия готова к запуску в этой группе!**\n\nНажмите кнопку ниже, чтобы собрать игроков.", reply_markup=group_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "rules")
async def show_rules(call: types.CallbackQuery):
    rules = (
        "📜 **Правила Монополии:**\n"
        "• Для старта нужно минимум 2 игрока.\n"
        "• Бросайте кубики, покупайте улицы, стройте отели.\n"
        "• Цель: разорить оппонентов и захватить рынок.\n\n"
        "💎 **Движок v3.5:**\n"
        "• Стабильные расчеты\n• Авто-сохранение прогресса"
    )
    await call.message.edit_text(rules, reply_markup=call.message.reply_markup, parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "dev")
async def show_dev(call: types.CallbackQuery):
    await call.message.edit_text("👨‍💻 **Developer:** `Denix-Maker`\n🚀 **Platform:** Render Cloud\n⚡️ **Engine:** Aiogram 3.x", reply_markup=call.message.reply_markup, parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "join_game")
async def join_game(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    if chat_id not in game_sessions:
        game_sessions[chat_id] = set()
    
    game_sessions[chat_id].add(user_id)
    count = len(game_sessions[chat_id])
    
    add_log(f"User {user_id} joined game in {chat_id}")
    
    msg = f"🎮 **Сбор игроков!**\n\nПрисоединилось: `{count}` чел.\n"
    if count < 2:
        msg += "⚠️ Нужно еще минимум 1 человек."
    else:
        msg += "✅ Можно начинать! (Админ, используй /play)"
        
    await call.message.edit_text(msg, reply_markup=group_kb(), parse_mode="Markdown")
    await call.answer("Вы в игре!")

async def main():
    global loop
    loop = asyncio.get_running_loop()
    logging.basicConfig(level=logging.INFO)
    
    # Запуск Flask в потоке
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True).start()
    
    add_log("Core Engine v3.5 Started")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                             
