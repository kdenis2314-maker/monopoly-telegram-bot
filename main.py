import asyncio
import logging
import os
import time
from flask import Flask, render_template_string, request, redirect
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ.get("TOKEN")
# Укажите юзернейм вашего бота БЕЗ @ (обязательно для кнопки "Добавить в группу")
BOT_USERNAME = "ВАШ_ЮЗЕРНЕЙМ_БОТА" 

# Глобальная статистика для сайта
start_time = time.time()
logs_list = []

def add_log(msg):
    logs_list.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    if len(logs_list) > 20: logs_list.pop(0)

# --- САМАЯ МОЩНАЯ АДМИН-ПАНЕЛЬ ---
app = Flask(__name__)

DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Monopoly Control</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0d1117; color: #c9d1d9; font-family: sans-serif; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; }
        .accent { color: #58a6ff; font-weight: bold; }
        .log-box { background: #000; color: #39ff14; padding: 10px; height: 300px; overflow-y: auto; font-family: monospace; border-radius: 8px; font-size: 13px; }
        .btn-action { background: #238636; border: none; color: white; }
        .btn-action:hover { background: #2ea043; }
    </style>
</head>
<body class="p-4">
    <div class="container">
        <h2 class="mb-4">🏦 Monopoly <span class="accent">Engine v3.5</span></h2>
        <div class="row g-3 mb-4">
            <div class="col-md-4"><div class="card p-3">Статус: <span class="text-success">ONLINE</span></div></div>
            <div class="col-md-4"><div class="card p-3">Аптайм: {{ uptime }} мин.</div></div>
            <div class="col-md-4"><div class="card p-3">Логи: {{ log_count }}</div></div>
        </div>
        <div class="row">
            <div class="col-md-7">
                <div class="card p-4 h-100">
                    <h5>🎭 Отправить сообщение от бота (Шутки)</h5>
                    <form action="/send" method="POST">
                        <input type="text" name="uid" class="form-control bg-dark text-white mb-2" placeholder="User ID">
                        <textarea name="msg" class="form-control bg-dark text-white mb-3" placeholder="Текст сообщения..."></textarea>
                        <button type="submit" class="btn btn-action w-100">Отправить в Telegram</button>
                    </form>
                </div>
            </div>
            <div class="col-md-5">
                <div class="card p-4 h-100">
                    <h5>📜 Консоль (Live)</h5>
                    <div class="log-box">
                        {% for log in logs %}<div style="border-bottom: 1px solid #222;">{{ log }}</div>{% endfor %}
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
    upt = int((time.time() - start_time) / 60)
    return render_template_string(DASH_HTML, uptime=upt, log_count=len(logs_list), logs=logs_list[::-1])

@app.route('/send', methods=['POST'])
def send_joke():
    uid, msg = request.form.get('uid'), request.form.get('msg')
    if uid and msg:
        asyncio.run_coroutine_threadsafe(bot.send_message(uid, msg), loop)
        add_log(f"ADMIN: Сообщение отправлено пользователю {uid}")
    return redirect('/')

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
loop = None

def get_keyboard(is_group=False):
    kb = InlineKeyboardBuilder()
    if is_group:
        kb.row(InlineKeyboardButton(text="🎮 Играть (от 2 чел)", callback_data="play_group"))
        kb.row(InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="info_dev"),
               InlineKeyboardButton(text="📜 Правила", callback_data="info_rules"))
    else:
        kb.row(InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
        kb.row(InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="info_dev"))
        kb.row(InlineKeyboardButton(text="📜 Правила игры", callback_data="info_rules"))
    return kb.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_log(f"User {message.from_user.id} ({message.from_user.first_name}) нажал /start")
    is_group = message.chat.type != "private"
    text = "🏘 **Добро пожаловать в Монополию!**\n\nВыберите действие:" if not is_group else "🏙 **Бот активен в группе!**"
    await message.answer(text, reply_markup=get_keyboard(is_group), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("info_"))
async def handle_info(call: types.CallbackQuery):
    if call.data == "info_dev":
        await call.message.edit_text("👨‍💻 **Разработчик:** Denix-Maker\n\nБот работает на мощном асинхронном движке v3.5 через Render Cloud.", reply_markup=call.message.reply_markup, parse_mode="Markdown")
    else:
        await call.message.edit_text("📜 **Краткие правила:**\n1. Минимум 2 игрока.\n2. Покупайте улицы, стройте монополии.\n3. Цель - разорить всех!", reply_markup=call.message.reply_markup, parse_mode="Markdown")
    await call.answer()

async def main():
    global loop
    loop = asyncio.get_running_loop()
    logging.basicConfig(level=logging.INFO)
    
    # Запуск сайта в фоне
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True).start()
    
    add_log("Система запущена. Движок готов.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
