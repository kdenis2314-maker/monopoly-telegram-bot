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

players = {} 
owners = {}   
lobby = []
lobby_active = False
game_started = False
organizer_id = None
lobby_msg_id = None # ID сообщения для редактирования списка

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
def get_lobby_text():
    names = "\n".join([f"• {players[uid]['name']}" for uid in lobby]) if lobby else "Пока никого нет..."
    return f"⏳ **СБОР ИГРОКОВ (3 МИНУТЫ)**\n\n**Вошли в игру:**\n{names}\n\nОрганизатор может начать игру раньше."

def get_lobby_kb():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Вступить", callback_data="join"),
           types.InlineKeyboardButton(text="❌ Выйти", callback_data="leave"))
    kb.row(types.InlineKeyboardButton(text="🚀 Начать игру", callback_data="force_start"))
    return kb.as_markup()

def render_list_map(uid):
    lines = ["📍 **ТЕКУЩАЯ КАРТА:**\n"]
    for i, cell in enumerate(BOARD):
        m = [("📍 **ВЫ**" if k == uid else f"👤 {v['name']}") for k, v in players.items() if v["position"] == i]
        status = "—" if cell["price"] == 0 else (f"👤 {players[owners[i]]['name']}" if i in owners else f"💰 {cell['price']}$")
        lines.append(f"{cell['name']} — `[{status}]` {' '.join(m)}")
    lines.append(f"\n💵 Баланс: `{players[uid]['balance']}$`")
    return "\n".join(lines)

# --- WEB СЕРВЕР ---
async def handle(request): return web.Response(text="Бот запущен!")
async def start_web_server():
    app = web.Application(); app.router.add_get('/', handle)
    runner = web.AppRunner(app); await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()

# --- КОМАНДЫ ---
@dp.message(Command("monopoly"))
async def cmd_monopoly(m: types.Message):
    if lobby_active or game_started: return await m.answer("⚠️ Игра уже идет!")
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🏁 Начать сбор", callback_data="start_lobby"))
    kb.row(types.InlineKeyboardButton(text="📜 Правила", callback_data="rules"),
           types.InlineKeyboardButton(text="👨‍💻 Девелопер", callback_data="dev"))
    
    try:
        await m.answer_photo(photo="https://i.ibb.co/v4m0YmH/monopoly-start.jpg", 
                             caption="💎 **M O N O P O L Y**\nНажми кнопку ниже, чтобы собрать игроков.", 
                             reply_markup=kb.as_markup())
    except:
        await m.answer("💎 **M O N O P O L Y**\nНажми кнопку ниже.", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_lobby")
async def lobby_start(c: types.CallbackQuery):
    global lobby_active, lobby, game_started, organizer_id, lobby_msg_id
    if lobby_active: return await c.answer("Сбор уже идет!", show_alert=True)
    
    lobby_active, game_started = True, False
    organizer_id = c.from_user.id
    lobby = [organizer_id] # Организатор заходит первым автоматически
    players[organizer_id] = {"name": c.from_user.first_name[:10], "balance": 1000, "position": 0}
    
    try:
        msg = await c.message.answer_photo(photo="https://i.ibb.co/0fX9G9g/monopoly-lobby.jpg", 
                                           caption=get_lobby_text(), reply_markup=get_lobby_kb())
        lobby_msg_id = msg.message_id
        await c.message.delete()
    except:
        msg = await c.message.answer(get_lobby_text(), reply_markup=get_lobby_kb())
        lobby_msg_id = msg.message_id
    
    asyncio.create_task(auto_timer(c.message.chat.id))

async def auto_timer(chat_id):
    await asyncio.sleep(180)
    if lobby_active: await start_game_logic(chat_id)

async def start_game_logic(chat_id):
    global lobby_active, game_started
    if not lobby_active: return
    lobby_active = False
    if len(lobby) >= 2:
        game_started = True
        kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
        await bot.send_message(chat_id, "🎮 **ИГРА НАЧАЛАСЬ!**\nБросайте кубик!", reply_markup=kb)
    else:
        await bot.send_message(chat_id, "❌ Сбор отменен: нужно минимум 2 игрока.")

@dp.callback_query(F.data == "join")
async def join(c: types.CallbackQuery):
    if c.from_user.id not in lobby:
        lobby.append(c.from_user.id)
        players[c.from_user.id] = {"name": c.from_user.first_name[:10], "balance": 1000, "position": 0}
        await c.message.edit_caption(caption=get_lobby_text(), reply_markup=get_lobby_kb())
    await c.answer()

@dp.callback_query(F.data == "leave")
async def leave(c: types.CallbackQuery):
    if c.from_user.id == organizer_id:
        return await c.answer("Организатор не может выйти!", show_alert=True)
    if c.from_user.id in lobby:
        lobby.remove(c.from_user.id)
        players.pop(c.from_user.id, None)
        await c.message.edit_caption(caption=get_lobby_text(), reply_markup=get_lobby_kb())
    await c.answer()

@dp.callback_query(F.data == "force_start")
async def force_start(c: types.CallbackQuery):
    if c.from_user.id != organizer_id:
        return await c.answer("Только организатор может запустить игру!", show_alert=True)
    if len(lobby) < 2:
        return await c.answer("Нужно хотя бы 2 игрока!", show_alert=True)
    await start_game_logic(c.message.chat.id)
    await c.answer()

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
        p["balance"] -= rent; players[owners[p["position"]]]["balance"] += rent
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

async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
