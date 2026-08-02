import requests
import json
import numpy as np
import cv2
import tempfile
import os
from database import init_db, get_db
from bson import ObjectId
from flask import Flask

BASE = "http://localhost:5000/api"

# Initialize Mongo context to configure database
app = Flask("test_app")
init_db(app)
db = get_db()

# Create a clean test user
test_user_id = ObjectId("6a5da7c4a6f9c6ec6b06e8f1")
db.users.delete_one({"_id": test_user_id})
db.users.insert_one({
    "_id": test_user_id,
    "name": "Rahul Kumar",
    "email": "rahul@test.com",
    "password": b"hashed",
    "role": "user",
    "identity_locked": False,
    "identity_profile": {}
})

# Delete previous vault documents for this user
db.vault_documents.delete_many({"user_id": str(test_user_id)})

# Helper to create a valid JPEG
def create_test_image():
    tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    tmp.close()
    img = np.ones((100, 100, 3), dtype=np.uint8) * 240
    cv2.imwrite(tmp.name, img)
    with open(tmp.name, 'rb') as f:
        bytes_data = f.read()
    os.unlink(tmp.name)
    return bytes_data

# 1. First upload: non-Aadhaar document before Identity Lock is created (Should fail)
print("\n--- 1. Uploading Income Cert before Identity Lock ---")
image_bytes = create_test_image()
files = {"file": ("income.jpg", image_bytes, "image/jpeg")}
data = {"user_id": str(test_user_id), "force_engine": "income_verifier"}
r = requests.post(f"{BASE}/vault/upload", files=files, data=data)
print("Status:", r.status_code)
print("Response:", r.json())

# 2. Upload Aadhaar Card (Should verify and create Identity Lock)
print("\n--- 2. Uploading Aadhaar to Lock Identity ---")
files = {"file": ("aadhaar.jpg", image_bytes, "image/jpeg")}
data = {"user_id": str(test_user_id), "force_engine": "aadhaar_ocr"}
r = requests.post(f"{BASE}/vault/upload", files=files, data=data)
print("Status:", r.status_code)
print("Response:", r.json())

# 3. Check if user document updated
user_doc = db.users.find_one({"_id": test_user_id})
print("\nUser Identity Locked Status:", user_doc.get("identity_locked"))
print("Identity Profile:", json.dumps(user_doc.get("identity_profile"), indent=2))

# 4. Upload income certificate matching name (Should succeed)
print("\n--- 3. Uploading matching Income Cert ---")
files = {"file": ("income.jpg", image_bytes, "image/jpeg")}
data = {"user_id": str(test_user_id), "force_engine": "income_verifier"}
r = requests.post(f"{BASE}/vault/upload", files=files, data=data)
print("Status:", r.status_code)
try:
    print("Response:", r.json())
except Exception:
    print("Response Text:", r.text)

# 5. Upload document belonging to someone else
# We simulate this by changing the profile name temporarily to check mismatch
print("\n--- 4. Testing Identity Mismatch ---")
# Modify the profile to "Amit Sharma" to force mismatch
db.users.update_one({"_id": test_user_id}, {"$set": {"identity_profile.full_name": "Amit Sharma"}})

files = {"file": ("income.jpg", image_bytes, "image/jpeg")}
data = {"user_id": str(test_user_id), "force_engine": "income_verifier"}
r = requests.post(f"{BASE}/vault/upload", files=files, data=data)
print("Status:", r.status_code)
try:
    print("Response:", r.json())
except Exception:
    print("Response Text:", r.text)

# Reset profile name to "Rahul Kumar"
db.users.update_one({"_id": test_user_id}, {"$set": {"identity_profile.full_name": "Rahul Kumar"}})

# Clean up
db.users.delete_one({"_id": test_user_id})
db.vault_documents.delete_many({"user_id": str(test_user_id)})
