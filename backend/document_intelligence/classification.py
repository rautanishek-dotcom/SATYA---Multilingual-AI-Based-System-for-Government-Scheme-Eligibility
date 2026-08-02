import re
from typing import Dict, Optional

from .config import DOCUMENT_CLASSIFICATION_LABELS, SUPPORTED_DOCUMENT_TYPES


class DocumentClassifier:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.model = None

    def load_model(self):
        # Placeholder for YOLO or other detection model.
        self.model = None

    def classify(self, file_name: str, hint_text: str = "", ocr_text: str = "") -> Dict[str, object]:
        text = " ".join([file_name or "", hint_text or "", ocr_text or ""]).lower()
        classification = self._heuristic_classify(text)
        if classification["confidence"] < 0.85 and self.model is not None:
            # Placeholder: run model-based classification if available.
            pass
        if classification["confidence"] < 0.60:
            classification["reason"] = "low confidence document classification"
        return classification

    def _heuristic_classify(self, text: str) -> Dict[str, object]:
        mapping = {
            "aadhaar": "aadhaar_front",
            "aadhar": "aadhaar_front",
            "pan": "pan",
            "passport": "passport",
            "driving license": "driving_license",
            "driving licence": "driving_license",
            "voter id": "voter_id",
            "income certificate": "income_certificate",
            "birth certificate": "birth_certificate",
            "caste certificate": "caste_certificate",
            "residence certificate": "residence_certificate",
            "disability certificate": "disability_certificate",
            "ration card": "ration_card",
            "offline ekyc": "aadhaar_ekyc",
            "ekyc": "aadhaar_ekyc",
        }
        for token, doc_type in mapping.items():
            if token in text:
                return {
                    "document_type": doc_type,
                    "document_label": SUPPORTED_DOCUMENT_TYPES.get(doc_type, {}).get("label", doc_type),
                    "confidence": 0.98,
                    "supported": True,
                }
        # fallback to file hints
        for doc_type, meta in SUPPORTED_DOCUMENT_TYPES.items():
            if doc_type in text:
                return {
                    "document_type": doc_type,
                    "document_label": meta.get("label", doc_type),
                    "confidence": 0.95,
                    "supported": True,
                }
        return {
            "document_type": "unknown",
            "document_label": "Unknown Document",
            "confidence": 0.40,
            "supported": False,
            "reason": "No strong document cues found",
        }

    def is_confident(self, classification: Dict[str, object]) -> bool:
        return float(classification.get("confidence", 0.0)) >= 0.95

    def needs_review(self, classification: Dict[str, object]) -> bool:
        return float(classification.get("confidence", 0.0)) < 0.95
