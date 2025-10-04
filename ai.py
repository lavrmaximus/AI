import g4f
import re
from typing import Dict, List, Tuple

g4f.debug.logging = False

# Глобальная память
conversation_memory = {}

# Промпты для разных типов сообщений
BUSINESS_ANALYSIS_PROMPT = """Ты - бизнес-аналитик. Твоя задача - ИЗВЛЕЧЬ ЦИФРЫ из текста.

Отвечай ТОЛЬКО в этом формате, БЕЗ ЛИШНИХ СЛОВ:

ВЫРУЧКА: 45000000
РАСХОДЫ: 38000000
ПРИБЫЛЬ: 7000000
КЛИЕНТЫ: 15
СРЕДНИЙ_ЧЕК: 3000000
ИНВЕСТИЦИИ: 10000000
ОЦЕНКА: 8

Если цифры не указаны - ставь 0.

НИКАКИХ комментариев, НИКАКИХ объяснений - ТОЛЬКО ЦИФРЫ в указанном формате."""

QUESTION_ANSWER_PROMPT = """Ты - опытный бизнес-консультант. Отвечай на вопросы развернуто и профессионально, но понятным языком. Используй примеры и практические кейсы."""

GENERAL_CHAT_PROMPT = """Ты - дружелюбный помощник для предпринимателей. Поддержи беседу и мягко направляй разговор в сторону бизнес-анализа."""

def detect_message_type(text: str) -> str:
    """Определяет тип сообщения"""
    text_lower = text.lower()
    
    # Бизнес-аналитика (цифры + бизнес-слова)
    business_words = ['выручка', 'доход', 'прибыль', 'расход', 'затрат', 'клиент', 'продаж', 
                     'заказ', 'чек', 'инвестиц', 'рентабельность', 'оборот', 'актив', 'капитал']
    has_numbers = bool(re.search(r'\d', text))
    has_business_words = any(word in text_lower for word in business_words)
    
    if has_numbers and has_business_words:
        return "business_analysis"
    
    # Вопросы
    question_words = ['как', 'что', 'почему', 'зачем', 'когда', 'где', 'кто', 'чем', '?']
    if any(word in text_lower for word in question_words):
        return "question"
    
    # Общий чат
    return "general"

def analyze_business(description: str, user_id: str = "default") -> Dict:
    """Расширенный анализ бизнеса с финансовыми метриками"""
    
    if user_id not in conversation_memory:
        conversation_memory[user_id] = [
            {"role": "system", "content": BUSINESS_ANALYSIS_PROMPT}
        ]
    
    messages = conversation_memory[user_id]
    messages.append({"role": "user", "content": description})
    
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4,
            messages=messages,
            stream=False
        )
        
        messages.append({"role": "assistant", "content": response})
        
        # Ограничиваем историю
        if len(messages) > 12:
            conversation_memory[user_id] = [messages[0]] + messages[-10:]
        
        return parse_business_response(response)
        
    except Exception as e:
        return {"error": str(e), "type": "business_analysis"}

def answer_question(question: str, user_id: str = "default") -> str:
    """Ответ на вопрос о бизнесе"""
    
    if user_id not in conversation_memory:
        conversation_memory[user_id] = [
            {"role": "system", "content": QUESTION_ANSWER_PROMPT}
        ]
    
    messages = conversation_memory[user_id]
    messages.append({"role": "user", "content": question})
    
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4,
            messages=messages,
            stream=False
        )
        
        messages.append({"role": "assistant", "content": response})
        
        if len(messages) > 12:
            conversation_memory[user_id] = [messages[0]] + messages[-10:]
        
        return response
        
    except Exception as e:
        return f"Извините, произошла ошибка: {str(e)}"

def general_chat(message: str, user_id: str = "default") -> str:
    """Общий разговор"""
    
    if user_id not in conversation_memory:
        conversation_memory[user_id] = [
            {"role": "system", "content": GENERAL_CHAT_PROMPT}
        ]
    
    messages = conversation_memory[user_id]
    messages.append({"role": "user", "content": message})
    
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4,
            messages=messages,
            stream=False
        )
        
        messages.append({"role": "assistant", "content": response})
        
        if len(messages) > 10:
            conversation_memory[user_id] = [messages[0]] + messages[-8:]
        
        return response
        
    except Exception as e:
        return "Привет! Расскажите о своем бизнесе - помогу с анализом!"

def parse_business_response(text: str) -> Dict:
    """Парсим расширенный бизнес-анализ"""
    
    data = {
        "ВЫРУЧКА": 0, "РАСХОДЫ": 0, "ПРИБЫЛЬ": 0, 
        "КЛИЕНТЫ": 0, "СРЕДНИЙ_ЧЕК": 0, "ИНВЕСТИЦИИ": 0,
        "ОЦЕНКА": 0, "РОЕНТАБЕЛЬНОСТЬ": 0, "ТОЧКА_БЕЗУБЫТОЧНОСТИ": 0,
        "ЗАПАС_ПРОЧНОСТИ": 0, "КОММЕНТАРИЙ": "", "СОВЕТЫ": [],
        "type": "business_analysis"
    }
    
    # Парсим базовые цифры
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        for key in data:
            if line.startswith(key + ":"):
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    data[key] = float(numbers[0])
    
    # Парсим аналитику и советы
    sections = text.split('\n\n')
    for section in sections:
        if "КОММЕНТАРИЙ:" in section:
            data["КОММЕНТАРИЙ"] = section.split("КОММЕНТАРИЙ:")[1].strip()
        elif "СОВЕТЫ:" in section:
            advice_lines = section.split('\n')[1:]
            data["СОВЕТЫ"] = [line.strip().lstrip('123456789. -') 
                            for line in advice_lines if line.strip()]
        elif "АНАЛИТИКА:" in section:
            # Извлекаем метрики из аналитики
            analytics_text = section.split("АНАЛИТИКА:")[1]
            # Можно добавить парсинг конкретных метрик если AI их указал
    
    return data

def calculate_financial_metrics(data: Dict) -> Dict:
    """Дополнительные расчеты метрик"""
    try:
        # Рентабельность
        if data["ВЫРУЧКА"] > 0:
            data["РОЕНТАБЕЛЬНОСТЬ"] = (data["ПРИБЫЛЬ"] / data["ВЫРУЧКА"]) * 100
        
        # Простая точка безубыточности (если есть постоянные расходы)
        if data["РАСХОДЫ"] > 0 and data["СРЕДНИЙ_ЧЕК"] > 0:
            data["ТОЧКА_БЕЗУБЫТОЧНОСТИ"] = data["РАСХОДЫ"] / data["СРЕДНИЙ_ЧЕК"]
        
        return data
    except:
        return data

def calculate_advanced_metrics(business_data: Dict) -> Dict:
    """Расчет продвинутых финансовых метрик"""
    
    metrics = {}
    
    try:
        # 1. Рентабельность продаж
        if business_data["ВЫРУЧКА"] > 0:
            metrics["РОЕНТАБЕЛЬНОСТЬ"] = (business_data["ПРИБЫЛЬ"] / business_data["ВЫРУЧКА"]) * 100
        
        # 2. Точка безубыточности (упрощенная)
        if business_data["СРЕДНИЙ_ЧЕК"] > 0 and business_data["РАСХОДЫ"] > 0:
            metrics["ТОЧКА_БЕЗУБЫТОЧНОСТИ"] = business_data["РАСХОДЫ"] / business_data["СРЕДНИЙ_ЧЕК"]
        
        # 3. Запас финансовой прочности
        if business_data["ВЫРУЧКА"] > 0 and metrics.get("ТОЧКА_БЕЗУБЫТОЧНОСТИ", 0) > 0:
            break_even_revenue = metrics["ТОЧКА_БЕЗУБЫТОЧНОСТИ"] * business_data["СРЕДНИЙ_ЧЕК"]
            if break_even_revenue > 0:
                metrics["ЗАПАС_ПРОЧНОСТИ"] = ((business_data["ВЫРУЧКА"] - break_even_revenue) / business_data["ВЫРУЧКА"]) * 100
        
        # 4. Оборачиваемость (если есть данные о запасах/активах)
        # Пока пропускаем - нужно больше данных
        
        # 5. Оценка по упрощенной формуле Альтмана для малого бизнеса
        # Z = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4 + 0.998*X5
        # Пока пропускаем - нужно больше данных о балансе
        
        # 6. Коэффициент устойчивости роста (SGR)
        if business_data["ПРИБЫЛЬ"] > 0 and business_data["ИНВЕСТИЦИИ"] > 0:
            # Предполагаем, что 50% прибыли реинвестируется
            roe = (business_data["ПРИБЫЛЬ"] / business_data["ИНВЕСТИЦИИ"]) * 100
            metrics["SGR"] = roe * 0.5  # 50% реинвестиций
        
        # 7. Индекс прибыльности (PI)
        if business_data["ИНВЕСТИЦИИ"] > 0:
            # Предполагаем годовую прибыль как ежемесячную * 12
            annual_profit = business_data["ПРИБЫЛЬ"] * 12
            metrics["ИНДЕКС_ПРИБЫЛЬНОСТИ"] = annual_profit / business_data["ИНВЕСТИЦИИ"]
        
        return metrics
        
    except Exception as e:
        print(f"Ошибка расчета метрик: {e}")
        return {}

def enhance_business_prompt_with_metrics(business_data: Dict, calculated_metrics: Dict) -> str:
    """Улучшаем промпт с рассчитанными метриками"""
    
    metrics_text = "РАССЧИТАННЫЕ МЕТРИКИ:\n"
    
    if calculated_metrics.get("РОЕНТАБЕЛЬНОСТЬ"):
        metrics_text += f"• Рентабельность: {calculated_metrics['РОЕНТАБЕЛЬНОСТИ']:.1f}%\n"
    
    if calculated_metrics.get("ТОЧКА_БЕЗУБЫТОЧНОСТИ"):
        metrics_text += f"• Точка безубыточности: {calculated_metrics['ТОЧКА_БЕЗУБЫТОЧНОСТИ']:.0f} клиентов\n"
    
    if calculated_metrics.get("ЗАПАС_ПРОЧНОСТИ"):
        metrics_text += f"• Запас прочности: {calculated_metrics['ЗАПАС_ПРОЧНОСТИ']:.1f}%\n"
    
    if calculated_metrics.get("SGR"):
        metrics_text += f"• Макс. устойчивый рост: {calculated_metrics['SGR']:.1f}%\n"
    
    if calculated_metrics.get("ИНДЕКС_ПРИБЫЛЬНОСТИ"):
        pi = calculated_metrics["ИНДЕКС_ПРИБЫЛЬНОСТИ"]
        pi_emoji = "🚀" if pi > 1.5 else "✅" if pi > 1.0 else "⚠️"
        metrics_text += f"• Индекс прибыльности: {pi:.2f} {pi_emoji}\n"
    
    enhanced_prompt = f"""
{business_data.get('КОММЕНТАРИЙ', '')}

{metrics_text}

Используй эти рассчитанные метрики в своем анализе. Дай оценку бизнесу от 1 до 10 и 3 конкретных совета.
    """
    
    return enhanced_prompt

# Тестирование
if __name__ == "__main__":
    print("🧠 Тестируем улучшенный AI...")
    
    # Тест бизнес-анализа
    test_business = "Кофейня: выручка 500к в месяц, 30 клиентов в день, расходы 200к"
    result = analyze_business(test_business)
    print("Бизнес-анализ:", result)
    
    # Тест вопроса
    test_question = "Как увеличить прибыль в розничном магазине?"
    result = answer_question(test_question)
    print("Ответ на вопрос:", result[:100] + "...")