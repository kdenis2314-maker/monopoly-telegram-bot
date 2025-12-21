import os, asyncio, aiosqlite, logging, random
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, URLInputFile

# --- [1] ЯДРО ПРИНЦА ---
API_TOKEN = os.getenv("BOT_TOKEN") or "ТВОЙ_ТОКЕН"
IS_ACTIVE = True 
MAINTENANCE_MSG = "Темный принц правит код... ♥️"
DEV_TAG = "@Whylovely05"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- [2] ЛОГИКА ТЮРЬМЫ И ШАНСА ---
# Клетки Шанса: 2, 7, 17, 22, 33, 36
CHANCE_CARDS = [
    ("Налоговый возврат! +$150", 150),
    ("Штраф за превышение скорости! -$50", -50),
    ("Ты нашел заначку Принца! +$200", 200),
    ("Оплата страховки... -$100", -100)
]

# --- [3] БАЗА ДАННЫХ (Расширенная) ---
async def init_db():
    async with aiosqlite.connect('monopoly_v6.db') as db:
        # jail_turns: сколько ходов осталось сидеть (0 - свободен)
        await db.execute("""CREATE TABLE IF NOT EXISTS players (
            chat_id int, user_id int, name text, 
            balance int DEFAULT 1500, pos int DEFAULT 0, 
            jail_turns int DEFAULT 0, PRIMARY KEY(chat_id, user_id))""")
        await db.execute("CREATE TABLE IF NOT EXISTS property (chat_id int, cell_idx int, owner_id int, PRIMARY KEY(chat_id, cell_idx))")
        await db.commit()

# --- [4] ИИ-ВЕДУЩИЙ (БЕЗ ПОДСКАЗОК) ---
async def ai_comment(event, name):
    phrases = {
        "to_jail": [f"🚔 {name}, допрыгался! Тюрьмыч ждет тебя.", f"⛓ {name}, наручники сидят на тебе отлично. Присядь на 3 хода.", f"👮‍♂️ Опа, {name}, проедемте! Срок 3 хода."],
        "out_jail": [f"🕊 {name} на свободе с чистой совестью!", f"🔓 {name} откинулся. С возвращением в бизнес!", f"🚶 {name} вышел по УДО. Попробуй не сесть снова."],
        "auction": [f"🔨 ЛОТ НА ТОРГАХ! Кто даст больше?", f"📢 Аукцион! Ставки, господа!", f"💰 Жадность — это хорошо! Погнали торги!"],
        "chance": [f"🎰 Судьба играет с {name}...", f"🃏 Что там в картах Шанса для {name}?", f"🎲 Рандом — бог Монополии! Смотрим..."]
    }
    return random.choice(phrases.get(event, ["Ход продолжается..."]))

# --- [5] ОСНОВНАЯ ИГРОВАЯ ЛОГИКА ---
@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice(m: types.Message):
    if not IS_ACTIVE: return await m.answer(MAINTENANCE_MSG)
    
    async with aiosqlite.connect('monopoly_v6.db') as db:
        res = await db.execute("SELECT pos, balance, jail_turns FROM players WHERE user_id=? AND chat_id=?", (m.from_user.id, m.chat.id))
        p = await res.fetchone()
        if not p: return await m.answer("Вступи в игру! /monopoly")

        # Проверка тюрьмы
        if p[2] > 0:
            new_jail = p[2] - 1
            await db.execute("UPDATE players SET jail_turns=? WHERE user_id=?", (new_jail, m.from_user.id))
            await db.commit()
            return await m.answer(f"⛓ Ты в Тюрьмыче! Осталось сидеть: {new_jail} хода(ов).")

        dice = await m.answer_dice("🎲")
        await asyncio.sleep(3.5)
        
        new_pos = (p[0] + dice.dice.value) % 40
        
        # ЛОГИКА ТЮРЬМЫ (Клетка 30 - Отправляйся в тюрьму)
        if new_pos == 30:
            await db.execute("UPDATE players SET pos=10, jail_turns=3 WHERE user_id=?", (m.from_user.id,))
            await db.commit()
            return await m.answer(await ai_comment("to_jail", m.from_user.first_name))

        # ЛОГИКА ШАНСА
        if new_pos in [2, 7, 17, 22, 33, 36]:
            txt, val = random.choice(CHANCE_CARDS)
            await db.execute("UPDATE players SET balance = balance + ?, pos=? WHERE user_id=?", (val, new_pos, m.from_user.id))
            await db.commit()
            await m.answer(await ai_comment("chance", m.from_user.first_name))
            return await m.answer(f"🃏 {txt}")

        # ЛОГИКА АУКЦИОНА (Если клетка свободна)
        # Здесь мы предлагаем: Купить или запустить Аукцион
        await db.execute("UPDATE players SET pos=? WHERE user_id=?", (new_pos, m.from_user.id))
        await db.commit()
        
        kb = InlineKeyboardBuilder()
        kb.button(text="💰 Купить", callback_data=f"buy_{new_pos}")
        kb.button(text="🔨 Аукцион", callback_data=f"auc_{new_pos}")
        await m.answer(f"📍 Ты на клетке {new_pos}. Что делаем?", reply_markup=kb.as_markup())

# --- [6] АУКЦИОН ---
@dp.callback_query(F.data.startswith("auc_"))
async def start_auc(c: types.CallbackQuery):
    await c.answer()
    cell_idx = c.data.split("_")[1]
    await c.message.answer(f"{await ai_comment('auction', '')}\nЛот: Клетка №{cell_idx}\nНачальная цена: $10. Пишите ставки в чат!")

# --- [7] ЗАПУСК ---
async def main():
    await init_db()
    Thread(target=lambda: app.run(host="0.0.0.0", port=8083), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
