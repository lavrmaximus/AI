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
    
    bot = BusinessBot()
    await bot.run_async()

def run_web():
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Переменная PORT: {os.environ.get('PORT', 'НЕ УСТАНОВЛЕНА')}")
    print(f"🌐 Запускаю веб-сайт на порту {port}")
    print(f"🌐 URL: http://0.0.0.0:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("🚀 Запускаю приложение...")
    # Запускаем веб-сайт в отдельном потоке
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    print("🌐 Веб-сайт запущен в фоне")
    
    # Запускаем бота в основном потоке
    print("🤖 Запускаю бота...")
    asyncio.run(run_bot())