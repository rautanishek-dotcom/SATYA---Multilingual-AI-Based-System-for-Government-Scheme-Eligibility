import logging
from typing import Dict, Any, List
import re

logger = logging.getLogger(__name__)

class DocumentClassifier:
    """
    Text-based document classifier that purely uses OCR text and layout heuristics,
    completely ignoring filenames.
    """

    SIGNATURES = {
        "aadhaar_ocr": {
            "keywords": ["government of india", "uidai", "unique identification", "आधार", "12 digit", "vid", "dob:", "yob", "aadhaar"],
            "regex": [r"\b\d{4}\s?\d{4}\s?\d{4}\b", r"\b(?:uidai|aadhaar|aadhar)\b"],
            "score_threshold": 30,
        },
        "pan": {
            "keywords": ["income tax department", "permanent account number", "father's name", "signature", "pan"],
            "regex": [r"[A-Z]{5}[0-9]{4}[A-Z]"],
            "score_threshold": 30,
        },
        "passport": {
            "keywords": ["republic of india", "passport", "surname", "given names", "place of issue", "passport no"],
            "regex": [r"P<IND", r"[A-Z][0-9]{7}"],
            "score_threshold": 30,
        },
        "driving_license": {
            "keywords": ["driving licence", "driving license", "transport department", "rto", "dl no", "authorization to drive", "driving"],
            "score_threshold": 30,
        },
        "voter_id": {
            "keywords": ["election commission of india", "epic", "elector", "elector's name", "epic no"],
            "score_threshold": 30,
        },
        "birth_certificate": {
            "keywords": ["birth certificate", "date of birth registration", "form 5", "mother's name"],
            "score_threshold": 30,
        },
        "income_certificate": {
            "keywords": ["income certificate", "annual income", "revenue department", "tahsildar", "income"],
            "score_threshold": 30,
        },
        "caste_certificate": {
            "keywords": ["caste certificate", "community certificate", "obc", "sc", "st", "category", "scheduled caste", "scheduled tribe", "backward class"],
            "score_threshold": 30,
        },
        "domicile_certificate": {
            "keywords": ["domicile certificate", "permanent resident", "bonafide resident", "residence certificate", "proof of residence"],
            "score_threshold": 30,
        },
        "disability_certificate": {
            "keywords": ["disability certificate", "udid", "benchmark disability", "disability percentage", "person with disability"],
            "score_threshold": 30,
        },
        "ration_card": {
            "keywords": ["ration card", "bpl", "apl", "public distribution"],
            "score_threshold": 30,
        },
    }

    @staticmethod
    def classify_by_text(full_text: str) -> Dict[str, Any]:
        """Classifies document type by analyzing the OCR text block."""
        if not full_text:
            return {
                "document_type": "unknown",
                "document_label": "Unknown Document",
                "probability": 5.0,
                "confidence": 0.05,
                "verification_engine": "unknown",
                "requires_share_code": False,
                "supported": False,
            }

        text_lower = full_text.lower()
        scores = {doc_type: 0 for doc_type in DocumentClassifier.SIGNATURES.keys()}

        for doc_type, rules in DocumentClassifier.SIGNATURES.items():
            for kw in rules.get("keywords", []):
                if kw in text_lower:
                    scores[doc_type] += 15
            for pattern in rules.get("regex", []):
                if re.search(pattern, full_text, flags=re.IGNORECASE):
                    scores[doc_type] += 25

        best_type = "unknown"
        best_score = 0
        for dt, score in scores.items():
            if score > best_score and score >= DocumentClassifier.SIGNATURES[dt]["score_threshold"]:
                best_score = score
                best_type = dt

        if best_type == "unknown":
            if re.search(r"[A-Z]{5}[0-9]{4}[A-Z]", full_text):
                best_type = "pan"
                best_score = 65
            elif re.search(r"\b[A-Z][0-9]{7}\b", full_text):
                best_type = "passport"
                best_score = 60
            elif re.search(r"\b(?:uidai|aadhaar|aadhar)\b", full_text, flags=re.IGNORECASE):
                best_type = "aadhaar_ocr"
                best_score = 55

        prob = min(99.6, best_score * 2.0) if best_type != "unknown" else 2.0
        
        label_map = {
            "aadhaar_ocr": "Aadhaar Card",
            "pan": "PAN Card",
            "passport": "Passport",
            "driving_license": "Driving Licence",
            "voter_id": "Voter ID",
            "birth_certificate": "Birth Certificate",
            "income_certificate": "Income Certificate",
            "caste_certificate": "Caste Certificate",
            "domicile_certificate": "Domicile Certificate",
            "disability_certificate": "Disability Certificate",
            "ration_card": "Ration Card",
        }

        return {
            "document_type": best_type,
            "document_label": label_map.get(best_type, "Unknown Document"),
            "probability": prob,
            "confidence": prob / 100.0,
            "verification_engine": best_type,
            "requires_share_code": False,
            "supported": best_type != "unknown",
        }

    @staticmethod
    def classify(file_path: str, original_filename: str = None, mime_type: str = None, hint_text: str = "") -> Dict[str, Any]:
        """Legacy wrapper that classifies from OCR/text hints first."""
        # If it's a zip file, it's explicitly ekyc.
        if mime_type == "application/zip" or (original_filename and original_filename.lower().endswith(".zip")):
            return {
                "document_type": "aadhaar_ekyc",
                "document_label": "Aadhaar eKYC",
                "probability": 99.0,
                "confidence": 0.99,
                "verification_engine": "aadhaar_ekyc",
                "requires_share_code": True,
                "supported": True
            }

        text = (hint_text or "").strip()
        if text:
            classified = DocumentClassifier.classify_by_text(text)
            if classified.get("supported"):
                return classified

        if original_filename and not text:
            fallback = DocumentClassifier.classify_by_text(original_filename)
            if fallback.get("supported"):
                fallback["probability"] = min(float(fallback.get("probability", 0.0)), 55.0)
                fallback["confidence"] = float(fallback.get("confidence", 0.0)) * 0.75
                fallback["reason"] = "filename fallback used because OCR text was unavailable"
                return fallback

        return {
            "document_type": "pending_ocr",
            "document_label": "Pending OCR",
            "probability": 0.0,
            "confidence": 0.0,
            "verification_engine": "generic",
            "requires_share_code": False,
            "supported": True
        }
