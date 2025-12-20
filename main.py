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

# Ссылки на картинки
IMG_START = "https://i.ibb.co/v4m0YmH/monopoly-start.jpg"
IMG_LOBBY = "https://i.ibb.co/0fX9G9g/monopoly-lobby.jpg"

# Поле игры
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

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_lobby_content():
    """Генерирует текст и кнопки для лобби."""
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
    """Рисует текущую карту и указывает, чей ход."""
    curr_uid = lobby[current_turn_index]
    turn_name = players[curr_uid]['name']
    
    lines = [f"🎲 **СЕЙЧАС ХОДИТ:** {turn_name}\n", "📍 **КАРТА:**\n"]
    for i, cell in enumerate(BOARD):
        m_list = []
        for pid, pdata in players.items():
            if pdata["position"] == i:
                m_list.append("📍 **ВЫ**" if pid == uid else f"👤 {pdata['name']}")
        
        markers = " ".join(m_list)
        if cell["price"] == 0:
            status = "—"
        elif i in owners:
            status = f"🏠 {players[owners[i]]['name']}"
        else:
            status = f"💰 {cell['price']}$"
            
        lines.append(f"{cell['name']} — `[{status}]` {markers}")
    
    lines.append(f"\n💵 Баланс: `{players[uid]['balance']}$`")
    return "\n".join(lines)

# --- WEB СЕРВЕР ДЛЯ RENDER ---

async def handle(request): return web.Response(text="Bot is Live")
async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: types.Message):
    if lobby_active or game_started:
        return await m.answer("⚠️ Игра уже идет или собирается!")
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🏁 Начать сбор", callback_data="start_lobby"))
    await m.answer_photo(photo=IMG_START, caption="💎 **M O N O P O L Y**\nНажми кнопку, чтобы собрать команду!", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_lobby")
async def lobby_start(c: types.CallbackQuery):
    global lobby_active, lobby, game_started, organizer_id, current_turn_index
    if lobby_active: return await c.answer("Сбор уже запущен!")
    
    lobby_active, game_started, current_turn_index = True, False, 0
    organizer_id = c.from_user.id
    lobby = [organizer_id]
    players[organizer_id] = {"name": c.from_user.first_name[:10], "balance": 1000, "position": 0}
    
    text, kb = get_lobby_content()
    await c.message.answer_photo(photo=IMG_LOBBY, caption=text, reply_markup=kb)
    await c.message.delete()
    
    asyncio.create_task(timer_task(c.message.chat.id))
    await c.answer()

async def timer_task(chat_id):
    """Таймер на 3 минуты."""
    await asyncio.sleep(180) 
    if lobby_active: 
        await start_game_logic(chat_id)

async def start_game_logic(chat_id):
    global lobby_active, game_started, current_turn_index
    if not lobby_active: return 
    
    if len(lobby) < 2:
        lobby_active = False
        players.clear()
        lobby.clear()
        return await bot.send_message(chat_id, "❌ **Сбор отменен:** недостаточно игроков (нужно минимум 2).")
    
    lobby_active = False
    game_started = True
    current_turn_index = 0
    
    kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
    first_name = players[lobby[0]]['name']
    await bot.send_message(chat_id, f"🎮 **ИГРА НАЧАЛАСЬ!**\nПервым ходит: **{first_name}**", reply_markup=kb)

@dp.callback_query(F.data == "join")
async def join(c: types.CallbackQuery):
    if not lobby_active: return
    if c.from_user.id not in lobby:
        lobby.append(c.from_user.id)
        players[c.from_user.id] = {"name": c.from_user.first_name[:10], "balance": 1000, "position": 0}
        text, kb = get_lobby_content()
        await c.message.edit_caption(caption=text, reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "leave")
async def leave(c: types.CallbackQuery):
    if c.from_user.id == organizer_id:
        return await c.answer("Организатор не может выйти!", show_alert=True)
    if c.from_user.id in lobby:
        lobby.remove(c.from_user.id)
        players.pop(c.from_user.id, None)
        text, kb = get_lobby_content()
        await c.message.edit_caption(caption=text, reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "force_start")
async def force_start(c: types.CallbackQuery):
    if c.from_user.id != organizer_id:
        return await c.answer("Только организатор может начать раньше!", show_alert=True)
    if len(lobby) < 2:
        return await c.answer("Нужно минимум 2 игрока!", show_alert=True)
    await start_game_logic(c.message.chat.id)
    await c.answer()

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    global current_turn_index
    uid = m.from_user.id
    if not game_started or uid not in players: return

    # Проверка очереди
    if uid != lobby[current_turn_index]:
        wait_for = players[lobby[current_turn_index]]['name']
        return await m.reply(f"⏳ Не твой ход! Сейчас очередь **{wait_for}**.")

    p = players[uid]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    cell = BOARD[p["position"]]
    
    res_text = f"🎲 **{p['name']}** выбросил: {dice}\nНа клетку: {cell['name']}\n"
    kb = InlineKeyboardBuilder()
    
    # Аренда
    if p["position"] in owners and owners[p["position"]] != uid:
        rent = cell["rent"]
        p["balance"] -= rent
        players[owners[p["position"]]]["balance"] += rent
        res_text += f"💸 Оплачена аренда: {rent}$ игроку {players[owners[p['position']]]['name']}\n"
    # Покупка
    elif cell["price"] > 0 and p["position"] not in owners:
        kb.button(text=f"🛒 Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")
    
    # Смена хода
    current_turn_index = (current_turn_index + 1) % len(lobby)
    
    await m.answer(res_text + "\n" + render_list_map(uid), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    uid = c.from_user.id
    if players[uid]["balance"] >= BOARD[idx]["price"]:
        players[uid]["balance"] -= BOARD[idx]["price"]
        owners[idx] = uid
        await c.message.edit_text(f"✅ Успешно куплено!\n\n" + render_list_map(uid), parse_mode="Markdown")
    else:
        await c.answer("Недостаточно денег!", show_alert=True)

# --- ЗАПУСК ---
async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
