from flask import Flask, render_template, request, jsonify
import sqlite3
import json
from datetime import datetime, timedelta
import math
import asyncio
import os

from database import db as async_db

app = Flask(__name__)

# Инициализируем новую БД (async) один раз при старте процесса
_event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_event_loop)
try:
    _event_loop.run_until_complete(async_db.init_db())
except Exception as e:
    print(f"Ошибка инициализации новой БД: {e}")

def await_db(coro):
    """Выполнить async-вызов к БД в синхронном Flask обработчике."""
    return _event_loop.run_until_complete(coro)

def get_new_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'business_bot_v2.db')

# Подготовка данных для 22+ метрик на основе снимков новой БД
def prepare_multi_metric_data(snapshots):
    # Отсортируем по дате по возрастанию для фронтенда
    snapshots_sorted = sorted(snapshots, key=lambda s: s.get('period_date') or s.get('created_at'))
    dates = [s.get('period_date') or str(s.get('created_at'))[:10] for s in snapshots_sorted]
    metric_keys = [
        'revenue', 'expenses', 'profit', 'clients', 'average_check', 'investments', 'marketing_costs', 'employees',
        'profit_margin', 'break_even_clients', 'safety_margin', 'roi', 'profitability_index',
        'ltv', 'cac', 'ltv_cac_ratio', 'customer_profit_margin', 'sgr', 'revenue_growth_rate',
        'asset_turnover', 'roe', 'months_to_bankruptcy',
        'financial_health_score', 'growth_health_score', 'efficiency_health_score', 'overall_health_score'
    ]
    series = {k: [float(s.get(k) or 0) for s in snapshots_sorted] for k in metric_keys}
    return {'dates': dates, 'series': series}

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

# Новый API: список бизнесов пользователя
@app.route('/api/businesses/<user_id>')
def get_businesses(user_id):
    try:
        businesses = await_db(async_db.get_user_businesses(user_id))
        return jsonify({'success': True, 'businesses': businesses})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Новый API: история снимков по бизнесу (включая все метрики)
@app.route('/api/business-history/<int:business_id>')
def get_business_history(business_id):
    try:
        snapshots = await_db(async_db.get_business_history(business_id, limit=120))
        data = prepare_multi_metric_data(snapshots)
        latest = snapshots[-1] if snapshots else None
        return jsonify({'success': True, 'data': data, 'latest': latest})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Упрощённый endpoint полноэкранного графика (используем фронтенд для построения)
@app.route('/api/fullscreen-chart/<int:business_id>')
def get_fullscreen_chart(business_id):
    try:
        snapshots = await_db(async_db.get_business_history(business_id, limit=180))
        data = prepare_multi_metric_data(snapshots)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint для KPI метрик по бизнесу (на основе новой схемы)
@app.route('/api/business-kpi/<int:business_id>')
def get_business_kpi(business_id):
    try:
        snapshots = await_db(async_db.get_business_history(business_id, limit=2))
        if not snapshots:
            return jsonify({'success': False, 'error': 'Нет данных'}), 404
        latest = snapshots[0]
        previous = snapshots[1] if len(snapshots) > 1 else None
        def calc_change(curr, prev):
            prev = float(prev or 0)
            curr = float(curr or 0)
            if prev > 0:
                return round(((curr - prev) / prev) * 100, 1)
            return 0
        kpi = {
            'revenue': {'current': float(latest.get('revenue') or 0), 'change': calc_change(latest.get('revenue'), previous.get('revenue') if previous else 0)},
            'expenses': {'current': float(latest.get('expenses') or 0), 'change': calc_change(latest.get('expenses'), previous.get('expenses') if previous else 0)},
            'profit': {'current': float(latest.get('profit') or 0), 'change': calc_change(latest.get('profit'), previous.get('profit') if previous else 0)},
            'clients': {'current': int(latest.get('clients') or 0), 'change': calc_change(latest.get('clients'), previous.get('clients') if previous else 0)},
            'average_check': float(latest.get('average_check') or 0),
            'overall_health_score': int(latest.get('overall_health_score') or 0)
        }
        return jsonify({'success': True, 'kpi': kpi})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint для анализа от ИИ (оставляем, но используем новую БД по первому бизнесу)
@app.route('/api/user-ai-analysis/<user_id>')
def get_user_ai_analysis(user_id):
    try:
        businesses = await_db(async_db.get_user_businesses(user_id))
        if not businesses:
            return jsonify({
                'success': False,
                'error': 'Данные не найдены. Выберите профиль с данными.'
            }), 404
        business_id = businesses[0]['business_id']
        snapshots = await_db(async_db.get_business_history(business_id, limit=12))
        if not snapshots:
            return jsonify({'success': False, 'error': 'Нет данных'}), 404
        latest = snapshots[0]
        analysis_data = generate_ai_analysis(latest, snapshots)
        
        return jsonify({
            'success': True,
            'analysis': analysis_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API endpoint для анализа от ИИ по конкретному бизнесу
@app.route('/api/business-ai-analysis/<int:business_id>')
def get_business_ai_analysis(business_id):
    try:
        snapshots = await_db(async_db.get_business_history(business_id, limit=12))
        if not snapshots:
            return jsonify({'success': False, 'error': 'Нет данных'}), 404
        latest = snapshots[0]
        analysis_data = generate_ai_analysis(latest, snapshots)
        
        return jsonify({
            'success': True,
            'analysis': analysis_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API endpoint для списка пользователей (читаем из новой БД напрямую)
@app.route('/api/users')
def get_users():
    try:
        conn = sqlite3.connect(get_new_db_path())
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, first_name, last_name FROM users')
        rows = cursor.fetchall()
        users = [{
            'id': row[0],
            'name': f"{row[2]} {row[3]}".strip() if (row[2] or row[3]) else (row[1] or f"User {row[0]}")
        } for row in rows]
        conn.close()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint для системной статистики (простая версия по новой схеме)
@app.route('/api/system-stats')
def get_system_stats():
    try:
        conn = sqlite3.connect(get_new_db_path())
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM businesses WHERE is_active = TRUE')
        total_businesses = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM business_snapshots WHERE DATE(created_at) = DATE("now")')
        active_today = cursor.fetchone()[0]
        conn.close()
        return jsonify({'success': True, 'stats': {
            'total_users': total_users,
            'total_analyses': total_businesses,
            'active_today': active_today
        }})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'stats': {'total_users': 0, 'total_analyses': 0, 'active_today': 0}}), 500

def generate_ai_analysis(latest_data, history_data):
    """Генерация AI анализа на основе данных из БД"""
    
    revenue = float(latest_data.get('revenue') or 0)
    expenses = float(latest_data.get('expenses') or 0)
    profit = float(latest_data.get('profit') or 0)
    clients = int(latest_data.get('clients') or 0)
    avg_check = float(latest_data.get('average_check') or 0)
    rating = int((latest_data.get('overall_health_score') or 0) / 10)
    
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
        prev_revenue = float(previous.get('revenue') or 0)
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
        'commentary': ''
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