import asyncio
import os
from dotenv import load_dotenv
from tgbot import BusinessBot
from env_utils import setup_environment, is_production

# Загружаем переменные окружения только локально
if not is_production():
    load_dotenv()

async def main():
    # Настраиваем окружение
    setup_environment()
    
    bot = BusinessBot()
    await bot.run_async()

if __name__ == "__main__":
    asyncio.run(main())