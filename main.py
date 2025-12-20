import asyncio
import logging
import random
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
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
lobby_active = False

def get_player(user_id, name):
    if user_id not in players:
        players[user_id] = {"name": name, "balance": 1000, "position": 0, "properties": []}
    return players[user_id]

# --- ЛОГИКА СБОРА ИГРОКОВ ---

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    builder = InlineKeyboardBuilder()
    # Кнопка поделиться (открывает выбор чата)
    builder.row(types.InlineKeyboardButton(
        text="🚀 Поделиться с друзьями", 
        switch_inline_query="Сыграем в Монополию в чате Shit daily!")
    )
    builder.row(types.InlineKeyboardButton(text="➡️ Начать сбор участников", callback_data="start_lobby_timer"))
    
    await message.answer(
        "✨ **M O N O P O L Y** ✨\n\nСделайте шаг навстречу империи!",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "start_lobby_timer")
async def start_lobby_handler(callback: types.CallbackQuery):
    global lobby_active, lobby, game_started
    if lobby_active:
        return await callback.answer("Сбор уже идет!")
    
    lobby = []
    game_started = False
    lobby_active = True
    
    # Первое сообщение сбора
    msg = await callback.message.answer("⏳ **Сбор игроков начат!**\nУ вас есть 3 минуты, чтобы вступить.")
    try:
        await bot.pin_chat_message(callback.message.chat.id, msg.message_id)
    except: pass # Если нет прав на закреп

    # Запускаем цикл на 3 минуты (180 секунд)
    asyncio.create_task(lobby_lifecycle(callback.message.chat.id, msg.message_id))
    await callback.answer()

async def lobby_lifecycle(chat_id, initial_msg_id):
    global lobby_active, game_started
    
    for i in range(6): # 6 циклов по 30 секунд = 3 минуты
        if not lobby_active: break
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Присоединиться", callback_data="lobby_join")
        
        names = "\n".join([f"🔹 {players[uid]['name']}" for uid in lobby]) or "_Пока никого нет..._"
        text = f"📝 **СПИСОК УЧАСТНИКОВ:**\n\n{names}\n\n⏱ До начала: {3 - (i*0.5)} мин."
        
        # Каждые 30 секунд шлем новое сообщение
        sent_msg = await bot.send_message(chat_id, text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        
        await asyncio.sleep(30)
        # Удаляем старое напоминание, чтобы не спамить вечно (опционально)
        # try: await bot.delete_message(chat_id, sent_msg.message_id) except: pass

    # ФИНАЛ СБОРА
    lobby_active = False
    try: await bot.unpin_chat_message(chat_id, initial_msg_id) 
    except: pass

    if len(lobby) >= 2:
        game_started = True
        await bot.send_message(chat_id, "🎮 **Время вышло! Игра начинается!**\nИспользуйте меню или /go для хода.")
    else:
        await bot.send_message(chat_id, "❌ **Сбор отменен.** Недостаточно игроков для начала игры.")
        lobby.clear()

@dp.callback_query(F.data == "lobby_join")
async def lobby_join(callback: types.CallbackQuery):
    if not lobby_active:
        return await callback.answer("Сбор уже окончен.")
    if callback.from_user.id not in lobby:
        lobby.append(callback.from_user.id)
        get_player(callback.from_user.id, callback.from_user.first_name)
        await callback.answer("Вы в игре!")
    else:
        await callback.answer("Вы уже записаны.")

# --- ОСТАЛЬНАЯ ЛОГИКА (ХОД И КАРТА) ИЗ ПРОШЛОГО КОДА ---
# (Тут остаются твои функции /go, /menu, draw_visual_map и т.д.)

# --- СЕРВЕР ---
async def handle_hc(r): return web.Response(text="OK")
async def main():
    asyncio.create_task(web.TCPSite(web.AppRunner(web.Application()).setup(), "0.0.0.0", PORT).start())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
