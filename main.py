import asyncio, logging, os, sys, time, random, psutil
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# --- НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
games, site_logs = {}, []
start_time = time.time()

def add_log(msg):
    entry = {"time": time.strftime('%H:%M:%S'), "msg": msg}
    site_logs.append(entry)
    if len(site_logs) > 20: site_logs.pop(0)

# --- САМАЯ ДЕТАЛИЗИРОВАННАЯ ПАНЕЛЬ (КОСМОС + СОСТОЯНИЕ) ---
app = Flask(__name__)
@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>УПРАВЛЕНИЕ СТАНЦИЕЙ</title>
        <style>
            body { 
                background: #02040a; color: #e0e6ed; font-family: 'Courier New', monospace; 
                margin: 0; padding: 20px; background-image: radial-gradient(#1b2735 1px, transparent 1px);
                background-size: 50px 50px;
            }
            .main-frame { 
                border: 2px solid #00f3ff; border-radius: 10px; padding: 20px;
                background: rgba(0, 10, 20, 0.9); box-shadow: 0 0 25px #00f3ff55;
            }
            .header { border-bottom: 1px solid #00f3ff; margin-bottom: 20px; padding-bottom: 10px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
            .stat-card { 
                background: rgba(255, 255, 255, 0.05); border: 1px solid #1a2a3a; 
                padding: 15px; border-radius: 8px; text-align: center;
            }
            .status-led { color: #00ff88; text-shadow: 0 0 10px #00ff88; }
            .log-area { 
                margin-top: 20px; height: 250px; overflow-y: auto; background: #000;
                border: 1px solid #333; padding: 10px; font-size: 13px; color: #00f3ff;
            }
            .danger-zone { color: #ff4444; border-top: 1px solid #333; margin-top: 15px; padding-top: 10px; font-size: 11px; }
        </style>
    </head>
    <body>
        <div class="main-frame">
            <div class="header">
                <h1 style="margin:0; color:#00f3ff;">🛰️ SIGMA CORE V.4.0</h1>
                <small>КОНТРОЛЬ ПОЛЛИНГА И ВЕБХУКОВ</small>
            </div>
            <div class="grid">
                <div class="stat-card">СОСТОЯНИЕ<br><span class="status-led">● В СЕТИ</span></div>
                <div class="stat-card">ВЕБХУК<br><b style="color:#ff4444">УДАЛЕН (FIX)</b></div>
                <div class="stat-card">ПАМЯТЬ<br><b>{{ mem }}%</b></div>
                <div class="stat-card">СЕССИЯ<br><b>{{ up }} м.</b></div>
            </div>
            <div class="log-area">
                {% for l in logs %}
                <div>[{{ l.time }}] > {{ l.msg }}</div>
                {% endfor %}
            </div>
            <div class="danger-zone">
                ВНИМАНИЕ: Если вы видите это, значит старый процесс успешно деактивирован.
            </div>
        </div>
    </body>
    </html>
    """, logs=site_logs[::-1], up=int((time.time()-start_time)/60), mem=psutil.virtual_memory().percent)

# --- БОТ ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def start_game(m: types.Message):
    await m.answer("🌌 **Система Монополии активна.**\nВерсия: 4.0 (Анти-Конфликт)")

async def main():
    # ШАГ 1: Принудительно сбрасываем состояние вебхука
    add_log("Удаление старого вебхука...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    # ШАГ 2: Пауза 3 секунды, чтобы Telegram «разлогинил» старый процесс
    add_log("Ожидание деактивации старой сессии (3с)...")
    await asyncio.sleep(3)
    
    # ШАГ 3: Запуск веб-панели
    add_log("Запуск космической панели...")
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    
    # ШАГ 4: Поллинг
    add_log("Запуск нового ядра бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"ERROR: {e}")
                                  
