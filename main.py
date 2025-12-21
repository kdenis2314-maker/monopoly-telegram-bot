import os
import asyncio
import aiosqlite
import logging
import random
import json
from datetime import datetime
from threading import Thread
from flask import Flask, render_template
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, URLInputFile, WebAppInfo

# --- [1] НАСТРОЙКИ И ПЕРЕМЕННЫЕ (ТВОЙ ОРИГИНАЛ) ---
API_TOKEN = os.environ.get("BOT_TOKEN")
if not API_TOKEN:
    logging.error("❌ BOT_TOKEN не найден в переменных окружения!")
    exit(1)

PORT = int(os.environ.get("PORT", 8083))
DEV_TAG = "@Whylovely05"
IS_ACTIVE = True
MAINTENANCE_MSG = "Бот обновляется, Темный принц уже исправляет это ♥️♥️"
BANNER = "┏━━━━━━━━━━━━━━━━━━┓\n┃  Monopoly Premium Edition  ┃\n┗━━━━━━━━━━━━━━━━━━┛"
MONOPOLY_IMG = "https://files.catbox.moe/o2809u.jpg"

STATS = {
    "active_games": 0,
    "total_players": 0,
    "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "version": "Premium v2.0 + AI"
}

WAITING_GAMES = {}
ACTIVE_GAMES = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- [ИНТЕГРАЦИЯ ИИ] ---
async def ai_commentator(event, name, balance=1500, value=None):
    """Искусственный интеллект для комментирования событий"""
    style = "дерзкий" if balance < 500 else "уважительный"
    phrases = {
        "gathering": [
            f"💰 {name} открывает бизнес-клуб! Кто готов рискнуть?",
            f"🎲 {name} ищет партнеров. Места ограничены!",
            f"🎯 {name} запускает сбор. Приготовьте кошельки!"
        ],
        "roll": [
            f"🎲 {name} бросает кости. ИИ предсказывает успех!",
            f"🎯 Кости в воздухе! При балансе ${balance} это волнительно, {name}."
        ],
        "jail": [
            f"⛓ {name}, Тюрьмыч ждал тебя. Присядь на 3 хода!",
            f"🚔 Наручники на {name}! Капитализм суров."
        ],
        "buy": [
            f"🏗 {name} расширяет империю! Конкуренты в ярости.",
            f"🏘 Поздравляю с покупкой, {name}! Отличный актив."
        ]
    }
    return random.choice(phrases.get(event, ["Ход принят..."]))

# --- [2] FLASK СЕРВЕР И ТВОЙ ПОЛНЫЙ HTML ---
@app.route('/')
def index():
    stats_copy = STATS.copy()
    stats_copy["active_games"] = len(ACTIVE_GAMES)
    stats_copy["waiting_games"] = len(WAITING_GAMES)
    return render_template('status.html', stats=stats_copy, bot_name="Monopoly Premium", 
                         domain=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost:' + str(PORT))}",
                         port=PORT, start_time=stats_copy["started"], dev_tag=DEV_TAG)

status_html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>МОНОПОЛИЯ ПРЕМИУМ - Статус</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: rgba(25, 25, 40, 0.9); border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); border: 1px solid #2a2a4a; }
        .header { text-align: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid #00ff88; }
        .header h1 { font-size: 2.8rem; background: linear-gradient(90deg, #00ff88, #00ccff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 2px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin-bottom: 40px; }
        .status-card { background: rgba(40, 40, 60, 0.7); border-radius: 15px; padding: 25px; border-left: 5px solid #00ff88; transition: transform 0.3s; }
        .info-line { display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
        .label { color: #a0a0ff; }
        .value.online { color: #00ff88; }
        .footer { text-align: center; margin-top: 40px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>МОНОПОЛИЯ ПРЕМИУМ</h1><h2>Система управления ботом</h2></div>
        <div class="status-grid">
            <div class="status-card">
                <div class="card-title">📊 Статус</div>
                <div class="info-line"><span class="label">Бот:</span><span class="value online">🟢 Онлайн</span></div>
                <div class="info-line"><span class="label">Активных игр:</span><span class="value">{{ stats.active_games }}</span></div>
            </div>
            <div class="status-card">
                <div class="card-title">⚙️ Система</div>
                <div class="info-line"><span class="label">Версия:</span><span class="value">{{ stats.version }}</span></div>
                <div class="info-line"><span class="label">Девелопер:</span><span class="value">{{ dev_tag }}</span></div>
            </div>
        </div>
        <div class="footer"><p>Developer: @Whylovely05</p></div>
    </div>
</body>
</html>'''

if not os.path.exists('templates'): os.makedirs('templates')
with open('templates/status.html', 'w', encoding='utf-8') as f: f.write(status_html)
# --- [3] ПОЛНАЯ ИГРОВАЯ КАРТА (ВСЕ 40 КЛЕТОК ИЗ ТВОЕГО ФАЙЛА) ---
BOARD = {
    0: ["СТАРТ", 0, 0, "SPECIAL"],
    1: ["Житная", 60, 4, "BROWN"],
    2: ["Общественная казна", 0, 0, "SPECIAL"],
    3: ["Нагатинская", 60, 4, "BROWN"],
    4: ["Подоходный налог", 0, 200, "TAX"],
    5: ["Рижская ж/д", 200, 25, "RAIL"],
    6: ["Варшавское ш.", 100, 6, "BLUE"],
    7: ["Шанс", 0, 0, "CHANCE"],
    8: ["Огородный пр.", 100, 6, "BLUE"],
    9: ["Рижская", 120, 8, "BLUE"],
    10: ["Тюрьма (Посещение)", 0, 0, "SPECIAL"],
    11: ["Курская", 140, 10, "PINK"],
    12: ["Электросеть", 150, 10, "UTIL"],
    13: ["Абрамцево", 140, 10, "PINK"],
    14: ["Пантелеевская", 160, 12, "PINK"],
    15: ["Казанская ж/д", 200, 25, "RAIL"],
    16: ["Вавилова", 180, 14, "ORANGE"],
    17: ["Общественная казна", 0, 0, "SPECIAL"],
    18: ["Тимирязевская", 180, 14, "ORANGE"],
    19: ["Лихоборы", 200, 16, "ORANGE"],
    20: ["Бесплатная стоянка", 0, 0, "SPECIAL"],
    21: ["Арбат", 220, 18, "RED"],
    22: ["Шанс", 0, 0, "CHANCE"],
    23: ["Полянка", 220, 18, "RED"],
    24: ["Сретенка", 240, 20, "RED"],
    25: ["Курская ж/д", 200, 25, "RAIL"],
    26: ["Ростовская", 260, 22, "YELLOW"],
    27: ["Рязанский пр.", 260, 22, "YELLOW"],
    28: ["Водопровод", 150, 10, "UTIL"],
    29: ["Новинский б-р", 280, 24, "YELLOW"],
    30: ["В ТЮРЬМУ", 0, 0, "SPECIAL"],
    31: ["Пушкинская", 300, 26, "GREEN"],
    32: ["Тверская", 300, 26, "GREEN"],
    33: ["Общественная казна", 0, 0, "SPECIAL"],
    34: ["Маяковского", 320, 28, "GREEN"],
    35: ["Ленинградская ж/д", 200, 25, "RAIL"],
    36: ["Шанс", 0, 0, "CHANCE"],
    37: ["Кутузовский", 350, 35, "DARKBLUE"],
    38: ["Сверхналог", 0, 100, "TAX"],
    39: ["Бродвей", 400, 50, "DARKBLUE"]
}

# --- [4] ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (ФИКС ОШИБОК) ---
async def init_db():
    try:
        async with aiosqlite.connect('monopoly_v2.db') as db:
            # Создаем таблицу игроков
            await db.execute("""CREATE TABLE IF NOT EXISTS players (
                chat_id int, 
                user_id int, 
                name text, 
                balance int DEFAULT 1500, 
                pos int DEFAULT 0, 
                jail int DEFAULT 0, 
                PRIMARY KEY(chat_id, user_id))""")
            
            # Создаем таблицу недвижимости
            await db.execute("""CREATE TABLE IF NOT EXISTS property (
                chat_id int, 
                cell_idx int, 
                owner_id int, 
                houses int DEFAULT 0, 
                PRIMARY KEY(chat_id, cell_idx))""")
            
            # Таблица достижений
            await db.execute("""CREATE TABLE IF NOT EXISTS awards (
                user_id int, 
                title text, 
                chat_id int)""")
            
            await db.commit()
        logger.info("✅ База данных и все таблицы успешно инициализированы")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

# --- [5] ВСПОМОГАТЕЛЬНЫЕ КЛАВИАТУРЫ ---
def get_main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Сбор игроков", callback_data="start_player_gathering")
    builder.button(text="📖 Правила", callback_data="show_rules")
    builder.button(text="👨‍💻 Девелопер", callback_data="show_dev_info")
    builder.button(text="🌐 Статус системы", web_app=WebAppInfo(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}"))
    builder.adjust(1)
    return builder.as_markup()
# --- [6] ЛОГИКА СБОРА ИГРОКОВ (ПОЛНЫЙ ПЕРЕНОС + AI) ---
@dp.callback_query(F.data == "start_player_gathering")
async def start_gathering(c: types.CallbackQuery):
    try:
        chat_id = c.message.chat.id
        if chat_id in WAITING_GAMES:
            return await c.answer("⚠️ Сбор игроков уже запущен в этом чате!", show_alert=True)
        
        # ИИ комментирует создание игры
        ai_msg = await ai_commentator("gathering", c.from_user.first_name)
        
        WAITING_GAMES[chat_id] = {
            "creator_id": c.from_user.id,
            "creator_name": c.from_user.first_name,
            "players": [{
                "id": c.from_user.id, 
                "name": c.from_user.first_name, 
                "username": c.from_user.username
            }],
            "message_id": c.message.message_id
        }
        
        await c.message.edit_text(
            f"🎮 <b>{ai_msg}</b>\n\n"
            f"Создатель: {c.from_user.first_name}\n"
            f"Участники: 1\n\n"
            f"✅ Нажмите кнопку ниже, чтобы войти в бизнес!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder()
                .button(text="✅ Присоединиться", callback_data=f"join_game_{chat_id}")
                .button(text="🚪 Выйти", callback_data=f"leave_game_{chat_id}")
                .button(text="▶️ Начать игру", callback_data=f"start_real_game_{chat_id}")
                .adjust(2, 1)
                .as_markup()
        )
        await c.answer()
    except Exception as e:
        logger.error(f"Ошибка в start_gathering: {e}")
        await c.answer(f"🤖 {MAINTENANCE_MSG}", show_alert=True)

@dp.callback_query(F.data.startswith("join_game_"))
async def join_game(c: types.CallbackQuery):
    try:
        chat_id = int(c.data.split("_")[2])
        game = WAITING_GAMES.get(chat_id)
        
        if not game:
            return await c.answer("❌ Игра больше не активна.", show_alert=True)
        
        if any(p['id'] == c.from_user.id for p in game['players']):
            return await c.answer("👀 Ты уже в списке участников!", show_alert=True)
        
        if len(game['players']) >= 6:
            return await c.answer("🚫 В игре может быть максимум 6 игроков.", show_alert=True)
        
        game['players'].append({
            "id": c.from_user.id, 
            "name": c.from_user.first_name, 
            "username": c.from_user.username
        })
        
        # Формируем список участников (как в твоем оригинале)
        players_text = ""
        for i, player in enumerate(game['players'], 1):
            players_text += f"{i}. {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"
            f"Создатель: {game['creator_name']}\n\n"
            f"{players_text}\n"
            f"✅ Нажмите 'Присоединиться' чтобы войти в игру\n"
            f"🚪 'Выйти из игры' - чтобы покинуть лобби\n"
            f"▶️ Создатель может начать игру когда все готовы",
            parse_mode="HTML",
            reply_markup=c.message.reply_markup
        )
        await c.answer(f"✅ Ты в деле! Игроков: {len(game['players'])}")
        
    except Exception as e:
        logger.error(f"Ошибка в join_game: {e}")
        await c.answer(f"🤖 {MAINTENANCE_MSG}", show_alert=True)

@dp.callback_query(F.data.startswith("leave_game_"))
async def leave_game(c: types.CallbackQuery):
    try:
        chat_id = int(c.data.split("_")[2])
        game = WAITING_GAMES.get(chat_id)
        
        if not game: return await c.answer("Игра не найдена")
        
        # Удаляем игрока
        game['players'] = [p for p in game['players'] if p['id'] != c.from_user.id]
        
        if not game['players']:
            del WAITING_GAMES[chat_id]
            return await c.message.edit_text("❌ Все игроки вышли, сбор отменен.")
            
        # Обновляем текст
        players_text = "\n".join([f"- {p['name']}" for p in game['players']])
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков:</b>\n\n{players_text}",
            parse_mode="HTML",
            reply_markup=c.message.reply_markup
        )
        await c.answer("Вы вышли из лобби.")
    except Exception as e:
        logger.error(f"Ошибка в leave_game: {e}")
# --- [7] ЗАПУСК ИГРЫ (СОЗДАНИЕ ПЕРСОНАЖЕЙ В БД) ---
@dp.callback_query(F.data.startswith("start_real_game_"))
async def start_real_game(c: types.CallbackQuery):
    try:
        chat_id = int(c.data.split("_")[3])
        game = WAITING_GAMES.get(chat_id)
        
        if not game:
            return await c.answer("❌ Сбор не найден.", show_alert=True)
        
        if c.from_user.id != game['creator_id']:
            return await c.answer("🚫 Только создатель может запустить игру!", show_alert=True)
        
        if len(game['players']) < 2:
            return await c.answer("👥 Нужно минимум 2 игрока для начала!", show_alert=True)
        
        # Регистрация игроков в базе данных
        async with aiosqlite.connect('monopoly_v2.db') as db:
            for player in game['players']:
                # INSERT OR IGNORE чтобы не сбросить баланс если игра уже была
                await db.execute("""
                    INSERT OR REPLACE INTO players (chat_id, user_id, name, balance, pos, jail)
                    VALUES (?, ?, ?, 1500, 0, 0)
                """, (chat_id, player['id'], player['name']))
            await db.commit()
        
        # ИИ комментирует старт
        ai_txt = await ai_commentator("start", game['creator_name'])
        
        # Переносим из ожидания в активные
        ACTIVE_GAMES[chat_id] = game
        del WAITING_GAMES[chat_id]
        
        kb = ReplyKeyboardBuilder()
        kb.button(text="🎲 Бросить кубик")
        kb.button(text="🏠 Построить дом")
        kb.button(text="📊 Мои активы")
        kb.button(text="❌ Скрыть меню")
        kb.adjust(2, 2)
        
        await c.message.answer(
            f"🚀 <b>{ai_txt}</b>\n\n"
            f"Все игроки получили по $1500. "
            f"Первым ходит <b>{game['players'][0]['name']}</b>!\n\n"
            f"Используйте кнопки внизу экрана.",
            parse_mode="HTML",
            reply_markup=kb.as_markup(resize_keyboard=True)
        )
        await c.message.delete()
        
    except Exception as e:
        logger.error(f"Ошибка при старте игры: {e}")
        await c.answer("Произошла ошибка при запуске БД.", show_alert=True)

# --- [8] ГЛАВНАЯ МЕХАНИКА: БРОСОК КУБИКА ---
@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice_logic(m: types.Message):
    try:
        chat_id = m.chat.id
        async with aiosqlite.connect('monopoly_v2.db') as db:
            # Ищем игрока в текущем чате
            res = await db.execute(
                "SELECT pos, balance, jail FROM players WHERE chat_id=? AND user_id=?", 
                (chat_id, m.from_user.id)
            )
            player_data = await res.fetchone()
            
            if not player_data:
                return await m.answer("Вы не участвуете в текущей игре! Нажмите /monopoly")
            
            pos, balance, jail = player_data
            
            # ПРОВЕРКА ТЮРЬМЫ
            if jail > 0:
                new_jail = jail - 1
                await db.execute(
                    "UPDATE players SET jail=? WHERE chat_id=? AND user_id=?", 
                    (new_jail, chat_id, m.from_user.id)
                )
                await db.commit()
                ai_j = await ai_commentator("jail", m.from_user.first_name)
                return await m.answer(f"<b>{ai_j}</b>\nОсталось сидеть: {new_jail} хода(ов).", parse_mode="HTML")

            # БРОСОК
            ai_roll = await ai_commentator("roll", m.from_user.first_name, balance)
            msg = await m.answer(f"<b>{ai_roll}</b>", parse_mode="HTML")
            dice = await m.answer_dice("🎲")
            
            # Ждем анимацию кубика
            await asyncio.sleep(3.5)
            
            dice_value = dice.dice.value
            old_pos = pos
            new_pos = (old_pos + dice_value) % 40
            
            # Проход через СТАРТ (+200)
            if new_pos < old_pos:
                balance += 200
                await m.answer("💰 Вы прошли через СТАРТ и получили $200!")

            # Обработка клетки ТЮРЬМА (поле 30)
            if new_pos == 30:
                new_pos = 10 # Переносим на поле тюрьмы
                jail = 3
                await m.answer("🚔 О нет! Вы попались на нарушении и отправляетесь в тюрьму на 3 хода!")

            # Обновляем БД
            await db.execute(
                "UPDATE players SET pos=?, balance=?, jail=? WHERE chat_id=? AND user_id=?", 
                (new_pos, balance, jail, chat_id, m.from_user.id)
            )
            await db.commit()
            
            # Инфо о клетке
            cell_info = BOARD.get(new_pos, ["Пустое поле", 0, 0, "SPECIAL"])
            await m.answer(
                f"📍 Игрок <b>{m.from_user.first_name}</b> переместился на:\n"
                f"<b>{new_pos} — {cell_info[0]}</b>\n\n"
                f"Ваш текущий баланс: ${balance}",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Ошибка в логике броска: {e}")
# --- [9] ЛОГИКА ПОКУПКИ НЕДВИЖИМОСТИ ---
@dp.message(F.text == "🏠 Построить дом")
async def buy_property_logic(m: types.Message):
    async with aiosqlite.connect('monopoly_v2.db') as db:
        res = await db.execute("SELECT pos, balance FROM players WHERE chat_id=? AND user_id=?", (m.chat.id, m.from_user.id))
        player = await res.fetchone()
        
        if not player: return await m.answer("Вы не в игре!")
        pos, balance = player
        
        cell = BOARD.get(pos)
        if not cell or cell[3] in ["SPECIAL", "TAX", "CHANCE"]:
            return await m.answer("На этой клетке нельзя ничего купить!")
        
        # Проверяем владельца
        prop_res = await db.execute("SELECT owner_id FROM property WHERE chat_id=? AND cell_idx=?", (m.chat.id, pos))
        owner = await prop_res.fetchone()
        
        if owner:
            return await m.answer(f"🏢 Это поле уже принадлежит другому магнату!")

        price = cell[1]
        if balance < price:
            return await m.answer(f"❌ Недостаточно денег! Нужно ${price}, а у вас ${balance}.")

        # Покупка
        new_balance = balance - price
        await db.execute("UPDATE players SET balance=? WHERE chat_id=? AND user_id=?", (new_balance, m.chat.id, m.from_user.id))
        await db.execute("INSERT INTO property (chat_id, cell_idx, owner_id) VALUES (?, ?, ?)", (m.chat.id, pos, m.from_user.id))
        await db.commit()
        
        ai_buy = await ai_commentator("buy", m.from_user.first_name)
        await m.answer(f"<b>{ai_buy}</b>\n\nВы купили <b>{cell[0]}</b> за ${price}!\nОстаток: ${new_balance}", parse_mode="HTML")

# --- [10] ПРОСМОТР АКТИВОВ ---
@dp.message(F.text == "📊 Мои активы")
async def show_assets(m: types.Message):
    async with aiosqlite.connect('monopoly_v2.db') as db:
        p_res = await db.execute("SELECT balance FROM players WHERE chat_id=? AND user_id=?", (m.chat.id, m.from_user.id))
        player = await p_res.fetchone()
        if not player: return await m.answer("Вы не в игре!")
        
        prop_res = await db.execute("SELECT cell_idx FROM property WHERE chat_id=? AND owner_id=?", (m.chat.id, m.from_user.id))
        properties = await prop_res.fetchall()
        
        text = f"👤 <b>Игрок:</b> {m.from_user.first_name}\n"
        text += f"💰 <b>Баланс:</b> ${player[0]}\n\n"
        text += "🏠 <b>Ваша недвижимость:</b>\n"
        
        if not properties:
            text += "— Пока ничего не куплено"
        else:
            for p in properties:
                text += f"• {BOARD[p[0]][0]}\n"
        
        await m.answer(text, parse_mode="HTML")

# --- [11] ФИНАЛЬНЫЙ ЗАПУСК ВСЕЙ СИСТЕМЫ ---
async def main():
    # 1. Запускаем базу данных
    await init_db()
    
    # 2. Поднимаем Flask сайт в отдельном потоке
    # Он будет доступен по адресу, который даст Render
    def run_flask():
        app.run(host="0.0.0.0", port=PORT)
    
    Thread(target=run_flask, daemon=True).start()
    logger.info(f"🌐 Сайт запущен на порту {PORT}")
    
    # 3. Запускаем бота
    logger.info("🤖 Бот Монополия вышел на связь!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        async with asyncio.Runner() as runner:
            asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")


@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    if not IS_ACTIVE:
        return await message.answer(f"🤖 {MAINTENANCE_MSG}")
    
    await message.answer_photo(
        photo=URLInputFile(MONOPOLY_IMG),
        caption=f"{BANNER}\n\nДобро пожаловать в Премиум Монополию! Используйте кнопки ниже для управления игрой.",
        reply_markup=get_main_menu_kb()
    )
