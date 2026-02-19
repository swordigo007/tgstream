import os
import logging
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")  # https://yourapp.up.railway.app
UPLOAD_DIR = "uploads"

DEFAULT_ADMIN = 5694344682  # 👈 PUT YOUR TELEGRAM ID HERE
admins = {DEFAULT_ADMIN}

expiry_minutes = 60
active_tasks = {}

PORT = int(os.environ.get("PORT", 8080))

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= LOGGING =================

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

# ================= WEB SERVER =================

async def handle_download(request):
    filename = request.match_info['filename']
    filepath = os.path.join(UPLOAD_DIR, filename)

    if os.path.exists(filepath):
        return web.FileResponse(filepath)

    return web.Response(text="File expired or not found", status=404)


async def start_web():
    app = web.Application()
    app.router.add_get('/file/{filename}', handle_download)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()


# ================= BOT COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a file to generate:\n\n"
        "🎬 Stream Link\n"
        "⚡ Fast Download Link"
    )


async def set_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global expiry_minutes

    if update.effective_user.id not in admins:
        return

    if not context.args:
        await update.message.reply_text("Usage: /setexpiry 30")
        return

    expiry_minutes = int(context.args[0])
    await update.message.reply_text(f"Expiry set to {expiry_minutes} minutes.")


async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admins:
        return

    if not context.args:
        await update.message.reply_text("Usage: /addadmin user_id")
        return

    new_admin = int(context.args[0])
    admins.add(new_admin)
    await update.message.reply_text(f"Admin added: {new_admin}")


async def cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admins:
        return

    if not context.args:
        await update.message.reply_text("Usage: /cancel user_id")
        return

    user_id = int(context.args[0])

    if user_id in active_tasks:
        filename = active_tasks[user_id]
        filepath = os.path.join(UPLOAD_DIR, filename)

        if os.path.exists(filepath):
            os.remove(filepath)

        del active_tasks[user_id]
        await update.message.reply_text(f"Cancelled task of {user_id}")
    else:
        await update.message.reply_text("No active task found.")


# ================= FILE HANDLER =================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    document = update.message.document

    logging.info(f"{user.id} sent file {document.file_name}")

    file = await document.get_file()

    filename = f"{user.id}_{int(datetime.now().timestamp())}_{document.file_name}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    active_tasks[user.id] = filename

    await file.download_to_drive(filepath)

    asyncio.create_task(auto_delete(filepath, user.id))

    stream_link = f"{BASE_URL}/file/{filename}"
    download_link = stream_link

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Stream", url=stream_link),
            InlineKeyboardButton("⚡ Fast Download", url=download_link)
        ]
    ])

    await update.message.reply_text(
        f"✅ Links Generated\n\n"
        f"⏳ Expires in {expiry_minutes} minutes",
        reply_markup=keyboard
    )


async def auto_delete(filepath, user_id):
    await asyncio.sleep(expiry_minutes * 60)

    if os.path.exists(filepath):
        os.remove(filepath)

    if user_id in active_tasks:
        del active_tasks[user_id]


# ================= MAIN =================

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setexpiry", set_expiry))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("cancel", cancel_task))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    await start_web()
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
