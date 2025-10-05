import asyncio
from datetime import datetime
import json
from typing import Dict, List, Optional
import logging
import os

# ПРОВЕРЯЕМ ДОСТУПНОСТЬ ASYNCPG
try:
    import asyncpg
    HAS_ASYNCGP = True
    print("✅ asyncpg доступен")
except ImportError:
    HAS_ASYNCGP = False
    print("❌ asyncpg НЕ доступен, используем SQLite")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool = None
        self.conn = None
    
    async def init_db(self):
        """Инициализация подключения к базе данных"""
        
        # ЕСЛИ ASYNCPG ДОСТУПЕН - ПРОБУЕМ POSTGRESQL
        if HAS_ASYNCGP:
            try:
                self.pool = await asyncpg.create_pool(
                    database='railway',
                    user='postgres',
                    password='wMpYpLQssFkpdqxISRxfvCFBEnObVpIS',
                    host='postgres.railway.internal',
                    port=5432
                )
                await self.create_tables()
                print("✅ PostgreSQL база данных подключена")
                
                # ОЧИЩАЕМ SQLite соединение когда PostgreSQL активен
                if hasattr(self, 'conn') and self.conn:
                    self.conn.close()
                self.conn = None
                return  # УСПЕШНО ПОДКЛЮЧИЛИСЬ К POSTGRESQL
                
            except Exception as e:
                print(f"❌ Ошибка PostgreSQL: {e}")
                # ПРОДОЛЖАЕМ НА SQLite ЕСЛИ POSTGRESQL НЕ РАБОТАЕТ
        
        # ИСПОЛЬЗУЕМ SQLite (ЕСЛИ ASYNCPG НЕ ДОСТУПЕН ИЛИ POSTGRESQL УПАЛ)
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'business_bot.db')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_sqlite_tables()
        print(f"✅ SQLite база данных подключена: {db_path}")
        
    def create_sqlite_tables(self):
        """Создание таблиц в SQLite"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                message_text TEXT,
                message_type TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                revenue REAL DEFAULT 0,
                expenses REAL DEFAULT 0,
                profit REAL DEFAULT 0,
                clients INTEGER DEFAULT 0,
                average_check REAL DEFAULT 0,
                investments REAL DEFAULT 0,
                rating INTEGER DEFAULT 0,
                commentary TEXT,
                advice TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    async def create_tables(self):
        """Создание таблиц в PostgreSQL"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT REFERENCES users(user_id),
                    message_text TEXT,
                    message_type TEXT,
                    response_text TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS business_analyses (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT REFERENCES users(user_id),
                    revenue DECIMAL DEFAULT 0,
                    expenses DECIMAL DEFAULT 0,
                    profit DECIMAL DEFAULT 0,
                    clients INTEGER DEFAULT 0,
                    average_check DECIMAL DEFAULT 0,
                    investments DECIMAL DEFAULT 0,
                    rating INTEGER DEFAULT 0,
                    commentary TEXT,
                    advice TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
    
    async def save_user(self, user_id: str, username: str, first_name: str, last_name: str):
        logger.info(f"💾 СОХРАНЕНИЕ ПОЛЬЗОВАТЕЛЯ: user_id={user_id}")
        try:
            if self.pool:
                logger.info("💾 Используем PostgreSQL")
                async with self.pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO users (user_id, username, first_name, last_name)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name
                    ''', user_id, username, first_name, last_name)
            else:
                logger.info("💾 Используем SQLite")
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self._sqlite_save_user, 
                    user_id, username, first_name, last_name
                )
            logger.info("✅ Пользователь успешно сохранен")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения пользователя: {e}")
    
    def _sqlite_save_user(self, user_id: str, username: str, first_name: str, last_name: str):
        """Синхронная версия для SQLite"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        self.conn.commit()
    
    def _sqlite_save_message(self, user_id: str, message_text: str, message_type: str, response_text: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO messages (user_id, message_text, message_type, response_text)
            VALUES (?, ?, ?, ?)
        ''', (user_id, message_text, message_type, response_text))
        self.conn.commit()
        cursor.execute("SELECT last_insert_rowid()")
        new_id = cursor.fetchone()[0]
        logger.info(f"🔍 СОЗДАНО СООБЩЕНИЕ С ID: {new_id}")
        logger.info("✅ Коммит sqlite успешно сохранено")
        print(f"🔍 Путь к БД: {os.path.abspath('business_bot.db')}")

    async def save_message(self, user_id: str, message_text: str, message_type: str, response_text: str):
        logger.info(f"💾 СОХРАНЕНИЕ СООБЩЕНИЯ: user_id={user_id}, type={message_type}")
        try:
            if self.pool:
                logger.info("💾 Используем PostgreSQL")
                async with self.pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO messages (user_id, message_text, message_type, response_text)
                        VALUES ($1, $2, $3, $4)
                    ''', user_id, message_text, message_type, response_text)
            else:
                logger.info("💾 Используем SQLite")
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._sqlite_save_message,
                    user_id, message_text, message_type, response_text
                )
            logger.info("✅ Сообщение успешно сохранено")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сообщения: {e}")
    
    async def save_business_analysis(self, user_id: str, business_data: Dict):
        """Сохранение результатов бизнес-анализа"""
        try:
            advice_text = json.dumps(business_data.get("СОВЕТЫ", []), ensure_ascii=False)
            
            if self.pool:
                async with self.pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO business_analyses 
                        (user_id, revenue, expenses, profit, clients, average_check, 
                         investments, rating, commentary, advice)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ''', user_id, 
                        business_data.get("ВЫРУЧКА", 0),
                        business_data.get("РАСХОДЫ", 0),
                        business_data.get("ПРИБЫЛЬ", 0),
                        business_data.get("КЛИЕНТЫ", 0),
                        business_data.get("СРЕДНИЙ_ЧЕК", 0),
                        business_data.get("ИНВЕСТИЦИИ", 0),
                        business_data.get("ОЦЕНКА", 0),
                        business_data.get("КОММЕНТАРИЙ", ""),
                        advice_text
                    )
            else:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._sqlite_save_business_analysis,
                    user_id, business_data, advice_text
                )
        except Exception as e:
            print(f"❌ Ошибка сохранения бизнес-анализа: {e}")
    
    def _sqlite_save_business_analysis(self, user_id: str, business_data: Dict, advice_text: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO business_analyses 
            (user_id, revenue, expenses, profit, clients, average_check, 
             investments, rating, commentary, advice)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            business_data.get("ВЫРУЧКА", 0),
            business_data.get("РАСХОДЫ", 0),
            business_data.get("ПРИБЫЛЬ", 0),
            business_data.get("КЛИЕНТЫ", 0),
            business_data.get("СРЕДНИЙ_ЧЕК", 0),
            business_data.get("ИНВЕСТИЦИИ", 0),
            business_data.get("ОЦЕНКА", 0),
            business_data.get("КОММЕНТАРИЙ", ""),
            advice_text
        ))
        self.conn.commit()
    
    async def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Получение истории сообщений пользователя"""
        try:
            if self.pool:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch('''
                        SELECT message_text, message_type, response_text, created_at
                        FROM messages 
                        WHERE user_id = $1 
                        ORDER BY created_at DESC 
                        LIMIT $2
                    ''', user_id, limit)
                    return [dict(row) for row in rows]
            else:
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._sqlite_get_user_history,
                    user_id, limit
                )
        except Exception as e:
            print(f"❌ Ошибка получения истории: {e}")
            return []
    
    def _sqlite_get_user_history(self, user_id: str, limit: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT message_text, message_type, response_text, created_at
            FROM messages 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        rows = cursor.fetchall()
        return [
            {
                'message_text': row[0],
                'message_type': row[1],
                'response_text': row[2],
                'created_at': row[3]
            }
            for row in rows
        ]
    
    async def get_user_business_data(self, user_id: str) -> List[Dict]:
        """Получение истории бизнес-анализов пользователя"""
        try:
            if self.pool:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch('''
                        SELECT revenue, expenses, profit, clients, average_check, 
                               investments, rating, commentary, created_at
                        FROM business_analyses 
                        WHERE user_id = $1 
                        ORDER BY created_at DESC
                    ''', user_id)
                    return [dict(row) for row in rows]
            else:
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._sqlite_get_user_business_data,
                    user_id
                )
        except Exception as e:
            print(f"❌ Ошибка получения бизнес-данных: {e}")
            return []
    
    def _sqlite_get_user_business_data(self, user_id: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT revenue, expenses, profit, clients, average_check, 
                   investments, rating, commentary, created_at
            FROM business_analyses 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        return [
            {
                'revenue': row[0],
                'expenses': row[1],
                'profit': row[2],
                'clients': row[3],
                'average_check': row[4],
                'investments': row[5],
                'rating': row[6],
                'commentary': row[7],
                'created_at': row[8]
            }
            for row in rows
        ]

# Глобальный экземпляр базы данных
db = Database()