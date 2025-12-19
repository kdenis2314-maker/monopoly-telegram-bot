import asyncio, logging, os, sys, time, random
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# --- НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
games, site_logs = {}, []
start_time = time.time()
bot_status = "Инициализация..."

def add_log(msg):
    entry = {"time": time.strftime('%H:%M:%S'), "msg": msg}
    site_logs.append(entry)
    if len(site_logs) > 25: site_logs.pop(0)

# --- КОСМИЧЕСКАЯ ПАНЕЛЬ СОСТОЯНИЯ ---
app = Flask(__name__)
@app.route('/')
def dashboard():
    uptime = int((time.time() - start_time) / 60)
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>SIGMA CORE | ПАНЕЛЬ УПРАВЛЕНИЯ</title>
        <style>
            body { 
                background: radial-gradient(circle, #0a0b1e 0%, #000 100%); 
                color: #00f3ff; font-family: 'Courier New', monospace; margin: 0; padding: 20px;
            }
            .container { max-width: 900px; margin: auto; }
            .header { text-align: center; border: 1px solid #00f3ff; padding: 20px; border-radius: 15px; box-shadow: 0 0 20px #00f3ff33; background: rgba(0,0,0,0.6); }
            .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
            .card { background: rgba(255,255,255,0.03); border: 1px solid #1a2a3a; padding: 15px; border-radius: 10px; text-align: center; position: relative; overflow: hidden; }
            .card::after { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px; background: #00f3ff; box-shadow: 0 0 10px #00f3ff; }
            .online { color: #00ff88; text-shadow: 0 0 10px #00ff88; }
            .value { font-size: 24px; margin-top: 5px; color: #fff; }
            .log-view { margin-top: 20px; height: 300px; overflow-y: auto; background: #000; border: 1px solid #333; padding: 15px; border-radius: 10px; font-size: 13px; }
            .log-line { border-bottom: 1px solid #111; padding: 4px 0; color: #576574; }
            .log-msg { color: #00f3ff; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="letter-spacing: 5px; margin: 0;">🛰️ SIGMA MONOPOLY CORE</h1>
                <p>ЦЕНТРАЛЬНЫЙ УЗЕЛ УПРАВЛЕНИЯ</p>
            </div>
            <div class="status-grid">
                <div class="card"><div>СТАТУС БОТА</div><div class="value online">● АКТИВЕН</div></div>
                <div class="card"><div>ВЕБХУКИ</div><div class="value" style="color:#ffcc00">ОТКЛЮЧЕНЫ</div></div>
                <div class="card"><div>АПТАЙМ</div><div class="value">{{ up }} МИН.</div></div>
                <div class="card"><div>ИГРОВЫЕ ЯДРА</div><div class="value">{{ g_count }}</div></div>
            </div>
            <div class="log-view">
                {% for l in logs %}
                <div class="log-line">[{{ l.time }}] <span class="log-msg">> {{ l.msg }}</span></div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, logs=site_logs[::-1], up=uptime, g_count=len(games))

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def start_game(m: types.Message):
    await m.answer("🌌 **Система монополии запущена в данном секторе.**\nОжидайте инициализации интерфейса...")

# --- ЗАПУСК ---
async def main():
    add_log("ЗАГРУЗКА ПРОТОКОЛОВ СВЯЗИ...")
    
    # Решение ошибки ConflictError
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("ВЕБХУКИ ОЧИЩЕНЫ. ПЕРЕХОД НА LONG POLLING.")
    
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    add_log("АДМИН-ПАНЕЛЬ ДОСТУПНА ПО ПОРТУ " + str(PORT))
    
    try:
        add_log("БОТ ЗАПУЩЕН УСПЕШНО.")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    
