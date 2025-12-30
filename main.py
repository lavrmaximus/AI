import asyncio
import os
import threading
from dotenv import load_dotenv
from tgbot import BusinessBot
from WEBSite import app
from env_utils import setup_environment, is_production

# Загружаем переменные окружения только локально
if not is_production():
    load_dotenv()

async def run_bot():
    # Настраиваем окружение
    setup_environment()
    
    # В продакшене бот инициализируется внутри Flask (WEBSite.py)
    # Локально мы запускаем его отдельно для polling
    if not is_production():
        bot = BusinessBot()
        await bot.run_async()
    else:
        # В продакшене просто ждем, так как бот работает через вебхуки в Flask
        print("🚀 Запуск в продакшене: Бот работает через Webhook внутри Flask")
        await asyncio.Event().wait()

def run_web():
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Переменная PORT: {os.environ.get('PORT', 'НЕ УСТАНОВЛЕНА')}")
    print(f"🌐 Запускаю веб-сайт на порту {port}")
    print(f"🌐 URL: http://0.0.0.0:{port}")
    
    # В продакшене Flask запускает бота через вебхуки
    if is_production():
        # Устанавливаем вебхук при старте
        webhook_url = f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}/webhook"
        print(f"🔗 Настройка вебхука на: {webhook_url}")
        
        # Инициализируем бота для установки вебхука
        async def init_webhook():
            bot = BusinessBot()
            await bot.set_webhook(webhook_url)
            
        try:
            asyncio.run(init_webhook())
        except Exception as e:
            print(f"❌ Ошибка установки вебхука: {e}")

    app.run(debug=False, host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("🚀 Запускаю приложение...")
    
    if is_production():
        # В продакшене запускаем только веб-сервер (он обрабатывает и вебхуки)
        run_web()
    else:
        # Локально запускаем веб-сайт в фоне и бота в polling режиме
        web_thread = threading.Thread(target=run_web)
        web_thread.daemon = True
        web_thread.start()
        print("🌐 Веб-сайт запущен в фоне")
        
        # Запускаем бота в основном потоке
        print("🤖 Запускаю бота (Polling)...")
        asyncio.run(run_bot())