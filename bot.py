"""
🎩 МОНОПОЛИЯ ПРЕМИУМ - только для групп 🎩
Версия для Render.com с Webhook
"""

import os
import json
import random
import logging
import asyncio
import traceback
from datetime import datetime
from typing import Dict, List
from threading import Thread
from queue import Queue
import html

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
    """УСИЛЕННАЯ версия - гарантированно работает"""
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
        
        # 1. Всегда печатаем в консоль (для Render логов)
        print(f"🟢 [WEB_LOG] {timestamp} {level}: {message}")
        print(f"🟢 [WEB_LOG_DEBUG] Всего логов до добавления: {len(web_logs)}")
        
        # 2. Добавляем в список
        web_logs.append(log_entry)
        
        # 3. Ограничиваем размер
        if len(web_logs) > MAX_WEB_LOGS:
            web_logs.pop(0)
            
        # 4. Проверяем результат
        print(f"🟢 [WEB_LOG_DEBUG] Всего логов после добавления: {len(web_logs)}")
        print(f"🟢 [WEB_LOG_DEBUG] Последний лог: {log_entry}")
        
    except Exception as e:
        # Даже если ошибка - пишем в консоль
        print(f"🔴 [WEB_LOG_ERROR] Ошибка в add_web_log: {e}")
        import traceback
        traceback.print_exc()

# ========== ТЕСТИРУЕМ add_web_log СРАЗУ ==========
print("=" * 50)
print("🟢 ТЕСТИРУЕМ add_web_log...")
add_web_log("🟢 ТЕСТ: функция add_web_log работает", "DEBUG")
print(f"🟢 РЕЗУЛЬТАТ: web_logs содержит {len(web_logs)} записей")
if web_logs:
    print(f"🟢 ПЕРВАЯ запись: {web_logs[0]}")
print("=" * 50)

# ========== ПРОСТЕЙШАЯ ИНИЦИАЛИЗАЦИЯ БОТА ==========
print("=" * 60)
print("🎩 МОНОПОЛИЯ ПРЕМИУМ - Telegram Bot")
print("=" * 60)
print(f"📅 Время запуска: {datetime.now()}")
print(f"📋 Токен установлен: {'✅ Да' if TOKEN else '❌ Нет'}")

application = None  # ← ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ ДЛЯ БОТА

if TOKEN:
    try:
        print("🤖 САМАЯ ПРОСТАЯ инициализация бота...")
        
        # 1. ТОЛЬКО создаем Application - БЕЗ обработчиков!
        print("  1. Создаем Application...")
        from telegram.ext import Application
        application = Application.builder().token(TOKEN).build()
        print(f"  ✅ Application создан: {type(application)}")
        
        # 2. НЕ добавляем обработчики сейчас - они добавятся позже через application.add_handler
        print("  2. Обработчики будут добавлены ПОЗЖЕ")
        
        # 3. Проверяем состояние
        if application:
            print(f"  ✅ Бот создан успешно")
            # Проверяем бота
            try:
                if hasattr(application, 'bot') and application.bot:
                    print(f"  ✅ application.bot доступен")
                else:
                    print("  ⚠️  application.bot = None или недоступен")
            except:
                print("  ⚠️  Не удалось проверить application.bot")
        else:
            print("  ⚠️  Бот не создан")
        
        # 4. Логируем
        add_web_log("🤖 Бот создан (только Application объект)", "INFO")
        print("  ✅ Лог добавлен")
        
    except Exception as e:
        print(f"❌ Ошибка создания Application: {e}")
        import traceback
        traceback.print_exc()
        application = None
        add_web_log(f"❌ Ошибка создания Application: {e}", "ERROR")
else:
    print("⚠️  Токен не установлен - бот не создан")
    application = None
    add_web_log("⚠️  Токен не установлен, бот не создан", "WARNING")

print(f"📊 Итог: application создан = {'✅ Да' if application else '❌ Нет'}")
print("=" * 60)
print("✅ Инициализация завершена")
print("=" * 60)

# ========== FLASK ДЛЯ WEBHOOK И АКТИВНОСТИ ==========
from flask import Flask, request, render_template_string

# Создаем Flask приложение
flask_app = Flask(__name__)

# ============ НАСТРОЙКИ ДЛЯ WEBHOOK (RENDER) ============
TOKEN = os.environ.get('BOT_TOKEN') 
if not TOKEN:
    print("⚠️ ВНИМАНИЕ: Переменная окружения BOT_TOKEN не установлена!")
    print("ℹ️ Добавьте переменную BOT_TOKEN в настройках Render")
    print("ℹ️ Получить токен: @BotFather в Telegram -> /newbot")

RENDER_DOMAIN = os.environ.get('RENDER_DOMAIN', 'https://monopoly-telegram-bot-7.onrender.com')
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"{RENDER_DOMAIN}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 10000))

# Настройка логирования для Render
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
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    web_logs.append(log_entry)
    if len(web_logs) > MAX_WEB_LOGS:
        web_logs.pop(0)
# --- FLASK МАРШРУТЫ ---
@flask_app.route('/ping')
def ping():
    add_web_log("Запрос /ping получен", "INFO")
    return "pong", 200

@flask_app.route('/')
def index():
    """Главная страница с информацией о состоянии бота"""
    bot_status = "✅ Активен" if TOKEN else "❌ Неактивен (нет токена)"
    webhook_status = "✅ Установлен" if check_webhook_status() else "❌ Не установлен"
    
    # Статистика игр
    active_games = len([g for g in games_storage.values() if g.get('status') != 'finished'])
    total_players = sum(len(g.get('players', {})) for g in games_storage.values())
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎩 МОНОПОЛИЯ ПРЕМИУМ - Telegram Bot</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .header .emoji {
                font-size: 4em;
                margin-bottom: 20px;
            }
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            .status-card {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 15px;
                padding: 25px;
                transition: transform 0.3s;
            }
            .status-card:hover {
                transform: translateY(-5px);
            }
            .status-card h3 {
                color: #ffcc00;
                margin-bottom: 15px;
                font-size: 1.3em;
            }
            .status-item {
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                padding-bottom: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .status-value {
                font-weight: bold;
                color: #4cd964;
            }
            .status-value.error { color: #ff3b30; }
            .status-value.warning { color: #ffcc00; }
            
            .actions {
                text-align: center;
                margin: 40px 0;
            }
            .btn {
                display: inline-block;
                background: #ffcc00;
                color: #333;
                padding: 15px 30px;
                margin: 10px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: bold;
                font-size: 1.1em;
                transition: all 0.3s;
                border: none;
                cursor: pointer;
            }
            .btn:hover {
                background: #ffdd44;
                transform: scale(1.05);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            }
            .btn-secondary {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            .btn-secondary:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            
            .logs-section {
                margin-top: 40px;
            }
            .logs-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            .logs-container {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 10px;
                padding: 20px;
                max-height: 300px;
                overflow-y: auto;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }
            .log-entry {
                padding: 8px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .log-timestamp { color: #4cd964; }
            .log-level { font-weight: bold; }
            .log-level.INFO { color: #5ac8fa; }
            .log-level.WARNING { color: #ffcc00; }
            .log-level.ERROR { color: #ff3b30; }
            .log-message { color: white; }
            
            .instructions {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 15px;
                padding: 25px;
                margin-top: 40px;
            }
            .instructions h3 {
                color: #ffcc00;
                margin-bottom: 15px;
            }
            .instructions ol {
                margin-left: 20px;
                line-height: 1.8;
            }
            
            @media (max-width: 768px) {
                .container { padding: 15px; }
                .header h1 { font-size: 2em; }
                .btn { display: block; width: 100%; margin: 10px 0; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">🎩</div>
                <h1>МОНОПОЛИЯ ПРЕМИУМ</h1>
                <p><strong>Telegram Bot для игры в группах</strong></p>
            </div>
            
            <div class="status-grid">
                <div class="status-card">
                    <h3>Статус системы</h3>
                    <div class="status-item">
                        <span>Бот:</span>
                        <span class="status-value">{{ bot_status }}</span>
                    </div>
                    <div class="status-item">
                        <span>Вебхук:</span>
                        <span class="status-value {{ 'error' if webhook_status.startswith('❌') else '' }}">
                            {{ webhook_status }}
                        </span>
                    </div>
                    <div class="status-item">
                        <span>Активных игр:</span>
                        <span class="status-value">{{ active_games }}</span>
                    </div>
                    <div class="status-item">
                        <span>Всего игроков:</span>
                        <span class="status-value">{{ total_players }}</span>
                    </div>
                </div>
                
                <div class="status-card">
                    <h3>Статистика</h3>
                    <div class="status-item">
                        <span>Запущен:</span>
                        <span class="status-value">{{ startup_time }}</span>
                    </div>
                    <div class="status-item">
                        <span>Версия:</span>
                        <span class="status-value">Render Webhook</span>
                    </div>
                    <div class="status-item">
                        <span>Порт:</span>
                        <span class="status-value">{{ PORT }}</span>
                    </div>
                    <div class="status-item">
                        <span>Домен:</span>
                        <span class="status-value">{{ RENDER_DOMAIN }}</span>
                    </div>
                </div>
            </div>
            
            <div class="actions">
                <a href="/ping" class="btn">🔍 Проверить статус API</a>
                <a href="/webhook_info" class="btn btn-secondary">🌐 Информация о вебхуке</a>
                <a href="/logs" class="btn btn-secondary">📊 Просмотр логов</a>
                {% if not webhook_status.startswith('✅') %}
                <a href="/set_webhook_manual" class="btn" style="background: #ff3b30;">
                    🔧 Установить вебхук
                </a>
                {% endif %}
            </div>
            
            <div class="instructions">
                <h3>📋 Инструкция по использованию</h3>
                <ol>
                    <li>Добавьте бота в Telegram группу как администратора</li>
                    <li>Напишите в группе команду <code>/monopoly</code></li>
                    <li>Пригласите друзей присоединиться к игре</li>
                    <li>Начните игру, когда наберется минимум 2 игрока</li>
                    <li>Используйте кнопки под сообщениями для игровых действий</li>
                </ol>
            </div>
            
            <div class="logs-section">
                <div class="logs-header">
                    <h3>📝 Последние логи (живые)</h3>
                    <a href="/clear_logs" class="btn btn-secondary" style="padding: 8px 20px; font-size: 0.9em;">
                        🗑️ Очистить логи
                    </a>
                </div>
                <div class="logs-container">
                    {% for log in recent_logs %}
                    <div class="log-entry">
                        <span class="log-timestamp">[{{ log.timestamp }}]</span>
                        <span class="log-level {{ log.level }}">{{ log.level }}</span>
                        <span class="log-message">{{ log.message }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <script>
            // Автообновление логов каждые 5 секунд
            function refreshLogs() {
                fetch('/get_logs')
                    .then(response => response.json())
                    .then(logs => {
                        const container = document.querySelector('.logs-container');
                        container.innerHTML = logs.map(log => 
                            `<div class="log-entry">
                                <span class="log-timestamp">[${log.timestamp}]</span>
                                <span class="log-level ${log.level}">${log.level}</span>
                                <span class="log-message">${log.message}</span>
                            </div>`
                        ).join('');
                    })
                    .catch(error => console.error('Ошибка загрузки логов:', error));
            }
            
            // Обновляем логи при загрузке страницы
            document.addEventListener('DOMContentLoaded', function() {
                refreshLogs();
                setInterval(refreshLogs, 5000); // Каждые 5 секунд
                
                // Автообновление статуса каждые 10 секунд
                setInterval(() => location.reload(), 10000);
            });
        </script>
    </body>
    </html>
    ''', 
    bot_status=bot_status,
    webhook_status=webhook_status,
    active_games=active_games,
    total_players=total_players,
    startup_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    PORT=PORT,
    RENDER_DOMAIN=RENDER_DOMAIN,
    recent_logs=web_logs[-20:] if web_logs else []
    ), 200

def check_webhook_status():
    """Проверяет статус вебхука"""
    try:
        import requests
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok') and data.get('result', {}).get('url'):
                return True
        return False
    except:
        return False
@flask_app.route('/webhook_info')
def webhook_info():
    """Страница с информацией о вебхуке"""
    try:
        import requests
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo", timeout=5)
        data = response.json() if response.status_code == 200 else {}
        
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Информация о вебхуке</title>
            <style>
                body { font-family: Arial; padding: 20px; background: #f0f0f0; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
                .status { padding: 15px; border-radius: 5px; margin: 20px 0; font-weight: bold; }
                .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
                .info-item { padding: 10px; background: #f8f9fa; border-radius: 5px; }
                .label { font-weight: bold; color: #666; }
                .value { color: #333; }
                pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
                .actions { margin-top: 30px; }
                .btn { display: inline-block; padding: 10px 20px; margin-right: 10px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }
                .btn:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌐 Информация о вебхуке Telegram</h1>
                
                <div class="status {{ 'success' if data.ok else 'error' }}">
                    {% if data.ok %}
                    ✅ Вебхук установлен и работает
                    {% else %}
                    ❌ Ошибка вебхука
                    {% endif %}
                </div>
                
                <div class="info-grid">
                    <div class="info-item">
                        <div class="label">URL вебхука:</div>
                        <div class="value">{{ data.result.url if data.ok else 'Не установлен' }}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">Ожидающих сообщений:</div>
                        <div class="value">{{ data.result.pending_update_count if data.ok else 'N/A' }}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">Ошибка:</div>
                        <div class="value">{{ data.result.last_error_message if data.ok and data.result.last_error_message else 'Нет ошибок' }}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">IP адрес:</div>
                        <div class="value">{{ data.result.ip_address if data.ok else 'N/A' }}</div>
                    </div>
                </div>
                
                <h3>Полный ответ API:</h3>
                <pre>{{ data|tojson(indent=2) }}</pre>
                
                <div class="actions">
                    <a href="/" class="btn">← На главную</a>
                    <a href="/set_webhook_manual" class="btn">🔧 Установить вебхук</a>
                    <a href="/delete_webhook" class="btn" style="background: #dc3545;">🗑️ Удалить вебхук</a>
                </div>
            </div>
        </body>
        </html>
        ''', data=data), 200
    except Exception as e:
        return f"Ошибка при получении информации о вебхуке: {str(e)}", 500

@flask_app.route('/set_webhook_manual')
def set_webhook_manual():
    """Ручная установка вебхука"""
    try:
        import requests
        webhook_url = f"{RENDER_DOMAIN}{WEBHOOK_PATH}"
        api_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        
        response = requests.get(api_url, timeout=10)
        data = response.json() if response.status_code == 200 else {}
        
        add_web_log(f"Вебхук установлен вручную: {webhook_url}", "INFO")
        
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Установка вебхука</title>
            <style>
                body { font-family: Arial; padding: 20px; background: #f0f0f0; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
                .success { color: #28a745; font-size: 24px; margin: 20px 0; }
                .error { color: #dc3545; font-size: 24px; margin: 20px 0; }
                .info { background: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: left; }
                code { background: #f8f9fa; padding: 2px 5px; border-radius: 3px; }
                .btn { display: inline-block; padding: 10px 20px; margin: 10px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
                .btn:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div class="container">
                {% if data.ok %}
                <div class="success">✅ Вебхук успешно установлен!</div>
                {% else %}
                <div class="error">❌ Ошибка при установке вебхука</div>
                {% endif %}
                
                <div class="info">
                    <strong>URL вебхука:</strong><br>
                    <code>{{ webhook_url }}</code><br><br>
                    <strong>Ответ Telegram API:</strong><br>
                    <code>{{ data|tojson }}</code>
                </div>
                
                <a href="/webhook_info" class="btn">🔍 Проверить статус вебхука</a>
                <a href="/" class="btn">🏠 На главную</a>
            </div>
        </body>
        </html>
        ''', data=data, webhook_url=webhook_url), 200
    except Exception as e:
        add_web_log(f"Ошибка установки вебхука: {str(e)}", "ERROR")
        return f"Ошибка: {str(e)}", 500

@flask_app.route('/delete_webhook')
def delete_webhook():
    """Удаление вебхука"""
    try:
        import requests
        api_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        response = requests.get(api_url, timeout=10)
        data = response.json() if response.status_code == 200 else {}
        
        add_web_log("Вебхук удален", "WARNING")
        
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head><title>Удаление вебхука</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
            <h1>{{ "✅ Вебхук удален" if data.ok else "❌ Ошибка удаления" }}</h1>
            <pre>{{ data|tojson(indent=2) }}</pre>
            <a href="/">На главную</a>
        </body>
        </html>
        ''', data=data), 200
    except Exception as e:
        return f"Ошибка: {str(e)}", 500

@flask_app.route('/logs')
def show_logs():
    """Страница с полными логами"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Логи бота</title>
        <style>
            body { font-family: 'Courier New', monospace; margin: 0; padding: 20px; background: #1a1a1a; color: #f0f0f0; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            h1 { color: #4cd964; margin: 0; }
            .controls { display: flex; gap: 10px; }
            .btn { padding: 8px 16px; background: #4cd964; color: #1a1a1a; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
            .btn:hover { background: #5ad874; }
            .btn-clear { background: #ff3b30; }
            .btn-clear:hover { background: #ff4d40; }
            .log-entry { padding: 8px; border-bottom: 1px solid #333; display: flex; align-items: baseline; }
            .timestamp { color: #5ac8fa; min-width: 100px; }
            .level { font-weight: bold; min-width: 80px; }
            .level.INFO { color: #5ac8fa; }
            .level.WARNING { color: #ffcc00; }
            .level.ERROR { color: #ff3b30; }
            .level.DEBUG { color: #4cd964; }
            .message { flex: 1; }
            .filter { margin-bottom: 20px; display: flex; gap: 10px; }
            .filter select, .filter input { padding: 8px; background: #2a2a2a; color: white; border: 1px solid #444; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Логи бота Монополия</h1>
                <div class="controls">
                    <button class="btn" onclick="location.reload()">🔄 Обновить</button>
                    <button class="btn btn-clear" onclick="clearLogs()">🗑️ Очистить логи</button>
                    <button class="btn" onclick="location.href='/'">🏠 На главную</button>
                </div>
            </div>
            
            <div class="filter">
                <select id="levelFilter">
                    <option value="ALL">Все уровни</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                    <option value="DEBUG">DEBUG</option>
                </select>
                <input type="text" id="searchFilter" placeholder="Поиск по сообщению...">
                <button class="btn" onclick="filterLogs()">🔍 Фильтровать</button>
            </div>
            
            <div id="logsContainer">
                {% for log in logs %}
                <div class="log-entry" data-level="{{ log.level }}">
                    <span class="timestamp">[{{ log.timestamp }}]</span>
                    <span class="level {{ log.level }}">{{ log.level }}</span>
                    <span class="message">{{ log.message }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <script>
            function filterLogs() {
                const level = document.getElementById('levelFilter').value;
                const search = document.getElementById('searchFilter').value.toLowerCase();
                const entries = document.querySelectorAll('.log-entry');
                
                entries.forEach(entry => {
                    const entryLevel = entry.getAttribute('data-level');
                    const entryMessage = entry.querySelector('.message').textContent.toLowerCase();
                    
                    const levelMatch = level === 'ALL' || entryLevel === level;
                    const searchMatch = !search || entryMessage.includes(search);
                    
                    entry.style.display = levelMatch && searchMatch ? 'flex' : 'none';
                });
            }
            
            function clearLogs() {
                if (confirm('Очистить все логи?')) {
                    fetch('/clear_logs')
                        .then(() => location.reload())
                        .catch(error => console.error('Ошибка:', error));
                }
            }
            
            // Автообновление каждые 3 секунды
            setInterval(() => {
                fetch('/get_logs')
                    .then(response => response.json())
                    .then(logs => {
                        const container = document.getElementById('logsContainer');
                        container.innerHTML = logs.map(log => 
                            `<div class="log-entry" data-level="${log.level}">
                                <span class="timestamp">[${log.timestamp}]</span>
                                <span class="level ${log.level}">${log.level}</span>
                                <span class="message">${log.message}</span>
                            </div>`
                        ).join('');
                    });
            }, 3000);
            
            // Применяем фильтры при загрузке
            document.addEventListener('DOMContentLoaded', filterLogs);
        </script>
    </body>
    </html>
    ''', logs=web_logs), 200

@flask_app.route('/get_logs')
def get_logs():
    """API для получения логов (JSON)"""
    return json.dumps(web_logs[-50:]), 200, {'Content-Type': 'application/json'}

@flask_app.route('/clear_logs')
def clear_logs():
    """Очистка логов"""
    web_logs.clear()
    add_web_log("Логи очищены", "INFO")
    return "Логи очищены", 200

@flask_app.route(WEBHOOK_PATH, methods=['POST'])
def telegram_webhook():
    """Обработчик вебхука Telegram с обработкой через application"""
    try:
        # 1. Получаем данные от Telegram
        data = request.get_json(force=True, silent=True)
        
        if not data:
            add_web_log("📩 Получен пустой вебхук", "INFO")
            return "ok", 200
        
        update_id = data.get('update_id', 'unknown')
        add_web_log(f"📩 Вебхук получен: ID {update_id}", "INFO")
        
        # 2. Логируем информацию о сообщении (для отладки)
        if 'message' in data:
            message = data['message']
            text = message.get('text', '')[:50]  # Первые 50 символов
            user = message.get('from', {})
            username = user.get('username', user.get('first_name', 'Unknown'))
            chat_id = message.get('chat', {}).get('id', 'unknown')
            chat_type = message.get('chat', {}).get('type', 'unknown')
            
            add_web_log(f"  👤 @{username} (чат {chat_type}): {text}", "INFO")
            
            # Логируем команды
            if text and text.startswith('/'):
                add_web_log(f"  🎯 Команда: {text.split()[0]}", "INFO")
        
        elif 'callback_query' in data:
            callback = data['callback_query']
            query_data = callback.get('data', '')[:30]
            user = callback.get('from', {})
            username = user.get('username', user.get('first_name', 'Unknown'))
            add_web_log(f"  🔘 Callback от @{username}: {query_data}", "INFO")
        
        # 3. Проверяем инициализацию бота
        global application
        
        if application is None:
            add_web_log("⚠️ Бот не инициализирован, пропускаем обработку", "WARNING")
            return "ok", 200
        
        if application.bot is None:
            add_web_log("⚠️ application.bot is None, пропускаем обработку", "WARNING")
            return "ok", 200
        
        # 4. Обрабатываем обновление через application
        try:
            from telegram import Update
            update = Update.de_json(data, application.bot)
            
            # Создаем event loop для асинхронной обработки
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Обрабатываем обновление
            loop.run_until_complete(application.process_update(update))
            
            add_web_log(f"✅ Обновление {update_id} обработано", "INFO")
            
        except Exception as process_error:
            add_web_log(f"⚠️ Ошибка обработки обновления: {str(process_error)[:100]}", "WARNING")
            # Продолжаем - главное вернуть OK Telegram
        
    except Exception as e:
        error_msg = f"❌ Ошибка в вебхуке: {str(e)[:100]}"
        add_web_log(error_msg, "ERROR")
        print(f"Webhook error: {e}")
        # Не выводим traceback в продакшене чтобы не засорять логи
    
    # 5. ВСЕГДА возвращаем OK, чтобы Telegram не отключал вебхук
    return "ok", 200
        
def init_bot_sync():
    """Минимальная инициализация бота"""
    global application
    
    if application is not None:
        add_web_log("✅ Бот уже инициализирован", "INFO")
        return True
    
    if not TOKEN:
        add_web_log("❌ BOT_TOKEN не установлен!", "ERROR")
        return False
    
    try:
        add_web_log("🤖 ЗАПУСК ИНИЦИАЛИЗАЦИИ БОТА", "INFO")
        
        # 1. Создаем application
        application = Application.builder().token(TOKEN).build()
        add_web_log("✅ Application создан", "INFO")
        
        # 2. Только САМЫЕ ВАЖНЫЕ обработчики
        application.add_handler(CommandHandler("start", private_start))
        application.add_handler(CommandHandler("help", help_command))
        
        add_web_log("✅ Обработчики добавлены", "INFO")
        
        # 3. Инициализируем
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(application.initialize())
        add_web_log("✅ Бот инициализирован", "INFO")
        
        loop.run_until_complete(application.start())
        add_web_log("✅ Бот запущен", "INFO")
        
        return True
        
    except Exception as e:
        add_web_log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False
        
# ========== ОСНОВНОЙ КОД БОТА ==========
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError

# Глобальная переменная для бота
application = None

# ===================== КОНФИГУРАЦИЯ =====================
START_MONEY = 1500
MAX_PLAYERS = 6
BOARD_SIZE = 24

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

# Игровое поле
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
    {"name": f"{EMOJI['chance']} ШАНС", "type": "chance", "price": 0, "color": "none"},  # ← Убрал лишнюю [
    {"name": f"{EMOJI['property']} Малая Бронная", "type": "property", "price": 320, "color": "green", "rent": [28, 150, 450, 1000, 1200, 1400]},
    {"name": f"{EMOJI['tax']} Суперналог", "type": "tax", "price": 100, "color": "none"},
    {"name": f"{EMOJI['property']} Тверской бульвар", "type": "property", "price": 400, "color": "darkblue", "rent": [50, 200, 600, 1400, 1700, 2000]},
]  # ← Эта скобка теперь правильно закрывает BOARD
# Хранилище игр {chat_id: game_data}
games_storage = {}

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def init_bot():
    """Инициализация бота"""
    global application
    if application is not None:
        return application
    
    if not TOKEN:
        add_web_log("❌ BOT_TOKEN не найден!", "ERROR")
        return None
    
    try:
        add_web_log("Инициализация бота...", "INFO")
        application = Application.builder().token(TOKEN).build()
        
        # Регистрация обработчиков
        register_handlers(application)
        
        # Инициализация
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(application.start())
        
        add_web_log("✅ Бот успешно инициализирован", "INFO")
        
        # Автоматическая установка вебхука
        setup_webhook()
        
        return application
        
    except Exception as e:
        error_msg = f"❌ Ошибка инициализации бота: {str(e)}"
        add_web_log(error_msg, "ERROR")
        logger.error(error_msg, exc_info=True)
        return None

def setup_webhook():
    """Автоматическая установка вебхука"""
    try:
        if application and application.bot:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(application.bot.set_webhook(url=WEBHOOK_URL))
            
            if success:
                add_web_log(f"✅ Вебхук установлен: {WEBHOOK_URL}", "INFO")
            else:
                add_web_log("❌ Не удалось установить вебхук", "ERROR")
    except Exception as e:
        add_web_log(f"Ошибка установки вебхука: {str(e)}", "ERROR")

def register_handlers(app):
    """Регистрация всех обработчиков"""
    try:
        # Команды
        app.add_handler(CommandHandler("start", private_start))
        app.add_handler(CommandHandler("monopoly", group_monopoly))
        app.add_handler(CommandHandler("help", help_command))
        
        # Кнопки (Callback queries)
        app.add_handler(CallbackQueryHandler(join_game, pattern="^join_"))
        app.add_handler(CallbackQueryHandler(start_game, pattern="^start_"))
        app.add_handler(CallbackQueryHandler(roll_dice, pattern="^roll_"))
        app.add_handler(CallbackQueryHandler(buy_property, pattern="^buy_"))
        app.add_handler(CallbackQueryHandler(skip_turn, pattern="^skip_"))
        app.add_handler(CallbackQueryHandler(end_turn, pattern="^end_"))
        app.add_handler(CallbackQueryHandler(check_balance, pattern="^balance_"))
        app.add_handler(CallbackQueryHandler(check_properties, pattern="^props_"))
        app.add_handler(CallbackQueryHandler(build_menu, pattern="^build_"))
        app.add_handler(CallbackQueryHandler(build_house, pattern="^build_house_"))
        app.add_handler(CallbackQueryHandler(build_hotel, pattern="^build_hotel_"))
        app.add_handler(CallbackQueryHandler(how_to_play, pattern="how_to_play"))
        app.add_handler(CallbackQueryHandler(cancel_game, pattern="^cancel_"))
        app.add_handler(CallbackQueryHandler(trade_menu, pattern="^trade_menu_"))
        app.add_handler(CallbackQueryHandler(auction_property, pattern="^auction_"))
        app.add_handler(CallbackQueryHandler(auction_bid, pattern="^auction_bid_"))
        app.add_handler(CallbackQueryHandler(auction_end, pattern="^auction_end_"))
        
        # Обработчик ошибок
        app.add_error_handler(error_handler)
        
        add_web_log(f"Зарегистрировано обработчиков: {len(app.handlers[0])}", "INFO")
        
    except Exception as e:
        add_web_log(f"Ошибка регистрации обработчиков: {str(e)}", "ERROR")
        raise

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
# ===================== ОСНОВНЫЕ ФУНКЦИИ =====================
async def private_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start в личных сообщениях"""
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        add_web_log(f"Команда /start от пользователя @{user.username or user.first_name} (ID: {user.id})", "INFO")
        
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
        
    except Exception as e:
        error_msg = f"Ошибка в private_start: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def group_monopoly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /monopoly в группе"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        add_web_log(f"Команда /monopoly в группе {chat.id} от @{user.username or user.first_name}", "INFO")
        
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
        
    except Exception as e:
        error_msg = f"Ошибка в group_monopoly: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await update.message.reply_text("❌ Произошла ошибка при создании игры. Попробуйте еще раз.")

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Присоединение к игре"""
    try:
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat.id
        user = query.from_user
        
        add_web_log(f"Попытка присоединения @{user.username or user.first_name} к игре в чате {chat_id}", "INFO")
        
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
        
        add_web_log(f"Игрок @{user.username or user.first_name} присоединился к игре в чате {chat_id}", "INFO")
        
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
        
    except Exception as e:
        error_msg = f"Ошибка в join_game: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await query.edit_message_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало игры"""
    try:
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat.id
        
        add_web_log(f"Попытка начала игры в чате {chat_id}", "INFO")
        
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
        
        add_web_log(f"Игра начата в чате {chat_id}. Игроков: {len(game['players'])}", "INFO")
        
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
        
    except Exception as e:
        error_msg = f"Ошибка в start_game: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await query.edit_message_text("❌ Произошла ошибка при начале игры.")
async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Бросок кубиков"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        player_id = int(data.split('_')[1])
        chat_id = query.message.chat.id
        
        add_web_log(f"Игрок {player_id} бросает кубики в чате {chat_id}", "INFO")
        
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
                add_web_log(f"Игрок {player_id} вышел из тюрьмы (дубль)", "INFO")
            else:
                player['jail_turns'] += 1
                if player['jail_turns'] >= 3:
                    # Платим штраф
                    player['balance'] -= 50
                    player['in_jail'] = False
                    jail_msg = f"💸 Выплатили штраф $50 и вышли из тюрьмы"
                    await query.message.reply_text(jail_msg)
                    add_web_log(f"Игрок {player_id} выплатил штраф и вышел из тюрьмы", "INFO")
                else:
                    await query.answer(f"❌ Осталось в тюрьме (ход {player['jail_turns']}/3)")
                    add_web_log(f"Игрок {player_id} остался в тюрьме (ход {player['jail_turns']}/3)", "INFO")
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
                add_web_log(f"Игрок {player_id} попал в тюрьму (3 дубля подряд)", "INFO")
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
                
                add_web_log(f"Игрок {player_id} заплатил ${rent} аренды игроку {owner}", "INFO")
                
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
            
            add_web_log(f"Игрок {player_id} уплатил налог ${cell['price']}", "INFO")
            
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
                add_web_log(f"Игрок {player_id} получил карточку шанса: {chance_result['text']}", "INFO")
            
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
            
            add_web_log(f"Игрок {player_id} прошел старт и получил $200", "INFO")
            
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
        
    except Exception as e:
        error_msg = f"Ошибка в roll_dice: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await query.edit_message_text("❌ Произошла ошибка при броске кубиков.")

async def buy_property(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Покупка собственности"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data.split('_')
        property_idx = int(data[1])
        player_id = int(data[2])
        chat_id = query.message.chat.id
        
        add_web_log(f"Игрок {player_id} покупает собственность {property_idx} в чате {chat_id}", "INFO")
        
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
        
        add_web_log(f"Игрок {player_id} купил {cell['name']} за ${cell['price']}", "INFO")
        
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
        
    except Exception as e:
        error_msg = f"Ошибка в buy_property: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await query.edit_message_text("❌ Произошла ошибка при покупке.")

async def skip_turn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск хода/отказ от покупки"""
    try:
        query = update.callback_query
        await query.answer()
        
        player_id = int(query.data.split('_')[1])
        chat_id = query.message.chat.id
        
        add_web_log(f"Игрок {player_id} пропускает ход в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            await query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        
        if game['current_player'] != player_id:
            await query.answer("❌ Сейчас не ваш ход!")
            return
        
        await query.edit_message_text("⏭️ Ход пропущен")
        await next_turn(game, chat_id, context)
        
    except Exception as e:
        error_msg = f"Ошибка в skip_turn: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await query.edit_message_text("❌ Произошла ошибка.")
async def end_turn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение хода"""
    try:
        query = update.callback_query
        await query.answer()
        
        player_id = int(query.data.split('_')[1])
        chat_id = query.message.chat.id
        
        add_web_log(f"Игрок {player_id} завершает ход в чате {chat_id}", "INFO")
        
        if chat_id not in games_storage:
            await query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = games_storage[chat_id]
        if game['current_player'] == player_id:
            await next_turn(game, chat_id, context)
            
    except Exception as e:
        error_msg = f"Ошибка в end_turn: {str(e)}"
        add_web_log(error_msg, "ERROR")

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка баланса"""
    try:
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
            
    except Exception as e:
        add_web_log(f"Ошибка в check_balance: {str(e)}", "ERROR")

async def check_properties(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка имущества"""
    try:
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
            
    except Exception as e:
        add_web_log(f"Ошибка в check_properties: {str(e)}", "ERROR")

async def trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню торговли"""
    try:
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
        
    except Exception as e:
        error_msg = f"Ошибка в trade_menu: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await query.answer("❌ Ошибка при открытии меню торговли.")

async def build_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню строительства"""
    try:
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
        
        await query.edit_message_text(
            f"🏗️ *СТРОИТЕЛЬСТВО*\n\nВыберите улицу для строительства:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        error_msg = f"Ошибка в build_menu: {str(e)}"
        add_web_log(error_msg, "ERROR")

async def build_house(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Строительство дома"""
    try:
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
        
        # Строим дом
        player['balance'] -= house_price
        game['board_state'][property_idx]['houses'] += 1
        
        add_web_log(f"Игрок {player_id} построил дом на {cell['name']}", "INFO")
        
        await query.edit_message_text(
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
        await query.answer("❌ Ошибка при строительстве дома.")
async def build_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Строительство отеля"""
    try:
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
        
        add_web_log(f"Игрок {player_id} построил отель на {cell['name']}", "INFO")
        
        await query.edit_message_text(
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
        await query.answer("❌ Ошибка при строительстве отеля.")

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена игры"""
    try:
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat.id
        
        add_web_log(f"Игра отменена в чате {chat_id}", "INFO")
        
        if chat_id in games_storage:
            del games_storage[chat_id]
        
        await query.edit_message_text("❌ Игра отменена")
        
    except Exception as e:
        error_msg = f"Ошибка в cancel_game: {str(e)}"
        add_web_log(error_msg, "ERROR")

async def how_to_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инструкция по игре"""
    try:
        query = update.callback_query
        await query.answer()
        
        add_web_log("Показана инструкция по игре", "INFO")
        
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

async def auction_property(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало аукциона"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data.split('_')
        property_idx = int(data[1])
        player_id = int(data[2])
        chat_id = query.message.chat.id
        
        add_web_log(f"Начало аукциона за собственность {property_idx} в чате {chat_id}", "INFO")
        
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
            'current_bid': cell['price'] // 2,
            'current_bidder': None,
            'bidders': list(game['players'].keys()),
            'min_increment': 10
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
        
    except Exception as e:
        error_msg = f"Ошибка в auction_property: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await query.edit_message_text("❌ Ошибка при начале аукциона.")

async def auction_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ставка на аукционе"""
    try:
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
        
        add_web_log(f"Игрок {player_id} сделал ставку ${bid_amount} на аукционе", "INFO")
        
        await query.edit_message_text(
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
        await query.answer("❌ Ошибка при ставке.")
async def auction_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение аукциона"""
    try:
        query = update.callback_query
        await query.answer()
        
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
        
    except Exception as e:
        error_msg = f"Ошибка в auction_end: {str(e)}"
        add_web_log(error_msg, "ERROR")
        await query.edit_message_text("❌ Ошибка при завершении аукциона.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    try:
        add_web_log("Команда /help выполнена", "INFO")
        
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
        
    except Exception as e:
        error_msg = f"Ошибка в help_command: {str(e)}"
        add_web_log(error_msg, "ERROR")

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
                house_emoji = "🏨" if houses >= 5 else "🏡" * min(houses, 4)
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
        
        add_web_log(f"Игрок {player_id} собрал монополию {color_name}", "INFO")
    
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
async def next_turn(game, chat_id, context):
    """Переход к следующему игроку"""
    try:
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
        
        add_web_log(f"Переход хода к игроку {next_player['id']} в чате {chat_id}", "INFO")
        
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
        
    except Exception as e:
        error_msg = f"Ошибка в next_turn: {str(e)}"
        add_web_log(error_msg, "ERROR")

async def handle_bankruptcy(game, player_id, chat_id, context):
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
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💀 *БАНКРОТСТВО!*\n\n"
                 f"{player['color']} @{player['username']} обанкротился!\n"
                 f"Его собственность возвращается банку.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = f"Ошибка в handle_bankruptcy: {str(e)}"
        add_web_log(error_msg, "ERROR")

async def end_game(game, chat_id, context):
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
            add_web_log(f"Игра удалена из хранилища (чат {chat_id})", "INFO")
            
    except Exception as e:
        error_msg = f"Ошибка в end_game: {str(e)}"
        add_web_log(error_msg, "ERROR")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Произошла ошибка. Попробуйте еще раз или перезапустите игру командой /monopoly"
                )
            except:
                pass
                
    except Exception as e:
        add_web_log(f"Ошибка в обработчике ошибок: {str(e)}", "ERROR")

# ===================== ОСНОВНАЯ ФУНКЦИЯ =====================
def main():
    """Запуск для локальной разработки"""
    print("⚠️  Режим локальной разработки")
    print("ℹ️  На Render используется gunicorn bot:flask_app")
    
    # ТОЛЬКО запуск Flask
    flask_app.run(
        host='0.0.0.0',
        port=PORT,
        debug=False
    )
