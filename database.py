import sqlite3

def init_db():
    """Инициализация всех таблиц базы данных при запуске"""
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    
    # 1. Таблица игроков (баланс, позиция, профиль)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            balance INTEGER DEFAULT 1500,
            pos INTEGER DEFAULT 0,
            inventory TEXT,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    # 2. Таблица активных чатов (ДЛЯ ТВОЕГО ТРОЛЛЬ-МЕНЮ)
    # Сюда попадают все группы, где бот был активирован
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_chats (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Таблица текущих игровых сессий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            chat_id INTEGER PRIMARY KEY,
            status TEXT, -- 'lobby' (сбор), 'playing' (игра)
            current_turn INTEGER DEFAULT 0,
            player_order TEXT -- Список ID игроков через запятую
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных успешно инициализирована")

def add_player(user_id, chat_id, username):
    """Добавляет нового игрока, если его еще нет в этом чате"""
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO players (user_id, chat_id, username) 
        VALUES (?, ?, ?)
    ''', (user_id, chat_id, username))
    conn.commit()
    conn.close()

def add_chat(chat_id, title):
    """Регистрирует чат в базе для управления через админку (Тролль-меню)"""
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    # Используем INSERT OR REPLACE, чтобы обновлять название, если оно сменилось
    cursor.execute('''
        INSERT OR REPLACE INTO active_chats (chat_id, title) 
        VALUES (?, ?)
    ''', (chat_id, title))
    conn.commit()
    conn.close()

def get_all_chats():
    """Получает список всех чатов для вывода в админ-панели"""
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, title FROM active_chats")
    chats = cursor.fetchall()
    conn.close()
    return chats

def update_player_pos(user_id, chat_id, new_pos):
    """Обновляет позицию игрока на карте"""
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE players SET pos = ? 
        WHERE user_id = ? AND chat_id = ?
    ''', (new_pos, user_id, chat_id))
    conn.commit()
    conn.close()
