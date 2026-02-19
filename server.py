from flask import Flask, redirect, abort
from pyrogram import Client, filters
import secrets, time
from pymongo import MongoClient
import os

# CONFIG
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BASE_URL = os.getenv("BASE_URL")

# DB
client = MongoClient(MONGO_URI)
db = client["StreamBot"]
links = db.links
settings = db.settings

# TELEGRAM BOT
bot = Client("streambot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# FLASK APP
app = Flask(__name__)


def get_default_expiry():
    s = settings.find_one({})
    return s["expiry"] if s else 3600


def save_link(token, file_id, expiry):
    links.insert_one({
        "token": token,
        "file_id": file_id,
        "expiry": expiry
    })


def get_link(token):
    return links.find_one({"token": token})


# TELEGRAM EVENTS
@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply("Send file/video → get streaming + fast link")


@bot.on_message(filters.document | filters.video | filters.audio)
async def generate_link(_, msg):
    file_id = msg.document.file_id if msg.document else msg.video.file_id

    token = secrets.token_urlsafe(16)
    expiry = time.time() + get_default_expiry()

    save_link(token, file_id, expiry)

    stream_link = f"{BASE_URL}/stream/{token}"
    download_link = f"{BASE_URL}/download/{token}"

    await msg.reply(
        f"🎬 Stream:\n{stream_link}\n\n⚡ Download:\n{download_link}"
    )


@bot.on_message(filters.command("setexpiry") & filters.user(ADMIN_ID))
async def set_expiry(_, msg):
    sec = int(msg.command[1])
    settings.update_one({}, {"$set": {"expiry": sec}}, upsert=True)
    await msg.reply(f"Expiry set to {sec} sec")


# STREAM ROUTES
@app.route("/stream/<token>")
def stream(token):
    data = get_link(token)

    if not data:
        return abort(404)

    if time.time() > data["expiry"]:
        return "Link expired"

    file_id = data["file_id"]
    return redirect(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_id}")


@app.route("/download/<token>")
def download(token):
    data = get_link(token)

    if not data:
        return abort(404)

    if time.time() > data["expiry"]:
        return "Link expired"

    file_id = data["file_id"]
    return redirect(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_id}")


# START BOTH
if __name__ == "__main__":
    bot.start()
    app.run(host="0.0.0.0", port=8080)
