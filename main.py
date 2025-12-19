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
    {"name": "🚩 СТАРТ (Вход +200$)", "price": 0},
    {"name": "🏘️ Улица Мира", "price": 100},
    {"name": "💸 Налог (-100$)", "price": 0},
    {"name": "🏢 Пр-т Ленина", "price": 150},
    {"name": "🛒 Магазин", "price": 200},
    {"name": "👮 Тюрьма (Отдых)", "price": 0},
    {"name": "🏨 Отель 'Гранд'", "price": 300},
    {"name": "🌳 Парк Культуры", "price": 120},
    {"name": "🚉 Вокзал", "price": 250},
    {"name": "🏛️ Рынок", "price": 180},
    {"name": "💎 Алмазный Фонд", "price": 400},
    {"name": "🎡 Цирк", "price": 140}
]
MAP_SIZE = len(BOARD)

players = {} 

# --- 4. ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)
@app.route('/')
def home():
    return f"MONOPOLY ONLINE | PLAYERS: {len(players)}"

def run_web():
    app.run(host='0.0.0.0', port=PORT)

# --- 5. КЛАВИАТУРА ---
def get_main_kb():
    buttons = [
        [types.KeyboardButton(text="🎲 Бросить кубик")],
        [types.KeyboardButton(text="💰 Баланс"), types.KeyboardButton(text="🏠 Моё имущество")],
        [types.KeyboardButton(text="📍 Где я?"), types.KeyboardButton(text="🏆 Топ")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- 6. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

def is_group(m: Message):
    return m.chat.type in ["group", "supergroup"]

@dp.message(Command("start"))
async def start_cmd(m: Message):
    if not is_group(m):
        return await m.answer("⚠️ **Игра доступна только в группах!**\nДобавьте бота в чат с друзьями, чтобы начать соревнование.")
    
    uid = m.from_user.id
    if uid not in players:
        players[uid] = {
            "balance": 1500, 
            "pos": 0, 
            "name": m.from_user.first_name, 
            "owns": []
        }
        await m.answer(f"✅ **{m.from_user.first_name}** вступил в игру!\nСтартовый капитал: `1500$`", reply_markup=get_main_kb())
    else:
        await m.answer(f"💎 **{m.from_user.first_name}**, вы уже в игре!", reply_markup=get_main_kb())

@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice(m: Message):
    if not is_group(m): return
    uid = m.from_user.id
    if uid not in players:
        return await m.answer("Нажми /start, чтобы участвовать!")

    steps = random.randint(1, 6)
    old_pos = players[uid]["pos"]
    new_pos = (old_pos + steps) % MAP_SIZE
    players[uid]["pos"] = new_pos

    cell = BOARD[new_pos]
    res = f"👤 *{m.from_user.first_name}*\n🎲 Выпало: **{steps}**\n📍 Клетка: **{cell['name']}**\n"

    if new_pos < old_pos:
        players[uid]["balance"] += 200
        res += "🎁 +200$ за прохождение круга!\n"

    if cell['name'] == "💸 Налог (-100$)":
        players[uid]["balance"] -= 100
        res += "💸 Вы заплатили налог **100$**."
    elif cell['price'] > 0:
        owner_id = next((pid for pid, pdata in players.items() if new_pos in pdata['owns']), None)
        if owner_id is None:
            if players[uid]['balance'] >= cell['price']:
                players[uid]['balance'] -= cell['price']
                players[uid]['owns'].append(new_pos)
                res += f"💳 Вы купили этот объект за **{cell['price']}$**!"
            else:
                res += f"❌ Недостаточно средств для покупки (**{cell['price']}$**)"
        elif owner_id == uid:
            res += "🏠 Это ваша собственность."
        else:
            rent = cell['price'] // 2
            players[uid]['balance'] -= rent
            players[owner_id]['balance'] += rent
            res += f"⚠️ Вы попали на чужое поле! Оплата аренды: **{rent}$** игроку {players[owner_id]['name']}."

    await m.answer(res)

@dp.message(F.text == "💰 Баланс")
async def check_balance(m: Message):
    if not is_group(m): return
    p = players.get(m.from_user.id)
    if p:
        await m.answer(f"👤 *{p['name']}*\n💵 Баланс: `{p['balance']}$`")

@dp.message(F.text == "📍 Где я?")
async def where_am_i(m: Message):
    if not is_group(m): return
    p = players.get(m.from_user.id)
    if p:
        cell = BOARD[p['pos']]
        await m.answer(f"👤 *{p['name']}*\n📍 Позиция: **{cell['name']}** (Клетка {p['pos']})")

@dp.message(F.text == "🏠 Моё имущество")
async def my_props(m: Message):
    if not is_group(m): return
    p = players.get(m.from_user.id)
    if p:
        if p['owns']:
            prop_list = "\n".join([f"— {BOARD[i]['name']}" for i in p['owns']])
            await m.answer(f"👤 *{p['name']}*\n🏢 Ваше имущество:\n{prop_list}")
        else:
            await m.answer(f"👤 *{p['name']}*\n🏢 У вас пока нет имущества.")

# --- 7. ЗАПУСК ---
async def main():
    # Запускаем Flask в отдельном потоке
    Thread(target=run_web, daemon=True).start()
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
