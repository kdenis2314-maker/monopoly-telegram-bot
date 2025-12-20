import asyncio
import random
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# Настройка логирования для Render
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAHgGmom23KQLyVh78L5CbrSaWaYFqTyOSY"
bot = Bot(token=TOKEN)
dp = Dispatcher()

players = {} 
owners = {}   
lobby = []
lobby_active = False
game_started = False

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

# --- КАРТА-СПИСОК ---
def render_list_map(uid):
    lines = ["📍 **ТЕКУЩАЯ КАРТА:**\n"]
    for i, cell in enumerate(BOARD):
        m = [("📍 **ВЫ**" if k == uid else f"👤 {v['name']}") for k, v in players.items() if v["position"] == i]
        status = "—" if cell["price"] == 0 else (f"👤 {players[owners[i]]['name']}" if i in owners else f"💰 {cell['price']}$")
        lines.append(f"{cell['name']} — `[{status}]` {' '.join(m)}")
    lines.append(f"\n💵 Твой баланс: `{players[uid]['balance']}$`")
    return "\n".join(lines)

# --- WEB СЕРВЕР (Для Render) ---
async def handle(request):
    return web.Response(text="Бот запущен!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- КОМАНДЫ ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(m: types.Message):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🏁 Начать сбор", callback_data="start_lobby"))
    kb.row(types.InlineKeyboardButton(text="🚀 Поделиться", switch_inline_query="Го играть!"))
    kb.row(types.InlineKeyboardButton(text="📜 Правила", callback_data="rules"),
           types.InlineKeyboardButton(text="👨‍💻 Девелопер", callback_data="dev"))
    
    text = "💎 **M O N O P O L Y**\nДля чата **Shit daily**."
    try:
        await m.answer_photo(photo="https://i.ibb.co/v4m0YmH/monopoly-start.jpg", caption=text, reply_markup=kb.as_markup())
    except:
        await m.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_lobby")
async def lobby_start(c: types.CallbackQuery):
    global lobby_active, lobby, game_started
    if lobby_active: return await c.answer("Сбор уже идет!")
    lobby, lobby_active, game_started = [], True, False
    await c.message.answer("⏳ **СБОР 3 МИНУТЫ!**", 
                           reply_markup=InlineKeyboardBuilder().button(text="✅ Вступить", callback_data="join").as_markup())
    asyncio.create_task(timer(c.message.chat.id))
    await c.answer()

async def timer(chat_id):
    global lobby_active, game_started
    await asyncio.sleep(180)
    lobby_active = False
    if len(lobby) >= 2:
        game_started = True
        await bot.send_message(chat_id, "🎮 **ИГРА НАЧАЛАСЬ!**", 
                               reply_markup=ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True))
    else:
        await bot.send_message(chat_id, "❌ Недостаточно игроков.")

@dp.callback_query(F.data == "join")
async def join(c: types.CallbackQuery):
    if c.from_user.id not in lobby:
        lobby.append(c.from_user.id)
        players[c.from_user.id] = {"name": c.from_user.first_name[:10], "balance": 1000, "position": 0}
        await c.answer("Вы в игре!")
    else: await c.answer("Уже в списке.")

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    uid = m.from_user.id
    if not game_started or uid not in players: return
    p = players[uid]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    cell = BOARD[p["position"]]
    text = f"🎲 Выпало: **{dice}**\n"
    kb = InlineKeyboardBuilder()
    
    if p["position"] in owners and owners[p["position"]] != uid:
        rent = cell["rent"]
        p["balance"] -= rent
        players[owners[p["position"]]]["balance"] += rent
        text += f"💸 Аренда: {rent}$\n"
    elif cell["price"] > 0 and p["position"] not in owners:
        kb.button(text=f"🛒 Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")
    
    await m.answer(text + "\n" + render_list_map(uid), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    p = players[c.from_user.id]
    if p["balance"] >= BOARD[idx]["price"]:
        p["balance"] -= BOARD[idx]["price"]; owners[idx] = c.from_user.id
        await c.message.edit_text(f"✅ Куплено!\n\n" + render_list_map(c.from_user.id), parse_mode="Markdown")
    else: await c.answer("Нет денег!")

# --- ЗАПУСК ---
async def main():
    await start_web_server() # Для Render
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
