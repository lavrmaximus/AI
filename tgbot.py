from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ai import *
import logging
from datetime import datetime

logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8350333926:AAEkf4If4LXh657SOTuGsAhEJx6EFSPKHbU"

print("Bot started")
class BusinessBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("about", self.about_command))
        self.app.add_handler(CommandHandler("analysis", self.analysis_command))
        self.app.add_handler(CommandHandler("history", self.history_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        
        # Логируем начало работы
        logger.info(f"🆕 Новый пользователь: {user.first_name} (ID: {user_id}, @{user.username})")
        
        # Сохраняем пользователя в базу
        await db.save_user(user_id, user.username, user.first_name, user.last_name)
        
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Я - твой продвинутый AI-аналитик! 🚀\n\n"
            "📊 *Что я умею:*\n"
            "• Автоматически определять тип сообщения\n"
            "• Анализировать бизнес с финансовыми формулами\n"
            "• Отвечать на вопросы о бизнесе\n"
            "• Запоминать всю историю диалога\n"
            "• Сохранять данные в базу\n\n"
            "💡 *Просто напиши:*\n"
            "• О своем бизнесе с цифрами\n"
            "• Вопрос о бизнесе\n"
            "• Или просто поздоровайся!\n\n"
            "🤖 *Новые возможности:*\n"
            "/history - посмотреть историю анализов",
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"ℹ️  Пользователь {user.first_name} запросил помощь")
        
        help_text = (
            "📋 *Доступные команды:*\n\n"
            "/start - начать работу\n"
            "/help - помощь\n"  
            "/about - о проекте\n"
            "/analysis - запустить анализ\n"
            "/history - история анализов\n\n"
            "💬 *Умное определение типов:*\n"
            "• *Бизнес-анализ:* 'Выручка 500к, расходы 200к, 100 клиентов'\n"
            "• *Вопрос:* 'Как увеличить прибыль?'\n"
            "• *Общение:* 'Привет! Как дела?'\n\n"
            "🎯 Я сам определю тип сообщения и отвечу соответственно!"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"ℹ️  Пользователь {user.first_name} запросил информацию о боте")
        
        about_text = (
            "🤖 *Business Intelligence AI Assistant*\n\n"
            "📈 *Расширенная аналитика:*\n"
            "• Финансовые формулы и метрики\n"
            "• Автоматическая классификация\n"  
            "• Анализ рентабельности\n"
            "• Расчет точки безубыточности\n"
            "• Сохранение истории в БД\n\n"
            "🧠 *Умные ответы:*\n"
            "• AI-классификация сообщений\n"
            "• Контекстная память\n"
            "• Персонализированные рекомендации\n\n"
            "💾 *База данных:*\n"
            "• PostgreSQL на Render.com\n"
            "• Сохранение всех диалогов\n"
            "• История бизнес-анализов\n\n"
            "🚀 *Постоянное развитие!*"
        )
        await update.message.reply_text(about_text, parse_mode='Markdown')
    
    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"🔍 Пользователь {user.first_name} запустил анализ")
        
        await update.message.reply_text(
            "🔍 *Режим бизнес-анализа активирован!*\n\n"
            "Расскажи о своем бизнесе с цифрами:\n"
            "• Выручка и расходы\n"
            "• Количество клиентов\n" 
            "• Инвестиции\n"
            "• Любые другие показатели\n\n"
            "Я проведу полный финансовый анализ!",
            parse_mode='Markdown'
        )
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        
        logger.info(f"📊 Пользователь {user.first_name} запросил историю")
        
        try:
            business_data = await db.get_user_business_data(user_id)
            
            if not business_data:
                await update.message.reply_text(
                    "📝 *История анализов пуста*\n\n"
                    "Проведите первый бизнес-анализ, и здесь появится ваша история!",
                    parse_mode='Markdown'
                )
                return
            
            response = "📊 *ИСТОРИЯ ВАШИХ АНАЛИЗОВ*\n\n"
            
            for i, analysis in enumerate(business_data[:5], 1):  # Показываем последние 5 анализов
                date = analysis['created_at'].strftime("%d.%m.%Y %H:%M") if hasattr(analysis['created_at'], 'strftime') else analysis['created_at']
                
                response += (
                    f"*Анализ #{i}* ({date})\n"
                    f"💰 Выручка: {analysis['revenue']:,.0f} руб\n"
                    f"📊 Прибыль: {analysis['profit']:,.0f} руб\n"
                    f"⭐ Оценка: {analysis['rating']}/10\n"
                )
                
                if analysis['commentary']:
                    response += f"💡 {analysis['commentary'][:100]}...\n"
                
                response += "\n"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении истории. Попробуйте позже.",
                parse_mode='Markdown'
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        user = update.effective_user
        user_id = str(user.id)
        
        # Логируем входящее сообщение
        logger.info(f"💬 Сообщение от {user.first_name} (ID: {user_id}): {user_text}")
        
        # Сохраняем пользователя
        await db.save_user(user_id, user.username, user.first_name, user.last_name)
        
        # Определяем тип сообщения с помощью AI
        thinking_msg = await update.message.reply_text(
            "🤔 *Анализирую сообщение...*", 
            parse_mode='Markdown'
        )
        
        try:
            message_type = await classify_message_type(user_text)
            logger.info(f"🎯 Определен тип сообщения: {message_type}")
            
            await thinking_msg.edit_text(
                self.get_thinking_message(message_type), 
                parse_mode='Markdown'
            )
            
            # Обрабатываем в зависимости от типа
            if message_type == "business_analysis":
                response = await self.handle_business_analysis(user_text, user_id)
            elif message_type == "question":
                response = await self.handle_question(user_text, user_id)
            else:
                response = await self.handle_general_chat(user_text, user_id)
            
            # Сохраняем сообщение и ответ в базу
            await db.save_message(user_id, user_text, message_type, response)
            
            # Логируем ответ
            logger.info(f"🤖 Ответ бота ({message_type}): {response[:100]}...")
            
            await thinking_msg.edit_text(response, parse_mode='Markdown')
            
        except Exception as e:
            error_msg = f"❌ Произошла ошибка при обработке запроса. Попробуйте еще раз."
            logger.error(f"Ошибка обработки сообщения: {e}")
            
            await db.save_message(user_id, user_text, "error", error_msg)
            await thinking_msg.edit_text(error_msg, parse_mode='Markdown')
    
    def get_thinking_message(self, message_type: str) -> str:
        """Сообщение о процессе обработки"""
        messages = {
            "business_analysis": "🔍 *Провожу финансовый анализ...*\n_Рассчитываю метрики и формулы_",
            "question": "💭 *Обдумываю ответ...*\n_Ищу лучшие решения для вашего бизнеса_", 
            "general": "💬 *Общаюсь...*\n_Всегда рад поболтать_"
        }
        return messages.get(message_type, "🤔 *Думаю...*")
    
    async def handle_business_analysis(self, text: str, user_id: str) -> str:
        """Обработка бизнес-анализа с расчетом формул"""
        
        business_data = await analyze_business(text, user_id)
        print(f"📊 Данные от AI: {business_data}")  # ДЛЯ ОТЛАДКИ
        
        if "error" in business_data:
            return "❌ Ошибка анализа. Попробуйте описать бизнес более подробно."
        
        # Рассчитываем продвинутые метрики
        calculated_metrics = calculate_advanced_metrics(business_data)
        print(f"📈 Рассчитанные метрики: {calculated_metrics}")  # ДЛЯ ОТЛАДКИ
        
        # Объединяем данные
        enhanced_data = {**business_data, **calculated_metrics}
        
        return self.format_business_response(enhanced_data)
    
    async def handle_question(self, text: str, user_id: str) -> str:
        """Обработка вопросов"""
        answer = await answer_question(text, user_id)
        return self.format_question_response(answer)
    
    async def handle_general_chat(self, text: str, user_id: str) -> str:
        """Обработка общего чата"""
        response = await general_chat(text, user_id)
        return self.format_general_response(response)
    
    def format_business_response(self, data: dict) -> str:
        """Форматирование ответа с рассчитанными метриками"""
        
        def clean_text(text):
            if not text:
                return ""
            return text.replace('###', '').replace('**', '').replace('__', '')
        
        rating_emoji = "🚀" if data["ОЦЕНКА"] >= 8 else "✅" if data["ОЦЕНКА"] >= 6 else "⚠️"
        
        response = (
            f"📊 *ФИНАНСОВЫЙ АНАЛИЗ*\n\n"
            f"💰 *Основные показатели:*\n"
            f"• Выручка: {data['ВЫРУЧКА']:,.0f} руб\n"
            f"• Расходы: {data['РАСХОДЫ']:,.0f} руб\n"
            f"• Прибыль: {data['ПРИБЫЛЬ']:,.0f} руб\n"
            f"• Клиенты: {data['КЛИЕНТЫ']:,.0f} чел\n"
            f"• Средний чек: {data['СРЕДНИЙ_ЧЕК']:,.0f} руб\n"
            f"• Инвестиции: {data['ИНВЕСТИЦИИ']:,.0f} руб\n\n"
        )
        
        # Добавляем РАССЧИТАННЫЕ метрики
        response += f"📈 *Рассчитанные метрики:*\n"
        
        if data.get("РОЕНТАБЕЛЬНОСТЬ", 0) > 0:
            rent_emoji = "✅" if data["РОЕНТАБЕЛЬНОСТЬ"] > 20 else "⚠️" if data["РОЕНТАБЕЛЬНОСТЬ"] > 10 else "❌"
            response += f"• Рентабельность: {data['РОЕНТАБЕЛЬНОСТЬ']:.1f}% {rent_emoji}\n"
        
        if data.get("ТОЧКА_БЕЗУБЫТОЧНОСТИ", 0) > 0:
            response += f"• Точка безубыточности: {data['ТОЧКА_БЕЗУБЫТОЧНОСТИ']:.0f} клиентов\n"
        
        if data.get("ЗАПАС_ПРОЧНОСТИ", 0) > 0:
            safety_emoji = "🛡️" if data["ЗАПАС_ПРОЧНОСТИ"] > 30 else "⚠️"
            response += f"• Запас прочности: {data['ЗАПАС_ПРОЧНОСТИ']:.1f}% {safety_emoji}\n"
        
        if data.get("ИНДЕКС_ПРИБЫЛЬНОСТИ", 0) > 0:
            pi_emoji = "🚀" if data["ИНДЕКС_ПРИБЫЛЬНОСТИ"] > 1.5 else "✅" if data["ИНДЕКС_ПРИБЫЛЬНОСТИ"] > 1.0 else "⚠️"
            response += f"• Индекс прибыльности: {data['ИНДЕКС_ПРИБЫЛЬНОСТИ']:.2f} {pi_emoji}\n"
        
        if data.get("SGR", 0) > 0:
            response += f"• Макс. устойчивый рост: {data['SGR']:.1f}%\n"
        
        # Комментарий и советы
        if data.get("КОММЕНТАРИЙ"):
            clean_comment = clean_text(data["КОММЕНТАРИЙ"])
            response += f"\n💡 *Комментарий аналитика:*\n{clean_comment}\n\n"
        
        if data.get("СОВЕТЫ"):
            response += f"🎯 *Рекомендации:*\n"
            for i, advice in enumerate(data["СОВЕТЫ"][:3], 1):
                clean_advice = clean_text(advice)
                response += f"{i}. {clean_advice}\n"
        
        response += f"\n⭐ *Общая оценка:* {data['ОЦЕНКА']}/10 {rating_emoji}"
        
        return response
    
    def format_question_response(self, answer: str) -> str:
        """Форматирование ответа на вопрос"""
        answer = answer.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
        return f"💡 *ОТВЕТ НА ВОПРОС*\n\n{answer}"
    
    def format_general_response(self, response: str) -> str:
        """Форматирование общего ответа"""
        return f"💬 {response}"
    
    def run(self):
        """Запуск бота с инициализацией базы данных"""
        print("🤖 Умный бот запускается...")
        
        # Инициализация базы данных
        import asyncio
        asyncio.run(db.init_db())
        
        print("✅ База данных инициализирована")
        print("✅ Умное определение типов сообщений")
        print("✅ Расширенная аналитика с финансовыми формулами")
        print("✅ Логирование всех действий")
        print("✅ Контекстная память пользователей")
        
        self.app.run_polling()

if __name__ == "__main__":
    bot = BusinessBot()
    bot.run()
