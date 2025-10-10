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
            print("SQLite база данных подключена и таблицы созданы")
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
    
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
        
        self.conn.commit()

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
            print(f"Ошибка получения бизнес-данных: {e}")
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
                'error': 'Данные не найдены. Выберите пользователя с данными.'
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
                'error': 'Данные не найдены. Выберите пользователя с данными.'
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
                'error': 'Данные не найдены. Выберите пользователя с данными.'
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
        'summary': f" Ваш бизнес показывает {profit_status} рентабельность ({profitability:.1f}%). Выручка: {revenue:,.0f} руб., Прибыль: {profit:,.0f} руб.",
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
    </head>
    <body>
        <h1 style="color: white;">Тест темной темы</h1>
        <div class="kpi-card">
            <h3>Тест KPI карточки</h3>
            <div class="value">100,000 ₽</div>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)