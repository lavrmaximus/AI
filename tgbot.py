from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from ai import classify_message_type, general_chat, answer_question, extract_business_data # Импортируем только нужные функции
from conversation_manager import conv_manager
from business_analyzer import business_analyzer
from database import db
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import asyncio
from datetime import datetime
from telegram.helpers import escape_markdown

logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Настройка логирования (ротация файла, явный путь)
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

class DailyFileHandler(logging.Handler):
    def __init__(self, log_dir: str):
        super().__init__()
        self.log_dir = log_dir
        self.current_date = None
        self.file_handler = None
        self._ensure_file()

    def _ensure_file(self):
        date_str = datetime.now().strftime('%Y-%m-%d')
        if date_str != self.current_date:
            if self.file_handler:
                try:
                    self.file_handler.close()
                except Exception:
                    pass
            self.current_date = date_str
            path = os.path.join(self.log_dir, f'{date_str}.log')
            self.file_handler = logging.FileHandler(path, encoding='utf-8')
            self.file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))

    def emit(self, record: logging.LogRecord):
        try:
            self._ensure_file()
            self.file_handler.emit(record)
        except Exception:
            # Не роняем приложение из-за проблем с логами
            pass

file_handler = DailyFileHandler(LOG_DIR)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler],
    force=True
)
logger = logging.getLogger(__name__)

# BOT_TOKEN будет читаться в __init__
ADMINS = [
    "1287604685",  # Вставьте сюда ID админа
]

def safe_markdown_text(text: str) -> str:
    """
    Безопасное форматирование Markdown с сохранением жирного текста
    """
    # Экранируем все спецсимволы
    safe_text = escape_markdown(text, version=2)
    # Возвращаем звездочки для жирного текста
    safe_text = safe_text.replace(r'\*', '*')
    return safe_text

def clean_ai_text(text: str) -> str:
    """
    Очистка AI-текста от Markdown форматирования для безопасной отправки
    """
    import re
    
    # Убираем заголовки ###
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Убираем жирный текст **текст**
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    
    # Убираем курсив __текст__
    text = re.sub(r'__([^_]+)__', r'\1', text)
    
    # Убираем курсив _текст_ (одиночные подчёркивания)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', text)
    
    # Убираем курсив *текст* (одиночные звёздочки)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', text)
    
    # Убираем код `текст`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Убираем квадратные скобки с экранированием
    text = re.sub(r'\\\[', '[', text)
    text = re.sub(r'\\\]', ']', text)
    
    return text

print("Запуск бота....")

class BusinessBot:
    def __init__(self):
        # Читаем токен при инициализации (не при импорте модуля)
        token = (
            os.getenv("BOT_TOKEN")
            or os.getenv("TELEGRAM_BOT_TOKEN")
            or os.getenv("TOKEN")
        )
        if not token:
            raise ValueError("BOT_TOKEN environment variable is required (try BOT_TOKEN or TELEGRAM_BOT_TOKEN)")
        
        self.app = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("about", self.about_command))
        self.app.add_handler(CommandHandler("history", self.history_command))
        self.app.add_handler(CommandHandler("admin_clear", self.admin_clear))
        self.app.add_handler(CommandHandler("new_business", self.new_business_command))
        self.app.add_handler(CommandHandler("edit_business", self.edit_business_command))
        self.app.add_handler(CommandHandler("delete_business", self.delete_business_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_inline_buttons))
        # Короткий обработчик ошибок без traceback
        self.app.add_error_handler(self.on_error)

    async def on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        try:
            err_text = str(context.error)
        except Exception:
            err_text = "unknown"
        logger.error(f"Update error: {err_text}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)

        #logger.info(f"🆕 Новый пользователь: {user.first_name} (ID: {user_id}, @{user.username})")
        await db.save_user(user_id, user.username, user.first_name, user.last_name)

        text = safe_markdown_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Я - твой продвинутый AI-аналитик! 🚀\n\n"
            "*Что я умею:*\n"
            "• Создавать бизнес с умным диалогом\n"
            "• Рассчитывать 22 финансовые метрики\n"
            "• Анализировать здоровье бизнеса\n"
            "• Отвечать на вопросы о бизнесе\n"
            "• Сохранять всю историю в базу\n\n"
            "*Начните прямо сейчас:*\n"
            "/new_business - создать новый бизнес\n"
            "[вопрос] - задать вопрос о бизнесе"
        )

        await update.message.reply_text(text, parse_mode='MarkdownV2')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"ℹ️ Пользователь {user.first_name} запросил помощь")

        text = safe_markdown_text(
            "*Доступные команды:*\n\n"
            "/start - начать работу\n"
            "/help - помощь\n"
            "/about - о проекте\n"
            "/history - история анализов\n"
            "/new_business - создать новый бизнес 🆕\n"
            "/edit_business - редактировать существующий бизнес ✏️\n\n"
            "*Умное определение типов:*\n"
            "• *Вопрос:* 'Как увеличить прибыль?'\n"
            "• *Бизнес-данные:* 'Выручка 500к, расходы 200к' (Бот предложит команду)\n"
            "• *Общение:* 'Привет! Как дела?'\n\n"
            "🎯 Для создания бизнеса используйте /new_business\n"
            "✏️ Для редактирования используйте /edit_business"
        )
        await update.message.reply_text(text, parse_mode='MarkdownV2')

    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"ℹ️ Пользователь {user.first_name} запросил информацию о боте")

        text = safe_markdown_text(
            "*💸ФИНАНСОВЫЙ ЛУЧ💸*\n\n"
            "*Новые возможности:*\n"
            "• Умный диалог с ИИ\n"
            "• 22 финансовые метрики\n"
            "• Business Health Score\n"
            "• AI рекомендации\n"
            "• Сохранение истории\n\n"
            "*Технологии:*\n"
            "• GPT-4 для анализа\n"
            "• Расширенные формулы\n"
            "• PostgreSQL база данных (или SQLite)\n\n"
            "🚀 *Полный анализ вашего бизнеса!*"
        )
        await update.message.reply_text(text, parse_mode='MarkdownV2')

    async def new_business_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Новая команда - создание бизнеса с умным диалогом"""
        user = update.effective_user
        user_id = str(user.id)

        logger.info(f"🆕 Пользователь {user.first_name} создает новый бизнес")

        # Получаем сессию диалога
        conversation = await conv_manager.get_conversation(user_id)

        # Начинаем диалог
        response = await conversation.process_message("")

        await self.send_long_message(update, response['response'], 'Markdown')

    async def edit_business_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для редактирования существующего бизнеса"""
        user = update.effective_user
        user_id = str(user.id)

        logger.info(f"✏️ Пользователь {user.first_name} хочет редактировать бизнес")

        try:
            businesses = await db.get_user_businesses(user_id)

            if not businesses:
                await update.message.reply_text(
                    safe_markdown_text("📝 *У вас нет бизнесов для редактирования*\n\n"
                    "Создайте первый бизнес с помощью /new_business!"),
                    parse_mode='MarkdownV2'
                )
                return

            # Создаем inline кнопки для выбора бизнеса
            keyboard = []
            for i, business in enumerate(businesses[:10], 1):
                business_name = business.get('business_name', f'Бизнес #{i}')
                business_id = business.get('business_id')
                keyboard.append([
                    InlineKeyboardButton(f"✏️ {business_name}", callback_data=f'edit_{business_id}'),
                    InlineKeyboardButton("🗑 Удалить", callback_data=f'delete_{business_id}')
                ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                safe_markdown_text("✏️ *РЕДАКТИРОВАНИЕ БИЗНЕСА*\n\n"
                "Выберите бизнес для обновления данных:"),
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )

        except Exception as e:
            logger.error(f"Ошибка получения списка бизнесов: {e}")
            await update.message.reply_text(
                safe_markdown_text("❌ Произошла ошибка при получении списка бизнесов\\. Попробуйте позже\\."),
                parse_mode='MarkdownV2'
            )

    async def delete_business_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для удаления бизнеса (мягкое удаление)"""
        user = update.effective_user
        user_id = str(user.id)

        logger.info(f"🗑 Пользователь {user.first_name} хочет удалить бизнес")

        try:
            businesses = await db.get_user_businesses(user_id)

            if not businesses:
                await update.message.reply_text(
                    safe_markdown_text("📝 *У вас нет бизнесов для удаления*\n\n"
                    "Создайте первый бизнес с помощью /new_business!"),
                    parse_mode='MarkdownV2'
                )
                return

            keyboard = []
            for i, business in enumerate(businesses[:10], 1):
                business_name = business.get('business_name', f'Бизнес #{i}')
                business_id = business.get('business_id')
                keyboard.append([InlineKeyboardButton(f"🗑 Удалить {business_name}", callback_data=f'delete_{business_id}')])

            await update.message.reply_text(
                safe_markdown_text("🗑 *УДАЛЕНИЕ БИЗНЕСА*\n\nВыберите бизнес для удаления:"),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )

        except Exception as e:
            logger.error(f"Ошибка получения списка бизнесов для удаления: {e}")
            await update.message.reply_text(
                safe_markdown_text("❌ Произошла ошибка\\. Попробуйте позже\\."),
                parse_mode='MarkdownV2'
            )

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)

        logger.info(f"📊 Пользователь {user.first_name} запросил историю")

        try:
            businesses = await db.get_user_businesses(user_id)

            if not businesses:
                await update.message.reply_text(
                    safe_markdown_text("📝 *История анализов пуста*\n\n"
                    "Создайте первый бизнес с помощью /new_business!"),
                    parse_mode='MarkdownV2'
                )
                return

            # Создаем inline кнопки для каждого бизнеса
            keyboard = []

            for i, business in enumerate(businesses[:10], 1):  # Показываем до 10 бизнесов
                business_name = business.get('business_name', f'Бизнес #{i}')
                business_id = business.get('business_id')

                # Получаем последний Health Score
                try:
                    history = await db.get_business_history(business_id, limit=1)
                    if history:
                        health_score = history[0].get('overall_health_score', 0)
                        button_text = f"📊 {business_name} (Health: {health_score}/100)"
                    else:
                        button_text = f"📊 {business_name}"
                except Exception as e:
                    logger.warning(f"Ошибка получения Health Score для бизнеса {business_id}: {e}")
                    button_text = f"📊 {business_name}" # Если ошибка, показываем только имя

                keyboard.append([InlineKeyboardButton(button_text, callback_data=f'business_{business_id}')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                safe_markdown_text("📊 *ВАШИ БИЗНЕСЫ*\n\n"
                "Выберите бизнес для подробного анализа:"),
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )

        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            await update.message.reply_text(
                safe_markdown_text("❌ Произошла ошибка при получении истории\\. Попробуйте позже\\."),
                parse_mode='MarkdownV2'
            )

    async def handle_inline_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка inline кнопок"""
        query = update.callback_query
        await query.answer()  # Обязательно отвечаем на query

        if query.data.startswith('business_'):
            business_id = int(query.data.split('_')[1])
            await self.show_business_details(query, business_id)
        elif query.data.startswith('edit_'):
            business_id = int(query.data.split('_')[1])
            await self.start_edit_business(query, business_id)
        elif query.data.startswith('delete_confirm_'):
            business_id = int(query.data.split('_')[2])
            await self.delete_business_confirmed(query, business_id)
        elif query.data.startswith('delete_'):
            business_id = int(query.data.split('_')[1])
            await self.confirm_delete_business(query, business_id)

    async def show_business_details(self, query: CallbackQuery, business_id: int):
        """Показ деталей бизнеса по запросу Inline кнопки"""
        try:
            # Получаем историю
            # Здесь мы используем business_analyzer, чтобы получить полный отчет
            report = await business_analyzer.generate_business_report(business_id)

            if 'error' in report:
                await query.edit_message_text(f"❌ Ошибка: {report['error']}")
                return

            health_score = report.get('health_score', 0)
            health_assessment = report.get('health_assessment', {})
            key_metrics = report.get('key_metrics', {})
            recommendations = report.get('recommendations', [])

            response = f"📊 *ДЕТАЛЬНЫЙ АНАЛИЗ БИЗНЕСА: {business_id}*\n\n" \
                       f"🏥 *БИЗНЕС-ЗДОРОВЬЕ: {health_score}/100 {health_assessment.get('emoji', '')}*\n" \
                       f"*{health_assessment.get('message', '')}*\n\n" \
                       f"📈 *Ключевые метрики:*\n" \
                       f"• Рентабельность: {key_metrics.get('profit_margin', 0):.1f}%\n" \
                       f"• ROI: {key_metrics.get('roi', 0):.1f}%\n" \
                       f"• LTV/CAC: {key_metrics.get('ltv_cac_ratio', 0):.2f}\n" \
                       f"• Запас прочности: {key_metrics.get('safety_margin', 0):.1f}%\n" \
                       f"• Темп роста выручки: {key_metrics.get('revenue_growth_rate', 0):.1f}%\n" \
                       f"• До банкротства: {key_metrics.get('months_to_bankruptcy', 0):.0f} мес\n\n"

            if recommendations:
                response += "🎯 *Рекомендации:*\n"
                for i, rec in enumerate(recommendations, 1):
                    response += f"{i}. {rec}\n"
                response += "\n"

            # Полный список рассчитанных метрик (если есть)
            all_metrics = report.get('all_metrics', {})
            if all_metrics:
                response += "📊 *ВСЕ МЕТРИКИ:*\n"
                metric_lines = []
                def fmt(name, value):
                    try:
                        if isinstance(value, (int, float)):
                            return f"{name}: {value:.2f}"
                        return f"{name}: {value}"
                    except Exception:
                        return f"{name}: {value}"
                for k, v in all_metrics.items():
                    if k in ['business_id','snapshot_id','period_type','period_date','created_at']:
                        continue
                    metric_lines.append("• " + fmt(k, v))
                response += "\n".join(metric_lines) + "\n\n"

            await self.send_long_message(query, response, parse_mode='MarkdownV2')

        except Exception as e:
            logger.error(f"Ошибка показа деталей бизнеса: {e}")
            await query.edit_message_text("❌ Произошла ошибка при загрузке деталей.")

    async def start_edit_business(self, query: CallbackQuery, business_id: int):
        """Начало редактирования бизнеса"""
        try:
            user_id = str(query.from_user.id)
            
            # Получаем информацию о бизнесе
            history = await db.get_business_history(business_id, limit=1)
            if not history:
                await query.edit_message_text("❌ Бизнес не найден")
                return
            
            current_data = history[0]
            business_name = current_data.get('business_name', f'Бизнес #{business_id}')
            
            # Создаем новую сессию диалога для редактирования
            conversation = await conv_manager.get_conversation(user_id)
            conversation.business_id = business_id
            conversation.collected_data = {
                'business_name': business_name,
                'revenue': current_data.get('revenue', 0),
                'expenses': current_data.get('expenses', 0),
                'profit': current_data.get('profit', 0),
                'clients': current_data.get('clients', 0),
                'average_check': current_data.get('average_check', 0),
                'investments': current_data.get('investments', 0),
                'marketing_costs': current_data.get('marketing_costs', 0),
                'employees': current_data.get('employees', 0)
            }
            
            await conversation._update_state(conversation.STATES['COLLECTING_DATA'])
            
            response = f"✏️ *РЕДАКТИРОВАНИЕ: {business_name}*\n\n" \
                      f"Текущие данные:\n{conversation._get_data_summary()}\n\n" \
                      f"Отправьте новые данные в свободной форме или напишите 'да' для завершения.\n\n" \
                      f"Чтобы отменить без изменений — напишите 'выйти'"
            
            await query.edit_message_text(safe_markdown_text(response), parse_mode='MarkdownV2')
            
        except Exception as e:
            logger.error(f"Ошибка начала редактирования: {e}")
            await query.edit_message_text("❌ Произошла ошибка при начале редактирования.")

    async def confirm_delete_business(self, query: CallbackQuery, business_id: int):
        """Подтверждение удаления бизнеса"""
        try:
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f'delete_confirm_{business_id}')],
                [InlineKeyboardButton("❌ Отмена", callback_data=f'business_{business_id}')]
            ]
            await query.edit_message_text(
                safe_markdown_text("⚠️ *Вы уверены, что хотите удалить бизнес?*\nЭто действие можно отменить только через администратора."),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            logger.error(f"Ошибка подтверждения удаления: {e}")
            await query.edit_message_text("❌ Ошибка при подтверждении удаления.")

    async def delete_business_confirmed(self, query: CallbackQuery, business_id: int):
        """Выполнение мягкого удаления бизнеса"""
        try:
            user_id = str(query.from_user.id)
            await db.soft_delete_business(user_id, business_id)
            await query.edit_message_text("✅ Бизнес помечен как удалён.")
        except Exception as e:
            logger.error(f"Ошибка удаления бизнеса: {e}")
            await query.edit_message_text("❌ Не удалось удалить бизнес.")

    async def admin_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)

        # Проверяем что пользователь в списке админов
        if user_id not in ADMINS:
            await update.message.reply_text("❌ Нет доступа")
            return

        if not context.args:
            await update.message.reply_text(
                "ℹ️ *Использование:*\n"
                "`/admin_clear USER_ID` - очистить по ID\n"
                "`/admin_clear @username` - очистить по username\n\n"
                f"👑 *Текущие админы*: {', '.join(ADMINS)}",
                parse_mode='MarkdownV2'
            )
            return

        target = context.args[0]
        deleted_count = 0

        try:
            # SQLite версия
            cursor = db.conn.cursor()

            if target.startswith('@'):
                cursor.execute(
                    "SELECT user_id FROM users WHERE username = ?",
                    (target[1:],)
                )
                user_row = cursor.fetchone()
                if not user_row:
                    await update.message.reply_text("❌ Пользователь не найден")
                    return
                target_user_id = user_row[0]
            else:
                target_user_id = target

            # Очищаем данные и считаем количество
            cursor.execute("DELETE FROM conversation_sessions WHERE user_id = ?", (target_user_id,))
            deleted_count += cursor.rowcount

            cursor.execute("DELETE FROM business_snapshots WHERE business_id IN (SELECT business_id FROM businesses WHERE user_id = ?)", (target_user_id,))
            deleted_count += cursor.rowcount

            cursor.execute("DELETE FROM businesses WHERE user_id = ?", (target_user_id,))
            deleted_count += cursor.rowcount

            cursor.execute("DELETE FROM users WHERE user_id = ?", (target_user_id,))
            deleted_count += cursor.rowcount

            db.conn.commit()

            await update.message.reply_text(
                f"✅ Данные пользователя `{target}` очищены!\\n"
                f"🗑️ Удалено записей: {deleted_count}",
                parse_mode='MarkdownV2'
            )

        except Exception as e:
            logger.error(f"Ошибка очистки: {e}")
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        user = update.effective_user
        user_id = str(user.id)

        logger.info(f"💬 Сообщение от {user.first_name} (ID: {user_id}): {user_text}")

        await db.save_user(user_id, user.username, user.first_name, user.last_name)

        # ПРОВЕРЯЕМ АКТИВНУЮ СЕССИЮ ДИАЛОГА
        if user_id in conv_manager.active_sessions:
            await self._handle_conversation_message(update, user_id, user_text)
            return

        # Игнорируем команды на этом этапе, они обрабатываются CommandHandler
        if user_text.startswith('/'):
            return

        thinking_msg = await update.message.reply_text(
            safe_markdown_text("🤔 *Анализирую сообщение...*"),
            parse_mode='MarkdownV2'
        )

        try:
            message_type = await classify_message_type(user_text)
            logger.info(f"🎯 Определен тип сообщения: {message_type}")

            if message_type == "business_data":
                # Ненавязчивая подсказка и продолжаем отвечать по сути сообщения
                try:
                    await update.message.reply_text(
                        "ℹ️ Чтобы создать бизнес используйте команду: /new_business"
                    )
                except Exception:
                    pass
                # Продолжаем как свободный диалог
                message_type = "general"

            try:
                await thinking_msg.edit_text(
                    self.get_thinking_message(message_type),
                    parse_mode='MarkdownV2'
                )
            except Exception:
                # Игнорируем 'Message is not modified'
                pass

            if message_type == "question":
                response = await self.handle_question(user_text, user_id)
                try:
                    await db.log_message(
                        session_id=None if user_id not in conv_manager.active_sessions else conv_manager.active_sessions[user_id].session_id,
                        user_message=user_text,
                        bot_response=response,
                        message_type='question'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось записать вопрос в БД: {e}")
                await self.send_long_message(update, response)
            else:  # general
                response = await self.handle_general_chat(user_text, user_id)
                try:
                    await db.log_message(
                        session_id=None if user_id not in conv_manager.active_sessions else conv_manager.active_sessions[user_id].session_id,
                        user_message=user_text,
                        bot_response=response,
                        message_type='general'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось записать общение в БД: {e}")
                await self.send_long_message(update, response, None)

            logger.info(f"🤖 Ответ бота ({message_type}): {response[:100]}...")

            await thinking_msg.delete()

        except Exception as e:
            error_msg = safe_markdown_text("❌ *Произошла ошибка при обработке запроса*. Попробуйте еще раз.")
            logger.error(f"Ошибка обработки сообщения: {e}")
            await thinking_msg.edit_text(error_msg, parse_mode='MarkdownV2')

    def get_thinking_message(self, message_type: str) -> str:
        """Сообщение о процессе обработки"""
        messages = {
            "question": "💭 *Обдумываю ответ\\.\\.\\.*\n_Ищу лучшие решения для вашего бизнеса_",
            "general": "💬 *Общаюсь\\.\\.\\.*\n_Всегда рад поболтать_"
        }
        return messages.get(message_type, "🤔 *Думаю\\.\\.\\.*")


    async def _handle_conversation_message(self, update: Update, user_id: str, user_text: str):
        """Обработка сообщения в рамках активной диалоговой сессии"""
        try:
            conversation = conv_manager.active_sessions[user_id]
            
            # Прогресс СРАЗУ после сообщения пользователя
            progress_msg = None
            try:
                progress_msg = await update.message.reply_text(
                    safe_markdown_text("🛠 *Делаю отчёт...*"),
                    parse_mode='MarkdownV2'
                )
            except Exception:
                pass
            
            # Обрабатываем сообщение
            response_data = await conversation.process_message(user_text)

            # Заменяем прогресс-сообщение на результат
            if progress_msg:
                try:
                    await progress_msg.edit_text(response_data['response'], parse_mode='MarkdownV2')
                except Exception:
                    # Если не удалось заменить, отправляем новое сообщение
                    await self.send_long_message(update, response_data['response'], 'MarkdownV2')
            else:
                await self.send_long_message(update, response_data['response'], 'MarkdownV2')
            
            try:
                await db.log_message(
                    session_id=conversation.session_id,
                    user_message=user_text,
                    bot_response=response_data['response'],
                    message_type='conversation'
                )
            except Exception as e:
                logger.warning(f"Не удалось записать сообщение в БД: {e}")

            # Если диалог завершен
            if response_data.get('is_complete', False):
                # Если анализ уже выполнен conversation_manager-ом (обычно так и есть)
                if response_data.get('next_action') == 'analysis_complete':
                    pass

                # Завершаем сессию
                conv_manager.end_conversation(user_id)
                logger.info(f"✅ Диалоговая сессия завершена для пользователя {user_id}")

        except Exception as e:
            logger.error(f"Ошибка в диалоговой сессии для пользователя {user_id}: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка в диалоге. Давайте начнем заново, попробуйте /new_business.",
                parse_mode='Markdown'
            )
            conv_manager.end_conversation(user_id)

    async def handle_question(self, text: str, user_id: str) -> str:
        """Обработка вопросов. Возвращает ответ."""
        answer = await answer_question(text, user_id)
        return clean_ai_text(answer)

    async def handle_general_chat(self, text: str, user_id: str) -> str:
        """Обработка общего чата. Возвращает ответ."""
        response = await general_chat(text, user_id)
        return clean_ai_text(response)

    # Отправляем ответ с возможным разделением
    async def send_long_message(self, update_or_query_object, text: str, parse_mode: str = None):
        """
        Элегантное разделение длинного сообщения на части и отправка.
        Принимает update или query объект для отправки сообщения.
        """
        MAX_LENGTH = 3800  # Максимальная длина сообщения Telegram с запасом

        # Важно! Применяем safe_markdown_text до разделения и отправки
        final_text_to_send = safe_markdown_text(text) if parse_mode == 'MarkdownV2' else text

        if len(final_text_to_send) <= MAX_LENGTH:
            if hasattr(update_or_query_object, 'message'):
                await update_or_query_object.message.reply_text(final_text_to_send, parse_mode=parse_mode)
            else: # Это CallbackQuery
                await update_or_query_object.edit_message_text(final_text_to_send, parse_mode=parse_mode)
            return

        parts = self.split_message_smart(final_text_to_send, MAX_LENGTH)

        for i, part in enumerate(parts):
            prefix = ""
            if len(parts) > 1:
                prefix = f"📄 ({i+1}/{len(parts)})\\n\\n" # Этот префикс тоже может содержать markdown символы

            current_part_to_send = prefix + part

            try:
                # Безопасная отправка с MarkdownV2
                safe_text = safe_markdown_text(current_part_to_send)
                if hasattr(update_or_query_object, 'message'):
                    await update_or_query_object.message.reply_text(safe_text, parse_mode='MarkdownV2')
                else:
                    if i == 0:
                        await update_or_query_object.edit_message_text(safe_text, parse_mode='MarkdownV2')
                    else:
                        user_id = update_or_query_object.from_user.id
                        await self.app.bot.send_message(chat_id=user_id, text=safe_text, parse_mode='MarkdownV2')

                if i < len(parts) - 1:
                    await asyncio.sleep(0.7)

            except Exception as e:
                logger.error(f"Ошибка отправки части {i+1}: {e}. Текст: {current_part_to_send[:200]}...")
                # Повторная попытка без MarkdownV2 (если ошибка парсинга)
                try:
                    if hasattr(update_or_query_object, 'message'):
                        await update_or_query_object.message.reply_text(f"Часть {i+1} (без форматирования):\n{part}")
                    else:
                        user_id = update_or_query_object.from_user.id
                        await self.app.bot.send_message(chat_id=user_id, text=f"Часть {i+1} (без форматирования):\n{part}")
                except Exception as e2:
                    logger.error(f"Критическая ошибка при отправке части сообщения пользователю {user_id}: {e2}")


    async def start_business_dialog(self, update: Update, user_id: str, business_text: str):
        """Начало диалога для анализа бизнеса из сообщения с данными"""
        try:
            # Получаем сессию диалога
            conversation = await conv_manager.get_conversation(user_id)

            # Пропускаем шаг названия и сразу переходим к сбору данных
            # Если бизнес_нейм не указан в сообщении, используем заполнитель
            extracted_data = await extract_business_data(business_text)
            business_name = extracted_data.get('business_name', 'Анализируемый бизнес')

            await conversation.initialize(user_id) # Начинаем новую сессию
            conversation.collected_data = extracted_data # Присваиваем извлеченные данные
            conversation.collected_data['business_name'] = business_name
            conversation.business_id = await db.create_business(user_id, business_name) # Создаем бизнес в БД
            await conversation._update_state(conversation.STATES['COLLECTING_DATA']) # Переходим в состояние сбора данных

            # Обрабатываем сообщение с данными
            response_data = await conversation.process_message(business_text)

            # Отправляем ответ с возможным разделением
            await self.send_long_message(update, response_data['response'], 'Markdown')

            # Если диалог завершен
            if response_data.get('is_complete', False):
                conv_manager.end_conversation(user_id)
                logger.info(f"✅ Диалоговая сессия завершена для пользователя {user_id}")

        except Exception as e:
            logger.error(f"Ошибка в автодиалоге: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте снова или используйте команду /new_business",
                parse_mode='Markdown'
            )

    def split_message_smart(self, text: str, max_length: int) -> list:
        """
        Умное разделение текста на части, стараясь сохранить целостность предложений и абзацев.
        """
        if len(text) <= max_length:
            return [text]

        parts = []
        current_part = ""

        # Разделение по абзацам
        paragraphs = text.split('\n\n')

        for paragraph in paragraphs:
            # Если абзац сам по себе слишком длинный, делим его на предложения
            if len(paragraph) > max_length:
                sentences = self.split_by_sentences(paragraph)
                for sentence in sentences:
                    # Проверяем, поместится ли предложение в текущую часть
                    if len(current_part) + len(sentence) + 2 <= max_length: # +2 для переноса строки
                        current_part += ("\n" if current_part else "") + sentence
                    else:
                        # Если не помещается, завершаем текущую часть и начинаем новую
                        if current_part:
                            parts.append(current_part.strip())
                        current_part = sentence
            else:
                # Если абзац помещается в текущую часть
                if len(current_part) + len(paragraph) + 4 <= max_length: # +4 для двойного переноса
                    current_part += ("\n\n" if current_part else "") + paragraph
                else:
                    # Если не помещается, завершаем текущую часть и начинаем новую
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = paragraph

        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part.strip())

        return parts

    def split_by_sentences(self, text: str) -> list:
        """
        Разделение текста на предложения.
        """
        import re
        # Используем regex для разделения по точкам, восклицательным и вопросительным знакам
        # (с учетом невидимых символов для русских текстов)
        sentences = re.split(r'(?<=[.!?…])\s+|(?<=[.!?…]["\'])', text)
        return [s.strip() for s in sentences if s.strip()]

    def escape_markdown(self, text: str) -> str:
        """Экранирует все спецсимволы Markdown для Telegram Bot API v2"""
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        for char in escape_chars:
            text = text.replace(char, '\\' + char)
        return text

    async def run_async(self):
        """Асинхронный запуск бота"""
        print("Bot is starting...")

        # Инициализация БД
        import sqlite3
        import os
        # asyncio уже импортирован в начале файла, нет необходимости импортировать его снова

        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'business_bot_v2.db')
        db.conn = sqlite3.connect(db_path, check_same_thread=False)
        await db.init_db()
        print(f"Database connected: {db_path}")

        print("Smart message classification enabled")
        print("Advanced analytics with 22 metrics")
        print("Activity logging enabled")
        print("User context memory enabled")
        print("Free-form dialog enabled")

        # ПРАВИЛЬНЫЙ ЗАПУСК для версии 20.7
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        # Бесконечный цикл
        await asyncio.Event().wait()

# Убедитесь, что здесь нет "bot = BusinessBot()" или других вызовов экземпляра бота