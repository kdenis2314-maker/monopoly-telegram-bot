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
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
BOT_USERNAME = "Monopolysigma_bot"
ADMIN_USER = "@Whylovely05"
PORT = int(os.environ.get("PORT", 8080))

# Настройка логирования специально для Render
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Глобальные переменные данных
games = {} 
site_logs = []
boot_time = time.time()

def add_log(msg):
    """Функция записи логов, которая гарантированно выводит их в консоль Render"""
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    # Печатаем с flush=True, чтобы Render сразу подхватывал строку
    print(f"RENDER_LOG: {entry}", flush=True)
    if len(site_logs) > 50: site_logs.pop(0)

# --- ФУТУРИСТИЧНАЯ АДМИН-ПАНЕЛЬ (FLASK) ---
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monopoly Sigma | Control Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { background-color: #050505; font-family: 'JetBrains Mono', monospace; color: #e2e8f0; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.1); }
        .log-container::-webkit-scrollbar { width: 4px; }
        .log-container::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 10px; }
    </style>
</head>
<body class="p-4 md:p-10">
    <div class="max-w-6xl mx-auto">
        <div class="flex justify-between items-center mb-10">
            <div>
                <h1 class="text-4xl font-extrabold text-white tracking-tighter">MONOPOLY<span class="text-blue-500">SIGMA</span></h1>
                <p class="text-slate-500 text-sm">Created by {{ creator }}</p>
            </div>
            <div class="text-right">
                <span class="px-4 py-1 rounded-full bg-green-500/20 text-green-400 border border-green-500/50 text-xs animate-pulse">● SYSTEM ONLINE</span>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="glass p-6 rounded-2xl">
                <p class="text-slate-400 text-xs uppercase mb-1">Uptime</p>
                <p class="text-2xl font-bold">{{ uptime }}m</p>
            </div>
            <div class="glass p-6 rounded-2xl">
                <p class="text-slate-400 text-xs uppercase mb-1">Active Games</p>
                <p class="text-2xl font-bold text-blue-400">{{ games_count }}</p>
            </div>
            <div class="glass p-6 rounded-2xl">
                <p class="text-slate-400 text-xs uppercase mb-1">CPU Load</p>
                <p class="text-2xl font-bold text-purple-400">{{ cpu }}%</p>
            </div>
            <div class="glass p-6 rounded-2xl">
                <p class="text-slate-400 text-xs uppercase mb-1">Memory</p>
                <p class="text-2xl font-bold text-orange-400">{{ ram }}%</p>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 glass rounded-2xl overflow-hidden flex flex-col">
                <div class="bg-slate-800/50 px-4 py-2 border-b border-white/5 flex items-center justify-between">
                    <span class="text-xs font-bold text-slate-400">CORE_LOGS_STREAM</span>
                </div>
                <div class="p-4 h-[400px] overflow-y-auto log-container font-mono text-sm space-y-1">
                    {% for l in logs %}
                        <div class="border-l-2 border-blue-500/30 pl-3 py-1 bg-white/5 rounded-r">
                            <span class="text-blue-400 opacity-70">>></span> {{ l }}
                        </div>
                    {% endfor %}
                </div>
            </div>
            <div class="glass p-6 rounded-2xl flex flex-col justify-center items-center text-center">
                <div class="w-24 h-24 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full mb-4 flex items-center justify-center">
                    <span class="text-4xl">🎲</span>
                </div>
                <h3 class="text-xl font-bold mb-1">@{{ bot_user }}</h3>
                <p class="text-slate-400 text-sm mb-6 font-sans">Telegram Bot Interface</p>
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
        bot_user=BOT_USERNAME,
        creator=ADMIN_USER
    )

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_game_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎲 Бросить кубики", callback_data="roll"))
    return kb.as_markup()

@dp.message(Command("start"))
async def global_start(m: types.Message):
    add_log(f"User {m.from_user.id} started bot")
    await m.answer(f"Привет, {m.from_user.first_name}! 🏢 Я бот Монополия Сигма.\n\nЯ работаю в группах. Используй /monopoly в чате с друзьями.")

@dp.message(Command("monopoly"), F.chat.type.in_({"group", "supergroup"}))
async def start_game(m: types.Message):
    cid = m.chat.id
    if cid in games:
        return await m.answer("⚠️ Игра в этом чате уже идет!")

    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"name": m.from_user.first_name, "pos": 0, "money": 15000}},
        "order": [m.from_user.id],
        "turn": 0
    }
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Вступить ✅", callback_data="join_game"),
           InlineKeyboardButton(text="Начать 🎲", callback_data="start_match"))
    
    add_log(f"New game lobby created in {m.chat.title}")
    await m.answer(f"🏦 **НОВАЯ ИГРА!**\n\nИгроки: {m.from_user.first_name}\n\nОжидание участников...", 
                  reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "join_game")
async def join_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    if cid not in games: return
    if uid in games[cid]["players"]: return await call.answer("Вы уже в игре!")
    
    games[cid]["players"][uid] = {"name": call.from_user.first_name, "pos": 0, "money": 15000}
    games[cid]["order"].append(uid)
    
    names = ", ".join([p["name"] for p in games[cid]["players"].values()])
    await call.message.edit_text(f"🏦 **НОВАЯ ИГРА!**\n\nИгроки: {names}\nВсего: {len(games[cid]['players'])}/6", 
                               reply_markup=call.message.reply_markup, parse_mode="Markdown")

@dp.callback_query(F.data == "start_match")
async def start_match_callback(call: types.CallbackQuery):
    cid = call.message.chat.id
    if len(games[cid]["players"]) < 2:
        return await call.answer("Нужно хотя бы 2 игрока!", show_alert=True)
    
    games[cid]["status"] = "playing"
    first_player = games[cid]["players"][games[cid]["order"][0]]["name"]
    add_log(f"Game started in chat {cid}")
    await call.message.answer(f"🎲 **Игра началась!**\nПервым ходит: *{first_player}*", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "roll")
async def roll_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    game = games.get(cid)
    
    if not game or game["status"] != "playing": return
    if game["order"][game["turn"]] != uid:
        return await call.answer("Сейчас не ваш ход!", show_alert=True)
    
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2
    game["players"][uid]["pos"] = (game["players"][uid]["pos"] + steps) % 28
    
    # Переход хода
    game["turn"] = (game["turn"] + 1) % len(game["order"])
    next_name = game["players"][game["order"][game["turn"]]]["name"]
    
    add_log(f"Roll in {cid}: {call.from_user.first_name} rolled {steps}")
    await call.message.answer(f"🎲 *{call.from_user.first_name}* выбросил {d1}+{d2} = **{steps}**\n\nСледующий ход: *{next_name}*", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

# --- ЗАПУСК ---
async def main():
    add_log("🚀 Запуск Monopoly Engine...")
    # Flask в отдельном потоке
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    
    add_log("🤖 Бот начал опрос (Polling)")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        add_log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
