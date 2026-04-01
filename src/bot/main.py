import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Додаємо voice у імпорти з пакету handlers
from src.bot.handlers import commands, voice
from src.core.config import settings


async def main() -> None:
    """Головна точка входу для запуску бота."""
    logging.basicConfig(level=logging.INFO)

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Реєстрація роутерів
    dp.include_router(commands.router)
    dp.include_router(voice.router)

    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
