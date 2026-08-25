import datetime
import logging
import os
import re
import tempfile
import uuid
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VaultUtils:
    @staticmethod
    def now():
        return datetime.datetime.utcnow()

    @staticmethod
    def now_iso():
        return VaultUtils.now().isoformat()

    @staticmethod
    def clean_extracted_text(text):
        if not text:
            return ""
        cleaned = re.sub(r"[^\w\s/,\-:.()&]", "", str(text), flags=re.UNICODE).strip()
        return re.sub(r"\s+", " ", cleaned)

    @staticmethod
    def normalize_text(text):
        if not text:
            return ""
        text = VaultUtils.clean_extracted_text(text)
        return re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE).strip().lower()

    @staticmethod
    def canonicalize_name(name):
        if not name:
            return ""
        text = VaultUtils.clean_extracted_text(name)
        text = re.sub(r"\b(mr|mrs|ms|shri|sri|kumari|dr|shrimati|smt|miss|md|m/s)\.?\b", "", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""
        if re.search(r"[^\x00-\x7F]", text):
            return text
        return text.title()

    @staticmethod
    def normalize_gender(gender):
        if not gender:
            return ""
        gender_l = str(gender).strip().lower()
        if gender_l.startswith("m") or gender_l in {"male", "पुरुष", "પુરુષ", "ஆண்", "ஆண", "పురుషుడు", "പുരുഷൻ", "ਮਰਦ"}:
            return "Male"
        if gender_l.startswith("f") or gender_l in {"female", "महिला", "સ્ત્રી", "பெண்", "స్త్రీ", "സ്ത്രീ", "ਔਰਤ"}:
            return "Female"
        if gender_l.startswith("t") or gender_l in {"transgender", "trangender", "तीसरा लिंग", "ತೃತೀಯ ಲಿಂಗ"}:
            return "Transgender"
        return str(gender).strip().title()

    @staticmethod
    def normalize_date(date_str):
        if not date_str:
            return ""
        date_str = str(date_str).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return date_str
        match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", date_str)
        if match:
            d, m, y = match.groups()
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        match = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", date_str)
        if match:
            y, m, d = match.groups()
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        year_match = re.search(r"(\d{4})", date_str)
        if year_match:
            return year_match.group(1)
        return date_str

    @staticmethod
    def mask_aadhaar(value):
        if not value:
            return "XXXX-XXXX-XXXX"
        digits = re.sub(r"\D", "", str(value))
        if len(digits) >= 4:
            return f"XXXX-XXXX-{digits[-4:]}"
        return "XXXX-XXXX-XXXX"

    @staticmethod
    def mask_number(value, visible=4):
        if not value:
            return ""
        raw = re.sub(r"\s+", "", str(value))
        if len(raw) <= visible:
            return raw
        return f"{'X' * max(0, len(raw) - visible)}{raw[-visible:]}"

    @staticmethod
    def validate_file(file_storage):
        """Validate an uploaded file using the same rules as the vault manager.

        Returns the normalized tuple produced by ``DocumentManager._validate_upload``.
        The method is intentionally lazy-imported to avoid a heavy import cycle at
        module load time.
        """
        from vault.document_manager import DocumentManager

        return DocumentManager()._validate_upload(file_storage)

    @staticmethod
    def field(value, confidence=0.0):
        return {"value": value if value is not None else "", "confidence": round(float(confidence), 1)}

    @staticmethod
    def similarity(a, b):
        a_norm = VaultUtils.normalize_text(a)
        b_norm = VaultUtils.normalize_text(b)
        if not a_norm and not b_norm:
            return 100.0
        if not a_norm or not b_norm:
            return 0.0
        ratio = SequenceMatcher(None, a_norm, b_norm).ratio()
        return round(ratio * 100, 2)

    @staticmethod
    def calculate_health_score(confidence, quality_score=None):
        confidence = float(confidence or 0)
        quality_score = float(quality_score if quality_score is not None else confidence)
        blended = (confidence * 0.7) + (quality_score * 0.3)
        if blended >= 90:
            return "Excellent"
        if blended >= 75:
            return "Good"
        if blended >= 55:
            return "Average"
        return "Poor"

    @staticmethod
    def document_summary(document_type, fields, quality, fraud, identity_score):
        missing = [k for k, v in fields.items() if isinstance(v, dict) and not str(v.get("value", "")).strip()]
        return {
            "documentType": document_type,
            "qualityScore": quality.get("quality_score", 0),
            "fraudProbability": fraud.get("fraud_probability", 0),
            "identityMatchScore": identity_score,
            "missingFields": missing,
            "risk": "high" if fraud.get("fraud_probability", 0) >= 70 else "medium" if fraud.get("fraud_probability", 0) >= 40 else "low",
        }

    @staticmethod
    def to_serializable(value: Any):
        if isinstance(value, dict):
            return {k: VaultUtils.to_serializable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [VaultUtils.to_serializable(v) for v in value]
        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.isoformat()
        return value
