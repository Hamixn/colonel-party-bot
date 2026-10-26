import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo, MenuButtonDefault

import config
from database import init_db
from handlers import user_router, admin_router, game_router
from server import start_webapp_server

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

    webapp_runner = None
    try:
        # Start aiohttp WebApp server concurrently
        if config.WEBAPP_PORT:
            try:
                webapp_runner = await start_webapp_server(bot, port=config.WEBAPP_PORT)
                logger.info(f"🌐 [Three.js WebApp Server] Live on http://0.0.0.0:{config.WEBAPP_PORT}")
            except Exception as e:
                logger.error(f"Failed to start WebApp server: {e}")

        # Configure Telegram Menu Button for Mini App
        if config.WEBAPP_URL:
            try:
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="🏰 عمارت ۳ بعدی",
                        web_app=WebAppInfo(url=config.WEBAPP_URL)
                    )
                )
                logger.info(f"🏰 Telegram Chat Menu Button set to: {config.WEBAPP_URL}")
            except Exception as e:
                logger.warning(f"Could not set WebApp chat menu button: {e}")
        else:
            try:
                await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
            except Exception:
                pass

        logger.info("Deleting pending updates and launching polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("💀 [Project Blackout: The Colonel's Garden] Bot & Mini App are LIVE!")
        await dp.start_polling(bot)
    finally:
        if webapp_runner:
            logger.info("Shutting down WebApp server...")
            await webapp_runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped by organizer.")
