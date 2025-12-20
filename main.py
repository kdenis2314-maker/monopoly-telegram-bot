import asyncio
import random
import os
import logging
import threading
from flask import Flask, render_template_string, request, redirect
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# --- НАСТРОЙКИ ---
logging.basicConfig(level=logging.INFO)
TOKEN = "8265158957:AAEMnEcldgMy7go_oxhHCweqxhe69XjKChE"
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()
app = Flask(__name__)

# --- СОСТОЯНИЕ ИГРЫ ---
state = {
    "players": {}, 
    "owners": {},   
    "lobby": [],
    "game_started": False,
    "current_turn": 0
}

BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "rent": 0},
    {"name": "🏠 Ул. Житная", "price": 60, "rent": 10},
    {"name": "🏠 Ул. Нагатинская", "price": 60, "rent": 10},
    {"name": "💸 Налог", "price": 0, "rent": 100},
    {"name": "🏢 Рижская ж/д", "price": 200, "rent": 50},
    {"name": "🏠 Ул. Огарева", "price": 120, "rent": 30},
    {"name": "⛓ Тюрьма", "price": 0, "rent": 0},
    {"name": "🏠 Парк Культуры", "price": 140, "rent": 40},
    {"name": "🏠 Охотный Ряд", "price": 160, "rent": 50},
    {"name": "🏨 Пр. Мира", "price": 200, "rent": 60},
    {"name": "🏠 Тверская", "price": 240, "rent": 80},
    {"name": "🏠 Ул. Пушкина", "price": 300, "rent": 110},
    {"name": "💎 Арбат", "price": 400, "rent": 150},
]

# --- АДМИН-ПАНЕЛЬ (FLASK) ---
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Monopoly</title><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"></head>
<body class="container mt-5 bg-light">
    <div class="card shadow p-4">
        <h2 class="mb-4">Управление игроками</h2>
        <table class="table table-hover">
            <thead class="table-dark"><tr><th>Имя</th><th>Баланс</th><th>Позиция</th><th>Действие</th></tr></thead>
            <tbody>
                {% for id, p in players.items() %}
                <tr>
                    <td>{{ p.name }}</td>
                    <td>{{ p.balance }}$</td>
                    <td>{{ p.position }}</td>
                    <td>
                        <form action="/edit" method="post" class="row g-2">
                            <input type="hidden" name="id" value="{{ id }}">
                            <div class="col-auto"><input type="number" name="money" class="form-control form-control-sm" placeholder="Баланс" required></div>
                            <div class="col-auto"><button class="btn btn-sm btn-warning">Установить</button></div>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="mt-3">
            <a href="/reset" class="btn btn-danger">Сбросить игру полностью</a>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def admin_index():
    return render_template_string(ADMIN_HTML, players=state["players"])

@app.route('/edit', methods=['POST']) # ИСПРАВЛЕНО ЗДЕСЬ
def edit_player():
    pid = int(request.form.get("id"))
    new_money = int(request.form.get("money"))
    if pid in state["players"]:
        state["players"][pid]["balance"] = new_money
    return redirect('/')

@app.route('/reset')
def reset_game():
    state["players"].clear()
    state["owners"].clear()
    state["lobby"].clear()
    state["game_started"] = False
    state["current_turn"] = 0
    return "Игра успешно сброшена! Можно начинать заново в Telegram."

# --- ЛОГИКА БОТА ---

def get_map(uid):
    if not state["lobby"]: return "Лобби пусто."
    curr_id = state["lobby"][state["current_turn"]]
    turn_name = state["players"][curr_id]['name']
    
    lines = [f"🎲 Сейчас ходит: *{turn_name}*\n", "📍 **КАРТА:**"]
    for i, cell in enumerate(BOARD):
        visitors = [state["players"][pid]["name"] for pid in state["lobby"] if state["players"][pid]["position"] == i]
        visitors_str = f"👤({', '.join(visitors)})" if visitors else ""
        
        owner_info = ""
        if i in state["owners"]:
            owner_info = f"🏠 {state['players'][state['owners'][i]]['name']}"
        else:
            owner_info = f"{cell['price']}$" if cell['price'] > 0 else "—"
            
        lines.append(f"{i}. {cell['name']} — `{owner_info}` {visitors_str}")
    
    lines.append(f"\n💰 Ваш баланс: `{state['players'][uid]['balance']}$`")
    return "\n".join(lines)

@dp.message(Command("monopoly"))
async def start_cmd(m: types.Message):
    if state["game_started"]: 
        return await m.answer("⚠️ Игра уже идет! Используйте кнопки управления или дождитесь завершения.")
    
    kb = InlineKeyboardBuilder().button(text="✅ Присоединиться", callback_data="join").as_markup()
    await m.answer("💎 **M O N O P O L Y**\n\nНажмите кнопку, чтобы вступить в игру!", reply_markup=kb)

@dp.callback_query(F.data == "join")
async def join_cb(c: types.CallbackQuery):
    uid = c.from_user.id
    if uid not in state["players"]:
        state["players"][uid] = {"name": c.from_user.first_name[:10], "balance": 1500, "position": 0}
        state["lobby"].append(uid)
        
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Присоединиться", callback_data="join")
        kb.button(text="🚀 Начать игру", callback_data="start_game")
        kb.adjust(1)
        
        await c.message.edit_text(f"⏳ **СБОР ИГРОКОВ**\nУчастников: {len(state['lobby'])}\n\nПоследним зашел: {c.from_user.first_name}", reply_markup=kb.as_markup())
    await c.answer()

@dp.callback_query(F.data == "start_game")
async def start_game_cb(c: types.CallbackQuery):
    if len(state["lobby"]) < 2:
        return await c.answer("Нужно минимум 2 игрока!", show_alert=True)
    
    state["game_started"] = True
    kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
    await bot.send_message(c.message.chat.id, f"🚀 **ИГРА НАЧАЛАСЬ!**\nПервым ходит: {state['players'][state['lobby'][0]]['name']}", reply_markup=kb)
    await c.message.delete()

@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice(m: types.Message):
    if not state["game_started"]: return
    
    uid = m.from_user.id
    if uid != state["lobby"][state["current_turn"]]:
        curr_name = state["players"][state["lobby"][state["current_turn"]]]['name']
        return await m.answer(f"❌ Сейчас ход игрока **{curr_name}**!")

    p = state["players"][uid]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    cell = BOARD[p["position"]]
    
    text = f"🎲 **{p['name']}** выкинул {dice} и приземлился на **{cell['name']}**\n"
    kb = InlineKeyboardBuilder()

    # Логика аренды/налога/покупки
    if cell["name"] == "💸 Налог":
        p["balance"] -= 100
        text += "💸 Вы заплатили налог 100$!\n"
    elif p["position"] in state["owners"] and state["owners"][p["position"]] != uid:
        owner_id = state["owners"][p["position"]]
        rent = cell["rent"]
        p["balance"] -= rent
        state["players"][owner_id]["balance"] += rent
        text += f"💰 Уплачена аренда {rent}$ игроку {state['players'][owner_id]['name']}\n"
    elif cell["price"] > 0 and p["position"] not in state["owners"]:
        if p["balance"] >= cell["price"]:
            kb.button(text=f"🛒 Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")

    state["current_turn"] = (state["current_turn"] + 1) % len(state["lobby"])
    await m.answer(text + "\n" + get_map(uid), reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def buy_cb(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    uid = c.from_user.id
    p = state["players"][uid]
    cell = BOARD[idx]
    
    if p["balance"] >= cell["price"] and idx not in state["owners"]:
        p["balance"] -= cell["price"]
        state["owners"][idx] = uid
        await c.message.answer(f"✅ **{p['name']}** купил {cell['name']}!")
    await c.answer()

# --- ЗАПУСК ---

def run_flask():
    # Render передает порт в переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def main():
    # Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Запуск Telegram бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
        
