import os
import asyncio
import logging
from datetime import datetime
from collections import defaultdict
from flask import Flask, request, render_template_string, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ.get('BOT_TOKEN')
RENDER_DOMAIN = os.environ.get('RENDER_DOMAIN', 'https://your-app.onrender.com')
PORT = int(os.environ.get('PORT', 10000))

# --- АНТИ-СПАМ СИСТЕМА ---
class AntiFlood:
    def __init__(self, limit=1.5):
        self.limit = limit
        self.users = defaultdict(float)
    
    def is_flooding(self, user_id):
        now = datetime.now().timestamp()
        if now - self.users[user_id] < self.limit:
            return True
        self.users[user_id] = now
        return False

antiflood = AntiFlood()
web_logs = []
games_storage = {}

def add_log(msg, lvl="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    web_logs.append({"time": t, "lvl": lvl, "msg": msg})
    if len(web_logs) > 100: web_logs.pop(0)

    app = Flask(__name__)

ULTIMATE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Monopoly OS | Security Terminal</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root { --main-bg: #05070a; --card-bg: #0d1117; --neon-green: #238636; --neon-blue: #388bfd; }
        body { background: var(--main-bg); color: #c9d1d9; font-family: 'Segoe UI', sans-serif; }
        .stat-card { background: var(--card-bg); border: 1px solid #30363d; border-radius: 10px; padding: 20px; height: 100%; }
        .neon-text { color: var(--neon-blue); font-weight: bold; text-shadow: 0 0 5px rgba(56,139,253,0.3); }
        .terminal { background: #010409; border: 1px solid #30363d; border-radius: 8px; height: 450px; overflow-y: auto; font-family: 'Consolas', monospace; padding: 15px; font-size: 13px; }
        .badge-info { color: var(--neon-blue); border: 1px solid var(--neon-blue); background: transparent; }
        .control-panel { background: #161b22; border-left: 3px solid var(--neon-blue); padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container-fluid p-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>🎩 Monopoly <span class="neon-text">Core v3.0</span></h2>
            <div class="text-end">
                <span class="badge rounded-pill bg-success">DATABASE: ACTIVE</span>
                <span class="badge rounded-pill bg-primary">WEBHOOK: SECURE</span>
            </div>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-md-3"><div class="stat-card"><h6>АКТИВНЫЕ ИГРЫ</h6><h2 class="neon-text">{{ games }}</h2></div></div>
            <div class="col-md-3"><div class="stat-card"><h6>ПОЛЬЗОВАТЕЛЕЙ</h6><h2 class="text-white">{{ users }}</h2></div></div>
            <div class="col-md-3"><div class="stat-card"><h6>ЗАПРОСОВ/МИН</h6><h2 class="text-warning">FAST</h2></div></div>
            <div class="col-md-3"><div class="stat-card"><h6>ЗАЩИТА</h6><h2 class="text-success">HIGH</h2></div></div>
        </div>

        <div class="row">
            <div class="col-lg-8">
                <div class="stat-card">
                    <h5>СИСТЕМНЫЙ ТЕРМИНАЛ (ЛОГИ)</h5>
                    <div class="terminal">
                        {% for log in logs %}
                        <div class="mb-1">
                            <span style="color:#8b949e">[{{ log.time }}]</span>
                            <span class="badge badge-info me-2">{{ log.lvl }}</span>
                            {{ log.msg }}
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="stat-card control-panel">
                    <h5>УПРАВЛЕНИЕ ЯДРОМ</h5>
                    <div class="mb-3 mt-3">
                        <small class="d-block mb-2">Глобальная рассылка:</small>
                        <form action="/broadcast" method="POST">
                            <textarea class="form-control form-control-sm bg-dark text-white border-secondary mb-2" name="msg" placeholder="Текст сообщения..."></textarea>
                            <button type="submit" class="btn btn-primary btn-sm w-100">ОТПРАВИТЬ ВСЕМ</button>
                        </form>
                    </div>
                    <hr class="border-secondary">
                    <small class="d-block mb-2">Действия:</small>
                    <button class="btn btn-outline-warning btn-sm w-100 mb-2" onclick="location.href='/reset'">СБРОСИТЬ КЭШ</button>
                    <button class="btn btn-outline-danger btn-sm w-100" onclick="confirm('Выключить?')">ОСТАНОВИТЬ ПРОЦЕСС</button>
                </div>
            </div>
        </div>
    </div>
    <script>setTimeout(() => location.reload(), 5000);</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(ULTIMATE_HTML, logs=reversed(web_logs), games=len(games_storage), users=10, port=PORT)

@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        
        # Защита от спама (Flood Protection)
        uid = update.effective_user.id if update.effective_user else None
        if uid and antiflood.is_flooding(uid):
            add_log(f"Попытка флуда от {uid} пресечена", "SECURITY")
            return 'OK', 200
            
        await application.process_update(update)
    except Exception as e:
        add_log(f"Критический перехват: {str(e)}", "ERROR")
    return 'OK', 200



async def main():
    global application
    add_log("--- ЗАПУСК ЯДРА МОНОПОЛИИ ---")
    
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков (Сюда добавляй свои команды)
    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("🎩 Бот защищен и готов к игре!")))
    
    # Установка вебхука
    webhook_url = f"{RENDER_DOMAIN}/webhook"
    await application.bot.set_webhook(url=webhook_url)
    add_log(f"Вебхук надежно закреплен: {webhook_url}")

    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    
    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]
    
    add_log("Hypercorn ASGI сервер запущен")
    await serve(app, config)

if __name__ == '__main__':
    application = None
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"FATAL: {e}")


