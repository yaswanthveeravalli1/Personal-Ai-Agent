from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from ai import generate_reply
from memory import forget
import config

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    reply = generate_reply(user_id, update.message.text)
    await update.message.reply_text(reply)

async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /forget <keyword>")
        return
    keyword = " ".join(context.args)
    removed = forget(user_id, keyword)
    msg = f"Removed memory matching: {keyword}" if removed else f"No memory found matching: {keyword}"
    await update.message.reply_text(msg)

app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("forget", forget_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
