from flask import Flask, render_template, request, jsonify
import sqlite3
import json
from datetime import datetime, timedelta
import math

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
        """Получение истории бизнес-анализов профилей"""
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
        """Получение списка профилей"""
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
            print(f"Ошибка получения профилей: {e}")
            return []

    def get_system_stats(self):
        """Получение системной статистики"""
        try:
            cursor = self.conn.cursor()
            
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            # Общее количество анализов
            cursor.execute('SELECT COUNT(*) FROM business_analyses')
            total_analyses = cursor.fetchone()[0]
            
            # Активные сегодня (пользователи с анализами за сегодня)
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) 
                FROM business_analyses 
                WHERE DATE(created_at) = DATE('now')
            ''')
            active_today = cursor.fetchone()[0]
            
            return {
                'total_users': total_users,
                'total_analyses': total_analyses,
                'active_today': active_today
            }
            
        except Exception as e:
            print(f"Ошибка получения статистики системы: {e}")
            return {'total_users': 0, 'total_analyses': 0, 'active_today': 0}

# Класс для рендеринга графиков
class ChartRenderer:
    def __init__(self):
        self.chart_colors = {
            'revenue': {'border': '#48bb78', 'background': 'rgba(72, 187, 120, 0.1)'},
            'expenses': {'border': '#f56565', 'background': 'rgba(245, 101, 101, 0.1)'},
            'profit': {'border': '#4299e1', 'background': 'rgba(66, 153, 225, 0.1)'}
        }
    
    def generate_chart_config(self, data, is_mobile=False, is_fullscreen=False):
        """Генерация конфигурации для Chart.js"""
        if not data or not data.get('dates'):
            return self._get_empty_chart_config()
        
        chart_config = {
            'type': 'line',
            'data': {
                'labels': data['dates'],
                'datasets': self._generate_datasets(data, is_mobile, is_fullscreen)
            },
            'options': self._generate_chart_options(is_mobile, is_fullscreen)
        }
        
        return chart_config
    
    def _generate_datasets(self, data, is_mobile, is_fullscreen):
        """Генерация datasets для графика"""
        datasets = []
        
        datasets_config = [
            ('revenue', 'Выручка', data.get('revenue', [])),
            ('expenses', 'Расходы', data.get('expenses', [])),
            ('profit', 'Прибыль', data.get('profit', []))
        ]
        
        for key, label, values in datasets_config:
            border_width = 3
            point_radius = 4
            point_hover_radius = 6
            
            if is_mobile:
                border_width = 2
                point_radius = 3
                point_hover_radius = 5
            
            if is_fullscreen:
                border_width = 4
                point_radius = 5
                point_hover_radius = 8
            
            datasets.append({
                'label': label,
                'data': values,
                'borderColor': self.chart_colors[key]['border'],
                'backgroundColor': self.chart_colors[key]['background'],
                'borderWidth': border_width,
                'tension': 0.4,
                'fill': True,
                'pointRadius': point_radius,
                'pointHoverRadius': point_hover_radius,
                'pointBorderWidth': 2
            })
        
        return datasets
    
    def _generate_chart_options(self, is_mobile, is_fullscreen):
        """Генерация опций для Chart.js"""
        font_sizes = self._get_font_sizes(is_mobile, is_fullscreen)
        
        options = {
            'responsive': False,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'position': 'top',
                    'labels': {
                        'boxWidth': 15,
                        'font': {
                            'size': font_sizes['legend']
                        },
                        'padding': 20,
                        'usePointStyle': True
                    }
                },
                'title': {
                    'display': True,
                    'text': 'Финансовая динамика' + (' - Полноэкранный режим' if is_fullscreen else ''),
                    'font': {
                        'size': font_sizes['title']
                    },
                    'padding': 20
                },
                'tooltip': {
                    'bodyFont': {
                        'size': font_sizes['tooltip_body']
                    },
                    'titleFont': {
                        'size': font_sizes['tooltip_title']
                    },
                    'padding': 12,
                    'backgroundColor': 'rgba(26, 32, 44, 0.95)',
                    'titleColor': '#fff',
                    'bodyColor': '#fff',
                    'borderColor': '#d400ff',
                    'borderWidth': 1
                }
            },
            'scales': {
                'y': {
                    'beginAtZero': True,
                    'ticks': {
                        'callback': 'function(value) { return window.formatChartCurrency(value); }',
                        'font': {
                            'size': font_sizes['y_ticks']
                        },
                        'padding': 10
                    },
                    'grid': {
                        'color': 'rgba(255,255,255,0.1)'
                    },
                    'title': {
                        'display': True,
                        'text': 'Сумма (руб)',
                        'font': {
                            'size': font_sizes['axis_title']
                        }
                    }
                },
                'x': {
                    'ticks': {
                        'font': {
                            'size': font_sizes['x_ticks']
                        },
                        'maxTicksLimit': 20,
                        'padding': 10
                    },
                    'grid': {
                        'color': 'rgba(255,255,255,0.1)'
                    },
                    'title': {
                        'display': True,
                        'text': 'Дата',
                        'font': {
                            'size': font_sizes['axis_title']
                        }
                    }
                }
            },
            'interaction': {
                'intersect': False,
                'mode': 'index'
            },
            'elements': {
                'point': {
                    'radius': font_sizes['point_radius'],
                    'hoverRadius': font_sizes['point_hover_radius']
                }
            },
            'layout': {
                'padding': {
                    'left': 20,
                    'right': 20,
                    'top': 20,
                    'bottom': 20
                }
            }
        }
        
        return options
    
    def _get_font_sizes(self, is_mobile, is_fullscreen):
        """Получение размеров шрифтов в зависимости от платформы"""
        if is_fullscreen:
            return {
                'legend': 16, 'title': 20, 'tooltip_body': 14, 'tooltip_title': 16,
                'y_ticks': 14, 'x_ticks': 12, 'axis_title': 16,
                'point_radius': 4, 'point_hover_radius': 8
            }
        elif is_mobile:
            return {
                'legend': 12, 'title': 16, 'tooltip_body': 12, 'tooltip_title': 13,
                'y_ticks': 11, 'x_ticks': 10, 'axis_title': 12,
                'point_radius': 3, 'point_hover_radius': 5
            }
        else:
            return {
                'legend': 14, 'title': 18, 'tooltip_body': 14, 'tooltip_title': 15,
                'y_ticks': 13, 'x_ticks': 12, 'axis_title': 14,
                'point_radius': 4, 'point_hover_radius': 6
            }
    
    def _get_empty_chart_config(self):
        """Конфигурация для пустого графика"""
        return {
            'type': 'line',
            'data': {
                'labels': [],
                'datasets': []
            },
            'options': {
                'responsive': False,
                'maintainAspectRatio': False,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': 'Нет данных для отображения'
                    }
                }
            }
        }
    
    def calculate_chart_dimensions(self, data_points_count):
        """Расчет размеров графика на основе количества точек данных"""
        min_width = 600
        point_width = 50
        calculated_width = max(min_width, data_points_count * point_width)
        
        return {
            'width': calculated_width,
            'height': 300
        }

# Инициализируем базу данных и рендерер
db = SyncDatabase()
chart_renderer = ChartRenderer()

# Вспомогательные функции для подготовки данных
def prepare_chart_data(business_data):
    """Подготовка данных для графика"""
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
    
    return {
        'dates': dates,
        'revenue': revenue,
        'expenses': expenses,
        'profit': profit,
        'clients': clients
    }

def get_data_summary(chart_data):
    """Получение сводки по данным"""
    if not chart_data or not chart_data['revenue']:
        return {}
    
    revenue = chart_data['revenue']
    expenses = chart_data['expenses']
    profit = chart_data['profit']
    
    return {
        'total_revenue': sum(revenue),
        'total_expenses': sum(expenses),
        'total_profit': sum(profit),
        'avg_revenue': sum(revenue) / len(revenue) if revenue else 0,
        'data_points': len(chart_data['dates'])
    }

def get_period_info(dates):
    """Получение информации о периоде"""
    if not dates:
        return "Нет данных"
    
    if len(dates) == 1:
        return dates[0]
    else:
        return f"{dates[-1]} - {dates[0]}"

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

# API endpoint для получения финансовых данных профиля
@app.route('/api/user-finance-data/<user_id>')
def get_user_finance_data(user_id):
    try:
        business_data = db.get_user_business_data(user_id)
        
        if not business_data:
            return jsonify({
                'success': False,
                'error': 'Данные не найдены. Выберите профиль с данными.'
            }), 404
        
        # Преобразуем данные для графиков
        chart_data = prepare_chart_data(business_data)
        
        # Генерируем конфигурацию графика
        is_mobile = request.headers.get('User-Agent', '').lower()
        is_mobile = 'mobile' in is_mobile or 'android' in is_mobile or 'iphone' in is_mobile
        
        chart_config = chart_renderer.generate_chart_config(chart_data, is_mobile=is_mobile)
        dimensions = chart_renderer.calculate_chart_dimensions(len(chart_data['dates']))
        
        return jsonify({
            'success': True,
            'data': chart_data,
            'latest': business_data[0] if business_data else None,
            'chart_config': chart_config,
            'dimensions': dimensions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Новый endpoint для полноэкранного графика
@app.route('/api/fullscreen-chart/<user_id>')
def get_fullscreen_chart(user_id):
    try:
        business_data = db.get_user_business_data(user_id)
        
        if not business_data:
            return jsonify({
                'success': True,
                'chart_config': chart_renderer._get_empty_chart_config(),
                'dimensions': {'width': 800, 'height': 400}
            })
        
        chart_data = prepare_chart_data(business_data)
        chart_config = chart_renderer.generate_chart_config(chart_data, is_fullscreen=True)
        
        dimensions = chart_renderer.calculate_chart_dimensions(len(chart_data['dates']))
        dimensions['width'] = 1200
        dimensions['height'] = 500
        
        return jsonify({
            'success': True,
            'chart_config': chart_config,
            'dimensions': dimensions,
            'period_info': get_period_info(chart_data['dates'])
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API endpoint для KPI метрик профиля
@app.route('/api/user-kpi-metrics/<user_id>')
def get_user_kpi_metrics(user_id):
    try:
        business_data = db.get_user_business_data(user_id)
        
        if not business_data:
            return jsonify({
                'success': False,
                'error': 'Данные не найдены. Выберите профиль с данными.'
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
                'error': 'Данные не найдены. Выберите профиль с данными.'
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

# API endpoint для системной статистики
@app.route('/api/system-stats')
def get_system_stats():
    try:
        stats = db.get_system_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {'total_users': 0, 'total_analyses': 0, 'active_today': 0}
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

# Страница для отладки
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