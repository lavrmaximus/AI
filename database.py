import asyncio
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
import os
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=4)

class Database:
    def __init__(self):
        self.conn = None
        self.executor = executor
    
    async def init_db(self):
        """Инициализация новой БД"""
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'business_bot_v2.db')
        # Поднимем timeout и busy_timeout, без включения WAL
        self.conn = sqlite3.connect(db_path, timeout=5.0, check_same_thread=False)
        try:
            self.conn.execute('PRAGMA busy_timeout=5000')
        except Exception:
            pass
        self.create_tables()
        print(f"✅ Новая SQLite база подключена: {db_path}")
    
    def create_tables(self):
        """Создание новых таблиц для мульти-бизнесов"""
        cursor = self.conn.cursor()
        
        # Таблица пользователей (остается)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Новая таблица бизнесов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS businesses (
                business_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                business_name TEXT,
                business_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Основная таблица снимков бизнеса
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                period_type TEXT,
                period_date DATE,
                
                -- Сырые данные от пользователя
                revenue REAL DEFAULT 0,
                expenses REAL DEFAULT 0,
                profit REAL DEFAULT 0,
                clients INTEGER DEFAULT 0,
                average_check REAL DEFAULT 0,
                investments REAL DEFAULT 0,
                marketing_costs REAL DEFAULT 0,
                employees INTEGER DEFAULT 0,
                new_clients_per_month INTEGER DEFAULT 0,
                customer_retention_rate REAL DEFAULT 0,
                
                -- Рассчитанные метрики (22 штуки)
                profit_margin REAL DEFAULT 0,
                break_even_clients REAL DEFAULT 0,
                safety_margin REAL DEFAULT 0,
                roi REAL DEFAULT 0,
                profitability_index REAL DEFAULT 0,
                ltv REAL DEFAULT 0,
                cac REAL DEFAULT 0,
                ltv_cac_ratio REAL DEFAULT 0,
                customer_profit_margin REAL DEFAULT 0,
                sgr REAL DEFAULT 0,
                revenue_growth_rate REAL DEFAULT 0,
                asset_turnover REAL DEFAULT 0,
                roe REAL DEFAULT 0,
                months_to_bankruptcy REAL DEFAULT 0,
                
                -- Health Score
                financial_health_score INTEGER DEFAULT 0,
                growth_health_score INTEGER DEFAULT 0,
                efficiency_health_score INTEGER DEFAULT 0,
                overall_health_score INTEGER DEFAULT 0,
                
                -- AI советы (4 штуки)
                advice1 TEXT DEFAULT '',
                advice2 TEXT DEFAULT '',
                advice3 TEXT DEFAULT '',
                advice4 TEXT DEFAULT '',
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses (business_id)
            )
        ''')
        
        # Сессии диалогов для умного сбора данных
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                business_id INTEGER,
                current_state TEXT,
                collected_data TEXT, -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (business_id) REFERENCES businesses (business_id)
            )
        ''')
        
        # Сообщения (логи чата)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                user_message TEXT,
                bot_response TEXT,
                message_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id)
            )
        ''')
        
        # Миграция: добавляем колонки advice1-4 если их нет
        # Проверяем существование колонок
        cursor.execute("PRAGMA table_info(business_snapshots)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        advice_columns = ['advice1', 'advice2', 'advice3', 'advice4']
        for col in advice_columns:
            if col not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE business_snapshots ADD COLUMN {col} TEXT DEFAULT ''")
                    print(f"✅ Добавлена колонка {col}")
                except sqlite3.OperationalError as e:
                    print(f"❌ Ошибка добавления колонки {col}: {e}")
        
        # Миграция: добавляем колонки new_clients_per_month и customer_retention_rate
        additional_columns = ['new_clients_per_month', 'customer_retention_rate']
        for col in additional_columns:
            if col not in existing_columns:
                try:
                    if col == 'new_clients_per_month':
                        cursor.execute(f"ALTER TABLE business_snapshots ADD COLUMN {col} INTEGER DEFAULT 0")
                    else:  # customer_retention_rate
                        cursor.execute(f"ALTER TABLE business_snapshots ADD COLUMN {col} REAL DEFAULT 0")
                    print(f"✅ Добавлена колонка {col}")
                except sqlite3.OperationalError as e:
                    print(f"❌ Ошибка добавления колонки {col}: {e}")
        
        # Миграция: удаляем колонку industry из таблицы businesses
        # Проверяем существование колонки industry
        cursor.execute("PRAGMA table_info(businesses)")
        businesses_columns = [row[1] for row in cursor.fetchall()]
        
        if 'industry' in businesses_columns:
            try:
                # SQLite не поддерживает DROP COLUMN, поэтому пересоздаем таблицу
                print("🔄 Удаляем колонку industry из таблицы businesses...")
                
                # Создаем временную таблицу без industry
                cursor.execute('''
                    CREATE TABLE businesses_new (
                        business_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        business_name TEXT,
                        business_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Копируем данные без колонки industry
                cursor.execute('''
                    INSERT INTO businesses_new (business_id, user_id, business_name, business_type, created_at, is_active)
                    SELECT business_id, user_id, business_name, business_type, created_at, is_active
                    FROM businesses
                ''')
                
                # Удаляем старую таблицу и переименовываем новую
                cursor.execute('DROP TABLE businesses')
                cursor.execute('ALTER TABLE businesses_new RENAME TO businesses')
                
                print("✅ Колонка industry успешно удалена из таблицы businesses")
                
            except sqlite3.OperationalError as e:
                print(f"❌ Ошибка удаления колонки industry: {e}")
        
        self.conn.commit()
    
    # ===== НОВЫЕ МЕТОДЫ ДЛЯ МУЛЬТИ-БИЗНЕСОВ =====
    
    async def create_business(self, user_id: str, name: str, business_type: str = "general") -> int:
        """Создание нового бизнеса"""
        def _create():
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO businesses (user_id, business_name, business_type)
                VALUES (?, ?, ?)
            ''', (user_id, name, business_type))
            self.conn.commit()
            return cursor.lastrowid
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _create)
    
    async def get_user_businesses(self, user_id: str) -> List[Dict]:
        """Получение всех бизнесов пользователя"""
        def _get():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT business_id, business_name, business_type, created_at, is_active
                FROM businesses 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            return [
                {
                    'business_id': row[0],
                    'business_name': row[1],
                    'business_type': row[2],
                    'created_at': row[3],
                    'is_active': row[4]
                }
                for row in rows
            ]
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)
    
    async def add_business_snapshot(self, business_id: int, raw_data: Dict, metrics: Dict, period_date: str = None, advice_list: List[str] = None) -> int:
        """Добавление снимка бизнеса со всеми метриками"""
        def _add():
            cursor = self.conn.cursor()
            # ФИКС: используем московское время (UTC+3) - строго +3 часа
            utc_now = datetime.utcnow()
            moscow_time = utc_now + timedelta(hours=3)
            actual_period_date = period_date or moscow_time.strftime("%Y-%m-%d")
            
            # Подготавливаем советы (до 4 штук)
            advice_list_local = (advice_list or [])[:4]
            while len(advice_list_local) < 4:
                advice_list_local.append('')
            
            # Используем московское время для created_at
            moscow_time_str = moscow_time.strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
                INSERT INTO business_snapshots (
                    business_id, period_type, period_date,
                    revenue, expenses, profit, clients, average_check, investments, marketing_costs, employees,
                    new_clients_per_month, customer_retention_rate,
                    profit_margin, break_even_clients, safety_margin, roi, profitability_index,
                    ltv, cac, ltv_cac_ratio, customer_profit_margin, sgr, revenue_growth_rate,
                    asset_turnover, roe, months_to_bankruptcy,
                    financial_health_score, growth_health_score, efficiency_health_score, overall_health_score,
                    advice1, advice2, advice3, advice4, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                business_id, 'monthly', actual_period_date,
                raw_data.get('revenue', 0), raw_data.get('expenses', 0), raw_data.get('profit', 0),
                raw_data.get('clients', 0), raw_data.get('average_check', 0), raw_data.get('investments', 0),
                raw_data.get('marketing_costs', 0), raw_data.get('employees', 0),
                raw_data.get('new_clients_per_month', 0), raw_data.get('customer_retention_rate', 0),
                metrics.get('profit_margin', 0), metrics.get('break_even_clients', 0),
                metrics.get('safety_margin', 0), metrics.get('roi', 0), metrics.get('profitability_index', 0),
                metrics.get('ltv', 0), metrics.get('cac', 0), metrics.get('ltv_cac_ratio', 0),
                metrics.get('customer_profit_margin', 0), metrics.get('sgr', 0), metrics.get('revenue_growth_rate', 0),
                metrics.get('asset_turnover', 0), metrics.get('roe', 0), metrics.get('months_to_bankruptcy', 0),
                metrics.get('financial_health_score', 0), metrics.get('growth_health_score', 0),
                metrics.get('efficiency_health_score', 0), metrics.get('overall_health_score', 0),
                advice_list_local[0], advice_list_local[1], advice_list_local[2], advice_list_local[3],
                moscow_time_str
            ))
            self.conn.commit()
            return cursor.lastrowid
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _add)
    
    async def get_business_history(self, business_id: int, limit: int = 12) -> List[Dict]:
        """Получение истории снимков бизнеса"""
        def _get():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM business_snapshots 
                WHERE business_id = ? 
                ORDER BY created_at DESC, snapshot_id DESC 
                LIMIT ?
            ''', (business_id, limit))
            rows = cursor.fetchall()
            
            # Получаем названия колонок
            columns = [description[0] for description in cursor.description]
            
            return [dict(zip(columns, row)) for row in rows]
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    async def soft_delete_business(self, user_id: str, business_id: int) -> None:
        """Мягкое удаление бизнеса (is_active = FALSE) только владельцем"""
        def _del():
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE businesses SET is_active = FALSE
                WHERE business_id = ? AND user_id = ?
                """,
                (business_id, user_id)
            )
            self.conn.commit()
        await asyncio.get_event_loop().run_in_executor(self.executor, _del)

    # Удалено: отрасль больше не обновляется
    
    # ===== СЕССИИ ДЛЯ УМНОГО ДИАЛОГА =====
    
    async def create_conversation_session(self, user_id: str, business_id: int = None, initial_state: str = "awaiting_business_name") -> int:
        """Создание сессии для умного диалога"""
        def _create():
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_sessions (user_id, business_id, current_state, collected_data)
                VALUES (?, ?, ?, ?)
            ''', (user_id, business_id, initial_state, json.dumps({})))
            self.conn.commit()
            return cursor.lastrowid
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _create)
    
    async def update_session_state(self, session_id: int, new_state: str, new_data: Dict = None):
        """Обновление состояния сессии"""
        def _update():
            cursor = self.conn.cursor()
            if new_data:
                cursor.execute('''
                    UPDATE conversation_sessions 
                    SET current_state = ?, collected_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (new_state, json.dumps(new_data), session_id))
            else:
                cursor.execute('''
                    UPDATE conversation_sessions 
                    SET current_state = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (new_state, session_id))
            self.conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(self.executor, _update)
    
    async def get_session(self, session_id: int) -> Optional[Dict]:
        """Получение данных сессии"""
        def _get():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT session_id, user_id, business_id, current_state, collected_data, created_at
                FROM conversation_sessions 
                WHERE session_id = ?
            ''', (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'session_id': row[0],
                    'user_id': row[1],
                    'business_id': row[2],
                    'current_state': row[3],
                    'collected_data': json.loads(row[4]) if row[4] else {},
                    'created_at': row[5]
                }
            return None
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)
    
    # ===== СТАРЫЕ МЕТОДЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ =====
    
    async def save_user(self, user_id: str, username: str, first_name: str, last_name: str):
        """Сохранение пользователя (старый метод)"""
        def _save():
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            self.conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(self.executor, _save)
    
    async def save_message(self, user_id: str, message_text: str, message_type: str, response_text: str):
        """Сохранение сообщения (старый метод для обратной совместимости)"""
        def _save():
            # Старая схема более не актуальна, оставляем пустой no-op для совместимости
            pass
        
        await asyncio.get_event_loop().run_in_executor(self.executor, _save)

    async def log_message(self, session_id: Optional[int], user_message: str, bot_response: str, message_type: str):
        """Сохранение сообщения в новую таблицу messages (связь через session_id, может быть NULL)."""
        def _insert():
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO messages (session_id, user_message, bot_response, message_type)
                VALUES (?, ?, ?, ?)
            ''', (session_id, user_message, bot_response, message_type))
            self.conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(self.executor, _insert)
    
    async def get_user_recent_messages(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Возвращает последние сообщения пользователя из всех его сессий для восстановления контекста."""
        def _select():
            cursor = self.conn.cursor()
            # Берем сообщения, связанные с сессиями данного пользователя
            cursor.execute('''
                SELECT m.user_message, m.bot_response, m.message_type, m.created_at
                FROM messages m
                JOIN conversation_sessions cs ON cs.session_id = m.session_id
                WHERE cs.user_id = ? AND m.session_id IS NOT NULL
                ORDER BY m.created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            rows = cursor.fetchall()
            results: List[Dict] = []
            for row in rows:
                results.append({
                    'user_message': row[0] or '',
                    'bot_response': row[1] or '',
                    'message_type': row[2] or '',
                    'created_at': row[3]
                })
            # Разворачиваем обратно в хронологический порядок (старые -> новые)
            results.reverse()
            return results
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _select)

    async def get_or_create_user_chat_session(self, user_id: str) -> int:
        """Возвращает id сессии для общего чата пользователя; создает при отсутствии."""
        def _get_or_create() -> int:
            cursor = self.conn.cursor()
            # Ищем последнюю сессию типа chat без привязки к бизнесу
            cursor.execute('''
                SELECT session_id FROM conversation_sessions
                WHERE user_id = ? AND current_state = 'chat'
                ORDER BY updated_at DESC, session_id DESC
                LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            if row:
                return row[0]
            # Создаем новую chat-сессию
            cursor.execute('''
                INSERT INTO conversation_sessions (user_id, business_id, current_state, collected_data)
                VALUES (?, NULL, 'chat', '{}')
            ''', (user_id,))
            self.conn.commit()
            return cursor.lastrowid
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get_or_create)
    
    async def save_business_analysis(self, user_id: str, business_data: Dict):
        """Сохранение бизнес-анализа (старый метод для обратной совместимости)"""
        # Создаем временный бизнес для старой системы
        business_id = await self.create_business(user_id, "Основной бизнес")
        
        # Преобразуем старые данные в новый формат
        raw_data = {
            'revenue': business_data.get("ВЫРУЧКА", 0),
            'expenses': business_data.get("РАСХОДЫ", 0),
            'profit': business_data.get("ПРИБЫЛЬ", 0),
            'clients': business_data.get("КЛИЕНТЫ", 0),
            'average_check': business_data.get("СРЕДНИЙ_ЧЕК", 0),
            'investments': business_data.get("ИНВЕСТИЦИИ", 0),
            'marketing_costs': 0,
            'employees': 0
        }
        
        # Базовые метрики (полную систему health score добавим позже)
        metrics = {
            'profit_margin': business_data.get("РЕНTAБЕЛЬНОСТЬ", 0),
            'break_even_clients': business_data.get("ТОЧKA_БЕЗУБЫТОЧНОСТИ", 0),
            'safety_margin': business_data.get("ЗАПАС_ПРОЧНОСТИ", 0),
            'overall_health_score': business_data.get("ОЦЕНКА", 0) * 10  # преобразуем 0-10 в 0-100
        }
        
        await self.add_business_snapshot(business_id, raw_data, metrics)
    
    async def get_user_business_data(self, user_id: str) -> List[Dict]:
        """Получение бизнес-данных пользователя (старый метод)"""
        businesses = await self.get_user_businesses(user_id)
        if not businesses:
            return []
        
        # Берем первый бизнес пользователя
        business_id = businesses[0]['business_id']
        snapshots = await self.get_business_history(business_id, limit=5)
        
        # Преобразуем в старый формат для обратной совместимости
        result = []
        for snapshot in snapshots:
            result.append({
                'revenue': snapshot['revenue'],
                'expenses': snapshot['expenses'],
                'profit': snapshot['profit'],
                'clients': snapshot['clients'],
                'average_check': snapshot['average_check'],
                'investments': snapshot['investments'],
                'rating': snapshot['overall_health_score'] // 10,  # преобразуем 0-100 в 0-10
                'commentary': f"Health Score: {snapshot['overall_health_score']}",
                'created_at': snapshot['created_at']
            })
        
        return result

# Глобальный экземпляр базы данных
db = Database()