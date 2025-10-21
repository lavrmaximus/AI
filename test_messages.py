#!/usr/bin/env python3
"""
Тест для проверки логирования сообщений в БД
"""

import os
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Загружаем переменные окружения
load_dotenv()

def build_dsn_from_env():
    """Строим DSN из переменных окружения"""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    
    # Или из отдельных переменных
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE", "postgres")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

async def test_messages():
    """Проверка сообщений в БД"""
    print("🔍 Проверяю сообщения в БД...")
    
    try:
        # Подключение к PostgreSQL
        dsn = build_dsn_from_env()
        conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Подключение к PostgreSQL установлено")
        
        # 1. Проверяем структуру таблицы messages
        print("\n📋 Структура таблицы messages:")
        cursor.execute('''
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'messages' 
            ORDER BY ordinal_position
        ''')
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # 2. Общая статистика
        cursor.execute("SELECT COUNT(*) as total FROM messages")
        total_messages = cursor.fetchone()['total']
        print(f"\n📊 Всего сообщений в БД: {total_messages}")
        
        # 3. Последние 10 сообщений
        print("\n📝 Последние 10 сообщений:")
        cursor.execute('''
            SELECT user_id, user_message, bot_response, message_type, created_at
            FROM messages 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        messages = cursor.fetchall()
        
        if messages:
            for i, msg in enumerate(messages, 1):
                print(f"\n{i}. Пользователь: {msg['user_id']}")
                print(f"   Время: {msg['created_at']}")
                print(f"   Тип: {msg['message_type']}")
                print(f"   Сообщение: {msg['user_message'][:100]}{'...' if len(msg['user_message']) > 100 else ''}")
                if msg['bot_response']:
                    print(f"   Ответ: {msg['bot_response'][:100]}{'...' if len(msg['bot_response']) > 100 else ''}")
        else:
            print("❌ Сообщения не найдены!")
        
        # 4. Статистика по типам сообщений
        print("\n📈 Статистика по типам сообщений:")
        cursor.execute('''
            SELECT message_type, COUNT(*) as count 
            FROM messages 
            GROUP BY message_type 
            ORDER BY count DESC
        ''')
        stats = cursor.fetchall()
        for stat in stats:
            print(f"  - {stat['message_type']}: {stat['count']} сообщений")
        
        # 5. Статистика по пользователям
        print("\n👥 Статистика по пользователям:")
        cursor.execute('''
            SELECT user_id, COUNT(*) as count 
            FROM messages 
            GROUP BY user_id 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        users = cursor.fetchall()
        for user in users:
            print(f"  - {user['user_id']}: {user['count']} сообщений")
        
        # 6. Проверяем последние сообщения за последний час
        print("\n⏰ Сообщения за последний час:")
        cursor.execute('''
            SELECT user_id, user_message, message_type, created_at
            FROM messages 
            WHERE created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
        ''')
        recent_messages = cursor.fetchall()
        
        if recent_messages:
            for msg in recent_messages:
                print(f"  - {msg['created_at']} | {msg['user_id']} | {msg['message_type']} | {msg['user_message'][:50]}...")
        else:
            print("  ❌ Сообщений за последний час не найдено")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Проверка завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Тест логирования сообщений")
    print("=" * 40)
    
    success = asyncio.run(test_messages())
    
    if success:
        print("\n✅ Тест выполнен успешно!")
    else:
        print("\n❌ Тест завершился с ошибками!")
