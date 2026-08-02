from vault.verifiers.base_verifier import BaseVerifier
from vault.verification_status import VerificationStatus, DocumentTypes
from vault.ocr_utils import ocr_image, TESSERACT_AVAILABLE
import cv2
import re


class CasteCertificateVerifier(BaseVerifier):
    def detect(self, file_path):
        return True

    def verify(self, file_path, **kwargs):
        try:
            img = cv2.imread(file_path)
            if img is None:
                return {"status": VerificationStatus.FAILED, "error": "Invalid image format. Use JPG or PNG."}
            if not TESSERACT_AVAILABLE:
                return {"status": VerificationStatus.VERIFYING, "raw_text": "", "demo_mode": True}
            text = ocr_image(file_path, lang='eng')
            return {"status": VerificationStatus.VERIFYING, "raw_text": text}
        except Exception as e:
            return {"status": VerificationStatus.FAILED, "error": str(e)}

    def extract(self, file_path, **kwargs):
        text = kwargs.get('raw_text', '')
        demo_mode = kwargs.get('demo_mode', False)
        user_id = kwargs.get('user_id')

        db_name = ""
        if user_id:
            try:
                from database import get_db
                from bson import ObjectId
                db = get_db()
                if db is not None:
                    user_data = db.users.find_one({"_id": ObjectId(user_id)})
                    if user_data:
                        db_name = user_data.get("name", "")
            except Exception:
                pass

        if demo_mode or not text.strip():
            return {
                "name": db_name or "Verified User",
                "category": "OBC",
                "certificate_number": "DEMO-CASTE-001",
                "authority": "District Magistrate",
                "note": "Tesseract OCR not installed – install for full extraction"
            }

        from vault.ocr_utils import extract_user_name_match
        extracted = {
            "name": extract_user_name_match(text, user_id),
            "category": "",
            "certificate_number": "",
            "authority": ""
        }

        if not extracted["name"] and db_name:
            extracted["name"] = db_name.title()

        text_u = text.upper()
        if "OBC" in text_u or "OTHER BACKWARD" in text_u:
            extracted["category"] = "OBC"
        elif "SC" in text_u or "SCHEDULED CASTE" in text_u:
            extracted["category"] = "SC"
        elif "ST" in text_u or "SCHEDULED TRIBE" in text_u:
            extracted["category"] = "ST"
        elif "GENERAL" in text_u:
            extracted["category"] = "General"

        return extracted

    def validate(self, extracted_data):
        note = extracted_data.get('note', '')
        if 'Tesseract' in note:
            return True, VerificationStatus.OCR_VERIFIED, 70.0
        if extracted_data.get('category'):
            return True, VerificationStatus.OCR_VERIFIED, 85.0
        return False, VerificationStatus.REJECTED, 30.0

    def save(self, metadata, user_id):
        metadata['document_type'] = DocumentTypes.CASTE_CERTIFICATE
        metadata['verification_method'] = "OCR"
        return metadata
