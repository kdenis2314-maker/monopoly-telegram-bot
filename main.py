import asyncio, logging, os, sys, time, random
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# --- SETTINGS ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
games = {} 
site_logs = []
start_time = time.time()

# Расширенная карта
BOARD = [
    ("СТАРТ 🚩", 0, 0), ("Ул. Рижская 🏙", 1500, 800), ("ШАНС 🎲", 0, 0), ("Ул. Тверская 🌃", 2000, 1000),
    ("НАЛОГ 💸", 0, 1500), ("МЕТРО 🚇", 3000, 1500), ("Ул. Арбат 🏟", 2500, 1200), ("КАЗНА 💰", 0, 0),
    ("Ул. Полянка 🏨", 3000, 1500), ("ТЮРЬМА ⚖️", 0, 0), ("Парк Победы 🌳", 3500, 1800), ("Ул. Вавилова 🏢", 4000, 2000),
    ("ШАНС 🎲", 0, 0), ("Кутузовский 🏛", 5000, 2500), ("ИНВЕСТ-ФОНД 📈", 0, 0), ("НЕФТЬ 🛢", 6000, 3000),
    ("Ул. Остоженка 💎", 7000, 3500), ("КАЗНА 💰", 0, 0), ("ЦВЕТНОЙ Б-Р 🎪", 8000, 4000), ("В ТЮРЬМУ! 👮" , 0, 0)
]

def add_log(msg):
    entry = {"time": time.strftime('%H:%M:%S'), "msg": msg}
    site_logs.append(entry)

# --- DEEP SPACE ADMIN PANEL ---
app = Flask(__name__)
@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <style>
        body { background: #020205; color: #fff; font-family: 'Orbitron', sans-serif; margin: 0; overflow: hidden; }
        .space-bg { position: fixed; width: 100%; height: 100%; background: radial-gradient(ellipse at bottom, #1B2735 0%, #090A0F 100%); z-index: -1; }
        .glass { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(10px); border: 1px solid rgba(0, 212, 255, 0.2); border-radius: 15px; padding: 25px; margin: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8); }
        .neon-text { color: #00f3ff; text-shadow: 0 0 10px #00f3ff, 0 0 20px #00f3ff; }
        .log-container { height: 400px; overflow-y: auto; font-family: 'Courier New'; font-size: 13px; color: #a0d2eb; }
        .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; }
        .card { background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; border-top: 2px solid #00f3ff; text-align: center; }
        @keyframes scan { 0% { top: 0; } 100% { top: 100%; } }
        .scanner { position: absolute; width: 100%; height: 2px; background: rgba(0, 243, 255, 0.2); animation: scan 4s linear infinite; }
    </style>
    <div class="space-bg"><div class="scanner"></div></div>
    <div class="glass">
        <h1 class="neon-text">🛰️ SIGMA OS: GALACTIC COMMAND</h1>
        <div class="grid">
            <div class="card"><h3>UPTIME</h3><p>{{ up }}m</p></div>
            <div class="card"><h3>CORES</h3><p>{{ g_count }} ACTIVE</p></div>
            <div class="card"><h3>ENGINE</h3><p>STABLE</p></div>
        </div>
        <div class="glass" style="margin: 20px 0;">
            <div class="log-container">
                {% for l in logs %}<div><span style="color:#576574">[{{ l.time }}]</span> >> {{ l.msg }}</div>{% endfor %}
            </div>
        </div>
    </div>
    """, logs=site_logs[::-1], up=int((time.time()-start_time)/60), g_count=len(games))

# --- BOT LOGIC ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def start_game(m: types.Message):
    cid = m.chat.id
    if cid in games: return await m.answer("🛸 **СИСТЕМА:** Игра уже активна в этом секторе.")
    
    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"name": m.from_user.first_name, "pos": 0, "money": 20000}},
        "order": [m.from_user.id], "turn": 0, "properties": {}
    }
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="ВСТУПИТЬ 🛰️", callback_data="join_game"))
    kb.row(InlineKeyboardButton(text="ЗАПУСК ЯДРА ⚡", callback_data="start_match"))
    
    await m.answer(
        f"🌌 **— ИНИЦИАЛИЗАЦИЯ МОНОПОЛИИ —**\n\n"
        f"👨‍🚀 **Капитан:** {m.from_user.first_name}\n"
        f"💳 **Бюджет:** `20,000$`\n"
        f"📍 **Статус:** Ожидание экипажа...", 
        reply_markup=kb.as_markup()
    )

@dp.callback_query(F.data == "join_game")
async def join_game(call: types.CallbackQuery):
    game = games.get(call.message.chat.id)
    if not game: return
    if call.from_user.id in game["players"]:
        return await call.answer("Вы уже на борту!", show_alert=True)
    
    game["players"][call.from_user.id] = {"name": call.from_user.first_name, "pos": 0, "money": 20000}
    game["order"].append(call.from_user.id)
    await call.message.edit_text(
        f"{call.message.text}\n✅ Присоединился: {call.from_user.first_name}",
        reply_markup=call.message.reply_markup
    )
    add_log(f"User {call.from_user.first_name} joined game {call.message.chat.id}")

@dp.callback_query(F.data == "roll")
async def roll_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    game = games.get(cid)
    if not game or game["order"][game["turn"]] != uid:
        return await call.answer("⏳ Не ваша очередь, пилот!", show_alert=True)
    
    p = game["players"][uid]
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2
    p["pos"] = (p["pos"] + steps) % len(BOARD)
    tile_name, price, rent = BOARD[p["pos"]]
    
    # Логика аренды
    owner_id = game["properties"].get(p["pos"])
    rent_msg = ""
    if owner_id and owner_id != uid:
        p["money"] -= rent
        game["players"][owner_id]["money"] += rent
        rent_msg = f"\n🔴 **УПЛАТА НАЛОГА:** -`{rent}$` владельцу {game['players'][owner_id]['name']}"

    can_buy = price > 0 and p["pos"] not in game["properties"] and p["money"] >= price
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎲 СЛЕД. ХОД", callback_data="roll"))
    if can_buy:
        kb.row(InlineKeyboardButton(text=f"💎 КУПИТЬ ЗА {price}$", callback_data=f"buy_{p['pos']}"))

    game["turn"] = (game["turn"] + 1) % len(game["order"])
    
    await call.message.answer(
        f"☄️ **РЕЗУЛЬТАТ ПРЫЖКА**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 **Пилот:** {p['name']}\n"
        f"🎲 **Кубики:** {d1} + {d2} = `{steps}`\n"
        f"📍 **Квадрант:** {tile_name}\n"
        f"{rent_msg}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 **Баланс:** `{p['money']}$`",
        reply_markup=kb.as_markup()
    )

# --- ENGINE START ---
async def main():
    add_log("CLEANING SESSIONS...")
    # Принудительно закрываем старые сессии и удаляем вебхуки
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close() # Закрываем старую сессию
    
    # Небольшая пауза, чтобы сервера Telegram сбросили конфликт
    await asyncio.sleep(2) 
    
    new_bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
    
    add_log("STARTING SPACE DASHBOARD...")
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    
    add_log("GALACTIC POLLING STARTED.")
    await dp.start_polling(new_bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    
