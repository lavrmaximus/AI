from flask import Flask, render_template, request, jsonify
import sqlite3
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Синхронная версия работы с базой данных
class SyncDatabase:
    def __init__(self):
        self.conn = None
        self.init_db()
    
    def init_db(self):
        """Инициализация подключения к SQLite базе данных"""
        try:
            self.conn = sqlite3.connect('business_bot.db', check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.create_tables()
            self.add_sample_goals()
            print("✅ SQLite база данных подключена и таблицы созданы")
        except Exception as e:
            print(f"❌ Ошибка подключения к базе данных: {e}")
    
    def create_tables(self):
        """Создание таблиц в SQLite"""
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                message_text TEXT,
                message_type TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица бизнес-анализов
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Добавляем тестовые данные, если их нет
        self.add_sample_data()
        self.conn.commit()
    def create_tables(self):
        """Создание таблиц в SQLite"""
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                message_text TEXT,
                message_type TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица бизнес-анализов
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица целей - ДОБАВЛЯЕМ ЭТУ ТАБЛИЦУ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                target_value INTEGER DEFAULT 1,
                current_value INTEGER DEFAULT 0,
                progress_percentage INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                category TEXT,
                deadline DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Добавляем тестовые данные, если их нет
        self.add_sample_data()
        self.conn.commit()
    
    def add_sample_data(self):
        """Добавление тестовых данных для демонстрации"""
        cursor = self.conn.cursor()
        
        # Проверяем, есть ли уже данные
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            # Добавляем тестового пользователя
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', ('123', 'test_user', 'Иван', 'Петров'))
            
            # Добавляем тестовые бизнес-данные
            sample_dates = [
                (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') 
                for i in range(30, 0, -1)
            ]
            
            for i, date in enumerate(sample_dates):
                revenue = 50000 + i * 1500 + (i % 7) * 2000
                expenses = 30000 + i * 800 + (i % 5) * 1000
                profit = revenue - expenses
                clients = 50 + i * 2
                avg_check = 1200 + i * 10
                
                cursor.execute('''
                    INSERT INTO business_analyses 
                    (user_id, revenue, expenses, profit, clients, average_check, 
                     investments, rating, commentary, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    '123', revenue, expenses, profit, clients, avg_check,
                    5000, min(10, 6 + i // 5),
                    f"Автоматически сгенерированные данные за {date}",
                    date
                ))
            
            self.conn.commit()
            print("✅ Тестовые данные добавлены")

    def get_user_business_data(self, user_id: str):
        """Получение истории бизнес-анализов пользователя"""
        try:
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
        except Exception as e:
            print(f"❌ Ошибка получения бизнес-данных: {e}")
            return []

    def get_users(self):
        """Получение списка пользователей"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT user_id, username, first_name, last_name FROM users')
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'name': f"{row[2]} {row[3]}" if row[2] and row[3] else row[1] or f"User {row[0]}"
                }
                for row in rows
            ]
        except Exception as e:
            print(f"❌ Ошибка получения пользователей: {e}")
            return []
    # Добавляем методы в класс SyncDatabase:

    def get_user_goals(self, user_id: str):
        """Получение целей пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, title, description, target_value, current_value, 
                    progress_percentage, status, category, deadline, created_at
                FROM goals 
                WHERE user_id = ? 
                ORDER BY 
                    CASE status 
                        WHEN 'active' THEN 1 
                        WHEN 'completed' THEN 2 
                        ELSE 3 
                    END,
                    created_at DESC
            ''', (user_id,))
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'target_value': row[3],
                    'current_value': row[4],
                    'progress_percentage': row[5],
                    'status': row[6],
                    'category': row[7],
                    'deadline': row[8],
                    'created_at': row[9]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"❌ Ошибка получения целей: {e}")
            return []

    def update_goal_progress(self, goal_id: int, current_value: int):
        """Обновление прогресса цели"""
        try:
            cursor = self.conn.cursor()
            
            # Получаем текущие данные цели
            cursor.execute('SELECT target_value FROM goals WHERE id = ?', (goal_id,))
            goal = cursor.fetchone()
            
            if not goal:
                return False
            
            target_value = goal[0]
            progress_percentage = min(100, int((current_value / target_value) * 100)) if target_value > 0 else 0
            status = 'completed' if progress_percentage >= 100 else 'active'
            
            cursor.execute('''
                UPDATE goals 
                SET current_value = ?, progress_percentage = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (current_value, progress_percentage, status, goal_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления цели: {e}")
            return False

    def complete_goal(self, goal_id: int):
        """Завершение цели"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE goals 
                SET status = 'completed', progress_percentage = 100, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (goal_id,))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка завершения цели: {e}")
            return False

    def add_sample_goals(self):
        """Добавление тестовых целей"""
        try:
            cursor = self.conn.cursor()
            
            # Проверяем, есть ли уже цели
            cursor.execute("SELECT COUNT(*) FROM goals")
            if cursor.fetchone()[0] == 0:
                sample_goals = [
                    ('123', 'Запуск интернет-магазина', 'Запустить полнофункциональный интернет-магазин', 10, 7, 'active', 'development', '2024-12-31'),
                    ('123', 'Привлечение первых клиентов', 'Привлечь первых 100 клиентов', 100, 45, 'active', 'marketing', '2024-11-30'),
                    ('123', 'Оптимизация расходов', 'Снизить операционные расходы на 15%', 15, 8, 'active', 'operations', '2024-10-31'),
                    ('123', 'Заказ первой партии товара', 'Заказать первую партию товара из 4 единиц', 4, 4, 'completed', 'purchasing', '2024-09-30')
                ]
                
                for goal in sample_goals:
                    progress = int((goal[4] / goal[3]) * 100) if goal[3] > 0 else 0
                    status = 'completed' if progress >= 100 else goal[5]
                    
                    cursor.execute('''
                        INSERT INTO goals (user_id, title, description, target_value, current_value, 
                                        progress_percentage, status, category, deadline)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (goal[0], goal[1], goal[2], goal[3], goal[4], progress, status, goal[6], goal[7]))
                
                self.conn.commit()
                print("✅ Тестовые цели добавлены")
        except Exception as e:
            print(f"❌ Ошибка добавления тестовых целей: {e}")

# В методе init_db вызвать add_sample_goals после create_tables

# Инициализируем базу данных
db = SyncDatabase()

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Страница дашборда
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Страница аналитики
@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

# API endpoint для получения финансовых данных пользователя
@app.route('/api/user-finance-data/<user_id>')
def get_user_finance_data(user_id):
    try:
        business_data = db.get_user_business_data(user_id)
        
        if not business_data:
            return jsonify({
                'success': False,
                'error': 'Данные не найдены'
            }), 404
        
        # Преобразуем данные для графиков
        dates = []
        revenue = []
        expenses = []
        profit = []
        clients = []
        
        for record in business_data[:30]:  # Последние 30 записей
            if isinstance(record['created_at'], str):
                dates.append(record['created_at'][:10])
            else:
                dates.append(record['created_at'].strftime('%d.%m'))
            
            revenue.append(float(record['revenue'] or 0))
            expenses.append(float(record['expenses'] or 0))
            profit.append(float(record['profit'] or 0))
            clients.append(int(record['clients'] or 0))
        
        return jsonify({
            'success': True,
            'data': {
                'dates': dates,
                'revenue': revenue,
                'expenses': expenses,
                'profit': profit,
                'clients': clients
            },
            'latest': business_data[0] if business_data else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API endpoint для KPI метрик пользователя
@app.route('/api/user-kpi-metrics/<user_id>')
def get_user_kpi_metrics(user_id):
    try:
        business_data = db.get_user_business_data(user_id)
        
        if not business_data:
            return jsonify({
                'success': False,
                'error': 'Данные не найдены'
            }), 404
        
        latest = business_data[0]
        previous = business_data[1] if len(business_data) > 1 else None
        
        # Расчет изменений в %
        def calculate_change(current_val, previous_val):
            if previous_val and float(previous_val) > 0:
                return round(((float(current_val) - float(previous_val)) / float(previous_val)) * 100, 1)
            return 0
        
        kpi_data = {
            'revenue': {
                'current': float(latest['revenue'] or 0),
                'change': calculate_change(latest['revenue'], previous['revenue'] if previous else 0)
            },
            'expenses': {
                'current': float(latest['expenses'] or 0),
                'change': calculate_change(latest['expenses'], previous['expenses'] if previous else 0)
            },
            'profit': {
                'current': float(latest['profit'] or 0),
                'change': calculate_change(latest['profit'], previous['profit'] if previous else 0)
            },
            'clients': {
                'current': int(latest['clients'] or 0),
                'change': calculate_change(latest['clients'], previous['clients'] if previous else 0)
            },
            'average_check': float(latest['average_check'] or 0),
            'rating': int(latest['rating'] or 0)
        }
        
        return jsonify({
            'success': True,
            'kpi': kpi_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API endpoint для анализа от ИИ
@app.route('/api/user-ai-analysis/<user_id>')
def get_user_ai_analysis(user_id):
    try:
        business_data = db.get_user_business_data(user_id)
        
        if not business_data:
            return jsonify({
                'success': False,
                'error': 'Данные не найдены'
            }), 404
        
        latest = business_data[0]
        
        # Генерируем анализ на основе данных
        analysis_data = generate_ai_analysis(latest, business_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
# API endpoint для получения целей пользователя
@app.route('/api/user-goals/<user_id>')
def get_user_goals(user_id):
    try:
        goals = db.get_user_goals(user_id)
        return jsonify({
            'success': True,
            'goals': goals
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API endpoint для обновления прогресса цели
@app.route('/api/update-goal-progress', methods=['POST'])
def update_goal_progress():
    try:
        data = request.json
        goal_id = data.get('goal_id')
        current_value = data.get('current_value')
        
        if db.update_goal_progress(goal_id, current_value):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Goal not found'}), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API endpoint для завершения цели
@app.route('/api/complete-goal', methods=['POST'])
def complete_goal():
    try:
        data = request.json
        goal_id = data.get('goal_id')
        
        if db.complete_goal(goal_id):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Goal not found'}), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
# Страница целей
@app.route('/goals')
def goals():
    return render_template('goals.html')


def generate_ai_analysis(latest_data, history_data):
    """Генерация AI анализа на основе данных из БД"""
    
    revenue = float(latest_data['revenue'] or 0)
    expenses = float(latest_data['expenses'] or 0)
    profit = float(latest_data['profit'] or 0)
    clients = int(latest_data['clients'] or 0)
    avg_check = float(latest_data['average_check'] or 0)
    rating = int(latest_data['rating'] or 0)
    
    # Анализ прибыльности
    profitability = (profit / revenue * 100) if revenue > 0 else 0
    if profitability > 20:
        profit_status = "высокой"
    elif profitability > 10:
        profit_status = "средней"
    else:
        profit_status = "низкой"
    
    # Анализ эффективности
    efficiency_analysis = []
    if expenses > revenue * 0.7:
        efficiency_analysis.append("Высокие расходы требуют оптимизации")
    if avg_check < 1000:
        efficiency_analysis.append("Низкий средний чек - рассмотрите повышение цен")
    if clients < 10:
        efficiency_analysis.append("Мало клиентов - усильте маркетинг")
    
    # Рекомендации
    recommendations = []
    if profitability < 15:
        recommendations.append("Снизить операционные расходы")
    if avg_check < 1500:
        recommendations.append("Внедрить up-sell стратегии")
    if len(history_data) > 1:
        previous = history_data[1]
        prev_revenue = float(previous['revenue'] or 0)
        if prev_revenue > 0:
            growth = ((revenue - prev_revenue) / prev_revenue * 100)
            if growth < 5:
                recommendations.append("Разработать стратегию роста продаж")
    
    return {
        'summary': f"📊 Ваш бизнес показывает {profit_status} рентабельность ({profitability:.1f}%). Выручка: {revenue:,.0f} руб., Прибыль: {profit:,.0f} руб.",
        'metrics': {
            'profitability': round(profitability, 1),
            'client_value': avg_check * clients if clients > 0 else 0,
            'efficiency_score': min(100, max(0, rating * 10 + profitability))
        },
        'trends': efficiency_analysis if efficiency_analysis else ["Бизнес стабилен, продолжайте в том же духе!"],
        'recommendations': recommendations if recommendations else ["Продолжайте текущую стратегию"],
        'rating': rating,
        'commentary': latest_data.get('commentary', '')
    }

# API endpoint для списка пользователей
@app.route('/api/users')
def get_users():
    try:
        users = db.get_users()
        return jsonify({
            'success': True,
            'users': users
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@app.route('/test-css')
@app.route('/debug-static')
def debug_static():
    """Страница для отладки статических файлов"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Static Files</title>
        <link rel="stylesheet" href="/static/style.css">
        <style>
            .test-red { color: red; font-size: 24px; }
            .test-blue { color: blue; font-size: 24px; background: #f0f0f0; padding: 20px; }
        </style>
    </head>
    <body>
        <h1 class="test-red">Если красный - встроенный CSS работает</h1>
        <h1 class="test-blue">Если синий - встроенный CSS работает</h1>
        <h1 style="color: green;">Если зеленый - inline стили работают</h1>
        
        <h2>Проверка внешнего CSS:</h2>
        <div class="kpi-card">
            <h3>Тест KPI карточки</h3>
            <div class="value">100,000 ₽</div>
        </div>
        
        <script>
            console.log('JavaScript работает');
        </script>
    </body>
    </html>
    '''
@app.route('/api/create-goals-table')
def create_goals_table():
    """Создание таблицы целей (для разработки)"""
    try:
        cursor = db.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                target_value INTEGER DEFAULT 1,
                current_value INTEGER DEFAULT 0,
                progress_percentage INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                category TEXT,
                deadline DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        db.conn.commit()
        
        # Добавляем тестовые цели
        db.add_sample_goals()
        
        return jsonify({
            'success': True,
            'message': 'Таблица целей создана и заполнена тестовыми данными'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
if __name__ == '__main__':
    app.run(debug=True)