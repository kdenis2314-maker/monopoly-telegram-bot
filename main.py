import asyncio, logging, os, sys, time, random, psutil
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# --- CONFIG ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))
INSTANCE_ID = random.randint(1000, 9999) # Уникальный номер этого запуска

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
site_logs = []
start_time = time.time()

def add_log(msg):
    site_logs.append({"time": time.strftime('%H:%M:%S'), "msg": msg})
    if len(site_logs) > 15: site_logs.pop(0)

# --- САМАЯ ДЕТАЛИЗИРОВАННАЯ АДМИНКА ---
app = Flask(__name__)

@app.route('/health') # Для Render Health Check
def health(): return "OK", 200

@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>COMMAND CENTER v8.0</title>
        <style>
            body { background: #000; color: #00f3ff; font-family: 'Consolas', monospace; padding: 20px; }
            .monitor { border: 2px solid #00f3ff; border-radius: 15px; padding: 20px; box-shadow: 0 0 20px #00f3ff44; }
            .header { border-bottom: 1px solid #1a3a5a; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; }
            .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
            .stat-card { background: rgba(0,243,255,0.05); border: 1px solid #1a3a5a; padding: 10px; text-align: center; }
            .log { background: #050505; height: 250px; overflow-y: auto; padding: 10px; border: 1px solid #111; font-size: 12px; }
            .blink { animation: blinker 1s linear infinite; color: #00ff88; }
            @keyframes blinker { 50% { opacity: 0; } }
            .version-tag { background: #00f3ff; color: #000; padding: 2px 5px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="monitor">
            <div class="header">
                <div>🛰️ <span class="version-tag">CORE v8.0</span> SESSION: #{{ inst }}</div>
                <div class="blink">● СИСТЕМА ПОДАВЛЕНИЯ КОНФЛИКТОВ АКТИВНА</div>
            </div>
            <div class="stat-grid">
                <div class="stat-card">ВЕБХУКИ<br><span style="color:#ff4444">ОТКЛЮЧЕНЫ</span></div>
                <div class="stat-card">CPU<br>{{ cpu }}%</div>
                <div class="stat-card">RAM<br>{{ mem }}%</div>
                <div class="stat-card">UPTIME<br>{{ up }}m</div>
            </div>
            <div class="log">
                {% for l in logs %}
                <div style="margin-bottom:4px; color:#576574;">[{{ l.time }}] <span style="color:#00f3ff;">>> {{ l.msg }}</span></div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, logs=site_logs[::-1], up=int((time.time()-start_time)/60), cpu=psutil.cpu_percent(), mem=psutil.virtual_memory().percent, inst=INSTANCE_ID)

# --- BOT LOGIC ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(m: types.Message):
    await m.answer(f"🪐 **БОРТОВОЙ КОМПЬЮТЕР v8.0**\n\nСтатус: **В СЕТИ**\nInstance ID: `{INSTANCE_ID}`\n\n_Старые процессы успешно вытеснены из памяти._")

async def run_bot():
    add_log("ЗАПУСК ПРОТОКОЛА ВЫТЕСНЕНИЯ...")
    
    # 1. СБРОС СТАРЫХ СОЕДИНЕНИЙ ТЕЛЕГРАМ
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("ВЕБХУКИ ОЧИЩЕНЫ. СТАРЫЕ ОБНОВЛЕНИЯ СБРОШЕНЫ.")
    
    # 2. ПАУЗА 15 СЕКУНД (Критически для бесплатного Render)
    # Это время нужно, чтобы Telegram закрыл TCP-соединение со старым ботом
    add_log("ОЖИДАНИЕ ТАЙМАУТА СТАРОЙ СЕССИИ (15 СЕК)...")
    await asyncio.sleep(15)
    
    add_log(f"ЗАПУСК ЯДРА ПОЛЛИНГА (ID: {INSTANCE_ID})")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    add_log("ИНИЦИАЛИЗАЦИЯ КОСМИЧЕСКОГО ТЕРМИНАЛА...")
    
    # Запуск Flask
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    
    try:
        asyncio.run(run_bot())
    except Exception as e:
        print(f"FATAL ERROR: {e}")
