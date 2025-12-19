import asyncio, os, time, random
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# --- 1. НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))
CORE_ID = random.randint(1000, 9999) 

# --- 2. ДАННЫЕ ИГРЫ ---
players = {}  # Хранилище: {user_id: {balance, position, name}}
MAP_SIZE = 20 # Количество клеток на карте

# --- 3. ВЕБ-ЗАГЛУШКА ДЛЯ RENDER ---
app = Flask(__name__)
@app.route('/')
def home():
    return f"MONOPOLY CORE: {CORE_ID} | PLAYERS: {len(players)} | STATUS: OK"

def run_web():
    app.run(host='0.0.0.0', port=PORT)

# --- 4. КЛАВИАТУРА ---
def get_main_kb():
    buttons = [
        [types.KeyboardButton(text="🎲 Бросить кубик")],
        [types.KeyboardButton(text="💰 Мой баланс"), types.KeyboardButton(text="📍 Где я?")],
        [types.KeyboardButton(text="🏆 Топ игроков")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- 5. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def start_cmd(m: types.Message):
    user_id = m.from_user.id
    if user_id not in players:
        players[user_id] = {
            "balance": 1500, 
            "position": 0, 
            "name": m.from_user.first_name
        }
    
    await m.answer(
        f"🎩 **ДОБРО ПОЖАЛОВАТЬ В МОНОПОЛИЮ!**\n\n"
        f"Ваш ID сессии: `{CORE_ID}`\n"
        f"Стартовый капитал: `1500$`\n\n"
        f"Нажимайте на кнопки, чтобы начать движение!",
        reply_markup=get_main_kb()
    )

# Бросок кубика
@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice(m: types.Message):
    user_id = m.from_user.id
    if user_id not in players:
        return await m.answer("Сначала напишите /start")

    # Имитация броска
    dice = random.randint(1, 6)
    old_pos = players[user_id]["position"]
    new_pos = (old_pos + dice) % MAP_SIZE
    players[user_id]["position"] = new_pos

    # Бонус за прохождение круга
    msg = f"🎲 Выпало: **{dice}**\n\n"
    if new_pos < old_pos:
        players[user_id]["balance"] += 200
        msg += "💰 Вы прошли через старт и получили **200$**!\n"

    msg += f"📍 Вы переместились на клетку **{new_pos}**."
    await m.answer(msg)

# Проверка баланса
@dp.message(F.text == "💰 Мой баланс")
async def check_balance(m: types.Message):
    user_id = m.from_user.id
    if user_id in players:
        await m.answer(f"💵 Ваш счет: `{players[user_id]['balance']}$`")

# Где я?
@dp.message(F.text == "📍 Где я?")
async def where_am_i(m: types.Message):
    user_id = m.from_user.id
    if user_id in players:
        pos = players[user_id]["position"]
        await m.answer(f"🚩 Ваша текущая позиция: клетка **{pos}** из {MAP_SIZE}")

# --- 6. ЗАПУСК ---
async def main():
    # Очистка старых обновлений
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск Flask в фоне
    Thread(target=run_web, daemon=True).start()
    
    print(f"--- СИСТЕМА ЗАПУЩЕНА (ID: {CORE_ID}) ---")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ошибка: {e}")
