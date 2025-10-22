import asyncio
from typing import Dict, List, Optional
from database import db
from business_analyzer import business_analyzer
from ai import extract_business_data, analyze_missing_data
from report_formatter import format_business_report
import logging

logger = logging.getLogger(__name__)

class BusinessConversation:
    """
    Умный диалоговый менеджер для сбора данных о бизнесе в свободной форме
    """
    
    STATES = {
        'START': 'start',
        'AWAITING_BUSINESS_NAME': 'awaiting_business_name',
        'COLLECTING_DATA': 'collecting_data',  # ← СВОБОДНЫЙ ВВОД
        'READY_FOR_ANALYSIS': 'ready_for_analysis',
        'COMPLETED': 'completed'
    }
    
    # Минимально необходимые поля для анализа (включая название бизнеса)
    REQUIRED_FIELDS = ['business_name', 'revenue', 'expenses', 'clients']
    OPTIONAL_FIELDS = ['investments', 'marketing_costs', 'employees', 'new_clients_per_month', 'customer_retention_rate']
    
    def __init__(self, session_id: int = None):
        self.session_id = session_id
        self.current_state = self.STATES['START']
        self.collected_data = {}
        self.business_id = None
        self.user_id = None
    
    async def get_conversation(self, user_id: str) -> 'BusinessConversation':
        """Получение или создание сессии для пользователя"""
        if user_id not in self.active_sessions:
            conversation = BusinessConversation()
            await conversation.initialize(user_id) # Инициализация нового экземпляра
            self.active_sessions[user_id] = conversation

        return self.active_sessions[user_id]

    def end_conversation(self, user_id: str):
        """Завершение сессии"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]

    async def initialize(self, user_id: str) -> int:
        """Инициализация новой сессии"""
        self.user_id = user_id
        self.session_id = await db.create_conversation_session(
            user_id=user_id,
            business_id=None,
            initial_state=self.STATES['START']
        )
        return self.session_id
    
    async def load_session(self, session_id: int) -> bool:
        """Загрузка существующей сессии"""
        session_data = await db.get_session(session_id)
        if not session_data:
            return False
            
        self.session_id = session_id
        self.current_state = session_data['current_state']
        self.collected_data = session_data['collected_data']
        self.business_id = session_data['business_id']
        self.user_id = session_data['user_id']
        return True
    
    async def process_message(self, user_message: str) -> Dict:
        """
        Обработка сообщения пользователя
        Возвращает: {'response': str, 'next_action': str, 'is_complete': bool}
        """
        # Сохраняем ответ пользователя в контексте текущего состояния
        await self._save_user_response(user_message)
        
        # Универсальная отмена без сохранения/анализа
        cancel_words = ['выйти', 'выход', 'отмена', 'cancel', 'exit', 'quit']
        if self.current_state in [self.STATES['COLLECTING_DATA'], self.STATES['READY_FOR_ANALYSIS']]:
            if user_message.strip().lower() in cancel_words:
                await self._update_state(self.STATES['COMPLETED'])
                return {
                    'response': "🚪 Вы вышли из режима без сохранения изменений. Чтобы вернуться: /edit_business",
                    'next_action': 'cancelled',
                    'is_complete': True
                }

        # Обрабатываем в зависимости от текущего состояния
        if self.current_state == self.STATES['START']:
            return await self._handle_start()
        
        elif self.current_state == self.STATES['AWAITING_BUSINESS_NAME']:
            return await self._handle_business_name(user_message)
        
        elif self.current_state == self.STATES['COLLECTING_DATA']:
            return await self._handle_data_collection(user_message)

        elif self.current_state == self.STATES['READY_FOR_ANALYSIS']:
            return await self._handle_analysis(user_message)
        
        else:
            return await self._handle_unknown_state()
    
    async def _handle_start(self) -> Dict:
        """Начало диалога - сразу переходим к свободному вводу данных"""
        await self._update_state(self.STATES['COLLECTING_DATA'])
        return {
            'response': "📝 Расскажите о вашем бизнесе в свободной форме: название, выручка, расходы, клиенты и т.д.",
            'next_action': 'collect_data',
            'is_complete': False
        }
    
    async def _handle_business_name(self, business_name: str) -> Dict:
        """Обработка названия бизнеса (поддержка старого шага)"""
        self.collected_data['business_name'] = business_name.strip()
        await self._update_state(self.STATES['COLLECTING_DATA'])
        return {
            'response': "📝 Принял название. Теперь опишите остальные данные: выручка, расходы, клиенты и т.д.",
            'next_action': 'collect_data',
            'is_complete': False
        }
    
    async def _handle_data_collection(self, user_message: str) -> Dict:
        """
        Обработка свободного ввода данных о бизнесе. Объединяет новые данные с существующими.
        """
        try:
            # Быстрое подтверждение: если пользователь пишет "да/готово" и базовые данные уже есть — запускаем анализ сразу
            if user_message.strip().lower() in ['да', 'yes', 'готово', 'готов'] and self._has_required_data():
                return await self._handle_analysis('да')

            # Извлекаем данные из текста с помощью AI (включая business_name)
            extracted_data = await extract_business_data(user_message)
            logger.info(f"🔍 Извлечено данных: {extracted_data}")

            # Объединяем с уже собранными данными: мердж только "значимых" значений
            for key, value in extracted_data.items():
                if value is None:
                    continue
                # Если пришёл ноль от ИИ как "не нашёл", не затираем ранее сохранённое число
                if key in self.collected_data and isinstance(self.collected_data[key], (int, float)) and value == 0:
                    continue
                # Строки и положительные/ненулевые числа обновляем
                if isinstance(value, str):
                    if value.strip() == "":
                        continue
                    self.collected_data[key] = value
                else:
                    self.collected_data[key] = value

            # Отрасль больше не используется

            # Проверяем достаточно ли данных для начала минимального анализа (требуем business_name)
            # Формируем данные для промпта как строку, где указано наличие или отсутствие
            collected_data_for_ai_prompt = {}
            for field in self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS:
                if field in self.collected_data and self.collected_data[field] is not None:
                    collected_data_for_ai_prompt[field] = f"ДА ({self.collected_data[field]})"
                else:
                    collected_data_for_ai_prompt[field] = "НЕТ"
            
            # Если monthly_costs отсутствует, но есть expenses — подставляем для полноты анализа
            if ('monthly_costs' not in self.collected_data or not self.collected_data.get('monthly_costs')) and self.collected_data.get('expenses'):
                self.collected_data['monthly_costs'] = self.collected_data['expenses']

            # Проверяем, сколько обязательных полей собрано
            required_fields_count = sum(
                1 for field in self.REQUIRED_FIELDS
                if field in self.collected_data and (
                    (isinstance(self.collected_data[field], (int, float)) and self.collected_data[field] is not None and self.collected_data[field] > 0)
                    or (isinstance(self.collected_data[field], str) and self.collected_data[field].strip() != '')
                )
            )
            
            # Если собраны все обязательные поля, переходим к сбору дополнительных
            if required_fields_count == len(self.REQUIRED_FIELDS):
                logger.info("🧠 Запрос недостающих данных у AI (полный набор полей)")
                missing_questions_text = await analyze_missing_data(self.collected_data) # Отдаем AI полные данные
                logger.info(f"🧠 Ответ AI по недостающим данным: {missing_questions_text[:20]}")
            else:
                # Если не хватает обязательных, то AI должен сфокусироваться только на них
                # Создаем временный словарь, чтобы AI не видел дополнительные, пока не соберет основные
                temp_collected_data = {k: v for k, v in self.collected_data.items() if k in self.REQUIRED_FIELDS}
                logger.info("🧠 Запрос недостающих данных у AI (только обязательные)")
                missing_questions_text = await analyze_missing_data(temp_collected_data)
                logger.info(f"🧠 Ответ AI по недостающим данным: {missing_questions_text[:20]}")


            if missing_questions_text.strip().upper() == "ENOUGH_DATA":
                await self._update_state(self.STATES['READY_FOR_ANALYSIS'])

                summary = self._get_data_summary()
                return {
                    'response': f"✅ Отлично! У меня есть все необходимые данные для анализа.\n\n"
                                f"Подведем итог собранных данных:\n{summary}\n\n"
                                f"Все готово! Готовы провести полный анализ? (Да/Нет)\n\n"
                                f"Чтобы отменить без изменений — напишите 'выйти'",
                    'next_action': 'await_analysis_confirm',
                    'is_complete': False
                }
            else:
                summary = self._get_data_summary()
                # Используем более информативное сообщение
                if self._has_required_data():
                    return {
                        'response': f"📊 Базовые данные собраны.\nПодведем итог:\n{summary}\n\n"
                                   f"🤔 Для *расширенного* анализа нужно ещё немного информации:\n\n"
                                   f"{missing_questions_text}\n\n"
                                   f"Поделитесь этими данными в свободной форме или напишите 'Да', чтобы начать анализ с текущими данными (без расширенных метрик).\n\n"
                                   f"Чтобы отменить без изменений — напишите 'выйти'",
                        'next_action': 'collect_data',
                        'is_complete': False
                    }
                else:
                    return {
                        'response': f"📊 Текущие данные:\n{summary}\n\n"
                                   f"🤔 Мне нужно ещё немного информации для базового анализа:\n\n"
                                   f"{missing_questions_text}\n\n"
                                   f"Расскажите подробнее в свободной форме.\n\n"
                                   f"Чтобы отменить без изменений — напишите 'выйти'",
                        'next_action': 'collect_data',
                        'is_complete': False
                    }

        except Exception as e:
            logger.error(f"Ошибка в сборе данных: {e}")
            return {
                'response': "❌ Произошла ошибка при обработке данных. Попробуйте ещё раз.",
                'next_action': 'collect_data',
                'is_complete': False
            }


    def _get_data_summary(self) -> str:
        """Сводка собранных данных. Возвращает отформатированную строку."""
        data = self.collected_data
        summary_lines = []

        field_names = {
            'business_name': '🏢 Бизнес',
            'revenue': '💰 Выручка',
            'expenses': '📊 Расходы',
            'profit': '📈 Прибыль',
            'clients': '👥 Клиенты',
            'average_check': '💳 Средний чек',
            'investments': '💼 Инвестиции',
            'marketing_costs': '📢 Маркетинг',
            'employees': '🧑‍🤝‍🧑 Сотрудники',
            'monthly_costs': '💸 Ежемесячные затраты',
            'new_clients_per_month': '🆕 Новые клиенты/мес',
            'customer_retention_rate': '🔄 Удержание клиентов'
        }

        for field in (self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS):
            if field in data and data[field] is not None:
                name = field_names.get(field, field) # Используем человеческое название или само поле
                val = data[field]
                if isinstance(val, (int, float)):
                    if field == 'customer_retention_rate':
                        summary_lines.append(f"*{name}*: {val:.1f}%")
                    elif field == 'business_name':
                        summary_lines.append(f"*{name}*: {val}")
                    elif field in ['clients', 'employees', 'new_clients_per_month']:
                        summary_lines.append(f"*{name}*: {val:,.0f}")
                    else: # Остальные числовые (рубли)
                         summary_lines.append(f"*{name}*: {val:,.0f} руб")
                else: # Если не число
                    summary_lines.append(f"*{name}*: {val}")
            else:
                name = field_names.get(field, field)
                summary_lines.append(f"*{name}*: _отсутствует_")

        if not summary_lines:
            return "Пока нет собранных данных."

        return "\n".join(summary_lines)


    async def _handle_analysis(self, user_response: str) -> Dict:
        """Обработка подтверждения анализа"""
        if user_response.lower() in ['да', 'yes', 'конечно', 'проведи', 'анализ', 'готов', 'готово']:
            
            # Запускаем полный анализ через business_analyzer
            # Создаём бизнес и snapshot ТОЛЬКО после подтверждения
            analysis_result = await business_analyzer.analyze_business_data(
                self.collected_data, 
                self.user_id, 
                self.business_id
            )
            
            await self._update_state(self.STATES['COMPLETED'])
            
            return {
                'response': self._format_analysis_response(analysis_result),
                'next_action': 'analysis_complete',
                'is_complete': True,
                'analysis_data': analysis_result
            }
        else:
            # Возвращаем к сбору данных
            await self._update_state(self.STATES['COLLECTING_DATA'])
            summary = self._get_data_summary()
            missing_questions = await analyze_missing_data(self.collected_data)
            
            if missing_questions.strip().upper() == "ENOUGH_DATA":
                return {
                    'response': f"{summary}\n\nДобавьте любую дополнительную информацию или напишите 'да' для анализа.",
                    'next_action': 'collect_data',
                    'is_complete': False
                }
            
            return {
                'response': f"📊 Текущие данные:\n{summary}\n\n🤔 Что еще важно знать:\n{missing_questions}",
                'next_action': 'collect_data',
                'is_complete': False
            }
    
    async def _handle_unknown_state(self) -> Dict:
        """Обработка неизвестного состояния"""
        return {
            'response': "Извините, произошла ошибка. Давайте начнем заново.",
            'next_action': 'restart',
            'is_complete': True
        }
    
    def _has_required_data(self) -> bool:
        """Проверка наличия обязательных данных"""
        for field in self.REQUIRED_FIELDS:
            value = self.collected_data.get(field)
            if value is None:
                return False
            if field == 'business_name':
                if not isinstance(value, str) or not value.strip():
                    return False
            else:
                try:
                    number_value = float(value)
                except (TypeError, ValueError):
                    return False
                if number_value <= 0:
                    return False
        return True
    
    
    def _format_analysis_response(self, analysis_result: Dict) -> str:
        """Форматирование ответа с анализом"""
        if 'error' in analysis_result:
            return f"❌ Ошибка анализа: {analysis_result['error']}"
        
        # Подготавливаем данные для единого формата
        business_data = {
            'business_name': 'Анализируемый бизнес',
            'revenue': analysis_result.get('raw_data', {}).get('revenue', 0),
            'expenses': analysis_result.get('raw_data', {}).get('expenses', 0),
            'profit': analysis_result.get('raw_data', {}).get('profit', 0),  # enriched
            'clients': analysis_result.get('raw_data', {}).get('clients', 0),
            'average_check': analysis_result.get('raw_data', {}).get('average_check', 0),  # enriched
            'investments': analysis_result.get('raw_data', {}).get('investments', 0),
            'marketing_costs': analysis_result.get('raw_data', {}).get('marketing_costs', 0),
            'employees': analysis_result.get('raw_data', {}).get('employees', 0),
            'new_clients_per_month': analysis_result.get('raw_data', {}).get('new_clients_per_month', 0),
            'customer_retention_rate': analysis_result.get('raw_data', {}).get('customer_retention_rate', 0)
        }
        
        metrics = analysis_result.get('detailed_metrics', {})
        recommendations = analysis_result.get('ai_advice', [])
        
        # Используем единый формат
        response = format_business_report(business_data, metrics, recommendations)
        
        # Добавляем AI комментарий если есть
        if analysis_result.get('ai_commentary'):
            response += f"\n💡 *КОММЕНТАРИЙ AI:*\n{analysis_result['ai_commentary']}\n"
        
        response += "\n✅ *Анализ завершен! Использовано 22 метрики*\n"
        response += "📊 *Используйте /history для отслеживания динамики*"
        
        return response
    
    async def _save_user_response(self, response: str):
        """Сохранение ответа пользователя"""
        try:
            await db.log_message(
                session_id=self.session_id,
                user_message=response,
                bot_response='',
                message_type='user_input'
            )
        except Exception:
            # Логирование умышленно молчит, чтобы не ломать диалог
            return
    
    async def _update_state(self, new_state: str):
        """Обновление состояния сессии"""
        self.current_state = new_state
        if self.session_id:
            await db.update_session_state(
                self.session_id, 
                new_state, 
                self.collected_data
            )

# Глобальный менеджер сессий
class ConversationManager:
    def __init__(self):
        self.active_sessions = {}  # user_id -> BusinessConversation
    
    async def get_conversation(self, user_id: str) -> 'BusinessConversation':
        """Получение или создание сессии для пользователя"""
        if user_id not in self.active_sessions:
            conversation = BusinessConversation()
            await conversation.initialize(user_id)
            self.active_sessions[user_id] = conversation
        
        return self.active_sessions[user_id]
    
    def end_conversation(self, user_id: str):
        """Завершение сессии"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]

# Глобальный экземпляр менеджера
conv_manager = ConversationManager()