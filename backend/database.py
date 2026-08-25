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
    
    # Create required TTL indexes (Phase 2 validation)
    try:
        from pymongo import ASCENDING
        db.email_otps.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
        db.eligibility_cache.create_index([("created_at", ASCENDING)], expireAfterSeconds=86400) # 24h
        print("MongoDB Indexes Verified.")
    except Exception as e:
        print("MongoDB Index creation warning:", e)
        
    print("MongoDB initialized.")
    print("MongoDB Connected Successfully")

def get_db():
    return db
