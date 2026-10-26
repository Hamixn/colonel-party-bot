import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, MenuButtonDefault

import config
from database import init_db
from handlers import user_router, admin_router, game_router

async def set_bot_commands(bot: Bot):
    """Configures the official Telegram command menu with Persian descriptions."""
    commands = [
        BotCommand(command="start", description="🚪 ورود به عمارت و دریافت کارت دعوت"),
        BotCommand(command="card", description="🎴 مشاهده کارت دعوت و کد روح من"),
        BotCommand(command="carpool", description="🚗 مشخصات خودرو و راننده در کاروان صدرا"),
        BotCommand(command="tape", description="🎙 نوار کاست صوتی شماره ۷ سرهنگ (۱۳۵۶)"),
        BotCommand(command="mission", description="📜 طومار و ماموریت مخفی نفوذ (مصونیت)"),
        BotCommand(command="lantern", description="🔴 فانوس سرخ دیجیتال (تنها نور مجاز)"),
        BotCommand(command="team", description="🔦 وضعیت تیم و معماهای حیاط"),
        BotCommand(command="solve", description="🧩 ثبت پاسخ معمای پاکت‌های حیاط"),
        BotCommand(command="rescue", description="💡 روشن کردن نور حیات باغ (مخصوص سالن)"),
        BotCommand(command="graveyard", description="⚰️ جدول زنده بازماندگان عمارت"),
        BotCommand(command="rules", description="📜 قوانین و سناریوی ۴ پرده‌ای مهمانی"),
        BotCommand(command="help", description="❓ راهنمای کامل امکانات و پشتیبانی")
    ]
    try:
        await bot.set_my_commands(commands)
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        logging.getLogger("ColonelPartyBot").info("✅ Telegram Bot Commands & Menu Button configured.")
    except Exception as e:
        logging.getLogger("ColonelPartyBot").warning(f"Could not configure bot commands: {e}")

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

    # Register Routers (Admin, Game Engine, User Onboarding)
    dp.include_router(admin_router)
    dp.include_router(game_router)
    dp.include_router(user_router)

    try:
        await set_bot_commands(bot)
        logger.info("Deleting pending updates and launching polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("💀 [Project Blackout: The Colonel's Garden] Bot is 100% LIVE and ready!")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped by organizer.")
