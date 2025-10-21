import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from env_utils import is_production, get_database_config, should_create_files

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
except ImportError:
    print("❌ Требуется пакет: pip install psycopg2-binary")
    raise

# Загружаем .env только локально
if not is_production():
    load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=4)

class Database:
    def __init__(self):
        self.conn = None
        self.executor = executor
    
    def build_dsn_from_env(self) -> str:
        """Build PostgreSQL DSN from environment variables"""
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url

        host = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST")
        port = os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or "5432"
        db = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB")
        user = os.getenv("PGUSER") or os.getenv("POSTGRES_USER")
        pwd = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
        sslmode = os.getenv("PGSSLMODE")

        missing = [k for k, v in {
            "PGHOST": host, "PGDATABASE": db, "PGUSER": user, "PGPASSWORD": pwd
        }.items() if not v]
        if missing:
            raise RuntimeError(f"Нет переменных: {', '.join(missing)} (или задайте DATABASE_URL)")

        parts = [
            f"host={host}",
            f"port={port}",
            f"dbname={db}",
            f"user={user}",
            f"password={pwd}",
        ]
        if sslmode:
            parts.append(f"sslmode={sslmode}")
        return " ".join(parts)
    
    async def init_db(self):
        """Инициализация базы данных"""
        try:
            if is_production():
                # В продакшене используем PostgreSQL
                dsn = self.build_dsn_from_env()
                self.conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
                self.conn.autocommit = True
                logger.info("✅ Подключение к PostgreSQL установлено (продакшен)")
            else:
                # Локально используем PostgreSQL (мигрировали с SQLite)
                dsn = self.build_dsn_from_env()
                self.conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
                self.conn.autocommit = True
                logger.info("✅ Подключение к PostgreSQL установлено (локально)")
            
            await self.create_tables()
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            raise
    
    async def create_tables(self):
        """Создание новых таблиц для мульти-бизнесов"""
        def _create():
            cursor = self.conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Новая таблица бизнесов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS businesses (
                    business_id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    business_name TEXT,
                    business_type TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Основная таблица снимков бизнеса
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_snapshots (
                    snapshot_id SERIAL PRIMARY KEY,
                    business_id INTEGER,
                    period_type TEXT,
                    period_date DATE,
                    
                    -- Сырые данные от пользователя
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
                    
                    -- Рассчитанные метрики (22 штуки)
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
                    
                    -- Health Score
                    financial_health_score INTEGER DEFAULT 0,
                    growth_health_score INTEGER DEFAULT 0,
                    efficiency_health_score INTEGER DEFAULT 0,
                    overall_health_score INTEGER DEFAULT 0,
                    
                    -- AI советы и комментарий
                    advice1 TEXT DEFAULT '',
                    advice2 TEXT DEFAULT '',
                    advice3 TEXT DEFAULT '',
                    advice4 TEXT DEFAULT '',
                    ai_commentary TEXT DEFAULT '',
                    
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (business_id) REFERENCES businesses(business_id)
                )
            ''')
            
            # Сессии диалогов для умного сбора данных
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    session_id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    business_id INTEGER,
                    current_state TEXT,
                    collected_data TEXT, -- JSON
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (business_id) REFERENCES businesses(business_id)
                )
            ''')
            
            # Сообщения (логи чата)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id INTEGER,
                    user_message TEXT,
                    bot_response TEXT,
                    message_type TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
                )
            ''')
        
        await asyncio.get_event_loop().run_in_executor(self.executor, _create)
    
    # ===== НОВЫЕ МЕТОДЫ ДЛЯ МУЛЬТИ-БИЗНЕСОВ =====
    
    async def create_business(self, user_id: str, name: str, business_type: str = "general") -> int:
        """Создание нового бизнеса"""
        def _create():
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO businesses (user_id, business_name, business_type)
                VALUES (%s, %s, %s) RETURNING business_id
            ''', (user_id, name, business_type))
            return cursor.fetchone()['business_id']
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _create)
    
    async def get_user_businesses(self, user_id: str) -> List[Dict]:
        """Получение всех бизнесов пользователя"""
        def _get():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT business_id, business_name, business_type, created_at, is_active
                FROM businesses 
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            return [
                {
                    'business_id': row['business_id'],
                    'business_name': row['business_name'],
                    'business_type': row['business_type'],
                    'created_at': row['created_at'],
                    'is_active': row['is_active']
                }
                for row in rows
            ]
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)
    
    async def add_business_snapshot(self, business_id: int, raw_data: Dict, metrics: Dict, period_date: str = None, advice_list: List[str] = None, ai_commentary: str = '') -> int:
        """Добавление снимка бизнеса со всеми метриками"""
        def _add():
            cursor = self.conn.cursor()
            utc_now = datetime.now(timezone.utc)
            moscow_time = utc_now
            actual_period_date = period_date or moscow_time.strftime("%Y-%m-%d")
            
            advice_list_local = (advice_list or [])[:4]
            while len(advice_list_local) < 4:
                advice_list_local.append('')
            
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
                    advice1, advice2, advice3, advice4, ai_commentary, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING snapshot_id
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
                ai_commentary, moscow_time_str
            ))
            return cursor.fetchone()['snapshot_id']
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _add)
    
    async def get_business_history(self, business_id: int, limit: int = 12) -> List[Dict]:
        """Получение истории снимков бизнеса"""
        def _get():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM business_snapshots 
                WHERE business_id = %s 
                ORDER BY created_at DESC, snapshot_id DESC 
                LIMIT %s
            ''', (business_id, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    async def soft_delete_business(self, user_id: str, business_id: int) -> None:
        """Мягкое удаление бизнеса (is_active = FALSE) только владельцем"""
        def _del():
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE businesses SET is_active = FALSE
                WHERE business_id = %s AND user_id = %s
                """,
                (business_id, user_id)
            )
        await asyncio.get_event_loop().run_in_executor(self.executor, _del)

    # Удалено: отрасль больше не обновляется
    
    # ===== СЕССИИ ДЛЯ УМНОГО ДИАЛОГА =====
    
    async def create_conversation_session(self, user_id: str, business_id: int = None, initial_state: str = "awaiting_business_name") -> int:
        """Создание сессии для умного диалога"""
        def _create():
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_sessions (user_id, business_id, current_state, collected_data)
                VALUES (%s, %s, %s, %s) RETURNING session_id
            ''', (user_id, business_id, initial_state, json.dumps({})))
            return cursor.fetchone()['session_id']
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _create)
    
    async def update_session_state(self, session_id: int, new_state: str, new_data: Dict = None):
        """Обновление состояния сессии"""
        def _update():
            cursor = self.conn.cursor()
            if new_data:
                cursor.execute('''
                    UPDATE conversation_sessions 
                    SET current_state = %s, collected_data = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                ''', (new_state, json.dumps(new_data), session_id))
            else:
                cursor.execute('''
                    UPDATE conversation_sessions 
                    SET current_state = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                ''', (new_state, session_id))
        
        await asyncio.get_event_loop().run_in_executor(self.executor, _update)
    
    async def get_session(self, session_id: int) -> Optional[Dict]:
        """Получение данных сессии"""
        def _get():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT session_id, user_id, business_id, current_state, collected_data, created_at
                FROM conversation_sessions 
                WHERE session_id = %s
            ''', (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'session_id': row['session_id'],
                    'user_id': row['user_id'],
                    'business_id': row['business_id'],
                    'current_state': row['current_state'],
                    'collected_data': json.loads(row['collected_data']) if row['collected_data'] else {},
                    'created_at': row['created_at']
                }
            return None
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)
    
    # ===== СТАРЫЕ МЕТОДЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ =====
    
    async def save_user(self, user_id: str, username: str, first_name: str, last_name: str):
        """Сохранение пользователя (старый метод)"""
        def _save():
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name
            ''', (user_id, username, first_name, last_name))
        
        await asyncio.get_event_loop().run_in_executor(self.executor, _save)
    
    async def save_message(self, user_id: str, message_text: str, message_type: str, response_text: str):
        """Сохранение сообщения (старый метод для обратной совместимости)"""
        def _save():
            # Старая схема более не актуальна, оставляем пустой no-op для совместимости
            pass
        
        await asyncio.get_event_loop().run_in_executor(self.executor, _save)

    async def log_message(self, user_id: str, session_id: Optional[int], user_message: str, bot_response: str, message_type: str):
        """Сохранение сообщения в новую таблицу messages с обязательным user_id."""
        def _insert():
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO messages (user_id, session_id, user_message, bot_response, message_type)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, session_id, user_message, bot_response, message_type))
        
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
                WHERE cs.user_id = %s AND m.session_id IS NOT NULL
                ORDER BY m.id DESC
                LIMIT %s
            ''', (user_id, limit))
            rows = cursor.fetchall()
            results: List[Dict] = []
            for row in rows:
                results.append({
                    'user_message': row['user_message'] or '',
                    'bot_response': row['bot_response'] or '',
                    'message_type': row['message_type'] or '',
                    'created_at': row['created_at']
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
                WHERE user_id = %s AND current_state = 'chat'
                ORDER BY updated_at DESC, session_id DESC
                LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            if row:
                return row['session_id']
            # Создаем новую chat-сессию
            cursor.execute('''
                INSERT INTO conversation_sessions (user_id, business_id, current_state, collected_data)
                VALUES (%s, NULL, 'chat', '{}') RETURNING session_id
            ''', (user_id,))
            return cursor.fetchone()['session_id']
        
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

    async def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей"""
        def _get():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT user_id, username, first_name, last_name
                FROM users 
                ORDER BY user_id DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)
    
    async def get_system_stats(self) -> Dict:
        """Получение системной статистики"""
        def _get():
            cursor = self.conn.cursor()
            
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) as total_users FROM users')
            total_users = cursor.fetchone()['total_users']
            
            # Общее количество анализов
            cursor.execute('SELECT COUNT(*) as total_analyses FROM business_snapshots')
            total_analyses = cursor.fetchone()['total_analyses']
            
            # Активные сегодня (пользователи с активностью за последние 24 часа)
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as active_today 
                FROM messages 
                WHERE created_at >= NOW() - INTERVAL '1 day'
            ''')
            active_today = cursor.fetchone()['active_today']
            
            return {
                'total_users': total_users,
                'total_analyses': total_analyses,
                'active_today': active_today
            }
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)
    
    async def get_advice(self) -> List[str]:
        """Получение общих советов"""
        def _get():
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT advice1, advice2, advice3, advice4 
                FROM business_snapshots 
                WHERE advice1 IS NOT NULL AND advice1 != ''
                ORDER BY created_at DESC 
                LIMIT 10
            ''')
            rows = cursor.fetchall()
            advice = []
            for row in rows:
                for key in ['advice1', 'advice2', 'advice3', 'advice4']:
                    val = row.get(key)
                    if val and str(val).strip():
                        advice.append(str(val).strip())
            return advice[:5]  # Возвращаем максимум 5 советов
        
        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

# Глобальный экземпляр базы данных
db = Database()