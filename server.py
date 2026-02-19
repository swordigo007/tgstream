import os
import time
import secrets
import sqlite3
from flask import Flask, redirect, abort
from pyrogram import Client, filters

# ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BASE_URL = os.getenv("BASE_URL")

# DATABASE (SQLITE)
conn = sqlite3.connect("links.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS links (
    token TEXT,
    file_id TEXT,
    expiry INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    expiry INTEGER
)
""")

conn.commit()

# TELEGRAM CLIENT
bot = Client("streambot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# FLASK APP
app = Flask(__name__)

# ---------------- SETTINGS ----------------

def get_default_expiry():
    cursor.execute("SELECT expiry FROM settings WHERE id=1")
    row = cursor.fetchone()
    return row[0] if row else 3600


def set_default_expiry(sec):
    cursor.execute("INSERT OR REPLACE INTO settings (id, expiry) VALUES (1, ?)", (sec,))
    conn.commit()


def save_link(token, file_id, expiry):
    cursor.execute("INSERT INTO links VALUES (?, ?, ?)", (token, file_id, expiry))
    conn.commit()


def get_link(token):
    cursor.execute("SELECT file_id, expiry FROM links WHERE token=?", (token,))
    return cursor.fetchone()

# ---------------- TELEGRAM BOT ----------------

@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply(
        "Send video/document.\n\n"
        "You'll get:\n"
        "• Stream link (MX Player/browser)\n"
        "• Fast direct download"
    )

# FILE HANDLER
@bot.on_message(filters.video | filters.document | filters.audio)
async def generate_link(_, msg):

    media = msg.video or msg.document or msg.audio
    file_id = media.file_id

    token = secrets.token_urlsafe(16)
    expiry = time.time() + get_default_expiry()

    save_link(token, file_id, expiry)

    stream_link = f"{BASE_URL}/stream/{token}"
    download_link = f"{BASE_URL}/download/{token}"

    await msg.reply(
        f"🎬 STREAM:\n{stream_link}\n\n⚡ DOWNLOAD:\n{download_link}"
    )

# ADMIN EXPIRY CONTROL
@bot.on_message(filters.command("setexpiry") & filters.user(ADMIN_ID))
async def set_expiry(_, msg):
    try:
        sec = int(msg.command[1])
        set_default_expiry(sec)
        await msg.reply(f"Default expiry set to {sec} seconds")
    except:
        await msg.reply("Usage:\n/setexpiry 3600")

# ---------------- STREAM SERVER ----------------

@app.route("/")
def home():
    return "Telegram Stream Bot Running"

@app.route("/stream/<token>")
def stream(token):

    data = get_link(token)
    if not data:
        return abort(404)

    file_id, expiry = data

    if time.time() > expiry:
        return "Link expired"

    # STREAM WITHOUT DOWNLOAD
    return redirect(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_id}")

@app.route("/download/<token>")
def download(token):

    data = get_link(token)
    if not data:
        return abort(404)

    file_id, expiry = data

    if time.time() > expiry:
        return "Link expired"

    return redirect(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_id}")

# ---------------- START BOT + SERVER ----------------

if __name__ == "__main__":
    bot.start()
    app.run(host="0.0.0.0", port=8080)
