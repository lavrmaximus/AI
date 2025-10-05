import asyncio
from tgbot import BusinessBot

async def main():
    bot = BusinessBot()
    await bot.run_async()  # ← оставляем await

if __name__ == "__main__":
    asyncio.run(main())