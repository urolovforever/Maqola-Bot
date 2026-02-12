import os
import logging
from datetime import datetime, timezone, timedelta

# Toshkent vaqt zonasi (UTC+5)
TASHKENT_TZ = timezone(timedelta(hours=5))
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Define conversation states
NAME, PHONE, FILE = range(3)

# Max file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Uploads directory (absolute path based on script location)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
logger.info("Uploads papka: %s", UPLOADS_DIR)

# Function to reset the conversation
async def reset_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Helper function to reset the conversation and start fresh."""
    user_first_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Assalomu alaykum, {user_first_name}!\n\n"
        "Ilmiy ishlar departamentiga maqola yuborish botiga xush kelibsiz!\n\n"
        "Iltimos, maqolangizni .doc, .docx yoki .pdf formatida yuboring.\n"
        "Fayl nomida muallif familyasini ko'rsating (masalan: Abdullayev_maqola.docx).\n\n"
        "Rahmat!"
    )
    await update.message.reply_text("Iltimos, ismingizni yuboring:")
    return NAME

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clear user data and cancel any ongoing conversation
    context.user_data.clear()
    return await reset_conversation(update, context)

# Handle name input
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.text
    context.user_data["name"] = user_name  # Store the name in user_data
    await update.message.reply_text(
        f"Rahmat, {user_name}! Iltimos, telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[{"text": "Raqamni yuborish", "request_contact": True}]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return PHONE

# Handle phone number input
async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_number = update.message.contact.phone_number
    context.user_data["phone"] = phone_number  # Store the phone number in user_data

    # Remove the custom keyboard
    await update.message.reply_text(
        f"Raqamingiz qabul qilindi: {phone_number}. Endi iltimos, maqola faylini yuboring.",
        reply_markup=ReplyKeyboardRemove()  # Remove the keyboard
    )
    return FILE

# Handle file upload
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    file_name = document.file_name

    # Validate file type
    if not file_name.lower().endswith((".doc", ".docx", ".pdf")):
        await update.message.reply_text("Iltimos, faqat .doc, .docx yoki .pdf formatidagi fayllarni yuboring.")
        return FILE

    # Validate file size
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("Fayl hajmi 10 MB dan oshmasligi kerak. Iltimos, kichikroq fayl yuboring.")
        return FILE

    # Generate unique file name
    timestamp = datetime.now(TASHKENT_TZ).strftime("%Y%m%d_%H%M%S")
    user_name = context.user_data.get("name", "nomalum")
    safe_name = user_name.replace(" ", "_")
    _, ext = os.path.splitext(file_name)
    unique_name = f"{timestamp}_{safe_name}{ext}"

    file_path = os.path.join(UPLOADS_DIR, unique_name)
    logger.info("Fayl saqlanmoqda: %s", file_path)

    try:
        tg_file = await document.get_file()
        await tg_file.download_to_drive(file_path)
        logger.info("Fayl muvaffaqiyatli saqlandi: %s", file_path)
    except Exception as e:
        logger.error("Faylni saqlashda xatolik: %s", e)
        await update.message.reply_text("Faylni saqlashda xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return FILE

    user_phone = context.user_data.get("phone", "Noma'lum")

    logger.info("Yangi maqola qabul qilindi: %s -> %s", file_name, unique_name)

    # Notify the user
    await update.message.reply_text(f"Fayl qabul qilindi: {file_name}. Rahmat!")

    # Send to admin
    await context.bot.send_document(
        chat_id=ADMIN_CHAT_ID,
        document=document.file_id,
        caption=f"Yangi maqola:\n"
               f"Fayl nomi: {file_name}\n"
               f"Foydalanuvchi: {user_name}\n"
               f"Telefon: {user_phone}",
    )

    # Clear user data
    context.user_data.clear()
    await update.message.reply_text("Yangi maqola yuborish uchun /start ni bosing.")
    return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Jarayon bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Update %s caused error %s", update, context.error)

# Main function to run the bot
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],  # Always resets
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            PHONE: [MessageHandler(filters.CONTACT, handle_phone)],
            FILE: [MessageHandler(filters.Document.ALL, handle_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],  # Ensure reset on /start
    )

    # Add handlers
    app.add_handler(conv_handler)
    app.add_error_handler(error)

    # Start the bot
    logger.info("Bot ishga tushdi...")
    app.run_polling()
