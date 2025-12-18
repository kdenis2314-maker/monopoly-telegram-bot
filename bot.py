"""
🎩 МОНОПОЛИЯ ПРЕМИУМ - только для групп 🎩
Версия для Render.com с Webhook
Поддерживает python-telegram-bot==20.7
"""

import os
import json
import random
import logging
import traceback
import html
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from threading import Thread
from queue import Queue

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("⚠️ ВНИМАНИЕ: Переменная окружения BOT_TOKEN не установлена!")
    print("ℹ️ Добавьте переменную BOT_TOKEN в настройках Render")
    print("ℹ️ Получить токен: @BotFather в Telegram -> /newbot")

RENDER_DOMAIN = os.environ.get('RENDER_DOMAIN', 'https://monopoly-telegram-bot-7.onrender.com')
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"{RENDER_DOMAIN}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 10000))

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище логов для веб-интерфейса
web_logs = []
MAX_WEB_LOGS = 100

def add_web_log(message: str, level: str = "INFO"):
    """Добавляет лог для отображения в веб-интерфейсе"""
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
        
        # Печатаем в консоль
        print(f"[{timestamp}] {level}: {message}")
        
        # Добавляем в список
        web_logs.append(log_entry)
        
        # Ограничиваем размер
        if len(web_logs) > MAX_WEB_LOGS:
            web_logs.pop(0)
            
    except Exception as e:
        print(f"Ошибка в add_web_log: {e}")

# ========== ТЕСТИРУЕМ add_web_log ==========
print("=" * 50)
print("🟢 ТЕСТИРУЕМ add_web_log...")
add_web_log("🟢 ТЕСТ: функция add_web_log работает", "DEBUG")
print(f"🟢 РЕЗУЛЬТАТ: web_logs содержит {len(web_logs)} записей")
print("=" * 50)

print("=" * 60)
print("🎩 МОНОПОЛИЯ ПРЕМИУМ - Telegram Bot")
print("=" * 60)
print(f"📅 Время запуска: {datetime.now()}")
print(f"📋 Токен установлен: {'✅ Да' if TOKEN else '❌ Нет'}")
print("=" * 60)
print("✅ Базовая инициализация завершена")
print("=" * 60)

# ========== FLASK ДЛЯ WEBHOOK И АКТИВНОСТИ ==========
from flask import Flask, request, render_template_string

# Создаем Flask приложение
flask_app = Flask(__name__)

# ========== ИНИЦИАЛИЗАЦИЯ PYTHON-TELEGRAM-BOT v20.7 ==========
print("\n🤖 ИНИЦИАЛИЗАЦИЯ PYTHON-TELEGRAM-BOT v20.7...")
print("=" * 50)

# Глобальные переменные для PTB
application = None  # Updater
bot = None
dispatcher = None

if TOKEN:
    try:
        print("1. Импортируем модули для PTB v20...")
        from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Updater, CommandHandler, CallbackQueryHandler, 
            MessageHandler, Filters, CallbackContext
        )
        from telegram.error import TelegramError
        print("   ✅ Модули импортированы")
        
        print("2. Создаем Updater...")
        # Для PTB v20.x используем правильный синтаксис
        updater = Updater(token=TOKEN, use_context=True)
        application = updater
        bot = updater.bot
        dispatcher = updater.dispatcher
        print(f"   ✅ Updater создан")
        print(f"   ✅ Bot ID: {bot.id}")
        
        # Проверяем бота
        bot_info = bot.get_me()
        print(f"   ✅ Бот: @{bot_info.username}")
        
        add_web_log(f"🤖 Бот @{bot_info.username} инициализирован (PTB v20.7)", "INFO")
        
    except Exception as e:
        print(f"❌ ФАТАЛЬНАЯ ошибка инициализации PTB: {e}")
        traceback.print_exc()
        application = None
        bot = None
        dispatcher = None
        add_web_log(f"❌ Фатальная ошибка PTB: {e}", "ERROR")
else:
    print("⚠️  Токен не установлен, PTB не инициализирован")
    application = None
    bot = None
    dispatcher = None

print(f"📊 Итог: application = {application is not None}")
print("=" * 50)
print("✅ PTB инициализация завершена")
print("=" * 50)

# ===================== КОНФИГУРАЦИЯ ИГРЫ =====================
START_MONEY = 1500
MAX_PLAYERS = 6
BOARD_SIZE = 40

# Эмодзи для оформления
EMOJI = {
    "start": "🚀",
    "property": "🏠",
    "railroad": "🚂",
    "utility": "⚡",
    "jail": "🚓",
    "chance": "🎭",
    "tax": "💰",
    "parking": "🅿️",
    "dice": "🎲",
    "money": "💵",
    "player": "👤",
    "house": "🏡",
    "hotel": "🏨",
    "trade": "🤝",
    "auction": "🔨",
    "bank": "🏦",
    "go": "🏁"
}

# Игровое поле (полная версия)
BOARD = [
    {"name": f"{EMOJI['go']} СТАРТ", "type": "start", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Старая дорога", "type": "property", "price": 60, "color": "brown", "rent": [2, 10, 30, 90, 160, 250]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Белая улица", "type": "property", "price": 60, "color": "brown", "rent": [4, 20, 60, 180, 320, 450]},
    {"name": f"{EMOJI['tax']} Налог на доход", "type": "tax", "price": 200, "color": "none"},
    {"name": f"{EMOJI['railroad']} Вокзал Южный", "type": "railroad", "price": 200, "color": "railroad", "rent": [25, 50, 100, 200]},
    {"name": f"{EMOJI['property']} Таганская", "type": "property", "price": 100, "color": "lightblue", "rent": [6, 30, 90, 270, 400, 550]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Варшавское шоссе", "type": "property", "price": 100, "color": "lightblue", "rent": [6, 30, 90, 270, 400, 550]},
    {"name": f"{EMOJI['property']} Полянка", "type": "property", "price": 120, "color": "lightblue", "rent": [8, 40, 100, 300, 450, 600]},
    {"name": f"{EMOJI['jail']} ТЮРЬМА", "type": "jail", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Рублевское шоссе", "type": "property", "price": 140, "color": "pink", "rent": [10, 50, 150, 450, 625, 750]},
    {"name": f"{EMOJI['utility']} Электростанция", "type": "utility", "price": 150, "color": "utility", "rent": [4, 10]},
    {"name": f"{EMOJI['property']} Улица Арбат", "type": "property", "price": 140, "color": "pink", "rent": [10, 50, 150, 450, 625, 750]},
    {"name": f"{EMOJI['property']} Смоленская площадь", "type": "property", "price": 160, "color": "pink", "rent": [12, 60, 180, 500, 700, 900]},
    {"name": f"{EMOJI['railroad']} Вокзал Северный", "type": "railroad", "price": 200, "color": "railroad", "rent": [25, 50, 100, 200]},
    {"name": f"{EMOJI['property']} Малая Бронная", "type": "property", "price": 180, "color": "orange", "rent": [14, 70, 200, 550, 750, 950]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Большая Бронная", "type": "property", "price": 180, "color": "orange", "rent": [14, 70, 200, 550, 750, 950]},
    {"name": f"{EMOJI['property']} Тверской бульвар", "type": "property", "price": 200, "color": "orange", "rent": [16, 80, 220, 600, 800, 1000]},
    {"name": f"{EMOJI['parking']} БЕСПЛАТНАЯ ПАРКОВКА", "type": "parking", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Пушкинская", "type": "property", "price": 220, "color": "red", "rent": [18, 90, 250, 700, 875, 1050]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Малая Дмитровка", "type": "property", "price": 220, "color": "red", "rent": [18, 90, 250, 700, 875, 1050]},
    {"name": f"{EMOJI['property']} Большая Дмитровка", "type": "property", "price": 240, "color": "red", "rent": [20, 100, 300, 750, 925, 1100]},
    {"name": f"{EMOJI['railroad']} Вокзал Западный", "type": "railroad", "price": 200, "color": "railroad", "rent": [25, 50, 100, 200]},
    {"name": f"{EMOJI['property']} Садовая-Кудринская", "type": "property", "price": 260, "color": "yellow", "rent": [22, 110, 330, 800, 975, 1150]},
    {"name": f"{EMOJI['property']} Большая Садовая", "type": "property", "price": 260, "color": "yellow", "rent": [22, 110, 330, 800, 975, 1150]},
    {"name": f"{EMOJI['utility']} Водокачка", "type": "utility", "price": 150, "color": "utility", "rent": [4, 10]},
    {"name": f"{EMOJI['property']} Сретенка", "type": "property", "price": 280, "color": "yellow", "rent": [24, 120, 360, 850, 1025, 1200]},
    {"name": f"{EMOJI['jail']} ОТПРАВЛЯЙТЕСЬ В ТЮРЬМУ", "type": "go_to_jail", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Пречистенка", "type": "property", "price": 300, "color": "green", "rent": [26, 130, 390, 900, 1100, 1275]},
    {"name": f"{EMOJI['property']} Остоженка", "type": "property", "price": 300, "color": "green", "rent": [26, 130, 390, 900, 1100, 1275]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Волхонка", "type": "property", "price": 320, "color": "green", "rent": [28, 150, 450, 1000, 1200, 1400]},
    {"name": f"{EMOJI['railroad']} Вокзал Восточный", "type": "railroad", "price": 200, "color": "railroad", "rent": [25, 50, 100, 200]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Шереметьевская", "type": "property", "price": 350, "color": "darkblue", "rent": [35, 175, 500, 1100, 1300, 1500]},
    {"name": f"{EMOJI['tax']} СУПЕРНАЛОГ", "type": "tax", "price": 100, "color": "none"},
    {"name": f"{EMOJI['property']} Рождественка", "type": "property", "price": 400, "color": "darkblue", "rent": [50, 200, 600, 1400, 1700, 2000]}
]

# Хранилище игр {chat_id: game_data}
games_storage = {}

# Карточки шанса
CHANCE_CARDS = [
    {"text": "Банковская ошибка в вашу пользу. Получите $200.", "money": 200, "move": 0, "jail": False},
    {"text": "Отправляйтесь в тюрьму. Отправляйтесь прямо в тюрьму.", "money": 0, "move": 0, "jail": True},
    {"text": "Отправляйтесь на Старую дорогу. Если вы проходите Старт, получите $200.", "money": 0, "move": 1, "jail": False},
    {"text": "Штраф за превышение скорости. Заплатите $15.", "money": -15, "move": 0, "jail": False},
    {"text": "Вы получили наследство. Получите $100.", "money": 100, "move": 0, "jail": False},
    {"text": "Отправляйтесь на Варшавское шоссе.", "money": 0, "move": 8, "jail": False},
    {"text": "Вас оштрафовали за парковку. Заплатите $10.", "money": -10, "move": 0, "jail": False},
    {"text": "Вы выиграли конкурс красоты. Получите $10.", "money": 10, "move": 0, "jail": False},
    {"text": "Пройдите вперед на 3 клетки.", "money": 0, "move": 3, "jail": False},
    {"text": "Вернитесь назад на 2 клетки.", "money": 0, "move": -2, "jail": False},
    {"text": "Получите дивиденды по акциям $50.", "money": 50, "move": 0, "jail": False},
    {"text": "Оплатите страховку $50.", "money": -50, "move": 0, "jail": False},
    {"text": "Вы заняли второе место в конкурсе. Получите $10.", "money": 10, "move": 0, "jail": False},
    {"text": "С Днем рождения! Получите $10 от каждого игрока.", "money": 10, "move": 0, "jail": False},
    {"text": "Отправляйтесь в ближайшую тюрьму.", "money": 0, "move": 10, "jail": False}
]

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================

def create_board_visual(game: dict) -> str:
    """Создает визуализацию поля"""
    board_lines = []
    
    for i in range(0, len(BOARD), 10):
        row = BOARD[i:i+10]
        line = ""
        for cell in row:
            idx = BOARD.index(cell)
            owner = game['board_state'][idx]['owner']
            houses = game['board_state'][idx]['houses']
            
            # Сокращаем название
            name_parts = cell['name'].split()
            short_name = name_parts[-1] if len(name_parts) > 1 else cell['name'][:8]
            
            if owner is not None and owner in game['players']:
                owner_color = game['players'][owner]['color']
                cell_display = f"{owner_color}{short_name}"
            else:
                cell_display = f"⬜{short_name}"
            
            # Добавляем дома
            if houses > 0:
                house_emoji = "🏨" if houses >= 5 else "🏡" * min(houses, 4)
                cell_display += house_emoji
            
            line += f"{cell_display:10}"
        board_lines.append(line)
    
    return "\n".join(board_lines)

def calculate_rent(game: dict, property_idx: int, owner_id: int) -> int:
    """Расчет арендной платы"""
    cell = BOARD[property_idx]
    state = game['board_state'][property_idx]
    
    if cell['type'] == 'property':
        # Базовый расчет для улиц
        houses = state['houses']
        if houses == 0:
            # Проверяем монополию
            color = cell['color']
            same_color_cells = [i for i, c in enumerate(BOARD) 
                              if c.get('color') == color and c['type'] == 'property']
            
            has_monopoly = all(
                game['board_state'][i]['owner'] == owner_id 
                for i in same_color_cells
            )
            
            if has_monopoly:
                return cell['rent'][0] * 2  # Двойная аренда при монополии
            else:
                return cell['rent'][0]
        else:
            # С домами/отелями
            rent_idx = min(houses, 5)  # 5 = отель
            return cell['rent'][rent_idx]
    
    elif cell['type'] == 'railroad':
        # Считаем количество вокзалов
        railroads_owned = sum(
            1 for i, c in enumerate(BOARD) 
            if c['type'] == 'railroad' and game['board_state'][i]['owner'] == owner_id
        )
        rent_idx = min(railroads_owned - 1, 3)
        return cell['rent'][rent_idx]
    
    elif cell['type'] == 'utility':
        # Электростанция/водокачка
        utilities_owned = sum(
            1 for i, c in enumerate(BOARD) 
            if c['type'] == 'utility' and game['board_state'][i]['owner'] == owner_id
        )
        
        # Бросаем кубик для множителя
        dice_roll = random.randint(1, 6) + random.randint(1, 6)
        
        if utilities_owned == 1:
            return dice_roll * 4
        else:  # 2 utilities
            return dice_roll * 10
    
    return 0

def check_monopoly(game: dict, player_id: int, color: str) -> bool:
    """Проверяет, собрал ли игрок монополию"""
    same_color_cells = [i for i, c in enumerate(BOARD) 
                       if c.get('color') == color and c['type'] == 'property']
    
    if not same_color_cells:
        return False
    
    has_monopoly = all(
        game['board_state'][i]['owner'] == player_id 
        for i in same_color_cells
    )
    
    if has_monopoly:
        player = game['players'][player_id]
        color_name = {
            'brown': 'коричневые',
            'lightblue': 'голубые', 
            'pink': 'розовые',
            'orange': 'оранжевые',
            'red': 'красные',
            'yellow': 'желтые',
            'green': 'зеленые',
            'darkblue': 'синие'
        }.get(color, color)
        
        add_web_log(f"Игрок {player_id} собрал монополию {color_name}", "INFO")
    
    return has_monopoly

def get_chance_card(player: dict, game: dict) -> dict:
    """Возвращает случайную карточку шанса"""
    card = random.choice(CHANCE_CARDS)
    
    if card.get('jail'):
        player['in_jail'] = True
        player['position'] = 10  # Тюрьма
        player['jail_turns'] = 0
    
    return card

def next_turn(game: dict, chat_id: int, context: CallbackContext):
    """Переход к следующему игроку"""
    try:
        if not game['turn_order']:
            return
        
        # Проверяем банкротство текущего игрока
        current_player = game['players'][game['current_player']]
        if current_player['balance'] < 0 and not current_player['is_bankrupt']:
            handle_bankruptcy(game, game['current_player'], chat_id, context)
        
        # Удаляем банкротов из порядка хода
        game['turn_order'] = [
            player_id for player_id in game['turn_order'] 
            if not game['players'][player_id]['is_bankrupt']
        ]
        
        if not game['turn_order']:
            end_game(game, chat_id, context)
            return
        
        # Проверяем, остался ли только один игрок
        active_players = [p for p in game['players'].values() if not p['is_bankrupt']]
        if len(active_players) == 1:
            end_game(game, chat_id, context)
            return
        
        # Находим следующего игрока
        current_idx = game['turn_order'].index(game['current_player'])
        next_idx = (current_idx + 1) % len(game['turn_order'])
        game['current_player'] = game['turn_order'][next_idx]
        
        next_player = game['players'][game['current_player']]
        
        add_web_log(f"Переход хода к игроку {next_player['id']} в чате {chat_id}", "INFO")
        
        # Отправляем сообщение о следующем ходе
        context.bot.send_message(
            chat_id=chat_id,
            text=f"""🎲 *СЛЕДУЮЩИЙ ХОД:*

{next_player['color']} @{next_player['username']}
💰 Баланс: ${next_player['balance']}
📍 Позиция: {BOARD[next_player['position']]['name']}
{"🚓 В ТЮРМЕ" if next_player['in_jail'] else ""}

👇 Ваш ход!""",
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(game['current_player'])
        )
        
    except Exception as e:
        error_msg = f"Ошибка в next_turn: {str(e)}"
        add_web_log(error_msg, "ERROR")

def handle_bankruptcy(game: dict, player_id: int, chat_id: int, context: CallbackContext):
    """Обработка банкротства игрока"""
    try:
        player = game['players'][player_id]
        player['is_bankrupt'] = True
        
        # Освобождаем собственность
        for property_idx in player['properties']:
            game['board_state'][property_idx]['owner'] = None
            game['board_state'][property_idx]['houses'] = 0
        
        player['properties'] = []
        
        add_web_log(f"Игрок {player_id} обанкротился в чате {chat_id}", "WARNING")
        
        context.bot.send_message(
            chat_id=chat_id,
            text=f"💀 *БАНКРОТСТВО!*\n\n"
                 f"{player['color']} @{player['username']} обанкротился!\n"
                 f"Его собственность возвращается банку.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = f"Ошибка в handle_bankruptcy: {str(e)}"
        add_web_log(error_msg, "ERROR")

def end_game(game: dict, chat_id: int, context: CallbackContext):
    """Завершение игры"""
    try:
        game['status'] = 'finished'
        
        # Находим победителя
        active_players = [p for p in game['players'].values() if not p['is_bankrupt']]
        
        if not active_players:
            winner_text = "❌ Все игроки обанкротились!"
        elif len(active_players) == 1:
            winner = active_players[0]
            winner_text = f"""🏆 *ПОБЕДИТЕЛЬ!*

{winner['color']} @{winner['username']}
💰 Финальный баланс: ${winner['balance']}
🏠 Собственность: {len(winner['properties'])} улиц

Поздравляем победителя! 🎉"""
        else:
            # Считаем общую стоимость имущества
            players_with_assets = []
            for player in active_players:
                total_assets = player['balance']
                for prop_idx in player['properties']:
                    cell = BOARD[prop_idx]
                    total_assets += cell['price']
                    # Добавляем стоимость домов
                    houses = game['board_state'][prop_idx]['houses']
                    if houses < 5:
                        total_assets += houses * 50  # Дома по $50
                    else:
                        total_assets += 4 * 50 + 200  # 4 дома + отель
                
                players_with_assets.append((player, total_assets))
            
            # Сортируем по убыванию активов
            players_with_assets.sort(key=lambda x: x[1], reverse=True)
            winner = players_with_assets[0][0]
            winner_assets = players_with_assets[0][1]
            
            winner_text = f"""🏆 *ПОБЕДИТЕЛЬ!*

{winner['color']} @{winner['username']}
💰 Общие активы: ${winner_assets}
🏠 Собственность: {len(winner['properties'])} улиц

Поздравляем победителя! 🎉"""
        
        add_web_log(f"Игра завершена в чате {chat_id}. Победитель: {winner.get('username', 'unknown') if 'winner' in locals() else 'unknown'}", "INFO")
        
        # Отправляем финальное сообщение
        context.bot.send_message(
            chat_id=chat_id,
            text=f"""🎮 *ИГРА ЗАВЕРШЕНА!*

{winner_text}

🎩 Спасибо за игру в Монополию!""",
            parse_mode='Markdown'
        )
        
        # Удаляем игру из хранилища через 5 минут
        def cleanup_game():
            import time
            time.sleep(300)  # 5 минут
            if chat_id in games_storage and games_storage[chat_id]['status'] == 'finished':
                del games_storage[chat_id]
                add_web_log(f"Игра удалена из хранилища (чат {chat_id})", "INFO")
        
        # Запускаем в отдельном потоке
        cleanup_thread = Thread(target=cleanup_game)
        cleanup_thread.start()
            
    except Exception as e:
        error_msg = f"Ошибка в end_game: {str(e)}"
        add_web_log(error_msg, "ERROR")

# ===================== КЛАВИАТУРЫ =====================

def get_add_to_group_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Клавиатура для добавления в группу"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"➕ ДОБАВИТЬ В ГРУППУ", 
            url=f"https://t.me/{bot_username}?startgroup=true"
        )],
        [InlineKeyboardButton("📋 Инструкция", callback_data="how_to_play")]
    ])

def get_lobby_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Клавиатура лобби"""
    player_count = 0
    if chat_id in games_storage and 'players' in games_storage[chat_id]:
        player_count = len(games_storage[chat_id]['players'])
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ ПРИСОЕДИНИТЬСЯ", callback_data=f"join_{chat_id}")],
        [InlineKeyboardButton(f"🎮 НАЧАТЬ ({player_count}/6)", callback_data=f"start_{chat_id}")],
        [InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data=f"cancel_{chat_id}")]
    ])

def get_game_keyboard(player_id: int) -> InlineKeyboardMarkup:
    """Основная игровая клавиатура"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJI['dice']} БРОСИТЬ КУБИКИ", callback_data=f"roll_{player_id}")],
        [
            InlineKeyboardButton(f"{EMOJI['money']} БАЛАНС", callback_data=f"balance_{player_id}"),
            InlineKeyboardButton(f"{EMOJI['property']} ИМУЩЕСТВО", callback_data=f"props_{player_id}")
        ],
        [
            InlineKeyboardButton(f"{EMOJI['trade']} ТОРГОВАТЬ", callback_data=f"trade_menu_{player_id}"),
            InlineKeyboardButton(f"{EMOJI['house']} СТРОИТЬ", callback_data=f"build_{player_id}")
        ],
        [InlineKeyboardButton(f"⏭️ ЗАКОНЧИТЬ ХОД", callback_data=f"end_{player_id}")]
    ])

def get_buy_keyboard(property_idx: int, price: int, player_id: int) -> InlineKeyboardMarkup:
    """Клавиатура покупки"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ КУПИТЬ (${price})", callback_data=f"buy_{property_idx}_{player_id}"),
            InlineKeyboardButton(f"{EMOJI['auction']} АУКЦИОН", callback_data=f"auction_{property_idx}_{player_id}")
        ],
        [InlineKeyboardButton("❌ ПРОПУСТИТЬ", callback_data=f"skip_{player_id}")]
    ])

def get_trade_keyboard(player_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для торговли"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💵 Предложить деньги", callback_data=f"trade_money_{player_id}")],
        [InlineKeyboardButton(f"🏠 Предложить имущество", callback_data=f"trade_props_{player_id}")],
        [InlineKeyboardButton(f"🤝 Принять предложение", callback_data=f"trade_accept_{player_id}")],
        [InlineKeyboardButton(f"❌ Отменить торговлю", callback_data=f"trade_cancel_{player_id}")]
    ])

def get_build_keyboard(property_idx: int, player_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для строительства"""
    house_price = 50
    hotel_price = 200
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🏡 Построить дом (${house_price})", callback_data=f"build_house_{property_idx}_{player_id}")],
        [InlineKeyboardButton(f"🏨 Построить отель (${hotel_price})", callback_data=f"build_hotel_{property_idx}_{player_id}")],
        [InlineKeyboardButton(f"↩️ Назад", callback_data=f"build_back_{player_id}")]
    ])

def get_auction_keyboard(property_idx: int, current_bid: int, player_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для аукциона"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"➕ ${current_bid + 10}", callback_data=f"auction_bid_{property_idx}_{current_bid + 10}_{player_id}"),
            InlineKeyboardButton(f"➕ ${current_bid + 50}", callback_data=f"auction_bid_{property_idx}_{current_bid + 50}_{player_id}")
        ],
        [
            InlineKeyboardButton(f"➕ ${current_bid + 100}", callback_data=f"auction_bid_{property_idx}_{current_bid + 100}_{player_id}"),
            InlineKeyboardButton(f"💎 Своя ставка", callback_data=f"auction_custom_{property_idx}_{player_id}")
        ],
        [InlineKeyboardButton("⏹️ Завершить", callback_data=f"auction_end_{property_idx}_{player_id}")]
    ])

# ===================== ОБРАБОТЧИКИ CALLBACK =====================

def trade_menu(update: Update, context: CallbackContext):
    """Меню торговли"""
    try:
        query = update.callback_query
        query.answer()
        
        data = query.data.split('_')
        player_id = int(data[2])
        chat_id = query.message.chat.id
        
        if chat_id not in games_storage:
            return
        
        game = games_storage[chat_id]
        
        if game['current_player'] != player_id:
            query.answer("❌ Сейчас не ваш ход!")
            return
        
        # Получаем список других игроков
        other_players = [
            p for p in game['players'].values() 
            if p['id'] != player_id and not p['is_bankrupt']
        ]
        
        if not other_players:
            query.answer("❌ Нет других игроков для торговли!")
            return
        
        # Создаем клавиатуру выбора игрока
        buttons = []
        for other_player in other_players:
            buttons.append([
                InlineKeyboardButton(
                    f"{other_player['color']} @{other_player['username']} (${other_player['balance']})",
                    callback_data=f"trade_with_{other_player['id']}_{player_id}"
                )
            ])
        
        buttons.append([InlineKeyboardButton("↩️ Назад", callback_data=f"trade_back_{player_id}")])
        
        query.edit_message_text(
            f"🤝 *ТОРГОВЛЯ*\n\nВыберите игрока для торговли:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в trade_menu: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.answer("❌ Ошибка при открытии меню торговли.")

def build_menu(update: Update, context: CallbackContext):
    """Меню строительства"""
    try:
        query = update.callback_query
        query.answer()
        
        player_id = int(query.data.split('_')[1])
        chat_id = query.message.chat.id
        
        if chat_id not in games_storage:
            return
        
        game = games_storage[chat_id]
        player = game['players'].get(player_id)
        
        if not player or game['current_player'] != player_id:
            query.answer("❌ Сейчас не ваш ход!")
            return
        
        # Получаем улицы, где можно строить
        buildable_properties = []
        for prop_idx in player['properties']:
            cell = BOARD[prop_idx]
            if cell['type'] == 'property':
                # Проверяем монополию
                color = cell['color']
                same_color_cells = [i for i, c in enumerate(BOARD) 
                                  if c.get('color') == color and c['type'] == 'property']
                
                has_monopoly = all(
                    game['board_state'][i]['owner'] == player_id 
                    for i in same_color_cells
                )
                
                if has_monopoly:
                    current_houses = game['board_state'][prop_idx]['houses']
                    if current_houses < 5:  # Максимум отель
                        buildable_properties.append((prop_idx, cell, current_houses))
        
        if not buildable_properties:
            query.answer("❌ Нет улиц для строительства!")
            return
        
        # Создаем клавиатуру
        buttons = []
        for prop_idx, cell, houses in buildable_properties:
            house_price = 50
            hotel_price = 200
            
            if houses < 4:
                button_text = f"🏠 {cell['name']} (дома: {houses}) - ${house_price}"
                callback_data = f"build_house_{prop_idx}_{player_id}"
            elif houses == 4:
                button_text = f"🏨 {cell['name']} - отель (${hotel_price})"
                callback_data = f"build_hotel_{prop_idx}_{player_id}"
            else:
                continue
                
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        buttons.append([InlineKeyboardButton("↩️ Назад", callback_data=f"build_back_{player_id}")])
        
        query.edit_message_text(
            f"🏗️ *СТРОИТЕЛЬСТВО*\n\nВыберите улицу для строительства:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в build_menu: {str(e)}"
        add_web_log(error_msg, "ERROR")

def build_house(update: Update, context: CallbackContext):
    """Строительство дома"""
    try:
        query = update.callback_query
        query.answer()
        
        data = query.data.split('_')
        property_idx = int(data[2])
        player_id = int(data[3])
        chat_id = query.message.chat.id
        
        if chat_id not in games_storage:
            return
        
        game = games_storage[chat_id]
        player = game['players'].get(player_id)
        
        if not player or game['current_player'] != player_id:
            query.answer("❌ Сейчас не ваш ход!")
            return
        
        cell = BOARD[property_idx]
        current_houses = game['board_state'][property_idx]['houses']
        house_price = 50
        
        if current_houses >= 4:
            query.answer("❌ Уже построено 4 дома!")
            return
        
        if player['balance'] < house_price:
            query.answer("❌ Недостаточно денег!")
            return
        
        # Строим дом
        player['balance'] -= house_price
        game['board_state'][property_idx]['houses'] += 1
        
        add_web_log(f"Игрок {player_id} построил дом на {cell['name']}", "INFO")
        
        query.edit_message_text(
            f"✅ *ДОМ ПОСТРОЕН!*\n\n"
            f"🏠 {cell['name']}\n"
            f"🏡 Теперь домов: {current_houses + 1}\n"
            f"💰 Потрачено: ${house_price}\n"
            f"💵 Остаток: ${player['balance']}",
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в build_house: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.answer("❌ Ошибка при строительстве дома.")

def build_hotel(update: Update, context: CallbackContext):
    """Строительство отеля"""
    try:
        query = update.callback_query
        query.answer()
        
        data = query.data.split('_')
        property_idx = int(data[2])
        player_id = int(data[3])
        chat_id = query.message.chat.id
        
        if chat_id not in games_storage:
            return
        
        game = games_storage[chat_id]
        player = game['players'].get(player_id)
        
        if not player or game['current_player'] != player_id:
            query.answer("❌ Сейчас не ваш ход!")
            return
        
        cell = BOARD[property_idx]
        current_houses = game['board_state'][property_idx]['houses']
        hotel_price = 200
        
        if current_houses != 4:
            query.answer("❌ Сначала постройте 4 дома!")
            return
        
        if player['balance'] < hotel_price:
            query.answer("❌ Недостаточно денег!")
            return
        
        # Строим отель
        player['balance'] -= hotel_price
        game['board_state'][property_idx]['houses'] = 5  # 5 = отель
        
        add_web_log(f"Игрок {player_id} построил отель на {cell['name']}", "INFO")
        
        query.edit_message_text(
            f"✅ *ОТЕЛЬ ПОСТРОЕН!*\n\n"
            f"🏨 {cell['name']}\n"
            f"💰 Потрачено: ${hotel_price}\n"
            f"💵 Остаток: ${player['balance']}\n\n"
            f"Теперь аренда максимальна!",
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в build_hotel: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.answer("❌ Ошибка при строительстве отеля.")

def auction_property(update: Update, context: CallbackContext):
    """Начало аукциона"""
    try:
        query = update.callback_query
        query.answer()
        
        data = query.data.split('_')
        property_idx = int(data[1])
        player_id = int(data[2])
        chat_id = query.message.chat.id
        
        add_web_log(f"Начало аукциона за собственность {property_idx} в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        cell = BOARD[property_idx]
        
        if game['current_player'] != player_id:
            query.answer("❌ Сейчас не ваш ход!")
            return
        
        # Создаем аукцион
        game['auctions'].append({
            'property_idx': property_idx,
            'current_bid': cell['price'] // 2,
            'current_bidder': None,
            'bidders': list(game['players'].keys()),
            'min_increment': 10
        })
        
        auction = game['auctions'][-1]
        
        query.edit_message_text(
            f"""🔨 *АУКЦИОН НАЧАТ!*

🏠 {cell['name']}
💰 Стартовая цена: ${auction['current_bid']}
👥 Участники: {len(auction['bidders'])} игроков

Правила:
• Минимальная ставка: ${auction['min_increment']}
• Ставка должна быть выше текущей
• Если никто не ставит 3 раза - аукцион завершается""",
            parse_mode='Markdown',
            reply_markup=get_auction_keyboard(property_idx, auction['current_bid'], player_id)
        )
        
        game['status'] = 'auction'
        
    except Exception as e:
        error_msg = f"Ошибка в auction_property: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.edit_message_text("❌ Ошибка при начале аукциона.")

def auction_bid(update: Update, context: CallbackContext):
    """Ставка на аукционе"""
    try:
        query = update.callback_query
        query.answer()
        
        data = query.data.split('_')
        property_idx = int(data[2])
        bid_amount = int(data[3])
        player_id = int(data[4])
        chat_id = query.message.chat.id
        
        if chat_id not in games_storage:
            return
        
        game = games_storage[chat_id]
        
        # Находим активный аукцион для этой собственности
        auction = None
        for a in game['auctions']:
            if a['property_idx'] == property_idx:
                auction = a
                break
        
        if not auction:
            query.answer("❌ Аукцион не найден!")
            return
        
        player = game['players'][player_id]
        
        # Проверяем ставку
        if bid_amount <= auction['current_bid']:
            query.answer(f"❌ Ставка должна быть выше ${auction['current_bid']}!")
            return
        
        if player['balance'] < bid_amount:
            query.answer("❌ Недостаточно денег для ставки!")
            return
        
        # Обновляем ставку
        auction['current_bid'] = bid_amount
        auction['current_bidder'] = player_id
        
        add_web_log(f"Игрок {player_id} сделал ставку ${bid_amount} на аукционе", "INFO")
        
        query.edit_message_text(
            f"""🔨 *АУКЦИОН*

🏠 {BOARD[property_idx]['name']}
💰 Текущая ставка: *${bid_amount}*
👤 Текущий лидер: {player['color']} @{player['username']}

👇 Сделайте следующую ставку:""",
            parse_mode='Markdown',
            reply_markup=get_auction_keyboard(property_idx, bid_amount, player_id)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в auction_bid: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.answer("❌ Ошибка при ставке.")

def auction_end(update: Update, context: CallbackContext):
    """Завершение аукциона"""
    try:
        query = update.callback_query
        query.answer()
        
        data = query.data.split('_')
        property_idx = int(data[2])
        player_id = int(data[3])
        chat_id = query.message.chat.id
        
        add_web_log(f"Завершение аукциона за собственность {property_idx} в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            return
        
        game = games_storage[chat_id]
        
        # Находим и завершаем аукцион
        auction_to_remove = None
        for auction in game['auctions']:
            if auction['property_idx'] == property_idx:
                auction_to_remove = auction
                break
        
        if auction_to_remove:
            game['auctions'].remove(auction_to_remove)
        
        game['status'] = 'active'
        
        if auction_to_remove and auction_to_remove['current_bidder']:
            # Продаем собственность победителю
            winner_id = auction_to_remove['current_bidder']
            winner = game['players'][winner_id]
            cell = BOARD[property_idx]
            
            winner['balance'] -= auction_to_remove['current_bid']
            winner['properties'].append(property_idx)
            game['board_state'][property_idx]['owner'] = winner_id
            
            add_web_log(f"Игрок {winner_id} выиграл аукцион за {cell['name']} за ${auction_to_remove['current_bid']}", "INFO")
            
            query.edit_message_text(
                f"""✅ *АУКЦИОН ЗАВЕРШЕН!*

🏠 {cell['name']}
💰 Продано за: ${auction_to_remove['current_bid']}
👑 Победитель: {winner['color']} @{winner['username']}

Поздравляем с покупкой!""",
                parse_mode='Markdown'
            )
        else:
            # Никто не купил
            query.edit_message_text(
                f"""⏹️ *АУКЦИОН ОТМЕНЕН*

🏠 {BOARD[property_idx]['name']}
❌ Никто не сделал ставку

Собственность остается у банка.""",
                parse_mode='Markdown'
            )
        
        import time
        time.sleep(2)
        next_turn(game, chat_id, context)
        
    except Exception as e:
        error_msg = f"Ошибка в auction_end: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.edit_message_text("❌ Ошибка при завершении аукциона.")

# ===================== ОСНОВНЫЕ ОБРАБОТЧИКИ КОМАНД =====================

def private_start(update: Update, context: CallbackContext):
    """Обработчик /start в личных сообщениях"""
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        add_web_log(f"Команда /start от пользователя @{user.username or user.first_name} (ID: {user.id})", "INFO")
        
        update.message.reply_text(
            f"""🎩 *ДОБРО ПОЖАЛОВАТЬ В МОНОПОЛИЮ!*

{EMOJI['player']} *{user.first_name}*, этот бот предназначен для игры в группах!

⚡ *Как начать:*
1. Добавьте меня в группу кнопкой ниже
2. Напишите в группе /monopoly
3. Пригласите друзей присоединиться
4. Начните игру!

🏆 *Особенности:*
• До 6 реальных игроков
• Торговля между игроками
• Аукционы
• Дома и отели
• Карточки шанса

👇 *Добавьте меня в группу:*""",
            parse_mode='Markdown',
            reply_markup=get_add_to_group_keyboard(context.bot.username)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в private_start: {str(e)}"
        add_web_log(error_msg, "ERROR")
        update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

def group_monopoly(update: Update, context: CallbackContext):
    """Команда /monopoly в группе"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        add_web_log(f"Команда /monopoly в группе {chat.id} от @{user.username or user.first_name}", "INFO")
        
        if chat.type not in ["group", "supergroup"]:
            update.message.reply_text("❌ Эта команда работает только в группах!")
            return
        
        chat_id = chat.id
        
        # Проверяем права бота
        try:
            member = chat.get_member(context.bot.id)
            if member.status != 'administrator':
                update.message.reply_text(
                    f"""⚠️ *Сначала дайте мне права администратора!*

Мне нужны права:
• 📝 Удаление сообщений
• 📌 Закрепление сообщений
• ✉️ Отправка сообщений

Без прав я не смогу нормально работать в группе!""",
                    parse_mode='Markdown'
                )
                return
        except Exception as e:
            add_web_log(f"Не удалось проверить права бота: {str(e)}", "WARNING")
        
        # Проверяем, есть ли активная игра
        if chat_id in games_storage and games_storage[chat_id].get('status') != 'finished':
            game = games_storage[chat_id]
            players_list = "\n".join(
                f"{p['color']} @{p['username']} (${p['balance']})" 
                for p in game['players'].values()
            )
            
            status_text = {
                'lobby': '🕐 ОЖИДАНИЕ ИГРОКОВ',
                'active': '🎮 ИГРА ИДЕТ',
                'trade': '🤝 ТОРГОВЛЯ',
                'auction': '🔨 АУКЦИОН'
            }.get(game.get('status', 'lobby'), '❓')
            
            update.message.reply_text(
                f"""{status_text}

🎮 *Активная игра в этой группе*

👥 *Игроки ({len(game['players'])}/6):*
{players_list}

👇 Присоединяйтесь или дождитесь окончания!""",
                parse_mode='Markdown',
                reply_markup=get_lobby_keyboard(chat_id)
            )
            return
        
        # Создаем новую игру
        colors = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠']
        games_storage[chat_id] = {
            'id': f"game_{chat_id}_{datetime.now().strftime('%H%M%S')}",
            'chat_id': chat_id,
            'creator': user.id,
            'players': {},
            'status': 'lobby',
            'board_state': {i: {'owner': None, 'houses': 0} for i in range(len(BOARD))},
            'current_player': None,
            'turn_order': [],
            'created_at': datetime.now().isoformat(),
            'properties': {},
            'auctions': [],
            'trades': [],
            'messages_to_delete': []
        }
        
        # Добавляем создателя
        games_storage[chat_id]['players'][user.id] = {
            'id': user.id,
            'username': user.username or user.first_name,
            'balance': START_MONEY,
            'position': 0,
            'color': colors[0],
            'properties': [],
            'in_jail': False,
            'jail_turns': 0,
            'get_out_of_jail': 0,
            'is_bankrupt': False,
            'dice_doubles': 0
        }
        
        add_web_log(f"Создана новая игра в чате {chat_id}. Создатель: @{user.username or user.first_name}", "INFO")
        
        update.message.reply_text(
            f"""🎮 *НОВАЯ ИГРА СОЗДАНА!*

🏁 *Создатель:* {colors[0]} @{user.username or user.first_name}
👥 *Игроки:* 1/6
💰 *Стартовый капитал:* ${START_MONEY}

👇 *Присоединяйтесь к игре!*
Минимум 2 игрока для начала.""",
            parse_mode='Markdown',
            reply_markup=get_lobby_keyboard(chat_id)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в group_monopoly: {str(e)}"
        add_web_log(error_msg, "ERROR")
        update.message.reply_text("❌ Произошла ошибка при создании игры. Попробуйте еще раз.")

def help_command(update: Update, context: CallbackContext):
    """Команда помощи"""
    try:
        add_web_log("Команда /help выполнена", "INFO")
        
        update.message.reply_text(
            f"""🆘 *ПОМОЩЬ ПО КОМАНДАМ*

🎮 *Основные команды:*
/start - информация о боте
/monopoly - начать новую игру (только в группах)
/help - эта справка

🎲 *Игровые команды:*
Все действия в игре выполняются через кнопки под сообщениями.

💰 *Экономика игры:*
• Стартовый капитал: ${START_MONEY}
• Проход старта: $200
• Тюремный штраф: $50 

🏠 *Стоимость строительства:*
• Дом: $50
• Отель: $200

*Для начала игры добавьте бота в группу и напишите /monopoly*""",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = f"Ошибка в help_command: {str(e)}"
        add_web_log(error_msg, "ERROR")

def join_game(update: Update, context: CallbackContext):
    """Присоединение к игре"""
    try:
        query = update.callback_query
        query.answer()
        
        chat_id = query.message.chat.id
        user = query.from_user
        
        add_web_log(f"Попытка присоединения @{user.username or user.first_name} к игре в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        
        if game['status'] != 'lobby':
            query.answer("❌ Игра уже началась!")
            return
        
        if user.id in game['players']:
            query.answer("✅ Вы уже в игре!")
            return
        
        if len(game['players']) >= MAX_PLAYERS:
            query.answer("🚫 Максимум 6 игроков!")
            return
        
        # Выбираем цвет
        colors = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠']
        used_colors = [p['color'] for p in game['players'].values()]
        available_colors = [c for c in colors if c not in used_colors]
        
        if not available_colors:
            query.answer("❌ Нет свободных цветов!")
            return
        
        color = available_colors[0]
        
        # Добавляем игрока
        game['players'][user.id] = {
            'id': user.id,
            'username': user.username or user.first_name,
            'balance': START_MONEY,
            'position': 0,
            'color': color,
            'properties': [],
            'in_jail': False,
            'jail_turns': 0,
            'get_out_of_jail': 0,
            'is_bankrupt': False,
            'dice_doubles': 0
        }
        
        add_web_log(f"Игрок @{user.username or user.first_name} присоединился к игре в чате {chat_id}", "INFO")
        
        # Формируем список игроков
        players_list = "\n".join(
            f"{p['color']} @{p['username']}" 
            for p in game['players'].values()
        )
        
        query.edit_message_text(
            f"""🎮 *ЛОББИ ИГРЫ*

👥 *Игроки ({len(game['players'])}/6):*
{players_list}

💰 *Стартовый капитал:* ${START_MONEY}

👇 Присоединяйтесь или начинайте игру!""",
            parse_mode='Markdown',
            reply_markup=get_lobby_keyboard(chat_id)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в join_game: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.edit_message_text("❌ Произошла ошибка. Попробуйте еще раз.")

def start_game(update: Update, context: CallbackContext):
    """Начало игры"""
    try:
        query = update.callback_query
        query.answer()
        
        chat_id = query.message.chat.id
        
        add_web_log(f"Попытка начала игры в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        
        if len(game['players']) < 2:
            query.answer("❌ Нужно минимум 2 игрока!")
            return
        
        if game['status'] != 'lobby':
            query.answer("❌ Игра уже началась!")
            return
        
        # Начинаем игру
        game['status'] = 'active'
        game['turn_order'] = list(game['players'].keys())
        random.shuffle(game['turn_order'])  # Случайный порядок
        game['current_player'] = game['turn_order'][0]
        current_player = game['players'][game['current_player']]
        
        # Создаем красивое поле
        board_visual = create_board_visual(game)
        
        add_web_log(f"Игра начата в чате {chat_id}. Игроков: {len(game['players'])}", "INFO")
        
        query.edit_message_text(
            f"""🎉 *ИГРА НАЧАЛАСЬ!*

{board_visual}

🎲 *ПЕРВЫЙ ХОД:*
{current_player['color']} @{current_player['username']}

💰 *Баланс:* ${current_player['balance']}
📍 *Позиция:* {BOARD[current_player['position']]['name']}

👇 Бросайте кубики!""",
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(game['current_player'])
        )
        
    except Exception as e:
        error_msg = f"Ошибка в start_game: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.edit_message_text("❌ Произошла ошибка при начале игры.")

# ===================== ОБРАБОТЧИКИ ИГРОВЫХ ДЕЙСТВИЙ =====================

def roll_dice(update: Update, context: CallbackContext):
    """Бросок кубиков"""
    try:
        query = update.callback_query
        query.answer()
        
        data = query.data
        player_id = int(data.split('_')[1])
        chat_id = query.message.chat.id
        
        add_web_log(f"Игрок {player_id} бросает кубики в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        
        if game['current_player'] != player_id:
            query.answer("❌ Сейчас не ваш ход!")
            return
        
        player = game['players'][player_id]
        
        # Бросаем кубики
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        is_double = dice1 == dice2
        
        # Если в тюрьме
        if player['in_jail']:
            if is_double:
                player['in_jail'] = False
                player['jail_turns'] = 0
                jail_msg = "🎉 Вы выбросили дубль и вышли из тюрьмы!"
                context.bot.send_message(chat_id, jail_msg)
                add_web_log(f"Игрок {player_id} вышел из тюрьмы (дубль)", "INFO")
            else:
                player['jail_turns'] += 1
                if player['jail_turns'] >= 3:
                    # Платим штраф
                    player['balance'] -= 50
                    player['in_jail'] = False
                    jail_msg = f"💸 Выплатили штраф $50 и вышли из тюрьмы"
                    context.bot.send_message(chat_id, jail_msg)
                    add_web_log(f"Игрок {player_id} выплатил штраф и вышел из тюрьмы", "INFO")
                else:
                    query.answer(f"❌ Осталось в тюрьме (ход {player['jail_turns']}/3)")
                    add_web_log(f"Игрок {player_id} остался в тюрьме (ход {player['jail_turns']}/3)", "INFO")
                    # Переход хода
                    import time
                    time.sleep(1)
                    next_turn(game, chat_id, context)
                    return
        
        # Учитываем дубли
        if is_double:
            player['dice_doubles'] += 1
            if player['dice_doubles'] >= 3:
                # Три дубля подряд - в тюрьму
                player['in_jail'] = True
                player['position'] = 10  # Тюрьма
                player['dice_doubles'] = 0
                context.bot.send_message(chat_id, "🚓 Три дубля подряд! Вы отправляетесь в тюрьму!")
                add_web_log(f"Игрок {player_id} попал в тюрьму (3 дубля подряд)", "INFO")
                time.sleep(2)
                next_turn(game, chat_id, context)
                return
        
        # Двигаем игрока
        new_position = (player['position'] + total) % len(BOARD)
        player['position'] = new_position
        
        cell = BOARD[new_position]
        
        # Формируем сообщение
        dice_visual = f"{EMOJI['dice']}{dice1} + {EMOJI['dice']}{dice2} = {total}"
        
        message = f"""🎲 *ХОД ИГРОКА*

{player['color']} @{player['username']}
{dice_visual}
📍 Перешел на: *{cell['name']}*

"""
        
        add_web_log(f"Игрок {player_id} переместился на позицию {new_position} ({cell['name']})", "INFO")
        
        # Обработка клетки
        if cell['type'] == 'property' or cell['type'] == 'railroad' or cell['type'] == 'utility':
            owner = game['board_state'][new_position]['owner']
            if owner is None:
                # Свободная собственность
                message += f"""💰 *СОБСТВЕННОСТЬ СВОБОДНА*

Цена: ${cell['price']}
Ваш баланс: ${player['balance']}

👇 Купите или начните аукцион!"""
                
                query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=get_buy_keyboard(new_position, cell['price'], player_id)
                )
                return
            elif owner == player_id:
                # Своя собственность
                message += "✅ Это ваша собственность!"
                query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=get_game_keyboard(player_id)
                )
            else:
                # Чужая собственность - платим аренду
                rent = calculate_rent(game, new_position, owner)
                player['balance'] -= rent
                game['players'][owner]['balance'] += rent
                
                message += f"""💸 *АРЕНДНАЯ ПЛАТА*

Платите ${rent} игроку:
{game['players'][owner]['color']} @{game['players'][owner]['username']}

Ваш баланс: ${player['balance']}"""
                
                add_web_log(f"Игрок {player_id} заплатил ${rent} аренды игроку {owner}", "INFO")
                
                query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=get_game_keyboard(player_id)
                )
        
        elif cell['type'] == 'tax':
            player['balance'] -= cell['price']
            message += f"""💸 *НАЛОГ*

Уплачено: ${cell['price']}
Баланс: ${player['balance']}"""
            
            add_web_log(f"Игрок {player_id} уплатил налог ${cell['price']}", "INFO")
            
            query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_game_keyboard(player_id)
            )
        
        elif cell['type'] == 'chance':
            # Карточка шанса
            chance_result = get_chance_card(player, game)
            message += f"""🎭 *КАРТОЧКА ШАНСА*

{chance_result['text']}"""
            
            if chance_result['money'] != 0:
                player['balance'] += chance_result['money']
                message += f"\n💰 Изменение баланса: ${chance_result['money']}"
                add_web_log(f"Игрок {player_id} получил карточку шанса: {chance_result['text']}", "INFO")
            
            if chance_result['move'] != 0:
                new_pos = (player['position'] + chance_result['move']) % len(BOARD)
                player['position'] = new_pos
                message += f"\n📍 Новая позиция: {BOARD[new_pos]['name']}"
            
            query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_game_keyboard(player_id)
            )
        
        elif cell['type'] == 'jail' or cell['type'] == 'go_to_jail':
            message += "🚓 *ТЮРЬМА*\nПроезжаете мимо."
            
            query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_game_keyboard(player_id)
            )
        
        elif cell['type'] == 'start':
            # Проходим старт - получаем деньги
            player['balance'] += 200
            message += f"""🚀 *СТАРТ*

Получаете $200 за проход старта!
💰 Баланс: ${player['balance']}"""
            
            add_web_log(f"Игрок {player_id} прошел старт и получил $200", "INFO")
            
            query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_game_keyboard(player_id)
            )
        
        else:
            message += f"📌 *{cell['type'].upper()}* клетка"
            query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_game_keyboard(player_id)
            )
        
        # Если выпал дубль - можно еще раз
        if is_double and not player['in_jail']:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"🎯 {player['color']} @{player['username']} выбросил дубль!\nБросайте еще раз!",
                reply_markup=get_game_keyboard(player_id)
            )
            return
        
        # Сбрасываем счетчик дублей если не выпал дубль
        if not is_double:
            player['dice_doubles'] = 0
        
        # Ждем 2 секунды и переходим к следующему ходу
        import time
        time.sleep(2)
        next_turn(game, chat_id, context)
        
    except Exception as e:
        error_msg = f"Ошибка в roll_dice: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.edit_message_text("❌ Произошла ошибка при броске кубиков.")

def buy_property(update: Update, context: CallbackContext):
    """Покупка собственности"""
    try:
        query = update.callback_query
        query.answer()
        
        data = query.data.split('_')
        property_idx = int(data[1])
        player_id = int(data[2])
        chat_id = query.message.chat.id
        
        add_web_log(f"Игрок {player_id} покупает собственность {property_idx} в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        player = game['players'][player_id]
        cell = BOARD[property_idx]
        
        if player['balance'] < cell['price']:
            query.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем
        player['balance'] -= cell['price']
        player['properties'].append(property_idx)
        game['board_state'][property_idx]['owner'] = player_id
        
        # Проверяем монополию
        check_monopoly(game, player_id, cell['color'])
        
        add_web_log(f"Игрок {player_id} купил {cell['name']} за ${cell['price']}", "INFO")
        
        query.edit_message_text(
            f"""✅ *ПОКУПКА УСПЕШНА!*

{player['color']} @{player['username']}
🏠 Купил: *{cell['name']}*
💰 Потрачено: ${cell['price']}
💵 Остаток: ${player['balance']}

Отличная покупка!""",
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )
        
        import time
        time.sleep(2)
        next_turn(game, chat_id, context)
        
    except Exception as e:
        error_msg = f"Ошибка в buy_property: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.edit_message_text("❌ Произошла ошибка при покупке.")

def skip_turn(update: Update, context: CallbackContext):
    """Пропуск хода/отказ от покупки"""
    try:
        query = update.callback_query
        query.answer()
        
        player_id = int(query.data.split('_')[1])
        chat_id = query.message.chat.id
        
        add_web_log(f"Игрок {player_id} пропускает ход в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        
        if game['current_player'] != player_id:
            query.answer("❌ Сейчас не ваш ход!")
            return
        
        query.edit_message_text("⏭️ Ход пропущен")
        next_turn(game, chat_id, context)
        
    except Exception as e:
        error_msg = f"Ошибка в skip_turn: {str(e)}"
        add_web_log(error_msg, "ERROR")
        query.edit_message_text("❌ Произошла ошибка.")

# ===================== ДОПОЛНИТЕЛЬНЫЕ ОБРАБОТЧИКИ =====================

def end_turn(update: Update, context: CallbackContext):
    """Завершение хода"""
    try:
        query = update.callback_query
        query.answer()
        
        player_id = int(query.data.split('_')[1])
        chat_id = query.message.chat.id
        
        add_web_log(f"Игрок {player_id} завершает ход в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        if game['current_player'] == player_id:
            next_turn(game, chat_id, context)
            
    except Exception as e:
        error_msg = f"Ошибка в end_turn: {str(e)}"
        add_web_log(error_msg, "ERROR")

def check_balance(update: Update, context: CallbackContext):
    """Проверка баланса"""
    try:
        query = update.callback_query
        query.answer()
        
        player_id = int(query.data.split('_')[1])
        chat_id = query.message.chat.id
        
        if chat_id not in games_storage:
            return
        
        game = games_storage[chat_id]
        player = game['players'].get(player_id)
        
        if player:
            query.answer(f"💰 Баланс: ${player['balance']}", show_alert=True)
            
    except Exception as e:
        add_web_log(f"Ошибка в check_balance: {str(e)}", "ERROR")

def check_properties(update: Update, context: CallbackContext):
    """Проверка имущества"""
    try:
        query = update.callback_query
        query.answer()
        
        player_id = int(query.data.split('_')[1])
        chat_id = query.message.chat.id
        
        if chat_id not in games_storage:
            return
        
        game = games_storage[chat_id]
        player = game['players'].get(player_id)
        
        if player:
            if not player['properties']:
                query.answer("У вас нет собственности", show_alert=True)
                return
            
            properties_list = "\n".join(
                f"• {BOARD[idx]['name']} (${BOARD[idx]['price']})" 
                for idx in player['properties']
            )
            
            query.answer(
                f"🏠 Ваша собственность:\n{properties_list}",
                show_alert=True
            )
            
    except Exception as e:
        add_web_log(f"Ошибка в check_properties: {str(e)}", "ERROR")

def cancel_game(update: Update, context: CallbackContext):
    """Отмена игры"""
    try:
        query = update.callback_query
        query.answer()
        
        chat_id = query.message.chat.id
        
        add_web_log(f"Игра отменена в чате {chat_id}", "INFO")
        
        if chat_id in games_storage:
            del games_storage[chat_id]
        
        query.edit_message_text("❌ Игра отменена")
        
    except Exception as e:
        error_msg = f"Ошибка в cancel_game: {str(e)}"
        add_web_log(error_msg, "ERROR")

def how_to_play(update: Update, context: CallbackContext):
    """Инструкция по игре"""
    try:
        query = update.callback_query
        query.answer()
        
        add_web_log("Показана инструкция по игре", "INFO")
        
        query.edit_message_text(
            f"""📚 *ИНСТРУКЦИЯ ПО ИГРЕ*

🎲 *Основные правила:*
1. Каждый игрок начинает с ${START_MONEY}
2. По очереди бросайте кубики
3. Покупайте свободные улицы
4. Собирайте монополии (все улицы одного цвета)
5. Стройте дома и отели
6. Получайте аренду с других игроков

💰 *Деньги получаются за:*
• Проход старта: $200
• Аренда с других игроков
• Продажа собственности

🚓 *Тюрьма:*
• Попадаете на клетку "ТЮРЬМА"
• Или 3 дубля подряд
• Чтобы выйти: дубль или $50 через 3 хода

🏠 *Строительство:*
• Только при монополии
• Дом: $50
• Отель: $200 (после 4 домов)

🤝 *Торговля:*
• Обменивайтесь улицами и деньгами
• Только в свой ход

🔨 *Аукцион:*
• Если игрок не покупает улицу
• Все могут предложить цену

🎭 *Шанс:*
• Случайные события
• Может дать или забрать деньги
• Может переместить на другую клетку

*Удачи в игре!* 🎩""",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = f"Ошибка в how_to_play: {str(e)}"
        add_web_log(error_msg, "ERROR")

def error_handler(update: Update, context: CallbackContext):
    """Обработчик ошибок"""
    try:
        error = context.error
        
        if isinstance(error, TelegramError):
            error_msg = f"Telegram ошибка: {error}"
        else:
            error_msg = f"Необработанное исключение: {error}"
        
        add_web_log(error_msg, "ERROR")
        logger.error(f"Ошибка: {error}", exc_info=error)
        
        # Пытаемся уведомить пользователя об ошибке
        if update and update.effective_chat:
            try:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Произошла ошибка. Попробуйте еще раз или перезапустите игру командой /monopoly"
                )
            except:
                pass
                
    except Exception as e:
        add_web_log(f"Ошибка в обработчике ошибок: {str(e)}", "ERROR")

# ===================== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ =====================

def register_handlers():
    """Регистрация всех обработчиков для PTB v20.7"""
    if dispatcher is None:
        print("❌ Dispatcher не создан, не могу зарегистрировать обработчики")
        return False
    
    try:
        print("🔧 Регистрирую обработчики команд...")
        
        # Команды
        dispatcher.add_handler(CommandHandler("start", private_start))
        dispatcher.add_handler(CommandHandler("monopoly", group_monopoly))
        dispatcher.add_handler(CommandHandler("help", help_command))
        
        # Callback queries (кнопки)
        dispatcher.add_handler(CallbackQueryHandler(join_game, pattern="^join_"))
        dispatcher.add_handler(CallbackQueryHandler(start_game, pattern="^start_"))
        dispatcher.add_handler(CallbackQueryHandler(roll_dice, pattern="^roll_"))
        dispatcher.add_handler(CallbackQueryHandler(buy_property, pattern="^buy_"))
        dispatcher.add_handler(CallbackQueryHandler(skip_turn, pattern="^skip_"))
        dispatcher.add_handler(CallbackQueryHandler(end_turn, pattern="^end_"))
        dispatcher.add_handler(CallbackQueryHandler(check_balance, pattern="^balance_"))
        dispatcher.add_handler(CallbackQueryHandler(check_properties, pattern="^props_"))
        dispatcher.add_handler(CallbackQueryHandler(build_menu, pattern="^build_"))
        dispatcher.add_handler(CallbackQueryHandler(build_house, pattern="^build_house_"))
        dispatcher.add_handler(CallbackQueryHandler(build_hotel, pattern="^build_hotel_"))
        dispatcher.add_handler(CallbackQueryHandler(how_to_play, pattern="how_to_play"))
        dispatcher.add_handler(CallbackQueryHandler(cancel_game, pattern="^cancel_"))
        dispatcher.add_handler(CallbackQueryHandler(trade_menu, pattern="^trade_menu_"))
        dispatcher.add_handler(CallbackQueryHandler(auction_property, pattern="^auction_"))
        dispatcher.add_handler(CallbackQueryHandler(auction_bid, pattern="^auction_bid_"))
        dispatcher.add_handler(CallbackQueryHandler(auction_end, pattern="^auction_end_"))
        
        # Обработчик ошибок
        dispatcher.add_error_handler(error_handler)
        
        print(f"✅ Зарегистрировано обработчиков: {len(dispatcher.handlers[0])}")
        add_web_log(f"🔧 Зарегистрировано {len(dispatcher.handlers[0])} обработчиков", "INFO")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка регистрации обработчиков: {e}")
        add_web_log(f"❌ Ошибка регистрации обработчиков: {e}", "ERROR")
        return False

@flask_app.route('/')
def index():
    """Красивая главная страница с полной информацией о боте"""
    bot_status = "✅ Активен" if application and bot else "❌ Неактивен"
    webhook_status = "✅ Установлен" if check_webhook_status() else "❌ Не установлен"
    
    # Статистика
    active_games = len([g for g in games_storage.values() if g.get('status') != 'finished'])
    total_players = sum(len(g.get('players', {})) for g in games_storage.values())
    total_properties = sum(len(g.get('players', {})) * 2 for g in games_storage.values())
    
    # Получаем информацию о боте
    bot_info = {}
    if bot:
        try:
            bot_info = bot.get_me()
        except:
            bot_info = {'username': 'Недоступен'}
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎮 МОНОПОЛИЯ ПРЕМИУМ | Telegram Бот для игры</title>
    <meta name="description" content="Лучший бот для игры в Монополию в Telegram группах. Реалистичная экономика, торговля, аукционы и многое другое!">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary: #6c5ce7;
            --secondary: #a29bfe;
            --accent: #00cec9;
            --success: #00b894;
            --warning: #fdcb6e;
            --danger: #d63031;
            --dark: #2d3436;
            --light: #f5f6fa;
            --glass: rgba(255, 255, 255, 0.1);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: var(--light);
            min-height: 100vh;
            line-height: 1.6;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        .hero {
            text-align: center;
            padding: 60px 20px;
            background: var(--glass);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            margin-bottom: 40px;
            box-shadow: var(--shadow);
            border: 1px solid rgba(255, 255, 255, 0.2);
            animation: fadeIn 1s ease;
        }
        
        .hero-emoji {
            font-size: 80px;
            margin-bottom: 20px;
            animation: float 6s ease-in-out infinite;
        }
        
        .hero h1 {
            font-size: 3.5em;
            background: linear-gradient(45deg, #ffcc00, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 15px;
            font-weight: 800;
        }
        
        .hero-subtitle {
            font-size: 1.4em;
            color: var(--secondary);
            margin-bottom: 30px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 50px;
        }
        
        .stat-card {
            background: var(--glass);
            backdrop-filter: blur(15px);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            transition: var(--transition);
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }
        
        .stat-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
            border-color: rgba(255, 255, 255, 0.3);
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: linear-gradient(90deg, var(--accent), var(--primary));
        }
        
        .stat-icon {
            font-size: 40px;
            margin-bottom: 20px;
            color: var(--accent);
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: 800;
            margin: 10px 0;
            color: #fff;
        }
        
        .stat-label {
            color: var(--secondary);
            font-size: 1.1em;
        }
        
        /* Features */
        .features-section {
            margin: 60px 0;
        }
        
        .section-title {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 50px;
            color: #fff;
            position: relative;
        }
        
        .section-title::after {
            content: '';
            display: block;
            width: 100px;
            height: 4px;
            background: linear-gradient(90deg, var(--accent), var(--primary));
            margin: 15px auto;
            border-radius: 2px;
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
        }
        
        .feature-card {
            background: var(--glass);
            backdrop-filter: blur(15px);
            border-radius: 20px;
            padding: 35px;
            transition: var(--transition);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.15);
        }
        
        .feature-icon {
            font-size: 45px;
            margin-bottom: 20px;
            color: var(--warning);
        }
        
        .feature-title {
            font-size: 1.5em;
            margin-bottom: 15px;
            color: #fff;
        }
        
        .feature-desc {
            color: var(--secondary);
            line-height: 1.7;
        }
        
        /* Game Info */
        .game-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
            margin: 60px 0;
        }
        
        .info-card {
            background: var(--glass);
            backdrop-filter: blur(15px);
            border-radius: 20px;
            padding: 35px;
        }
        
        .info-title {
            font-size: 1.8em;
            margin-bottom: 25px;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .info-title i {
            color: var(--accent);
        }
        
        .info-list {
            list-style: none;
        }
        
        .info-list li {
            margin-bottom: 15px;
            padding-left: 25px;
            position: relative;
            color: var(--secondary);
        }
        
        .info-list li::before {
            content: '✓';
            position: absolute;
            left: 0;
            color: var(--success);
            font-weight: bold;
        }
        
        /* Controls */
        .controls {
            text-align: center;
            margin: 60px 0;
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 18px 35px;
            margin: 15px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.1em;
            transition: var(--transition);
            border: none;
            cursor: pointer;
            min-width: 200px;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, var(--primary), var(--accent));
            color: white;
            box-shadow: 0 5px 20px rgba(108, 92, 231, 0.4);
        }
        
        .btn-primary:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 25px rgba(108, 92, 231, 0.6);
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.15);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.25);
            transform: scale(1.05);
        }
        
        .btn-success {
            background: linear-gradient(45deg, var(--success), #00d2d3);
            color: white;
        }
        
        .btn-danger {
            background: linear-gradient(45deg, var(--danger), #ff7675);
            color: white;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 40px 20px;
            margin-top: 60px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        
        .footer-links {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 30px 0;
            flex-wrap: wrap;
        }
        
        .footer-link {
            color: var(--secondary);
            text-decoration: none;
            transition: var(--transition);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .footer-link:hover {
            color: white;
            transform: translateY(-2px);
        }
        
        .copyright {
            color: var(--secondary);
            font-size: 0.9em;
            margin-top: 20px;
        }
        
        /* Status Badges */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 20px;
            border-radius: 50px;
            font-weight: 600;
            font-size: 0.9em;
            margin: 5px;
        }
        
        .status-success {
            background: rgba(0, 184, 148, 0.2);
            color: var(--success);
            border: 1px solid rgba(0, 184, 148, 0.3);
        }
        
        .status-error {
            background: rgba(214, 48, 49, 0.2);
            color: var(--danger);
            border: 1px solid rgba(214, 48, 49, 0.3);
        }
        
        .status-warning {
            background: rgba(253, 203, 110, 0.2);
            color: var(--warning);
            border: 1px solid rgba(253, 203, 110, 0.3);
        }
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-20px); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .hero h1 { font-size: 2.5em; }
            .hero-subtitle { font-size: 1.2em; }
            .section-title { font-size: 2em; }
            .btn { width: 100%; margin: 10px 0; }
            .stats-grid { grid-template-columns: 1fr; }
            .features-grid { grid-template-columns: 1fr; }
            .game-info { grid-template-columns: 1fr; }
        }
        
        /* Live Stats */
        .live-stats {
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin: 30px 0;
        }
        
        .live-stat {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px 25px;
            border-radius: 15px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 150px;
        }
        
        .live-stat-value {
            font-size: 2em;
            font-weight: bold;
            color: var(--accent);
            animation: pulse 2s infinite;
        }
        
        /* Progress Bars */
        .progress-container {
            margin: 20px 0;
        }
        
        .progress-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            color: var(--secondary);
        }
        
        .progress-bar {
            height: 10px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--primary));
            border-radius: 5px;
            transition: width 1s ease;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Hero Section -->
        <section class="hero">
            <div class="hero-emoji">🎮</div>
            <h1>МОНОПОЛИЯ ПРЕМИУМ</h1>
            <p class="hero-subtitle">
                Самый продвинутый Telegram бот для классической игры в Монополию. 
                Реалистичная экономика, живая торговля и увлекательные аукционы прямо в вашем чате!
            </p>
            
            <div class="live-stats">
                <div class="live-stat">
                    <div class="live-stat-value" id="activeGames">{{ active_games }}</div>
                    <div>Активных игр</div>
                </div>
                <div class="live-stat">
                    <div class="live-stat-value" id="totalPlayers">{{ total_players }}</div>
                    <div>Всего игроков</div>
                </div>
                <div class="live-stat">
                    <div class="live-stat-value" id="botStatus">{{ '🟢' if application else '🔴' }}</div>
                    <div>Статус бота</div>
                </div>
            </div>
        </section>
        
        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">👥</div>
                <div class="stat-value">{{ MAX_PLAYERS }}</div>
                <div class="stat-label">Максимум игроков</div>
                <p class="feature-desc">До 6 реальных игроков в одной игре</p>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">💰</div>
                <div class="stat-value">${{ START_MONEY }}</div>
                <div class="stat-label">Стартовый капитал</div>
                <p class="feature-desc">Начальная сумма каждого игрока</p>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">🏠</div>
                <div class="stat-value">{{ len(BOARD) }}</div>
                <div class="stat-label">Клеток на поле</div>
                <p class="feature-desc">Полноценное игровое поле</p>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">⚡</div>
                <div class="stat-value">24/7</div>
                <div class="stat-label">Доступность</div>
                <p class="feature-desc">Работает на облачном сервере</p>
            </div>
        </div>
        
        <!-- Status Section -->
        <div class="info-card">
            <h2 class="info-title"><i class="fas fa-server"></i> Статус системы</h2>
            <div class="progress-container">
                <div class="progress-label">
                    <span>Бот:</span>
                    <span class="status-badge {{ 'status-success' if application else 'status-error' }}">
                        {{ bot_status }}
                    </span>
                </div>
            </div>
            
            <div class="progress-container">
                <div class="progress-label">
                    <span>Вебхук:</span>
                    <span class="status-badge {{ 'status-success' if check_webhook_status() else 'status-error' }}">
                        {{ webhook_status }}
                    </span>
                </div>
            </div>
            
            <div class="progress-container">
                <div class="progress-label">
                    <span>Telegram API:</span>
                    <span class="status-badge status-success">✅ Доступен</span>
                </div>
            </div>
            
            <div class="progress-container">
                <div class="progress-label">
                    <span>База данных игр:</span>
                    <span class="status-badge status-success">✅ Активна</span>
                </div>
            </div>
        </div>
        
        <!-- Features Section -->
        <section class="features-section">
            <h2 class="section-title">🎯 Ключевые особенности</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">🤝</div>
                    <h3 class="feature-title">Живая торговля</h3>
                    <p class="feature-desc">Обменивайтесь улицами и деньгами с другими игроками в реальном времени.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🔨</div>
                    <h3 class="feature-title">Аукционы</h3>
                    <p class="feature-desc">Соревнуйтесь за лучшие улицы на динамичных аукционах.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🏗️</div>
                    <h3 class="feature-title">Строительство</h3>
                    <p class="feature-desc">Стройте дома и отели для увеличения арендной платы.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🎭</div>
                    <h3 class="feature-title">Карточки шанса</h3>
                    <p class="feature-desc">Случайные события делают каждую игру уникальной.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🚓</div>
                    <h3 class="feature-title">Тюремная система</h3>
                    <p class="feature-desc">Реалистичная механика тюрьмы с возможностью выкупа.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <h3 class="feature-title">Детальная статистика</h3>
                    <p class="feature-desc">Отслеживайте баланс, имущество и историю сделок.</p>
                </div>
            </div>
        </section>
        
        <!-- Game Info -->
        <div class="game-info">
            <div class="info-card">
                <h2 class="info-title"><i class="fas fa-gamepad"></i> Как начать игру</h2>
                <ol class="info-list">
                    <li>Добавьте бота @{{ bot_info.username if bot_info else 'monopoly_bot' }} в Telegram группу</li>
                    <li>Назначьте бота администратором (нужны права на отправку сообщений)</li>
                    <li>Напишите в группе команду <code>/monopoly</code></li>
                    <li>Пригласите друзей присоединиться через кнопку "ПРИСОЕДИНИТЬСЯ"</li>
                    <li>Нажмите "НАЧАТЬ" когда наберется минимум 2 игрока</li>
                    <li>Используйте кнопки под сообщениями для игровых действий</li>
                </ol>
            </div>
            
            <div class="info-card">
                <h2 class="info-title"><i class="fas fa-coins"></i> Экономика игры</h2>
                <ul class="info-list">
                    <li>Стартовый капитал: <strong>${{ START_MONEY }}</strong></li>
                    <li>Проход старта: <strong>$200</strong></li>
                    <li>Тюремный штраф: <strong>$50</strong></li>
                    <li>Стоимость дома: <strong>$50</strong></li>
                    <li>Стоимость отеля: <strong>$200</strong></li>
                    <li>Налог на доход: <strong>$200</strong></li>
                    <li>Суперналог: <strong>$100</strong></li>
                </ul>
            </div>
        </div>
        
        <!-- Controls -->
        <section class="controls">
            <h2 class="section-title">⚙️ Управление</h2>
            
            <div>
                <a href="/ping" class="btn btn-primary">
                    <i class="fas fa-heartbeat"></i> Проверить API
                </a>
                
                <a href="/webhook_info" class="btn btn-secondary">
                    <i class="fas fa-satellite-dish"></i> Статус вебхука
                </a>
                
                <a href="/logs" class="btn btn-secondary">
                    <i class="fas fa-scroll"></i> Просмотр логов
                </a>
                
                {% if not check_webhook_status() %}
                <a href="/set_webhook_manual" class="btn btn-success">
                    <i class="fas fa-plug"></i> Установить вебхук
                </a>
                {% endif %}
                
                <a href="/delete_webhook" class="btn btn-danger">
                    <i class="fas fa-unlink"></i> Удалить вебхук
                </a>
            </div>
        </section>
        
        <!-- Bot Commands -->
        <div class="info-card">
            <h2 class="info-title"><i class="fas fa-terminal"></i> Команды бота</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px;">
                <div>
                    <h3 style="color: var(--accent); margin-bottom: 10px;">Основные команды</h3>
                    <p><code>/start</code> - Информация о боте</p>
                    <p><code>/help</code> - Помощь по командам</p>
                    <p><code>/monopoly</code> - Начать игру в группе</p>
                </div>
                <div>
                    <h3 style="color: var(--accent); margin-bottom: 10px;">Игровые действия</h3>
                    <p>🎲 Бросок кубиков</p>
                    <p>💰 Проверка баланса</p>
                    <p>🏠 Покупка имущества</p>
                    <p>🤝 Торговля с игроками</p>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <footer class="footer">
            <h2 style="margin-bottom: 20px; color: #fff;">🎩 МОНОПОЛИЯ ПРЕМИУМ</h2>
            <p style="color: var(--secondary); max-width: 600px; margin: 0 auto 30px;">
                Лучший способ играть в классическую Монополию с друзьями в Telegram. 
                Полностью бесплатно, без рекламы и с открытым исходным кодом.
            </p>
            
            <div class="footer-links">
                <a href="/" class="footer-link">
                    <i class="fas fa-home"></i> Главная
                </a>
                <a href="/docs" class="footer-link">
                    <i class="fas fa-book"></i> Документация
                </a>
                <a href="https://t.me/{{ bot_info.username if bot_info else 'monopoly_bot' }}" class="footer-link" target="_blank">
                    <i class="fab fa-telegram"></i> Telegram бот
                </a>
                <a href="/status" class="footer-link">
                    <i class="fas fa-chart-line"></i> Статус
                </a>
                <a href="https://github.com" class="footer-link" target="_blank">
                    <i class="fab fa-github"></i> GitHub
                </a>
            </div>
            
            <div class="live-stats" style="margin: 30px auto; max-width: 500px;">
                <div class="live-stat" style="background: rgba(255,255,255,0.05);">
                    <div>Серверное время</div>
                    <div class="live-stat-value" id="serverTime">{{ datetime.now().strftime("%H:%M") }}</div>
                </div>
                <div class="live-stat" style="background: rgba(255,255,255,0.05);">
                    <div>Аптайм</div>
                    <div class="live-stat-value" id="uptime">99.9%</div>
                </div>
            </div>
            
            <div class="copyright">
                © 2024 Монополия Премиум. Все права защищены. 
                <br>Версия: Render Webhook | Python {{ python_version }}
            </div>
        </footer>
    </div>
    
    <script>
        // Обновление времени
        function updateServerTime() {
            const now = new Date();
            const timeString = now.toLocaleTimeString('ru-RU', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
            document.getElementById('serverTime').textContent = timeString;
        }
        
        // Обновление статистики
        function updateStats() {
            fetch('/get_stats')
                .then(response => response.json())
                .then(data => {
                    if (data.active_games !== undefined) {
                        document.getElementById('activeGames').textContent = data.active_games;
                        document.getElementById('totalPlayers').textContent = data.total_players;
                    }
                })
                .catch(error => console.error('Ошибка загрузки статистики:', error));
        }
        
        // Анимация прогресс-баров
        function animateProgressBars() {
            const bars = document.querySelectorAll('.progress-fill');
            bars.forEach(bar => {
                const width = bar.style.width || '0%';
                const targetWidth = bar.getAttribute('data-width') || '75%';
                if (width !== targetWidth) {
                    bar.style.width = targetWidth;
                }
            });
        }
        
        // Инициализация
        document.addEventListener('DOMContentLoaded', function() {
            // Обновление времени каждую секунду
            updateServerTime();
            setInterval(updateServerTime, 1000);
            
            // Обновление статистики каждые 10 секунд
            updateStats();
            setInterval(updateStats, 10000);
            
            // Анимация прогресс-баров
            animateProgressBars();
            
            // Плавная прокрутка для якорей
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href');
                    if (targetId !== '#') {
                        const targetElement = document.querySelector(targetId);
                        if (targetElement) {
                            targetElement.scrollIntoView({ behavior: 'smooth' });
                        }
                    }
                });
            });
            
            // Эффект параллакса
            window.addEventListener('scroll', function() {
                const scrolled = window.pageYOffset;
                const parallaxElements = document.querySelectorAll('.hero, .stat-card');
                parallaxElements.forEach(element => {
                    const speed = element.dataset.speed || 0.5;
                    const yPos = -(scrolled * speed);
                    element.style.transform = `translateY(${yPos}px)`;
                });
            });
        });
        
        // Добавляем данные для прогресс-баров
        document.querySelectorAll('.progress-container').forEach((container, index) => {
            const fill = container.querySelector('.progress-fill');
            if (fill) {
                const widths = ['95%', '85%', '90%', '99%'];
                fill.setAttribute('data-width', widths[index] || '75%');
            }
        });
    </script>
</body>
</html>
    ''', 
    bot_status=bot_status,
    webhook_status=webhook_status,
    active_games=active_games,
    total_players=total_players,
    total_properties=total_properties,
    MAX_PLAYERS=MAX_PLAYERS,
    START_MONEY=START_MONEY,
    BOARD=BOARD,
    bot_info=bot_info,
    application=application,
    datetime=datetime,
    python_version='3.11',
    check_webhook_status=check_webhook_status
    ), 200

# Добавляем дополнительные маршруты для статистики
@flask_app.route('/get_stats')
def get_stats():
    """API для получения статистики"""
    active_games = len([g for g in games_storage.values() if g.get('status') != 'finished'])
    total_players = sum(len(g.get('players', {})) for g in games_storage.values())
    
    return json.dumps({
        'active_games': active_games,
        'total_players': total_players,
        'bot_online': application is not None,
        'timestamp': datetime.now().isoformat()
    }), 200, {'Content-Type': 'application/json'}

@flask_app.route('/docs')
def documentation():
    """Документация по API"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Документация API - Монополия Премиум</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f5f6fa; color: #2d3436; }
            .container { max-width: 1200px; margin: 0 auto; padding: 40px; }
            .api-endpoint { background: white; padding: 25px; margin: 20px 0; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .method { display: inline-block; padding: 5px 15px; border-radius: 5px; color: white; font-weight: bold; }
            .get { background: #00b894; }
            .post { background: #0984e3; }
            .endpoint { font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 Документация API</h1>
            <p>API для взаимодействия с ботом Монополия Премиум</p>
            
            <div class="api-endpoint">
                <span class="method get">GET</span>
                <span class="endpoint">/get_stats</span>
                <p>Получить текущую статистику сервера</p>
                <pre>{
    "active_games": 3,
    "total_players": 12,
    "bot_online": true,
    "timestamp": "2024-12-18T19:30:00"
}</pre>
            </div>
            
            <div class="api-endpoint">
                <span class="method get">GET</span>
                <span class="endpoint">/ping</span>
                <p>Проверка работоспособности API</p>
                <pre>Ответ: "pong"</pre>
            </div>
            
            <div class="api-endpoint">
                <span class="method get">GET</span>
                <span class="endpoint">/logs</span>
                <p>Просмотр логов сервера</p>
            </div>
            
            <div class="api-endpoint">
                <span class="method post">POST</span>
                <span class="endpoint">{{ WEBHOOK_PATH }}</span>
                <p>Вебхук для Telegram Bot API</p>
                <p>Принимает обновления от Telegram</p>
            </div>
        </div>
    </body>
    </html>
    ''', WEBHOOK_PATH=WEBHOOK_PATH), 200
