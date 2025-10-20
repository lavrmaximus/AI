"""
Утилиты для определения окружения и настройки путей
"""
import os
import platform
from pathlib import Path

def is_production():
    """Определяет, работаем ли мы в продакшене (Railway, Heroku, etc.)"""
    # Проверяем переменные окружения, характерные для хостингов
    production_indicators = [
        'RAILWAY_ENVIRONMENT',
        'DYNO',  # Heroku
        'PORT',  # Обычно есть на хостингах
        'DATABASE_URL',  # PostgreSQL URL
        'PGHOST',  # PostgreSQL хост
    ]
    
    # Если есть хотя бы одна переменная, характерная для продакшена
    if any(os.getenv(var) for var in production_indicators):
        return True
    
    # Проверяем, что мы не в Windows (обычно локальная разработка)
    if platform.system() == "Windows":
        return False
    
    # Проверяем наличие .env файла (обычно только локально)
    if os.path.exists('.env'):
        return False
    
    # Если есть переменная окружения, явно указывающая на продакшен
    return os.getenv('ENVIRONMENT', '').lower() in ['production', 'prod']

def get_data_dir():
    """Возвращает путь к директории с данными в зависимости от окружения"""
    if is_production():
        # В продакшене используем временную директорию
        return '/tmp'
    else:
        # Локально используем текущую директорию
        return '.'

def get_log_dir():
    """Возвращает путь к директории с логами в зависимости от окружения"""
    if is_production():
        # В продакшене логи идут в stdout/stderr
        return None
    else:
        # Локально создаем папку logs
        return 'logs'

def should_create_files():
    """Определяет, нужно ли создавать локальные файлы"""
    return not is_production()

def get_database_config():
    """Возвращает конфигурацию базы данных в зависимости от окружения"""
    if is_production():
        # В продакшене используем PostgreSQL
        return {
            'type': 'postgresql',
            'url': os.getenv('DATABASE_URL'),
            'host': os.getenv('PGHOST'),
            'port': os.getenv('PGPORT', '5432'),
            'database': os.getenv('PGDATABASE'),
            'user': os.getenv('PGUSER'),
            'password': os.getenv('PGPASSWORD'),
        }
    else:
        # Локально используем SQLite
        return {
            'type': 'sqlite',
            'path': os.path.join(get_data_dir(), 'business_bot_v2.db')
        }

def setup_environment():
    """Настраивает окружение в зависимости от типа развертывания"""
    if is_production():
        print("🚀 Запуск в продакшене (Railway/Heroku)")
        print("📊 Используется PostgreSQL")
        print("📝 Логи выводятся в stdout")
    else:
        print("💻 Запуск в локальном окружении")
        print("📊 Используется SQLite")
        print("📝 Логи сохраняются в файлы")
        
        # Создаем необходимые директории локально
        data_dir = get_data_dir()
        log_dir = get_log_dir()
        
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"📁 Создана директория логов: {log_dir}")

if __name__ == "__main__":
    print("🔍 Проверка окружения:")
    print(f"Продакшен: {is_production()}")
    print(f"Директория данных: {get_data_dir()}")
    print(f"Директория логов: {get_log_dir()}")
    print(f"Создавать файлы: {should_create_files()}")
    print(f"Конфигурация БД: {get_database_config()}")
    setup_environment()
