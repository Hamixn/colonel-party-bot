import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from database import init_db
from handlers import user_router, admin_router, game_router

async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger("ColonelPartyBot")

    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "❌ BOT_TOKEN is missing or not configured!\n"
            "Please create a .env file and set your BOT_TOKEN.\n"
            "Example: BOT_TOKEN=123456789:ABCDefGhIjKlMnOpQrStUvWxYz"
        )
        return

    logger.info("Initializing SQLite database...")
    await init_db()

    logger.info("Initializing Telegram Bot instance...")
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Register Routers (User, Admin & Game Engine)
    dp.include_router(admin_router)
    dp.include_router(game_router)
    dp.include_router(user_router)

    logger.info("Deleting pending updates and launching polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("💀 [Project Blackout: The Colonel's Garden] Bot is LIVE!")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped by organizer.")
