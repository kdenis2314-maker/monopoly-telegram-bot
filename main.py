import asyncio
import os
import random
import logging
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- 1. НАСТРОЙКИ И ЛОГИРОВАНИЕ ---
# Включаем логи, чтобы видеть, доходят ли сообщения до кода
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 10000))

# --- 2. КАРТА И ДАННЫЕ ---
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "icon": "🚩"},
    {"name": "🏘️ Улица Мира", "price": 100, "icon": "🏘️"},
    {"name": "🎲 ШАНС", "price": 0, "icon": "❓"},
    {"name": "🏢 Пр-т Ленина", "price": 150, "icon": "🏢"},
    {"name": "🛒 Магазин", "price": 200, "icon": "🛒"},
    {"name": "👮 Тюрьма", "price": 0, "icon": "👮"},
    {"name": "🎲 ШАНС", "price": 0, "icon": "❓"},
    {"name": "🏨 Отель 'Гранд'", "price": 300, "icon": "🏨"},
    {"name": "🌳 Парк Культуры", "price": 120, "icon": "🌳"},
    {"name": "🚉 Вокзал", "price": 250, "icon": "🚉"},
    {"name": "💎 Алмазный Фонд", "price": 400, "icon": "💎"},
    {"name": "🎡 Цирк", "price": 140, "icon": "🎡"}
]

CHANCES = [
    {"text": "🎰 Выигрыш в казино!", "reward": 500},
    {"text": "📉 Падение акций!", "reward": -200},
    {"text": "🎁 Наследство!", "reward": 300},
    {"text": "🚓 Штраф!", "reward": -100}
]

players = {}
lobby_players = []
game_active = False

# --- 3. ВЕБ-САЙТ (FLASK) ---
app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Monopoly Admin</title>
    <style>
        body { background: #121212; color: white; font-family: sans-serif; text-align: center; padding-top: 50px; }
        .box { display: inline-block; padding: 20px; border: 2px solid #4CAF50; border-radius: 15px; background: #1e1e1e; }
        h1 { color: #4CAF50; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🎮 Monopoly Bot Panel</h1>
        <p>Игроков в базе: <b>{{ count }}</b></p>
        <p>Статус: <span style="color: #4CAF50;">ONLINE</span></p>
        <p>Разработчик: @Whylovely05</p>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE, count=len(players))

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- 4. КЛАВИАТУРЫ ---
def get_game_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить кубик", callback_query_data="roll")],
        [InlineKeyboardButton(text="💰 Баланс", callback_query_data="bal"), InlineKeyboardButton(text="🏆 Топ", callback_query_data="top")],
        [InlineKeyboardButton(text="🤝 Обмен", callback_query_data="trade_menu")],
        [InlineKeyboardButton(text="🏃 Выход", callback_query_data="exit_ask")]
    ])

# --- 5. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: Message):
    logger.info(f"Команда /monopoly от {m.from_user.id}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Начать сбор", callback_query_data="l_start")]])
    await m.answer("🏨 **MONOPOLY ONLINE**\nНажмите кнопку ниже, чтобы собрать игроков!", reply_markup=kb)

@dp.callback_query(F.data == "l_start")
async def l_start(call: CallbackQuery):
    global lobby_players, game_active
    lobby_players, game_active = [], False
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Вступить", callback_query_data="l_join")]])
    await call.message.edit_text("📢 **СБОР ИГРОКОВ**\nЖдем участников (минимум 2)...", reply_markup=kb)

@dp.callback_query(F.data == "l_join")
async def l_join(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in lobby_players:
        lobby_players.append(uid)
        players[uid] = {"balance": 1500, "pos": 0, "name": call.from_user.first_name, "owns": []}
    
    kb = [[InlineKeyboardButton(text="✅ Вступить", callback_query_data="l_join")]]
    if len(lobby_players) >= 2:
        kb.append([InlineKeyboardButton(text="🏁 НАЧАТЬ ИГРУ", callback_query_data="g_start")])
    
    await call.message.edit_text(f"👥 **Игроков в лобби:** {len(lobby_players)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "g_start")
async def g_start(call: CallbackQuery):
    global game_active
    game_active = True
    await call.message.answer("🎉 **ИГРА НАЧАЛАСЬ!**", reply_markup=get_game_kb())
    await call.message.delete()

@dp.callback_query(F.data == "roll")
async def roll(call: CallbackQuery):
    uid = call.from_user.id
    if not game_active or uid not in lobby_players:
        return await call.answer("Вы не в игре!", show_alert=True)

    steps = random.randint(1, 6)
    p = players[uid]
    p['pos'] = (p['pos'] + steps) % len(BOARD)
    cell = BOARD[p['pos']]
    
    msg = f"🎲 **{p['name']}** выкинул {steps}\n📍 Клетка: {cell['icon']} {cell['name']}\n"

    if "ШАНС" in cell['name']:
        ev = random.choice(CHANCES)
        p['balance'] += ev['reward']
        msg += f"\n✨ **ШАНС:** {ev['text']} (`{ev['reward']}$`)"
    elif cell['price'] > 0:
        p['balance'] -= cell['price']
        msg += f"\n💳 Списано: {cell['price']}$"

    await call.message.answer(msg, reply_markup=get_game_kb())
    await call.answer()

@dp.callback_query(F.data == "bal")
async def cb_bal(call: CallbackQuery):
    p = players.get(call.from_user.id)
    if p: await call.answer(f"💰 Ваш баланс: {p['balance']}$", show_alert=True)

@dp.callback_query(F.data == "exit_ask")
async def exit_ask(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да", callback_query_data="exit_yes"),
        InlineKeyboardButton(text="❌ Нет", callback_query_data="exit_no")
    ]])
    await call.message.edit_text("Вы действительно хотите выйти?", reply_markup=kb)

@dp.callback_query(F.data == "exit_yes")
async def exit_yes(call: CallbackQuery):
    uid = call.from_user.id
    if uid in lobby_players:
        lobby_players.remove(uid)
        players.pop(uid, None)
    await call.message.edit_text(f"🏃 {call.from_user.first_name} покинул игру.")

@dp.callback_query(F.data == "exit_no")
async def exit_no(call: CallbackQuery):
    await call.message.edit_text("Игра продолжается!", reply_markup=get_game_kb())

# --- 6. ЗАПУСК ---
async def main():
    # Запуск веб-панели в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
    
    # Удаляем вебхуки (критично для исправления "молчания")
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Бот запущен. Ожидание сообщений...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Работа завершена")
