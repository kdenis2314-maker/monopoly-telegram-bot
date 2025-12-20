import asyncio
import os
import random
import logging
from flask import Flask, render_template_string
from threading import Thread
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramConflictError

# --- 1. ЛОГИ ДЛЯ САЙТА (УПРОЩЕННЫЕ) ---
logs_list = []
def add_log(text):
    time_str = datetime.now().strftime("%H:%M:%S")
    log = f"[{time_str}] {text}"
    logs_list.append(log)
    if len(logs_list) > 15: logs_list.pop(0)
    print(log)

# --- 2. НАСТРОЙКИ ---
TOKEN = "8265158957:AAF47AzlevRoyn7CLOMHkB7HsxQu5MUdpSg"
PORT = int(os.environ.get("PORT", 10000))

players = {}
lobby_players = []
game_active = False

BOARD = [
    {"name": "🚩 СТАРТ", "icon": "🚩"},
    {"name": "🏘️ Улица Мира", "icon": "🏘️"},
    {"name": "🏢 Пр-т Ленина", "icon": "🏢"},
    {"name": "🛒 Магазин", "icon": "🛒"},
    {"name": "👮 Тюрьма", "icon": "👮"},
    {"name": "🏨 Отель 'Гранд'", "icon": "🏨"},
    {"name": "🚉 Вокзал", "icon": "🚉"},
    {"name": "💎 Алмазный Фонд", "icon": "💎"}
]

# --- 3. ВЕБ-ИНТЕРФЕЙС ---
app = Flask(__name__)
@app.route('/')
def index():
    return render_template_string("""
    <html><head><meta http-equiv="refresh" content="3"></head>
    <body style="background:#000;color:#0f0;font-family:monospace;padding:20px;">
    <h2>🔗 Monopoly Debug Console</h2>
    <div style="border:1px solid #333;padding:10px;">
    {% for log in logs %}<p style="margin:2px;">{{ log }}</p>{% endfor %}
    </div>
    </body></html>
    """, logs=logs_list[::-1])

# --- 4. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def start_cmd(m: Message):
    add_log(f"📩 Команда /monopoly от {m.from_user.id}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Сбор игроков", callback_query_data="l_start")]])
    await m.answer("🏨 **MONOPOLY ONLINE**\nБот готов!", reply_markup=kb)

@dp.callback_query(F.data == "l_start")
async def l_start(call: CallbackQuery):
    global lobby_players, game_active
    lobby_players, game_active = [], False
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Вступить", callback_query_data="l_join")]])
    await call.message.edit_text("📢 **СБОР ИГРОКОВ**", reply_markup=kb)

@dp.callback_query(F.data == "l_join")
async def l_join(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in lobby_players:
        lobby_players.append(uid)
        players[uid] = {"balance": 1500, "pos": 0, "name": call.from_user.first_name}
    
    kb = [[InlineKeyboardButton(text="✅ Вступить", callback_query_data="l_join")]]
    if len(lobby_players) >= 1:
        kb.append([InlineKeyboardButton(text="🏁 НАЧАТЬ", callback_query_data="g_start")])
    await call.message.edit_text(f"👥 В лобби: {len(lobby_players)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "g_start")
async def g_start(call: CallbackQuery):
    global game_active
    game_active = True
    await call.message.answer("🎉 Поехали!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить кубик", callback_query_data="roll")]
    ]))
    await call.message.delete()

@dp.callback_query(F.data == "roll")
async def roll(call: CallbackQuery):
    p = players.get(call.from_user.id)
    if not p:
        return await call.answer("❌ Ошибка: Вы не в базе данных. Начните заново.", show_alert=True)
    
    steps = random.randint(1, 6)
    p['pos'] = (p['pos'] + steps) % len(BOARD)
    cell = BOARD[p['pos']]
    
    await call.message.answer(f"🎲 **{p['name']}** выкинул {steps}\n📍 Клетка: {cell['name']}", 
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                 [InlineKeyboardButton(text="🎲 Бросить еще", callback_query_data="roll")]
                             ]))
    await call.answer()

# --- 5. ЗАПУСК ---
async def main():
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    add_log("🌐 Веб-сервер запущен")
    
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            add_log("🚀 Поллинг запущен!")
            await dp.start_polling(bot)
        except TelegramConflictError:
            add_log("⚠️ Конфликт! Жду 10 сек...")
            await asyncio.sleep(10)
        except Exception as e:
            add_log(f"⚠️ Ошибка: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
