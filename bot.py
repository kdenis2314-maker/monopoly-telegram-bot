"""
🎩 МОНОПОЛИЯ ПРЕМИУМ - только для групп 🎩
Версия для Railway.app
"""

import json
import random
import logging
import os
import asyncio
from datetime import datetime
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError

# ========== БЕЗОПАСНЫЙ ТОКЕН ==========
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен! Добавьте в Variables на Railway")
    exit(1)

# Настройка логирования для Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
START_MONEY = 1500
MAX_PLAYERS = 6
BOARD_SIZE = 24  # Упрощенное поле для групп

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
    "auction": "🔨"
}

# Игровое поле (красивое с эмодзи)
BOARD = [
    {"name": f"{EMOJI['start']} СТАРТ", "type": "start", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Старая дорога", "type": "property", "price": 60, "color": "brown", "rent": [2, 10, 30, 90, 160, 250]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Белая улица", "type": "property", "price": 60, "color": "brown", "rent": [4, 20, 60, 180, 320, 450]},
    {"name": f"{EMOJI['tax']} Налог", "type": "tax", "price": 200, "color": "none"},
    {"name": f"{EMOJI['railroad']} Вокзал Южный", "type": "railroad", "price": 200, "color": "railroad", "rent": [25, 50, 100, 200]},
    {"name": f"{EMOJI['property']} Таганская", "type": "property", "price": 100, "color": "lightblue", "rent": [6, 30, 90, 270, 400, 550]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Варшавское шоссе", "type": "property", "price": 100, "color": "lightblue", "rent": [6, 30, 90, 270, 400, 550]},
    {"name": f"{EMOJI['jail']} ТЮРЬМА", "type": "jail", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Рублевское шоссе", "type": "property", "price": 140, "color": "pink", "rent": [10, 50, 150, 450, 625, 750]},
    {"name": f"{EMOJI['utility']} Электростанция", "type": "utility", "price": 150, "color": "utility", "rent": [4, 10]},
    {"name": f"{EMOJI['property']} Улица Арбат", "type": "property", "price": 220, "color": "red", "rent": [18, 90, 250, 700, 875, 1050]},
    {"name": f"{EMOJI['parking']} Парковка", "type": "parking", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Пушкинская", "type": "property", "price": 220, "color": "red", "rent": [18, 90, 250, 700, 875, 1050]},
    {"name": f"{EMOJI['railroad']} Вокзал Северный", "type": "railroad", "price": 200, "color": "railroad", "rent": [25, 50, 100, 200]},
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},
    {"name": f"{EMOJI['property']} Малая Бронная", "type": "property", "price": 320, "color": "green", "rent": [28, 150, 450, 1000, 1200, 1400]},
    {"name": f"{EMOJI['tax']} Суперналог", "type": "tax", "price": 100, "color": "none"},
    {"name": f"{EMOJI['property']} Тверской бульвар", "type": "property", "price": 400, "color": "darkblue", "rent": [50, 200, 600, 1400, 1700, 2000]},
]

# Хранилище игр {chat_id: game_data}
games = {}

# ===================== КРАСИВЫЕ КЛАВИАТУРЫ =====================
def get_add_to_group_keyboard(bot_username):
    """Клавиатура для добавления в группу"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"➕ ДОБАВИТЬ В ГРУППУ", 
            url=f"https://t.me/{bot_username}?startgroup=true"
        )],
        [InlineKeyboardButton("📋 Инструкция", callback_data="how_to_play")]
    ])

def get_lobby_keyboard(chat_id):
    """Клавиатура лобби"""
    player_count = len(games[chat_id]['players']) if chat_id in games and 'players' in games[chat_id] else 0
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ ПРИСОЕДИНИТЬСЯ", callback_data=f"join_{chat_id}")],
        [InlineKeyboardButton(f"🎮 НАЧАТЬ ({player_count}/6)", callback_data=f"start_{chat_id}")],
        [InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data=f"cancel_{chat_id}")]
    ])

def get_game_keyboard(player_id):
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

def get_buy_keyboard(property_idx, price, player_id):
    """Клавиатура покупки"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ КУПИТЬ (${price})", callback_data=f"buy_{property_idx}_{player_id}"),
            InlineKeyboardButton(f"{EMOJI['auction']} АУКЦИОН", callback_data=f"auction_{property_idx}_{player_id}")
        ],
        [InlineKeyboardButton("❌ ПРОПУСТИТЬ", callback_data=f"skip_{player_id}")]
    ])

# ===================== ОСНОВНЫЕ ФУНКЦИИ =====================
async def private_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start в личных сообщениях"""
    user = update.effective_user
    
    await update.message.reply_text(
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

async def group_monopoly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /monopoly в группе"""
    chat = update.effective_chat
    
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Эта команда работает только в группах!")
        return
    
    chat_id = chat.id
    
    # Проверяем, есть ли активная игра
    if chat_id in games and games[chat_id].get('status') != 'finished':
        game = games[chat_id]
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
        
        await update.message.reply_text(
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
    user = update.effective_user
    
    games[chat_id] = {
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
        'trades': []
    }
    
    # Добавляем создателя
    colors = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠']
    games[chat_id]['players'][user.id] = {
        'id': user.id,
        'username': user.username or user.first_name,
        'balance': START_MONEY,
        'position': 0,
        'color': colors[0],
        'properties': [],
        'in_jail': False,
        'jail_turns': 0,
        'get_out_of_jail': 0,
        'is_bankrupt': False
    }
    
    await update.message.reply_text(
        f"""🎮 *НОВАЯ ИГРА СОЗДАНА!*

🏁 *Создатель:* {colors[0]} @{user.username or user.first_name}
👥 *Игроки:* 1/6
💰 *Стартовый капитал:* ${START_MONEY}

👇 *Присоединяйтесь к игре!*
Минимум 2 игрока для начала.""",
        parse_mode='Markdown',
        reply_markup=get_lobby_keyboard(chat_id)
    )

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Присоединение к игре"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    user = query.from_user
    
    if chat_id not in games:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games[chat_id]
    
    if game['status'] != 'lobby':
        await query.answer("❌ Игра уже началась!")
        return
    
    if user.id in game['players']:
        await query.answer("✅ Вы уже в игре!")
        return
    
    if len(game['players']) >= MAX_PLAYERS:
        await query.answer("🚫 Максимум 6 игроков!")
        return
    
    # Выбираем цвет
    colors = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠']
    used_colors = [p['color'] for p in game['players'].values()]
    available_colors = [c for c in colors if c not in used_colors]
    
    if not available_colors:
        await query.answer("❌ Нет свободных цветов!")
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
        'is_bankrupt': False
    }
    
    # Формируем список игроков
    players_list = "\n".join(
        f"{p['color']} @{p['username']}" 
        for p in game['players'].values()
    )
    
    await query.edit_message_text(
        f"""🎮 *ЛОББИ ИГРЫ*

👥 *Игроки ({len(game['players'])}/6):*
{players_list}

💰 *Стартовый капитал:* ${START_MONEY}

👇 Присоединяйтесь или начинайте игру!""",
        parse_mode='Markdown',
        reply_markup=get_lobby_keyboard(chat_id)
    )

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало игры"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    
    if chat_id not in games:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games[chat_id]
    
    if len(game['players']) < 2:
        await query.answer("❌ Нужно минимум 2 игрока!")
        return
    
    if game['status'] != 'lobby':
        await query.answer("❌ Игра уже началась!")
        return
    
    # Начинаем игру
    game['status'] = 'active'
    game['turn_order'] = list(game['players'].keys())
    game['current_player'] = game['turn_order'][0]
    current_player = game['players'][game['current_player']]
    
    # Создаем красивое поле
    board_visual = create_board_visual(game)
    
    await query.edit_message_text(
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

async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Бросок кубиков"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    player_id = int(data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games[chat_id]
    
    if game['current_player'] != player_id:
        await query.answer("❌ Сейчас не ваш ход!")
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
        else:
            player['jail_turns'] += 1
            if player['jail_turns'] >= 3:
                # Платим штраф
                player['balance'] -= 50
                player['in_jail'] = False
                jail_msg = f"💸 Выплатили штраф $50 и вышли из тюрьмы"
            else:
                await query.answer(f"❌ Осталось в тюрьме (ход {player['jail_turns']}/3)")
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
    
    # Обработка клетки
    if cell['type'] == 'property':
        owner = game['board_state'][new_position]['owner']
        if owner is None:
            # Свободная собственность
            message += f"""💰 *СОБСТВЕННОСТЬ СВОБОДНА*

Цена: ${cell['price']}
Ваш баланс: ${player['balance']}

👇 Купите или начните аукцион!"""
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_buy_keyboard(new_position, cell['price'], player_id)
            )
            return
        elif owner == player_id:
            # Своя собственность
            message += "✅ Это ваша собственность!"
            await query.edit_message_text(
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
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_game_keyboard(player_id)
            )
    
    elif cell['type'] == 'tax':
        player['balance'] -= cell['price']
        message += f"""💸 *НАЛОГ*

Уплачено: ${cell['price']}
Баланс: ${player['balance']}"""
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )
    
    else:
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )
    
    # Если выпал дубль - можно еще раз
    if is_double and not player['in_jail']:
        await query.message.reply_text(
            f"🎯 {player['color']} @{player['username']} выбросил дубль!\nБросайте еще раз!",
            reply_markup=get_game_keyboard(player_id)
        )
        return
    
    # Ждем 2 секунды и переходим к следующему ходу
    await asyncio.sleep(2)
    await next_turn(game, chat_id, context)

async def buy_property(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Покупка собственности"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    property_idx = int(data[1])
    player_id = int(data[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games[chat_id]
    player = game['players'][player_id]
    cell = BOARD[property_idx]
    
    if player['balance'] < cell['price']:
        await query.answer("❌ Недостаточно денег!")
        return
    
    # Покупаем
    player['balance'] -= cell['price']
    player['properties'].append(property_idx)
    game['board_state'][property_idx]['owner'] = player_id
    
    await query.edit_message_text(
        f"""✅ *ПОКУПКА УСПЕШНА!*

{player['color']} @{player['username']}
🏠 Купил: *{cell['name']}*
💰 Потрачено: ${cell['price']}
💵 Остаток: ${player['balance']}

Отличная покупка!""",
        parse_mode='Markdown',
        reply_markup=get_game_keyboard(player_id)
    )
    
    await asyncio.sleep(2)
    await next_turn(game, chat_id, context)

async def skip_turn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск хода"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    await query.edit_message_text("⏭️ Ход пропущен")
    await next_turn(games[chat_id], chat_id, context)

async def end_turn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение хода"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games[chat_id]
    if game['current_player'] == player_id:
        await next_turn(game, chat_id, context)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка баланса"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games:
        return
    
    game = games[chat_id]
    player = game['players'].get(player_id)
    
    if player:
        await query.answer(f"💰 Баланс: ${player['balance']}", show_alert=True)

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def create_board_visual(game):
    """Создает визуализацию поля"""
    board = ""
    for i, cell in enumerate(BOARD):
        owner = game['board_state'][i]['owner']
        houses = game['board_state'][i]['houses']
        
        # Эмодзи для клетки
        if owner is not None and owner in game['players']:
            owner_color = game['players'][owner]['color']
            cell_display = f"{owner_color} {cell['name']}"
        else:
            cell_display = f"◻️ {cell['name']}"
        
        # Добавляем дома
        if houses > 0:
            house_emoji = EMOJI['hotel'] if houses >= 5 else EMOJI['house'] * min(houses, 4)
            cell_display += f" {house_emoji}"
        
        board += f"{i+1:2d}. {cell_display}\n"
    
    return board

def calculate_rent(game, property_idx, owner_id):
    """Расчет арендной платы"""
    cell = BOARD[property_idx]
    state = game['board_state'][property_idx]
    
    if cell['type'] =        
