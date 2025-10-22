from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from ai import classify_message_type, general_chat, answer_question, extract_business_data, conversation_memory
from conversation_manager import conv_manager
from business_analyzer import business_analyzer
from database import db
from metrics_help import get_categories_keyboard, get_metrics_keyboard, get_metric_description, get_category_description
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import asyncio
from typing import Dict, List
from datetime import datetime
from telegram.helpers import escape_markdown
from env_utils import is_production, get_log_dir, should_create_files
from report_formatter import format_business_report, get_health_assessment
import sys

logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if should_create_files():
    LOG_DIR = get_log_dir() or os.path.join(BASE_DIR, 'logs')
    os.makedirs(LOG_DIR, exist_ok=True)
else:
    LOG_DIR = None

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
            pass

handlers = []

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
handlers.append(stream_handler)

if should_create_files() and LOG_DIR:
    file_handler = DailyFileHandler(LOG_DIR)
    handlers.append(file_handler)

logging.basicConfig(
    level=logging.INFO,
    handlers=handlers,
    force=True
)
logger = logging.getLogger(__name__)

ADMINS = [
    "1287604685",
]

def safe_markdown_text(text: str) -> str:
    """
    Безопасное форматирование Markdown с сохранением жирного текста
    """
    safe_text = escape_markdown(text, version=2)
    safe_text = safe_text.replace(r'\*', '*')
    return safe_text

def clean_ai_text(text: str) -> str:
    """
    Очистка AI-текста от Markdown форматирования для безопасной отправки
    """
    import re
    
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\\\[', '[', text)
    text = re.sub(r'\\\]', ']', text)
    
    return text
    
print("Запуск бота....")

class BusinessBot:
    def __init__(self):
        token = (
            os.getenv("BOT_TOKEN")
            or os.getenv("TELEGRAM_BOT_TOKEN")
            or os.getenv("TOKEN")
        )
        if not token:
            raise ValueError("BOT_TOKEN environment variable is required (try BOT_TOKEN or TELEGRAM_BOT_TOKEN)")
        
        self.app = Application.builder().token(token).concurrent_updates(True).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("guide", self.guide_command))
        self.app.add_handler(CommandHandler("about", self.about_command))
        self.app.add_handler(CommandHandler("history", self.history_command))
        self.app.add_handler(CommandHandler("help_metrics", self.help_metrics_command))
        self.app.add_handler(CommandHandler("new_business", self.new_business_command))
        self.app.add_handler(CommandHandler("edit_business", self.edit_business_command))
        self.app.add_handler(CommandHandler("delete_business", self.delete_business_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_inline_buttons))
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

        await db.save_user(user_id, user.username, user.first_name, user.last_name)

        text = safe_markdown_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Я *Финансовый Луч* - ваш персональный AI-аналитик для бизнеса! 💰\n\n"
            "Я помогу вам:\n"
            "• Проанализировать финансовое состояние бизнеса\n"
            "• Рассчитать ключевые метрики и показатели\n"
            "• Получить персональные рекомендации\n"
            "• Отслеживать динамику развития\n\n"
            "Просто отправьте мне информацию о вашем бизнесе, и я проведу полный анализ! 📊\n\n"
            "Для начала работы используйте /guide - там есть примеры того, как правильно описать ваш бизнес!\n"
            "Полный список команд: /help"
        )

        await update.message.reply_text(text, parse_mode='MarkdownV2')

    async def help_metrics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справочник по метрикам"""
        try:
            user_id = str(update.effective_user.id)
            await db.save_user(
                user_id=user_id,
                username=update.effective_user.username or "",
                first_name=update.effective_user.first_name or "",
                last_name=update.effective_user.last_name or ""
            )
            
            message = "📚 **СПРАВОЧНИК ПО БИЗНЕС-МЕТРИКАМ**\n\n"
            message += "Выберите категорию метрик для подробного изучения:\n\n"
            message += "• **💰 Рентабельность** - метрики прибыльности\n"
            message += "• **📈 Рост** - метрики развития бизнеса\n"
            message += "• **👥 Клиенты** - метрики работы с клиентами\n"
            message += "• **🛡️ Безопасность** - метрики финансовой устойчивости\n"
            message += "• **🏥 Здоровье** - общие показатели здоровья бизнеса"
            
            keyboard = get_categories_keyboard()
            await update.message.reply_text(
                safe_markdown_text(message),
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка команды help_metrics: {e}")
            await update.message.reply_text("❌ Произошла ошибка при загрузке справочника.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"ℹ️ Пользователь {user.first_name} запросил помощь")

        text = safe_markdown_text(
            "*📋 ДОСТУПНЫЕ КОМАНДЫ*\n\n"
            "*Основные команды:*\n"
            "/start - начать работу с ботом\n"
            "/help - показать это сообщение\n"
            "/about - подробная информация о проекте\n"
            "/guide - примеры использования и инструкции\n\n"
            "*Работа с бизнесом:*\n"
            "/new_business - создать новый бизнес 🆕\n"
            "/edit_business - редактировать существующий бизнес ✏️\n"
            "/delete_business - удалить бизнес 🗑️\n"
            "/history - история всех анализов 📊\n\n"
            "*Справочники:*\n"
            "/help_metrics - справочник по метрикам 📚\n\n"
            "*Как использовать:*\n"
            "1. Отправьте информацию о вашем бизнесе одним сообщением\n"
            "2. ИИ автоматически извлечет все нужные данные\n"
            "3. Получите полный анализ с метриками и рекомендациями\n\n"
            "*Примеры вопросов:*\n"
            "• \"Как увеличить прибыль?\"\n"
            "• \"Какие метрики важны для моего бизнеса?\"\n"
            "• \"Как рассчитать точку безубыточности?\"\n\n"
            "💡 *Совет:* Используйте /guide для подробных примеров!"
        )
        await update.message.reply_text(text, parse_mode='MarkdownV2')

    async def guide_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда с примерами использования"""
        user = update.effective_user
        logger.info(f"📖 Пользователь {user.first_name} запросил руководство")

        text = safe_markdown_text(
            "*📖 РУКОВОДСТВО ПО ИСПОЛЬЗОВАНИЮ*\n\n"
            "*Как правильно описать ваш бизнес:*\n\n"
            "*Пример 1 - Полное описание:*\n"
            "\"Мой бизнес называется 'Кофейня на углу'. Выручка 500000 рублей в месяц, расходы 300000 рублей. У меня 150 клиентов, средний чек 3300 рублей. Инвестиции составили 2000000 рублей. На маркетинг трачу 50000 рублей в месяц. У меня работает 5 сотрудников. Каждый месяц приходит 20 новых клиентов, удержание клиентов 80%.\"\n\n"
            "*Пример 2 - Краткое описание:*\n"
            "\"Кафе: выручка 300к, расходы 200к, 100 клиентов, средний чек 3к, инвестиции 1млн, маркетинг 30к, 3 сотрудника.\"\n\n"
            "*Пример 3 - Только основные данные:*\n"
            "\"Магазин одежды: доходы 800000, траты 500000, клиентов 200, чек 4000.\"\n\n"
            "*Что можно указывать:*\n"
            "• Название бизнеса\n"
            "• Выручку/доходы\n"
            "• Расходы/траты\n"
            "• Количество клиентов\n"
            "• Средний чек\n"
            "• Инвестиции\n"
            "• Затраты на маркетинг\n"
            "• Количество сотрудников\n"
            "• Новых клиентов в месяц\n"
            "• Процент удержания клиентов\n\n"
            "*💡 Совет:* Чем больше данных вы укажете, тем точнее будет анализ!\n\n"
            "*После отправки данных вы получите:*\n"
            "• Полный финансовый анализ\n"
            "• 22 ключевые метрики\n"
            "• Оценку здоровья бизнеса\n"
            "• Персональные рекомендации\n\n"
            "🚀 *Готовы начать? Отправьте данные о вашем бизнесе!*"
        )
        await update.message.reply_text(text, parse_mode='MarkdownV2')

    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"ℹ️ Пользователь {user.first_name} запросил информацию о боте")

        main_text = safe_markdown_text(
            "*💸 ФИНАНСОВЫЙ ЛУЧ 💸*\n\n"
            "*О проекте:*\n"
            "Финансовый Луч - это интеллектуальный помощник для анализа и управления бизнесом, разработанный в рамках проекта \"Инженеры будущего\".\n\n"
            "*Возможности:*\n"
            "• Умный диалог с ИИ для сбора данных\n"
            "• Расчет 22 ключевых финансовых метрик\n"
            "• Business Health Score - оценка здоровья бизнеса\n"
            "• Персональные AI-рекомендации\n"
            "• Сохранение и отслеживание истории развития\n"
            "• Интерактивный справочник по метрикам\n\n"
            "*Технологии:*\n"
            "• GPT-4 для интеллектуального анализа\n"
            "• Продвинутые финансовые формулы\n"
            "• PostgreSQL база данных\n"
            "• Асинхронная архитектура\n\n"
            "*Команды:*\n"
            "/start - начать работу\n"
            "/help - помощь\n"
            "/guide - примеры использования\n"
            "/new_business - новый бизнес\n"
            "/history - история анализов\n"
            "/help_metrics - справочник метрик\n\n"
            "🚀 *Полный анализ вашего бизнеса!*"
        )
        
        license_text = ">Финансовый луч © 2025 by Lavrinov Maxim is licensed under CC BY\\-NC 4\\.0\\. To view a copy of this license, visit https://creativecommons\\.org/licenses/by\\-nc/4\\.0/"
        
        text = main_text + "\n\n" + license_text
        await update.message.reply_text(text, parse_mode='MarkdownV2')

    async def new_business_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Новая команда - создание бизнеса с умным диалогом"""
        user = update.effective_user
        user_id = str(user.id)

        logger.info(f"🆕 Пользователь {user.first_name} создает новый бизнес")

        text = safe_markdown_text(
            "*🆕 СОЗДАНИЕ НОВОГО БИЗНЕСА*\n\n"
            "Отправьте мне всю информацию о вашем бизнесе одним сообщением!\n\n"
            "*Что можно указать:*\n"
            "• Название бизнеса\n"
            "• Выручку/доходы\n"
            "• Расходы/траты\n"
            "• Количество клиентов\n"
            "• Средний чек\n"
            "• Инвестиции\n"
            "• Затраты на маркетинг\n"
            "• Количество сотрудников\n"
            "• Новых клиентов в месяц\n"
            "• Процент удержания клиентов\n\n"
            "*Пример:*\n"
            "\"Мой бизнес 'Кофейня на углу': выручка 500000 рублей в месяц, расходы 300000, 150 клиентов, средний чек 3300, инвестиции 2000000, маркетинг 50000, 5 сотрудников, 20 новых клиентов в месяц, удержание 80%.\"\n\n"
            "💡 *Совет:* Используйте /guide для подробных примеров!\n\n"
            "📝 *Отправьте данные о вашем бизнесе:*"
        )
        
        await update.message.reply_text(text, parse_mode='MarkdownV2')
        
        # Ставим флаг: следующее сообщение пользователя будет обработано как свободный ввод данных
        if not hasattr(self, 'awaiting_business_data'):
            self.awaiting_business_data = set()
        self.awaiting_business_data.add(user_id)

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
                safe_markdown_text("❌ Произошла ошибка при получении списка бизнесов. Попробуйте позже."),
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
                safe_markdown_text("❌ Произошла ошибка. Попробуйте позже."),
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
            keyboard = []
            for i, business in enumerate(businesses[:10], 1):
                business_name = business.get('business_name', f'Бизнес #{i}')
                business_id = business.get('business_id')
                try:
                    history = await db.get_business_history(business_id, limit=1)
                    if history:
                        health_score = history[0].get('overall_health_score', 0)
                        button_text = f"📊 {business_name} (Health: {health_score}/100)"
                    else:
                        button_text = f"📊 {business_name}"
                except Exception as e:
                    logger.warning(f"Ошибка получения Health Score для бизнеса {business_id}: {e}")
                    button_text = f"📊 {business_name}"
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
                safe_markdown_text("❌ Произошла ошибка при получении истории. Попробуйте позже."),
                parse_mode='MarkdownV2'
            )

    async def handle_inline_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка inline кнопок"""
        query = update.callback_query
        await query.answer()

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
        elif query.data.startswith('metrics_cat_'):
            category_id = query.data.replace('metrics_cat_', '')
            await self.show_metrics_category(query, category_id)
        elif query.data.startswith('metrics_detail_'):
            metric_id = query.data.replace('metrics_detail_', '')
            await self.show_metric_detail(query, metric_id)
        elif query.data == 'metrics_back':
            await self.show_metrics_categories(query)
        elif query.data == 'metrics_close':
            await query.edit_message_text("📚 Справочник закрыт. Используйте /help_metrics для повторного открытия.")

    async def show_metrics_categories(self, query: CallbackQuery):
        """Показ категорий метрик"""
        try:
            message = "📚 **СПРАВОЧНИК ПО БИЗНЕС-МЕТРИКАМ**\n\n"
            message += "Выберите категорию метрик для подробного изучения:\n\n"
            message += "• **💰 Рентабельность** - метрики прибыльности\n"
            message += "• **📈 Рост** - метрики развития бизнеса\n"
            message += "• **👥 Клиенты** - метрики работы с клиентами\n"
            message += "• **🛡️ Безопасность** - метрики финансовой устойчивости\n"
            message += "• **🏥 Здоровье** - общие показатели здоровья бизнеса"
            
            keyboard = get_categories_keyboard()
            await query.edit_message_text(
                safe_markdown_text(message),
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка показа категорий метрик: {e}")
            await query.edit_message_text("❌ Произошла ошибка при загрузке категорий.")

    async def show_metrics_category(self, query: CallbackQuery, category_id: str):
        """Показ метрик выбранной категории"""
        try:
            description = get_category_description(category_id)
            keyboard = get_metrics_keyboard(category_id)
            
            if keyboard is None:
                await query.edit_message_text("❌ Категория не найдена")
                return

            await query.edit_message_text(
                safe_markdown_text(description),
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка показа метрик категории: {e}")
            await query.edit_message_text("❌ Произошла ошибка при загрузке метрик.")

    async def show_metric_detail(self, query: CallbackQuery, metric_id: str):
        """Показ подробного описания метрики"""
        try:
            description = get_metric_description(metric_id)
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="metrics_back")
            ]])
            
            await query.edit_message_text(
                safe_markdown_text(description),
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка показа деталей метрики: {e}")
            await query.edit_message_text("❌ Произошла ошибка при загрузке описания метрики.")

    async def show_business_details(self, query: CallbackQuery, business_id: int):
        """Показ деталей бизнеса по запросу Inline кнопки"""
        try:
            # Получаем историю
            history = await db.get_business_history(business_id, limit=1)
            if not history:
                await query.edit_message_text("❌ Бизнес не найден")
                return
            
            current_data = history[0]
            
            # Получаем метрики и рекомендации
            report = await business_analyzer.generate_business_report(business_id)
            metrics = report.get('detailed_metrics', {}) if 'error' not in report else {}
            recommendations = report.get('recommendations', []) if 'error' not in report else {}
            # Используем данные из БД, а не из отчета
            raw_data = current_data
            
            # Используем единый формат отчета
            response = format_business_report(raw_data, metrics, recommendations)

            # Удаляем меню и отправляем отчет
            await query.edit_message_text("📊 *Делаю отчет\\.\\.\\.*", parse_mode='MarkdownV2')
            await self.send_long_message(query, response, parse_mode='MarkdownV2')
            
            # Удаляем сообщение "Загружаю отчет"
            try:
                await query.delete_message()
            except Exception:
                pass

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
                'employees': current_data.get('employees', 0),
                'new_clients_per_month': current_data.get('new_clients_per_month', 0),
                'customer_retention_rate': current_data.get('customer_retention_rate', 0)
            }
            
            await conversation._update_state(conversation.STATES['COLLECTING_DATA'])
            
            # Получаем метрики и рекомендации для отображения
            report = await business_analyzer.generate_business_report(business_id)
            metrics = report.get('detailed_metrics', {}) if 'error' not in report else {}
            recommendations = report.get('recommendations', []) if 'error' not in report else []
            
            # Используем единый формат отчета
            response = f"✏️ *РЕДАКТИРОВАНИЕ: {business_name}*\n\n"
            response += format_business_report(current_data, metrics, recommendations)
            response += f"\n\nОтправьте новые данные в свободной форме или напишите 'да' для завершения.\n\n"
            response += f"Чтобы отменить без изменений — напишите 'выйти'"
            
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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        user = update.effective_user
        user_id = str(user.id)

        logger.info(f"💬 Сообщение от {user.first_name} (ID: {user_id}): {user_text}")

        await db.save_user(user_id, user.username, user.first_name, user.last_name)

        # Если ждём первое сообщение для нового бизнеса – сразу собираем данные без стартового промпта
        if hasattr(self, 'awaiting_business_data') and user_id in self.awaiting_business_data:
            try:
                conversation = await conv_manager.get_conversation(user_id)
                await conversation._update_state(conversation.STATES['COLLECTING_DATA'])
                progress_msg = None
                try:
                    progress_msg = await update.message.reply_text(
                        "🛠 *Делаю отчёт\\.\\.\\.*",
                        parse_mode='MarkdownV2'
                    )
                except Exception:
                    pass
                response_data = await conversation._handle_data_collection(user_text)
                if progress_msg:
                    try:
                        await progress_msg.edit_text(
                            safe_markdown_text(response_data['response']),
                            parse_mode='MarkdownV2'
                        )
                    except Exception:
                        try:
                            await progress_msg.delete()
                        except Exception:
                            pass
                        await self.send_long_message(update, response_data['response'], 'Markdown')
                else:
                    await self.send_long_message(update, response_data['response'], 'Markdown')
            finally:
                self.awaiting_business_data.discard(user_id)
            return

        try:
            from ai import conversation_memory as ai_memory
            if user_id not in ai_memory or len(ai_memory[user_id]) == 0:
                recent = await db.get_user_recent_messages(user_id, limit=20)
                history = []
                for msg in recent:
                    if msg.get('user_message'):
                        history.append({"role": "user", "content": msg['user_message']})
                    if msg.get('bot_response'):
                        history.append({"role": "assistant", "content": msg['bot_response']})
                if history:
                    ai_memory[user_id] = history[-12:]
        except Exception as e:
            logger.warning(f"Не удалось гидрировать историю из БД: {e}")

        if user_id in conv_manager.active_sessions:
            await self._handle_conversation_message(update, user_id, user_text)
            return

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
                try:
                    await update.message.reply_text(
                        "ℹ️ Чтобы создать бизнес используйте команду: /new_business"
                    )
                except Exception:
                    pass
                message_type = "general"

            if message_type == "general":
                import asyncio
                await asyncio.sleep(0.1)
                try:
                    await thinking_msg.edit_text(
                        "💬 *Общаюсь\\.\\.\\.*\n_Всегда рад поболтать_",
                        parse_mode='MarkdownV2'
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка обновления на 'общаюсь': {e}")
            elif message_type == "question":
                try:
                    await thinking_msg.edit_text(
                        "💭 *Обдумываю ответ\\.\\.\\.*\n_Ищу лучшие решения для вашего бизнеса_",
                        parse_mode='MarkdownV2'
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка обновления на 'обдумываю': {e}")

            if message_type == "question":
                response = await self.handle_question(user_text, user_id)
                try:
                    session_id = None if user_id not in conv_manager.active_sessions else conv_manager.active_sessions[user_id].session_id
                    if session_id is None:
                        session_id = await db.get_or_create_user_chat_session(user_id)
                    await db.log_message(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_text,
                        bot_response=response,
                        message_type='question'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось записать вопрос в БД: {e}")
                await self.send_long_message(update, response)
            else:
                response = await self.handle_general_chat(user_text, user_id)
                try:
                    session_id = None if user_id not in conv_manager.active_sessions else conv_manager.active_sessions[user_id].session_id
                    if session_id is None:
                        session_id = await db.get_or_create_user_chat_session(user_id)
                    await db.log_message(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_text,
                        bot_response=response,
                        message_type='general'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось записать общение в БД: {e}")
                await self.send_long_message(update, response, None)
            
            try:
                await thinking_msg.delete()
            except Exception:
                pass

            logger.info(f"🤖 Ответ бота ({message_type}): {response[:20]}...")

        except Exception as e:
            error_msg = safe_markdown_text("❌ *Произошла ошибка при обработке запроса*. Попробуйте еще раз.")
            logger.error(f"Ошибка обработки сообщения: {e}")
            await thinking_msg.edit_text(error_msg, parse_mode='MarkdownV2')


    def get_thinking_message(self, message_type: str) -> str:
        """Сообщение о процессе обработки"""
        messages = {
            "question": "💭 *Обдумываю ответ...*\n_Ищу лучшие решения для вашего бизнеса_",
            "general": "💬 *Общаюсь...*\n_Всегда рад поболтать_"
        }
        return messages.get(message_type, "🤔 *Думаю...*")


    async def _handle_conversation_message(self, update: Update, user_id: str, user_text: str):
        """Обработка сообщения в рамках активной диалоговой сессии"""
        try:
            conversation = conv_manager.active_sessions[user_id]

            # Прогресс СРАЗУ после сообщения пользователя
            progress_msg = None
            try:
                progress_msg = await update.message.reply_text(
                    "🛠 *Делаю отчёт\\.\\.\\.*",
                    parse_mode='MarkdownV2'
                )
            except Exception:
                pass

            # Обрабатываем сообщение
            response_data = await conversation.process_message(user_text)

            # Заменяем прогресс-сообщение на результат
            if progress_msg:
                try:
                    # Пробуем заменить сообщение
                    await progress_msg.edit_text(
                        safe_markdown_text(response_data['response']),
                        parse_mode='MarkdownV2'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось заменить прогресс-сообщение: {e}")
                    try:
                        # Если не получилось заменить, удаляем прогресс-сообщение
                        await progress_msg.delete()
                    except Exception:
                        pass
                    # Отправляем новое сообщение
                    await self.send_long_message(update, response_data['response'], 'Markdown')
            else:
                await self.send_long_message(update, response_data['response'], 'Markdown')
            
            try:
                await db.log_message(
                    user_id=user_id,
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
        MAX_LENGTH = 3800
        final_text_to_send = safe_markdown_text(text) if parse_mode == 'MarkdownV2' else text

        if len(final_text_to_send) <= MAX_LENGTH:
            if hasattr(update_or_query_object, 'message'):
                await update_or_query_object.message.reply_text(final_text_to_send, parse_mode=parse_mode)
            else:
                await update_or_query_object.edit_message_text(final_text_to_send, parse_mode=parse_mode)
            return

        parts = self.split_message_smart(final_text_to_send, MAX_LENGTH)

        for i, part in enumerate(parts):
            prefix = ""
            if len(parts) > 1:
                prefix = f"📄 ({i+1}/{len(parts)})\n\n" # Этот префикс тоже может содержать markdown символы

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
        current_part 

        paragraphs = text.split('\n\n')

        for paragraph in paragraphs:
            if len(paragraph) > max_length:
                sentences = self.split_by_sentences(paragraph)
                for sentence in sentences:
                    if len(current_part) + len(sentence) + 2 <= max_length:
                        current_part += ("\n" if current_part else "") + sentence
                    else:
                        if current_part:
                            parts.append(current_part.strip())
                        current_part = sentence
            else:
                if len(current_part) + len(paragraph) + 4 <= max_length:
                    current_part += ("\n\n" if current_part else "") + paragraph
                else:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = paragraph

        if current_part:
            parts.append(current_part.strip())

        return parts

    def split_by_sentences(self, text: str) -> list:
        """
        Разделение текста на предложения.
        """
        import re
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

        import sqlite3
        import os

        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'business_bot_v2.db')
        db.conn = sqlite3.connect(db_path, check_same_thread=False)
        await db.init_db()

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        await asyncio.Event().wait()
