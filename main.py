import asyncio, logging, os, sys, time, random, psutil
from flask import Flask, render_template_string, redirect, url_for
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

# КАРТА С ДИЗАЙНЕРСКИМИ ИКОНКАМИ
BOARD = [
    ("СТАРТ 🚩", 0, 0), ("Ул. Рижская 🏙", 1500, 800), ("ШАНС 🎲", 0, 0), ("Ул. Тверская 🌃", 2000, 1000),
    ("НАЛОГ 💸", 0, 1500), ("МЕТРО 🚇", 3000, 1500), ("Ул. Арбат 🏟", 2500, 1200), ("КАЗНА 💰", 0, 0),
    ("Ул. Полянка 🏨", 3000, 1500), ("ТЮРЬМА ⚖️", 0, 0), ("Парк Победы 🌳", 3500, 1800), ("Ул. Вавилова 🏢", 4000, 2000),
    ("ШАНС 🎲", 0, 0), ("Кутузовский 🏛", 5000, 2500), ("ИНВЕСТ-ФОНД 📈", 0, 0), ("НЕФТЬ 🛢", 6000, 3000),
    ("Ул. Остоженка 💎", 7000, 3500), ("КАЗНА 💰", 0, 0), ("ЦВЕТНОЙ Б-Р 🎪", 8000, 4000), ("В ТЮРЬМУ! 👮" , 0, 0)
]

def add_log(msg):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    site_logs.append(entry)
    print(f"DESIGN_LOG: {entry}", flush=True)

# --- FLASK DASHBOARD ---
app = Flask(__name__)
@app.route('/')
def dashboard():
    return render_template_string("""
    <body style="background:#0a0a0a; color:#00d4ff; font-family:monospace; padding:40px;">
        <h1 style="text-shadow: 0 0 10px #00d4ff;">⚡ SIGMA MONOPOLY OS v3.0</h1>
        <hr style="border:1px solid #1a1a1a;">
        <p>SYSTEM_UPTIME: {{ up }}m | ACTIVE_CORES: {{ g_count }}</p>
        <div style="background:#000; border:1px solid #333; padding:20px; height:350px; overflow-y:auto;">
            {% for l in logs %} <div style="margin-bottom:5px;">>> {{ l }}</div> {% endfor %}
        </div>
    </body>""", logs=site_logs[::-1], up=int((time.time()-start_time)/60), g_count=len(games))

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
    if cid in games: return await m.answer("❌ **СИСТЕМА УЖЕ ЗАПУЩЕНА**")
    
    games[cid] = {
        "status": "lobby",
        "players": {m.from_user.id: {"name": m.from_user.first_name, "pos": 0, "money": 20000}},
        "order": [m.from_user.id], "turn": 0, "properties": {}
    }
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="ВСТУПИТЬ ✅", callback_data="join_game"))
    kb.row(InlineKeyboardButton(text="ЗАПУСТИТЬ ТЕРМИНАЛ 🚀", callback_data="start_match"))
    
    welcome_text = (
        "➖➖➖➖➖➖➖➖➖➖\n"
        "🏙 **SIGMA MONOPOLY ULTIMATE**\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "💰 Стартовый капитал: `20,000$`\n"
        "👤 Создатель: " + m.from_user.first_name + "\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "🤖 *Ожидание подключения игроков...*"
    )
    await m.answer(welcome_text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "roll")
async def roll_callback(call: types.CallbackQuery):
    cid, uid = call.message.chat.id, call.from_user.id
    game = games.get(cid)
    if not game or game["order"][game["turn"]] != uid:
        return await call.answer("⏳ СЕЙЧАС ХОД ДРУГОГО ИГРОКА", show_alert=False)
    
    p = game["players"][uid]
    steps = random.randint(2, 12)
    p["pos"] = (p["pos"] + steps) % len(BOARD)
    tile_name, price, rent = BOARD[p["pos"]]
    
    # Логика аренды (упрощенно для примера)
    owner_id = game["properties"].get(p["pos"])
    rent_status = ""
    if owner_id and owner_id != uid:
        p["money"] -= rent
        game["players"][owner_id]["money"] += rent
        rent_status = f"\n💸 **ОПЛАТА АРЕНДЫ:** `- {rent}$`"

    can_buy = price > 0 and p["pos"] not in game["properties"] and p["money"] >= price

    # --- КРАСИВЫЙ ДИЗАЙН ХОДА ---
    move_text = (
        f"🎲 **ХОД: {p['name'].upper()}**\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🔢 Выброшено: `{steps}`\n"
        f"📍 Локация: **{tile_name}**\n"
        f"{rent_status}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💵 Баланс: `{p['money']}$`\n"
        f"👤 Следующий: *{game['players'][game['order'][(game['turn']+1)%len(game['order'])]]['name']}*"
    )

    game["turn"] = (game["turn"] + 1) % len(game["order"])
    await call.message.answer(move_text, reply_markup=get_game_kb(can_buy), parse_mode="Markdown")

# --- LAUNCH ---
async def main():
    add_log("INITIALIZING CORE...")
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, use_reloader=False), daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    add_log("PRIME SYSTEM ONLINE.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                                  
