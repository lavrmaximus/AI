import asyncio
from typing import Dict, List, Optional
from database import db
from business_analyzer import business_analyzer
from ai import extract_business_data, analyze_missing_data  # ← НОВЫЕ ИМПОРТЫ
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
    
    # Минимально необходимые поля для анализа
    REQUIRED_FIELDS = ['revenue', 'expenses', 'clients']
    OPTIONAL_FIELDS = ['investments', 'marketing_costs']
    
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
        """Начало диалога - спрашиваем название бизнеса"""
        await self._update_state(self.STATES['AWAITING_BUSINESS_NAME'])
        
        return {
            'response': "👋 Отлично! Давайте разберем ваш бизнес.\n\nКак называется ваш бизнес?",
            'next_action': 'await_business_name',
            'is_complete': False
        }
    
    async def _handle_business_name(self, business_name: str) -> Dict:
        """Обработка названия бизнеса"""
        self.collected_data['business_name'] = business_name.strip()
        
        # Создаем бизнес в базе данных
        self.business_id = await db.create_business(
            user_id=self.user_id,
            name=business_name
        )
        
        await self._update_state(self.STATES['COLLECTING_DATA'])
        
        return {
            'response': f"📝 Записал: {business_name}\n\n"
                       "Теперь расскажите о своем бизнесе в свободной форме.\n\n"
                       "💡 *Пример:*\n"
                       "Кофейня в центре города, выручка 500к в месяц, расходы на аренду и зарплаты 300к, "
                       "приходит около 1000 клиентов, средний чек 500 рублей, "
                       "инвестиции 1 млн рублей на открытие.",
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

            # Извлекаем данные из текста с помощью AI
            extracted_data = await extract_business_data(user_message)
            logger.info(f"🔍 Извлечено данных: {extracted_data}")

            # Объединяем с уже собранными данными, не перезаписывая, а дополняя
            for key, value in extracted_data.items():
                if value is not None:  # Не перезаписываем None
                    # Если поле уже есть и новое значение != 0 или новое значение - строка
                    # АИ может вернуть 0 если не нашел. Если предыдущее было числовым, оставляем его.
                    if key in self.collected_data and self.collected_data[key] is not None and value == 0:
                        continue
                    self.collected_data[key] = value

            # Отрасль больше не используется

            # Проверяем достаточно ли данных для начала минимального анализа
            # Формируем данные для промпта как строку, где указано наличие или отсутствие
            collected_data_for_ai_prompt = {}
            for field in self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS:
                if field in self.collected_data and self.collected_data[field] is not None:
                    collected_data_for_ai_prompt[field] = f"ДА ({self.collected_data[field]})"
                else:
                    collected_data_for_ai_prompt[field] = "НЕТ"
            
            # Проверяем, сколько обязательных полей собрано
            required_fields_count = sum(1 for field in self.REQUIRED_FIELDS if field in self.collected_data and self.collected_data[field] is not None)
            
            # Если собраны все обязательные поля, переходим к сбору дополнительных
            if required_fields_count == len(self.REQUIRED_FIELDS):
                missing_questions_text = await analyze_missing_data(self.collected_data) # Отдаем AI полные данные
            else:
                # Если не хватает обязательных, то AI должен сфокусироваться только на них
                # Создаем временный словарь, чтобы AI не видел дополнительные, пока не соберет основные
                temp_collected_data = {k: v for k, v in self.collected_data.items() if k in self.REQUIRED_FIELDS}
                missing_questions_text = await analyze_missing_data(temp_collected_data)


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
                summary_lines.append(f"*{name}*: _отсутствует_") # Четко указываем, что отсутствует

        if not summary_lines:
            return "Пока нет собранных данных."

        return "\n".join(summary_lines)


    async def _handle_analysis(self, user_response: str) -> Dict:
        """Обработка подтверждения анализа"""
        if user_response.lower() in ['да', 'yes', 'конечно', 'проведи', 'анализ', 'готов', 'готово']:
            
            # Запускаем полный анализ через business_analyzer
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
        return all(
            field in self.collected_data and 
            self.collected_data[field] is not None and 
            self.collected_data[field] > 0 
            for field in self.REQUIRED_FIELDS
        )
    
    
    def _format_analysis_response(self, analysis_result: Dict) -> str:
        """Форматирование ответа с анализом"""
        if 'error' in analysis_result:
            return f"❌ Ошибка анализа: {analysis_result['error']}"
        
        health_score = analysis_result.get('health_score', 0)
        health_assessment = analysis_result.get('health_assessment', {})
        key_metrics = analysis_result.get('key_metrics', {})
        detailed_metrics = analysis_result.get('detailed_metrics', {})
        
        # Заголовок с Health Score
        emoji = health_assessment.get('emoji', '⚪')
        response = f"🏥 *БИЗНЕС-ЗДОРОВЬЕ: {health_score}/100* {emoji}\n\n"
        response += f"*{health_assessment.get('message', '')}*\n\n"
        
        # Ключевые метрики
        response += "💰 *КЛЮЧЕВЫЕ МЕТРИКИ:*\n"
        response += f"• Рентабельность: {key_metrics.get('profit_margin', 0):.1f}%\n"
        response += f"• ROI: {key_metrics.get('roi', 0):.1f}%\n"
        response += f"• LTV/CAC: {key_metrics.get('ltv_cac_ratio', 0):.2f}\n"
        response += f"• Запас прочности: {key_metrics.get('safety_margin', 0):.1f}%\n\n"

        # Полный список рассчитанных метрик
        if detailed_metrics:
            response += "📊 *ВСЕ МЕТРИКИ:*\n"
            metric_lines = []
            def fmt(name, value):
                try:
                    if isinstance(value, (int, float)):
                        return f"{name}: {value:.2f}"
                    return f"{name}: {value}"
                except Exception:
                    return f"{name}: {value}"
            for k, v in detailed_metrics.items():
                if k in ['business_id','snapshot_id','period_type','period_date','created_at']:
                    continue
                metric_lines.append("• " + fmt(k, v))
            response += "\n".join(metric_lines) + "\n\n"
        
        # AI комментарий и рекомендации
        if analysis_result.get('ai_commentary'):
            response += f"💡 *КОММЕНТАРИЙ AI:*\n{analysis_result['ai_commentary']}\n\n"
        
        if analysis_result.get('ai_advice'):
            response += "🎯 *РЕКОМЕНДАЦИИ:*\n"
            for i, advice in enumerate(analysis_result['ai_advice'][:4], 1):
                response += f"{i}. {advice}\n"
            response += "\n"
        
        response += "✅ *Анализ завершен! Использовано 22 метрики*\n"
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