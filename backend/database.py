from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = None
db = None

def init_db(app):
    global client, db
    # use local mongodb by default if string isn't provided
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["Satya"]
    print("MongoDB initialized.")
    print("MongoDB Connected Successfully")

def get_db():
    return db
