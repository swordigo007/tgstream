from pyrogram import Client, filters
import secrets, time
from config import *
from database import save_link, get_default_expiry, set_default_expiry

app = Client("streambot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)


@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply("Send me any file/video.\nI will generate streaming + fast download link.")


@app.on_message(filters.document | filters.video | filters.audio)
async def generate_link(_, msg):
    file_id = msg.document.file_id if msg.document else msg.video.file_id

    token = secrets.token_urlsafe(16)
    expiry = time.time() + get_default_expiry()

    save_link(token, file_id, expiry)

    stream_link = f"{BASE_URL}/stream/{token}"
    download_link = f"{BASE_URL}/download/{token}"

    await msg.reply(
        f"🎬 Stream Link:\n{stream_link}\n\n"
        f"⚡ Fast Download:\n{download_link}"
    )


# Admin expiry control
@app.on_message(filters.command("setexpiry") & filters.user(ADMIN_ID))
async def set_expiry(_, msg):
    sec = int(msg.command[1])
    set_default_expiry(sec)
    await msg.reply(f"Default expiry set to {sec} seconds.")


app.run()
