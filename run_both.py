import os
import sys
from threading import Thread
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_flask():
    """Запуск Flask части"""
    from main_and_web import run_flask_server
    run_flask_server()

def run_bot():
    """Запуск Telegram бота"""
    from telegram_bot import run_bot
    run_bot()

def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск Monopoly Premium Bot...")
    
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask сервер запущен")
    
    # Запускаем бота в основном потоке
    run_bot()

if __name__ == "__main__":
    main()
