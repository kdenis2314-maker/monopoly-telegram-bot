import asyncio
import logging
import os
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

# --- СЕКЦИЯ ДЛЯ RENDER (ЧТОБЫ НЕ ЗАСЫПАЛ) ---
app = Flask('')
@app.route('/')
def home(): return "Бот работает стабильно!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ЛОГИКА БОТА ---
# Вставь свой токен сюда
TOKEN = "ТВОЙ_ТОКЕН_ЗДЕСЬ"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Генератор клавиатуры для главного меню
def main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎮 Играть", callback_data="play"),
                InlineKeyboardButton(text="💰 Баланс", callback_data="balance"))
    builder.row(InlineKeyboardButton(text="🏆 Лидеры", callback_data="top"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"))
    builder.row(InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        f"🌟 **Добро пожаловать, {message.from_user.first_name}!**\n\n"
        "Это твоя личная панель управления Monopoly. "
        "Используй кнопки ниже, чтобы начать приключение.",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "balance")
async def show_balance(call: types.CallbackQuery):
    # Эффект "загрузки" или перехода
    await call.message.edit_text(
        "💵 **Ваш кошелек**\n\n"
        "● Наличные: `$1,250,000`\n"
        "● В активах: `$5,000,000`\n\n"
        "📈 *Ваш доход вырос на 5% за сегодня!*",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query(F.data == "about")
async def about_info(call: types.CallbackQuery):
    await call.message.edit_text(
        "🤖 **Monopoly Bot v2.0**\n\n"
        "Самый быстрый бот на асинхронном движке.\n"
        "Разработано специально для работы на Render.",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )
    await call.answer()

# Запуск
async def main():
    logging.basicConfig(level=logging.INFO)
    keep_alive() # Запускаем веб-сервер
    print(">>> Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print(">>> Бот остановлен")
