from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from ai import generate_reply
from memory import forget
import config
import os
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, format, *args):
            pass # Suppress logging to keep console clean

    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[Server] Starting dummy server on port {port} for Render health checks...", flush=True)
    server.serve_forever()

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

# Start dummy web server for Render health checks
threading.Thread(target=run_dummy_server, daemon=True).start()

app.run_polling()
