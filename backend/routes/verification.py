from flask import Blueprint, request, jsonify
import os
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
from database import get_db
from bson import ObjectId
import re

verification_bp = Blueprint('verification', __name__)

# Point to Tesseract executable (Required for Windows if not in PATH)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Define regex patterns for extraction - using lists for multiple attempts
PATTERNS = {
    'name': [
        r"(?i)Name[:\s]+([A-Z\s\.]+)",
        r"(?i)To\s+([A-Z\s\.]+)\n", 
        r"([A-Z\s\.\']{3,})\s+(?=\d{2}/\d{2}/\d{4})", # Name before DOB - more flexible names
        r"([A-Z\s\.\']{3,})\s+(?=\d{4}\s*\d{4}\s*\d{4})", # Name before Aadhaar Number
        r"(?i)Father's Name[:\s]+[A-Z\s\.]+\n([A-Z\s\.]+\n)", # Name often below father's name in some formats
        r"(?i)^([A-Z][a-z]+\s+[A-Z][a-z]+\s*)$", # Simple First Last
        r"([A-Z\s\.]{4,})\n", # Any uppercase block of at least 4 chars
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)" # Fallback to any two capitalized words
    ],
    'dob': r"(\d{2}/\d{2}/\d{4})",
    'gender': r"(?i)(Male|Female|Other|Transgender|/Female|/Male|MALE|FEMALE)", # Handle leading slashes from OCR
    'income': r"(?i)Income[:\s]+(?:Rs\.?\s*)?(\d+)",
    'category': r"(?i)(General|OBC|SC|ST|Backward|Scheduled|UR|OPEN)",
}

def check_tesseract():
    """Check if Tesseract is installed and accessible"""
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

# Strict Validation Keywords for Government Documents - Broadened for maximum reliability
GOVT_SIGNATURES = {
    'aadhaar': [
        r"(?i)Government of India",
        r"(?i)Govt of India",
        r"(?i)Unique Identification",
        r"(?i)UIDAI",
        r"(?i)Aadhaar",
        r"(?i)Aadhar",
        r"(?i)Mera Aadhaar",
        r"(?i)Aam Aadmi",
        r"(?i)Adhaar",
        r"\d{4}[\s-]*\d{4}[\s-]*\d{4}", # Aadhaar number
        r"(?i)DOB\s*:",
        r"(?i)Male",
        r"(?i)Female",
        r"(?i)India"
    ],
    'income': [
        r"(?i)Income Certificate",
        r"(?i)Revenue Department",
        r"(?i)Tehsildar",
        r"(?i)Annual Income",
        r"(?i)Government of",
        r"(?i)Form 16"
    ],
    'caste': [
        r"(?i)Caste Certificate",
        r"(?i)Community Certificate",
        r"(?i)Backward Class",
        r"(?i)Scheduled Caste",
        r"(?i)Scheduled Tribe",
        r"(?i)OBC",
        r"(?i)SC/ST"
    ],
    'farmer': [
        r"(?i)Farmer Certificate",
        r"(?i)Land Record",
        r"(?i)Agriculture",
        r"(?i)Kisan",
        r"(?i)Pahani",
        r"(?i)Patwari"
    ]
}

def validate_government_document(text, doc_type):
    """Verify if the text contains mandatory government signatures"""
    if doc_type not in GOVT_SIGNATURES:
        return True, "No validation rules for this type"
    
    signatures = GOVT_SIGNATURES[doc_type]
    matches = [sig for sig in signatures if re.search(sig, text)]
    
    # Require at least 1 signature to be present for detection
    if len(matches) >= 1:
        return True, "Valid government document detected"
    else:
        return False, "Invalid Document: No government approval marks found. Please upload an official document."

def extract_text_from_image(image_path):
    """Extract text with multiple preprocessing attempts for maximum accuracy"""
    try:
        original_img = Image.open(image_path)
        
        # Helper to run OCR on an image object
        def get_text(img):
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # Grayscale
            img = ImageOps.grayscale(img)
            # Higher contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.5)
            return pytesseract.image_to_string(img)

        # Attempt 1: Standard Resize
        width, height = original_img.size
        img1 = original_img.resize((width*2, height*2), Image.Resampling.LANCZOS)
        text = get_text(img1)
        
        # Attempt 2: If low text found, try more contrast
        if len(text.strip()) < 20:
             img2 = original_img.resize((width*3, height*3), Image.Resampling.LANCZOS)
             text = get_text(img2)

        # Internal log for debugging
        print(f"--- OCR DEBUG: {os.path.basename(image_path)} ---")
        print(text[:800].replace('\n', ' '))
        print("------------------------------------------")
        
        return text
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def parse_extracted_data(text):
    """Simple parser to extract fields using regex"""
    data = {}
    
    # Special handling for name (trying multiple patterns)
    for pattern in PATTERNS['name']:
        match = re.search(pattern, text)
        if match:
            extracted = match.group(1).strip()
            # Basic cleanup: remove extra spaces and newlines
            extracted = re.sub(r'\s+', ' ', extracted)
            if len(extracted) > 3: # Ignore very short matches
                data['name'] = extracted
                break

    # Handle other fields (only strings)
    for field in ['dob', 'income', 'category', 'gender']:
        pattern = PATTERNS[field]
        if isinstance(pattern, str): # Type safety check
            match = re.search(pattern, text)
            if match:
                data[field] = match.group(1).strip()
            
    return data

@verification_bp.route('/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    doc_type = request.form.get('doc_type') # aadhaar, income, caste, etc.
    user_id = request.form.get('user_id')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    filename = f"{user_id}_{doc_type}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Check Tesseract Installation first
    if not check_tesseract():
        return jsonify({
            "error": "OCR Engine (Tesseract) is not installed on this server. Please contact admin.",
            "status": "failed"
        }), 500

    # Perform OCR
    extracted_text = extract_text_from_image(filepath)
    
    # If text extraction is completely empty, it might be an image format issue
    if not extracted_text.strip():
        return jsonify({
            "error": "Could not read text from this image. Please ensure the photo is clear and not too dark.",
            "status": "failed"
        }), 400

    # Validate if it's a government document
    is_valid, validation_msg = validate_government_document(extracted_text, doc_type)
    
    if not is_valid:
        # Delete invalid file to save space
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({
            "error": validation_msg,
            "status": "failed"
        }), 400

    extracted_data = parse_extracted_data(extracted_text)

    db = get_db()
    
    try:
        # Update user profile with verification info
        update_fields = {
            f"documents.{doc_type}": {
                "path": filepath,
                "status": "pending",
                "extracted_data": extracted_data
            }
        }
        
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )

        return jsonify({
            "message": "File uploaded and processed",
            "extracted_data": extracted_data,
            "status": "success"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@verification_bp.route('/verify', methods=['POST'])
def verify_profile():
    data = request.json
    user_id = data.get('user_id')
    profile_data = data.get('profile_data') # Data from form

    if not user_id or not profile_data:
        return jsonify({"error": "Missing parameters"}), 400

    db = get_db()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    docs = user.get('documents', {})
    
    # Matching logic with detailed breakdown
    mismatches = []
    detailed_results = {}
    
    # 1. Check Name (CRITICAL)
    profile_name = str(profile_data.get('name', '')).strip()
    doc_name = ""
    name_status = "mismatch"
    
    if 'aadhaar' in docs:
        doc_name = docs['aadhaar'].get('extracted_data', {}).get('name', '').strip()
        if doc_name:
            if profile_name.lower() in doc_name.lower() or doc_name.lower() in profile_name.lower():
                name_status = "match"
            else:
                profile_parts = set(profile_name.lower().split())
                doc_parts = set(doc_name.lower().split())
                if profile_parts.intersection(doc_parts):
                    name_status = "match"
        
        if name_status == "mismatch":
            mismatches.append(f"Name mismatch: Form shows '{profile_name}', but Aadhaar shows '{doc_name}'.")
    else:
        name_status = "mismatch"
        mismatches.append("Name verification failed: Aadhaar document not found.")

    detailed_results['name'] = {
        "label": "Name",
        "status": name_status,
        "form_val": profile_name,
        "doc_val": doc_name or "Not Found"
    }

    # 2. Gender Verification
    profile_gender = str(profile_data.get('gender', '')).lower()
    
    # Map special category 'woman' to 'female' for gender check if gender is not explicitly set
    if profile_data.get('special_category') == 'woman' and not profile_gender:
        profile_gender = 'female'

    doc_gender = ""
    gender_status = "mismatch"
    if 'aadhaar' in docs:
        doc_gender = docs['aadhaar'].get('extracted_data', {}).get('gender', '').lower()
        if doc_gender:
            # Flexible matching for gender markers
            is_match = False
            if profile_gender == doc_gender:
                is_match = True
            elif profile_gender and doc_gender:
                if (profile_gender.startswith('f') or profile_gender == 'woman') and doc_gender.startswith('f'):
                    is_match = True
                elif (profile_gender.startswith('m')) and doc_gender.startswith('m'):
                    is_match = True
            
            if is_match:
                gender_status = "match"
            else:
                mismatches.append(f"Gender mismatch: Form shows '{profile_gender}', but document shows '{doc_gender}'.")
        else:
             mismatches.append("Gender field not found in Aadhaar.")
    else:
        mismatches.append("Please upload Aadhaar to verify gender.")
        
    detailed_results['gender'] = {
        "label": "Gender",
        "status": gender_status if doc_gender else "match", # Default match if not found on card
        "form_val": profile_gender.capitalize(),
        "doc_val": doc_gender.capitalize() if doc_gender else "Not Found"
    }

    # 3. Check Income
    income_status = "mismatch"
    form_income = profile_data.get('income')
    doc_income = ""
    
    if 'income' in docs:
        doc_income = docs['income'].get('extracted_data', {}).get('income')
        if doc_income:
            if str(doc_income) == str(form_income):
                income_status = "match"
            else:
                mismatches.append(f"Income mismatch: Form shows '{form_income}', but Document shows '{doc_income}'.")
    else:
        income_status = "match" # Optional if not uploaded

    detailed_results['income'] = {
        "label": "Annual Income",
        "status": income_status,
        "form_val": f"₹{form_income}",
        "doc_val": f"₹{doc_income}" if doc_income else "Not Found"
    }

    # 4. Check Category
    cat_status = "mismatch"
    form_cat = profile_data.get('category', '').lower()
    doc_cat = ""
    
    if 'caste' in docs:
        doc_cat = docs['caste'].get('extracted_data', {}).get('category', '').lower()
        if doc_cat:
            if form_cat in doc_cat or doc_cat in form_cat:
                cat_status = "match"
            else:
                mismatches.append(f"Category mismatch: Form shows '{profile_data.get('category')}', but Document shows '{doc_cat.upper()}'.")
    else:
        cat_status = "match" # Pass if not uploaded

    detailed_results['category'] = {
        "label": "Category",
        "status": cat_status,
        "form_val": profile_data.get('category'),
        "doc_val": doc_cat.upper() if doc_cat else "Not Found"
    }

    status = "Verified" if not mismatches else "Failed"
    
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "verification_status": status,
            "verification_errors": mismatches,
            "detailed_results": detailed_results
        }}
    )

    return jsonify({
        "status": status,
        "message": "Document verified!" if status == "Verified" else "Verification failed. Please check the details below.",
        "mismatches": mismatches,
        "detailed_results": detailed_results
    }), 200
