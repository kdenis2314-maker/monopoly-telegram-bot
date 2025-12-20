import asyncio
import logging
import random
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAHHBM33jT4XcYMxRXyKzzmN97ZianTiUWE"
PORT = 8082

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ДАННЫЕ ИГРЫ ---
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "rent": 0},
    {"name": "🏠 Улица Пушкина", "price": 100, "rent": 20},
    {"name": "🏠 Улица Чехова", "price": 120, "rent": 25},
    {"name": "💸 Налоговая", "price": 0, "rent": 50},
    {"name": "🏨 Улица Горького", "price": 200, "rent": 40},
    {"name": "🏨 Проспект Мира", "price": 240, "rent": 50},
    {"name": "⛓ Тюрьма", "price": 0, "rent": 0},
    {"name": "💎 Арбат", "price": 400, "rent": 100},
]

players = {}
lobby = []
game_started = False
creator_id = None

def get_player(user_id, name):
    if user_id not in players:
        players[user_id] = {"name": name, "balance": 1000, "position": 0, "properties": []}
    return players[user_id]

# --- КЛАВИАТУРА ИГРОКА ---
def get_game_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎲 Бросить кубик")
    builder.button(text="👤 Мой профиль")
    builder.button(text="❌ Скрыть меню")
    builder.adjust(2, 1) # Две кнопки в ряд, затем одна
    return builder.as_markup(resize_keyboard=True)

# --- ВИЗУАЛИЗАЦИЯ КАРТЫ ---
def draw_visual_map(current_player_id):
    p = players[current_player_id]
    map_lines = ["🗺 **ТЕКУЩЕЕ ПОЛОЖЕНИЕ НА КАРТЕ**", "—" * 25]
    
    for i, field in enumerate(BOARD):
        # Поиск владельца
        owner_name = ""
        for uid, pl in players.items():
            if i in pl["properties"]:
                owner_name = f" [Владелец: {pl['name']}]"
        
        # Основная строка поля
        line = f"{field['name']}{owner_name}"
        
        # Если игрок здесь, выделяем жирным и ставим метку
        if p["position"] == i:
            map_lines.append(f"▶️ **{line}**")
            map_lines.append("┗━━ 📍 ВЫ ЗДЕСЬ 📍")
        else:
            map_lines.append(f"▫️ {line}")
            
    map_lines.append("—" * 25)
    return "\n".join(map_lines)

# --- КОМАНДЫ ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    global creator_id, lobby, game_started
    creator_id = message.from_user.id
    lobby = [creator_id]
    get_player(creator_id, message.from_user.first_name)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Вступить в игру", callback_data="lobby_join")
    builder.button(text="🏁 НАЧАТЬ", callback_data="game_start_final")
    
    await message.answer(
        "✨ **M O N O P O L Y** ✨\n\n"
        "Вы запустили сбор игроков для чата **Shit daily**.\n"
        "Используйте кнопки ниже, чтобы собрать команду.",
        reply_markup=builder.as_markup()
    )

@dp.message(Command("menu"))
async def show_menu(message: types.Message):
    await message.answer("Кнопки управления активированы!", reply_markup=get_game_keyboard())

# --- ОБРАБОТКА КНОПОК КЛАВИАТУРЫ ---

@dp.message(F.text == "❌ Скрыть меню")
async def hide_menu(message: types.Message):
    await message.answer("Меню скрыто. Чтобы вернуть, напиши /menu", reply_markup=types.ReplyKeyboardRemove())

@dp.message(F.text == "👤 Мой профиль")
async def view_profile(message: types.Message):
    p = get_player(message.from_user.id, message.from_user.first_name)
    props = ", ".join([BOARD[i]["name"] for i in p["properties"]]) or "Нет имущества"
    await message.answer(f"💰 **Баланс:** {p['balance']}$\n🏠 **Имущество:** {props}", parse_mode="Markdown")

@dp.message(F.text == "🎲 Бросить кубик")
async def handle_go(message: types.Message):
    if not game_started or message.from_user.id not in lobby:
        return await message.answer("Игра еще не началась или вы не в игре.")

    p = players[message.from_user.id]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    field = BOARD[p["position"]]
    
    # Генерация карты
    map_text = draw_visual_map(message.from_user.id)
    
    response = f"🎲 **{p['name']}**, выпало: **{dice}**\n\n{map_text}"
    
    builder = InlineKeyboardBuilder()
    owner_id = next((uid for uid, pl in players.items() if p["position"] in pl["properties"]), None)
    
    if field["price"] > 0 and not owner_id:
        builder.button(text=f"💰 Купить {field['name']} за {field['price']}$", callback_data=f"buy_{p['position']}")
    elif owner_id and owner_id != message.from_user.id:
        rent = field["rent"]
        p["balance"] -= rent
        players[owner_id]["balance"] += rent
        response += f"\n\n⚠️ Списана аренда: **{rent}$**"

    await message.answer(response, reply_markup=builder.as_markup(), parse_mode="Markdown")

# --- CALLBACKS ---

@dp.callback_query(F.data == "lobby_join")
async def join_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in lobby:
        lobby.append(callback.from_user.id)
        get_player(callback.from_user.id, callback.from_user.first_name)
        await callback.answer("Вы в игре!")
    else:
        await callback.answer("Вы уже в списке")

@dp.callback_query(F.data == "game_start_final")
async def start_game_callback(callback: types.CallbackQuery):
    global game_started
    if callback.from_user.id != creator_id:
        return await callback.answer("Только создатель может начать!")
    if len(lobby) < 2:
        return await callback.answer("Нужно минимум 2 игрока!")
    
    game_started = True
    await callback.message.answer(
        "🎮 **ИГРА НАЧАЛАСЬ!**\nУ вас появились кнопки управления внизу экрана.",
        reply_markup=get_game_keyboard(),
        parse_mode="Markdown"
    )
    await callback.message.delete()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_callback(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    p = players[callback.from_user.id]
    field = BOARD[idx]
    
    if p["balance"] >= field["price"]:
        p["balance"] -= field["price"]
        p["properties"].append(idx)
        await callback.message.edit_text(f"✅ **{p['name']}** купил поле **{field['name']}**!")
    else:
        await callback.answer("Недостаточно денег!", show_alert=True)

@dp.callback_query(F.data.startswith("info_"))
async def info_callback(callback: types.CallbackQuery):
    if callback.data == "info_dev":
        await callback.message.answer("👨‍💻 Разработчик: @Whylovely05\n🎮 Для чата: Shit daily")
    await callback.answer()

# --- СЕРВЕР ---
async def handle_hc(request): return web.Response(text="OK")
async def main():
    asyncio.create_task(web.TCPSite(web.AppRunner(web.Application()).setup(), "0.0.0.0", PORT).start())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
