import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Define conversation states
NAME, PHONE, FILE = range(3)

# Ensure the uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Function to reset the conversation
async def reset_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Helper function to reset the conversation and start fresh."""
    user_first_name = update.message.from_user.first_name  # Get the user's first name
    await update.message.reply_text(
        f"👋 Assalomu alaykum, {user_first_name}!\n\n"
        "🎓 O'zbekiston Respublikasi Bank-moliya akademiyasining konferensiyasiga xush kelibsiz!\n\n"
        "📄 Iltimos, axborot xatida belgilangan talablarga javob beruvchi tezis faylini mos bo'lgan "
        "seksiya (ilmiy yo'nalish) raqam va muallif familyasini ko'rsatgan holda nomlab jo'natishingizni so'raymiz.\n"
        "(masalan: 2.Abdullayev.doc).\n\n"
        "🙏 Rahmat!"
    )
    await update.message.reply_text("📝 Iltimos, ismingizni yuboring:")
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
        f"🙏 Rahmat, {user_name}! Iltimos, telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[{"text": "📱 Raqamni yuborish", "request_contact": True}]],
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
        f"✅ Raqamingiz qabul qilindi: {phone_number}. Endi iltimos, tezis faylini yuboring.",
        reply_markup=ReplyKeyboardRemove()  # Remove the keyboard
    )
    return FILE

# Handle file upload
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    file_name = document.file_name

    # Validate file type (only .doc, .docx, or .pdf allowed)
    if not file_name.lower().endswith((".doc", ".docx", ".pdf")):
        await update.message.reply_text("❌ Iltimos, faqat .doc, .docx yoki .pdf formatidagi fayllarni yuboring.")
        return FILE

    # Save the file with a proper path
    file_path = os.path.join("uploads", file_name)
    file = await document.get_file()
    await file.download_to_drive(file_path)

    # Notify the user
    await update.message.reply_text(f"✅ Fayl qabul qilindi: {file_name}. Rahmat! 🙏")

    # Send user details and file to admin
    admin_chat_id = "5407162492"  # Replace with your admin's chat ID
    user_name = context.user_data.get("name", "Noma'lum")
    user_phone = context.user_data.get("phone", "Noma'lum")

    await context.bot.send_document(
        chat_id=admin_chat_id,
        document=document.file_id,
        caption=f"📤 Yangi fayl:\n"
               f"📄 Fayl nomi: {file_name}\n"
               f"👤 Foydalanuvchi ismi: {user_name}\n"
               f"📞 Telefon raqami: {user_phone}"
    )

    # Clear user data
    context.user_data.clear()
    await update.message.reply_text("🔄 Yangi fayl yuborish uchun /start ni bosing.")
    return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Jarayon bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

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
    print("Bot is running...")
    app.run_polling()
