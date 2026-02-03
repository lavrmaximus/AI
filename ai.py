import g4f
import re
import logging
import asyncio
from typing import Dict, List, Tuple
from database import db

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

g4f.debug.logging = False

# Глобальная память (теперь дублируется в базе данных)
conversation_memory = {}
SIMPLE_MODEL = g4f.models.gpt_4

# Умный промпт для классификации сообщений
MESSAGE_CLASSIFIER_PROMPT = """Ты - классификатор сообщений. Определи тип и верни ТОЛЬКО ОДНО СЛОВО: BUSINESS_DATA или BUSINESS_QUESTION или GENERAL_CHAT.

ПРАВИЛА:
- BUSINESS_DATA: есть цифры и бизнес-слова, речь идет о конкретном бизнесе (выручка, прибыль, клиенты и т.д.)
- BUSINESS_QUESTION: вопрос о бизнесе без конкретных данных (как, почему, что лучше)
- GENERAL_CHAT: все остальное

ВЕРНИ ТОЛЬКО ОДНО СЛОВО!"""

# Новый промпт для извлечения бизнес-данных из свободного текста
BUSINESS_DATA_EXTRACTION_PROMPT = """Ты - инструмент для извлечения бизнес-данных. Извлеки ВСЕ доступные числовые показатели из текста и верни в СТРОГОМ JSON формате.

ЗАПРЕЩЕНО:
- Писать пояснения, комментарии, советы
- Отвечать как обычный чат-бот  
- Использовать свободный текст
- Выдумывать данные если их нет в тексте

ОБЯЗАТЕЛЬНО:
- Вернуть данные ТОЛЬКО в указанном JSON формате
- Если поле не найдено - поставить null
- Все числа преобразовать в числа (15000 вместо 15к)
- Расшифровывать сокращения (к->1000, млн->1000000)

ФОРМТ ВЫВОДА:
{
  "business_name": "название бизнеса или null",
  "revenue": число или null,
  "expenses": число или null,
  "clients": число или null,
  "investments": число или null,
  "marketing_costs": число или null,
  "employees": число или null,
  "monthly_costs": число или null,
  "new_clients_per_month": число или null,
  "customer_retention_rate": число или null
}

Пример:
СООБЩЕНИЕ: "У меня кофейня в центре, выручка 500к в месяц, расходы на аренду и зарплаты 300к, приходит около 1000 клиентов, средний чек 500 рублей"

ОТВЕТ:
{
  "business_name": "кофейня",
  "revenue": 500000,
  "expenses": 300000,
  "clients": 1000,
  "investments": null,
  "marketing_costs": null,
  "employees": null,
  "monthly_costs": 300000,
  "new_clients_per_month": null,
  "customer_retention_rate": null
}

НИКАКИХ ДРУГИХ ТЕКСТОВ КРОМЕ JSON!"""

# Промпт для определения недостающих данных
MISSING_DATA_ANALYSIS_PROMPT = """Ты - бизнес-аналитик, который помогает собрать данные для полного анализа бизнеса.
Твоя задача - определить, каких данных не хватает, и задать 1-2 ЧЕТКИХ, КОНКРЕТНЫХ вопроса, чтобы получить недостающую информацию.
Каждый вопрос должен быть С НОВОЙ СТРОКИ.

ВНИМАТЕЛЬНО ИЗУЧИ УЖЕ СОБРАННЫЕ ДАННЫЕ.
НЕ ЗАДАВАЙ ВОПРОСЫ О ДАННЫХ, КОТОРЫЕ УЖЕ ПРИСУТСТВУЮТ!

Если все необходимы данные собраны (как "ТРЕБУЕМЫЕ ДАННЫЕ", так и "ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ"), то верни ТОЛЬКО ОДНО СЛОВО: ENOUGH_DATA.
Не используй форматирование жирным или курсивом, только обычный текст и вопросы.

УЖЕ СОБРАННЫЕ ДАННЫЕ:
{collected_data}

СПИСОК ВСЕХ ВОЗМОЖНЫХ ДАННЫХ ДЛЯ АНАЛИЗА:
- business_name (название бизнеса)
- revenue (выручка)
- expenses (расходы)
- clients (количество клиентов)
- investments (инвестиции)
- marketing_costs (затраты на маркетинг)
- employees (количество сотрудников)
- monthly_costs (ежемесячные постоянные расходы)
- new_clients_per_month (новых клиентов в месяц)
- customer_retention_rate (коэффициент удержания клиентов в процентах)

ТРЕБУЕМЫЕ ДАННЫЕ (критически важны для минимального анализа):
- business_name (название бизнеса) - ПРИОРИТЕТ #1
- revenue
- expenses
- clients

ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ (для расширенного анализа, спрашивай о них, только если основные уже есть):
- investments
- marketing_costs
- employees
- monthly_costs
- new_clients_per_month
- customer_retention_rate

ВАЖНО: НЕ СПРАШИВАЙ О ДАННЫХ, КОТОРЫЕ МОЖНО ВЫЧИСЛИТЬ:
- Если есть revenue и clients, НЕ спрашивай о average_check (он вычисляется автоматически)
- Если есть revenue и expenses, НЕ спрашивай о profit (он вычисляется автоматически)

ПОМНИ: monthly_costs и expenses - РАЗНЫЕ поля:
- expenses = общие расходы (аренда + зарплаты + материалы + маркетинг)
- monthly_costs = только постоянные расходы (аренда + зарплаты)

ЗАДАЧА:
1. СНАЧАЛА проверь business_name - если его нет, спроси ОБЯЗАТЕЛЬНО: "Как называется ваш бизнес?"
2. Затем проверь остальные ТРЕБУЕМЫЕ ДАННЫЕ (revenue, expenses, clients)
3. Если не хватает ТРЕБУЕМЫХ ДАННЫХ, НЕ СПРАШИВАЙ о ДОПОЛНИТЕЛЬНЫХ! Сфокусируйся только на обязательных.
4. Сформулируй 1-2 максимально конкретных и коротких вопроса по ОДНОЙ, НАИБОЛЕЕ ВАЖНОЙ ОТСУТСТВУЮЩЕЙ метрике
5. Если ВСЕ данные из обоих списков собраны, верни ТОЛЬКО ОДНО СЛОВО: ENOUGH_DATA

Пример вопросов (только если данных нет!):
Как называется ваш бизнес?
Какая у вас выручка в месяц?
Сколько клиентов в среднем у вас бывает?
"""
QUESTION_ANSWER_PROMPT = """Ты - опытный бизнес-консультант с 10-летним опытом. Отвечай на вопросы развернуто, профессионально, но понятным языком. Используй практические кейсы и конкретные примеры. Будь полезным и поддерживающим."""

GENERAL_CHAT_PROMPT = """Ты - дружелюбный помощник для предпринимателей. Поддержи беседу, будь позитивным и полезным. Мягко направляй разговор в сторону бизнес-анализа, если это уместно."""

async def classify_message_type(text: str) -> str:
    """Умное определение типа сообщения с помощью AI"""
    try:
        messages = [
            {"role": "user", "content": MESSAGE_CLASSIFIER_PROMPT},
            {"role": "user", "content": text}
        ]

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: g4f.ChatCompletion.create(
                model=SIMPLE_MODEL,
                messages=messages,
                stream=False
            )
        )

        logger.debug(f"Классификатор отработал для сообщения: '{text[:50]}...'")

        response_upper = response.upper().strip()

        if "BUSINESS_DATA" in response_upper:
            return "business_data"
        elif "BUSINESS_QUESTION" in response_upper:
            return "question"
        elif "GENERAL_CHAT" in response_upper:
            return "general"
        else:
            # Fallback
            # Проверяем, если сообщение похоже на бизнес-данные (есть цифры и бизнес-слова)
            business_words = ['выручка', 'доход', 'прибыль', 'расход', 'трачу', 'клиент', 'продаю', 'чек', 'инвестиц', 'материалы', 'помещение', 'сотрудника', 'деталей', 'штуку']
            text_lower = text.lower()
            if any(word in text_lower for word in business_words) and any(char.isdigit() for char in text):
                return "business_data"
            
            return simple_detect_message_type(text) # Если не бизнес_дата, то используем простой классификатор

    except Exception as e:
        logger.error(f"Ошибка классификации сообщения: {e}")
        # Fallback на простое определение
        # Проверяем, если сообщение похоже на бизнес-данные (есть цифры и бизнес-слова)
        business_words = ['выручка', 'доход', 'прибыль', 'расход', 'трачу', 'клиент', 'продаю', 'чек', 'инвестиц', 'материалы', 'помещение', 'сотрудника', 'деталей', 'штуку']
        text_lower = text.lower()
        if any(word in text_lower for word in business_words) and any(char.isdigit() for char in text):
            return "business_data"
        
        return simple_detect_message_type(text)

def simple_detect_message_type(text: str) -> str:
    """Простое определение типа сообщения (fallback)"""
    text_lower = text.lower()
    
    # Бизнес-аналитика (цифры + бизнес-слова)
    business_words = ['выручка', 'доход', 'прибыль', 'расход', 'затрат', 'клиент', 'продаж', 
                     'заказ', 'чек', 'инвестиц', 'рентабельность', 'оборот', 'актив', 'капитал',
                     'бизнес', 'компания', 'предприятие', 'предприниматель', 'карбон', 'деталь', 'материалы', 
                     'сотрудник', 'помещение', 'продаю', 'штука']
    has_numbers = bool(re.search(r'\d', text))
    has_business_words = any(word in text_lower for word in business_words)
    
    if has_numbers and has_business_words:
        return "business_data"
    
    # Вопросы
    question_words = ['как', 'что', 'почему', 'зачем', 'когда', 'где', 'кто', 'тем', '?']
    business_questions = ['увелич', 'улучш', 'оптимиз', 'развит', 'проблем', 'совет', 'рекомендац']
    
    is_question = any(word in text_lower for word in question_words)
    is_business_question = any(word in text_lower for word in business_questions)
    
    if is_question and is_business_question:
        return "question"
    
    # Общий чат
    return "general"

async def extract_business_data(text: str) -> Dict:
    """Извлечение бизнес-данных из свободного текста"""
    try:
        messages = [
            {"role": "user", "content": BUSINESS_DATA_EXTRACTION_PROMPT},
            {"role": "user", "content": text}
        ]
        
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: g4f.ChatCompletion.create(
                model=g4f.models.gpt_4,
                messages=messages,
                stream=False
            )
        )

        logger.debug("Извлечение данных выполнено")

        # Парсим JSON ответ
        import json
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data
            else:
                logger.warning(f"Не найден JSON в ответе: {response}")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return {}
        
    except Exception as e:
        logger.error(f"Ошибка извлечения бизнес-данных: {e}")
        return {}

async def analyze_missing_data(collected_data: Dict) -> str:
    """Анализ недостающих данных и формирование вопросов"""
    try:
        # Форматируем собранные данные для промпта
        # Фильтруем только значимые данные (не None, не 0, не пустые строки)
        significant_data = {}
        for k, v in collected_data.items():
            if v is not None and v != 0 and v != '' and str(v).strip() != '':
                significant_data[k] = v
        
        data_text = "\n".join([f"- {k}: {v}" for k, v in significant_data.items()])
        
        prompt = MISSING_DATA_ANALYSIS_PROMPT.format(collected_data=data_text)
        
        messages = [
            {"role": "user", "content": prompt}
        ]

        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4,
            messages=messages,
            stream=False
        )

        logger.debug("Анализ недостающих данных выполнен")
        
        return response.strip()
        
    except Exception as e:
        logger.error(f"Ошибка анализа недостающих данных: {e}")
        return "ENOUGH_DATA"  # В случае ошибки считаем что данных достаточно

def prepare_messages(user_id: str, prompt: str, user_message: str):
    """Подготавливает сообщения с промптом предposlедним"""
    if user_id not in conversation_memory:
        conversation_memory[user_id] = []
    
    messages = conversation_memory[user_id].copy()  # История
    if prompt:
        messages.append({"role": "user", "content": prompt})  # Промпт предposledним
    messages.append({"role": "user", "content": user_message})  # Запрос последним
    
    return messages

async def answer_question(question: str, user_id: str = "default") -> str:
    """Ответ на вопрос о бизнесе"""
    try:
        messages = prepare_messages(user_id, QUESTION_ANSWER_PROMPT, question)

        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: g4f.ChatCompletion.create(
                model=SIMPLE_MODEL,
                messages=messages,
                stream=False
            )
        )
        
        conversation_memory[user_id].extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": response}
        ])
        
        # Ограничиваем историю
        if len(conversation_memory[user_id]) > 12:
            conversation_memory[user_id] = conversation_memory[user_id][-12:]   
        return response
        
    except Exception as e:
        logger.error(f"Ошибка ответа на вопрос: {e}")
        return f"Извините, произошла ошибка: {str(e)}"

async def general_chat(message: str, user_id: str = "default") -> str:
    """Общий разговор"""
    try:
        messages = prepare_messages(user_id, GENERAL_CHAT_PROMPT, message)

        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: g4f.ChatCompletion.create(
                model=SIMPLE_MODEL,
                messages=messages,
                stream=False
            )
        )
        
        conversation_memory[user_id].extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": response}
        ])
        
        # Ограничиваем историю
        if len(conversation_memory[user_id]) > 12:
            conversation_memory[user_id] = conversation_memory[user_id][-12:]   
        return response
        
    except Exception as e:
        logger.error(f"Ошибка общего чата: {e}")
        return "Привет! Расскажите о своем бизнесе - помогу с анализом!"

# Тестирование
if __name__ == "__main__":
    import asyncio
    
    async def test_ai():
        print("🧠 Тестируем обновленный AI...")
        
        # Тест извлечения данных
        test_text = "У меня кофейня, выручка 500к в месяц, расходы 200к, около 100 клиентов в день, средний чек 500 рублей"
        result = await extract_business_data(test_text)
        print("Извлеченные данные:", result)
        
    asyncio.run(test_ai())