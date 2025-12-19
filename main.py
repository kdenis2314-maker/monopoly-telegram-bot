import asyncio
import logging
import os
import sys
import time
import random
import psutil
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

# --- КОНФИГУРАЦИЯ ---
# Используем ваш токен и данные из предоставленных файлов
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
BOT_USERNAME = "Monopolysigma_bot"
ADMIN_USER = "@Whylovely05"
# Принудительно ставим 8081, если в Render не задана переменная PORT
PORT = int(os.environ.get("PORT", 8081))

# Настройка логирования для вывода в консоль Render
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

games = {} 
site_logs = []
boot_time = time.time()

def add_log(msg):
    """Функция логирования с немедленным выводом (flush)"""
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    print(f"RENDER_LOG: {entry}", flush=True)
    if len(site_logs) > 50: site_logs.pop(0)

# --- АДМИН-ПАНЕЛЬ (FLASK) ---
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Monopoly Sigma | Admin</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #050505; color: #e2e8f0; font-family: monospace; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
    </style>
</head>
<body class="p-10">
    <div class="max-w-5xl mx-auto">
        <h1 class="text-3xl font-bold mb-8">MONOPOLY <span class="text-blue-500">SIGMA</span> ADM</h1>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="glass p-5 rounded-xl">
                <p class="text-gray-400 text-xs uppercase">Uptime</p>
                <p class="text-2xl font-bold">{{ uptime }}m</p>
            </div>
            <div class="glass p-5 rounded-xl">
                <p class="text-gray-400 text-xs uppercase">Games</p>
                <p class="text-2xl font-bold text-blue-400">{{ games_count }}</p>
            </div>
            <div class="glass p-5 rounded-xl">
                <p class="text-gray-400 text-xs uppercase">CPU / RAM</p>
                <p class="text-2xl font-bold text-green-400">{{ cpu }}% / {{ ram }}%</p>
            </div>
        </div>

        <div class="glass rounded-xl overflow-hidden">
            <div class="bg-white/5 p-3 text-xs font-bold border-b border-white/10">SYSTEM LOGS (PORT {{ port }})</div>
            <div class="p-4 h-80 overflow-y-auto space-y-1 text-sm">
                {% for l in logs %}
                    <div class="text-blue-300"><span class="opacity-50">></span> {{ l }}</div>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    uptime = int((time.time() - boot_time) / 60)
    return render_template_string(
        DASHBOARD_HTML, 
        logs=site_logs[::-1], 
        uptime=uptime, 
        games_count=len(games),
        cpu=psutil.cpu_percent(),
        ram=psutil.virtual_memory().percent,
        port=PORT
    )

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_game_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎲 Бросить кубики", callback_data="roll"))
    return kb.as_markup()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    add_log(f"User {m.from_user.id} used /start")
    await m.answer(f"Привет, {m.from_user.first_name}! 🏦\nЯ Monopoly Sigma. Для игры добавь меня в группу и введи /monopoly.")

@dp.message(Command("monopoly"), F.chat.type.in_({"group", "supergroup"}))
async def start_game(m: types.Message):
    cid = m.chat.id
    if cid in games:
        return await m.answer("⚠️ Игра в этом чате уже запущена!")

    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"name": m.from_user.first_name, "pos": 0, "money": 15000}},
        "order": [m.from_user.id],
        "turn": 0
    }
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Вступить ✅", callback_data="join_game"),
           InlineKeyboardButton(text="Начать 🎲", callback_data="start_match"))
    
    add_log(f"Lobby created in chat {cid}")
    await m.answer(f"🏦 **НОВАЯ ИГРА!**\n\nИгроки: {m.from_user.first_name}\nСтартовый капитал: 15,000$", 
                  reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "join_game")
async def join_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    if cid not in games: return
    if uid in games[cid]["players"]: return await call.answer("Вы уже участвуете!")
    
    games[cid]["players"][uid] = {"name": call.from_user.first_name, "pos": 0, "money": 15000}
    games[cid]["order"].append(uid)
    
    names = ", ".join([p["name"] for p in games[cid]["players"].values()])
    await call.message.edit_text(f"🏦 **НОВАЯ ИГРА!**\n\nИгроки: {names}\nВсего: {len(games[cid]['players'])}/6", 
                               reply_markup=call.message.reply_markup, parse_mode="Markdown")

@dp.callback_query(F.data == "start_match")
async def start_match_callback(call: types.CallbackQuery):
    cid = call.message.chat.id
    if len(games[cid]["players"]) < 2:
        return await call.answer("Нужно минимум 2 игрока!", show_alert=True)
    
    games[cid]["status"] = "playing"
    first_player = games[cid]["players"][games[cid]["order"][0]]["name"]
    add_log(f"Game started in {cid}")
    await call.message.answer(f"🚀 **Игра началась!**\nПервым ходит: *{first_player}*", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "roll")
async def roll_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    game = games.get(cid)
    
    if not game or game["status"] != "playing": return
    if game["order"][game["turn"]] != uid:
        return await call.answer("⏳ Сейчас не ваш ход!", show_alert=True)
    
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2
    game["players"][uid]["pos"] = (game["players"][uid]["pos"] + steps) % 20 # Упрощенная доска на 20 клеток
    
    # Переход хода
    game["turn"] = (game["turn"] + 1) % len(game["order"])
    next_name = game["players"][game["order"][game["turn"]]]["name"]
    
    add_log(f"Move in {cid}: {call.from_user.first_name} rolled {steps}")
    await call.message.answer(f"🎲 *{call.from_user.first_name}* выкинул {d1}+{d2} = **{steps}**\n📍 Позиция: {game['players'][uid]['pos']}\n\nСледующий: *{next_name}*", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

# --- ЗАПУСК ---
async def main():
    add_log(f"🛠 Запуск системы на порту {PORT}...")
    
    # Flask запускается на 0.0.0.0, чтобы Render видел порт
    def run_flask():
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

    Thread(target=run_flask, daemon=True).start()
    
    # Очистка старых обновлений для избежания конфликтов
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("🤖 Бот активен. Ожидание сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        add_log("🛑 Выключение...")
    
