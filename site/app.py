from flask import Flask, render_template, request, session, redirect, url_for
import math

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Замените на случайный ключ

# Простая база данных (в реальном приложении используйте SQLite/PostgreSQL)
food_db = {
    'яблоко': 52, 'банан': 89, 'апельсин': 47, 'куриная грудка': 165,
    'рис': 130, 'овсянка': 68, 'яйцо': 78, 'хлеб': 265,
    'молоко': 42, 'йогурт': 59, 'сыр': 402, 'говядина': 250,
    'лосось': 208, 'картофель': 77, 'морковь': 41, 'брокколи': 34
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['GET', 'POST'])
def calculate():
    if request.method == 'POST':
        # Получаем данные из формы
        age = int(request.form.get('age', 0))
        weight = float(request.form.get('weight', 0))
        height = float(request.form.get('height', 0))
        gender = request.form.get('gender', 'male')
        activity = request.form.get('activity', 'sedentary')
        goal = request.form.get('goal', 'maintain')
        
        # Сохраняем в сессию
        session['user_data'] = {
            'age': age, 'weight': weight, 'height': height,
            'gender': gender, 'activity': activity, 'goal': goal
        }
        
        # Рассчитываем калории
        calories = calculate_calories(age, weight, height, gender, activity, goal)
        session['daily_calories'] = calories
        
        return render_template('calculate.html', calories=calories, food_db=food_db)
    
    return render_template('calculate.html')

@app.route('/add_food', methods=['POST'])
def add_food():
    food = request.form.get('food')
    quantity = float(request.form.get('quantity', 1))
    
    if food in food_db:
        calories = food_db[food] * quantity
        # Сохраняем в сессию
        if 'foods_eaten' not in session:
            session['foods_eaten'] = []
        
        session['foods_eaten'].append({
            'food': food,
            'quantity': quantity,
            'calories': calories
        })
        
        # Обновляем общее количество калорий
        total_eaten = sum(item['calories'] for item in session['foods_eaten'])
        session['total_eaten'] = total_eaten
        
    return redirect(url_for('calculate'))

@app.route('/clear_foods')
def clear_foods():
    session.pop('foods_eaten', None)
    session.pop('total_eaten', None)
    return redirect(url_for('calculate'))

@app.route('/tips')
def tips():
    calories = session.get('daily_calories', 2000)
    return render_template('tips.html', calories=calories)

def calculate_calories(age, weight, height, gender, activity, goal):
    # Формула Миффлина-Сан Жеора
    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Умножаем на коэффициент активности
    activity_multipliers = {
        'sedentary': 1.2,      # Сидячий образ жизни
        'light': 1.375,        # Легкая активность
        'moderate': 1.55,      # Умеренная активность
        'active': 1.725,       # Активный образ жизни
        'very_active': 1.9     # Очень активный
    }
    
    maintenance_calories = bmr * activity_multipliers.get(activity, 1.2)
    
    # Корректируем в зависимости от цели
    goal_adjustments = {
        'lose': -500,      # Похудение
        'maintain': 0,     # Поддержание веса
        'gain': 500        # Набор массы
    }
    
    return math.floor(maintenance_calories + goal_adjustments.get(goal, 0))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)