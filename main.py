"""
Entry point — works with python-telegram-bot v21/v22 (latest)
"""
from __future__ import annotations
import logging
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
import config
import database as db
import handlers as h

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

def main() -> None:
    db.init_db()
    logger.info("Database ready at %s", config.DATABASE_PATH)
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", h.cmd_start))
    app.add_handler(CommandHandler("help",  h.cmd_help))

    app.add_handler(CallbackQueryHandler(h.cb_shop,              pattern=r"^shop$"))
    app.add_handler(CallbackQueryHandler(h.cb_rank_selected,     pattern=r"^rank:"))
    app.add_handler(CallbackQueryHandler(h.cb_duration_selected, pattern=r"^dur:"))
    app.add_handler(CallbackQueryHandler(h.cb_toggle_extra,      pattern=r"^toggle:"))
    app.add_handler(CallbackQueryHandler(h.cb_confirm,           pattern=r"^confirm:"))
    app.add_handler(CallbackQueryHandler(h.cb_cancel_order,      pattern=r"^cancel_order$"))
    app.add_handler(CallbackQueryHandler(h.cb_cancel_pending,    pattern=r"^cancel_pending:"))
    app.add_handler(CallbackQueryHandler(h.cb_back_main,         pattern=r"^back_main$"))
    app.add_handler(CallbackQueryHandler(h.cb_my_orders,         pattern=r"^my_orders$"))
    app.add_handler(CallbackQueryHandler(h.cb_help,              pattern=r"^help$"))
    app.add_handler(CallbackQueryHandler(h.cb_admin_action,      pattern=r"^admin:"))

    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
            h.handle_message,
        )
    )
    app.add_error_handler(h.error_handler)
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
