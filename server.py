from flask import Flask, redirect, abort
from pyrogram import Client
from config import *
from database import get_link
import time

app = Flask(__name__)

bot = Client("streambot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
bot.start()


@app.route("/stream/<token>")
def stream(token):
    data = get_link(token)

    if not data:
        return abort(404)

    if time.time() > data["expiry"]:
        return "Link expired"

    file = bot.get_messages(chat_id="me", message_ids=data["file_id"])
    return redirect(file.document.file_id)


@app.route("/download/<token>")
def download(token):
    data = get_link(token)

    if not data:
        return abort(404)

    if time.time() > data["expiry"]:
        return "Link expired"

    file = bot.get_messages(chat_id="me", message_ids=data["file_id"])
    return redirect(file.document.file_id)


app.run(host="0.0.0.0", port=8080)
