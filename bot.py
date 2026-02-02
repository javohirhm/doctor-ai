from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app.config import TELEGRAM_TOKEN, PROJECT_ID, LOCATION, ENDPOINT_ID, logger
from app.database import init_database
from app.handlers import (
    start, help_command, stats_command, language_command, clear_command,
    language_callback, suggestion_callback, handle_message, handle_image
)


def main():
    """Start the bot"""

    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN environment variable not set!")

    # Initialize database
    init_database()

    logger.info("=" * 60)
    logger.info("🚀 Starting MedGemma Telegram Bot for SinoAI")
    logger.info("=" * 60)
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Region: {LOCATION}")
    logger.info(f"Endpoint: {ENDPOINT_ID}")
    logger.info("=" * 60)

    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("clear", clear_command))

    # Add callback handler for language selection
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))

    # Add callback handler for suggestion buttons
    application.add_handler(CallbackQueryHandler(suggestion_callback, pattern="^suggest_"))

    # Add message handler for questions
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Add handler for images
    application.add_handler(
        MessageHandler(filters.PHOTO, handle_image)
    )

    # Start polling
    logger.info("✅ Bot is running! Doctors can now ask questions.")
    logger.info("Press Ctrl+C to stop the bot")
    logger.info("=" * 60)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
