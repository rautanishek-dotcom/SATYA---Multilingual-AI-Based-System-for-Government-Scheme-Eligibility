import os
from typing import Dict, List, Optional

from .config import SUPPORTED_LANGUAGES
from .correction import normalize_fields
from .qr import QREngine
from .classification import DocumentClassifier
from .layout import LayoutDetector


class OCRPipeline:
    def __init__(self, classifier: Optional[DocumentClassifier] = None, layout_detector: Optional[LayoutDetector] = None):
        self.classifier = classifier or DocumentClassifier()
        self.layout_detector = layout_detector or LayoutDetector()
        self.ocr_models = {
            "paddleocr": None,
            "trocr": None,
            "donut": None,
            "doctr": None,
        }

    def load_models(self):
        self.classifier.load_model()
        self.layout_detector.load_model()

    def classify_document(self, image_path: str, file_name: str, hint_text: str = "", ocr_text: str = "") -> Dict[str, object]:
        classification = self.classifier.classify(file_name, hint_text, ocr_text)
        if not self.classifier.is_confident(classification):
            classification["requires_clarification"] = True
        return classification

    def detect_layout(self, image_path: str) -> Dict[str, List[Dict[str, object]]]:
        return self.layout_detector.detect(image_path)

    def extract_fields(self, image_path: str, document_type: str, qr_payload: Optional[str] = None) -> Dict[str, Dict[str, object]]:
        # Placeholder: should run regional OCR and field extraction on crops.
        # For now this returns an empty field map with canonical field keys.
        result = {}
        for key in [
            "full_name", "dob", "gender", "address", "aadhaar_number", "pan_number",
            "issue_date", "expiry_date", "district", "state", "pin_code",
            "certificate_number", "issuing_authority", "income", "category",
            "disability_percent", "disability_type", "family_members", "document_number"
        ]:
            result[key] = {"value": "", "confidence": 0.0, "source": ""}
        return result

    def apply_qr_engine(self, ocr_fields: Dict[str, Dict[str, object]], image_path: str) -> Dict[str, Dict[str, object]]:
        qr_result = QREngine.decode_qr(image_path)
        if qr_result.get("qr_data"):
            merged = QREngine.trust_qr_over_ocr(ocr_fields, {"uid": qr_result["qr_data"][0]})
            return merged
        return ocr_fields

    def normalize_output(self, extracted_fields: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
        return normalize_fields(extracted_fields)

    def infer(self, image_path: str, file_name: str, hint_text: str = "", ocr_text: str = "") -> Dict[str, object]:
        classification = self.classify_document(image_path, file_name, hint_text, ocr_text)
        layout = self.detect_layout(image_path)
        extracted = self.extract_fields(image_path, classification.get("document_type", "unknown"))
        extracted = self.apply_qr_engine(extracted, image_path)
        extracted = self.normalize_output(extracted)
        return {
            "classification": classification,
            "layout": layout,
            "fields": extracted,
            "document_type": classification.get("document_type", "unknown"),
        }
