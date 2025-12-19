import asyncio, os, random
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- 1. НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 10000)) # Render использует порт 10000

# --- 2. КАРТА И ДАННЫЕ ---
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "icon": "🚩"},
    {"name": "🏘️ Улица Мира", "price": 100, "icon": "🏘️"},
    {"name": "🎲 ШАНС", "price": 0, "icon": "❓"},
    {"name": "🏢 Пр-т Ленина", "price": 150, "icon": "🏢"},
    {"name": "🛒 Магазин", "price": 200, "icon": "🛒"},
    {"name": "👮 Тюрьма", "price": 0, "icon": "👮"},
    {"name": "🏨 Отель 'Гранд'", "price": 300, "icon": "🏨"},
    {"name": "💎 Алмазный Фонд", "price": 400, "icon": "💎"}
]

players = {}
lobby_players = []
game_active = False

# --- 3. ВЕБ-САЙТ (FLASK) ---
app = Flask(__name__)

# Красивый HTML-шаблон для твоего сайта
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Monopoly Control Panel</title>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Arial', sans-serif; background: #0f0f0f; color: white; text-align: center; padding: 50px; }
        .container { background: #1a1a1a; padding: 30px; border-radius: 20px; box-shadow: 0 0 20px #4CAF50; display: inline-block; }
        h1 { color: #4CAF50; }
        .stat { font-size: 24px; margin: 20px 0; }
        .status { color: #4CAF50; font-weight: bold; }
        .footer { color: #666; margin-top: 30px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎲 Monopoly Online Bot</h1>
        <p>Панель управления состоянием игры</p>
        <div class="stat">Игроков онлайн: <span style="color:white">{{ count }}</span></div>
        <div class="stat">Статус сервера: <span class="status">РАБОТАЕТ ✅</span></div>
        <hr border="0" height="1px" background="#333">
        <p>Разработчик: @Whylovely05</p>
    </div>
    <div class="footer">Powered by Render & Aiogram 3.x</div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE, count=len(players))

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- 4. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

# Функция для кнопок в чате
def get_game_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить кубик", callback_query_data="roll")],
        [InlineKeyboardButton(text="💰 Баланс", callback_query_data="bal"), InlineKeyboardButton(text="🏆 Топ", callback_query_data="top")],
        [InlineKeyboardButton(text="🏃 Выйти", callback_query_data="exit_confirm")]
    ])

@dp.message(Command("monopoly"))
async def start_game(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Начать сбор", callback_query_data="lobby_start")]])
    await m.answer("🏨 **ДОБРО ПОЖАЛОВАТЬ В МОНОПОЛИЮ!**\nНажмите кнопку, чтобы открыть лобби.", reply_markup=kb)

@dp.callback_query(F.data == "lobby_start")
async def lobby_start(call: CallbackQuery):
    global lobby_players, game_active
    lobby_players, game_active = [], False
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Вступить", callback_query_data="join")]])
    await call.message.edit_text("📢 **СБОР ИГРОКОВ**\nЖдем минимум 2-х человек...", reply_markup=kb)

@dp.callback_query(F.data == "join")
async def join(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in lobby_players:
        lobby_players.append(uid)
        players[uid] = {"balance": 1500, "pos": 0, "name": call.from_user.first_name, "owns": []}
        
    kb = [[InlineKeyboardButton(text="✅ Вступить", callback_query_data="join")]]
    if len(lobby_players) >= 2:
        kb.append([InlineKeyboardButton(text="🏁 НАЧАТЬ ИГРУ", callback_query_data="match_start")])
    
    await call.message.edit_text(f"👥 **В лобби:** {len(lobby_players)} чел.\nНужно 2 игрока для старта.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "match_start")
async def match_start(call: CallbackQuery):
    global game_active
    game_active = True
    await call.message.answer("🎉 **ИГРА НАЧАЛАСЬ!**\nИспользуйте кнопки под сообщениями.", reply_markup=get_game_kb())
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
    
    res = f"🎲 **{p['name']}** выкинул {steps}\n📍 Клетка: {cell['icon']} {cell['name']}"
    # Упрощенная логика баланса
    if cell['price'] > 0:
        p['balance'] -= cell['price']
        res += f"\n💳 Списано за покупку/аренду: {cell['price']}$"

    await call.message.answer(res, reply_markup=get_game_kb())
    await call.answer()

# --- 5. ЗАПУСК ---
async def main():
    # Запускаем сайт в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Сервер запущен!")
    asyncio.run(main())
    
