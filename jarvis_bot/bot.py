from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from ai import generate_reply
from memory import forget
import config
import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))

    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, format, *args):
            pass  # suppress default logging

    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[Server] Health check server running on port {port}", flush=True)
    server.serve_forever()


# Start health check server immediately so Render can detect the open port
t = threading.Thread(target=run_dummy_server, daemon=True)
t.start()
t.join(timeout=1)  # Give the server 1 second to bind before bot starts


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    # Run blocking AI call in a thread so it doesn't freeze the event loop
    reply = await asyncio.to_thread(generate_reply, user_id, update.message.text)
    await update.message.reply_text(reply)


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /forget <keyword>")
        return
    keyword = " ".join(context.args)
    removed = await asyncio.to_thread(forget, user_id, keyword)
    msg = f"Removed memory matching: {keyword}" if removed else f"No memory found matching: {keyword}"
    await update.message.reply_text(msg)


if __name__ == "__main__":
    # Explicitly create and set event loop — required for Python 3.14+
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("forget", forget_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("[Bot] Starting Telegram polling...", flush=True)
    # run_polling() is synchronous — do NOT await it
    app.run_polling()
