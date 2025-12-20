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

# Глобальные переменные
players = {} 
owners = {}   
lobby = []
lobby_active = False
game_started = False
organizer_id = None
current_turn_index = 0 

IMG_START = "https://i.ibb.co/v4m0YmH/monopoly-start.jpg"
IMG_LOBBY = "https://i.ibb.co/0fX9G9g/monopoly-lobby.jpg"

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

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def render_list_map(uid):
    curr_uid = lobby[current_turn_index]
    turn_name = players[curr_uid]['name']
    lines = [f"🎲 **СЕЙЧАС ХОДИТ:** {turn_name}\n", "📍 **КАРТА:**\n"]
    for i, cell in enumerate(BOARD):
        m_list = [("📍 **ВЫ**" if pid == uid else f"👤 {pdata['name']}") for pid, pdata in players.items() if pdata["position"] == i]
        # Проверка владельца
        if i in owners:
            owner_name = players[owners[i]]['name']
            status = f"🏠 {owner_name}"
        else:
            status = "—" if cell["price"] == 0 else f"💰 {cell['price']}$"
            
        lines.append(f"{cell['name']} — `[{status}]` {' '.join(m_list)}")
    lines.append(f"\n💵 Ваш баланс: `{players[uid]['balance']}$`")
    return "\n".join(lines)

def get_lobby_content():
    names = "\n".join([f"{i+1}. {players[uid]['name']}" for i, uid in enumerate(lobby)])
    text = (f"⏳ **ИДЕТ СБОР ИГРОКОВ**\n\n"
            f"**Участники:**\n{names}\n\n"
            f"📍 Минимум: 2 игрока.")
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Вступить", callback_data="join"),
           types.InlineKeyboardButton(text="❌ Выйти", callback_data="leave"))
    kb.row(types.InlineKeyboardButton(text="🚀 Начать сейчас", callback_data="force_start"))
    return text, kb.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: types.Message):
    global lobby_active, game_started, lobby, owners
    # Сброс игры для теста, если нужно начать заново
    lobby_active, game_started = False, False
    lobby, owners = [], {}
    
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🏁 Начать сбор", callback_data="start_lobby"))
    await m.answer_photo(photo=IMG_START, caption="💎 **M O N O P O L Y**\nНажми кнопку ниже!", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_lobby")
async def lobby_start(c: types.CallbackQuery):
    global lobby_active, organizer_id, current_turn_index
    lobby_active, organizer_id, current_turn_index = True, c.from_user.id, 0
    lobby.append(organizer_id)
    players[organizer_id] = {"name": c.from_user.first_name[:10], "balance": 1500, "position": 0}
    
    text, kb = get_lobby_content()
    await c.message.answer_photo(photo=IMG_LOBBY, caption=text, reply_markup=kb)
    await c.message.delete()

@dp.callback_query(F.data == "join")
async def join(c: types.CallbackQuery):
    if lobby_active and c.from_user.id not in lobby:
        lobby.append(c.from_user.id)
        players[c.from_user.id] = {"name": c.from_user.first_name[:10], "balance": 1500, "position": 0}
        text, kb = get_lobby_content()
        await c.message.edit_caption(caption=text, reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "force_start")
async def force_start(c: types.CallbackQuery):
    if c.from_user.id == organizer_id:
        if len(lobby) >= 2:
            global lobby_active, game_started
            lobby_active, game_started = False, True
            kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
            await c.message.answer(f"🎮 **ИГРА НАЧАЛАСЬ!**\nПервым ходит: **{players[lobby[0]]['name']}**", reply_markup=kb)
            await c.message.delete()
        else:
            await c.answer("Нужно минимум 2 игрока!", show_alert=True)
    await c.answer()

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    global current_turn_index
    if not game_started: return
    if m.from_user.id != lobby[current_turn_index]:
        return await m.answer("Сейчас не твой ход! Подожди очереди.")
    
    p = players[m.from_user.id]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    cell = BOARD[p["position"]]
    
    res = f"🎲 **{p['name']}** выкинул {dice} и встал на **{cell['name']}**\n"
    kb = InlineKeyboardBuilder()
    
    # Логика аренды
    if p["position"] in owners and owners[p["position"]] != m.from_user.id:
        owner_id = owners[p["position"]]
        rent = cell["rent"]
        p["balance"] -= rent
        players[owner_id]["balance"] += rent
        res += f"💸 Оплачена аренда: {rent}$ игроку {players[owner_id]['name']}\n"
    
    # Логика покупки
    elif cell["price"] > 0 and p["position"] not in owners:
        if p["balance"] >= cell["price"]:
            kb.button(text=f"🛒 Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")
    
    # Передаем ход СЛЕДУЮЩЕМУ
    current_turn_index = (current_turn_index + 1) % len(lobby)
    
    await m.answer(res + "\n" + render_list_map(m.from_user.id), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    p = players[c.from_user.id]
    cell = BOARD[idx]
    
    if p["balance"] >= cell["price"] and idx not in owners:
        p["balance"] -= cell["price"]
        owners[idx] = c.from_user.id
        await c.message.edit_text(f"✅ **{p['name']}** купил {cell['name']}!\n\n" + render_list_map(c.from_user.id), parse_mode="Markdown")
    else:
        await c.answer("Недостаточно денег или уже куплено!", show_alert=True)
    await c.answer()

# --- ЗАПУСК ---
async def handle(request): return web.Response(text="Bot is running")

async def main():
    # Запускаем веб-сервер фоном, чтобы не блокировать бота
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    asyncio.create_task(site.start()) 

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
