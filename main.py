import asyncio
import random
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAEMnEcldgMy7go_oxhHCweqxhe69XjKChE" 
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальные переменные состояния
players = {} 
owners = {}   
lobby = []
lobby_active = False
game_started = False
organizer_id = None
current_turn_index = 0 

# Твои картинки из кода
IMG_START = "https://i.ibb.co/v4m0YmH/monopoly-start.jpg"
IMG_LOBBY = "https://i.ibb.co/0fX9G9g/monopoly-lobby.jpg"

# Расширенное поле игры
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "rent": 0},
    {"name": "🏠 Ул. Житная", "price": 60, "rent": 10},
    {"name": "🏠 Ул. Нагатинская", "price": 60, "rent": 10},
    {"name": "💸 Налог", "price": 0, "rent": 100},
    {"name": "🏠 Варшавское ш.", "price": 100, "rent": 20},
    {"name": "🏠 Ул. Огарева", "price": 120, "rent": 30},
    {"name": "⛓ Тюрьма", "price": 0, "rent": 0},
    {"name": "🏠 Парк Культуры", "price": 140, "rent": 40},
    {"name": "🏠 Охотный Ряд", "price": 160, "rent": 50},
    {"name": "🏨 Пр. Мира", "price": 200, "rent": 60},
    {"name": "🏠 Тверская", "price": 240, "rent": 80},
    {"name": "🏠 Ул. Пушкина", "price": 300, "rent": 110},
    {"name": "💎 Арбат", "price": 400, "rent": 150},
]

# --- ИНТЕРФЕЙС ---

def get_lobby_content():
    names = "\n".join([f"{i+1}. {players[uid]['name']}" for i, uid in enumerate(lobby)])
    text = (f"⏳ **ИДЕТ СБОР ИГРОКОВ (3 МИНУТЫ)**\n\n"
            f"**Очередь ходов:**\n{names}\n\n"
            f"📍 Минимум: 2 игрока.\n📍 Старт: Автоматически через 3 мин.")
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Вступить", callback_data="join"),
           types.InlineKeyboardButton(text="❌ Выйти", callback_data="leave"))
    kb.row(types.InlineKeyboardButton(text="🚀 Начать сейчас", callback_data="force_start"))
    return text, kb.as_markup()

def render_list_map(uid):
    curr_uid = lobby[current_turn_index]
    turn_name = players[curr_uid]['name']
    lines = [f"🎲 **СЕЙЧАС ХОДИТ:** {turn_name}\n", "📍 **КАРТА:**\n"]
    for i, cell in enumerate(BOARD):
        m_list = [("📍 **ВЫ**" if pid == uid else f"👤 {pdata['name']}") for pid, pdata in players.items() if pdata["position"] == i]
        status = "—" if cell["price"] == 0 else (f"🏠 {players[owners[i]]['name']}" if i in owners else f"💰 {cell['price']}$")
        lines.append(f"{cell['name']} — `[{status}]` {' '.join(m_list)}")
    lines.append(f"\n💵 Баланс: `{players[uid]['balance']}$`")
    return "\n".join(lines)

# --- WEB СЕРВЕР ---
async def handle(request): return web.Response(text="Live")
async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()

# --- КОМАНДЫ ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: types.Message):
    if lobby_active or game_started: return await m.answer("⚠️ Игра уже идет!")
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🏁 Начать сбор", callback_data="start_lobby"))
    await m.answer_photo(photo=IMG_START, caption="💎 **M O N O P O L Y**\nНажми кнопку, чтобы собрать команду!", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_lobby")
async def lobby_start(c: types.CallbackQuery):
    global lobby_active, lobby, organizer_id, current_turn_index
    lobby_active, organizer_id, current_turn_index = True, c.from_user.id, 0
    lobby = [organizer_id]
    players[organizer_id] = {"name": c.from_user.first_name[:10], "balance": 1500, "position": 0}
    
    text, kb = get_lobby_content()
    await c.message.answer_photo(photo=IMG_LOBBY, caption=text, reply_markup=kb)
    await c.message.delete()
    asyncio.create_task(timer_task(c.message.chat.id))
    await c.answer()

async def timer_task(chat_id):
    await asyncio.sleep(180) 
    if lobby_active: await start_game_logic(chat_id)

async def start_game_logic(chat_id):
    global lobby_active, game_started
    if len(lobby) < 2:
        lobby_active = False
        return await bot.send_message(chat_id, "❌ Сбор отменен: мало игроков.")
    lobby_active, game_started = False, True
    kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
    await bot.send_message(chat_id, f"🎮 **ИГРА НАЧАЛАСЬ!**\nХодит: **{players[lobby[0]]['name']}**", reply_markup=kb)

@dp.callback_query(F.data == "join")
async def join(c: types.CallbackQuery):
    if lobby_active and c.from_user.id not in lobby:
        lobby.append(c.from_user.id)
        players[c.from_user.id] = {"name": c.from_user.first_name[:10], "balance": 1500, "position": 0}
        text, kb = get_lobby_content()
        await c.message.edit_caption(caption=text, reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "leave")
async def leave(c: types.CallbackQuery):
    if c.from_user.id != organizer_id and c.from_user.id in lobby:
        lobby.remove(c.from_user.id)
        players.pop(c.from_user.id)
        text, kb = get_lobby_content()
        await c.message.edit_caption(caption=text, reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "force_start")
async def force_start(c: types.CallbackQuery):
    if c.from_user.id == organizer_id and len(lobby) >= 2:
        await start_game_logic(c.message.chat.id)
    await c.answer()

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    global current_turn_index
    if not game_started or m.from_user.id != lobby[current_turn_index]: return
    
    p = players[m.from_user.id]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    cell = BOARD[p["position"]]
    
    res = f"🎲 **{p['name']}** выкинул {dice} и попал на {cell['name']}\n"
    kb = InlineKeyboardBuilder()
    
    if p["position"] in owners and owners[p["position"]] != m.from_user.id:
        rent = cell["rent"]
        p["balance"] -= rent; players[owners[p["position"]]]["balance"] += rent
        res += f"💸 Аренда: {rent}$ игроку {players[owners[p['position']]]['name']}\n"
    elif cell["price"] > 0 and p["position"] not in owners:
        kb.button(text=f"🛒 Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")
    
    current_turn_index = (current_turn_index + 1) % len(lobby)
    await m.answer(res + "\n" + render_list_map(m.from_user.id), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    if players[c.from_user.id]["balance"] >= BOARD[idx]["price"]:
        players[c.from_user.id]["balance"] -= BOARD[idx]["price"]; owners[idx] = c.from_user.id
        await c.message.edit_text(f"✅ Куплено!\n\n" + render_list_map(c.from_user.id), parse_mode="Markdown")
    await c.answer()

async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
