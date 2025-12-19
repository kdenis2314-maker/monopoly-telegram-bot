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
# Данные из твоих настроек
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
BOT_USERNAME = "Monopolysigma_bot"
ADMIN_USER = "@Whylovely05"

# Принудительно используем 8081 для Render
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
    """Добавляет лог и выводит его в консоль Render"""
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    print(f"RENDER_LOG: {entry}", flush=True) 
    if len(site_logs) > 50: site_logs.pop(0)

# --- КРАСИВАЯ АДМИН-ПАНЕЛЬ (FLASK) ---
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Monopoly Sigma Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #020617; color: #f8fafc; font-family: ui-monospace, monospace; }
        .glass { background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1); }
    </style>
</head>
<body class="p-6 md:p-12">
    <div class="max-w-4xl mx-auto">
        <div class="flex justify-between items-center mb-10">
            <h1 class="text-3xl font-bold tracking-tight text-blue-500 underline decoration-blue-800">MONOPOLY SIGMA</h1>
            <div class="text-right text-xs text-slate-500 uppercase tracking-widest">System Live | Port {{ port }}</div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="glass p-5 rounded-2xl border-l-4 border-blue-500">
                <p class="text-slate-400 text-[10px] uppercase font-bold">Uptime</p>
                <p class="text-2xl font-bold">{{ uptime }}m</p>
            </div>
            <div class="glass p-5 rounded-2xl border-l-4 border-purple-500">
                <p class="text-slate-400 text-[10px] uppercase font-bold">Active Games</p>
                <p class="text-2xl font-bold text-blue-400">{{ games_count }}</p>
            </div>
            <div class="glass p-5 rounded-2xl border-l-4 border-emerald-500">
                <p class="text-slate-400 text-[10px] uppercase font-bold">RAM Usage</p>
                <p class="text-2xl font-bold text-emerald-400">{{ ram }}%</p>
            </div>
        </div>

        <div class="glass rounded-2xl overflow-hidden border border-slate-700">
            <div class="bg-slate-800/80 px-4 py-2 text-[10px] font-bold text-slate-400 border-b border-white/5">CORE_STREAM_LOGS</div>
            <div class="p-4 h-96 overflow-y-auto space-y-2 text-sm font-mono scrollbar-hide">
                {% for l in logs %}
                    <div class="flex gap-3 border-b border-white/5 pb-1">
                        <span class="text-blue-500/50">#</span>
                        <span class="text-slate-300">{{ l }}</span>
                    </div>
                {% endfor %}
            </div>
        </div>
        <p class="mt-4 text-[10px] text-slate-600 text-center uppercase tracking-widest italic">Created for @Whylovely05</p>
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
        ram=psutil.virtual_memory().percent,
        port=PORT
    )

# --- МЕХАНИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_game_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎲 Бросить кубики", callback_data="roll"))
    return kb.as_markup()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    add_log(f"User {m.from_user.id} accessed bot")
    await m.answer(f"🏢 **Привет, {m.from_user.first_name}!**\n\nЯ — Monopoly Sigma. Чтобы начать игру, добавь меня в группу и напиши /monopoly.", parse_mode="Markdown")

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
    
    add_log(f"Lobby created in chat {cid}")
    await m.answer(f"🏢 **НОВАЯ ИГРА!**\n\n**Организатор:** {m.from_user.first_name}\n**Бюджет:** 15,000$\n\nЖдем участников...", 
                  reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "join_game")
async def join_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    if cid not in games: return
    if uid in games[cid]["players"]: return await call.answer("Вы уже в списке участников!")
    
    games[cid]["players"][uid] = {"name": call.from_user.first_name, "pos": 0, "money": 15000}
    games[cid]["order"].append(uid)
    
    names = "\n👤 ".join([p["name"] for p in games[cid]["players"].values()])
    await call.message.edit_text(f"🏢 **НОВАЯ ИГРА!**\n\n**Участники:**\n👤 {names}\n\nВсего: {len(games[cid]['players'])}/6", 
                               reply_markup=call.message.reply_markup, parse_mode="Markdown")

@dp.callback_query(F.data == "start_match")
async def start_match_callback(call: types.CallbackQuery):
    cid = call.message.chat.id
    if len(games[cid]["players"]) < 2:
        return await call.answer("Нужно минимум 2 игрока!", show_alert=True)
    
    games[cid]["status"] = "playing"
    first_player = games[cid]["players"][games[cid]["order"][0]]["name"]
    add_log(f"Match started in {cid}")
    await call.message.answer(f"🚀 **ИГРА НАЧАЛАСЬ!**\n\nПервым ходит: **{first_player}**", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "roll")
async def roll_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    game = games.get(cid)
    
    if not game or game["status"] != "playing": return
    if game["order"][game["turn"]] != uid:
        return await call.answer("⏳ Сейчас ход другого игрока!", show_alert=True)
    
    steps = random.randint(2, 12)
    game["players"][uid]["pos"] = (game["players"][uid]["pos"] + steps) % 20
    
    # Переход хода
    game["turn"] = (game["turn"] + 1) % len(game["order"])
    next_name = game["players"][game["order"][game["turn"]]]["name"]
    
    add_log(f"Game {cid}: {call.from_user.first_name} rolled {steps}")
    await call.message.answer(f"🎲 **{call.from_user.first_name}** выкинул **{steps}**\n📍 Новая позиция: {game['players'][uid]['pos']}\n\n➡️ Следующий ход: **{next_name}**", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

# --- ЗАПУСК ---
async def main():
    add_log(f"Initializing Monopoly Engine on port {PORT}...")
    
    # ВАЖНО: Привязка к 0.0.0.0 обязательна для Render
    def run_flask():
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

    Thread(target=run_flask, daemon=True).start()
    
    # Очистка старых обновлений для предотвращения конфликтов
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("Bot engine online and polling.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        add_log(f"CRITICAL ERROR: {e}")
    
