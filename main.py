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
from aiogram.types import InlineKeyboardButton

# --- НАСТРОЙКИ СИСТЕМЫ ---
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
TOKEN = os.environ.get("TOKEN")
PORT = int(os.environ.get("PORT", 8080))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Bot")

# Данные игр и логи
games = {} 
site_logs = []
start_time = time.time()

def add_log(msg):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    print(f"RENDER_LOG: {entry}", flush=True)
    if len(site_logs) > 30: site_logs.pop(0)

# --- АДМИН-ПАНЕЛЬ (FLASK) ---
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Monopoly Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: sans-serif; }
        .terminal { background: #000; color: #22c55e; padding: 15px; border-radius: 8px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 13px; border: 1px solid #1e293b; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-4xl mx-auto">
        <h1 class="text-3xl font-bold mb-6 text-blue-400">🏢 Monopoly Engine Dashboard</h1>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div class="bg-slate-800 p-6 rounded-xl border border-slate-700">
                <h2 class="text-xl mb-2 font-semibold text-slate-300">Статус Системы</h2>
                <p>Uptime: <span class="text-blue-400">{{ uptime }} мин.</span></p>
                <p>Активных игр: <span class="text-blue-400">{{ games_count }}</span></p>
                <p>Статус бота: <span class="text-green-500 font-bold">ONLINE</span></p>
            </div>
            <div class="bg-slate-800 p-6 rounded-xl border border-slate-700">
                <h2 class="text-xl mb-2 font-semibold text-slate-300">Консоль</h2>
                <div class="terminal">
                    {% for l in logs %} <div>{{ l }}</div> {% endfor %}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    uptime = int((time.time() - start_time) / 60)
    return render_template_string(DASHBOARD_HTML, logs=site_logs[::-1], uptime=uptime, games_count=len(games))

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Вспомогательные клавиатуры
def get_start_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🏢 Добавить в группу", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
    return kb.as_markup()

def get_game_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎲 Бросить кубики", callback_data="roll"))
    return kb.as_markup()

# 1. Запрет на использование в ЛС
@dp.message(F.chat.type == "private", Command("monopoly"))
async def private_monopoly(m: types.Message):
    await m.answer("❌ **Ошибка:** В Монополию нельзя играть одному! Добавьте меня в группу с друзьями.", 
                   reply_markup=get_start_kb(), parse_mode="Markdown")

# 2. Приветствие при добавлении в группу
@dp.message(F.new_chat_members)
async def welcome_to_group(m: types.Message):
    for user in m.new_chat_members:
        if user.id == bot.id:
            add_log(f"Added to group: {m.chat.title}")
            await m.answer(f"Привет всем! 🏢 Я готов запустить Монополию в этом чате.\nВведите /monopoly для начала!")

# 3. Старт игры (только в группе)
@dp.message(Command("monopoly"), F.chat.type.in_({"group", "supergroup"}))
async def start_game(m: types.Message):
    cid = m.chat.id
    if cid in games:
        return await m.answer("⚠️ Игра уже идет!")

    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"name": m.from_user.first_name, "pos": 0, "money": 1500}},
        "order": [m.from_user.id],
        "turn": 0
    }
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Вступить ✅", callback_data="join_game"),
           InlineKeyboardButton(text="Начать 🎲", callback_data="start_match"))
    
    await m.answer(f"🏦 **НОВАЯ ИГРА!**\n\nИгроки: {m.from_user.first_name}\n\nОжидание участников...", 
                  reply_markup=kb.as_markup(), parse_mode="Markdown")

# 4. Обработка кнопок
@dp.callback_query(F.data == "join_game")
async def join_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    if cid not in games: return
    if uid in games[cid]["players"]: return await call.answer("Вы уже в игре!")
    
    games[cid]["players"][uid] = {"name": call.from_user.first_name, "pos": 0, "money": 1500}
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
    
    await call.message.answer(f"🎲 *{call.from_user.first_name}* выбросил {d1}+{d2} = **{steps}**\n\nСледующий ход: *{next_name}*", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

# Универсальный /start
@dp.message(Command("start"))
async def global_start(m: types.Message):
    if m.chat.type == "private":
        await m.answer(f"Привет, {m.from_user.first_name}! 🏦 Я бот Монополия.\n\nЯ работаю **только в группах**. Нажмите кнопку ниже, чтобы пригласить меня в чат!", 
                      reply_markup=get_start_kb())
    else:
        await m.answer("Бот готов! Используйте /monopoly для начала.")

# --- ЗАПУСК ---
async def main():
    add_log("Starting Monopoly Engine...")
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        add_log(f"CRITICAL ERROR: {e}")
