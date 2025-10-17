import asyncio
import os
from dotenv import load_dotenv
from tgbot import BusinessBot

# Загружаем переменные окружения
load_dotenv()

async def main():
    bot = BusinessBot()
    await bot.run_async()  # ← оставляем await

if __name__ == "__main__":
    asyncio.run(main())