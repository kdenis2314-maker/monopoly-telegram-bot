import asyncio, logging, os, sys, time, random, psutil
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
games, site_logs = {}, []
start_time = time.time()

def add_log(msg):
    entry = {"time": time.strftime('%H:%M:%S'), "msg": msg}
    site_logs.append(entry)
    if len(site_logs) > 15: site_logs.pop(0)

# --- ИНФОРМАТИВНАЯ АДМИН-ПАНЕЛЬ ---
app = Flask(__name__)
@app.route('/')
def dashboard():
    mem = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>GALAXY ADMIN</title>
        <style>
            body { background: #020205; color: #00f3ff; font-family: 'Segoe UI', sans-serif; padding: 20px; }
            .panel { border: 2px solid #00f3ff; border-radius: 20px; padding: 25px; background: rgba(0, 10, 20, 0.8); box-shadow: 0 0 30px #00f3ff44; }
            .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
            .card { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; border-left: 5px solid #00f3ff; }
            .status { color: #00ff88; font-weight: bold; animation: pulse 2s infinite; }
            .log-box { background: #000; padding: 15px; height: 200px; overflow-y: auto; font-family: monospace; border-radius: 10px; border: 1px solid #1a1a1a; }
            @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
        </style>
    </head>
    <body>
        <div class="panel">
            <h1 style="text-align: center; letter-spacing: 3px;">🛰️ КОНТРОЛЬ ПОЛЕТА: МОНОПОЛИЯ</h1>
            <div style="text-align:center;">Статус: <span class="status">СИСТЕМЫ СТАБИЛЬНЫ</span></div>
            
            <div class="grid">
                <div class="card">ВЕБХУКИ<br><b style="color:#ff4444">ОТКЛЮЧЕНЫ (FIX)</b></div>
                <div class="card">АПТАЙМ<br><b>{{ up }} мин.</b></div>
                <div class="card">ПАМЯТЬ<br><b>{{ mem }}%</b></div>
            </div>

            <div class="log-box">
                {% for l in logs %}
                <div style="margin-bottom:5px;"><span style="color:#555;">[{{ l.time }}]</span> > {{ l.msg }}</div>
                {% endfor %}
            </div>
            <p style="font-size:10px; color:#333; text-align:right;">ID СЕССИИ: {{ session_id }}</p>
        </div>
    </body>
    </html>
    """, logs=site_logs[::-1], up=int((time.time()-start_time)/60), mem=mem, session_id=random.randint(1000,9999))

# --- БОТ ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def start_cmd(m: types.Message):
    await m.answer("🌌 **Космическая монополия готова к запуску.**")

async def main():
    add_log("УДАЛЕНИЕ ВЕБХУКОВ...")
    # 100% ГАРАНТИЯ: Очищаем всё перед стартом
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("КОНФЛИКТЫ УСТРАНЕНЫ.")
    
    # Запуск сервера
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    add_log("ПАНЕЛЬ СОСТОЯНИЯ ЗАПУЩЕНА.")
    
    add_log("ПОЛЛИНГ АКТИВИРОВАН.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        pass
    
