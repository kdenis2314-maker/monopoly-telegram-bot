import asyncio, logging, os, sys, time, random
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

# --- SETTINGS ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 8081))

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
games = {} 
site_logs = []
start_time = time.time()

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
    if len(site_logs) > 50: site_logs.pop(0)

# --- SPACE ADMIN PANEL ---
app = Flask(__name__)
@app.route('/')
def dashboard():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>COSMOS ADMIN OS</title>
        <style>
            body { 
                background: radial-gradient(circle at center, #050510 0%, #000 100%);
                color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0; overflow: hidden; height: 100vh;
            }
            .stars { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; }
            .container { 
                max-width: 1000px; margin: 50px auto; 
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(15px); border-radius: 20px;
                border: 1px solid rgba(0, 212, 255, 0.3);
                padding: 30px; box-shadow: 0 0 50px rgba(0, 100, 255, 0.2);
            }
            h1 { text-align: center; letter-spacing: 5px; color: #00d4ff; text-shadow: 0 0 15px #00d4ff; }
            .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
            .stat-card { 
                background: rgba(0, 0, 0, 0.5); padding: 15px; border-radius: 10px; 
                border-left: 4px solid #00d4ff; text-align: center;
            }
            .log-box { 
                height: 300px; overflow-y: auto; background: rgba(0,0,0,0.8);
                border-radius: 10px; padding: 15px; font-family: 'Courier New', monospace;
                border: 1px solid #1a1a1a;
            }
            .log-entry { margin-bottom: 8px; border-bottom: 1px solid #111; padding-bottom: 4px; }
            .time { color: #00d4ff; font-weight: bold; margin-right: 10px; }
            .msg { color: #e0e0e0; }
            @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
            .online-indicator { color: #00ff88; animation: pulse 2s infinite; }
        </style>
    </head>
    <body>
        <div class="stars"></div>
        <div class="container">
            <h1>🌌 COSMOS CONTROL CENTER</h1>
            <div class="stat-grid">
                <div class="stat-card"><h3>UPTIME</h3><p>{{ up }} min</p></div>
                <div class="stat-card"><h3>ACTIVE GAMES</h3><p>{{ g_count }}</p></div>
                <div class="stat-card"><h3>STATUS</h3><p class="online-indicator">SYSTEM ACTIVE</p></div>
            </div>
            <div class="log-box">
                {% for l in logs %}
                <div class="log-entry">
                    <span class="time">[{{ l.time }}]</span>
                    <span class="msg">> {{ l.msg }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, logs=site_logs[::-1], up=int((time.time()-start_time)/60), g_count=len(games))

# --- BOT LOGIC ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_game_kb(can_buy=False):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎲 БРОСИТЬ КУБИКИ", callback_data="roll"))
    if can_buy:
        kb.row(InlineKeyboardButton(text="💎 КУПИТЬ ОБЪЕКТ", callback_data="buy_prop"))
    return kb.as_markup()

@dp.message(Command("monopoly"))
async def start_game(m: types.Message):
    cid = m.chat.id
    if cid in games: return await m.answer("⚠️ **ОШИБКА:** Игра уже запущена в этом чате.")
    
    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"name": m.from_user.first_name, "pos": 0, "money": 20000}},
        "order": [m.from_user.id], "turn": 0, "properties": {}
    }
    add_log(f"New game created by {m.from_user.first_name}")
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="ВСТУПИТЬ ✅", callback_data="join_game"))
    kb.row(InlineKeyboardButton(text="ЗАПУСТИТЬ ТЕРМИНАЛ 🚀", callback_data="start_match"))
    
    text = f"🚀 **SIGMA MONOPOLY: SPACE EDITION**\n\n👤 Хост: {m.from_user.first_name}\n💰 Капитал: `20,000$`\n\nОжидание игроков..."
    await m.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "join_game")
async def join_game(call: types.CallbackQuery):
    game = games.get(call.message.chat.id)
    if not game or call.from_user.id in game["players"]: return await call.answer("Вы уже в игре!")
    
    game["players"][call.from_user.id] = {"name": call.from_user.first_name, "pos": 0, "money": 20000}
    game["order"].append(call.from_user.id)
    await call.answer("Вы успешно вошли!")
    add_log(f"Player {call.from_user.first_name} joined.")

@dp.callback_query(F.data == "roll")
async def roll_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    game = games.get(cid)
    if not game or game["order"][game["turn"]] != uid:
        return await call.answer("⏳ Сейчас ход другого игрока!", show_alert=True)
    
    p = game["players"][uid]
    steps = random.randint(2, 12)
    p["pos"] = (p["pos"] + steps) % len(BOARD)
    tile_name, price, rent = BOARD[p["pos"]]
    
    owner_id = game["properties"].get(p["pos"])
    rent_status = ""
    if owner_id and owner_id != uid:
        p["money"] -= rent
        game["players"][owner_id]["money"] += rent
        rent_status = f"\n💸 **АРЕНДА:** `- {rent}$` игроку {game['players'][owner_id]['name']}"

    can_buy = price > 0 and p["pos"] not in game["properties"] and p["money"] >= price

    move_text = (
        f"🌌 **ХОД ИГРОКА: {p['name']}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🎲 Кубики: `{steps}`\n"
        f"📍 Локация: **{tile_name}**\n"
        f"{rent_status}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 Баланс: `{p['money']}$`"
    )

    game["turn"] = (game["turn"] + 1) % len(game["order"])
    await call.message.answer(move_text, reply_markup=get_game_kb(can_buy), parse_mode="Markdown")

async def main():
    add_log("INITIALIZING SPACE CORE...")
    # Запуск Flask в потоке
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    
    # КРИТИЧЕСКИЙ ИСПРАВЛЕНИЯ ДЛЯ ConflictError:
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("WEBHOOK CLEARED. STARTING POLLING...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
