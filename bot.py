from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import logging
import sys

# تنظیم لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8815432500:AAEcNCYABbXgz6ntBwndERExzawFh1tyqag"

def start(update: Update, context):
    try:
        user = update.effective_user
        logger.info(f"✅ کاربر {user.first_name} استارت زد!")
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار", callback_data="stats")],
            [InlineKeyboardButton("📢 کانال", url="https://t.me/ReaperMusicTM")]
        ]
        
        update.message.reply_text(
            f"🌟 سلام {user.first_name} عزیز!\nبه ربات ZX خوش اومدی!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info("✅ پیام استارت ارسال شد!")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")

def button(update: Update, context):
    try:
        query = update.callback_query
        query.answer()
        query.edit_message_text("✅ در حال پردازش...")
        logger.info(f"👆 دکمه {query.data} کلیک شد!")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")

def main():
    logger.info("🚀 ربات در حال راه‌اندازی...")
    
    try:
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CallbackQueryHandler(button))
        
        logger.info("✅ ربات شروع به کار کرد...")
        updater.start_polling(clean=True, drop_pending_updates=True)
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ خطای راه‌اندازی: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()