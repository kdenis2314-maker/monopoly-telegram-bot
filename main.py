import asyncio
import logging
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAGN2onCGgPbQ1qilkp0LCYMHFY6Sa4T3wo"
PORT = 8082

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ДАННЫЕ ИГРЫ ---
BOARD = [
    {"name": "СТАРТ", "price": 0, "rent": 0},
    {"name": "Улица Пушкина", "price": 100, "rent": 20},
    {"name": "Улица Чехова", "price": 120, "rent": 25},
    {"name": "Налоговая", "price": 0, "rent": 50},
    {"name": "Улица Горького", "price": 200, "rent": 40},
    {"name": "Проспект Мира", "price": 240, "rent": 50},
    {"name": "Тюрьма", "price": 0, "rent": 0},
    {"name": "Арбат", "price": 400, "rent": 100},
]

# Глобальные состояния
players = {}      # Данные игроков
lobby = []        # ID тех, кто вступил в очередь
game_started = False
creator_id = None # Тот, кто вызвал меню

def get_player(user_id, name):
    if user_id not in players:
        players[user_id] = {"name": name, "balance": 1000, "position": 0, "properties": []}
    return players[user_id]

# --- ГЛАВНОЕ МЕНЮ (/monopoly) ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    global creator_id
    creator_id = message.from_user.id
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🚀 Начать сбор игроков", callback_data="lobby_join"))
    builder.row(types.InlineKeyboardButton(text="📜 Правила", callback_data="info_rules"),
                types.InlineKeyboardButton(text="🤖 О боте", callback_data="info_bot"))
    builder.row(types.InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="info_dev"))

    await message.answer(
        f"Привет, {message.from_user.first_name}! Это меню управления Монополией.\n"
        "Только ты можешь управлять этим меню.",
        reply_markup=builder.as_markup()
    )

# --- ЛОГИКА ЛОББИ ---

@dp.callback_query(F.data == "lobby_join")
async def lobby_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name

    if user_id not in lobby:
        lobby.append(user_id)
        get_player(user_id, user_name)
        await callback.answer("Вы вступили в игру!")
    else:
        await callback.answer("Вы уже в списке.", show_alert=True)
    
    await update_lobby_message(callback.message)

@dp.callback_query(F.data == "lobby_leave")
async def lobby_leave(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in lobby:
        lobby.remove(user_id)
        await callback.answer("Вы вышли из очереди.")
    await update_lobby_message(callback.message)

async def update_lobby_message(message: types.Message):
    names = [f"• {players[uid]['name']}" for uid in lobby]
    list_str = "\n".join(names) if names else "Пусто"
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Вступить", callback_data="lobby_join"),
                types.InlineKeyboardButton(text="❌ Выйти", callback_data="lobby_leave"))
    
    # Кнопка старта доступна только создателю
    builder.row(types.InlineKeyboardButton(text="🏁 НАЧАТЬ ИГРУ", callback_data="game_start_final"))

    await message.edit_text(
        f"📝 **Сбор игроков** (Минимум 2):\n\n{list_str}\n\nВсего: {len(lobby)}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# --- ПРОВЕРКА НАЖАТИЙ (Только создатель) ---

@dp.callback_query()
async def global_callbacks(callback: types.CallbackQuery):
    global game_started
    
    # Если нажимает не тот, кто вызвал /monopoly, и это не кнопки входа в лобби
    if callback.from_user.id != creator_id and callback.data not in ["lobby_join", "lobby_leave"]:
        await callback.answer("Это меню другого игрока!", show_alert=True)
        return

    # Обработка инфо-кнопок
    if callback.data == "info_rules":
        await callback.message.answer("Правила: Ходите по очереди (/go), покупайте улицы, берите аренду. Цель - обанкротить других.")
    elif callback.data == "info_dev":
        await callback.message.answer("Разработчик: [Твоё Имя/Ник]")
    elif callback.data == "info_bot":
        await callback.message.answer("Бот для игры в Монополию. Используйте кнопки под сообщениями для действий.")

    # Старт игры
    elif callback.data == "game_start_final":
        if len(lobby) < 2:
            await callback.answer("Нужно минимум 2 игрока!", show_alert=True)
        else:
            game_started = True
            await callback.message.answer("🎲 ИГРА НАЧАЛАСЬ! Используйте /go для хода.")
            await callback.message.delete()

# --- МЕХАНИКА ХОДА ---

@dp.message(Command("go"))
async def cmd_go(message: types.Message):
    if not game_started or message.from_user.id not in lobby:
        await message.answer("Вы не в игре или игра еще не началась.")
        return

    p = players[message.from_user.id]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    field = BOARD[p["position"]]
    
    text = f"🎲 {p['name']} выкинул {dice} и встал на **{field['name']}**"
    builder = InlineKeyboardBuilder()

    if field["price"] > 0:
        owner = next((uid for uid, pl in players.items() if p["position"] in pl["properties"]), None)
        if not owner:
            text += f"\nЦена: {field['price']}$"
            builder.button(text="Купить", callback_data=f"buy_{p['position']}")
        elif owner != message.from_user.id:
            rent = field["rent"]
            p["balance"] -= rent
            players[owner]["balance"] += rent
            text += f"\nЗаплачена аренда {rent}$ игроку {players[owner]['name']}"

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

# --- СЛУЖЕБНЫЙ КОД ---
async def handle_hc(request): return web.Response(text="OK")
async def main():
    app = web.Application()
    app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    asyncio.create_task(web.TCPSite(runner, "0.0.0.0", PORT).start())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
