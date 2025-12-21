import asyncio
import random
import logging
import sys
from datetime import datetime
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, WebAppInfo

# Импортируем общие данные из первого файла
# В реальном проекте это должны быть общие модули
try:
    from main_and_web import (
        API_TOKEN, PORT, DEV_TAG, MAINTENANCE_MSG, BANNER,
        STATS, WAITING_GAMES, ACTIVE_GAMES, BOARD, init_db, get_cell_info
    )
except ImportError:
    # Если запускаем отдельно, создаем локальные переменные
    API_TOKEN = "YOUR_BOT_TOKEN"
    PORT = 8083
    DEV_TAG = "@Whylovely05"
    MAINTENANCE_MSG = "Бот обновляется"
    BANNER = "Monopoly Premium"
    STATS = {"active_games": 0, "total_players": 0, "version": "Premium v2.0"}
    WAITING_GAMES = {}
    ACTIVE_GAMES = {}
    BOARD = {}

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРЫ ---
def main_menu_kb():
    """Главное меню бота"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎮 Начать сбор игроков", callback_data="start_player_gathering")
    kb.button(text="📖 Правила игры", callback_data="show_rules")
    kb.button(text="👨‍💻 О девелопере", callback_data="show_developer")
    
    # WebApp кнопка
    domain = "localhost"  # В реальном коде получаем из окружения
    web_app_url = f"http://{domain}:{PORT}" if PORT else f"http://{domain}"
    kb.button(text="🌐 Статус системы", web_app=WebAppInfo(url=web_app_url))
    
    kb.adjust(1)
    return kb.as_markup()

def waiting_room_kb(chat_id, user_id=None, is_creator=False):
    """Клавиатура лобби ожидания"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Присоединиться", callback_data=f"join_game_{chat_id}")
    kb.button(text="🚪 Выйти", callback_data=f"leave_game_{chat_id}")
    if is_creator:
        kb.button(text="▶️ Начать игру", callback_data=f"start_real_game_{chat_id}")
    kb.adjust(2, 1)
    return kb.as_markup()

def game_main_kb():
    """Основная игровая клавиатура"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Бросить кубик")
    kb.button(text="🏠 Построить")
    kb.button(text="📊 Мои активы")
    kb.button(text="🤝 Торговля")
    kb.button(text="❌ Скрыть меню")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def hide_menu_kb():
    """Клавиатура для скрытия меню"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Показать меню")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

def trade_kb():
    """Клавиатура для торговли"""
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Предложить деньги", callback_data="trade_money")
    kb.button(text="🏠 Предложить недвижимость", callback_data="trade_property")
    kb.button(text="🤝 Обменять активы", callback_data="trade_assets")
    kb.button(text="❌ Отменить сделку", callback_data="trade_cancel")
    kb.adjust(2, 2)
    return kb.as_markup()

def build_kb(properties):
    """Клавиатура для строительства"""
    kb = InlineKeyboardBuilder()
    for prop in properties:
        kb.button(text=f"🏠 {prop['name']} ({prop['houses']}/5)", callback_data=f"build_{prop['id']}")
    kb.button(text="🏨 Построить отель", callback_data="build_hotel")
    kb.button(text="◀️ Назад", callback_data="back_to_game")
    kb.adjust(2)
    return kb.as_markup()

# --- ОСНОВНЫЕ КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    try:
        await message.answer(
            f"👋 Привет! Я бот для игры в Монополию!\n\n"
            f"Используйте команду /monopoly чтобы начать игру в группе.\n"
            f"Используйте /hide чтобы скрыть меню.\n\n"
            f"Разработчик: {DEV_TAG}"
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

@dp.message(Command("monopoly"))
async def cmd_monopoly(message: types.Message):
    """Главная команда для запуска игры"""
    try:
        await message.answer(
            f"{BANNER}\n\n🎲 <b>Monopoly Premium Edition</b>\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_monopoly: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

@dp.message(Command("hide"))
async def cmd_hide_menu(message: types.Message):
    """Команда для скрытия меню"""
    try:
        await message.answer(
            "✅ Меню скрыто. Чтобы вернуть меню, нажмите кнопку ниже или используйте /monopoly",
            reply_markup=hide_menu_kb()
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_hide: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Показать статистику бота"""
    try:
        stats_text = (
            f"📊 <b>Статистика Monopoly Premium:</b>\n\n"
            f"• Активных игр: {len(ACTIVE_GAMES)}\n"
            f"• Ожидающих игр: {len(WAITING_GAMES)}\n"
            f"• Всего игроков: {STATS['total_players']}\n"
            f"• Версия: {STATS['version']}\n"
            f"• Запущен: {STATS['started']}\n\n"
            f"👤 Разработчик: {DEV_TAG}"
        )
        await message.answer(stats_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка в cmd_stats: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

# --- ОБРАБОТЧИКИ КНОПОК МЕНЮ ---
@dp.message(F.text == "❌ Скрыть меню")
async def hide_menu_button(message: types.Message):
    """Обработка кнопки скрытия меню"""
    try:
        await message.answer(
            "✅ Меню скрыто. Чтобы вернуть меню, нажмите кнопку ниже или используйте /monopoly",
            reply_markup=hide_menu_kb()
        )
    except Exception as e:
        logger.error(f"Ошибка в hide_menu_button: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

@dp.message(F.text == "📱 Показать меню")
async def show_menu_button(message: types.Message):
    """Показ меню после скрытия"""
    try:
        await cmd_monopoly(message)
    except Exception as e:
        logger.error(f"Ошибка в show_menu_button: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

@dp.message(F.text == "🎲 Бросить кубик")
async def roll_dice_button(message: types.Message):
    """Обработка броска кубика"""
    try:
        chat_id = message.chat.id
        
        if chat_id not in ACTIVE_GAMES:
            await message.answer("⚠️ Активная игра не найдена в этом чате!")
            return
        
        game = ACTIVE_GAMES[chat_id]
        
        if not game.get("players"):
            await message.answer("⚠️ В игре нет игроков!")
            return
        
        # Определяем текущего игрока
        current_idx = game.get("current_player", 0)
        player = game["players"][current_idx]
        
        # Бросаем кубик
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        # Обновляем позицию
        current_pos = player.get("position", 0)
        new_pos = (current_pos + total) % 40
        
        # Определяем клетку
        cell_info = get_cell_info(new_pos)
        
        # Формируем сообщение
        message_text = (
            f"🎲 <b>Ход игрока {player['name']}:</b>\n"
            f"🎯 Кубик 1: {dice1}\n"
            f"🎯 Кубик 2: {dice2}\n"
            f"📊 Сумма: <b>{total}</b>\n"
            f"📍 Позиция: {current_pos} → {new_pos}\n"
            f"🏠 Клетка: <b>{cell_info.get('name', f'Клетка {new_pos}')}</b>\n"
        )
        
        # Добавляем информацию о клетке
        if cell_info.get("type") == "property":
            message_text += f"💰 Стоимость: {cell_info.get('price', 0)}$\n"
            message_text += f"🎨 Цвет: {cell_info.get('color', 'Нет')}"
        elif cell_info.get("type") == "special":
            message_text += f"📝 {cell_info.get('description', '')}"
        
        await message.answer(message_text, parse_mode="HTML")
        
        # Передаем ход следующему игроку
        next_idx = (current_idx + 1) % len(game["players"])
        ACTIVE_GAMES[chat_id]["current_player"] = next_idx
        
        # Уведомляем о следующем ходе
        next_player = game["players"][next_idx]
        await message.answer(
            f"➡️ Следующий ход: <b>{next_player['name']}</b>\n"
            f"Нажмите '🎲 Бросить кубик' для хода",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в roll_dice_button: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

@dp.message(F.text == "📊 Мои активы")
async def show_assets(message: types.Message):
    """Показать активы игрока"""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        if chat_id not in ACTIVE_GAMES:
            await message.answer("⚠️ Активная игра не найдена!")
            return
        
        # Здесь должна быть логика получения активов из БД
        # Временный заглушка
        assets_text = (
            f"💰 <b>Ваши активы:</b>\n\n"
            f"• Баланс: <b>1500$</b>\n"
            f"• Позиция: <b>0 (Старт)</b>\n"
            f"• Недвижимость: <b>0 объектов</b>\n"
            f"• Дома: <b>0</b>\n"
            f"• Отели: <b>0</b>\n\n"
            f"📈 Для покупки недвижимости бросайте кубик!"
        )
        
        await message.answer(assets_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка в show_assets: {e}")
        await message.answer(f"🤖 {MAINTENANCE_MSG}")

# --- ОБРАБОТЧИКИ CALLBACK-ЗАПРОСОВ ---
@dp.callback_query(F.data == "start_player_gathering")
async def start_gathering(c: types.CallbackQuery):
    """Начать сбор игроков"""
    try:
        chat_id = c.message.chat.id
        user_id = c.from_user.id
        
        if chat_id in WAITING_GAMES:
            await c.answer("⚠️ В этой группе уже идет сбор игроков!", show_alert=True)
            return
        
        # Создаем новую игру в ожидании
        WAITING_GAMES[chat_id] = {
            "creator_id": user_id,
            "creator_name": c.from_user.first_name,
            "players": [{
                "id": user_id,
                "name": c.from_user.first_name,
                "username": c.from_user.username,
                "position": 0,
                "balance": 1500
            }],
            "message_id": c.message.message_id,
            "created_at": datetime.now()
        }
        
        # Обновляем статистику
        STATS["active_games"] = len(ACTIVE_GAMES) + len(WAITING_GAMES)
        
        # Формируем список игроков
        players_text = "👥 <b>Игроки в ожидании:</b>\n"
        for player in WAITING_GAMES[chat_id]["players"]:
            players_text += f"• {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"
            f"Создатель: {c.from_user.first_name}\n\n"
            f"{players_text}\n"
            f"✅ Нажмите 'Присоединиться' чтобы войти в игру\n"
            f"🚪 'Выйти из игры' - чтобы покинуть лобби\n"
            f"▶️ Создатель может начать игру когда все готовы",
            parse_mode="HTML",
            reply_markup=waiting_room_kb(chat_id, user_id, is_creator=True)
        )
        
        await c.answer("🎮 Сбор игроков начат!")
        
    except Exception as e:
        logger.error(f"Ошибка в start_gathering: {e}")
        await c.answer(f"🤖 {MAINTENANCE_MSG}", show_alert=True)

@dp.callback_query(F.data.startswith("join_game_"))
async def join_game(c: types.CallbackQuery):
    """Присоединение к игре"""
    try:
        chat_id = int(c.data.split("_")[2])
        
        if chat_id not in WAITING_GAMES:
            await c.answer("⚠️ Игра не найдена или уже началась", show_alert=True)
            return
        
        game = WAITING_GAMES[chat_id]
        user_id = c.from_user.id
        
        # Проверяем, не в игре ли уже пользователь
        for player in game["players"]:
            if player["id"] == user_id:
                await c.answer("✅ Вы уже в игре!")
                return
        
        # Добавляем игрока
        game["players"].append({
            "id": user_id,
            "name": c.from_user.first_name,
            "username": c.from_user.username,
            "position": 0,
            "balance": 1500
        })
        
        # Обновляем сообщение
        players_text = "👥 <b>Игроки в ожидании:</b>\n"
        for player in game["players"]:
            players_text += f"• {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        is_creator = (user_id == game["creator_id"])
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"
            f"Создатель: {game['creator_name']}\n\n"
            f"{players_text}\n"
            f"✅ Нажмите 'Присоединиться' чтобы войти в игру\n"
            f"🚪 'Выйти из игры' - чтобы покинуть лобби\n"
            f"▶️ Создатель может начать игру когда все готовы",
            parse_mode="HTML",
            reply_markup=waiting_room_kb(chat_id, user_id, is_creator=is_creator)
        )
        
        await c.answer(f"🎮 Вы присоединились! Игроков: {len(game['players'])}")
        
    except Exception as e:
        logger.error(f"Ошибка в join_game: {e}")
        await c.answer(f"🤖 {MAINTENANCE_MSG}", show_alert=True)

@dp.callback_query(F.data.startswith("leave_game_"))
async def leave_game(c: types.CallbackQuery):
    """Выход из игры"""
    try:
        chat_id = int(c.data.split("_")[2])
        
        if chat_id not in WAITING_GAMES:
            await c.answer("⚠️ Игра не найдена", show_alert=True)
            return
        
        game = WAITING_GAMES[chat_id]
        user_id = c.from_user.id
        
        # Удаляем игрока
        original_count = len(game["players"])
        game["players"] = [p for p in game["players"] if p["id"] != user_id]
        
        # Если игроков не осталось
        if not game["players"]:
            del WAITING_GAMES[chat_id]
            await c.message.edit_text("❌ Игра отменена - все игроки вышли")
            await c.answer("Игра отменена")
            return
        
        # Если вышел создатель, назначаем нового
        if user_id == game["creator_id"]:
            new_creator = game["players"][0]
            game["creator_id"] = new_creator["id"]
            game["creator_name"] = new_creator["name"]
        
        # Обновляем сообщение
        players_text = "👥 <b>Игроки в ожидании:</b>\n"
        for player in game["players"]:
            players_text += f"• {player['name']}"
            if player.get('username'):
                players_text += f" (@{player['username']})"
            players_text += "\n"
        
        is_creator = (c.from_user.id == game["creator_id"])
        
        await c.message.edit_text(
            f"🎮 <b>Сбор игроков начат!</b>\n"
            f"Создатель: {game['creator_name']}\n\n"
            f"{players_text}\n"
            f"✅ Нажмите 'Присоединиться' чтобы войти в игру\n"
            f"🚪 'Выйти из игры' - чтобы покинуть лобби\n"
            f"▶️ Создатель может начать игру когда все готовы",
            parse_mode="HTML",
            reply_markup=waiting_room_kb(chat_id, c.from_user.id, is_creator=is_creator)
        )
        
        await c.answer(f"🚪 Вы вышли. Игроков: {len(game['players'])}")
        
    except Exception as e:
        logger.error(f"Ошибка в leave_game: {e}")
        await c.answer(f"🤖 {MAINTENANCE_MSG}", show_alert=True)

@dp.callback_query(F.data.startswith("start_real_game_"))
async def start_real_game(c: types.CallbackQuery):
    """Начать реальную игру"""
    try:
        chat_id = int(c.data.split("_")[3])
        
        if chat_id not in WAITING_GAMES:
            await c.answer("⚠️ Игра не найдена", show_alert=True)
            return
        
        game = WAITING_GAMES[chat_id]
        
        # Проверяем права создателя
        if c.from_user.id != game["creator_id"]:
            await c.answer("⚠️ Только создатель игры может её начать!", show_alert=True)
            return
        
        # Проверяем количество игроков
        if len(game["players"]) < 2:
            await c.answer("⚠️ Нужно минимум 2 игрока для начала игры!", show_alert=True)
            return
        
        # Переносим игру в активные
        ACTIVE_GAMES[chat_id] = {
            "players": game["players"],
            "current_player": 0,
            "started_at": datetime.now(),
            "creator_id": game["creator_id"],
            "creator_name": game["creator_name"],
            "turn": 1
        }
        
        # Удаляем из ожидающих
        del WAITING_GAMES[chat_id]
        
        # Обновляем статистику
        STATS["total_players"] += len(ACTIVE_GAMES[chat_id]["players"])
        STATS["active_games"] = len(ACTIVE_GAMES)
        
        # Формируем список игроков
        players_list = "\n".join([f"• {p['name']}" for p in ACTIVE_GAMES[chat_id]["players"]])
        
        # Отправляем сообщение о начале игры
        await c.message.edit_text(
            f"🎉 <b>Игра началась!</b>\n\n"
            f"<b>Участники:</b>\n{players_list}\n\n"
            f"💰 Стартовый баланс: <b>1500$</b>\n"
            f"🎲 Первым ходит: <b>{ACTIVE_GAMES[chat_id]['players'][0]['name']}</b>\n"
            f"🔄 Ход: <b>1</b>\n\n"
            f"<i>Используйте меню ниже для управления игрой</i>",
            parse_mode="HTML"
        )
        
        # Отправляем игровое меню
        first_player = ACTIVE_GAMES[chat_id]["players"][0]
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎮 <b>Игра началась!</b>\n\n"
                 f"📢 <b>{first_player['name']}</b>, ваш ход первый!\n"
                 f"Нажмите '🎲 Бросить кубик' чтобы сделать ход",
            parse_mode="HTML",
            reply_markup=game_main_kb()
        )
        
        await c.answer("🎮 Игра началась!")
        
    except Exception as e:
        logger.error(f"Ошибка в start_real_game: {e}")
        await c.answer(f"🤖 {MAINTENANCE_MSG}", show_alert=True)

@dp.callback_query(F.data == "show_rules")
async def show_rules(c: types.CallbackQuery):
    """Показать правила игры"""
    try:
        rules_text = (
            "📖 <b>Правила Monopoly Premium:</b>\n\n"
            "1. 🏁 Каждый игрок начинает с <b>1500$</b> на позиции <b>Старт</b>\n"
            "2. 🎲 По очереди бросайте кубик и передвигайтесь по полю\n"
            "3. 🏠 При попадании на свободную клетку можете её купить\n"
            "4. 💰 При попадании на чужую клетку платите аренду владельцу\n"
            "5. 🎨 Собирайте наборы одного цвета для увеличения аренды\n"
            "6. 🏘️ Стройте дома (до 4) и отели для увеличения доходов\n"
            "7. 🏦 Цель - остаться последним непобанкротившимся игроком\n\n"
            "🎯 <b>Особенности Premium версии:</b>\n"
            "• 🌐 Web-статистика в реальном времени\n"
            "• 🏆 Система достижений и наград\n"
            "• 🤝 Поддержка торговли между игроками\n"
            "• 💾 Автосохранение прогресса в БД\n"
            "• 👥 Поддержка до 8 игроков одновременно\n\n"
            "⚠️ <b>Важно:</b>\n"
            "• Минимум 2 игрока для начала\n"
            "• Используйте /hide чтобы скрыть меню\n"
            "• Игра сохраняется автоматически"
        )
        
        # Создаем клавиатуру для правил
        kb = InlineKeyboardBuilder()
        kb.button(text="◀️ Назад в меню", callback
