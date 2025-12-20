import asyncio
import logging
import random
import sys
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- НАСТРОЙКИ ---
TOKEN = "8265158957:AAFXxWg63zCNqjdPHHD3LjCLQSKc7ZbgcQ0"
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

# --- КЛАВИАТУРА ИГРЫ ---
def get_game_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎲 Бросить кубик")
    builder.button(text="👤 Мой профиль")
    builder.button(text="❌ Скрыть меню")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

# --- ВИЗУАЛИЗАЦИЯ КАРТЫ ---
def draw_visual_map(current_player_id):
    p = players[current_player_id]
    map_lines = ["🗺 **ТЕКУЩЕЕ ПОЛОЖЕНИЕ**", "—" * 20]
    
    for i, field in enumerate(BOARD):
        owner_name = ""
        for uid, pl in players.items():
            if i in pl["properties"]:
                owner_name = f" 🏷 [{pl['name']}]"
        
        line = f"{field['name']}{owner_name}"
        
        if p["position"] == i:
            map_lines.append(f"▶️ **{line}**")
            map_lines.append("┗━━ 📍 ВЫ ЗДЕСЬ 📍")
        else:
            map_lines.append(f"▫️ {line}")
            
    map_lines.append("—" * 20)
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
    builder.row(types.InlineKeyboardButton(text="📜 Правила", callback_data="info_rules"),
                types.InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="info_dev"))
    
    await message.answer(
        "✨ **M O N O P O L Y** ✨\n\n"
        "Игра для чата: **Shit daily**\n"
        "Сбор игроков открыт! Используйте кнопки ниже.",
        reply_markup=builder.as_markup()
    )

@dp.message(Command("menu"))
async def show_menu(message: types.Message):
    await message.answer("🎮 Меню управления активировано!", reply_markup=get_game_keyboard())

# --- ЛОГИКА КЛАВИАТУРЫ ---

@dp.message(F.text == "❌ Скрыть меню")
async def hide_menu(message: types.Message):
    await message.answer("Меню скрыто. Напиши /menu, чтобы вернуть.", reply_markup=types.ReplyKeyboardRemove())

@dp.message(F.text == "👤 Мой профиль")
async def view_profile(message: types.Message):
    p = get_player(message.from_user.id, message.from_user.first_name)
    props = ", ".join([BOARD[i]["name"] for i in p["properties"]]) or "Нет имущества"
    await message.answer(f"👤 **Игрок:** {p['name']}\n💰 **Баланс:** {p['balance']}$\n🏠 **Владения:** {props}", parse_mode="Markdown")

@dp.message(F.text == "🎲 Бросить кубик")
async def handle_go(message: types.Message):
    if not game_started or message.from_user.id not in lobby:
        return await message.answer("Сначала вступите в игру через /monopoly")

    p = players[message.from_user.id]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    field = BOARD[p["position"]]
    
    map_text = draw_visual_map(message.from_user.id)
    response = f"🎲 **{p['name']}**, выпало: **{dice}**\n\n{map_text}"
    
    builder = InlineKeyboardBuilder()
    owner_id = next((uid for uid, pl in players.items() if p["position"] in pl["properties"]), None)
    
    if field["price"] > 0 and not owner_id:
        builder.button(text=f"💰 Купить за {field['price']}$", callback_data=f"buy_{p['position']}")
    elif owner_id and owner_id != message.from_user.id:
        rent = field["rent"]
        p["balance"] -= rent
        players[owner_id]["balance"] += rent
        response += f"\n\n⚠️ Вы заплатили **{rent}$** аренды игроку {players[owner_id]['name']}!"

    await message.answer(response, reply_markup=builder.as_markup(), parse_mode="Markdown")

# --- CALLBACKS ---

@dp.callback_query(F.data == "lobby_join")
async def join_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in lobby:
        lobby.append(callback.from_user.id)
        get_player(callback.from_user.id, callback.from_user.first_name)
        await callback.answer("Вы вступили в игру!")
    else:
        await callback.answer("Вы уже в игре")

@dp.callback_query(F.data == "game_start_final")
async def start_game_callback(callback: types.CallbackQuery):
    global game_started
    if callback.from_user.id != creator_id:
        return await callback.answer("Только создатель может запустить!", show_alert=True)
    if len(lobby) < 2:
        return await callback.answer("Нужно минимум 2 игрока!", show_alert=True)
    
    game_started = True
    await callback.message.answer(
        "🏁 **ИГРА НАЧАЛАСЬ!**\nИспользуйте кнопки внизу экрана для хода.",
        reply_markup=get_game_keyboard(),
        parse_mode="Markdown"
    )
    await callback.message.delete()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_callback(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    p = players[callback.from_user.id]
    field = BOARD[idx]
    
    if any(idx in pl["properties"] for pl in players.values()):
        return await callback.answer("Уже куплено!")

    if p["balance"] >= field["price"]:
        p["balance"] -= field["price"]
        p["properties"].append(idx)
        await callback.message.edit_text(f"🏠 **{p['name']}** купил **{field['name']}**!\nОстаток: {p['balance']}$")
    else:
        await callback.answer("Недостаточно денег!", show_alert=True)

@dp.callback_query(F.data == "info_dev")
async def info_dev(callback: types.CallbackQuery):
    await callback.message.answer("👨‍💻 **Разработчик:** @Whylovely05\n🎮 Сделано для: **Shit daily**")
    await callback.answer()

@dp.callback_query(F.data == "info_rules")
async def info_rules(callback: types.CallbackQuery):
    rules = (
        "📖 **ПРАВИЛА:**\n\n"
        "1. Нажимай кнопку '🎲 Бросить кубик'.\n"
        "2. Покупай свободные улицы.\n"
        "3. Если встал на чужую улицу — платишь аренду автоматически.\n"
        "4. Клетка 💸 Налоговая списывает 50$.\n"
        "5. Если кнопки пропали — напиши /menu."
    )
    await callback.message.answer(rules)
    await callback.answer()

# --- СЕРВЕР ДЛЯ RENDER ---

async def handle_hc(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    
