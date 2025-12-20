import asyncio, os, random, logging
from flask import Flask, render_template_string
from threading import Thread
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- 1. ГЛОБАЛЬНЫЕ ЛОГИ ДЛЯ САЙТА ---
logs_list = []

def add_log(text):
    time_str = datetime.now().strftime("%H:%M:%S")
    logs_list.append(f"[{time_str}] {text}")
    if len(logs_list) > 10: logs_list.pop(0) # Храним только последние 10 записей

# Настройка стандартного логирования в консоль
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 2. НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 10000))

players = {}
lobby_players = []
game_active = False

# --- 3. ВЕБ-САЙТ (FLASK) ---
app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Monopoly Admin</title>
    <meta http-equiv="refresh" content="5"> <style>
        body { background: #121212; color: white; font-family: 'Segoe UI', sans-serif; text-align: center; padding: 20px; }
        .box { display: inline-block; width: 80%; max-width: 600px; padding: 20px; border: 2px solid #4CAF50; border-radius: 15px; background: #1e1e1e; box-shadow: 0 0 20px rgba(76,175,80,0.2); }
        .logs { text-align: left; background: #000; padding: 15px; border-radius: 10px; font-family: monospace; color: #00ff00; margin-top: 20px; border: 1px solid #333; }
        h1 { color: #4CAF50; margin-bottom: 5px; }
        .status { color: #4CAF50; font-weight: bold; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🎮 Monopoly Bot Panel</h1>
        <p>Разработчик: <b>@Whylovely05</b></p>
        <hr style="border: 0.5px solid #333;">
        <p>Статус: <span class="status">ONLINE</span> | Игроков: <b>{{ count }}</b></p>
        
        <div class="logs">
            <strong>📝 Последние логи:</strong><br>
            {% for log in logs %}
                <div>{{ log }}</div>
            {% endfor %}
            {% if not logs %} <div style="color: #666;">Пока записей нет...</div> {% endif %}
        </div>
        <p style="font-size: 0.8em; color: #666; margin-top: 10px;">Страница обновляется автоматически каждые 5 секунд</p>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE, count=len(players), logs=logs_list[::-1])

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- 4. MIDDLEWARE ДЛЯ МОНИТОРИНГА ---
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            add_log(f"📩 Сообщение от {event.from_user.first_name}: {event.text[:15]}")
        elif isinstance(event, CallbackQuery):
            add_log(f"🔘 Кнопка от {event.from_user.first_name}: {event.data}")
        return await handler(event, data)

# --- 5. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())

@dp.message(Command("monopoly"))
async def cmd_monopoly(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Начать сбор", callback_query_data="l_start")]])
    await m.answer("🏨 **MONOPOLY ONLINE**\nБот активен! Нажмите кнопку ниже:", reply_markup=kb)

@dp.callback_query(F.data == "l_start")
async def l_start(call: CallbackQuery):
    global lobby_players, game_active
    lobby_players, game_active = [], False
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Вступить", callback_query_data="l_join")]])
    await call.message.edit_text("📢 **СБОР ИГРОКОВ**\nЖдем участников...", reply_markup=kb)

@dp.callback_query(F.data == "l_join")
async def l_join(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in lobby_players:
        lobby_players.append(uid)
        players[uid] = {"balance": 1500, "pos": 0, "name": call.from_user.first_name}
    
    kb = [[InlineKeyboardButton(text="✅ Вступить", callback_query_data="l_join")]]
    if len(lobby_players) >= 1: # Для теста поставил 1, потом верни 2
        kb.append([InlineKeyboardButton(text="🏁 НАЧАТЬ", callback_query_data="g_start")])
    
    await call.message.edit_text(f"👥 **В лобби:** {len(lobby_players)} чел.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "g_start")
async def g_start(call: CallbackQuery):
    global game_active
    game_active = True
    await call.message.answer("🎉 **ИГРА НАЧАЛАСЬ!**", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить кубик", callback_query_data="roll")]
    ]))
    await call.message.delete()

# --- 6. ЗАПУСК С УСИЛЕННЫМИ МЕРАМИ ---
async def main():
    add_log("🚀 Запуск системы...")
    
    # 1. Запуск сайта
    Thread(target=run_flask, daemon=True).start()
    add_log("🌐 Веб-панель запущена")

    # 2. Очистка сессии и вебхуков
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("🧹 Очередь обновлений очищена")

    # 3. Проверка связи с Telegram
    try:
        me = await bot.get_me()
        add_log(f"✅ Подключено к @{me.username}")
    except Exception as e:
        add_log(f"❌ ОШИБКА API: {e}")

    # 4. Поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
