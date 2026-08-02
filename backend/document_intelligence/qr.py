import cv2
from typing import Dict, List, Optional

try:
    from pyzbar.pyzbar import decode as decode_barcodes
    _PYZBAR_AVAILABLE = True
except Exception:
    _PYZBAR_AVAILABLE = False


class QREngine:
    @staticmethod
    def decode_qr(image_path: str) -> Dict[str, List[str]]:
        decoded_payloads: List[str] = []
        barcode_payloads: List[str] = []
        image = cv2.imread(image_path)
        if image is None:
            return {"qr_data": [], "barcode_data": []}

        if _PYZBAR_AVAILABLE:
            try:
                codes = decode_barcodes(image)
                for item in codes:
                    data = item.data.decode("utf-8", errors="ignore").strip()
                    if not data:
                        continue
                    if item.type and "qrcode" in item.type.lower():
                        decoded_payloads.append(data)
                    else:
                        barcode_payloads.append(data)
            except Exception:
                pass

        if not decoded_payloads and not barcode_payloads:
            qr_detector = cv2.QRCodeDetector()
            data, points, _ = qr_detector.detectAndDecode(image)
            if data:
                decoded_payloads.append(data.strip())

        return {"qr_data": decoded_payloads, "barcode_data": barcode_payloads}

    @staticmethod
    def parse_aadhaar_qr(payload: str) -> Dict[str, Optional[str]]:
        if not payload:
            return {}
        parsed: Dict[str, Optional[str]] = {}
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(payload)
            for attr in ["name", "dob", "gender", "uid"]:
                value = root.get(attr) or root.get(attr.upper())
                if value:
                    if attr == "uid":
                        parsed["aadhaar_number"] = value
                    else:
                        parsed[attr if attr != "uid" else "aadhaar_number"] = value
        except Exception:
            pass

        if not parsed:
            # fallback parsing for key=value pairs in plaintext
            for key in ["name", "dob", "gender", "uid", "aadhaar"]:
                if key in payload.lower():
                    parts = payload.split()
                    for part in parts:
                        if "name" in part.lower() and "=" in part:
                            parsed["full_name"] = part.split("=", 1)[1]
                        if "dob" in part.lower() and "=" in part:
                            parsed["dob"] = part.split("=", 1)[1]
                        if "uid" in part.lower() and "=" in part:
                            parsed["aadhaar_number"] = part.split("=", 1)[1]
        return parsed

    @staticmethod
    def trust_qr_over_ocr(ocr_fields: Dict[str, Dict[str, object]], qr_fields: Dict[str, str]) -> Dict[str, Dict[str, object]]:
        merged = {k: dict(v) for k, v in ocr_fields.items()}
        for key, value in qr_fields.items():
            if not value:
                continue
            if key == "uid":
                q_key = "aadhaar_number"
            else:
                q_key = key
            if q_key in merged:
                merged[q_key] = {
                    "value": value,
                    "confidence": 99.9,
                    "source": "qr",
                }
            else:
                merged[q_key] = {
                    "value": value,
                    "confidence": 99.9,
                    "source": "qr",
                }
        return merged
