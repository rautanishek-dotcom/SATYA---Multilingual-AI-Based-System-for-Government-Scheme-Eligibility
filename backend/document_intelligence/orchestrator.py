import os
from typing import Dict, List

from vault.quality_detector import QualityDetector
from vault.ocr_utils import decode_qr_and_barcode, extract_structured_document_fields, multi_ocr_candidates, ocr_document, quick_document_hint
from vault.utils import VaultUtils

from .classification import DocumentClassifier
from .correction import normalize_fields
from .field_mapping import map_to_canonical_fields, required_fields_for_document
from .qr import QREngine
from .config import SUPPORTED_DOCUMENT_TYPES


def _map_force_engine(force_engine: str) -> Dict[str, object]:
    mapping = {
        "aadhaar_ekyc": "aadhaar_ekyc",
        "aadhaar_ocr": "aadhaar_ocr",
        "income_verifier": "income_certificate",
        "caste_verifier": "caste_certificate",
        "ration_verifier": "ration_card",
        "disability_verifier": "disability_certificate",
        "passport": "passport",
        "pan": "pan",
        "driving_license": "driving_license",
    }
    forced_type = mapping.get(force_engine)
    if not forced_type:
        return {}
    return {
        "document_type": forced_type,
        "document_label": SUPPORTED_DOCUMENT_TYPES.get(forced_type, {}).get("label", forced_type),
        "confidence": 100.0,
        "verification_engine": force_engine,
        "requires_share_code": forced_type == "aadhaar_ekyc",
        "supported": True,
        "reason": "Forced by request",
    }


class DocumentIntelligenceOrchestrator:
    def __init__(self):
        self.classifier = DocumentClassifier()

    def _collect_ocr_text(self, file_path: str):
        hint_text = quick_document_hint(file_path)
        ocr_result = ocr_document(file_path, lang_hints=["eng", "en"])
        candidates = [
            {
                "engine": item.engine,
                "lang": item.lang,
                "text": item.text,
                "confidence": item.confidence,
            }
            for item in (ocr_result.get("candidates") or [])
        ]
        best = ocr_result.get("best")
        raw_text = best.text if best else ""
        combined = " ".join(part for part in [hint_text, raw_text] if part).strip()
        return combined or raw_text, candidates, hint_text

    def infer(self, user_id: str, file_path: str, original_filename: str, share_code: str = None, force_engine: str = None):
        if not os.path.exists(file_path):
            return {"status": "FAILED", "error": "File not found"}

        quality_result = QualityDetector.analyze(file_path)
        qr_result = decode_qr_and_barcode(file_path)
        qr_payload = " ".join(qr_result.get("qr_data", []) + qr_result.get("barcode_data", []))
        preflight_hint = quick_document_hint(file_path)
        hint_blob = " ".join(part for part in [preflight_hint, qr_payload] if part)

        classification = self.classifier.classify(file_path, hint_text=hint_blob)
        if force_engine:
            forced = _map_force_engine(force_engine)
            if forced:
                classification = forced

        raw_text, ocr_candidates, hint_text = self._collect_ocr_text(file_path)
        document_type = classification.get("document_type", "government_certificate")

        extracted = extract_structured_document_fields(
            file_path,
            document_type=document_type,
            user_name=None,
            share_code=share_code,
            hint_text=hint_text,
            qr_payload=qr_payload,
        )

        fields = map_to_canonical_fields(extracted.get("fields", {}))
        if qr_result.get("qr_data"):
            qr_payload_text = qr_result["qr_data"][0]
            qr_fields = QREngine.parse_aadhaar_qr(qr_payload_text)
            if qr_fields:
                fields = QREngine.trust_qr_over_ocr(fields, qr_fields)

        normalized_fields = normalize_fields(fields)
        required_fields = required_fields_for_document(document_type)
        missing_fields = [name for name in required_fields if not str(normalized_fields.get(name, {}).get("value", "")).strip()]

        return {
            "status": "EXTRACTED",
            "message": "Document extraction completed",
            "document_type": document_type,
            "document_label": classification.get("document_label"),
            "classification": classification,
            "quality": quality_result,
            "fields": normalized_fields,
            "missing_fields": missing_fields,
            "validation": {
                "required_fields": required_fields,
                "document_type": document_type,
            },
            "qr": qr_result,
            "ocr_candidates": ocr_candidates,
        }
