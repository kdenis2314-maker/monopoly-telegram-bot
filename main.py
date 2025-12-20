import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAHt8yXQs0OruAZppA62feT1riAKMwDr6j8"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Данные
players = {} 
owners = {}   
lobby = []
lobby_active = False
game_started = False

# Поля (9 клеток для баланса списка)
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

# Ссылка на твою зелено-черную картинку
START_IMAGE = "https://files.oaiusercontent.com/file-m7iKqQvEPrT4YV89U4x8zS?se=2024-10-31T12%3A58%3A39Z&sp=r&sv=2024-08-04&sr=b&rscc=max-age%3D604800%2C%20immutable%2C%20private&rscd=attachment%3B%20filename%3D16912384-2394-4d8e-948f-398457239.webp&sig=some_signature" 
# Примечание: Если ссылка выше временная, замени её на постоянную (например, загрузи на ImgBB)

# --- ОТРИСОВКА СПИСКА ---
def render_list_map(current_user_id):
    map_lines = ["📍 **КАРТА ИГРОКОВ:**\n"]
    for i, cell in enumerate(BOARD):
        # Метки игроков
        m_list = []
        for uid, p_data in players.items():
            if p_data["position"] == i:
                m_list.append("📍 **ВЫ**" if uid == current_user_id else f"👤 {p_data['name']}")
        
        markers = " ".join(m_list)
        
        # Статус
        if cell["price"] == 0: status = "—"
        elif i in owners: status = f"👤 {players[owners[i]]['name']}"
        else: status = f"💰 {cell['price']}$"
            
        map_lines.append(f"{cell['name']} — `[{status}]` {markers}")
        
    map_lines.append(f"\n💵 Твой баланс: `{players[current_user_id]['balance']}$`")
    return "\n".join(map_lines)

# --- КОМАНДЫ ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏁 Начать сбор игроков", callback_data="start_lobby"))
    builder.row(types.InlineKeyboardButton(text="🚀 Поделиться", switch_inline_query="Го в Монополию!"))
    builder.row(
        types.InlineKeyboardButton(text="📜 Правила", callback_data="info_rules"),
        types.InlineKeyboardButton(text="👨‍💻 О девелопере", callback_data="info_dev")
    )
    
    # Отправляем зелено-черный арт
    await message.answer_photo(
        photo="https://i.ibb.co/v4m0YmH/monopoly-start.jpg", # Запасная ссылка на похожий арт
        caption="💎 **M O N O P O L Y**\n\nДобро пожаловать в игру для чата **Shit daily**!",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "start_lobby")
async def start_lobby(c: types.CallbackQuery):
    global lobby_active, lobby, game_started
    if lobby_active: return await c.answer("Сбор уже идет!")
    
    lobby, lobby_active, game_started = [], True, False
    kb = InlineKeyboardBuilder().button(text="✅ Вступить в игру", callback_data="join").as_markup()
    
    await c.message.answer("⏳ **СБОР ИГРОКОВ ОТКРЫТ!**\nУ вас есть 3 минуты.", reply_markup=kb)
    asyncio.create_task(timer_3min(c.message.chat.id))

async def timer_3min(chat_id):
    global lobby_active, game_started
    await asyncio.sleep(180) # 3 минуты
    lobby_active = False
    if len(lobby) >= 2:
        game_started = True
        kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
        await bot.send_message(chat_id, "🎮 **ИГРА НАЧАЛАСЬ!**\nПервый игрок, бросайте кубик!", reply_markup=kb)
    else:
        await bot.send_message(chat_id, "❌ Сбор отменен: нужно минимум 2 игрока.")

@dp.callback_query(F.data == "join")
async def join_game(c: types.CallbackQuery):
    if c.from_user.id not in lobby:
        lobby.append(c.from_user.id)
        players[c.from_user.id] = {"name": c.from_user.first_name, "balance": 1000, "position": 0}
        await c.answer("Вы добавлены!")
    else: await c.answer("Вы уже в игре.")

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    uid = m.from_user.id
    if not game_started or uid not in players: return
    
    p = players[uid]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    
    cell = BOARD[p["position"]]
    kb = InlineKeyboardBuilder()
    res_text = f"🎲 Выпало: **{dice}**\n\n"
    
    if p["position"] in owners and owners[p["position"]] != uid:
        rent = cell["rent"]
        p["balance"] -= rent
        players[owners[p["position"]]]["balance"] += rent
        res_text += f"💸 Вы заплатили {rent}$ за аренду!\n"
    elif cell["price"] > 0 and p["position"] not in owners:
        kb.button(text=f"🛒 Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")

    await m.answer(res_text + render_list_map(uid), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    p = players[c.from_user.id]
    if p["balance"] >= BOARD[idx]["price"]:
        p["balance"] -= BOARD[idx]["price"]
        owners[idx] = c.from_user.id
        await c.message.edit_text(f"✅ Успешная покупка!\n\n" + render_list_map(c.from_user.id), parse_mode="Markdown")
    else: await c.answer("Недостаточно средств!")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
