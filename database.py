import sqlite3

def init_db():
    # Подключаемся к файлу базы данных (он создастся сам)
    conn = sqlite3.connect('monopoly_final.db')
    cur = conn.cursor()

    # 1. Таблица Игроков: ID чата, ID юзера, Имя, Баланс, Позиция на поле, Статус Тюрьмы
    cur.execute('''
    CREATE TABLE IF NOT EXISTS players (
        chat_id INTEGER,
        user_id INTEGER,
        name TEXT,
        balance INTEGER DEFAULT 1500,
        pos INTEGER DEFAULT 0,
        jail INTEGER DEFAULT 0,
        PRIMARY KEY (chat_id, user_id)
    )''')

    # 2. Таблица Недвижимости: ID чата, Индекс клетки (0-39), ID владельца, Кол-во домов
    cur.execute('''
    CREATE TABLE IF NOT EXISTS property (
        chat_id INTEGER,
        cell_idx INTEGER,
        owner_id INTEGER,
        houses INTEGER DEFAULT 0,
        PRIMARY KEY (chat_id, cell_idx)
    )''')

    conn.commit()
    conn.close()
    print("База данных инициализирована успешно!")
