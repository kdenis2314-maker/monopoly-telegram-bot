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
PORT = 8080 # Убедись, что этот порт не занят другим ботом!

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
games = {} 
site_logs = []
boot_time = time.time()

def add_log(msg):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    if len(site_logs) > 50: site_logs.pop(0)

# --- ФУТУРИСТИЧНАЯ АДМИН-ПАНЕЛЬ ---
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
        .neon-text { text-shadow: 0 0 10px #3b82f6, 0 0 20px #3b82f6; }
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
                    <div class="flex gap-1">
                        <div class="w-2 h-2 rounded-full bg-red-500"></div>
                        <div class="w-2 h-2 rounded-full bg-yellow-500"></div>
                        <div class="w-2 h-2 rounded-full bg-green-500"></div>
                    </div>
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
                <div class="w-24 h-24 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full mb-4 shadow-[0_0_30px_rgba(59,130,246,0.5)] flex items-center justify-center">
                    <span class="text-4xl">🎲</span>
                </div>
                <h3 class="text-xl font-bold mb-1">@{{ bot_user }}</h3>
                <p class="text-slate-400 text-sm mb-6 font-sans">Telegram Bot Interface</p>
                <div class="w-full space-y-3">
                    <div class="h-1 bg-slate-700 rounded-full overflow-hidden">
                        <div class="h-full bg-blue-500 w-3/4"></div>
                    </div>
                    <p class="text-[10px] text-slate-500">DATABASE INTEGRITY: 100%</p>
                </div>
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

def get_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💎 Создать Лобби", callback_data="create_game"))
    builder.row(InlineKeyboardButton(text="👨‍💻 Разработчик", url=f"https://t.me/{ADMIN_USER.replace('@', '')}"))
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    welcome_text = (
        f"👋 Привет, **{m.from_user.first_name}**!\n\n"
        f"🏢 Я — **Monopoly Sigma**, самый продвинутый бот для игры в монополию.\n"
        f"Чтобы начать, добавь меня в группу или создай лобби прямо здесь (но в группе веселее!)"
    )
    await m.answer(welcome_text, reply_markup=get_main_kb(), parse_mode="Markdown")

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: types.Message):
    if m.chat.type == "private":
        return await m.answer("❌ Игры доступны только в **групповых чатах**!", parse_mode="Markdown")
    
    cid = m.chat.id
    if cid in games:
        return await m.answer("⚠️ В этом чате уже запущена активная сессия!")

    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"name": m.from_user.first_name, "pos": 0, "balance": 15000, "assets": []}},
        "order": [m.from_user.id],
        "turn": 0
    }
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Вступить ✅", callback_data="join_game"))
    builder.add(InlineKeyboardButton(text="Старт ⚡", callback_data="start_match"))
    
    add_log(f"New lobby in chat {cid}")
    await m.answer(f"🏢 **МОНОПОЛИЯ СИГМА**\n\nСоздатель: {m.from_user.first_name}\nИгроков: 1/6\n\nЖдем остальных...", 
                  reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "join_game")
async def handle_join(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    if cid not in games: return
    if uid in games[cid]["players"]: return await call.answer("Вы уже в игре!", show_alert=True)
    if len(games[cid]["players"]) >= 6: return await call.answer("Лобби заполнено!", show_alert=True)

    games[cid]["players"][uid] = {"name": call.from_user.first_name, "pos": 0, "balance": 15000, "assets": []}
    games[cid]["order"].append(uid)
    
    names = "\n".join([f"👤 {p['name']}" for p in games[cid]["players"].values()])
    await call.message.edit_text(f"🏢 **МОНОПОЛИЯ СИГМА**\n\n**Участники:**\n{names}\n\nСвободных мест: {6 - len(games[cid]['players'])}", 
                               reply_markup=call.message.reply_markup, parse_mode="Markdown")

@dp.callback_query(F.data == "start_match")
async def handle_start(call: types.CallbackQuery):
    cid = call.message.chat.id
    if len(games[cid]["players"]) < 2:
        return await call.answer("Нужно минимум 2 игрока!", show_alert=True)
    
    games[cid]["status"] = "playing"
    curr_uid = games[cid]["order"][0]
    curr_name = games[cid]["players"][curr_uid]["name"]
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🎲 Бросить кубики", callback_data="roll_dice"))
    
    await call.message.answer(f"🚀 **ИГРА НАЧАЛАСЬ!**\n\nПервый ход делает: **{curr_name}**\nСтартовый капитал: 15,000$", 
                             reply_markup=builder.as_markup(), parse_mode="Markdown")
    await call.message.delete()

@dp.callback_query(F.data == "roll_dice")
async def handle_roll(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    game = games.get(cid)
    
    if not game or game["status"] != "playing": return
    if game["order"][game["turn"]] != uid:
        return await call.answer("⏳ Сейчас не твой ход!", show_alert=True)
    
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2
    
    # Логика перемещения
    p_data = game["players"][uid]
    p_data["pos"] = (p_data["pos"] + total) % 20
    
    # Случайное событие (Налог)
    tax_msg = ""
    if random.random() < 0.2:
        tax = random.choice([500, 1000, 1500])
        p_data["balance"] -= tax
        tax_msg = f"\n⚠️ **Налог:** Вы заплатили {tax}$ гос-ву!"

    # Переход хода
    game["turn"] = (game["turn"] + 1) % len(game["order"])
    next_uid = game["order"][game["turn"]]
    next_name = game["players"][next_uid]["name"]
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🎲 Бросить кубики", callback_data="roll_dice"))

    res = (
        f"🎲 **{p_data['name']}** выкидывает {d1} + {d2} = **{total}**\n"
        f"📍 Позиция: {p_data['pos']}/20\n"
        f"💰 Баланс: {p_data['balance']}${tax_msg}\n\n"
        f"➡️ Очередь игрока: **{next_name}**"
    )
    
    await call.message.answer(res, reply_markup=builder.as_markup(), parse_mode="Markdown")
    add_log(f"Game {cid}: {p_data['name']} rolled {total}")

# --- ЗАПУСК ---
async def main():
    add_log("System initializing...")
    # Запуск Flask в отдельном потоке
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    
    add_log("Bot engine started. Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        add_log("System shutdown.")
    
