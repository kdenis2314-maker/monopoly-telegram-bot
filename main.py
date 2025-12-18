import asyncio
import logging
import os
import sys
import time
from flask import Flask, render_template_string, request, redirect
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

# Принудительная настройка логирования для Render
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

# Переменные из вашей панели Render
TOKEN = os.environ.get("TOKEN")
PORT = int(os.environ.get("PORT", 8080))
# Вставьте имя вашего бота БЕЗ @ (например: MonopolyBestBot)
BOT_USERNAME = "ВАШ_ЮЗЕРНЕЙМ_БОТА" 

site_logs = []

def add_log(msg):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    print(f"RENDER_LOG: {entry}", flush=True)
    if len(site_logs) > 20: site_logs.pop(0)

# --- АДМИН-ПАНЕЛЬ (САЙТ) ---
app = Flask(__name__)

@app.route('/')
def dashboard():
    uptime = int((time.time() - start_time) / 60)
    html = """
    <body style="background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:20px;">
        <h1 style="color:#58a6ff;">🏦 Monopoly Admin Control Center</h1>
        <div style="display:flex; gap:20px;">
            <div style="flex:1; background:#161b22; padding:15px; border:1px solid #30363d; border-radius:10px;">
                <h3>📊 Статус Системы</h3>
                <p>Uptime: <b>{{ uptime }} мин.</b></p>
                <p>Статус бота: <b style="color:#3fb950;">ONLINE 🟢</b></p>
                <hr>
                <form action="/send_joke" method="POST">
                    <h4>🎭 Шутка (Написать от бота)</h4>
                    <input type="text" name="uid" placeholder="User ID" style="width:100%; margin-bottom:5px; background:#0d1117; color:white; border:1px solid #30363d;">
                    <textarea name="msg" placeholder="Текст шутки" style="width:100%; height:60px; background:#0d1117; color:white; border:1px solid #30363d;"></textarea>
                    <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">Отправить</button>
                </form>
            </div>
            <div style="flex:1; background:#161b22; padding:15px; border:1px solid #30363d; border-radius:10px;">
                <h3>📜 Консоль событий</h3>
                <div style="background:black; color:#39ff14; padding:10px; height:280px; overflow-y:auto; font-family:monospace; font-size:12px;">
                    {% for l in logs %} <div>{{ l }}</div> {% endfor %}
                </div>
            </div>
        </div>
    </body>
    """
    return render_template_string(html, uptime=uptime, logs=site_logs[::-1])

@app.route('/send_joke', methods=['POST'])
def send_joke():
    uid, msg = request.form.get('uid'), request.form.get('msg')
    if uid and msg:
        asyncio.run_coroutine_threadsafe(bot.send_message(uid, msg), loop)
        add_log(f"ADMIN: Отправлено сообщение пользователю {uid}")
    return redirect('/')

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
loop = None
start_time = time.time()

def get_kb(is_group):
    kb = InlineKeyboardBuilder()
    if is_group:
        kb.row(InlineKeyboardButton(text="🎮 Играть (от 2 чел)", callback_data="join"))
    else:
        kb.row(InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
    kb.row(InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="dev"),
           InlineKeyboardButton(text="📜 Правила", callback_data="rules"))
    return kb.as_markup()

@dp.message(Command("start"))
async def start(m: types.Message):
    add_log(f"Старт от {m.from_user.id}")
    is_group = m.chat.type != 'private'
    txt = "🏙 **Монополия готова к игре в группе!**" if is_group else "🏦 **Добро пожаловать в Банк!**"
    await m.answer(txt, reply_markup=get_kb(is_group), parse_mode="Markdown")

async def main():
    global loop
    loop = asyncio.get_running_loop()
    # Запуск сайта
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    add_log("Движок запущен. Жду игроков...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}", flush=True)
