"""Reusable OCR and vision utilities for the SATYA vault."""

from __future__ import annotations

import os
import re
import time
import traceback
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging

import cv2
import numpy as np

from vault.utils import VaultUtils

logger = logging.getLogger(__name__)

try:
    import pytesseract
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

try:
    from pyzbar.pyzbar import decode as decode_barcodes
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

try:
    import easyocr  # type: ignore
    EASYOCR_AVAILABLE = True
except Exception:
    EASYOCR_AVAILABLE = False

try:
    import paddleocr  # type: ignore
    from paddleocr import PaddleOCR  # type: ignore
    PADDLEOCR_AVAILABLE = True
except Exception:
    PADDLEOCR_AVAILABLE = False

try:
    from PyPDF2 import PdfReader  # type: ignore
    PYPDF2_AVAILABLE = True
except Exception:
    PYPDF2_AVAILABLE = False


@dataclass
class OCRCandidate:
    engine: str
    lang: str
    text: str
    confidence: float


@dataclass
class OCRField:
    value: str
    confidence: float
    source: str = ""


SCRIPT_LANGUAGE_HINTS = OrderedDict([
    (r"[\u0900-\u097F]", "hin"),  # Devanagari
    (r"[\u0980-\u09FF]", "ben"),  # Bengali
    (r"[\u0A00-\u0A7F]", "pan"),  # Gurmukhi
    (r"[\u0A80-\u0AFF]", "guj"),  # Gujarati
    (r"[\u0B00-\u0B7F]", "ori"),  # Odia
    (r"[\u0B80-\u0BFF]", "tam"),  # Tamil
    (r"[\u0C00-\u0C7F]", "tel"),  # Telugu
    (r"[\u0C80-\u0CFF]", "kan"),  # Kannada
    (r"[\u0D00-\u0D7F]", "mal"),  # Malayalam
])

TESSERACT_LANG_ALIASES = {
    "hin": "hin",
    "mar": "mar",
    "guj": "guj",
    "ben": "ben",
    "tam": "tam",
    "tel": "tel",
    "kan": "kan",
    "mal": "mal",
    "pan": "pan",
    "ori": "ori",
    "eng": "eng",
    "en": "eng",
}

EASYOCR_LANG_ALIASES = {
    "hin": "hi",
    "mar": "mr",
    "guj": "gu",
    "ben": "bn",
    "tam": "ta",
    "tel": "te",
    "kan": "kn",
    "mal": "ml",
    "pan": "pa",
    "ori": "or",
    "eng": "en",
    "en": "en",
}


def _unique(items):
    seen = set()
    ordered = []
    for item in items or []:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _detect_script_languages(text):
    raw = str(text or "")
    languages = []
    for pattern, code in SCRIPT_LANGUAGE_HINTS.items():
        if re.search(pattern, raw):
            languages.append(code)
    text_l = raw.lower()
    if any(keyword in text_l for keyword in [
        "aadhaar", "aadhar", "government", "india", "ministry", "unique identification",
        "date of birth", "dob", "gender", "address", "passport", "pan", "driving licence",
        "driving license", "voter id", "income certificate", "caste certificate",
        "domicile certificate", "birth certificate",
    ]):
        languages.insert(0, "eng")
    if "eng" not in languages:
        languages.insert(0, "eng")
    return _unique(languages)


def _build_tesseract_lang_string(langs):
    mapped = []
    for lang in langs or []:
        mapped.append(TESSERACT_LANG_ALIASES.get(lang, lang))
    mapped = _unique(mapped)
    return "+".join(mapped) if mapped else "eng"


def _build_easyocr_langs(langs):
    mapped = []
    for lang in langs or []:
        mapped.append(EASYOCR_LANG_ALIASES.get(lang, "en"))
    mapped = _unique(mapped)
    return mapped or ["en"]


def _postprocess_ocr_text(text):
    text = _normalize_text(text)
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _field_value_confidence(value, base=80.0):
    if not value:
        return 0.0
    length_bonus = min(len(str(value).strip()) / 20.0, 12.0)
    return round(min(99.0, base + length_bonus), 1)


def _crop_plan(image, ratios):
    crops = OrderedDict()
    for name, (left, top, right, bottom) in ratios.items():
        crops[name] = _crop_region(image, left, top, right, bottom)
    return crops


def _aadhaar_regions(image):
    h, w = image.shape[:2]
    regions = OrderedDict()
    regions["full_top"] = _crop_region(image, 0.0, 0.0, 1.0, 0.34)
    regions["header"] = _crop_region(image, 0.0, 0.0, 1.0, 0.18)
    regions["identity_block"] = _crop_region(image, 0.0, 0.12, 0.72, 0.72)
    regions["number_block"] = _crop_region(image, 0.0, 0.52, 1.0, 0.92)
    regions["address_block"] = _crop_region(image, 0.02, 0.32, 0.98, 0.98)
    regions["qr_block"] = _crop_region(image, 0.68, 0.42, 1.0, 1.0)
    regions["photo_block"] = _crop_region(image, 0.68, 0.12, 0.98, 0.42)
    return regions


def _generic_regions(image):
    return OrderedDict([
        ("header", _crop_region(image, 0.0, 0.0, 1.0, 0.20)),
        ("photo_block", _crop_region(image, 0.0, 0.12, 0.36, 0.58)),
        ("identity_block", _crop_region(image, 0.32, 0.12, 1.0, 0.58)),
        ("number_block", _crop_region(image, 0.0, 0.35, 1.0, 0.72)),
        ("address_block", _crop_region(image, 0.0, 0.55, 1.0, 0.95)),
        ("footer", _crop_region(image, 0.0, 0.82, 1.0, 1.0)),
        ("qr_block", _crop_region(image, 0.66, 0.36, 1.0, 1.0)),
    ])


def _ensure_gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image


def _resize_for_ocr(gray):
    h, w = gray.shape[:2]
    if w < 1400:
        scale = 1400 / max(w, 1)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return gray


def _deskew(image):
    gray = _ensure_gray(image)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
      return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _autorange(gray):
    return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)


def _clahe(gray):
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _remove_shadow(gray):
    dilated = cv2.dilate(gray, np.ones((7, 7), np.uint8))
    bg = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(gray, bg)
    return cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)


def _sharpen(gray):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return cv2.filter2D(gray, -1, kernel)


def _adaptive_threshold(gray):
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)


def _otsu_threshold(gray):
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _noise_reduction(gray):
    return cv2.fastNlMeansDenoising(gray, h=18)


def _enhance_image(image):
    image = _deskew(image)
    gray = _ensure_gray(image)
    gray = _resize_for_ocr(gray)
    gray = _autorange(gray)
    gray = _remove_shadow(gray)
    gray = _clahe(gray)
    gray = _noise_reduction(gray)
    sharp = _sharpen(gray)
    binary_a = _adaptive_threshold(sharp)
    binary_b = _otsu_threshold(sharp)
    return [gray, sharp, binary_a, binary_b]


def _enhance_image_strong(image):
    variants = _enhance_image(image)
    gray = variants[0]
    try:
        upscaled = cv2.resize(gray, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
    except Exception:
        upscaled = gray
    try:
        denoised = cv2.bilateralFilter(upscaled, 9, 75, 75)
    except Exception:
        denoised = upscaled
    try:
        edge_boost = cv2.addWeighted(denoised, 1.25, cv2.GaussianBlur(denoised, (0, 0), 2.0), -0.25, 0)
    except Exception:
        edge_boost = denoised
    return variants + [upscaled, denoised, edge_boost]


def _load_image(file_path):
    if not file_path or not os.path.exists(file_path):
        return None
    image = cv2.imread(file_path)
    if image is None:
        return None
    return image


def _crop_region(image, left=0.0, top=0.0, right=1.0, bottom=1.0):
    if image is None:
        return None
    h, w = image.shape[:2]
    x1 = max(0, min(w, int(w * left)))
    y1 = max(0, min(h, int(h * top)))
    x2 = max(0, min(w, int(w * right)))
    y2 = max(0, min(h, int(h * bottom)))
    if x2 <= x1 or y2 <= y1:
        return None
    return image[y1:y2, x1:x2]


def _ocr_candidates_from_image(image, lang_hints=None):
    if image is None:
        return []
    lang_hints = _unique(lang_hints or ["eng"])
    tesseract_lang = _build_tesseract_lang_string(lang_hints)
    easyocr_langs = _build_easyocr_langs(lang_hints)
    candidates: List[OCRCandidate] = []
    candidates.extend(_ocr_paddleocr(image, lang="en"))
    candidates.extend(_ocr_easyocr(image, lang=easyocr_langs))
    candidates.extend(_ocr_tesseract(image, lang=tesseract_lang))
    if not candidates and "eng" not in lang_hints:
        candidates.extend(_ocr_paddleocr(image, lang="en"))
        candidates.extend(_ocr_easyocr(image, lang=["en"]))
        candidates.extend(_ocr_tesseract(image, lang="eng"))
    candidates.sort(key=lambda item: item.confidence, reverse=True)
    return candidates


def _best_candidate_from_image(image, lang_hints=None):
    candidates = _ocr_candidates_from_image(image, lang_hints=lang_hints)
    if not candidates:
        return OCRCandidate("none", "none", "", 0.0), []
    return candidates[0], candidates


def _fallback_text_from_image(image):
    if image is None:
        return "", 0.0
    if TESSERACT_AVAILABLE:
        try:
            for processed in [image] + _enhance_image(image)[:2]:
                text = pytesseract.image_to_string(processed, lang="eng", config=r"--oem 1 --psm 6")
                text = _normalize_text(text)
                if text:
                    return text, _score_text(text, 62.0)
        except Exception:
            pass
    try:
        best, _ = _best_candidate_from_image(image, lang_hints=["eng"])
        return best.text, best.confidence
    except Exception:
        return "", 0.0


def _quick_image_hint(image):
    if image is None:
        return ""
    h, w = image.shape[:2]
    top = _crop_region(image, 0.0, 0.0, 1.0, 0.28)
    mid = _crop_region(image, 0.0, 0.28, 1.0, 0.68)
    bottom = _crop_region(image, 0.0, 0.68, 1.0, 1.0)
    hint_parts = []
    for region in [top, mid, bottom]:
        if region is None:
            continue
        text, _ = _fallback_text_from_image(region)
        if text:
            hint_parts.append(text[:800])
    return _normalize_text(" ".join(hint_parts))


def quick_document_hint(file_path):
    image = _load_image(file_path)
    if image is None:
        return ""
    return _quick_image_hint(image)


def _parse_aadhaar_qr_payload(qr_text):
    payload = _normalize_text(qr_text)
    if not payload:
        return {}
    parsed = {}
    patterns = {
        "name": [r"(?:name|nm)\s*[:=]\s*([^,;|]+)"],
        "dob": [r"(?:dob|yob|date of birth)\s*[:=]\s*([^,;|]+)"],
        "gender": [r"(?:gender|sex)\s*[:=]\s*([^,;|]+)"],
        "aadhaar_number": [r"(?:uid|aadhaar|aadhaar number|aadhar number)\s*[:=]\s*([0-9xX\-\s]{8,20})"],
    }
    for key, regexes in patterns.items():
        for pattern in regexes:
            match = re.search(pattern, payload, re.IGNORECASE)
            if match:
                parsed[key] = _normalize_text(match.group(1))
                break
    digits = re.sub(r"\D", "", payload)
    if "aadhaar_number" not in parsed and len(digits) >= 12:
        parsed["aadhaar_number"] = digits[-12:]
    return parsed


def _tesseract_data(image, lang="eng"):
    if not TESSERACT_AVAILABLE or image is None:
        return []
    try:
        config = r"--oem 1 --psm 6"
        data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=pytesseract.Output.DICT)
        words = []
        n = len(data.get("text", []))
        for i in range(n):
            text = _normalize_text(data["text"][i])
            if not text:
                continue
            conf_raw = data.get("conf", [])[i]
            try:
                confidence = float(conf_raw)
            except Exception:
                confidence = 0.0
            if confidence < 0:
                continue
            words.append({
                "text": text,
                "confidence": confidence,
                "left": int(data["left"][i]),
                "top": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
            })
        return words
    except Exception:
        return []


def _ocr_region_text(image, lang_hints=None):
    best, candidates = _best_candidate_from_image(image, lang_hints=lang_hints)
    return best, candidates


def _aadhaar_regions(image):
    regions = OrderedDict()
    regions["full_top"] = _crop_region(image, 0.0, 0.0, 1.0, 0.34)
    regions["header"] = _crop_region(image, 0.0, 0.0, 1.0, 0.18)
    regions["identity_block"] = _crop_region(image, 0.0, 0.12, 0.72, 0.72)
    regions["number_block"] = _crop_region(image, 0.0, 0.52, 1.0, 0.92)
    regions["address_block"] = _crop_region(image, 0.02, 0.32, 0.98, 0.98)
    regions["qr_block"] = _crop_region(image, 0.68, 0.42, 1.0, 1.0)
    regions["photo_block"] = _crop_region(image, 0.68, 0.12, 0.98, 0.42)
    return regions


def _is_aadhaar_hint(text):
    text_l = _normalize_text(text).lower()
    keywords = ["aadhaar", "aadhar", "uidai", "unique identification", "government of india", "dob", "gender", "year of birth"]
    return any(keyword in text_l for keyword in keywords)


def _field(value="", confidence=0.0, source=""):
    return {"value": value if value is not None else "", "confidence": round(float(confidence), 1), "source": source}


def _sanitize_ocr_token(text: str) -> str:
    return _normalize_text(text).strip(":-,;|")


def _first_regex_match(patterns, text, flags=re.IGNORECASE):
    for pattern in patterns:
        match = re.search(pattern, text or "", flags)
        if match:
            return match
    return None


def _merge_field(current: Dict, value: str, confidence: float, source: str):
    value = _sanitize_ocr_token(value)
    if not value:
        return current
    if not current or confidence >= float(current.get("confidence", 0.0)):
        return _field(value, confidence, source)
    return current


def _extract_name_from_text_block(text, user_name=None):
    text = _normalize_text(text)
    lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
    patterns = [
        r"\bname\b\s*[:\-]\s*([^\n\r,;|]+)",
        r"\bholder name\b\s*[:\-]\s*([^\n\r,;|]+)",
        r"\bresident name\b\s*[:\-]\s*([^\n\r,;|]+)",
    ]
    match = _first_regex_match(patterns, text)
    if match:
        return _field(VaultUtils.canonicalize_name(match.group(1)), 97.0, "label")

    for line in lines:
        line_l = line.lower()
        if any(keyword in line_l for keyword in ["uidai", "government", "india", "aadhaar", "address", "dob", "gender", "qr", "pincode", "certificate", "passport", "license"]):
            continue
        if re.fullmatch(r"[^\W\d_][\w\s\.\'\-]{2,}", line, flags=re.UNICODE):
            candidate = VaultUtils.canonicalize_name(line)
            if candidate:
                return _field(candidate, 88.0, "line")

    if user_name:
        return _field(VaultUtils.canonicalize_name(user_name), 70.0, "profile")
    return _field()


def _extract_dob_from_text_block(text):
    text = _normalize_text(text)
    patterns = [
        r"\b(?:dob|date of birth|year of birth|yob)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
        r"\b(?:dob|date of birth|year of birth|yob)\s*[:\-]?\s*(\d{4}[/-]\d{2}[/-]\d{2})",
        r"\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b",
        r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b",
        r"\b(\d{4}[/-]\d{2}[/-]\d{2})\b",
    ]
    match = _first_regex_match(patterns, text)
    if match:
        return _field(VaultUtils.normalize_date(match.group(1)), 96.0, "pattern")
    return _field()


def _extract_gender_from_text_block(text):
    text_l = _normalize_text(text).lower()
    if "female" in text_l or "महिला" in text_l or "സ്ത്രീ" in text_l or "பெண்" in text_l or "స్త్రీ" in text_l or "ਔਰਤ" in text_l:
        return _field("Female", 96.0, "keyword")
    if "male" in text_l or "पुरुष" in text_l or "ਮਰਦ" in text_l or "ஆண்" in text_l or "పురుషుడు" in text_l or "പുരുഷൻ" in text_l:
        return _field("Male", 96.0, "keyword")
    if "transgender" in text_l or "third gender" in text_l:
        return _field("Transgender", 96.0, "keyword")
    return _field()


def _extract_aadhaar_number(text):
    text = _normalize_text(text)
    patterns = [
        r"\b(?:aadhaar|aadhar|uid|uidai)\s*(?:number|no|id)?\s*[:\-]?\s*([0-9]{4}\s*[0-9]{4}\s*[0-9]{4})\b",
        r"\b([0-9]{4}\s*[0-9]{4}\s*[0-9]{4})\b",
        r"\b([0-9]{12})\b",
    ]
    match = _first_regex_match(patterns, text)
    if match:
        digits = re.sub(r"\D", "", match.group(1))
        if len(digits) == 12:
            return _field(VaultUtils.mask_aadhaar(digits), 97.0, "pattern")
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 12:
        return _field(VaultUtils.mask_aadhaar(digits[-12:]), 88.0, "digits")
    return _field()


def _extract_address_from_text_block(text):
    text = _normalize_text(text)
    if not text:
        return _field()
    address_patterns = [
        r"\b(?:address|addr|residence|resident)\s*[:\-]?\s*(.+)",
        r"\b(?:c/o|s/o|d/o|w/o|care of)\s+(.+)",
    ]
    match = _first_regex_match(address_patterns, text)
    if match:
        return _field(VaultUtils.clean_extracted_text(match.group(1)), 93.0, "label")
    line_tokens = []
    for line in re.split(r"[\r\n]+", text):
        clean = VaultUtils.clean_extracted_text(line)
        clean_l = clean.lower()
        if not clean or len(clean) < 6:
            continue
        if any(keyword in clean_l for keyword in [
            "house", "street", "village", "taluk", "tehsil", "district", "state", "pin", "pincode", "road",
            "sector", "ward", "colony", "nagar", "mohalla", "post", "police station", "dist", "vtc", "loc", "po", "ps"
        ]) or re.search(r"\b\d{6}\b", clean):
            line_tokens.append(clean)
    if line_tokens:
        return _field(", ".join(line_tokens[:5]), 86.0, "lines")
    return _field()


def _extract_signature_hint(text):
    text_l = _normalize_text(text).lower()
    if any(token in text_l for token in ["digitally signed", "digital signature", "signed by", "signature verified"]):
        return _field("Present", 80.0, "text")
    return _field()


def _extract_number(text, document_type):
    text = _normalize_text(text)
    if not text:
        return ""
    if document_type == "pan":
        match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    if document_type == "passport":
        match = re.search(r"\b([A-Z]{1}[0-9]{7})\b", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    if document_type == "driving_license":
        match = re.search(r"\b([A-Z]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{4}[-\s]?[0-9]{7})\b", text, re.IGNORECASE)
        if match:
            return re.sub(r"[-\s]", "", match.group(1)).upper()
    if document_type == "voter_id":
        match = re.search(r"\b([A-Z]{3}[0-9]{7})\b", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    match = re.search(r"(?:certificate\s+no|cert\s+no|registration\s+no|id\s+no)\s*[:\-]?\s*([a-zA-Z0-9\-/]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ""


def _extract_certificate_specific(text, document_type):
    text = _normalize_text(text)
    fields = {}
    authority_match = re.search(r"(?:issued by|issuing authority|office of the)\s*[:\-]?\s*([^,\n]+)", text, re.IGNORECASE)
    if authority_match:
        fields["issuing_authority"] = authority_match.group(1).strip()
    if document_type == "income_certificate":
        income_match = re.search(r"(?:income of\s*(?:rs|inr|rupees)?|annual income\s*(?:is)?\s*(?:rs|inr|rupees)?)\s*[:\-\.]?\s*(\d+(?:,\d+)*(?:\.\d+)?)\b", text, re.IGNORECASE)
        if income_match:
            fields["income"] = income_match.group(1)
    if document_type == "caste_certificate":
        caste_match = re.search(r"(?:caste|community)\s*[:\-]?\s*([a-zA-Z\s]+?)\s*(?:category|religion|recognized)", text, re.IGNORECASE)
        if caste_match:
            fields["caste"] = caste_match.group(1).strip()
        category_match = re.search(r"(?:category|class)\s*[:\-]?\s*(sc|st|obc|sebc|ebc|general|nt|sbc)\b", text, re.IGNORECASE)
        if category_match:
            fields["category"] = category_match.group(1).upper()
    if document_type == "disability_certificate":
        dis_type_match = re.search(r"(?:disability type|type of disability)\s*[:\-]?\s*([^,\n]+)", text, re.IGNORECASE)
        if dis_type_match:
            fields["disability_type"] = dis_type_match.group(1).strip()
        percent_match = re.search(r"(?:percentage|extent of disability)\s*[:\-]?\s*(\d+)\s*%", text, re.IGNORECASE)
        if percent_match:
            fields["disability_percent"] = percent_match.group(1)
    return fields


def _extract_parents(text):
    text = _normalize_text(text)
    parents = []
    father_match = re.search(r"(?:father\'?s? name|son of|d/o|s/o|w/o)\s*[:\-]?\s*([A-Za-z\s]+)(?:mother|dob|address|$)", text, re.IGNORECASE)
    if father_match:
        parents.append(father_match.group(1).strip())
    mother_match = re.search(r"(?:mother\'?s? name)\s*[:\-]?\s*([A-Za-z\s]+)(?:father|dob|address|$)", text, re.IGNORECASE)
    if mother_match:
        parents.append(mother_match.group(1).strip())
    return " and ".join(parents) if parents else ""


def _refine_field(field_name, field, source_hint=""):
    if not isinstance(field, dict):
        field = _field(field, 0.0, source_hint)
    value = str(field.get("value", "") or "").strip()
    confidence = float(field.get("confidence", 0.0) or 0.0)
    source = field.get("source", source_hint)
    if not value:
        return _field("", 0.0, source)

    if field_name in {"name", "bride", "groom", "parents"}:
        value = VaultUtils.canonicalize_name(value)
        confidence = max(confidence, _field_value_confidence(value, 86.0))
    elif field_name in {"dob", "marriage_date"}:
        value = VaultUtils.normalize_date(value)
        confidence = max(confidence, _field_value_confidence(value, 88.0))
    elif field_name in {"gender"}:
        value = VaultUtils.normalize_gender(value)
        confidence = max(confidence, _field_value_confidence(value, 90.0))
    elif field_name in {"masked_aadhaar", "aadhaar_reference_id", "identity_number", "certificate_number", "pin_code"}:
        corrected = re.sub(r"[OQ]", "0", value, flags=re.IGNORECASE)
        corrected = re.sub(r"[Il|]", "1", corrected)
        corrected = re.sub(r"[S]", "5", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"[B]", "8", corrected, flags=re.IGNORECASE)
        digits = re.sub(r"\D", "", corrected)
        if field_name == "masked_aadhaar" and len(digits) >= 12:
            value = VaultUtils.mask_aadhaar(digits[-12:])
        elif field_name == "pin_code" and len(digits) >= 6:
            value = digits[-6:]
        elif field_name == "aadhaar_reference_id":
            value = corrected.upper()
        elif digits:
            value = digits if field_name != "masked_aadhaar" else VaultUtils.mask_aadhaar(digits[-12:])
        else:
            value = corrected.upper()
        confidence = max(confidence, _field_value_confidence(value, 88.0))
    elif field_name in {"address", "issuing_authority", "caste", "category", "disability_type", "document_type"}:
        value = VaultUtils.clean_extracted_text(value)
        confidence = max(confidence, _field_value_confidence(value, 84.0))
    else:
        value = VaultUtils.clean_extracted_text(value)

    return _field(value, confidence, source or source_hint)


def _extract_aadhaar_structured_fields(image, user_name=None, qr_payload=None, hint_text=""):
    strong_variants = _enhance_image_strong(image)
    best_text = ""
    best_confidence = 0.0
    region_texts = {}
    region_candidates = {}
    last_variant = None
    language_hints = _detect_script_languages(" ".join(part for part in [hint_text, qr_payload] if part))

    for variant in strong_variants:
        best_candidate, candidates = _ocr_region_text(variant, lang_hints=language_hints)
        if best_candidate.text and best_candidate.confidence >= best_confidence:
            best_text = best_candidate.text
            best_confidence = best_candidate.confidence
            last_variant = variant
        if best_confidence >= 92.0:
            break

    if last_variant is None:
        last_variant = image

    for name, region in _aadhaar_regions(last_variant).items():
        if region is None:
            continue
        best_candidate, candidates = _ocr_region_text(region, lang_hints=language_hints)
        region_texts[name] = best_candidate.text if best_candidate else ""
        region_candidates[name] = [
            {"engine": c.engine, "lang": c.lang, "text": c.text, "confidence": c.confidence}
            for c in candidates[:4]
        ]

    combined_text = " ".join(
        part for part in [
            hint_text,
            best_text,
            region_texts.get("header", ""),
            region_texts.get("full_top", ""),
            region_texts.get("identity_block", ""),
            region_texts.get("number_block", ""),
            region_texts.get("address_block", ""),
        ] if part
    )
    qr_text = _normalize_text(qr_payload or "")
    qr_fields = _parse_aadhaar_qr_payload(qr_text)

    fields = OrderedDict()
    fields["document_language"] = _field(language_hints[0] if language_hints else "eng", 70.0, "language")
    fields["name"] = _refine_field("name", _extract_name_from_text_block(" ".join([qr_text, region_texts.get("header", ""), region_texts.get("full_top", ""), combined_text]), user_name=user_name), "aadhaar")
    fields["dob"] = _refine_field("dob", _extract_dob_from_text_block(" ".join([qr_text, region_texts.get("identity_block", ""), combined_text])), "aadhaar")
    fields["gender"] = _refine_field("gender", _extract_gender_from_text_block(" ".join([qr_text, region_texts.get("identity_block", ""), combined_text])), "aadhaar")
    fields["masked_aadhaar"] = _refine_field("masked_aadhaar", _extract_aadhaar_number(" ".join([qr_text, region_texts.get("number_block", ""), combined_text])), "aadhaar")
    fields["aadhaar_reference_id"] = _refine_field("aadhaar_reference_id", _field(qr_fields.get("reference_id", ""), 95.0, "qr") if qr_fields.get("reference_id") else _field(), "qr")
    fields["address"] = _refine_field("address", _extract_address_from_text_block(" ".join([qr_text, region_texts.get("address_block", ""), combined_text])), "aadhaar")
    fields["district"] = _field("", 0.0, "")
    fields["state"] = _field("", 0.0, "")
    fields["pin_code"] = _field("", 0.0, "")
    fields["verification_id"] = _field("", 0.0, "")

    if qr_fields.get("name"):
        fields["name"] = _merge_field(fields["name"], VaultUtils.canonicalize_name(qr_fields["name"]), 99.0, "qr")
    if qr_fields.get("dob"):
        fields["dob"] = _merge_field(fields["dob"], VaultUtils.normalize_date(qr_fields["dob"]), 99.0, "qr")
    if qr_fields.get("gender"):
        fields["gender"] = _merge_field(fields["gender"], VaultUtils.normalize_gender(qr_fields["gender"]), 99.0, "qr")
    if qr_fields.get("aadhaar_number"):
        fields["masked_aadhaar"] = _field(VaultUtils.mask_aadhaar(qr_fields["aadhaar_number"]), 99.0, "qr")

    address_value = fields["address"]["value"]
    if address_value:
        pin_match = re.search(r"\b(\d{6})\b", address_value)
        if pin_match:
            fields["pin_code"] = _field(pin_match.group(1), 92.0, "address")
        state_match = re.search(r"\b([A-Z][A-Za-z ]{2,})\b", address_value)
        if state_match:
            fields["state"] = _field(VaultUtils.clean_extracted_text(state_match.group(1)), 70.0, "address")

    if fields["masked_aadhaar"]["value"] and not fields["verification_id"]["value"]:
        fields["verification_id"] = _field(fields["masked_aadhaar"]["value"], fields["masked_aadhaar"]["confidence"], "aadhaar")

    for key in ["name", "dob", "gender", "masked_aadhaar", "aadhaar_reference_id", "address", "pin_code", "state", "district", "verification_id"]:
        fields[key] = _refine_field(key, fields.get(key, _field()), fields[key].get("source", "aadhaar") if isinstance(fields.get(key), dict) else "aadhaar")

    signature_hint = _extract_signature_hint(" ".join([qr_text, combined_text]))
    fields["digital_signature"] = signature_hint
    fields["seal"] = _field("", 0.0, "")
    fields["stamp"] = _field("", 0.0, "")
    fields["watermark"] = _field("", 0.0, "")

    candidates = []
    for region_name, entries in region_candidates.items():
        for entry in entries:
            entry = dict(entry)
            entry["region"] = region_name
            candidates.append(entry)
    candidates.sort(key=lambda item: item.get("confidence", 0.0), reverse=True)
    return {
        "fields": fields,
        "raw_text": combined_text,
        "best_text": best_text,
        "best_confidence": best_confidence,
        "candidates": candidates,
        "document_side": "back" if "address" in region_texts.get("address_block", "").lower() or fields["address"]["value"] else "front",
    }


def _extract_aadhaar_xml_fields(file_path, share_code):
    extracted = OrderedDict()
    raw_xml = ""
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        if share_code is not None:
            zip_ref.setpassword(str(share_code).encode("utf-8"))
        xml_filename = [f for f in zip_ref.namelist() if f.lower().endswith(".xml")]
        if not xml_filename:
            raise ValueError("No XML found in ZIP")
        with zip_ref.open(xml_filename[0]) as xml_file:
            raw_xml = xml_file.read().decode("utf-8", errors="ignore")
    root = ET.fromstring(raw_xml)
    ns = {"uid": "http://www.uidai.gov.in/offlinePaperlessKYC/2.0"}
    poi = root.find(".//uid:Poi", ns)
    if poi is None:
        poi = root.find(".//Poi")
    poa = root.find(".//uid:Poa", ns)
    if poa is None:
        poa = root.find(".//Poa")
    if poi is None:
        raise ValueError("Unable to extract Aadhaar identity details")

    extracted["name"] = _field(VaultUtils.canonicalize_name(poi.get("name", "")), 98.0, "xml")
    extracted["dob"] = _field(VaultUtils.normalize_date(poi.get("dob", "")), 98.0, "xml")
    extracted["gender"] = _field(VaultUtils.normalize_gender(poi.get("gender", "")), 98.0, "xml")
    ref_id = root.get("referenceId", "") or root.get("uid", "")
    extracted["masked_aadhaar"] = _field(VaultUtils.mask_aadhaar(ref_id), 95.0, "xml")
    extracted["aadhaar_reference_id"] = _field(ref_id, 95.0, "xml") if ref_id else _field()
    address = ""
    if poa is not None:
        address = ", ".join(
            part for part in [
                poa.get("house", ""),
                poa.get("street", ""),
                poa.get("loc", ""),
                poa.get("vtc", ""),
                poa.get("dist", ""),
                poa.get("state", ""),
                poa.get("pc", ""),
            ] if part
        )
    extracted["address"] = _field(address, 92.0 if address else 0.0, "xml")
    extracted["digital_signature"] = _field("Present" if "signature" in raw_xml.lower() or "ds:" in raw_xml.lower() else "", 85.0 if raw_xml else 0.0, "xml")
    extracted["raw_xml"] = raw_xml
    return extracted


def extract_structured_document_fields(file_path, document_type=None, user_name=None, share_code=None, hint_text="", qr_payload=None):
    ext = os.path.splitext(file_path)[1].lower()
    image = _load_image(file_path)
    qr_payload = _normalize_text(qr_payload or "")

    if ext == ".zip" or document_type == "aadhaar_ekyc":
        return {
            "fields": _extract_aadhaar_xml_fields(file_path, share_code),
            "raw_text": "",
            "best_text": "",
            "best_confidence": 99.0,
            "candidates": [],
            "document_side": "xml",
        }

    if image is None:
        return {
            "fields": OrderedDict(),
            "raw_text": "",
            "best_text": "",
            "best_confidence": 0.0,
            "candidates": [],
            "document_side": "unknown",
        }

    hint_blob = " ".join(part for part in [hint_text, qr_payload] if part)
    if document_type == "aadhaar_ocr" or _is_aadhaar_hint(hint_blob):
        aadhaar_result = _extract_aadhaar_structured_fields(image, user_name=user_name, qr_payload=qr_payload, hint_text=hint_blob)
        aadhaar_result["fields"]["document_type"] = _field("Aadhaar Card", 99.0, "classifier")
        return aadhaar_result

    language_hints = _detect_script_languages(hint_blob)
    region_texts = {}
    region_candidates = {}
    best_candidate = OCRCandidate("none", "none", "", 0.0)
    best_score = 0.0

    for variant in _enhance_image_strong(image):
        variant_best, variant_candidates = _ocr_region_text(variant, lang_hints=language_hints)
        if variant_best.text and variant_best.confidence >= best_score:
            best_candidate = variant_best
            best_score = variant_best.confidence
        if best_score >= 90.0:
            break

    regions = _generic_regions(image)
    for region_name, region in regions.items():
        if region is None:
            continue
        region_best, region_cands = _ocr_region_text(region, lang_hints=language_hints)
        region_texts[region_name] = region_best.text if region_best else ""
        region_candidates[region_name] = [
            {"engine": c.engine, "lang": c.lang, "text": c.text, "confidence": c.confidence}
            for c in region_cands[:4]
        ]

    text = " ".join(part for part in [
        hint_blob,
        best_candidate.text if best_candidate else "",
        region_texts.get("header", ""),
        region_texts.get("identity_block", ""),
        region_texts.get("number_block", ""),
        region_texts.get("address_block", ""),
        region_texts.get("footer", ""),
    ] if part)
    fields = OrderedDict()
    fields["document_language"] = _field(language_hints[0] if language_hints else "eng", 70.0, "language")
    fields["name"] = _refine_field("name", _extract_name_from_text_block(" ".join([hint_blob, region_texts.get("header", ""), region_texts.get("identity_block", ""), text]), user_name=user_name), "document")
    fields["dob"] = _refine_field("dob", _extract_dob_from_text_block(" ".join([hint_blob, region_texts.get("identity_block", ""), text])), "document")
    fields["gender"] = _refine_field("gender", _extract_gender_from_text_block(" ".join([hint_blob, region_texts.get("identity_block", ""), text])), "document")
    fields["identity_number"] = _refine_field("identity_number", _extract_number(" ".join([hint_blob, text]), document_type or "government_certificate"), "document")
    fields["address"] = _refine_field("address", _extract_address_from_text_block(" ".join([hint_blob, region_texts.get("address_block", ""), text])), "document")
    fields["digital_signature"] = _extract_signature_hint(" ".join([hint_blob, text]))
    fields["raw_text"] = text

    if document_type in {"passport", "pan", "driving_license", "voter_id"}:
        fields["identity_number"] = _refine_field("identity_number", _extract_number(text, document_type), "document")
    if document_type in {"income_certificate", "caste_certificate", "birth_certificate", "domicile_certificate", "disability_certificate", "residence_certificate"}:
        fields.update(_extract_certificate_specific(text, document_type))
        for key, value in list(fields.items()):
            if isinstance(value, dict):
                fields[key] = _refine_field(key, value, "document")
    if document_type == "birth_certificate":
        fields["parents"] = _refine_field("parents", _extract_parents(text), "document")
    if document_type == "domicile_certificate":
        fields["certificate_number"] = _refine_field("certificate_number", _extract_number(text, "certificate_number"), "document")
    fields["seal"] = _field("", 0.0, "")
    fields["stamp"] = _field("", 0.0, "")
    fields["watermark"] = _field("", 0.0, "")
    candidates = []
    for region_name, entries in region_candidates.items():
        for entry in entries:
            entry = dict(entry)
            entry["region"] = region_name
            candidates.append(entry)
    if best_candidate and best_candidate.text:
        candidates.append({
            "engine": best_candidate.engine,
            "lang": best_candidate.lang,
            "text": best_candidate.text,
            "confidence": best_candidate.confidence,
            "region": "document",
        })
    candidates.sort(key=lambda item: item.get("confidence", 0.0), reverse=True)
    return {
        "fields": fields,
        "raw_text": text,
        "best_text": best_candidate.text if best_candidate else text,
        "best_confidence": best_candidate.confidence if best_candidate else 0.0,
        "candidates": candidates,
        "document_side": "unknown",
    }


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _score_text(text: str, confidence: float) -> float:
    length_bonus = min(len(_normalize_text(text)) / 20.0, 35.0)
    return round(min(99.0, max(0.0, confidence + length_bonus)), 1)


def _ocr_tesseract(image, lang="eng"):
    if not TESSERACT_AVAILABLE:
        return []
    if isinstance(lang, (list, tuple, set)):
        lang = _build_tesseract_lang_string(list(lang))
    candidates: List[OCRCandidate] = []
    custom_config = r"--oem 1 --psm 6"
    gray = _ensure_gray(image)
    for processed in [gray]:
        try:
            text = pytesseract.image_to_string(processed, lang=lang, config=custom_config)
        except Exception:
            try:
                text = pytesseract.image_to_string(processed, lang="eng", config=custom_config)
            except Exception:
                text = ""
        text = _normalize_text(text)
        if text:
            confidence = _score_text(text, 54.0)
            candidates.append(OCRCandidate("tesseract", lang, text, confidence))
    return candidates


_EASYOCR_READER = None
def _ocr_easyocr(image, lang="en"):
    global _EASYOCR_READER
    if not EASYOCR_AVAILABLE:
        return []
    try:
        if isinstance(lang, str):
            lang = [lang]
        lang = _build_easyocr_langs(lang)
        if _EASYOCR_READER is None:
            _EASYOCR_READER = easyocr.Reader(lang, gpu=False)
        candidates = []
        for processed in _enhance_image(image):
            result = _EASYOCR_READER.readtext(processed, detail=1, paragraph=True)
            text_parts = []
            scores = []
            for item in result or []:
                if len(item) >= 2:
                    text_parts.append(str(item[1]))
                    if len(item) > 2:
                        scores.append(float(item[2]))
            text = _normalize_text(" ".join(text_parts))
            if text:
                confidence = _score_text(text, (sum(scores) / max(len(scores), 1)) * 100 if scores else 68.0)
                candidates.append(OCRCandidate("easyocr", lang, text, confidence))
        return candidates
    except Exception:
        return []


_PADDLEOCR_READER = None

def warm_up_ocr_models():
    """Call this at application startup to load OCR models into memory once."""
    global _PADDLEOCR_READER
    if PADDLEOCR_AVAILABLE and _PADDLEOCR_READER is None:
        t0 = time.time()
        try:
            import logging as _logging
            _logging.getLogger("ppocr").setLevel(_logging.ERROR)
            _PADDLEOCR_READER = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False, use_tensorrt=False)
            logger.info("[OCR] PaddleOCR model loaded and ready. Took %.2fs", time.time() - t0)
        except Exception as e:
            logger.error("[OCR] Failed to initialize PaddleOCR: %s\n%s", e, traceback.format_exc())

def _ocr_paddleocr(image, lang="en"):
    global _PADDLEOCR_READER
    if not PADDLEOCR_AVAILABLE:
        logger.debug("[OCR] PaddleOCR unavailable - skipped.")
        return []
    t0 = time.time()
    try:
        if _PADDLEOCR_READER is None:
            logger.info("[OCR] PaddleOCR: lazy-loading model...")
            import logging as _logging
            _logging.getLogger("ppocr").setLevel(_logging.ERROR)
            _PADDLEOCR_READER = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False, use_tensorrt=False)
            logger.info("[OCR] PaddleOCR: model loaded in %.2fs", time.time() - t0)
        candidates = []
        # PaddleOCR expects 3-channel BGR/RGB images, so do NOT convert to grayscale
        resized = _resize_for_ocr(image)
        if len(resized.shape) == 2:
            resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
        result = _PADDLEOCR_READER.ocr(resized)
        text_parts = []
        scores = []
        for line in result or []:
            if not line:
                continue
            for box in line:
                if len(box) >= 2:
                    text_parts.append(str(box[1][0]))
                    scores.append(float(box[1][1]))
        text = _normalize_text(" ".join(text_parts))
        if text:
            raw_conf = (sum(scores) / max(len(scores), 1)) * 100 if scores else 70.0
            confidence = _score_text(text, raw_conf)
            logger.info(
                "[OCR] PaddleOCR: engine=paddleocr, text_len=%d, raw_conf=%.1f%%, final_conf=%.1f%%, time=%.2fs",
                len(text), raw_conf, confidence, time.time() - t0
            )
            candidates.append(OCRCandidate("paddleocr", lang, text, confidence))
        else:
            logger.warning("[OCR] PaddleOCR: no text extracted. time=%.2fs", time.time() - t0)
        return candidates
    except Exception as e:
        logger.error("[OCR] PaddleOCR exception: %s\n%s", e, traceback.format_exc())
        return []


def _extract_pdf_text(file_path):
    if not PYPDF2_AVAILABLE:
        return ""
    try:
        reader = PdfReader(file_path)
        parts = []
        for page in reader.pages[:3]:
            parts.append(page.extract_text() or "")
        return _normalize_text("\n".join(parts))
    except Exception:
        return ""


def ocr_document(file_path, lang_hints=None):
    """Primary: PaddleOCR. Fallback: Tesseract only if PaddleOCR returns no text."""
    lang_hints = _unique(lang_hints or ["eng"])
    ext = os.path.splitext(file_path)[1].lower()
    t0 = time.time()

    # Step 1: For PDFs, attempt direct text extraction first
    if ext == ".pdf":
        pdf_text = _extract_pdf_text(file_path)
        if pdf_text and len(pdf_text.strip()) > 20:
            logger.info("[OCR] PDF direct text extraction succeeded: len=%d, time=%.2fs", len(pdf_text), time.time() - t0)
            return {
                "best": OCRCandidate("pdf-text", "text", pdf_text, 96.0),
                "candidates": [OCRCandidate("pdf-text", "text", pdf_text, 96.0)],
            }

    # Step 2: Load image
    image = cv2.imread(file_path)
    if image is None:
        logger.error("[OCR] cv2.imread failed for: %s", file_path)
        return {"best": OCRCandidate("none", "none", "", 0.0), "candidates": []}

    # Step 3: Primary OCR - PaddleOCR
    candidates: List[OCRCandidate] = []
    paddle_candidates = _ocr_paddleocr(image, lang="en")
    candidates.extend(paddle_candidates)

    # Step 4: Fallback - Tesseract only if PaddleOCR returned nothing
    if not candidates or not any(c.text for c in candidates):
        logger.warning("[OCR] PaddleOCR returned no text. Falling back to Tesseract.")
        tess_lang = _build_tesseract_lang_string(lang_hints)
        tess_candidates = _ocr_tesseract(image, lang=tess_lang)
        candidates.extend(tess_candidates)
        if tess_candidates:
            logger.info("[OCR] Tesseract fallback produced %d candidates.", len(tess_candidates))
        else:
            logger.warning("[OCR] Tesseract fallback also returned no text.")

    if not candidates:
        logger.error("[OCR] All OCR engines failed for: %s", file_path)
        return {"best": OCRCandidate("none", "none", "", 0.0), "candidates": []}

    candidates.sort(key=lambda item: item.confidence, reverse=True)
    best = candidates[0]
    logger.info(
        "[OCR] Final result: engine=%s, confidence=%.1f%%, text_len=%d, total_time=%.2fs",
        best.engine, best.confidence, len(best.text or ""), time.time() - t0
    )
    return {"best": best, "candidates": candidates}


def multi_ocr_candidates(file_path):
    result = ocr_document(file_path, lang_hints=["eng", "en"])
    candidates = result["candidates"] or [OCRCandidate("none", "none", "", 0.0)]
    return [
        {
            "engine": candidate.engine,
            "lang": candidate.lang,
            "text": candidate.text,
            "confidence": candidate.confidence,
        }
        for candidate in candidates
    ]


def ocr_image(file_path, lang="eng"):
    result = ocr_document(file_path, lang_hints=[lang])
    best = result["best"]
    return best.text if best else ""


def decode_qr_and_barcode(file_path):
    result = {"qr_data": [], "barcode_data": []}
    if not os.path.exists(file_path) or not PYZBAR_AVAILABLE:
        return result
    img = cv2.imread(file_path)
    if img is None:
        return result
    try:
        decoded = decode_barcodes(img)
        for item in decoded:
            data = item.data.decode("utf-8", errors="ignore")
            if not data:
                continue
            if item.type and "qrcode" in item.type.lower():
                result["qr_data"].append(data)
            else:
                result["barcode_data"].append(data)
    except Exception:
        return result
    return result


def extract_name_from_filename(filename):
    if not filename:
        return None
    name_part = os.path.splitext(os.path.basename(filename))[0]
    name_part = re.sub(
        r"\b(aadhaar|aadhar|card|ocr|verified|copy|temp|doc|document|pdf|jpg|jpeg|png|zip|income|caste|disability|ration|cert|certificate|passport|pan|dl|license|licence)\b",
        "",
        name_part,
        flags=re.IGNORECASE,
    )
    name_part = re.sub(r"[\d_\-\(\)\[\]]+", " ", name_part).strip()
    name_part = re.sub(r"\s+", " ", name_part)
    return name_part.title() if len(name_part) >= 3 else None


def extract_user_name_match(raw_text, user_id):
    if not raw_text or not user_id:
        return ""
    try:
        from bson import ObjectId
        from database import get_db

        db = get_db()
        if db is not None:
            user = db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                db_name = user.get("name", "").strip()
                if not db_name:
                    return ""
                raw_text_u = raw_text.upper()
                db_name_u = db_name.upper()
                if db_name_u in raw_text_u:
                    return db_name.title()
                db_tokens = [t for t in db_name_u.split() if len(t) > 2]
                if db_tokens:
                    for line in raw_text_u.split("\n"):
                        matched = sum(1 for t in db_tokens if t in line)
                        if matched >= max(1, int(len(db_tokens) * 0.7)):
                            return db_name.title()
    except Exception as e:
        print("Error in extract_user_name_match:", e)
    return ""
