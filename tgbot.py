from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ai import *

BOT_TOKEN = "8350333926:AAEkf4If4LXh657SOTuGsAhEJx6EFSPKHbU"

class BusinessBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("about", self.about_command))
        self.app.add_handler(CommandHandler("analysis", self.analysis_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Я - твой продвинутый AI-аналитик! 🚀\n\n"
            "📊 *Что я умею:*\n"
            "• Анализировать бизнес с финансовыми формулами\n"
            "• Отвечать на вопросы о бизнесе\n"
            "• Общаться на общие темы\n"
            "• Запоминать контекст разговора\n\n"
            "💡 *Просто напиши:*\n"
            "• О своем бизнесе с цифрами\n"
            "• Вопрос о бизнесе\n"
            "• Или просто поздоровайся!",
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📋 *Доступные команды:*\n\n"
            "/start - начать работу\n"
            "/help - помощь\n"  
            "/about - о проекте\n"
            "/analysis - запустить анализ\n\n"
            "💬 *Просто напиши:*\n"
            "• *Бизнес-анализ:* 'Выручка 500к, расходы 200к, 100 клиентов'\n"
            "• *Вопрос:* 'Как увеличить прибыль?'\n"
            "• *Общение:* 'Привет! Как дела?'\n\n"
            "🎯 Я сам определю тип сообщения и отвечу соответственно!"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        about_text = (
            "🤖 *Business Intelligence AI Assistant*\n\n"
            "📈 *Расширенная аналитика:*\n"
            "• Финансовые формулы и метрики\n"
            "• Оценка по Альтману\n"  
            "• Анализ рентабельности\n"
            "• Расчет точки безубыточности\n\n"
            "🧠 *Умные ответы:*\n"
            "• Автоматическое определение типа сообщения\n"
            "• Контекстная память\n"
            "• Персонализированные рекомендации\n\n"
            "🚀 *Постоянное развитие!*"
        )
        await update.message.reply_text(about_text, parse_mode='Markdown')
    
    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        user_id = str(update.effective_user.id)
        
        # Определяем тип сообщения
        # message_type = detect_message_type(user_text)
        message_type = "business_analysis"
        
        thinking_msg = await update.message.reply_text(
            self.get_thinking_message(message_type), 
            parse_mode='Markdown'
        )
        
        try:
            if message_type == "business_analysis":
                response = await self.handle_business_analysis(user_text, user_id)
            elif message_type == "question":
                response = await self.handle_question(user_text, user_id)
            else:
                response = await self.handle_general_chat(user_text, user_id)
            
            await thinking_msg.edit_text(response, parse_mode='Markdown')
            
        except Exception as e:
            await thinking_msg.edit_text(
                "❌ Произошла ошибка при обработке запроса. Попробуйте еще раз.",
                parse_mode='Markdown'
            )
            print(f"Ошибка: {e}")
    
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
        business_data = analyze_business(text, user_id)
        
        if "error" in business_data:
            return "❌ Ошибка анализа. Попробуйте описать бизнес более подробно."
        
        # Рассчитываем продвинутые метрики
        calculated_metrics = calculate_advanced_metrics(business_data)
        
        # Объединяем данные
        enhanced_data = {**business_data, **calculated_metrics}
        
        return self.format_business_response(enhanced_data)
    
    async def handle_question(self, text: str, user_id: str) -> str:
        """Обработка вопросов"""
        answer = answer_question(text, user_id)
        return self.format_question_response(answer)
    
    async def handle_general_chat(self, text: str, user_id: str) -> str:
        """Обработка общего чата"""
        response = general_chat(text, user_id)
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
            f"• Средний чек: {data['СРЕДНИЙ_ЧЕК']:,.0f} руб\n\n"
        )
        
        # Добавляем РАССЧИТАННЫЕ метрики
        response += f"📈 *Рассчитанные метрики:*\n"
        
        if data.get("РОЕНТАБЕЛЬНОСТЬ", 0) > 0:
            rent_emoji = "✅" if data["РОЕНТАБЕЛЬНОСТЬ"] > 20 else "⚠️" if data["РОЕНТАБЕЛЬНОСТЬ"] > 10 else "❌"
            response += f"• Рентабельность: {data['РОЕНТАБЕЛЬНОСТИ']:.1f}% {rent_emoji}\n"
        
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
        return f"💡 *ОТВЕТ НА ВОПРОС*\n\n{answer}"
    
    def format_general_response(self, response: str) -> str:
        """Форматирование общего ответа"""
        return f"💬 {response}"
    
    def run(self):
        print("🤖 Умный бот запускается...")
        print("✅ Определение типов сообщений: бизнес-анализ, вопросы, общение")
        print("✅ Расширенная аналитика с финансовыми формулами")
        print("✅ Контекстная память пользователей")
        self.app.run_polling()

if __name__ == "__main__":
    bot = BusinessBot()
    bot.run()