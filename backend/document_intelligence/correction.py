import re
from typing import Dict, Optional

CONFUSION_MAP = {
    "O": "0",
    "0": "0",
    "I": "1",
    "1": "1",
    "L": "1",
    "S": "5",
    "5": "5",
    "B": "8",
    "8": "8",
}

DATE_SEPARATORS = ["/", "-", "."]


def normalize_spacing(value: str) -> str:
    if not value:
        return ""
    text = re.sub(r"\s+", " ", value.strip())
    return text


def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = normalize_spacing(name)
    name = re.sub(r"\b(mr|mrs|ms|dr|shri|sri|smt|kumari)\.?\b", "", name, flags=re.I)
    name = re.sub(r"[^\w\s\-\.' ]", "", name, flags=re.U)
    return normalize_spacing(name).title()


def normalize_address(address: str) -> str:
    if not address:
        return ""
    address = re.sub(r"[^\w\s,\-./]", "", address, flags=re.U)
    address = address.replace("\n", ", ")
    address = re.sub(r",\s*,+", ", ", address)
    return normalize_spacing(address)


def normalize_date(date_str: str) -> str:
    if not date_str:
        return ""
    text = date_str.strip()
    text = re.sub(r"[^0-9A-Za-z/\-\. ]", "", text)
    text = text.replace(".", "/")
    match = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", text)
    if match:
        d, m, y = match.groups()
        if len(y) == 2:
            y = "20" + y if int(y) <= 30 else "19" + y
        return f"{int(d):02d}/{int(m):02d}/{int(y):04d}"
    match = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", text)
    if match:
        y, m, d = match.groups()
        return f"{int(d):02d}/{int(m):02d}/{int(y):04d}"
    return text


def fix_ocr_confusions(value: str) -> str:
    if not value:
        return ""
    corrected = []
    for char in value:
        if char in CONFUSION_MAP:
            corrected.append(CONFUSION_MAP[char])
        else:
            corrected.append(char)
    return normalize_spacing("".join(corrected))


def normalize_field(name: str, value: str) -> str:
    if not value:
        return ""
    name_lower = name.lower()
    if "name" in name_lower:
        return normalize_name(value)
    if name_lower in {"dob", "issue_date", "expiry_date"}:
        return normalize_date(value)
    if "address" in name_lower:
        return normalize_address(value)
    if name_lower in {"aadhaar_number", "pan_number", "pin_code", "document_number"}:
        return fix_ocr_confusions(value.upper())
    return normalize_spacing(value)


def normalize_fields(fields: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    normalized = {}
    for name, payload in fields.items():
        if not isinstance(payload, dict):
            normalized[name] = {"value": str(payload), "confidence": 0.0, "source": "normalized"}
            continue
        raw = str(payload.get("value", ""))
        cleaned = normalize_field(name, raw)
        normalized[name] = {
            "value": cleaned,
            "confidence": float(payload.get("confidence", 0.0) or 0.0),
            "source": payload.get("source", "normalized"),
        }
    return normalized
