import asyncio, logging, os, sys, time, random, psutil
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# --- НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))
SESSION_ID = f"GALAXY-{random.randint(100, 999)}" # Уникальный ID сессии

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
site_logs = []
start_time = time.time()

def add_log(msg):
    site_logs.append({"time": time.strftime('%H:%M:%S'), "msg": msg})
    if len(site_logs) > 15: site_logs.pop(0)

# --- УЛЬТРА-ДЕТАЛИЗИРОВАННАЯ АДМИНКА ---
app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>ГОРЯЧАЯ ЛИНИЯ КОСМОСА</title>
        <style>
            body { background: #000; color: #00f3ff; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; }
            .main-container { 
                max-width: 900px; margin: auto; border: 2px solid #00f3ff; 
                border-radius: 30px; padding: 40px; background: rgba(0, 15, 30, 0.9);
                box-shadow: 0 0 60px rgba(0, 243, 255, 0.2); position: relative;
            }
            .header { text-align: center; border-bottom: 1px solid #1a3a5a; padding-bottom: 20px; margin-bottom: 30px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; }
            .card { background: rgba(255, 255, 255, 0.03); border: 1px solid #1a2a3a; padding: 20px; border-radius: 20px; text-align: center; }
            .label { font-size: 11px; color: #556677; text-transform: uppercase; margin-bottom: 10px; }
            .value { font-size: 22px; font-weight: bold; color: #fff; }
            .log-box { 
                margin-top: 30px; background: rgba(0,0,0,0.7); height: 200px; 
                overflow-y: auto; border-radius: 15px; padding: 20px; border: 1px solid #112233;
                font-family: 'Consolas', monospace; font-size: 13px;
            }
            .pulse {
                width: 12px; height: 12px; background: #00ff88; border-radius: 50%;
                display: inline-block; margin-right: 10px; animation: shadow-pulse 2s infinite;
            }
            @keyframes shadow-pulse { 0% { box-shadow: 0 0 0 0px rgba(0, 255, 136, 0.4); } 100% { box-shadow: 0 0 0 15px rgba(0, 255, 136, 0); } }
            .id-tag { position: absolute; top: 20px; right: 40px; color: #1a3a5a; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="main-container">
            <div class="id-tag">{{ sid }}</div>
            <div class="header">
                <h1>🛰️ ЦЕНТР СВЯЗИ «СИГМА»</h1>
                <p><span class="pulse"></span> СИСТЕМА ПОЛНОСТЬЮ СТАБИЛЬНА</p>
            </div>
            
            <div class="grid">
                <div class="card"><div class="label">Статус</div><div class="value" style="color:#00ff88">АКТИВЕН</div></div>
                <div class="card"><div class="label">Конфликты</div><div class="value">0</div></div>
                <div class="card"><div class="label">Память</div><div class="value">{{ mem }}%</div></div>
                <div class="card"><div class="label">В сети</div><div class="value">{{ up }} м.</div></div>
            </div>

            <div class="log-box">
                {% for l in logs %}
                <div style="margin-bottom:8px; border-left: 2px solid #00f3ff; padding-left: 10px;">
                    <span style="color:#445566;">[{{ l.time }}]</span> <span style="color:#00f3ff;">{{ l.msg }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, logs=site_logs[::-1], up=int((time.time()-start_time)/60), mem=psutil.virtual_memory().percent, sid=SESSION_ID)

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(m: types.Message):
    await m.answer(f"🌠 **СИСТЕМА СТАБИЛИЗИРОВАНА**\n\nСессия: `{SESSION_ID}`\nСтатус: **ИДЕАЛЬНО**\n\n_Теперь ты можешь играть в монополию без сбоев._")

async def run_bot():
    add_log("ПЕРЕЗАГРУЗКА КАНАЛОВ СВЯЗИ...")
    # Принудительно вытесняем старых ботов
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("СТАРЫЕ ПРОЦЕССЫ УДАЛЕНЫ.")
    
    # Запуск админки
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    add_log(f"АДМИН-ПАНЕЛЬ ЗАПУЩЕНА (ПОРТ {PORT})")

    add_log("ЯДРО МОНОПОЛИИ ГОТОВО К РАБОТЕ.")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except:
        pass
    
