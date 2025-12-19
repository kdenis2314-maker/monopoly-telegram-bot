import asyncio
import logging
import os
import sys
import time
import random
from flask import Flask, render_template_string, request, jsonify
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- БАЗОВЫЕ НАСТРОЙКИ ---
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
TOKEN = os.environ.get("TOKEN")
PORT = int(os.environ.get("PORT", 8080))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "YourBotName")

# --- ГЛОБАЛЬНЫЕ ДАННЫЕ ИГРЫ ---
games = {} 
# Структура: {chat_id: {"status": str, "players": {uid: {"money": 1500, "pos": 0, "name": str}}, "order": [], "turn": 0, "board": {}}}
site_logs = []

def add_log(msg):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    print(f"SYSTEM: {msg}", flush=True)
    if len(site_logs) > 50: site_logs.pop(0)

# --- ДИЗАЙН САЙТА (ADMIN DASHBOARD) ---
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monopoly Control Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background: radial-gradient(circle at top left, #1a1c2c, #4a192c); min-height: 100vh; color: white; font-family: 'Inter', sans-serif; }
        .glass { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; }
        .log-line { border-left: 2px solid #ec4899; padding-left: 10px; margin-bottom: 5px; font-family: monospace; }
        @keyframes pulse-green { 0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); } 100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); } }
        .status-pulse { animation: pulse-green 2s infinite; }
    </style>
</head>
<body class="p-4 md:p-10">
    <div class="max-w-6xl mx-auto">
        <header class="flex justify-between items-center mb-10 glass p-6">
            <div>
                <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-pink-500 to-violet-500">🏦 Monopoly Engine v2.0</h1>
                <p class="text-gray-400">Протокол управления игровыми серверами</p>
            </div>
            <div class="flex items-center gap-3">
                <div class="h-3 w-3 bg-green-500 rounded-full status-pulse"></div>
                <span class="font-bold text-green-400">ONLINE</span>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="glass p-6 col-span-1">
                <h3 class="text-xl mb-4 text-pink-400 font-semibold"><i class="fas fa-chart-line mr-2"></i> Статистика</h3>
                <div class="space-y-4">
                    <div class="flex justify-between border-b border-white/10 pb-2"><span>Активных игр:</span><span class="text-white font-mono">{{ games_count }}</span></div>
                    <div class="flex justify-between border-b border-white/10 pb-2"><span>Uptime:</span><span class="text-white font-mono">{{ uptime }}m</span></div>
                    <div class="flex justify-between border-b border-white/10 pb-2"><span>Версия ядра:</span><span class="text-white font-mono">3.8.2-stable</span></div>
                </div>
                
                <div class="mt-8">
                    <h3 class="text-xl mb-4 text-violet-400 font-semibold"><i class="fas fa-tools mr-2"></i> Команды</h3>
                    <button onclick="location.reload()" class="w-full bg-violet-600 hover:bg-violet-700 p-3 rounded-lg transition mb-2 font-bold">ОБНОВИТЬ ДАННЫЕ</button>
                    <button class="w-full border border-pink-500/50 hover:bg-pink-500/10 p-3 rounded-lg transition font-bold text-pink-500">ПЕРЕЗАГРУЗИТЬ БОТА</button>
                </div>
            </div>

            <div class="glass p-6 col-span-2 flex flex-col h-[500px]">
                <h3 class="text-xl mb-4 text-blue-400 font-semibold"><i class="fas fa-terminal mr-2"></i> Консоль событий</h3>
                <div class="bg-black/40 rounded-xl p-4 flex-grow overflow-y-auto custom-scrollbar">
                    {% for l in logs %}
                        <div class="log-line text-sm text-gray-300">{{ l }}</div>
                    {% endfor %}
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
start_time = time.time()

# КЛАВИАТУРЫ
def get_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏢 Добавить в группу", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
    builder.row(InlineKeyboardButton(text="📖 Правила игры", callback_data="rules"),
                InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="dev"))
    builder.row(InlineKeyboardButton(text="🚀 Обновить статус", callback_data="refresh"))
    return builder.as_markup()

# ОБРАБОТЧИКИ
@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    if m.chat.type == 'private':
        add_log(f"User {m.from_user.id} accessed Home")
        msg = (
            f"👑 *Добро пожаловать в элитарный клуб, {m.from_user.first_name}!*\n\n"
            "Я — самый совершенный бот для игры в **Монополию**.\n\n"
            "📍 *Мои возможности:*\n"
            "• Полная автоматизация банковских операций\n"
            "• Поддержка до 6 игроков одновременно\n"
            "• Система прокачки предприятий\n\n"
            "❗ *Важно:* Я работаю только в группах. Добавь меня и начни игру командой /monopoly"
        )
        await m.answer(msg, reply_markup=get_main_kb(), parse_mode="Markdown")
    else:
        await m.answer("👋 Группа распознана! Для старта введите /monopoly")

@dp.callback_query(F.data == "dev")
async def dev_info(call: types.CallbackQuery):
    await call.message.edit_text("💻 *Разработчик:* @YourHandle\n*Версия:* Stable 2.0\n*Стек:* Aiogram 3.x + Flask", 
                               reply_markup=get_main_kb(), parse_mode="Markdown")

@dp.message(Command("monopoly"))
async def start_monopoly(m: types.Message):
    if m.chat.type == 'private':
        return await m.answer("❌ *Ошибка:* В монополию играют компанией! Запустите меня в группе.", parse_mode="Markdown")
    
    cid = m.chat.id
    if cid in games:
        return await m.answer("⚠️ Игра уже запущена!")

    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"money": 1500, "pos": 0, "name": m.from_user.first_name}},
        "order": [m.from_user.id],
        "turn": 0
    }
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Вступить ✅", callback_data="join"),
           InlineKeyboardButton(text="Начать 🎲", callback_data="go"))
    
    await m.answer(f"🏦 *НОВАЯ ПАРТИЯ!*\n\nУчастники: 1/6\nОжидаем игроков...", 
                  reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "join")
async def join_logic(call: types.CallbackQuery):
    cid = call.message.chat.id
    uid = call.from_user.id
    
    if cid not in games: return
    if uid in games[cid]["players"]:
        return await call.answer("Вы уже в списке!", show_alert=True)
    if len(games[cid]["players"]) >= 6:
        return await call.answer("Группа заполнена!", show_alert=True)

    games[cid]["players"][uid] = {"money": 1500, "pos": 0, "name": call.from_user.first_name}
    games[cid]["order"].append(uid)
    
    names = ", ".join([p["name"] for p in games[cid]["players"].values()])
    await call.message.edit_text(f"🏦 *НОВАЯ ПАРТИЯ!*\n\nУчастники: {names}\nВсего: {len(games[cid]['players'])}/6", 
                               reply_markup=call.message.reply_markup, parse_mode="Markdown")

@dp.callback_query(F.data == "go")
async def start_match(call: types.CallbackQuery):
    cid = call.message.chat.id
    if len(games[cid]["players"]) < 2:
        return await call.answer("Нужно минимум 2 игрока!", show_alert=True)
    
    games[cid]["status"] = "playing"
    current_uid = games[cid]["order"][0]
    name = games[cid]["players"][current_uid]["name"]
    
    await call.message.answer(f"🎲 *ИГРА НАЧАЛАСЬ!*\n\nПервым ходит: *{name}*\nИспользуйте кнопку ниже, чтобы бросить кубики.", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

def get_game_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎲 Бросить кубики", callback_data="roll"))
    kb.row(InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
           InlineKeyboardButton(text="🏠 Мои активы", callback_data="assets"))
    return kb.as_markup()

@dp.callback_query(F.data == "roll")
async def roll_dice(call: types.CallbackQuery):
    cid = call.message.chat.id
    uid = call.from_user.id
    
    game = games.get(cid)
    if not game or game["order"][game["turn"]] != uid:
        return await call.answer("Сейчас не ваш ход!", show_alert=True)
    
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2
    game["players"][uid]["pos"] = (game["players"][uid]["pos"] + steps) % 28
    
    # Смена хода
    game["turn"] = (game["turn"] + 1) % len(game["order"])
    next_uid = game["order"][game["turn"]]
    next_name = game["players"][next_uid]["name"]
    
    await call.message.answer(f"🎲 *{call.from_user.first_name}* выбросил {d1}+{d2} = *{steps}*\nПереход на клетку: {game['players'][uid]['pos']}\n\nСледующий ход: *{next_name}*", 
                             reply_markup=get_game_kb(), parse_mode="Markdown")

# --- ЗАПУСК ---
async def main():
    add_log("Starting Monopoly Core...")
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        add_log(f"CRITICAL: {e}")
