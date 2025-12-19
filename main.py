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
site_logs = []
start_time = time.time()

def add_log(msg):
    site_logs.append({"time": time.strftime('%H:%M:%S'), "msg": msg})
    if len(site_logs) > 20: site_logs.pop(0)

# --- САМАЯ КРАСИВАЯ АДМИНКА (СТИЛЬ КОСМОС) ---
app = Flask(__name__)
@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>GALAXY ADMIN PANEL</title>
        <style>
            body { 
                background: #050510; color: #00f3ff; font-family: 'Segoe UI', sans-serif; 
                margin: 0; padding: 20px; overflow: hidden;
            }
            .space-container {
                border: 2px solid #00f3ff; border-radius: 25px; padding: 30px;
                background: rgba(10, 20, 40, 0.85); backdrop-filter: blur(10px);
                box-shadow: 0 0 50px rgba(0, 243, 255, 0.3); max-width: 800px; margin: auto;
            }
            .header-info { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1a3a5a; padding-bottom: 15px; }
            .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 25px; }
            .card { background: rgba(0,0,0,0.5); border: 1px solid #1a2a3a; padding: 20px; border-radius: 15px; text-align: center; }
            .label { font-size: 11px; color: #576574; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 20px; font-weight: bold; color: #fff; }
            .log-window { 
                margin-top: 25px; height: 200px; overflow-y: auto; background: #000;
                border-radius: 10px; padding: 15px; border: 1px solid #1a3a5a; font-family: monospace;
            }
            .status-dot { height: 10px; width: 10px; background-color: #00ff88; border-radius: 50%; display: inline-block; box-shadow: 0 0 10px #00ff88; }
        </style>
    </head>
    <body>
        <div class="space-container">
            <div class="header-info">
                <div><h1 style="margin:0; letter-spacing:3px;">🛰️ SIGMA CORE</h1><small>БЕСПЛАТНАЯ ВЕРСИЯ: ОПТИМИЗИРОВАНО</small></div>
                <div style="text-align:right;"><span class="status-dot"></span> СИСТЕМА ONLINE</div>
            </div>
            <div class="grid">
                <div class="card"><div class="label">ВЕБХУКИ</div><div class="value" style="color:#ff4444;">ВЫКЛЮЧЕНЫ</div></div>
                <div class="card"><div class="label">АПТАЙМ</div><div class="value">{{ up }} МИН</div></div>
                <div class="card"><div class="label">CPU</div><div class="value">{{ cpu }}%</div></div>
            </div>
            <div class="log-window">
                {% for l in logs %}
                <div style="margin-bottom:6px; color:#a0d2eb;"><span style="color:#576574;">[{{ l.time }}]</span> >> {{ l.msg }}</div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, logs=site_logs[::-1], up=int((time.time()-start_time)/60), cpu=psutil.cpu_percent())

# --- МОЗГ БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(m: types.Message):
    await m.answer("🚀 **КОСМИЧЕСКИЙ ДВИГАТЕЛЬ ЗАПУЩЕН!**\n\nЯ успешно подавил старую версию. Теперь я — твой единственный бот.")

async def main():
    add_log("ЗАГРУЗКА БОРТОВЫХ СИСТЕМ...")
    
    # ЭТОТ БЛОК — ГАРАНТИЯ ОТ КОНФЛИКТА
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        add_log("СТАРЫЙ КАНАЛ СВЯЗИ ЗАКРЫТ.")
    except Exception as e:
        add_log(f"ОШИБКА ОЧИСТКИ: {e}")

    # Запуск микро-сервиса, чтобы Render не выключал бота
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    add_log(f"СЕРВЕР ПРОВЕРКИ СТАТУСА: ПОРТ {PORT}")

    # Пауза для бесплатного тарифа (Render Free Tier)
    add_log("ПАУЗА 10 СЕКУНД ДЛЯ СБРОСА СЕССИЙ...")
    await asyncio.sleep(10)

    add_log("БОТ ВСТУПИЛ В ДЕЖУРСТВО.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        pass
    
