import asyncio, os, random
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- 1. НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 10000))
ADMIN_ID = 0  # Сюда твой ID

# --- 2. КАРТА И ДАННЫЕ ---
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "icon": "🚩"},
    {"name": "🏘️ Улица Мира", "price": 100, "icon": "🏘️"},
    {"name": "💸 Налог", "price": 0, "icon": "💸"},
    {"name": "🏢 Пр-т Ленина", "price": 150, "icon": "🏢"},
    {"name": "🛒 Магазин", "price": 200, "icon": "🛒"},
    {"name": "👮 Тюрьма", "price": 0, "icon": "👮"},
    {"name": "🏨 Отель 'Гранд'", "price": 300, "icon": "🏨"},
    {"name": "🌳 Парк Культуры", "price": 120, "icon": "🌳"},
    {"name": "🚉 Вокзал", "price": 250, "icon": "🚉"},
    {"name": "🏛️ Рынок", "price": 180, "icon": "🏛️"},
    {"name": "💎 Алмазный Фонд", "price": 400, "icon": "💎"},
    {"name": "🎡 Цирк", "price": 140, "icon": "🎡"}
]
MAP_SIZE = len(BOARD)

players = {}  # База игроков
game_active = False # Статус: идет ли сама игра
lobby_players = [] # Список ID тех, кто нажал "Вступить" в лобби

# --- 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_visual_board(current_pos):
    line = "".join(["👤" if i == current_pos else "▫️" for i in range(MAP_SIZE)])
    return f"Карта: |{line}|"

# --- 4. КЛАВИАТУРЫ ---
def get_start_menu():
    kb = [
        [InlineKeyboardButton(text="🚀 Начать сбор игроков", callback_query_data="lobby_start")],
        [InlineKeyboardButton(text="📜 Правила", callback_query_data="rules")],
        [InlineKeyboardButton(text="👨‍💻 Разработчик", callback_query_data="dev")],
        [InlineKeyboardButton(text="🛠️ Команды и Помощь", callback_query_data="help_info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_lobby_kb(count):
    kb = [[InlineKeyboardButton(text="✅ Вступить в игру", callback_query_data="join_lobby")]]
    if count >= 2:
        kb.append([InlineKeyboardButton(text="🏁 НАЧАТЬ ИГРУ", callback_query_data="start_match")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_main_kb():
    buttons = [
        [types.KeyboardButton(text="🎲 Бросить кубик")],
        [types.KeyboardButton(text="💰 Баланс"), types.KeyboardButton(text="🏠 Моё имущество")],
        [types.KeyboardButton(text="📍 Где я?"), types.KeyboardButton(text="🏆 Топ")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- 5. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: Message):
    if m.chat.type == "private":
        return await m.answer("⚠️ Добавьте бота в группу для игры!")
    
    text = (
        "🏨 **ДОБРО ПОЖАЛОВАТЬ В MONOPOLY ONLINE**\n\n"
        "Для активации игры выберите пункт меню ниже.\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Бот позволяет играть прямо в чате с друзьями!"
    )
    await m.answer(text, reply_markup=get_start_menu())

@dp.callback_query(F.data == "lobby_start")
async def lobby_start(call: CallbackQuery):
    global lobby_players, game_active
    lobby_players = []
    game_active = False
    await call.message.edit_text(
        "📢 **СБОР ИГРОКОВ ОТКРЫТ!**\n\nНажмите кнопку ниже, чтобы участвовать.\nНужно минимум 2 человека.",
        reply_markup=get_lobby_kb(0)
    )

@dp.callback_query(F.data == "join_lobby")
async def join_lobby(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in lobby_players:
        lobby_players.append(uid)
        # Инициализируем данные игрока
        players[uid] = {"balance": 1500, "pos": 0, "name": call.from_user.first_name, "owns": []}
        
        count = len(lobby_players)
        names = ", ".join([players[i]['name'] for i in lobby_players])
        await call.message.edit_text(
            f"📢 **СБОР ИГРОКОВ**\n\nУчастники ({count}):\n👤 {names}\n\nОжидаем еще или начинаем?",
            reply_markup=get_lobby_kb(count)
        )
    await call.answer()

@dp.callback_query(F.data == "start_match")
async def start_match(call: CallbackQuery):
    global game_active
    game_active = True
    await call.message.answer("🎉 **ИГРА НАЧАЛАСЬ!**\n\nИспользуйте кнопки меню, чтобы ходить.", reply_markup=get_main_kb())
    await call.message.delete()

# --- Информационные колбэки ---
@dp.callback_query(F.data == "rules")
async def rules(call: CallbackQuery):
    await call.answer("Цель: стать самым богатым, скупая участки. Если попали на чужой — платите аренду!", show_alert=True)

@dp.callback_query(F.data == "dev")
async def dev(call: CallbackQuery):
    await call.message.answer("👨‍💻 **Developer:** @Whylovely05\nВерсия: 2.0 Stable")
    await call.answer()

@dp.callback_query(F.data == "help_info")
async def help_info(call: CallbackQuery):
    help_text = (
        "📖 **СПРАВКА ПО КОМАНДАМ**\n"
        "• `/monopoly` — Главное меню\n"
        "• `/exit` — Выход из игры\n"
        "• `/admin` — Панель (только админ)\n\n"
        "**Как играть?**\n"
        "Просто нажимай 'Бросить кубик', когда придет твой черед!"
    )
    await call.message.answer(help_text)
    await call.answer()

# --- ИГРОВЫЕ КНОПКИ ---
@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice(m: Message):
    if not game_active:
        return await m.answer("🛑 Игра еще не запущена! Введите /monopoly")
    
    uid = m.from_user.id
    if uid not in lobby_players:
        return await m.answer("❌ Вы не вступили в этот матч!")

    steps = random.randint(1, 6)
    old_pos = players[uid]["pos"]
    new_pos = (old_pos + steps) % MAP_SIZE
    players[uid]["pos"] = new_pos
    cell = BOARD[new_pos]
    
    res = f"🎲 **{m.from_user.first_name}** выкидывает {steps}!\n📍 Клетка: {cell['icon']} {cell['name']}\n`{get_visual_board(new_pos)}`"
    
    # (Тут остается твоя логика покупки/налога из предыдущего кода...)
    if new_pos < old_pos:
        players[uid]["balance"] += 200
        res += "\n🎁 +200$ за круг!"
    
    await m.answer(res)

# (Остальные команды: Баланс, Топ и т.д. остаются такими же)

# --- 7. ЗАПУСК ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK"

def run_web(): app.run(host='0.0.0.0', port=PORT)

async def main():
    Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
