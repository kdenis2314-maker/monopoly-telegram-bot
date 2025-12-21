import sqlite3

def init_db():
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    # Игроки: баланс, позиция, чат
    cursor.execute('''CREATE TABLE IF NOT EXISTS players 
        (user_id INTEGER, chat_id INTEGER, username TEXT, balance INTEGER DEFAULT 1500, pos INTEGER DEFAULT 0, PRIMARY KEY(user_id, chat_id))''')
    # Список чатов для админки (Тролль-меню)
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_chats (chat_id INTEGER PRIMARY KEY, title TEXT)''')
    conn.commit()
    conn.close()

def add_chat(chat_id, title):
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO active_chats (chat_id, title) VALUES (?, ?)", (chat_id, title))
    conn.commit()
    conn.close()

def get_all_chats():
    conn = sqlite3.connect('monopoly.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, title FROM active_chats")
    res = cursor.fetchall()
    conn.close()
    return res
