from pymongo import MongoClient
from config import MONGO_URI
import time

client = MongoClient(MONGO_URI)
db = client["StreamBot"]

links = db.links
settings = db.settings


def save_link(token, file_id, expiry):
    links.insert_one({
        "token": token,
        "file_id": file_id,
        "expiry": expiry
    })


def get_link(token):
    return links.find_one({"token": token})


def set_default_expiry(seconds):
    settings.update_one({}, {"$set": {"expiry": seconds}}, upsert=True)


def get_default_expiry():
    s = settings.find_one({})
    return s["expiry"] if s else 3600
