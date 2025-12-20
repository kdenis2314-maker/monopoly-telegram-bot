import asyncio
import random
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAEMnEcldgMy7go_oxhHCweqxhe69XjKChE" 
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

# Состояние игры
players = {} 
owners = {}   
lobby = []
lobby_active = False
game_started = False
organizer_id = None
current_turn_index = 0 

# Ресурсы
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

# --- ЛОГИКА ИНТЕРФЕЙСА ---

def render_list_map(viewer_id):
    """Отрисовка карты и статуса игроков"""
    curr_uid = lobby[current_turn_index]
    turn_name = players[curr_uid]['name']
    
    lines = [f"🎲 **СЕЙЧАС ХОДИТ:** {turn_name}\n", "📍 **КАРТА:**\n"]
    
    for i, cell in enumerate(BOARD):
        # Кто стоит на этой клетке
        visitors = [f"👤 {players[pid]['name']}" if pid != viewer_id else "📍 **ВЫ**" 
                    for pid in lobby if players[pid]['position'] == i]
        
        # Статус клетки (владелец или цена)
        if i in owners:
            owner_name = players[owners[i]]['name']
            status = f"🏠 {owner_name}"
        else:
            status = "—" if cell["price"] == 0 else f"💰 {cell['price']}$"
            
        visitors_str = " ".join(visitors)
        lines.append(f"{cell['name']} — `[{status}]` {visitors_str}")
    
    lines.append(f"\n💵 Ваш баланс: `{players[viewer_id]['balance']}$`")
    return "\n".join(lines)

def get_lobby_kb():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Вступить", callback_data="join"),
           types.InlineKeyboardButton(text="❌ Выйти", callback_data="leave"))
    kb.row(types.InlineKeyboardButton(text="🚀 Начать игру", callback_data="force_start"))
    return kb.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: types.Message):
    global lobby_active, game_started, lobby, owners, players
    if lobby_active or game_started:
        return await m.answer("⚠️ Игра уже запущена или идет сбор!")
    
    # Сброс данных перед новой игрой
    lobby, owners, players = [], {}, {}
    lobby_active = True
    
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🏁 Создать лобби", callback_data="start_lobby"))
    await m.answer_photo(photo=IMG_START, caption="💎 **M O N O P O L Y**\nНажми кнопку, чтобы собрать игроков!", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_lobby")
async def lobby_start(c: types.CallbackQuery):
    global organizer_id, current_turn_index
    organizer_id = c.from_user.id
    current_turn_index = 0
    
    if organizer_id not in lobby:
        lobby.append(organizer_id)
        players[organizer_id] = {"name": c.from_user.first_name[:10], "balance": 1500, "position": 0}
    
    await c.message.delete()
    await c.message.answer_photo(
        photo=IMG_LOBBY, 
        caption=f"⏳ **СБОР ИГРОКОВ**\n\nОрганизатор: {c.from_user.first_name}\nУчастников: {len(lobby)}", 
        reply_markup=get_lobby_kb()
    )

@dp.callback_query(F.data == "join")
async def join_game(c: types.CallbackQuery):
    if not lobby_active: return await c.answer("Сбор уже закончен.")
    if c.from_user.id in lobby: return await c.answer("Вы уже в игре!")
    
    lobby.append(c.from_user.id)
    players[c.from_user.id] = {"name": c.from_user.first_name[:10], "balance": 1500, "position": 0}
    
    await c.message.edit_caption(
        caption=f"⏳ **СБОР ИГРОКОВ**\n\nУчастников: {len(lobby)}\nПоследний зашел: {c.from_user.first_name}",
        reply_markup=get_lobby_kb()
    )
    await c.answer("Вы вступили!")

@dp.callback_query(F.data == "force_start")
async def force_start(c: types.CallbackQuery):
    global lobby_active, game_started
    if c.from_user.id != organizer_id:
        return await c.answer("Только организатор может начать игру!", show_alert=True)
    
    if len(lobby) < 2:
        return await c.answer("Нужно хотя бы 2 игрока!", show_alert=True)
    
    lobby_active, game_started = False, True
    kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
    
    await c.message.delete()
    await bot.send_message(c.message.chat.id, f"🎮 **ИГРА НАЧАЛАСЬ!**\n\nПервым ходит: **{players[lobby[0]]['name']}**", reply_markup=kb)

@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice(m: types.Message):
    global current_turn_index
    if not game_started: return
    
    current_player_id = lobby[current_turn_index]
    if m.from_user.id != current_player_id:
        return await m.answer(f"⏳ Сейчас ход игрока **{players[current_player_id]['name']}**!")
    
    p = players[current_player_id]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    cell = BOARD[p["position"]]
    
    msg = f"🎲 **{p['name']}** выкинул {dice} и попал на **{cell['name']}**\n"
    kb = InlineKeyboardBuilder()
    
    # 1. Налог или спец-клетка
    if cell["name"] == "💸 Налог":
        p["balance"] -= 100
        msg += "💸 Вы заплатили налог 100$!\n"
        
    # 2. Аренда
    elif p["position"] in owners and owners[p["position"]] != current_player_id:
        owner_id = owners[p["position"]]
        rent = cell["rent"]
        p["balance"] -= rent
        players[owner_id]["balance"] += rent
        msg += f"💰 Оплачена аренда {rent}$ игроку {players[owner_id]['name']}\n"
        
    # 3. Возможность покупки
    elif cell["price"] > 0 and p["position"] not in owners:
        if p["balance"] >= cell["price"]:
            kb.button(text=f"🛒 Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")
    
    # Переход хода
    current_turn_index = (current_turn_index + 1) % len(lobby)
    
    await m.answer(msg + "\n" + render_list_map(m.from_user.id), reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    p = players[c.from_user.id]
    cell = BOARD[idx]
    
    if p["balance"] >= cell["price"] and idx not in owners:
        p["balance"] -= cell["price"]
        owners[idx] = c.from_user.id
        await c.message.edit_text(f"✅ **{p['name']}** приобрел {cell['name']}!\n\n" + render_list_map(c.from_user.id))
    else:
        await c.answer("Ошибка покупки!", show_alert=True)

# --- ИСПРАВЛЕННЫЙ ЗАПУСК ДЛЯ RENDER ---

async def handle(request):
    return web.Response(text="Monopoly Bot is Running", status=200)

async def main():
    # Настройка Web-сервера (Health Check для Render)
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    logging.info(f"Server starting on port {port}")
    asyncio.create_task(site.start()) # Запуск в фоне

    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"FATAL: {e}")
