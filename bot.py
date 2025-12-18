"""
🎩 МОНОПОЛИЯ ПРЕМИУМ - только для групп 🎩
Версия для Render.com с Webhook
"""

import os
import json
import random
import logging
import asyncio
from datetime import datetime
from typing import Dict, List
from threading import Thread

# ========== FLASK ДЛЯ WEBHOOK И АКТИВНОСТИ ==========
from flask import Flask, request

# Создаем Flask приложение
flask_app = Flask(__name__)

# ============ НАСТРОЙКИ ДЛЯ WEBHOOK (RENDER) ============

TOKEN = os.environ.get('BOT_TOKEN') 
if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

RENDER_DOMAIN = 'https://monopoly-telegram-bot.onrender.com'
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"{RENDER_DOMAIN}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 10000))

# --- FLASK МАРШРУТЫ ---
@flask_app.route('/ping')
def ping():
    return "pong", 200

# ==== ВСТАВЬТЕ ЭТОТ КОД ЗДЕСЬ ====
@flask_app.route('/')
def index():
    return """
    <html>
    <head>
        <title>🎩 МОНОПОЛИЯ ПРЕМИУМ - Telegram Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                max-width: 600px;
                margin: 0 auto;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            h1 {
                font-size: 2.5em;
                margin-bottom: 20px;
            }
            .emoji {
                font-size: 3em;
            }
            .status {
                background: rgba(0, 255, 0, 0.2);
                padding: 10px 20px;
                border-radius: 50px;
                display: inline-block;
                margin: 20px 0;
            }
            .links {
                margin-top: 30px;
            }
            a {
                color: #ffcc00;
                text-decoration: none;
                font-weight: bold;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">🎩</div>
            <h1>МОНОПОЛИЯ ПРЕМИУМ</h1>
            <p><strong>Telegram Bot для игры в группах</strong></p>
            
            <div class="status">
                ✅ Бот активен и работает
            </div>
            
            <div class="links">
                <p><a href="/ping">Проверить статус API</a></p>
                <p>Для начала игры добавьте бота в Telegram группу и напишите <code>/monopoly</code></p>
                <p>Бот: <a href="https://t.me/ВАШ_БОТ_ЮЗЕРНЕЙМ">@ВАШ_БОТ_ЮЗЕРНЕЙМ</a></p>
            </div>
            
            <p style="margin-top: 30px; font-size: 0.9em; opacity: 0.8;">
                Версия для Render.com с Webhook
            </p>
        </div>
    </body>
    </html>
    """, 200
# ==== КОНЕЦ ВСТАВЛЯЕМОГО КОДА ====

@flask_app.route(WEBHOOK_PATH, methods=['POST'])
def telegram_webhook():
    # ... ваш существующий код ...
    from telegram import Update
    if 'application' not in globals():
        return "Bot application not initialized", 503
    
    try:
        update_json = request.get_json(force=True)
        # Создаем объект Update
        update = Update.de_json(update_json, application.bot)
        # Обрабатываем update асинхронно
        asyncio.run(application.process_update(update))
        return "ok", 200
    except Exception as e:
        print(f"Ошибка вебхука: {e}")
        return "error", 500
# --- ОСНОВНОЙ КОД БОТА ---


# ========== ОСНОВНОЙ КОД БОТА ==========
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.ext import ApplicationBuilder
from telegram.error import TelegramError

# ... (Остальные глобальные переменные и настройки) ...

if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен! Добавьте в Environment Variables")
    # Не вызываем exit(1) здесь, чтобы Flask мог запуститься и показать ошибку в логах
    # print("❌ Ошибка: BOT_TOKEN не найден!")
    # print("ℹ️ Добавьте переменную BOT_TOKEN в настройках Render")
    
# Настройка логирования для Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
START_MONEY = 1500
MAX_PLAYERS = 6
BOARD_SIZE = 24

# Эмодзи для оформления (Оставлен как в вашем коде)
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

# Игровое поле (Оставлено как в вашем коде)
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
games_storage = {}
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
    player_count = len(games_storage[chat_id]['players']) if chat_id in games_storage and 'players' in games_storage[chat_id] else 0
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

def get_trade_keyboard(player_id):
    """Клавиатура для торговли"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💵 Предложить деньги", callback_data=f"trade_money_{player_id}")],
        [InlineKeyboardButton(f"🏠 Предложить имущество", callback_data=f"trade_props_{player_id}")],
        [InlineKeyboardButton(f"🤝 Принять предложение", callback_data=f"trade_accept_{player_id}")],
        [InlineKeyboardButton(f"❌ Отменить торговлю", callback_data=f"trade_cancel_{player_id}")]
    ])

def get_build_keyboard(property_idx, player_id):
    """Клавиатура для строительства"""
    house_price = 50
    hotel_price = 200
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🏡 Построить дом (${house_price})", callback_data=f"build_house_{property_idx}_{player_id}")],
        [InlineKeyboardButton(f"🏨 Построить отель (${hotel_price})", callback_data=f"build_hotel_{property_idx}_{player_id}")],
        [InlineKeyboardButton(f"↩️ Назад", callback_data=f"build_back_{player_id}")]
    ])

# ===================== ОСНОВНЫЕ ФУНКЦИИ (Продолжение в Части 2) =====================# ===================== ОСНОВНЫЕ ФУНКЦИИ (Продолжение из Части 1) =====================
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
    
    # Проверяем права бота
    try:
        member = await chat.get_member(context.bot.id)
        if member.status != 'administrator':
            await update.message.reply_text(
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
        logger.warning(f"Не удалось проверить права бота: {e}")
    
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
    colors = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠']
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
    
    if chat_id not in games_storage:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games_storage[chat_id]
    
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
        'is_bankrupt': False,
        'dice_doubles': 0
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
    
    if chat_id not in games_storage:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games_storage[chat_id]
    
    if len(game['players']) < 2:
        await query.answer("❌ Нужно минимум 2 игрока!")
        return
    
    if game['status'] != 'lobby':
        await query.answer("❌ Игра уже началась!")
        return
    
    # Начинаем игру
    game['status'] = 'active'
    game['turn_order'] = list(game['players'].keys())
    random.shuffle(game['turn_order'])  # Случайный порядок
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
    
    if chat_id not in games_storage:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games_storage[chat_id]
    
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
            await query.message.reply_text(jail_msg)
        else:
            player['jail_turns'] += 1
            if player['jail_turns'] >= 3:
                # Платим штраф
                player['balance'] -= 50
                player['in_jail'] = False
                jail_msg = f"💸 Выплатили штраф $50 и вышли из тюрьмы"
                await query.message.reply_text(jail_msg)
            else:
                await query.answer(f"❌ Осталось в тюрьме (ход {player['jail_turns']}/3)")
                # Переход хода
                await asyncio.sleep(1)
                await next_turn(game, chat_id, context)
                return
    
    # Учитываем дубли
    if is_double:
        player['dice_doubles'] += 1
        if player['dice_doubles'] >= 3:
            # Три дубля подряд - в тюрьму
            player['in_jail'] = True
            player['position'] = 9  # Тюрьма
            player['dice_doubles'] = 0
            await query.message.reply_text("🚓 Три дубля подряд! Вы отправляетесь в тюрьму!")
            await asyncio.sleep(2)
            await next_turn(game, chat_id, context)
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
    if cell['type'] == 'property' or cell['type'] == 'railroad' or cell['type'] == 'utility':
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
    
    elif cell['type'] == 'chance':
        # Карточка шанса
        chance_result = get_chance_card(player, game)
        message += f"""🎭 *КАРТОЧКА ШАНСА*

{chance_result['text']}"""
        
        if chance_result['money'] != 0:
            player['balance'] += chance_result['money']
            message += f"\n💰 Изменение баланса: ${chance_result['money']}"
        
        if chance_result['move'] != 0:
            new_pos = (player['position'] + chance_result['move']) % len(BOARD)
            player['position'] = new_pos
            message += f"\n📍 Новая позиция: {BOARD[new_pos]['name']}"
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )
    
    elif cell['type'] == 'jail':
        message += "🚓 *ТЮРЬМА*\nПроезжаете мимо."
        
        await query.edit_message_text(
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
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )
    
    else:
        message += f"📌 *{cell['type'].upper()}* клетка"
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
    
    # Сбрасываем счетчик дублей если не выпал дубль
    if not is_double:
        player['dice_doubles'] = 0
    
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
    
    if chat_id not in games_storage:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games_storage[chat_id]
    player = game['players'][player_id]
    cell = BOARD[property_idx]
    
    if player['balance'] < cell['price']:
        await query.answer("❌ Недостаточно денег!")
        return
    
    # Покупаем
    player['balance'] -= cell['price']
    player['properties'].append(property_idx)
    game['board_state'][property_idx]['owner'] = player_id
    
    # Проверяем монополию
    check_monopoly(game, player_id, cell['color'])
    
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
    """Пропуск хода/отказ от покупки"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games_storage[chat_id]
    
    if game['current_player'] != player_id:
        await query.answer("❌ Сейчас не ваш ход!")
        return
    
    await query.edit_message_text("⏭️ Ход пропущен")
    await next_turn(game, chat_id, context)

async def end_turn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение хода"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games_storage[chat_id]
    if game['current_player'] == player_id:
        await next_turn(game, chat_id, context)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка баланса"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    player = game['players'].get(player_id)
    
    if player:
        await query.answer(f"💰 Баланс: ${player['balance']}", show_alert=True)

async def check_properties(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка имущества"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    player = game['players'].get(player_id)
    
    if player:
        if not player['properties']:
            await query.answer("У вас нет собственности", show_alert=True)
            return
        
        properties_list = "\n".join(
            f"• {BOARD[idx]['name']} (${BOARD[idx]['price']})" 
            for idx in player['properties']
        )
        
        await query.answer(
            f"🏠 Ваша собственность:\n{properties_list}",
            show_alert=True
        )

async def trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню торговли"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    if game['current_player'] != player_id:
        await query.answer("❌ Сейчас не ваш ход!")
        return
    
    # Получаем список других игроков
    other_players = [
        p for p in game['players'].values() 
        if p['id'] != player_id and not p['is_bankrupt']
    ]
    
    if not other_players:
        await query.answer("❌ Нет других игроков для торговли!")
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
    
    await query.edit_message_text(
        f"🤝 *ТОРГОВЛЯ*\n\nВыберите игрока для торговли:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def trade_with_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Торговля с выбранным игроком"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    other_player_id = int(data[2])
    player_id = int(data[3])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    if game['current_player'] != player_id:
        await query.answer("❌ Сейчас не ваш ход!")
        return
    
    player = game['players'][player_id]
    other_player = game['players'][other_player_id]
    
    # Создаем предложение торговли
    game['trades'].append({
        'from_player': player_id,
        'to_player': other_player_id,
        'money_offer': 0,
        'properties_offer': [],
        'money_request': 0,
        'properties_request': [],
        'status': 'pending'
    })
    
    await query.edit_message_text(
        f"🤝 *ПРЕДЛОЖЕНИЕ ТОРГОВЛИ*\n\n"
        f"👤 Вы торгуете с: {other_player['color']} @{other_player['username']}\n"
        f"💰 Ваш баланс: ${player['balance']}\n"
        f"💰 Его баланс: ${other_player['balance']}\n\n"
        f"Выберите что предложить:",
        parse_mode='Markdown',
        reply_markup=get_trade_keyboard(player_id)
    )

async def trade_money_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предложение денег в торговле"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    player = game['players'][player_id]
    
    # Находим активную торговлю
    active_trade = None
    for trade in game['trades']:
        if trade['from_player'] == player_id and trade['status'] == 'pending':
            active_trade = trade
            break
    
    if not active_trade:
        await query.answer("❌ Нет активной торговли!")
        return
    
    await query.edit_message_text(
        f"💵 *ПРЕДЛОЖЕНИЕ ДЕНЕГ*\n\n"
        f"💰 Ваш баланс: ${player['balance']}\n"
        f"Введите сумму которую хотите предложить:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ Назад", callback_data=f"trade_back_{player_id}")]
        ])
    )
    
    # Сохраняем состояние для ввода суммы
    context.user_data['waiting_for_trade_money'] = True
    context.user_data['trade_player_id'] = player_id
    context.user_data['trade_chat_id'] = chat_id

async def trade_properties_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предложение имущества в торговле"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    player = game['players'][player_id]
    
    if not player['properties']:
        await query.answer("❌ У вас нет собственности для обмена!")
        return
    
    # Находим активную торговлю
    active_trade = None
    for trade in game['trades']:
        if trade['from_player'] == player_id and trade['status'] == 'pending':
            active_trade = trade
            break
    
    if not active_trade:
        await query.answer("❌ Нет активной торговли!")
        return
    
    # Создаем клавиатуру с имуществом
    buttons = []
    for prop_idx in player['properties']:
        cell = BOARD[prop_idx]
        buttons.append([
            InlineKeyboardButton(
                f"{cell['name']} (${cell['price']})",
                callback_data=f"trade_prop_select_{prop_idx}_{player_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("✅ Завершить выбор", callback_data=f"trade_props_done_{player_id}")])
    buttons.append([InlineKeyboardButton("↩️ Назад", callback_data=f"trade_back_{player_id}")])
    
    await query.edit_message_text(
        f"🏠 *ПРЕДЛОЖЕНИЕ ИМУЩЕСТВА*\n\n"
        f"Выберите собственность которую хотите предложить:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def trade_prop_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор конкретного имущества для торговли"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    prop_idx = int(data[3])
    player_id = int(data[4])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    # Находим активную торговлю
    active_trade = None
    for trade in game['trades']:
        if trade['from_player'] == player_id and trade['status'] == 'pending':
            active_trade = trade
            break
    
    if not active_trade:
        await query.answer("❌ Нет активной торговли!")
        return
    
    # Добавляем или удаляем имущество из предложения
    if prop_idx in active_trade['properties_offer']:
        active_trade['properties_offer'].remove(prop_idx)
        await query.answer("✅ Имущество удалено из предложения")
    else:
        active_trade['properties_offer'].append(prop_idx)
        await query.answer("✅ Имущество добавлено в предложение")
    
    # Обновляем список выбранного имущества
    selected_props = "\n".join([f"• {BOARD[idx]['name']}" for idx in active_trade['properties_offer']]) if active_trade['properties_offer'] else "Нет выбранного имущества"
    
    # Создаем клавиатуру с имуществом
    buttons = []
    for prop_idx in game['players'][player_id]['properties']:
        cell = BOARD[prop_idx]
        is_selected = prop_idx in active_trade['properties_offer']
        button_text = f"{'✅ ' if is_selected else ''}{cell['name']} (${cell['price']})"
        buttons.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"trade_prop_select_{prop_idx}_{player_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("✅ Завершить выбор", callback_data=f"trade_props_done_{player_id}")])
    buttons.append([InlineKeyboardButton("↩️ Назад", callback_data=f"trade_back_{player_id}")])
    
    await query.edit_message_text(
        f"🏠 *ПРЕДЛОЖЕНИЕ ИМУЩЕСТВА*\n\n"
        f"Выберите собственность которую хотите предложить:\n\n"
        f"📋 *Выбрано:*\n{selected_props}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def trade_props_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение выбора имущества для торговли"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[3])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    # Находим активную торговлю
    active_trade = None
    for trade in game['trades']:
        if trade['from_player'] == player_id and trade['status'] == 'pending':
            active_trade = trade
            break
    
    if not active_trade:
        await query.answer("❌ Нет активной торговли!")
        return
    
    other_player = game['players'][active_trade['to_player']]
    
    # Показываем итоговое предложение
    money_text = f"💰 Деньги: ${active_trade['money_offer']}" if active_trade['money_offer'] > 0 else ""
    props_text = "🏠 Имущество:\n" + "\n".join([f"• {BOARD[idx]['name']}" for idx in active_trade['properties_offer']]) if active_trade['properties_offer'] else ""
    
    await query.edit_message_text(
        f"🤝 *ВАШЕ ПРЕДЛОЖЕНИЕ*\n\n"
        f"👤 Для: {other_player['color']} @{other_player['username']}\n\n"
        f"{money_text}\n{props_text}\n\n"
        f"Ожидайте ответа от игрока...",
        parse_mode='Markdown'
    )
    
    # Уведомляем другого игрока
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🤝 *ПРЕДЛОЖЕНИЕ ТОРГОВЛИ*\n\n"
             f"👤 {game['players'][player_id]['color']} @{game['players'][player_id]['username']} предлагает вам сделку!\n\n"
             f"{money_text}\n{props_text}\n\n"
             f"Хотите принять предложение?",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Принять", callback_data=f"trade_accept_{active_trade['to_player']}")],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f"trade_reject_{active_trade['to_player']}")]
        ])
    )

async def trade_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принятие торгового предложения"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    # Находим торговлю где этот игрок получатель
    active_trade = None
    for trade in game['trades']:
        if trade['to_player'] == player_id and trade['status'] == 'pending':
            active_trade = trade
            break
    
    if not active_trade:
        await query.answer("❌ Нет активных предложений для вас!")
        return
    
    from_player = game['players'][active_trade['from_player']]
    to_player = game['players'][active_trade['to_player']]
    
    # Проверяем что у игроков достаточно денег
    if from_player['balance'] < active_trade['money_offer']:
        await query.answer("❌ У предлагающего недостаточно денег!")
        return
    
    # Выполняем обмен деньгами
    from_player['balance'] -= active_trade['money_offer']
    to_player['balance'] += active_trade['money_offer']
    
    # Выполняем обмен имуществом
    for prop_idx in active_trade['properties_offer']:
        if prop_idx in from_player['properties']:
            from_player['properties'].remove(prop_idx)
            to_player['properties'].append(prop_idx)
            game['board_state'][prop_idx]['owner'] = to_player['id']
    
    for prop_idx in active_trade['properties_request']:
        if prop_idx in to_player['properties']:
            to_player['properties'].remove(prop_idx)
            from_player['properties'].append(prop_idx)
            game['board_state'][prop_idx]['owner'] = from_player['id']
    
    # Отмечаем торговлю как выполненную
    active_trade['status'] = 'accepted'
    
    await query.edit_message_text(
        f"✅ *СДЕЛКА ЗАВЕРШЕНА!*\n\n"
        f"🤝 Игроки успешно обменялись:\n"
        f"{from_player['color']} @{from_player['username']} ↔️ {to_player['color']} @{to_player['username']}\n\n"
        f"💰 Переведено: ${active_trade['money_offer']}\n"
        f"🏠 Обменяно имущество",
        parse_mode='Markdown'
    )
    
    # Удаляем завершенные торги
    game['trades'] = [t for t in game['trades'] if t['status'] != 'accepted']

async def trade_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отклонение торгового предложения"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    # Находим и удаляем торговлю
    for trade in game['trades']:
        if trade['to_player'] == player_id and trade['status'] == 'pending':
            game['trades'].remove(trade)
            break
    
    await query.edit_message_text(
        "❌ *ПРЕДЛОЖЕНИЕ ОТКЛОНЕНО*",
        parse_mode='Markdown'
    )
    
    # Уведомляем предлагающего
    from_player_id = trade['from_player'] if 'trade' in locals() else None
    if from_player_id and from_player_id in game['players']:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ {game['players'][player_id]['color']} @{game['players'][player_id]['username']} отклонил ваше торговое предложение.",
            parse_mode='Markdown'
        )

async def trade_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена торговли"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    # Удаляем все pending торги этого игрока
    game['trades'] = [t for t in game['trades'] if not (t['from_player'] == player_id and t['status'] == 'pending')]
    
    await query.edit_message_text(
        "❌ *ТОРГОВЛЯ ОТМЕНЕНА*",
        parse_mode='Markdown',
        reply_markup=get_game_keyboard(player_id)
    )

async def trade_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назад из меню торговли"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    if game['current_player'] == player_id:
        await query.edit_message_text(
            f"🎮 *ВАШ ХОД*\n\n"
            f"{game['players'][player_id]['color']} @{game['players'][player_id]['username']}\n"
            f"💰 Баланс: ${game['players'][player_id]['balance']}\n"
            f"📍 Позиция: {BOARD[game['players'][player_id]['position']]['name']}",
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )

# ===================== ФУНКЦИИ СТРОИТЕЛЬСТВА И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (Продолжение из Части 2) =====================
async def build_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню строительства"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[1])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    player = game['players'].get(player_id)
    
    if not player or game['current_player'] != player_id:
        await query.answer("❌ Сейчас не ваш ход!")
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
        await query.answer("❌ Нет улиц для строительства!")
        return
    
    # Создаем клавиатуру
    buttons = []
    for prop_idx, cell, houses in buildable_properties:
        house_price = 50
        hotel_price = 200 # Стоимость отеля
        
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
    
    await query.edit_message_text(
        f"🏗️ *СТРОИТЕЛЬСТВО*\n\nВыберите улицу для строительства:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def build_house(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Строительство дома"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    property_idx = int(data[2])
    player_id = int(data[3])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    player = game['players'].get(player_id)
    
    if not player or game['current_player'] != player_id:
        await query.answer("❌ Сейчас не ваш ход!")
        return
    
    cell = BOARD[property_idx]
    current_houses = game['board_state'][property_idx]['houses']
    house_price = 50
    
    if current_houses >= 4:
        await query.answer("❌ Уже построено 4 дома!")
        return
    
    if player['balance'] < house_price:
        await query.answer("❌ Недостаточно денег!")
        return
    
    # Проверяем равномерность строительства
    color = cell['color']
    same_color_cells = [i for i, c in enumerate(BOARD) 
                       if c.get('color') == color and c['type'] == 'property']
    
    # Находим минимальное количество домов в этом цвете
    min_houses = min([game['board_state'][i]['houses'] for i in same_color_cells])
    
    if current_houses > min_houses:
        await query.answer("❌ Сначала постройте дома на других улицах этого цвета!")
        return
    
    # Строим дом
    player['balance'] -= house_price
    game['board_state'][property_idx]['houses'] += 1
    
    await query.edit_message_text(
        f"✅ *ДОМ ПОСТРОЕН!*\n\n"
        f"🏠 {cell['name']}\n"
        f"🏡 Теперь домов: {current_houses + 1}\n"
        f"💰 Потрачено: ${house_price}\n"
        f"💵 Остаток: ${player['balance']}",
        parse_mode='Markdown',
        reply_markup=get_game_keyboard(player_id)
    )

async def build_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Строительство отеля"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    property_idx = int(data[2])
    player_id = int(data[3])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    player = game['players'].get(player_id)
    
    if not player or game['current_player'] != player_id:
        await query.answer("❌ Сейчас не ваш ход!")
        return
    
    cell = BOARD[property_idx]
    current_houses = game['board_state'][property_idx]['houses']
    hotel_price = 200
    
    if current_houses != 4:
        await query.answer("❌ Сначала постройте 4 дома!")
        return
    
    if player['balance'] < hotel_price:
        await query.answer("❌ Недостаточно денег!")
        return
    
    # Строим отель
    player['balance'] -= hotel_price
    game['board_state'][property_idx]['houses'] = 5  # 5 = отель
    
    await query.edit_message_text(
        f"✅ *ОТЕЛЬ ПОСТРОЕН!*\n\n"
        f"🏨 {cell['name']}\n"
        f"💰 Потрачено: ${hotel_price}\n"
        f"💵 Остаток: ${player['balance']}\n\n"
        f"Теперь аренда максимальна!",
        parse_mode='Markdown',
        reply_markup=get_game_keyboard(player_id)
    )

async def build_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назад из меню строительства"""
    query = update.callback_query
    await query.answer()
    
    player_id = int(query.data.split('_')[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    if game['current_player'] == player_id:
        await query.edit_message_text(
            f"🎮 *ВАШ ХОД*\n\n"
            f"{game['players'][player_id]['color']} @{game['players'][player_id]['username']}\n"
            f"💰 Баланс: ${game['players'][player_id]['balance']}\n"
            f"📍 Позиция: {BOARD[game['players'][player_id]['position']]['name']}",
            parse_mode='Markdown',
            reply_markup=get_game_keyboard(player_id)
        )

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена игры"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    
    if chat_id in games_storage:
        del games_storage[chat_id]
    
    await query.edit_message_text("❌ Игра отменена")

async def how_to_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инструкция по игре"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
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
• Стройте равномерно на всех улицах цвета

🤝 *Торговля:*
• Обменивайтесь улицами и деньгами
• Только в свой ход
• Нужно согласие обоих игроков

🔨 *Аукцион:*
• Если игрок не покупает улицу
• Все могут предложить цену
• Выигрывает самая высокая ставка

🎭 *Шанс:*
• Случайные события
• Может дать или забрать деньги
• Может переместить на другую клетку

*Удачи в игре!* 🎩""",
        parse_mode='Markdown'
    )

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def create_board_visual(game):
    """Создает визуализацию поля"""
    board_lines = []
    
    for i in range(0, len(BOARD), 5):
        row = BOARD[i:i+5]
        line = ""
        for cell in row:
            idx = BOARD.index(cell)
            owner = game['board_state'][idx]['owner']
            houses = game['board_state'][idx]['houses']
            
            # Сокращаем название для компактности
            name_parts = cell['name'].split()
            short_name = name_parts[-1] if len(name_parts) > 1 else cell['name'][:10]
            
            if owner is not None and owner in game['players']:
                owner_color = game['players'][owner]['color']
                cell_display = f"{owner_color}{short_name}"
            else:
                cell_display = f"⬜{short_name}"
            
            # Добавляем дома
            if houses > 0:
                if houses >= 5:
                    house_emoji = "🏨"
                else:
                    house_emoji = "🏡" * houses
                cell_display += house_emoji
            
            line += f"{cell_display:12}"
        board_lines.append(line)
    
    return "\n".join(board_lines)

def calculate_rent(game, property_idx, owner_id):
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

def check_monopoly(game, player_id, color):
    """Проверяет, собрал ли игрок монополию"""
    same_color_cells = [i for i, c in enumerate(BOARD) 
                       if c.get('color') == color and c['type'] == 'property']
    
    has_monopoly = all(
        game['board_state'][i]['owner'] == player_id 
        for i in same_color_cells
    )
    
    if has_monopoly:
        # Уведомляем о монополии
        player = game['players'][player_id]
        color_name = {
            'brown': 'коричневые',
            'lightblue': 'голубые', 
            'pink': 'розовые',
            'red': 'красные',
            'green': 'зеленые',
            'darkblue': 'синие'
        }.get(color, color)
        
        # Можно добавить уведомление в чат
        logger.info(f"Игрок {player['username']} собрал монополию {color_name}")
    
    return has_monopoly

def get_chance_card(player, game):
    """Возвращает случайную карточку шанса"""
    chance_cards = [
        {
            "text": "Банковская ошибка в вашу пользу. Получите $200.",
            "money": 200,
            "move": 0
        },
        {
            "text": "Отправляйтесь в тюрьму. Отправляйтесь прямо в тюрьму.",
            "money": 0,
            "move": 0,
            "jail": True
        },
        {
            "text": "Отправляйтесь на Старую дорогу. Если вы проходите Старт, получите $200.",
            "money": 0,
            "move": 1 - player['position'] if player['position'] > 1 else 0
        },
        {
            "text": "Штраф за превышение скорости. Заплатите $15.",
            "money": -15,
            "move": 0
        },
        {
            "text": "Вы получили наследство. Получите $100.",
            "money": 100,
            "move": 0
        },
        {
            "text": "Отправляйтесь на Варшавское шоссе.",
            "money": 0,
            "move": 8 - player['position'] if player['position'] != 8 else 0
        },
        {
            "text": "Вас оштрафовали за парковку. Заплатите $10.",
            "money": -10,
            "move": 0
        },
        {
            "text": "Вы выиграли конкурс красоты. Получите $10.",
            "money": 10,
            "move": 0
        }
    ]
    
    card = random.choice(chance_cards)
    
    if card.get('jail'):
        player['in_jail'] = True
        player['position'] = 9  # Тюрьма
    
    return card

# ===================== ЛОГИКА ПЕРЕХОДА И ЗАВЕРШЕНИЯ (Продолжение из Части 3) =====================
async def next_turn(game, chat_id, context):
    """Переход к следующему игроку"""
    if not game['turn_order']:
        return
    
    # Проверяем банкротство текущего игрока
    current_player = game['players'][game['current_player']]
    if current_player['balance'] < 0 and not current_player['is_bankrupt']:
        await handle_bankruptcy(game, game['current_player'], chat_id, context)
    
    # Удаляем банкротов из порядка хода
    game['turn_order'] = [
        player_id for player_id in game['turn_order'] 
        if not game['players'][player_id]['is_bankrupt']
    ]
    
    if not game['turn_order']:
        await end_game(game, chat_id, context)
        return
    
    # Проверяем, остался ли только один игрок
    active_players = [p for p in game['players'].values() if not p['is_bankrupt']]
    if len(active_players) == 1:
        await end_game(game, chat_id, context)
        return
    
    # Находим следующего игрока
    current_idx = game['turn_order'].index(game['current_player'])
    next_idx = (current_idx + 1) % len(game['turn_order'])
    game['current_player'] = game['turn_order'][next_idx]
    
    next_player = game['players'][game['current_player']]
    
    # Отправляем сообщение о следующем ходе
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"""🎲 *СЛЕДУЮЩИЙ ХОД:*

{next_player['color']} @{next_player['username']}
💰 Баланс: ${next_player['balance']}
📍 Позиция: {BOARD[next_player['position']]['name']}
{"🚓 В ТЮРЬМЕ" if next_player['in_jail'] else ""}

👇 Ваш ход!""",
        parse_mode='Markdown',
        reply_markup=get_game_keyboard(game['current_player'])
    )

async def handle_bankruptcy(game, player_id, chat_id, context):
    """Обработка банкротства игрока"""
    player = game['players'][player_id]
    player['is_bankrupt'] = True
    
    # Освобождаем собственность
    for property_idx in player['properties']:
        game['board_state'][property_idx]['owner'] = None
        game['board_state'][property_idx]['houses'] = 0
    
    player['properties'] = []
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💀 *БАНКРОТСТВО!*\n\n"
             f"{player['color']} @{player['username']} обанкротился!\n"
             f"Его собственность возвращается банку.",
        parse_mode='Markdown'
    )

async def end_game(game, chat_id, context):
    """Завершение игры"""
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
    
    # Отправляем финальное сообщение
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"""🎮 *ИГРА ЗАВЕРШЕНА!*

{winner_text}

🎩 Спасибо за игру в Монополию!""",
        parse_mode='Markdown'
    )
    
    # Удаляем игру из хранилища через 5 минут
    await asyncio.sleep(300)  # 5 минут
    if chat_id in games_storage and games_storage[chat_id]['status'] == 'finished':
        del games_storage[chat_id]

async def auction_property(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало аукциона"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    property_idx = int(data[1])
    player_id = int(data[2])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        await query.edit_message_text("❌ Игра не найдена!")
        return
    
    game = games_storage[chat_id]
    cell = BOARD[property_idx]
    
    if game['current_player'] != player_id:
        await query.answer("❌ Сейчас не ваш ход!")
        return
    
    # Создаем аукцион
    game['auctions'].append({
        'property_idx': property_idx,
        'current_bid': cell['price'] // 2,  # Стартовая цена - половина стоимости
        'current_bidder': None,
        'bidders': list(game['players'].keys()),
        'min_increment': 10,
        'bid_count': 0,
        'max_bids': 3
    })
    
    auction = game['auctions'][-1]
    
    await query.edit_message_text(
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

def get_auction_keyboard(property_idx, current_bid, player_id):
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

async def auction_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ставка на аукционе"""
    query = update.callback_query
    await query.answer()
    
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
        await query.answer("❌ Аукцион не найден!")
        return
    
    player = game['players'][player_id]
    
    # Проверяем ставку
    if bid_amount <= auction['current_bid']:
        await query.answer(f"❌ Ставка должна быть выше ${auction['current_bid']}!")
        return
    
    if player['balance'] < bid_amount:
        await query.answer("❌ Недостаточно денег для ставки!")
        return
    
    # Обновляем ставку
    auction['current_bid'] = bid_amount
    auction['current_bidder'] = player_id
    auction['bid_count'] = 0  # Сбрасываем счетчик пропусков
    
    await query.edit_message_text(
        f"""🔨 *АУКЦИОН*

🏠 {BOARD[property_idx]['name']}
💰 Текущая ставка: *${bid_amount}*
👤 Текущий лидер: {player['color']} @{player['username']}

👇 Сделайте следующую ставку:""",
        parse_mode='Markdown',
        reply_markup=get_auction_keyboard(property_idx, bid_amount, player_id)
    )

async def auction_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Своя ставка на аукционе"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    property_idx = int(data[2])
    player_id = int(data[3])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    # Находим активный аукцион
    auction = None
    for a in game['auctions']:
        if a['property_idx'] == property_idx:
            auction = a
            break
    
    if not auction:
        await query.answer("❌ Аукцион не найден!")
        return
    
    await query.edit_message_text(
        f"""💎 *СВОЯ СТАВКА*

🏠 {BOARD[property_idx]['name']}
💰 Текущая ставка: ${auction['current_bid']}

Введите сумму вашей ставки (не менее ${auction['current_bid'] + auction['min_increment']}):""",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ Назад", callback_data=f"auction_back_{property_idx}_{player_id}")]
        ])
    )
    
    # Сохраняем состояние для ввода суммы
    context.user_data['waiting_for_auction_bid'] = True
    context.user_data['auction_property_idx'] = property_idx
    context.user_data['auction_player_id'] = player_id
    context.user_data['auction_chat_id'] = chat_id

async def auction_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назад в аукцион"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    property_idx = int(data[2])
    player_id = int(data[3])
    chat_id = query.message.chat.id
    
    if chat_id not in games_storage:
        return
    
    game = games_storage[chat_id]
    
    # Находим активный аукцион
    auction = None
    for a in game['auctions']:
        if a['property_idx'] == property_idx:
            auction = a
            break
    
    if not auction:
        await query.edit_message_text("❌ Аукцион не найден!")
        return
    
    await query.edit_message_text(
        f"""🔨 *АУКЦИОН*

🏠 {BOARD[property_idx]['name']}
💰 Текущая ставка: ${auction['current_bid']}
👤 Текущий лидер: {game['players'][auction['current_bidder']]['color'] if auction['current_bidder'] else 'Нет'}

👇 Сделайте следующую ставку:""",
        parse_mode='Markdown',
        reply_markup=get_auction_keyboard(property_idx, auction['current_bid'], player_id)
    )

async def auction_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение аукциона"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    property_idx = int(data[2])
    player_id = int(data[3])
    chat_id = query.message.chat.id
    
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
        
        # Проверяем монополию
        check_monopoly(game, winner_id, cell['color'])
        
        await query.edit_message_text(
            f"""✅ *АУКЦИОН ЗАВЕРШЕН!*

🏠 {cell['name']}
💰 Продано за: ${auction_to_remove['current_bid']}
👑 Победитель: {winner['color']} @{winner['username']}

Поздравляем с покупкой!""",
            parse_mode='Markdown'
        )
    else:
        # Никто не купил
        await query.edit_message_text(
            f"""⏹️ *АУКЦИОН ОТМЕНЕН*

🏠 {BOARD[property_idx]['name']}
❌ Никто не сделал ставку

Собственность остается у банка.""",
            parse_mode='Markdown'
        )
    
    await asyncio.sleep(2)
    await next_turn(game, chat_id, context)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода"""
    if not update.message:
        return
    
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Проверяем ожидание суммы для торговли
    if context.user_data.get('waiting_for_trade_money'):
        try:
            amount = int(text)
            player_id = context.user_data['trade_player_id']
            trade_chat_id = context.user_data['trade_chat_id']
            
            if trade_chat_id not in games_storage:
                return
            
            game = games_storage[trade_chat_id]
            player = game['players'].get(player_id)
            
            if not player:
                await update.message.reply_text("❌ Игрок не найден!")
                return
            
            if amount <= 0:
                await update.message.reply_text("❌ Сумма должна быть положительной!")
                return
            
            if amount > player['balance']:
                await update.message.reply_text("❌ У вас недостаточно денег!")
                return
            
            # Находим активную торговлю
            active_trade = None
            for trade in game['trades']:
                if trade['from_player'] == player_id and trade['status'] == 'pending':
                    active_trade = trade
                    break
            
            if not active_trade:
                await update.message.reply_text("❌ Нет активной торговли!")
                return
            
            # Устанавливаем сумму предложения
            active_trade['money_offer'] = amount
            
            # Очищаем состояние
            context.user_data.pop('waiting_for_trade_money', None)
            context.user_data.pop('trade_player_id', None)
            context.user_data.pop('trade_chat_id', None)
            
            await update.message.reply_text(
                f"✅ Сумма ${amount} установлена как предложение!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад к торговле", callback_data=f"trade_back_{player_id}")]
                ])
            )
            
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите число!")
    
    # Проверяем ожидание ставки для аукциона
    elif context.user_data.get('waiting_for_auction_bid'):
        try:
            amount = int(text)
            property_idx = context.user_data['auction_property_idx']
            player_id = context.user_data['auction_player_id']
            auction_chat_id = context.user_data['auction_chat_id']
            
            if auction_chat_id not in games_storage:
                return
            
            game = games_storage[auction_chat_id]
            
            # Находим активный аукцион
            auction = None
            for a in game['auctions']:
                if a['property_idx'] == property_idx:
                    auction = a
                    break
            
            if not auction:
                await update.message.reply_text("❌ Аукцион не найден!")
                return
            
            player = game['players'].get(player_id)
            
            if not player:
                await update.message.reply_text("❌ Игрок не найден!")
                return
            
            # Проверяем ставку
            if amount <= auction['current_bid']:
                await update.message.reply_text(f"❌ Ставка должна быть выше ${auction['current_bid']}!")
                return
            
            if player['balance'] < amount:
                await update.message.reply_text("❌ Недостаточно денег для ставки!")
                return
            
            # Обновляем ставку
            auction['current_bid'] = amount
            auction['current_bidder'] = player_id
            auction['bid_count'] = 0
            
            # Очищаем состояние
            context.user_data.pop('waiting_for_auction_bid', None)
            context.user_data.pop('auction_property_idx', None)
            context.user_data.pop('auction_player_id', None)
            context.user_data.pop('auction_chat_id', None)
            
            await update.message.reply_text(
                f"✅ Ваша ставка ${amount} принята!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад к аукциону", callback_data=f"auction_back_{property_idx}_{player_id}")]
                ])
            )
            
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите число!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    
    try:
        # Пытаемся уведомить пользователя об ошибке
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Произошла ошибка. Попробуйте еще раз или перезапустите игру командой /monopoly"
            )
    except:
        pass

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик неизвестных команд"""
    await update.message.reply_text(
        "🤔 Неизвестная команда. Используйте:\n"
        "/start - информация о боте\n"
        "/monopoly - начать игру в группе\n"
        "/help - помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    await update.message.reply_text(
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

# ===================== ОСНОВНАЯ ФУНКЦИЯ =====================
application = None

def main():
    global application
    if not TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return

    # 1. Создаем объект приложения
    application = Application.builder().token(TOKEN).build()

    # 2. Регистрируем все обработчики
    # Команды
    application.add_handler(CommandHandler("start", private_start))
    application.add_handler(CommandHandler("monopoly", group_monopoly))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    # Кнопки (Callback queries)
    application.add_handler(CallbackQueryHandler(join_game, pattern="^join_"))
    application.add_handler(CallbackQueryHandler(start_game, pattern="^start_"))
    application.add_handler(CallbackQueryHandler(roll_dice, pattern="^roll_"))
    application.add_handler(CallbackQueryHandler(buy_property, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(skip_turn, pattern="^skip_"))
    application.add_handler(CallbackQueryHandler(end_turn, pattern="^end_"))
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^balance_"))
    application.add_handler(CallbackQueryHandler(check_properties, pattern="^props_"))
    application.add_handler(CallbackQueryHandler(trade_menu, pattern="^trade_menu_"))
    application.add_handler(CallbackQueryHandler(trade_with_player, pattern="^trade_with_"))
    application.add_handler(CallbackQueryHandler(trade_money_offer, pattern="^trade_money_"))
    application.add_handler(CallbackQueryHandler(trade_properties_offer, pattern="^trade_props_"))
    application.add_handler(CallbackQueryHandler(trade_prop_select, pattern="^trade_prop_select_"))
    application.add_handler(CallbackQueryHandler(trade_props_done, pattern="^trade_props_done_"))
    application.add_handler(CallbackQueryHandler(trade_accept, pattern="^trade_accept_"))
    application.add_handler(CallbackQueryHandler(trade_reject, pattern="^trade_reject_"))
    application.add_handler(CallbackQueryHandler(trade_cancel, pattern="^trade_cancel_"))
    application.add_handler(CallbackQueryHandler(trade_back, pattern="^trade_back_"))
    application.add_handler(CallbackQueryHandler(build_menu, pattern="^build_"))
    application.add_handler(CallbackQueryHandler(build_house, pattern="^build_house_"))
    application.add_handler(CallbackQueryHandler(build_hotel, pattern="^build_hotel_"))
    application.add_handler(CallbackQueryHandler(build_back, pattern="^build_back_"))
    application.add_handler(CallbackQueryHandler(auction_property, pattern="^auction_"))
    application.add_handler(CallbackQueryHandler(auction_bid, pattern="^auction_bid_"))
    application.add_handler(CallbackQueryHandler(auction_custom, pattern="^auction_custom_"))
    application.add_handler(CallbackQueryHandler(auction_back, pattern="^auction_back_"))
    application.add_handler(CallbackQueryHandler(auction_end, pattern="^auction_end_"))
    application.add_handler(CallbackQueryHandler(how_to_play, pattern="how_to_play"))
    application.add_handler(CallbackQueryHandler(cancel_game, pattern="^cancel_"))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # 3. Асинхронная инициализация
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Запускаем внутренние механизмы бота
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start()) 
    
    # Установка вебхука в Telegram
    try:
        loop.run_until_complete(application.bot.set_webhook(url=WEBHOOK_URL))
        logger.info(f"✅ Webhook установлен на: {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ Ошибка установки вебхука: {e}")

    # 4. ЗАПУСК FLASK (это блокирующая операция, должна быть последней)
    logger.info(f"🚀 Запуск Flask на порту {PORT}...")
    # host='0.0.0.0' — обязательное требование Render
    flask_app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
