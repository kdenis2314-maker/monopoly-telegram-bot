import asyncio, os, time, random
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message

# --- 1. НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))

# --- 2. КАРТА ИГРЫ ---
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0},
    {"name": "🏘️ Улица Мира", "price": 100},
    {"name": "💸 Налог", "price": 0},
    {"name": "🏢 Пр-т Ленина", "price": 150},
    {"name": "🛒 Магазин", "price": 200},
    {"name": "👮 Тюрьма", "price": 0},
    {"name": "🏨 Отель", "price": 300},
    {"name": "🌳 Парк", "price": 120},
    {"name": "🚉 Вокзал", "price": 250},
    {"name": "🏛️ Рынок", "price": 180}
]
MAP_SIZE = len(BOARD)

# --- 3. ХРАНИЛИЩЕ ДАННЫХ ---
players = {} # {user_id: {balance, pos, name, owns: []}}

# --- 4. ВЕБ-СЕРВЕР ---
app = Flask(__name__)
@app.route('/')
def home(): return "GROUP MONOPOLY IS RUNNING"

# --- 5. КЛАВИАТУРА ---
def get_main_kb():
    buttons = [
        [types.KeyboardButton(text="🎲 Бросить кубик")],
        [types.KeyboardButton(text="💰 Баланс"), types.KeyboardButton(text="🏠 Имущество")],
        [types.KeyboardButton(text="📍 Где я?")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- 6. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

# Фильтр: Проверка, что это группа или супергруппа
def is_group(m: Message):
    return m.chat.type in ["group", "supergroup"]

@dp.message(Command("start"))
async def start_cmd(m: Message):
    if not is_group(m):
        return await m.answer("⚠️ В Монополию можно играть только в группах! Добавь меня в чат с друзьями.")
    
    uid = m.from_user.id
    if uid not in players:
        players[uid] = {"balance": 1500, "pos": 0, "name": m.from_user.first_name, "owns": []}
        await m.answer(f"✅ {m.from_user.first_name} вступил в игру!", reply_markup=get_main_kb())
    else:
        await m.answer(f"💎 {m.from_user.first_name}, ты уже в игре!", reply_markup=get_main_kb())

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: Message):
    if not is_group(m): return
    uid = m.from_user.id
    if uid not in players: 
        return await m.answer(f"@{m.from_user.username}, нажми /start чтобы играть!")
    
    steps = random.randint(1, 6)
    old_pos = players[uid]["pos"]
    new_pos = (old_pos + steps) % MAP_SIZE
    players[uid]["pos"] = new_pos
    
    cell = BOARD[new_pos]
    res = f"👤 *{m.from_user.first_name}*\n🎲 Выпало: **{steps}**\n📍 Клетка: **{cell['name']}**\n"
    
    if cell['price'] > 0:
        # Кто владелец?
        owner_id = next((pid for pid, pdata in players.items() if new_pos in pdata['owns']), None)
        
        if owner_id is None:
            if players[uid]['balance'] >= cell['price']:
                players[uid]['balance'] -= cell['price']
                players[uid]['owns'].append(new_pos)
                res += f"💳 Куплено за **{cell['price']}$**!"
            else:
                res += f"❌ Недостаточно денег ({cell['price']}$)"
        elif owner_id == uid:
            res += "🏠 Твоя недвижимость."
        else:
            rent = cell['price'] // 2
            players[uid]['balance'] -= rent
            players[owner_id]['balance'] += rent
            res += f"⚠️ Штраф! Ты заплатил **{rent}$** игроку {players[owner_id]['name']}."

    await m.answer(res)

@dp.message(F.text == "💰 Баланс")
async def bal(m: Message):
    if not is_group(m): return
    p = players.get(m.from_user.id)
    if p: await m.answer(f"👤 *{p['name']}*\n💵 Твой счет: `{p['balance']}$`")

@dp.message(F.text == "📍 Где я?")
async def where(m: Message):
    if not is_group(m): return
    p = players.get(m.from_user.id)
    if p: await m.answer(f"👤 *{p['name']}*\n🚩 Ты на клетке №{p['pos']}: **{BOARD[p['pos']]['name']}**")

@dp.message(F.text == "🏠 Имущество")
async def owns(m: Message):
    if not is_group(m): return
    p = players.get(m.from_user.id)
    if p and p['owns']:
        items = ", ".join([BOARD[i]['name'] for i in p['owns']])
        await m.answer(f"👤 *{p['name']}*\n🏢 Твои объекты: {items}")
    else:
        await m.answer("🏘️ У тебя пока ничего нет.")

# Запуск
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                              
