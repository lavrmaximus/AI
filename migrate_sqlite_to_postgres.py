#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Перенос данных из локальной SQLite (business_bot_v2.db) в PostgreSQL (DATABASE_URL).

Использование:
  1) pip install psycopg2-binary python-dotenv
  2) В .env задайте:
       DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
       PGSSLMODE=require   (для Railway, при необходимости)
  3) Запустите: python migrate_sqlite_to_postgres.py

Скрипт создаст таблицы в Postgres (если их нет) и скопирует в них данные из SQLite.
"""

import os
import sys
import sqlite3
from typing import List, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    import psycopg2
    from psycopg2.extras import execute_values
except Exception as e:
    print("❌ Требуется пакет: pip install psycopg2-binary")
    sys.exit(1)


SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'business_bot_v2.db')


def get_pg_conn():
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        raise RuntimeError('DATABASE_URL не задан')
    # PGSSLMODE читается драйвером из env при необходимости
    return psycopg2.connect(dsn)


def create_pg_schema(cur):
    # Схема подобрана к текущему проекту; типы приведены к Postgres-аналогам
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS businesses (
        business_id SERIAL PRIMARY KEY,
        user_id TEXT REFERENCES users(user_id),
        business_name TEXT,
        business_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS business_snapshots (
        snapshot_id SERIAL PRIMARY KEY,
        business_id INTEGER REFERENCES businesses(business_id),
        period_type TEXT,
        period_date DATE,
        revenue DOUBLE PRECISION DEFAULT 0,
        expenses DOUBLE PRECISION DEFAULT 0,
        profit DOUBLE PRECISION DEFAULT 0,
        clients INTEGER DEFAULT 0,
        average_check DOUBLE PRECISION DEFAULT 0,
        investments DOUBLE PRECISION DEFAULT 0,
        marketing_costs DOUBLE PRECISION DEFAULT 0,
        employees INTEGER DEFAULT 0,
        new_clients_per_month INTEGER DEFAULT 0,
        customer_retention_rate DOUBLE PRECISION DEFAULT 0,
        profit_margin DOUBLE PRECISION DEFAULT 0,
        break_even_clients DOUBLE PRECISION DEFAULT 0,
        safety_margin DOUBLE PRECISION DEFAULT 0,
        roi DOUBLE PRECISION DEFAULT 0,
        profitability_index DOUBLE PRECISION DEFAULT 0,
        ltv DOUBLE PRECISION DEFAULT 0,
        cac DOUBLE PRECISION DEFAULT 0,
        ltv_cac_ratio DOUBLE PRECISION DEFAULT 0,
        customer_profit_margin DOUBLE PRECISION DEFAULT 0,
        sgr DOUBLE PRECISION DEFAULT 0,
        revenue_growth_rate DOUBLE PRECISION DEFAULT 0,
        asset_turnover DOUBLE PRECISION DEFAULT 0,
        roe DOUBLE PRECISION DEFAULT 0,
        months_to_bankruptcy DOUBLE PRECISION DEFAULT 0,
        financial_health_score INTEGER DEFAULT 0,
        growth_health_score INTEGER DEFAULT 0,
        efficiency_health_score INTEGER DEFAULT 0,
        overall_health_score INTEGER DEFAULT 0,
        advice1 TEXT DEFAULT '',
        advice2 TEXT DEFAULT '',
        advice3 TEXT DEFAULT '',
        advice4 TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversation_sessions (
        session_id SERIAL PRIMARY KEY,
        user_id TEXT REFERENCES users(user_id),
        business_id INTEGER REFERENCES businesses(business_id),
        current_state TEXT,
        collected_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        session_id INTEGER REFERENCES conversation_sessions(session_id),
        user_message TEXT,
        bot_response TEXT,
        message_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


def fetch_all(sqlite_cur, query: str) -> List[Tuple]:
    sqlite_cur.execute(query)
    return sqlite_cur.fetchall()


def migrate_table(sqlite_cur, pg_cur, table: str, columns: List[str], row_transform=None):
    placeholders = ','.join([f'"{c}"' for c in columns])
    rows = fetch_all(sqlite_cur, f'SELECT {placeholders} FROM {table}')
    if not rows:
        print(f"- {table}: нет данных, пропущено")
        return
    if row_transform:
        rows = [row_transform(list(r)) for r in rows]
    # Вставляем пакетно
    target_cols = ','.join([f'"{c}"' for c in columns])
    sql = f'INSERT INTO {table} ({target_cols}) VALUES %s'
    execute_values(pg_cur, sql, rows, page_size=1000)
    print(f"+ {table}: перенесено {len(rows)} строк")


def main():
    # Подключаемся к SQLite
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ Не найден файл SQLite: {SQLITE_PATH}")
        sys.exit(2)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    # Подключаемся к Postgres
    with get_pg_conn() as pg_conn:
        with pg_conn.cursor() as pg_cur:
            print("🔧 Создаю схему в Postgres (если отсутствует)...")
            create_pg_schema(pg_cur)
            pg_conn.commit()

            # Гарантируем существование пользователей до зависимых таблиц
            # Сначала очищаем таблицы в правильном порядке (от зависимых к родительским)
            print("🧹 Очищаю таблицы в Postgres (если есть данные)...")
            tables_to_clear = ['messages', 'conversation_sessions', 'business_snapshots', 'businesses', 'users']
            for table in tables_to_clear:
                try:
                    pg_cur.execute(f'TRUNCATE TABLE {table} RESTART IDENTITY CASCADE')
                    print(f"  ✅ Таблица {table} очищена")
                except Exception as e:
                    print(f"  ⚠️  Ошибка очистки таблицы {table}: {e}")
                    # Попробуем удалить данные по-другому
                    try:
                        pg_cur.execute(f'DELETE FROM {table}')
                        print(f"  ✅ Данные из {table} удалены через DELETE")
                    except Exception as e2:
                        print(f"  ❌ Не удалось очистить {table}: {e2}")
            pg_conn.commit()

            print("➡️  Переношу данные...")

            # users
            migrate_table(sqlite_cur, pg_cur, 'users', [
                'user_id', 'username', 'first_name', 'last_name'
            ])

            # businesses (важно: PK может отличаться по значениям из-за SERIAL; переносим значения business_id как есть)
            def businesses_transform(row):
                # row: [business_id, user_id, business_name, business_type, created_at, is_active]
                # Преобразуем is_active из 0/1 в boolean
                if len(row) >= 6:
                    row[5] = bool(row[5])
                return tuple(row)

            # Сначала проверим, какие user_id есть в businesses, но нет в users
            sqlite_cur.execute("""
                SELECT DISTINCT b.user_id 
                FROM businesses b 
                LEFT JOIN users u ON b.user_id = u.user_id 
                WHERE u.user_id IS NULL
            """)
            missing_users = sqlite_cur.fetchall()
            
            if missing_users:
                print(f"⚠️  Найдены businesses с отсутствующими пользователями: {[u[0] for u in missing_users]}")
                print("   Добавляю недостающих пользователей...")
                
                for user_id, in missing_users:
                    pg_cur.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name) 
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, None, 'Unknown', 'User'))
                pg_conn.commit()

            migrate_table(sqlite_cur, pg_cur, 'businesses', [
                'business_id', 'user_id', 'business_name', 'business_type', 'created_at', 'is_active'
            ], row_transform=businesses_transform)

            # business_snapshots
            migrate_table(sqlite_cur, pg_cur, 'business_snapshots', [
                'snapshot_id','business_id','period_type','period_date',
                'revenue','expenses','profit','clients','average_check','investments','marketing_costs','employees',
                'new_clients_per_month','customer_retention_rate',
                'profit_margin','break_even_clients','safety_margin','roi','profitability_index',
                'ltv','cac','ltv_cac_ratio','customer_profit_margin','sgr','revenue_growth_rate',
                'asset_turnover','roe','months_to_bankruptcy',
                'financial_health_score','growth_health_score','efficiency_health_score','overall_health_score',
                'advice1','advice2','advice3','advice4','created_at'
            ])

            # conversation_sessions
            migrate_table(sqlite_cur, pg_cur, 'conversation_sessions', [
                'session_id','user_id','business_id','current_state','collected_data','created_at','updated_at'
            ])

            # messages
            migrate_table(sqlite_cur, pg_cur, 'messages', [
                'id','session_id','user_message','bot_response','message_type','created_at'
            ])

            # Обновляем последовательности (sequences) для SERIAL полей
            print("🔄 Обновляю последовательности...")
            sequences_to_update = [
                ('businesses_business_id_seq', 'businesses', 'business_id'),
                ('business_snapshots_snapshot_id_seq', 'business_snapshots', 'snapshot_id'),
                ('conversation_sessions_session_id_seq', 'conversation_sessions', 'session_id'),
                ('messages_id_seq', 'messages', 'id')
            ]
            
            for seq_name, table_name, column_name in sequences_to_update:
                try:
                    pg_cur.execute(f"SELECT MAX({column_name}) FROM {table_name}")
                    max_val = pg_cur.fetchone()[0]
                    
                    if max_val is not None and max_val > 0:
                        # Устанавливаем последовательность на максимальное значение
                        pg_cur.execute(f"SELECT setval('{seq_name}', {max_val})")
                        result = pg_cur.fetchone()[0]
                        print(f"  ✅ {seq_name} установлен в {result}")
                    elif max_val == 0:
                        # Если максимальное значение 0, устанавливаем в 1
                        pg_cur.execute(f"SELECT setval('{seq_name}', 1)")
                        result = pg_cur.fetchone()[0]
                        print(f"  ✅ {seq_name} установлен в {result} (было 0)")
                    else:
                        # Таблица пуста, устанавливаем в 1
                        pg_cur.execute(f"SELECT setval('{seq_name}', 1)")
                        result = pg_cur.fetchone()[0]
                        print(f"  ✅ {seq_name} установлен в {result} (таблица пуста)")
                        
                except Exception as e:
                    print(f"  ❌ Ошибка обновления {seq_name}: {e}")
            
            # Проверяем, что последовательности работают
            print("🧪 Проверяем последовательности...")
            test_sequences = [
                ('businesses_business_id_seq', 'businesses'),
                ('conversation_sessions_session_id_seq', 'conversation_sessions')
            ]
            
            for seq_name, table_name in test_sequences:
                try:
                    pg_cur.execute(f"SELECT nextval('{seq_name}')")
                    next_id = pg_cur.fetchone()[0]
                    print(f"  ✅ {seq_name}: следующий ID будет {next_id}")
                except Exception as e:
                    print(f"  ❌ Ошибка проверки {seq_name}: {e}")

            pg_conn.commit()

    sqlite_cur.close()
    sqlite_conn.close()
    print("✅ Миграция завершена")


if __name__ == '__main__':
    main()


