import sqlite3

def init_db():
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    # Игроки: баланс, позиция, чат
    cursor.execute('''CREATE TABLE IF NOT EXISTS players 
        (user_id INTEGER, chat_id INTEGER, username TEXT, balance INTEGER DEFAULT 1500, pos INTEGER DEFAULT 0, PRIMARY KEY(user_id, chat_id))''')
    # Список чатов для админки
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_chats (chat_id INTEGER PRIMARY KEY, title TEXT)''')
    conn.commit()
    conn.close()

def add_player(user_id, chat_id, username):
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO players (user_id, chat_id, username) VALUES (?, ?, ?)", (user_id, chat_id, username))
    conn.commit()
    conn.close()
