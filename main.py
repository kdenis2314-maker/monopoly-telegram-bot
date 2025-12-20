import asyncio
import random
import os
import logging
import threading
from flask import Flask, render_template_string, request, redirect, url_for
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

# --- СОСТОЯНИЕ ИГРЫ (В памяти) ---
state = {
    "players": {}, # {id: {name, balance, position, in_jail, properties: []}}
    "owners": {},   # {cell_index: owner_id}
    "lobby": [],
    "game_started": False,
    "current_turn": 0,
    "logs": [] # Для админ-панели
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

# --- ЛОГИКА АДМИН-ПАНЕЛИ (Flask) ---
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Monopoly</title><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"></head>
<body class="container mt-5">
    <h2>управление игрой (Админ-панель)</h2>
    <table class="table table-dark">
        <thead><tr><th>Игрок</th><th>Баланс</th><th>Позиция</th><th>Действие</th></tr></thead>
        <tbody>
            {% for id, p in players.items() %}
            <tr>
                <td>{{ p.name }}</td>
                <td>{{ p.balance }}$</td>
                <td>{{ p.position }}</td>
                <td>
                    <form action="/edit" method="post" class="d-inline">
                        <input type="hidden" name="id" value="{{ id }}">
                        <input type="number" name="money" placeholder="Баланс" required>
                        <button class="btn btn-sm btn-warning">Уст. деньги</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <a href="/reset" class="btn btn-danger">Сбросить игру</a>
</body>
</html>
"""

@app.route('/')
def admin_index():
    return render_template_string(ADMIN_HTML, players=state["players"])

@app.route('/edit', method=['POST'])
def edit_player():
    pid = int(request.form.get("id"))
    new_money = int(request.form.get("money"))
    if pid in state["players"]:
        state["players"][pid]["balance"] = new_money
    return redirect('/')

@app.route('/reset')
def reset_game():
    state["players"], state["owners"], state["lobby"] = {}, {}, []
    state["game_started"] = False
    return "Игра сброшена. Введите /monopoly в боте."

# --- ЛОГИКА БОТА ---

def get_map(uid):
    curr_id = state["lobby"][state["current_turn"]]
    lines = [f"🎲 Сейчас ходит: *{state['players'][curr_id]['name']}*\n"]
    for i, cell in enumerate(BOARD):
        marker = "📍 ВЫ" if state["players"][uid]["position"] == i else ""
        owner = f"🏠 {state['players'][state['owners'][i]]['name']}" if i in state["owners"] else (f"{cell['price']}$" if cell['price'] > 0 else "—")
        lines.append(f"{i}. {cell['name']} [{owner}] {marker}")
    lines.append(f"\n💰 Баланс: `{state['players'][uid]['balance']}$`")
    return "\n".join(lines)

@dp.message(Command("monopoly"))
async def start_cmd(m: types.Message):
    if state["game_started"]: return await m.answer("Игра уже идет.")
    kb = InlineKeyboardBuilder().button(text="Присоединиться", callback_data="join").as_markup()
    await m.answer("💎 Набор в Монополию! Нажмите кнопку для входа.", reply_markup=kb)

@dp.callback_query(F.data == "join")
async def join_cb(c: types.CallbackQuery):
    if c.from_user.id not in state["players"]:
        state["players"][c.from_user.id] = {"name": c.from_user.first_name[:10], "balance": 1500, "position": 0, "in_jail": False}
        state["lobby"].append(c.from_user.id)
        kb = InlineKeyboardBuilder().button(text="Начать игру", callback_data="start").as_markup()
        await c.message.edit_text(f"Игроков: {len(state['lobby'])}", reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "start")
async def start_game(c: types.CallbackQuery):
    if len(state["lobby"]) < 2: return await c.answer("Нужно 2 игрока!", show_alert=True)
    state["game_started"] = True
    kb = ReplyKeyboardBuilder().button(text="🎲 Бросить кубик").as_markup(resize_keyboard=True)
    await bot.send_message(c.message.chat.id, "🚀 Игра началась!", reply_markup=kb)
    await c.answer()

@dp.message(F.text == "🎲 Бросить кубик")
async def roll(m: types.Message):
    if not state["game_started"]: return
    uid = m.from_user.id
    if uid != state["lobby"][state["current_turn"]]: return await m.answer("Не твой ход!")

    p = state["players"][uid]
    dice = random.randint(1, 6)
    p["position"] = (p["position"] + dice) % len(BOARD)
    cell = BOARD[p["position"]]
    
    text = f"🎲 **{p['name']}** выкинул {dice} и встал на **{cell['name']}**\n"
    kb = InlineKeyboardBuilder()

    # Логика клетки
    if cell["name"] == "💸 Налог":
        p["balance"] -= 100
        text += "💸 Налог: -100$"
    elif p["position"] in state["owners"] and state["owners"][p["position"]] != uid:
        owner_id = state["owners"][p["position"]]
        rent = cell["rent"]
        p["balance"] -= rent
        state["players"][owner_id]["balance"] += rent
        text += f"💰 Оплата аренды: {rent}$ игроку {state['players'][owner_id]['name']}"
    elif cell["price"] > 0 and p["position"] not in state["owners"]:
        kb.button(text=f"Купить за {cell['price']}$", callback_data=f"buy_{p['position']}")

    # Проверка на банкротство
    if p["balance"] < 0:
        text += "\n\n💀 **ВЫ БАНКРОТ!**"
        # Тут можно добавить логику удаления игрока

    state["current_turn"] = (state["current_turn"] + 1) % len(state["lobby"])
    await m.answer(text + "\n\n" + get_map(uid), reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def buy_property(c: types.CallbackQuery):
    idx = int(c.data.split("_")[1])
    uid = c.from_user.id
    p = state["players"][uid]
    if p["balance"] >= BOARD[idx]["price"]:
        p["balance"] -= BOARD[idx]["price"]
        state["owners"][idx] = uid
        await c.message.answer(f"✅ {p['name']} купил {BOARD[idx]['name']}!")
    await c.answer()

# --- ЗАПУСК ---

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

async def main():
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
