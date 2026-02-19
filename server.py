import os
import time
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")

EXPIRE_TIME = 3600  # 1 hour
CHUNK_SIZE = 1024 * 1024  # 1MB (increase speed)

# ===========================================

app = FastAPI()
bot = Client("streambot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

TEMP_FILES = {}


# ================= START BOT =================

@app.on_event("startup")
async def startup():
    await bot.start()


@app.on_event("shutdown")
async def shutdown():
    await bot.stop()


# ================= STREAM ROUTE =================

@app.get("/stream/{file_key}")
async def stream(file_key: str, request: Request):

    if file_key not in TEMP_FILES:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    file_id, created = TEMP_FILES[file_key]

    if time.time() - created > EXPIRE_TIME:
        del TEMP_FILES[file_key]
        raise HTTPException(status_code=403, detail="Link expired")

    msg = await bot.get_messages("me", file_id)
    media = msg.document or msg.video

    if not media:
        raise HTTPException(status_code=404, detail="File not found")

    file_size = media.file_size
    file_name = media.file_name or "video.mp4"

    range_header = request.headers.get("range")
    start = 0
    end = file_size - 1

    if range_header:
        range_value = range_header.replace("bytes=", "")
        start_str, end_str = range_value.split("-")

        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1

    length = end - start + 1

    async def generator():
        async for chunk in bot.stream_media(
            media.file_id,
            offset=start,
            limit=length,
            chunk_size=CHUNK_SIZE
        ):
            yield chunk

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Disposition": f'attachment; filename="{file_name}"'
    }

    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        return StreamingResponse(generator(), status_code=206, headers=headers)

    return StreamingResponse(generator(), headers=headers)


# ================= BOT HANDLER =================

@bot.on_message(filters.document | filters.video)
async def generate_link(client, message):

    key = str(uuid.uuid4())
    TEMP_FILES[key] = (message.id, time.time())

    stream_link = f"{BASE_URL}/stream/{key}"
    download_link = f"{BASE_URL}/stream/{key}"

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎬 Stream", url=stream_link)
            ],
            [
                InlineKeyboardButton("⚡ Fast Download", url=download_link)
            ]
        ]
    )

    file = message.document or message.video
    size_mb = round(file.file_size / (1024 * 1024), 2)

    await message.reply_text(
        f"🚀 File Ready!\n\n"
        f"📦 Size: {size_mb} MB\n"
        f"⏳ Expires in: 1 Hour\n\n"
        f"Choose an option below:",
        reply_markup=buttons
    )
