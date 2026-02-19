import os
import time
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pyrogram import Client, filters

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")

app = FastAPI()
bot = Client("streambot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

TEMP_FILES = {}
EXPIRE_TIME = 86400


@app.on_event("startup")
async def startup():
    await bot.start()


@app.get("/stream/{file_key}")
async def stream(file_key: str, request: Request):
    if file_key not in TEMP_FILES:
        raise HTTPException(status_code=404)

    file_id, created = TEMP_FILES[file_key]

    if time.time() - created > EXPIRE_TIME:
        del TEMP_FILES[file_key]
        raise HTTPException(status_code=403)

    msg = await bot.get_messages("me", file_id)
    media = msg.document or msg.video
    file_size = media.file_size
    file_name = media.file_name or "video.mp4"

    range_header = request.headers.get("range")
    start = 0
    end = file_size - 1

    if range_header:
        bytes_range = range_header.replace("bytes=", "").split("-")
        start = int(bytes_range[0])
        if bytes_range[1]:
            end = int(bytes_range[1])

    async def generator():
        async for chunk in bot.stream_media(media.file_id, offset=start):
            yield chunk

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }

    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        return StreamingResponse(generator(), status_code=206, headers=headers)

    return StreamingResponse(generator(), headers=headers)


@bot.on_message(filters.document | filters.video)
async def link_generator(client, message):
    key = str(uuid.uuid4())
    TEMP_FILES[key] = (message.id, time.time())

    link = f"{BASE_URL}/stream/{key}"
    await message.reply(f"🚀 Fast Download & Stream Link:\n\n{link}")
