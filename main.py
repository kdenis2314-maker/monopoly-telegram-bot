import asyncio
import random
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAHgGmom23KQLyVh78L5CbrSaWaYFqTyOSY" # Вставь сюда токен от BotFather
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Данные игры
players = {} 
owners = {}   
lobby = []
lobby_active = False
game_started = False

# Список всех клеток
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "rent": 0},
    {"name": "🏠 Ул. Пушкина", "price": 100, "rent": 20},
    {"name": "🏠 Ул. Гоголя", "price": 120, "rent": 30},
    {"name": "💸 Налоговая", "price": 0, "rent": 50},
    {"name": "🏠 Ул. Чехова", "price": 140, "rent": 40},
    {"name": "🏨 Пр. Мира", "price": 200, "rent": 60},
    {"name": "🏨 Ул. Горького", "price": 240, "rent": 80},
    {"name": "⛓ Тюрьма", "price": 0, "rent": 0},
    {"name": "💎 Арбат", "price": 400, "rent": 150},
]

# --- ФУНКЦИЯ КАРТЫ (СПИСОК) ---
def render_list_map(current_user_id):
    map_lines = ["📍 **ТЕКУЩАЯ КАРТА:**\n"]
    for i, cell in enumerate(BOARD):
        m_list = []
        for uid, p_data in players.items():
            if p_data["position"] == i:
                m_list.append("📍 **ВЫ**" if uid == current_user_id else f"👤 {p_data['name']}")
        
        markers = " ".join(m_list)
        if cell["price"] == 0: status = "—"
        elif i in owners: status = f"👤 {players[owners[i]]['name']}"
        else: status = f"💰 {cell['price']}$"
            
        map_lines.append(f"{cell['name']} — `[{status}]` {markers}")
        
    map_lines.append(f"\n💵 Твой баланс: `{players[current_user_id]['balance']}$`")
    return "\n".join(map_lines)

# --- WEB СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Бот Монополия запущен и работает!")

async def run_web():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render дает порт в переменной окружения PORT
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- КОМАНДЫ БОТА ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏁 Начать сбор игроков", callback_data="start_lobby"))
    builder.row(types.InlineKeyboardButton(text="🚀 Поделиться", switch_inline_query="Го в Монополию!"))
    builder.row(
        types.InlineKeyboardButton(text="📜 Правила", callback_data="info_rules"),
        types.InlineKeyboardButton(text="👨‍💻 О девелопере", callback_data="info_dev")
    )
    
    # Зелено-черный прямоугольный арт
    await message.answer_photo(
        photo="https://i.ibb.co/v4m0YmH/monopoly-start.jpg", 
        caption="💎 **M O N O P O L Y** 💎\n\nСпециально для чата **Shit daily**.",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "info_rules")
async def info_rules(c: types.CallbackQuery):
    await c.message.answer("📜 **ПРАВИЛА:**\n1. Сбор 3 минуты.\n2. Бросай кубик и покупай улицы.\n3. Стой на своем или плати аренду чужим!")
    await c.answer()

@dp.callback_query(F.data == "info_dev")
async def info_dev(c: types.CallbackQuery):
    await c.message.answer("👨‍💻 **ДЕВЕЛОПЕР:**\nАвтор: @Whylovely05\nДля чата: **Shit daily**")
    await c.answer()

@dp.callback_query(F.data == "start_lobby")
async def start_lobby(c: types.CallbackQuery):
    global lobby_active, lobby, game_started
    if lobby_active: return await c.answer("Сбор уже идет!")
    lobby, lobby_active, game_started = [], True, False
    kb = InlineKeyboardBuilder().button(text="✅ Вступить", callback_data="join").as_markup()
    await c.message.answer("⏳ **СБОР ИГРОКОВ (3 МИН)**\nВступайте в игру!", reply_markup=kb)
    asyncio.create_task(timer_3min(c.message.chat.id))

async def timer_3min(chat_id):
    global lobby_active, game_started
    await asyncio.sleep(180)
    lobby_active = False
    if len(lobby) >= 2:
        game_started = True
        kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
        await bot.send_message(chat_id, "🎮 **ИГРА НАЧАЛАСЬ!**", reply_markup=kb)
    else:
        await bot.send_message(chat_id, "❌ Недостаточно игроков.")

@dp.callback_query(F.data == "join")
async def join_game(c: types.CallbackQuery):
    if c.from_user.id not in lobby:
        lobby.append(c.from_user.id)
        players[c.from_user.id] = {"name": c.from_user.first_name, "balance": 1000, "position": 0}
        await c.answer("Ты в игре!")
    else: await c.answer("Ты уже вступил.")

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    uid = m.from_user.id
    if not game_started or uid not in players: return
    p = players[uid]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    cell = BOARD[p["position"]]
    kb = InlineKeyboardBuilder()
    text = f"🎲 Выпало: **{dice}**\n\n"
    if p["position"] in owners and owners[p["position"]] != uid:
        rent = cell["rent"]
        p["balance"] -= rent
        players[owners[p["position"]]]["balance"] += rent
        text += f"💸 Оплачена аренда: **{rent}$**\n"
    elif cell["price"] > 0 and p["position"] not in owners:
        kb.button(text=f"🛒 Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")
    await m.answer(text + render_list_map(uid), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_prop(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    p = players[c.from_user.id]
    if p["balance"] >= BOARD[idx]["price"]:
        p["balance"] -= BOARD[idx]["price"]
        owners[idx] = c.from_user.id
        await c.message.edit_text(f"✅ Успешно куплено!\n\n" + render_list_map(c.from_user.id), parse_mode="Markdown")
    else: await c.answer("Нет денег!")

# --- СТАРТ ---
async def main():
    await run_web() # Запуск веб-части для Render
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
