from flask import Blueprint, request, jsonify
import os
from database import get_db
from bson import ObjectId
import re
import cv2
import numpy as np
from PIL import Image
import pytesseract
import time
try:
    from pyzbar.pyzbar import decode
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    print("Warning: pyzbar not found or DLLs missing. Falling back to OpenCV QR detection.")
except Exception as e:
    PYZBAR_AVAILABLE = False
    print(f"Warning: pyzbar error: {e}. Falling back to OpenCV QR detection.")

import xml.etree.ElementTree as ET

verification_bp = Blueprint('verification', __name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configuration for Tesseract (Adjust path if needed for Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def is_valid_name(name):
    """Validate if extracted name looks legitimate (not garbage from OCR/QR)."""
    if not name or len(name.strip()) < 2:
        return False
    
    name_upper = name.upper()
    name_clean = name.replace(" ", "").replace(".", "").replace(",", "")
    
    # **REJECT CLEARLY INVALID PATTERNS**
    
    # 1. Reject if it looks like acronyms or abbreviations (all caps, no vowels, short)
    if name_upper == name and len(name_clean) < 5:  # All caps AND short
        vowels = sum(1 for c in name_clean if c in 'AEIOU')
        if vowels == 0:  # No vowels at all
            return False
    
    # 2. Reject if contains address keywords
    address_keywords = [
        "VILLAGE", "TALUK", "BLOCK", "DISTRICT", "POST", "TEHSIL", "MANDAL",
        "ROAD", "STREET", "LANE", "GALI", "OPPOSITION", "JHARKHAND", "ODISHA",
        "WEST BENGAL", "MAHARASHTRA", "PUNJAB", "HARYANA", "UTTARPRADESH",
        "ADDRESS", "NEAR", "OPP", "PIN", "LOC", "HOUSE", "FLAT", "APARTMENT",
        "SECTOR", "PHASE", "COLONY", "MENT", "NDT"  # Common corruption patterns
    ]
    for keyword in address_keywords:
        if keyword in name_upper:
            return False
    
    # 3. Reject if too many repeated characters
    for char in name_clean:
        if name_clean.count(char) >= 4:
            return False
    
    # 4. Reject if mostly numbers or symbols (<50% are letters)
    alpha_count = sum(1 for c in name_clean if c.isalpha())
    if len(name_clean) > 0 and alpha_count < len(name_clean) * 0.5:
        return False
    
    # 5. Minimum vowel requirement for longer strings
    vowel_count = sum(1 for c in name_clean.upper() if c in 'AEIOU')
    if len(name_clean) > 5 and vowel_count == 0:
        return False
    
    return True

def clean_val(val):
    """Clean extracted text: lowercase, remove spaces, commas, and special chars."""
    if not val: return ""
    # Only remove special characters, keep spaces for better matching
    cleaned = re.sub(r'[^a-z0-9 ]', '', str(val).lower()).strip()
    return re.sub(r'\s+', ' ', cleaned) # normalize spaces

def clean_val_no_space(val):
    """Clean extracted text without spaces for flexible matching."""
    if not val: return ""
    return re.sub(r'[^a-z0-9]', '', str(val).lower()).strip()

class SATYAPixelEngine:
    @staticmethod
    def validate_quality(img):
        """Validate if image is suitable for AI extraction."""
        if img is None: return False, "Missing Image"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_val = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_val < 35: return False, "Upload clear image (image too blurry)"
        return True, "Success"

    @staticmethod
    def neural_preprocess(img):
        """High-sensitivity Neural preprocessing."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Sharpening kernel
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        gray = cv2.filter2D(gray, -1, kernel)
        # Adaptive Thresholding for crisp text
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        # Scale up for OCR
        h, w = gray.shape
        scale = 1500.0 / h
        res = cv2.resize(gray, (int(w * scale), 1500), interpolation=cv2.INTER_CUBIC)
        return res

    @staticmethod
    def detect_type(text):
        """Auto-detect document type from internal text."""
        text = text.upper()
        if "GOVERNMENT OF INDIA" in text or "AADHAAR" in text or "UNIQUE IDENTIFICATION" in text:
            return "Aadhaar Card"
        if "INCOME CERTIFICATE" in text or "ANNUAL INCOME" in text:
            return "Income Certificate"
        if "CASTE" in text or "OBC" in text or "SCHEDULED" in text:
            return "Caste Certificate"
        return "Unknown"

    @staticmethod
    def normalize_date(date_str):
        """Converts various date formats to YYYY-MM-DD for matching."""
        if not date_str: return ""
        date_str = str(date_str).strip()

        # Already in YYYY-MM-DD format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str

        # DD/MM/YYYY or DD-MM-YYYY format
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
        if match:
            d, m, y = match.groups()
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"

        # Just return year if that's all we have
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            return year_match.group(1)

        return date_str

    @staticmethod
    def extract_fields(text, doc_type, user_input_name=None):
        """Structured field extraction with targeted name tracking."""
        data = {"name": "", "dob": "", "income": "", "category": ""}
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if doc_type == "Aadhaar Card":
            # Targeted Matcher: Look for user's name words anywhere in text
            if user_input_name:
                inp_words = [w for w in clean_val(user_input_name).upper().split() if len(w) > 3]
                if inp_words:
                    for line in lines[:20]:
                        if any(w in clean_val(line).upper() for w in inp_words):
                            if is_valid_name(line):
                                data['name'] = line
                                break
            
            # Fallback filters - only accept valid names
            addr_keys = ["VLG", "BIA", "PHT", "VILL", "POST", "DIST", "TALUK", "VILLAGE", "BLOCK", "GALI"]
            if not data['name']:
                for line in lines[:15]:
                    line_u = line.upper()
                    if any(h in line_u for h in ["INDIA", "UIDAI", "AADHAAR", "SARKAR", "GOVERNMENT"]): continue
                    if any(ak in line_u for ak in addr_keys): continue
                    if len(re.findall(r'\d', line)) > 4: continue
                    words = [w for w in line.split() if len(w) > 2]
                    if 2 <= len(words) <= 5 and any(c.isupper() for c in line[0]):
                        candidate_name = " ".join(words)
                        if is_valid_name(candidate_name):  # Validate before accepting
                            data['name'] = candidate_name
                            break
            
            # DOB Search
            dates = re.findall(r'\d{2}[/-]\d{2}[/-]\d{4}', text)
            if dates: data['dob'] = SATYAPixelEngine.normalize_date(dates[0])
            else:
                years = re.findall(r'\d{4}', text)
                if years: data['dob'] = years[0]
            
        elif doc_type == "Income Certificate":
            # Context-specific: Look for salary/annual income patterns
            amounts = re.findall(r'(?:Rs\.?|INR|Total|Annual|Income|Amount|Salary)[:\s]*([\d,]+)', text, re.I)
            if amounts: 
                # Pick the most likely candidate (usually the largest or last listed)
                valid_nums = [n.replace(',', '') for n in amounts if len(n.replace(',', '')) >= 5]
                if valid_nums: data['income'] = valid_nums[0]
                
        elif doc_type == "Caste Certificate":
            # Context-specific keywords
            for cat in ["OBC", "SC", "ST", "GENERAL"]:
                if cat in text.upper():
                    data['category'] = cat; break
                    
        return data

@verification_bp.route('/upload', methods=['POST'])
def upload_document():
    try:
        user_id = request.form.get('user_id')
        user_input_name = request.form.get('name')
        file = request.files.get('file')

        if not file: return jsonify({"error": "No file uploaded"}), 400

        # Save and Process
        path = os.path.join(UPLOAD_FOLDER, f"AI_EXTRACT_{int(time.time())}.png")
        file.save(path)
        img = cv2.imread(path)

        # 1. Image Quality Check
        ok, msg = SATYAPixelEngine.validate_quality(img)
        if not ok: return jsonify({"status": "Failed", "error": msg}), 200

        # 2. Neural OCR Engine (LSTM)
        proc = SATYAPixelEngine.neural_preprocess(img)
        raw_text = pytesseract.image_to_string(proc, config='--oem 3 --psm 6', lang='eng+hin')
        
        if not raw_text.strip():
            return jsonify({"status": "Failed", "error": "Document not readable"}), 200

        # 3. Structured Prediction
        doc_type = SATYAPixelEngine.detect_type(raw_text)
        extracted = SATYAPixelEngine.extract_fields(raw_text, doc_type, user_input_name)
        
        # 4. QR Fallback for Aadhaar
        if doc_type == "Aadhaar Card":
            detector = cv2.QRCodeDetector()
            qr_data, _, _ = detector.detectAndDecode(img)
            if qr_data:
                try:
                    # Try parsing as XML first
                    root = ET.fromstring(qr_data)
                    # Try nested tags first (modern format: <name>...  </name>)
                    name_elem = root.find('name')
                    dob_elem = root.find('dob')
                    if name_elem is not None and name_elem.text and is_valid_name(name_elem.text.strip()):
                        extracted['name'] = name_elem.text.strip()
                    if dob_elem is not None and dob_elem.text:
                        extracted['dob'] = SATYAPixelEngine.normalize_date(dob_elem.text.strip())
                    
                    # Fallback to attributes if tags don't exist (older format)
                    if not extracted['name']:
                        attr_name = root.get('name', '') or root.get('Name', '')
                        if is_valid_name(attr_name):
                            extracted['name'] = attr_name
                    if not extracted['dob']:
                        dob_attr = root.get('dob', '') or root.get('DOB', '')
                        if dob_attr:
                            extracted['dob'] = SATYAPixelEngine.normalize_date(dob_attr)
                except ET.ParseError:
                    # Fallback to regex if XML parsing fails
                    m_name = re.search(r'<name[^>]*>([^<]+)</name>', qr_data, re.I)
                    m_dob = re.search(r'<dob[^>]*>([^<]+)</dob>', qr_data, re.I)
                    if m_name and is_valid_name(m_name.group(1).strip()): 
                        extracted['name'] = m_name.group(1).strip()
                    if m_dob: extracted['dob'] = SATYAPixelEngine.normalize_date(m_dob.group(1).strip())

        # Deep-Scan Fallback: If user input name is found as a substring of any line
        if user_input_name and not extracted['name']:
            if clean_val(user_input_name).upper() in clean_val(raw_text).upper():
                extracted['name'] = user_input_name

        # 5. Build Final Confidence JSON & Final Verification
        is_verified = "Failed"
        confidence = 0
        mismatches = []
        status = "Processing"
        
        # Name Validation (50%)
        if user_input_name and extracted['name']:
            # Use version without spaces for more flexible matching
            inp_clean = clean_val_no_space(user_input_name)
            ext_clean = clean_val_no_space(extracted['name'])

            # Match if: exact match, or one is substring of other (with >3 char minimum)
            if inp_clean and ext_clean:
                if inp_clean == ext_clean:
                    confidence += 50
                elif (len(inp_clean) > 3 and inp_clean in ext_clean) or \
                     (len(ext_clean) > 3 and ext_clean in inp_clean):
                    confidence += 50  # Allow partial matches (e.g. first/last name only)
                else:
                    # Check word-level match (e.g. "John Smith" vs "John")
                    inp_words = inp_clean.split()
                    ext_words = ext_clean.split()
                    if any(word in ext_clean for word in inp_words if len(word) > 3):
                        confidence += 40  # Partial word match = 40 points

            if confidence < 40:
                mismatches.append(f"Name mismatch: '{extracted['name']}' (Card) vs '{user_input_name}' (Entered)")
        else:
            if user_input_name: mismatches.append("Name not found in document")
        
        # DOB Validation (50%)
        inp_dob = request.form.get('dob')
        if inp_dob and extracted['dob']:
            # Normalize both dates to YYYY-MM-DD format for comparison
            inp_dob_norm = SATYAPixelEngine.normalize_date(inp_dob)
            ext_dob_norm = SATYAPixelEngine.normalize_date(extracted['dob'])

            # Remove non-alphanumeric for comparison (handles format differences)
            inp_clean = clean_val_no_space(inp_dob_norm)
            ext_clean = clean_val_no_space(ext_dob_norm)

            if inp_clean and ext_clean and inp_clean == ext_clean:
                confidence += 50
            else:
                mismatches.append(f"DOB mismatch: '{ext_dob_norm}' (Card) vs '{inp_dob_norm}' (Entered)")
        elif inp_dob:
            mismatches.append("DOB not found in document")

        # Sync with Database
        db = get_db()
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {f"documents.{doc_type.split()[0].lower()}": {
                "status": "Verified" if confidence >= 50 else "Processed",
                "extracted_data": extracted,
                "confidence": confidence
            }}}
        )

        # Immediate Verification Status
        if confidence >= 90:
            status = "Verified"
        elif confidence >= 50:
            status = "Partially Verified"
        elif confidence >= 40:
            status = "Processing"
        else:
            status = "Rejected"

        return jsonify({
            "status": status,
            "score": confidence,
            "verificationStatus": status,
            "mismatches": mismatches,
            "results": {
                "name": "Verified" if confidence >= 40 else "Mismatch",
                "dob": "Verified" if confidence >= 40 else "Mismatch",
                "income": "Not Scanned",
                "category": "Not Scanned"
            },
            "extracted_summary": {
                "name": extracted['name'] or 'N/A',
                "dob": extracted['dob'] or 'N/A',
                "income": extracted['income'] or '0',
                "category": extracted['category'] or 'N/A'
            },
            "log": ["Neural Verification Complete", f"Result: {status} ({confidence}/100)"],
            "raw_text": ["Neural processing successful."]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal Engine Error: {str(e)}"}), 500


@verification_bp.route('/verify', methods=['POST'])
def verify_profile():
    data = request.json
    user_id = data.get('user_id')
    user_input = data.get('profile_data', {})

    db = get_db()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user: return jsonify({"error": "User not found"}), 404

    docs = user.get('documents', {})
    score = 0
    results = {}
    mismatches = []

    # Aadhaar Scan Data (50 pts) - Priotize data sent from frontend (ephemeral)
    aa_ext = data.get('aadhaar_data', {})
    if not aa_ext or not aa_ext.get('name'):
        aa_doc = docs.get('aadhaar', {})
        aa_ext = aa_doc.get('extracted_data', {})
    
    # 1. Identity Match (Must be non-empty)
    ext_name = aa_ext.get('name')
    inp_name = user_input.get('name')

    print(f"[VERIFY] Extracted name: '{ext_name}', Input name: '{inp_name}'")

    if ext_name and inp_name:
        c_ext = clean_val_no_space(ext_name)
        c_inp = clean_val_no_space(inp_name)
        
        print(f"[VERIFY] Cleaned - Extracted: '{c_ext}', Input: '{c_inp}'")
        
        # Exact match
        if c_ext == c_inp:
            name_match = True
            print("[VERIFY] ✓ Exact match")
        # Substring match (for partial names or abbreviations)
        elif len(c_inp) > 3 and c_inp in c_ext:
            name_match = True
            print(f"[VERIFY] ✓ Substring match: input '{c_inp}' found in extracted '{c_ext}'")
        elif len(c_ext) > 3 and c_ext in c_inp:
            name_match = True
            print(f"[VERIFY] ✓ Reverse substring match: extracted '{c_ext}' found in input '{c_inp}'")
        else:
            # Check word-level match - extract last name from both
            inp_words = c_inp.split() if c_inp.count(' ') else [c_inp]
            ext_words = c_ext.split() if c_ext.count(' ') else [c_ext]
            
            # Check if last names match (common pattern: "FirstName LastName")
            name_match = False
            for iw in inp_words:
                if len(iw) > 3:  # Valid word length
                    for ew in ext_words:
                        if len(ew) > 3 and iw == ew:
                            name_match = True
                            print(f"[VERIFY] ✓ Word match: '{iw}' == '{ew}'")
                            break
                if name_match:
                    break
            
            if not name_match:
                print(f"[VERIFY] ✗ No match found between words: input={inp_words}, extracted={ext_words}")
    else:
        name_match = False
        print(f"[VERIFY] ✗ Empty name: ext_name={ext_name}, inp_name={inp_name}")

    # 2. DOB Match
    ext_dob = aa_ext.get('dob')
    inp_dob = user_input.get('dob')
    if ext_dob and inp_dob:
        ext_dob_norm = SATYAPixelEngine.normalize_date(ext_dob)
        inp_dob_norm = SATYAPixelEngine.normalize_date(inp_dob)
        ext_clean = clean_val_no_space(ext_dob_norm)
        inp_clean = clean_val_no_space(inp_dob_norm)
        dob_match = ext_clean == inp_clean if (ext_clean and inp_clean) else False
    else:
        dob_match = False
        
    if name_match and dob_match:
        score += 50
        results['name'] = results['dob'] = 'Verified'
    else:
        results['name'] = 'Verified' if name_match else 'Mismatch'
        results['dob'] = 'Verified' if dob_match else 'Mismatch'
        if not name_match: mismatches.append(f"Name mismatch: Card says '{ext_name}' vs Input '{inp_name}'")
        if not dob_match: mismatches.append(f"DOB mismatch: Card says '{ext_dob}' vs Input '{inp_dob}'")

    # 2. Income Logic (25 pts)
    inc_doc = docs.get('income', {})
    inc_ext = inc_doc.get('extracted_data', {})
    ext_income_val = inc_ext.get('income')
    
    if ext_income_val is not None:
        try:
            ext_inc = int(ext_income_val)
            # Safe conversion for input
            raw_inp_inc = user_input.get('income', '0')
            if not raw_inp_inc: raw_inp_inc = '0'
            inp_inc = int(str(raw_inp_inc).replace(',', '').split('.')[0])
            
            if inp_inc > 0 and abs(ext_inc - inp_inc) < (inp_inc * 0.15): # 15% tolerance
                score += 25
                results['income'] = 'Verified'
            else:
                results['income'] = 'Mismatch'
                mismatches.append(f"Income mismatch: Extracted {ext_inc}, Input {inp_inc}")
        except (ValueError, TypeError):
            results['income'] = 'Error Parsing'
    else:
        results['income'] = 'Not Scanned'

    # 3. Category Logic (25 pts)
    caste_doc = docs.get('caste', {})
    caste_ext = caste_doc.get('extracted_data', {})
    if caste_ext.get('category'):
        cat_clean = clean_val_no_space(caste_ext['category'])
        inp_cat_clean = clean_val_no_space(user_input.get('category', ''))
        if cat_clean == inp_cat_clean:
            score += 25
            results['category'] = 'Verified'
        else:
            results['category'] = 'Mismatch'
            mismatches.append(f"Category mismatch: '{caste_ext['category']}' vs '{user_input.get('category')}'")
    else:
        results['category'] = 'Not Scanned'

    # Final Status
    if score >= 80: status = "Verified"
    elif score >= 50: status = "Partially Verified"
    else: status = "Rejected"

    return jsonify({
        "status": status,
        "score": score,
        "results": results,
        "mismatches": mismatches,
        "extracted_summary": {
            "name": aa_ext.get('name', 'N/A'),
            "dob": aa_ext.get('dob', 'N/A'),
            "income": str(inc_ext.get('income', '0')),
            "category": caste_ext.get('category', 'N/A')
        },
        "scanning_log": [f"Scoring Complete. Total Score: {score}", f"Status: {status}"]
    })

@verification_bp.route('/scan-aadhaar', methods=['POST'])
def scan_aadhaar_qr():
    """
    Specialized route for Aadhaar QR scanning to auto-fill profiles.
    Returns structured data if extraction is successful.
    """
    try:
        user_id = request.form.get('user_id')
        file = request.files.get('file')

        expected_name = ""
        try:
            if user_id and user_id != 'undefined':
                db = get_db()
                from bson.objectid import ObjectId
                user = db.users.find_one({"_id": ObjectId(user_id)})
                if user and user.get("name"):
                    expected_name = clean_val(user["name"]).upper()
        except Exception as ignore:
            pass

        if not file:
            return jsonify({"error": "No Aadhaar document uploaded"}), 400

        # Save temporarily
        filename = f"Aadhaar_Scan_{int(time.time())}.png"
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        # 1. Image Quality Check
        img = cv2.imread(path)
        ok, msg = SATYAPixelEngine.validate_quality(img)
        if not ok:
            return jsonify({
                "status": "Failed",
                "message": msg,
                "error_type": "quality"
            }), 200

        # 2. QR Code Detection
        qr_found = False
        raw_data = ""

        # Strategy 1: Initial Scan with pyzbar (Fastest)
        if PYZBAR_AVAILABLE:
            try:
                decoded_objects = decode(Image.open(path))
                if decoded_objects:
                    qr_found = True
                    raw_data = decoded_objects[0].data.decode('utf-8')
            except Exception as e:
                print(f"Pyzbar runtime error: {e}")

        # Strategy 2: Scan with OpenCV on multiple processed versions if not found
        if not qr_found:
            # Prepare processed images for detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 2.1 Standard OpenCV Detection
            detector = cv2.QRCodeDetector()
            qr_data, _, _ = detector.detectAndDecode(img)
            
            if qr_data:
                qr_found = True
                raw_data = qr_data
            else:
                # 2.2 Try with Histogram Equalization (Contrast Enhancement)
                equ = cv2.equalizeHist(gray)
                qr_data, _, _ = detector.detectAndDecode(equ)
                if qr_data:
                    qr_found = True
                    raw_data = qr_data
                else:
                    # 2.3 Try at a larger scale if it's a small QR
                    h, w = gray.shape
                    resized = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
                    qr_data, _, _ = detector.detectAndDecode(resized)
                    if qr_data:
                        qr_found = True
                        raw_data = qr_data

        # Fallback to pure pyzbar on processed versions if still not found
        if not qr_found and PYZBAR_AVAILABLE:
             # Try sharpening
             kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
             sharpened = cv2.filter2D(img, -1, kernel)
             pil_sharpened = Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_BGR2RGB))
             decoded_objects = decode(pil_sharpened)
             if decoded_objects:
                qr_found = True
                raw_data = decoded_objects[0].data.decode('utf-8')
        
        if not qr_found:
            return jsonify({
                "status": "Failed",
                "message": "QR code not detected. Please upload a clear Aadhaar image.",
                "error_type": "qr_not_found"
            }), 200

        # 3. Data Extraction (Aadhaar QR is usually XML or Secure Binary)
        extracted_data = {
            "name": "",
            "dob": "",
            "gender": "",
            "address": "",
            "is_verified": False,
            "debug_source": ""  # Track where data came from
        }

        print(f"[DEBUG QR] Raw data length: {len(raw_data)}, First 200 chars: {raw_data[:200]}")

        # Case 1: XML-based QR
        if "<PrintLetterBarcodeData" in raw_data:
            try:
                # Handle cases where it is not perfectly formed XML
                root = ET.fromstring(raw_data)
                
                # Try nested tags first (modern format)
                name_elem = root.find('name')
                dob_elem = root.find('dob')
                gender_elem = root.find('gender')
                
                # Only accept name from QR if it's reasonably long (not abbreviated like "Rt")
                if name_elem is not None and name_elem.text and len(name_elem.text.strip()) > 3:
                    extracted_data["name"] = name_elem.text.strip()
                    extracted_data["debug_source"] = "XML_tag_name"
                else:
                    attr_name = root.get('name', '')
                    # Also check attribute but require minimum length of 4 chars (e.g., "John" or longer names)
                    if len(attr_name) > 3:
                        extracted_data["name"] = attr_name
                        extracted_data["debug_source"] = "XML_attr_name"
                    
                if dob_elem is not None and dob_elem.text:
                    extracted_data["dob"] = SATYAPixelEngine.normalize_date(dob_elem.text.strip())
                else:
                    extracted_data["dob"] = root.get('dob', '')
                    if extracted_data["dob"]:
                        extracted_data["dob"] = SATYAPixelEngine.normalize_date(extracted_data["dob"])
                
                if gender_elem is not None and gender_elem.text:
                    extracted_data["gender"] = gender_elem.text.strip()
                else:
                    extracted_data["gender"] = root.get('gender', '')

                # Handle Gender format
                if extracted_data["gender"] == 'M': extracted_data["gender"] = 'Male'
                elif extracted_data["gender"] == 'F': extracted_data["gender"] = 'Female'
                
                # Combine address parts (try nested elements first, then attributes)
                addr_parts = []
                addr_keys = ['house', 'street', 'lm', 'loc', 'vtc', 'dist', 'state', 'pc']
                for k in addr_keys:
                    elem = root.find(k)
                    if elem is not None and elem.text:
                        addr_parts.append(elem.text.strip())
                    elif root.get(k):
                        addr_parts.append(root.get(k))
                if addr_parts:
                    extracted_data["address"] = ", ".join(addr_parts)
                
                if extracted_data["name"]:  # Mark as verified only if we got the name
                    extracted_data["is_verified"] = True
                print(f"[DEBUG XML] Extracted name: {extracted_data['name']}, DOB: {extracted_data['dob']}")
            except Exception as e:
                print(f"[DEBUG] XML Parsing Error: {e}")
        
        # Case 2: Secure QR or alternative formats
        if not extracted_data["name"]:
            # Try regex patterns for nested XML tags - require 4+ chars minimum
            m_name = re.search(r'<name[^>]*>([^<]+)</name>', raw_data, re.I)
            if m_name and len(m_name.group(1).strip()) > 3: 
                extracted_data["name"] = m_name.group(1).strip()
                extracted_data["debug_source"] = "regex_tag_name"
            
            m_dob = re.search(r'<dob[^>]*>([^<]+)</dob>', raw_data, re.I)
            if m_dob: 
                extracted_data["dob"] = SATYAPixelEngine.normalize_date(m_dob.group(1).strip())
            
            m_gender = re.search(r'<gender[^>]*>([^<]+)</gender>', raw_data, re.I)
            if m_gender: 
                extracted_data["gender"] = m_gender.group(1).strip()
            
            # Fallback to attribute patterns - require 4+ chars minimum
            if not extracted_data["name"]:
                m_name = re.search(r'name="([^"]+)"', raw_data, re.I)
                if m_name and len(m_name.group(1).strip()) > 3: 
                    extracted_data["name"] = m_name.group(1).strip()
                    extracted_data["debug_source"] = "regex_attr_name"
            
            if not extracted_data["dob"]:
                m_dob = re.search(r'dob="([^"]+)"', raw_data, re.I)
                if m_dob: 
                    extracted_data["dob"] = SATYAPixelEngine.normalize_date(m_dob.group(1).strip())
            
            # Also try plain text patterns (Name: John, DOB: 1990-05-15)
            if not extracted_data["name"]:
                m_name = re.search(r'Name:?\s*([\w\s\.]+?)(?:\n|DOB|Gender|$)', raw_data, re.I)
                if m_name and len(m_name.group(1).strip()) > 3: 
                    extracted_data["name"] = m_name.group(1).strip()
                    extracted_data["debug_source"] = "regex_plaintext"
            
            if not extracted_data["dob"]:
                m_dob = re.search(r'DOB:?\s*([\d/-]+)', raw_data, re.I)
                if m_dob: 
                    extracted_data["dob"] = SATYAPixelEngine.normalize_date(m_dob.group(1).strip())
            
            if not extracted_data["gender"]:
                m_gender = re.search(r'Gender:?\s*(Male|Female|M|F)', raw_data, re.I)
                if m_gender: 
                    g = m_gender.group(1).strip()
                    if g.upper() in ['M', 'MALE']: 
                        extracted_data["gender"] = 'Male'
                    elif g.upper() in ['F', 'FEMALE']: 
                        extracted_data["gender"] = 'Female'
            
            if extracted_data["name"] and len(extracted_data["name"]) > 3:
                extracted_data["is_verified"] = True
            print(f"[DEBUG Fallback] Extracted name: {extracted_data['name']}, Source: {extracted_data.get('debug_source', 'unknown')}")

        # Final Strategy: OCR Fallback (if QR fails)
        if not extracted_data["is_verified"]:
             print("[DEBUG] Falling back to OCR since QR didn't provide verified name")
             # Use the Neural OCR engine
             proc = SATYAPixelEngine.neural_preprocess(img)
             raw_text = pytesseract.image_to_string(proc, config='--oem 3 --psm 4', lang='eng+hin')
             
             print(f"[DEBUG OCR] Raw OCR text (first 500 chars): {raw_text[:500]}")
             
             # Extract from OCR text structurally: The Name always comes right before the DOB in e-Aadhaar/Digilocer
             lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
             print(f"[DEBUG OCR] Total lines: {len(lines)}")
             
             ignore_words = ["GOVERNMENT", "INDIA", "UIDAI", "FATHER", "NAME", "DOB", "YEAR", "BIRTH", "MALE", "FEMALE", "GENDER", "ADDRESS", "AADHAAR"]
             
             # Extract strictly by position (Name is right before or on the DOB line)
             for i, line in enumerate(lines[:20]):
                 line_u = line.upper()
                 
                 if re.search(r'\d{4}', line): # Found a year
                    m_dob = re.search(r'(\d{4}-\d{2}-\d{2})|(\d{2}/\d{2}/\d{4})', line)
                    if m_dob and not extracted_data["dob"]:
                        extracted_data["dob"] = SATYAPixelEngine.normalize_date(m_dob.group(0))
                        print(f"[DEBUG OCR] Found DOB on line {i}: {line}")
                        
                        # Check if merged on same line (e.g. "Rakesh Ranjan 2004-03-27")
                        idx = line.find(m_dob.group(0))
                        if idx > 3:
                            leftover = line[:idx].strip()
                            # Strip out Hindi or garbage
                            leftover = re.sub(r'[^A-Za-z\s\.]', '', leftover).strip()
                            print(f"[DEBUG OCR] Checking name on same line as DOB: '{leftover}'")
                            if is_valid_name(leftover):
                                extracted_data["name"] = leftover.title()
                                print(f"[DEBUG OCR] Accepted name from same line: {extracted_data['name']}")
                            else:
                                print(f"[DEBUG OCR] Name validation failed for: '{leftover}'")
                        
                        # If not on same line, step backwards to find the nearest valid Name
                        if not extracted_data["name"] and i > 0:
                            for j in range(i-1, -1, -1):
                                prev_line = lines[j]
                                prev_u = prev_line.upper()
                                # Ignore small noise words, headers, and DigiLocker elements
                                if any(w in prev_u for w in ignore_words + ["RNMENT", "NDT", "GOVT", "TAP", "ZOOM", "MERA", "PEHCHAAN"]):
                                    continue
                                
                                # Strip out Hindi or garbage, keep only English letters
                                cleaned = re.sub(r'[^A-Za-z\s\.]', '', prev_line).strip()
                                cleaned = re.sub(r'\s+', ' ', cleaned)
                                print(f"[DEBUG OCR] Checking line {j} before DOB: '{cleaned}'")
                                if is_valid_name(cleaned):
                                    extracted_data["name"] = cleaned.title()
                                    extracted_data["debug_source"] = "ocr_predate"
                                    print(f"[DEBUG OCR] Accepted name before DOB: {extracted_data['name']}")
                                    break
                                else:
                                    print(f"[DEBUG OCR] Name validation failed for: '{cleaned}'")
                    continue
                 
                 # Gender search independent of Name
                 if "MALE" in line_u and "FEMALE" not in line_u: extracted_data["gender"] = "Male"
                 elif "FEMALE" in line_u: extracted_data["gender"] = "Female"

             # Fallback: If we still don't have a name (e.g. DOB misread), scan globally
             if not extracted_data["name"]:
                 print("[DEBUG OCR] No name found using DOB strategy, trying global scan...")
                 digilocker_ignores = ignore_words + ["RNMENT", "NDT", "GOVT", "TAP", "ZOOM", "MERA", "PEHCHAAN"]
                 for idx, line in enumerate(lines[:20]):
                     line_u = line.upper()
                     if len(line) < 3:
                         continue
                     if any(w in line_u for w in digilocker_ignores):
                         print(f"[DEBUG OCR] Skipping line {idx} (contains ignore word): {line}")
                         continue
                     cleaned = re.sub(r'[^A-Za-z\s\.]', '', line).strip()
                     cleaned = re.sub(r'\s+', ' ', cleaned)
                     print(f"[DEBUG OCR] Trying global line {idx}: '{cleaned}'")
                     if is_valid_name(cleaned):
                         words = cleaned.split()
                         # Accept if 2+ words (full name) or if it's clearly a name
                         if len(words) >= 2:
                             extracted_data["name"] = cleaned.title()
                             extracted_data["debug_source"] = "ocr_global"
                             print(f"[DEBUG OCR] Accepted name from global scan: {extracted_data['name']}")
                             break
                         else:
                             print(f"[DEBUG OCR] Single word '{cleaned}', looking for full name...")

             if extracted_data["name"]:
                 extracted_data["is_verified"] = True
             print(f"[DEBUG OCR] Final extraction: name='{extracted_data['name']}', dob='{extracted_data['dob']}', verified={extracted_data['is_verified']}")

        if not extracted_data["is_verified"]:
             return jsonify({
                "status": "Failed",
                "message": "Aadhaar data could not be extracted. Please upload a clearer image.",
                "error_type": "decoding_failed"
            }), 200

        return jsonify({
            "status": "Success",
            "message": "Aadhaar scanned successfully!",
            "data": extracted_data
        }), 200

    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@verification_bp.route('/confirm-aadhaar', methods=['POST'])
def confirm_aadhaar():
    """
    Saves the user-confirmed Aadhaar data into the database.
    """
    try:
        data = request.json
        user_id = data.get('user_id')
        extracted_data = data.get('profile_data')

        if not user_id or not extracted_data:
            return jsonify({"error": "User ID and profile data required"}), 400

        db = get_db()
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                "aadhaar_verified": True,
                "profile.name": extracted_data.get("name"),
                "profile.dob": extracted_data.get("dob"),
                "profile.gender": extracted_data.get("gender"),
                "profile.address": extracted_data.get("address"),
                "documents.aadhaar": {
                    "status": "Verified",
                    "extracted_data": {
                        "name": extracted_data.get("name"),
                        "dob": extracted_data.get("dob"),
                        "gender": extracted_data.get("gender")
                    },
                    "confidence": 100,
                    "verified_at": int(time.time())
                }
            }}
        )

        return jsonify({"status": "Success", "message": "Profile updated and verified!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@verification_bp.route('/clear-documents', methods=['POST'])
def clear_documents():
    """
    Clears stored document verification data for a user.
    Allows user to re-scan documents fresh.
    """
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        db = get_db()
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                "documents": {},
                "aadhaar_verified": False,
                "profile.name": "",
                "profile.dob": "",
                "profile.gender": ""
            }}
        )
        
        return jsonify({"status": "Success", "message": "Documents cleared. You can now re-verify."}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@verification_bp.route('/reset-documents/<user_id>', methods=['POST'])
def reset_documents(user_id):
    """
    Force reset and clear all stored document verification data.
    This removes corrupted or old data so users can re-verify fresh.
    """
    try:
        db = get_db()
        
        # Clear all documents and profile data
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$unset': {
                "documents": "",
                "aadhaar_verified": "",
                "profile.name": "",
                "profile.dob": "",
                "profile.gender": "",
                "profile.address": ""
            }}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "status": "Success",
            "message": "All documents cleared successfully. You can now re-verify your documents."
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@verification_bp.route('/validate-stored-data/<user_id>', methods=['GET'])
def validate_stored_data(user_id):
    """
    Check if stored document data is valid.
    If invalid/corrupted, clear it automatically.
    """
    try:
        db = get_db()
        user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        docs = user.get('documents', {})
        has_invalid = False
        invalid_fields = []
        
        # Check each document type
        for doc_type, doc_data in docs.items():
            if isinstance(doc_data, dict):
                extracted = doc_data.get('extracted_data', {})
                name = extracted.get('name', '')
                
                # Check if name looks like garbage
                if name and ('NDT' in name.upper() or 'RNMENT' in name.upper() or 
                            name.count(name[0]) >= 3 if name else False):
                    has_invalid = True
                    invalid_fields.append(doc_type)
        
        if has_invalid:
            # Auto-clear invalid data
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$unset': {'documents': ""}}
            )
            return jsonify({
                "status": "Cleaned",
                "message": f"Corrupted data found in {', '.join(invalid_fields)}. Data has been cleared.",
                "cleared_fields": invalid_fields
            }), 200
        
        return jsonify({
            "status": "Valid",
            "message": "Stored data is valid"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
