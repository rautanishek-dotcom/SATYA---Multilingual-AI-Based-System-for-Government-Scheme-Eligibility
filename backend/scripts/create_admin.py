import sys
import os
import bcrypt
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Add parent directory to path so we can import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "Satya"

def create_admin(email, password, name="Admin User"):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    users = db.users
    
    # Check if admin already exists
    if users.find_one({"email": email}):
        print(f"User with email {email} already exists.")
        return
        
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    admin_user = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": "admin",
        "created_at": datetime.datetime.utcnow(),
        "aadhaar_verified": True
    }
    
    users.insert_one(admin_user)
    print(f"Admin user {email} created successfully!")

if __name__ == "__main__":
    # You can change these defaults
    ADMIN_EMAIL = "admin@satya.com"
    ADMIN_PASS = "admin123"
    
    create_admin(ADMIN_EMAIL, ADMIN_PASS)
