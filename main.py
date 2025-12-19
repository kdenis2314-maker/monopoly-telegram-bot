import asyncio, os, random
from flask import Flask, render_template_string
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- 1. НАСТРОЙКИ ---
TOKEN = "8265158957:AAF8LjmyLM4nsBEnLOvVSNRNzC6X-ZIbGzU"
PORT = int(os.environ.get("PORT", 10000))

# --- 2. КАРТА И ШАНСЫ ---
BOARD = [
    {"name": "🚩 СТАРТ", "price": 0, "icon": "🚩"},
    {"name": "🏘️ Улица Мира", "price": 100, "icon": "🏘️"},
    {"name": "❓ ШАНС", "price": 0, "icon": "🎲"},
    {"name": "🏢 Пр-т Ленина", "price": 150, "icon": "🏢"},
    {"name": "🛒 Магазин", "price": 200, "icon": "🛒"},
    {"name": "👮 Тюрьма", "price": 0, "icon": "👮"},
    {"name": "❓ ШАНС", "price": 0, "icon": "🎲"},
    {"name": "🏨 Отель 'Гранд'", "price": 300, "icon": "🏨"},
    {"name": "🌳 Парк Культуры", "price": 120, "icon": "🌳"},
    {"name": "🚉 Вокзал", "price": 250, "icon": "🚉"},
    {"name": "💎 Алмазный Фонд", "price": 400, "icon": "💎"},
    {"name": "🎡 Цирк", "price": 140, "icon": "🎡"}
]

CHANCES = [
    {"text": "🎰 Вы выиграли в лотерею!", "reward": 300},
    {"text": "💸 Налоговая проверка! Штраф.", "reward": -150},
    {"text": "🎁 День рождения! Подарки от банка.", "reward": 100},
    {"text": "📉 Кризис акций. Вы теряете деньги.", "reward": -200},
    {"text": "🛡️ Страховая выплата.", "reward": 50}
]

players = {}
lobby_players = []
game_active = False

# --- 3. ВЕБ-ИНТЕРФЕЙС ---
app = Flask(__name__)
@app.route('/')
def home(): return render_template_string("<body style='background:#121212;color:white;text-align:center'><h1>Monopoly Game is Live</h1></body>")

# --- 4. КЛАВИАТУРЫ ---
def get_game_control_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Бросить кубик", callback_query_data="roll_dice")],
        [InlineKeyboardButton(text="💰 Баланс", callback_query_data="check_balance"), InlineKeyboardButton(text="🏠 Имущество", callback_query_data="my_props")],
        [InlineKeyboardButton(text="🤝 Предложить обмен", callback_query_data="trade_start")],
        [InlineKeyboardButton(text="🏆 Топ", callback_query_data="show_top"), InlineKeyboardButton(text="🏃 Выход", callback_query_data="request_exit")]
    ])

# --- 5. ЛОГИКА БОТА ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

@dp.message(Command("monopoly"))
async def start_menu(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Начать сбор", callback_query_data="lobby_start")]])
    await m.answer("🏨 **MONOPOLY ONLINE**\n\nГотовы стать миллионером?", reply_markup=kb)

# --- МЕХАНИКА ХОДА И ШАНСОВ ---
@dp.callback_query(F.data == "roll_dice")
async def roll(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in lobby_players: return await call.answer("Вы не в игре!")

    steps = random.randint(1, 6)
    old_pos = players[uid]["pos"]
    new_pos = (old_pos + steps) % len(BOARD)
    players[uid]["pos"] = new_pos
    cell = BOARD[new_pos]

    res = f"🎲 **{players[uid]['name']}** передвинулся на **{steps}**\n📍 Остановка: {cell['icon']} **{cell['name']}**\n"

    # Логика ШАНСА
    if cell['name'] == "❓ ШАНС":
        event = random.choice(CHANCES)
        players[uid]['balance'] += event['reward']
        res += f"\n✨ **ШАНС:** {event['text']}\n💰 Изменение баланса: `{event['reward']}$`"
    
    # Логика покупки/аренды
    else:
        owner_id = next((pid for pid, pdata in players.items() if new_pos in pdata['owns']), None)
        if cell['price'] > 0 and owner_id is None:
            if players[uid]['balance'] >= cell['price']:
                players[uid]['balance'] -= cell['price']
                players[uid]['owns'].append(new_pos)
                res += f"\n💳 Куплено за {cell['price']}$"
        elif owner_id and owner_id != uid:
            rent = cell['price'] // 2
            players[uid]['balance'] -= rent
            players[owner_id]['balance'] += rent
            res += f"\n⚠️ Аренда {rent}$ для {players[owner_id]['name']}"

    await call.message.answer(res, reply_markup=get_game_control_kb())
    await call.answer()

# --- МЕХАНИКА ОБМЕНА (УПРОЩЕННАЯ) ---
@dp.callback_query(F.data == "trade_start")
async def trade_start(call: CallbackQuery):
    # Создаем кнопки с игроками для обмена
    kb = []
    for pid in lobby_players:
        if pid != call.from_user.id:
            kb.append([InlineKeyboardButton(text=f"🤝 Предложить {players[pid]['name']}", callback_query_data=f"trade_with_{pid}")])
    
    if not kb:
        return await call.answer("Нет других игроков для обмена!", show_alert=True)
    
    await call.message.edit_text("Кому вы хотите предложить сделку (200$ за одну случайную недвижимость)?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("trade_with_"))
async def trade_offer(call: CallbackQuery):
    target_id = int(call.data.split("_")[2])
    sender_id = call.from_user.id
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_query_data=f"trade_acc_{sender_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_query_data="trade_decl")
    ]])
    
    await bot.send_message(target_id, f"🤝 Игрок **{players[sender_id]['name']}** предлагает вам сделку!\nОн платит вам **200$**, а вы отдаете ему одну случайную недвижимость.", reply_markup=kb)
    await call.message.edit_text("⏳ Предложение отправлено...")

@dp.callback_query(F.data.startswith("trade_acc_"))
async def trade_accept(call: CallbackQuery):
    sender_id = int(call.data.split("_")[2])
    target_id = call.from_user.id
    
    if not players[target_id]['owns']:
        return await call.message.edit_text("❌ У вас нет недвижимости для обмена!")
    
    if players[sender_id]['balance'] < 200:
        return await call.message.edit_text("❌ У отправителя недостаточно денег!")

    # Процесс обмена
    prop_idx = players[target_id]['owns'].pop(random.randrange(len(players[target_id]['owns'])))
    players[sender_id]['owns'].append(prop_idx)
    players[sender_id]['balance'] -= 200
    players[target_id]['balance'] += 200
    
    await call.message.edit_text(f"✅ Сделка завершена! Вы получили 200$, а {players[sender_id]['name']} получил {BOARD[prop_idx]['name']}.")
    await bot.send_message(sender_id, f"✅ Сделка принята! Вы купили {BOARD[prop_idx]['name']} за 200$.")

# --- СИСТЕМНЫЕ ФУНКЦИИ ---
@dp.callback_query(F.data == "lobby_start")
async def lobby_start(call: CallbackQuery):
    global lobby_players, game_active
    lobby_players, game_active = [], False
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Вступить", callback_query_data="join_lobby")]])
    await call.message.edit_text("📢 Сбор открыт! Ждем минимум 2-х.", reply_markup=kb)

@dp.callback_query(F.data == "join_lobby")
async def join(call: CallbackQuery):
    if call.from_user.id not in lobby_players:
        lobby_players.append(call.from_user.id)
        players[call.from_user.id] = {"balance": 1500, "pos": 0, "name": call.from_user.first_name, "owns": []}
    
    kb = [[InlineKeyboardButton(text="✅ Вступить", callback_query_data="join_lobby")]]
    if len(lobby_players) >= 2:
        kb.append([InlineKeyboardButton(text="🏁 НАЧАТЬ", callback_query_data="start_match")])
    
    await call.message.edit_text(f"👥 Игроков: {len(lobby_players)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "start_match")
async def start_match(call: CallbackQuery):
    global game_active
    game_active = True
    await call.message.answer("🎉 Поехали! Управление ниже.", reply_markup=get_game_control_kb())
    await call.message.delete()

# --- ЗАПУСК ---
def run_web(): app.run(host='0.0.0.0', port=PORT)
async def main():
    Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
    
