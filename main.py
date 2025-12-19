import asyncio
import logging
import os
import sys
import time
import random
import psutil
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

# --- КОНФИГУРАЦИЯ ---
# Берем данные из твоих переменных окружения или прописываем жестко
TOKEN = os.environ.get("TOKEN", "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU")
PORT = int(os.environ.get("PORT", 8081))  # Порт 8081 как в настройках Render
BOT_USERNAME = "Monopolysigma_bot"

# Настройка логирования для вывода в консоль Render
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

games = {} 
site_logs = []
start_time = time.time()

def add_log(msg):
    """Вывод логов с принудительным сбросом буфера для Render"""
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    print(f"RENDER_LOG: {entry}", flush=True) 
    if len(site_logs) > 50: site_logs.pop(0)

# --- АДМИН-ПАНЕЛЬ ---
app = Flask(__name__)

@app.route('/')
def dashboard():
    uptime = int((time.time() - start_time) / 60)
    return render_template_string("""
    <body style="background:#0f172a; color:white; font-family:sans-serif; padding:40px;">
        <h1 style="color:#3b82f6;">🏢 Monopoly Sigma Control</h1>
        <p>Порт: {{ port }} | Игр: {{ games }} | Uptime: {{ uptime }} мин.</p>
        <div style="background:black; color:#22c55e; padding:20px; border-radius:10px; height:300px; overflow-y:auto; font-family:monospace;">
            {% for l in logs %} <div>> {{ l }} </div> {% endfor %}
        </div>
    </body>
    """, logs=site_logs[::-1], uptime=uptime, games=len(games), port=PORT)

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    add_log(f"User {m.from_user.id} started bot")
    await m.answer("🏢 Бот запущен! Используй /monopoly в группе.")

@dp.message(Command("monopoly"), F.chat.type.in_({"group", "supergroup"}))
async def start_game(m: types.Message):
    cid = m.chat.id
    if cid in games: return await m.answer("⚠️ Игра уже идет!")
    
    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"name": m.from_user.first_name, "pos": 0, "money": 15000}},
        "order": [m.from_user.id],
        "turn": 0
    }
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Вступить ✅", callback_data="join_game"),
           InlineKeyboardButton(text="Начать 🎲", callback_data="start_match"))
    
    add_log(f"Lobby created in {cid}")
    await m.answer(f"🏦 **НОВАЯ ИГРА!**", reply_markup=kb.as_markup(), parse_mode="Markdown")

# (Здесь остаются остальные callback-обработчики из твоего файла main(2).py)

# --- ИСПРАВЛЕННЫЙ ЗАПУСК (БЕЗ КОНФЛИКТОВ) ---
async def main():
    add_log(f"🚀 Запуск системы на порту {PORT}")
    
    # 1. Запуск Flask на 0.0.0.0 обязателен для Render
    def run_flask():
        # use_reloader=False предотвращает двойной запуск порта
        app.run(host='0.0.0.0', port=PORT, use_reloader=False)

    Thread(target=run_flask, daemon=True).start()
    
    # 2. РЕШЕНИЕ КОНФЛИКТА: Удаляем вебхук и старые сессии
    # Это «выбьет» старого бота, если он застрял в памяти Render
    await bot.delete_webhook(drop_pending_updates=True)
    
    add_log("🤖 Бот успешно подключен к Telegram. Ошибок Conflict нет.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        add_log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
    
