import g4f
import re
import logging
from typing import Dict, List, Tuple
from database import db

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

g4f.debug.logging = False

# Глобальная память (теперь дублируется в базе данных)
conversation_memory = {}

# Умный промпт для классификации сообщений
MESSAGE_CLASSIFIER_PROMPT = """Проанализируй сообщение пользователя и определи его тип:

1. BUSINESS_ANALYSIS - если пользователь описывает бизнес с цифрами (выручка, расходы, клиенты, прибыль и т.д.)
2. BUSINESS_QUESTION - если пользователь задает вопрос о бизнесе, финансах, предпринимательстве
3. GENERAL_CHAT - если это приветствие, общение или сообщение не связано с бизнесом

Отвечай ТОЛЬКО одним словом: BUSINESS_ANALYSIS, BUSINESS_QUESTION или GENERAL_CHAT.

Примеры:
- "Выручка 500к, расходы 200к" -> BUSINESS_ANALYSIS
- "Как увеличить прибыль?" -> BUSINESS_QUESTION  
- "Привет, как дела?" -> GENERAL_CHAT
- "Спасибо за помощь" -> GENERAL_CHAT"""

BUSINESS_ANALYSIS_PROMPT = """Ты - профессиональный бизнес-аналитик. Твоя задача - ИЗВЛЕЧЬ ЦИФРЫ из текста и дать краткий анализ.

Отвечай ТОЛЬКО в этом формате, БЕЗ ЛИШНИХ СЛОВ:

ВЫРУЧКА: 45000000
РАСХОДЫ: 38000000
ПРИБЫЛЬ: 7000000
КЛИЕНТЫ: 15
СРЕДНИЙ_ЧЕК: 3000000
ИНВЕСТИЦИИ: 10000000
ОЦЕНКА: 8
КОММЕНТАРИЙ: Ваш бизнес показывает хорошую рентабельность. Рекомендую оптимизировать расходы.
СОВЕТЫ: 1. Снизить операционные расходы|2. Увеличить средний чек|3. Привлечь больше клиентов

Если цифры не указаны - ставь 0.
НИКАКИХ комментариев кроме указанных полей."""

QUESTION_ANSWER_PROMPT = """Ты - опытный бизнес-консультант с 10-летним опытом. Отвечай на вопросы развернуто, профессионально, но понятным языком. Используй практические кейсы и конкретные примеры. Будь полезным и поддерживающим."""

GENERAL_CHAT_PROMPT = """Ты - дружелюбный помощник для предпринимателей. Поддержи беседу, будь позитивным и полезным. Мягко направляй разговор в сторону бизнес-анализа, если это уместно."""

async def classify_message_type(text: str) -> str:
    """Умное определение типа сообщения с помощью AI"""
    try:
        messages = [
            {"role": "system", "content": MESSAGE_CLASSIFIER_PROMPT},
            {"role": "user", "content": text}
        ]
        
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4,
            messages=messages,
            stream=False
        )
        
        response = response.strip().upper()
        
        if "BUSINESS_ANALYSIS" in response:
            return "business_analysis"
        elif "BUSINESS_QUESTION" in response:
            return "question"
        else:
            return "general"
            
    except Exception as e:
        logger.error(f"Ошибка классификации сообщения: {e}")
        # Fallback на простое определение
        return simple_detect_message_type(text)

def simple_detect_message_type(text: str) -> str:
    """Простое определение типа сообщения (fallback)"""
    text_lower = text.lower()
    
    # Бизнес-аналитика (цифры + бизнес-слова)
    business_words = ['выручка', 'доход', 'прибыль', 'расход', 'затрат', 'клиент', 'продаж', 
                     'заказ', 'чек', 'инвестиц', 'рентабельность', 'оборот', 'актив', 'капитал',
                     'бизнес', 'компания', 'предприятие', 'предприниматель']
    has_numbers = bool(re.search(r'\d', text))
    has_business_words = any(word in text_lower for word in business_words)
    
    if has_numbers and has_business_words:
        return "business_analysis"
    
    # Вопросы
    question_words = ['как', 'что', 'почему', 'зачем', 'когда', 'где', 'кто', 'чем', '?']
    business_questions = ['увелич', 'улучш', 'оптимиз', 'развит', 'проблем', 'совет', 'рекомендац']
    
    is_question = any(word in text_lower for word in question_words)
    is_business_question = any(word in text_lower for word in business_questions)
    
    if is_question and is_business_question:
        return "question"
    
    # Общий чат
    return "general"

async def analyze_business(description: str, user_id: str = "default") -> Dict:
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
        
        parsed_data = parse_business_response(response)
        
        # Сохраняем в базу данных
        await db.save_business_analysis(user_id, parsed_data)
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Ошибка бизнес-анализа: {e}")
        return {"error": str(e), "type": "business_analysis"}

async def answer_question(question: str, user_id: str = "default") -> str:
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
        logger.error(f"Ошибка ответа на вопрос: {e}")
        return f"Извините, произошла ошибка: {str(e)}"

async def general_chat(message: str, user_id: str = "default") -> str:
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
        logger.error(f"Ошибка общего чата: {e}")
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
    
    # Парсим комментарий и советы
    if "КОММЕНТАРИЙ:" in text:
        comment_part = text.split("КОММЕНТАРИЙ:")[1]
        if "СОВЕТЫ:" in comment_part:
            data["КОММЕНТАРИЙ"] = comment_part.split("СОВЕТЫ:")[0].strip()
        else:
            data["КОММЕНТАРИЙ"] = comment_part.strip()
    
    if "СОВЕТЫ:" in text:
        advice_part = text.split("СОВЕТЫ:")[1]
        advice_lines = [line.strip() for line in advice_part.split('\n') if line.strip()]
        for line in advice_lines:
            # Убираем нумерацию (1., 2., и т.д.)
            clean_advice = re.sub(r'^\d+\.\s*', '', line).strip()
            if clean_advice and '|' in clean_advice:
                # Разделяем советы по |
                data["СОВЕТЫ"].extend([a.strip() for a in clean_advice.split('|') if a.strip()])
            elif clean_advice:
                data["СОВЕТЫ"].append(clean_advice)
    
    # Ограничиваем количество советов
    data["СОВЕТЫ"] = data["СОВЕТЫ"][:3]
    
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
        
        # 6. Коэффициент устойчивости роста (SGR)
        if business_data["ПРИБЫЛЬ"] > 0 and business_data["ИНВЕСТИЦИИ"] > 0:
            roe = (business_data["ПРИБЫЛЬ"] / business_data["ИНВЕСТИЦИИ"]) * 100
            metrics["SGR"] = roe * 0.5  # 50% реинвестиций
        
        # 7. Индекс прибыльности (PI)
        if business_data["ИНВЕСТИЦИИ"] > 0:
            annual_profit = business_data["ПРИБЫЛЬ"] * 12
            metrics["ИНДЕКС_ПРИБЫЛЬНОСТИ"] = annual_profit / business_data["ИНВЕСТИЦИИ"]
        
        return metrics
        
    except Exception as e:
        logger.error(f"Ошибка расчета метрик: {e}")
        return {}

# Тестирование
if __name__ == "__main__":
    import asyncio
    
    async def test_ai():
        print("🧠 Тестируем улучшенный AI...")
        
        # Тест классификации
        test_messages = [
            "Выручка 500к в месяц, расходы 200к",
            "Как увеличить прибыль?",
            "Привет, как дела?",
            "У меня кофейня, 30 клиентов в день, средний чек 500 рублей"
        ]
        
        for msg in test_messages:
            msg_type = await classify_message_type(msg)
            print(f"Сообщение: '{msg}' -> Тип: {msg_type}")
        
        # Тест бизнес-анализа
        test_business = "Кофейня: выручка 500000 в месяц, 30 клиентов в день, расходы 200000, инвестиции 1000000"
        result = await analyze_business(test_business)
        print("Бизнес-анализ:", result)
        
        # Тест вопроса
        test_question = "Как увеличить прибыль в розничном магазине?"
        result = await answer_question(test_question)
        print("Ответ на вопрос:", result[:100] + "...")
    
    asyncio.run(test_ai())