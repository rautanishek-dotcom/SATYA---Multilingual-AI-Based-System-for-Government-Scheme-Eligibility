import datetime
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict

from bson import ObjectId

from database import get_db
from vault.audit import AuditLogger
from vault.document_classifier import DocumentClassifier
from vault.document_vault import DocumentVault
from vault.identity_matcher import evaluate_identity_match, lock_identity_if_needed
from vault.policy import (
    ACCEPT_SCORE,
    CONFIRM_SCORE,
    LOW_CONFIDENCE_THRESHOLD,
    MIN_ACCEPTABLE_QUALITY,
    MISMATCH_RESPONSE,
    SUPPORTED_DOCUMENT_TYPES,
)
from vault.quality_detector import QualityDetector
from vault.ocr_utils import (
    decode_qr_and_barcode,
    extract_structured_document_fields,
    multi_ocr_candidates,
    ocr_document,
    ocr_image,
    quick_document_hint,
)
from vault.security import SecurityManager
from vault.utils import VaultUtils
from vault.verification_status import VerificationStatus


def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj


def _empty_field(value="", confidence=0.0):
    return VaultUtils.field(value, confidence)


def _normalize_lines(text):
    lines = []
    for raw_line in (text or "").splitlines():
        line = VaultUtils.clean_extracted_text(raw_line).strip()
        if line:
            lines.append(line)
    return lines


def _first_match(patterns, text, flags=re.IGNORECASE):
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match
    return None


def _field_from_label(text, labels, confidence=94.0):
    for label in labels:
        pattern = rf"{label}\s*[:\-]\s*(.+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _empty_field(VaultUtils.clean_extracted_text(match.group(1)), confidence)
    return _empty_field()


def _extract_name(lines, text, user_name=None):
    patterns = [
        r"\bname\b\s*[:\-]\s*([A-Za-z][A-Za-z\s\.\']{2,})",
        r"\bholder name\b\s*[:\-]\s*([A-Za-z][A-Za-z\s\.\']{2,})",
        r"\bapplicant name\b\s*[:\-]\s*([A-Za-z][A-Za-z\s\.\']{2,})",
    ]
    match = _first_match(patterns, text)
    if match:
        return _empty_field(VaultUtils.canonicalize_name(match.group(1)), 96.0)

    for line in lines:
        if len(line) < 4:
            continue
        if any(token in line.lower() for token in ["government", "uidai", "ministry", "department", "certificate"]):
            continue
        if re.fullmatch(r"[A-Za-z][A-Za-z\s\.\']{3,}", line):
            candidate = VaultUtils.canonicalize_name(line)
            if candidate:
                return _empty_field(candidate, 85.0)

    if user_name:
        return _empty_field(VaultUtils.canonicalize_name(user_name), 70.0)
    return _empty_field()


def _extract_dob(text):
    patterns = [
        r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b",
        r"\b(\d{4}[/-]\d{2}[/-]\d{2})\b",
        r"\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b",
        r"\b(?:dob|date of birth|year of birth|yob)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2}|\d{4})",
    ]
    match = _first_match(patterns, text)
    if match:
        return _empty_field(VaultUtils.normalize_date(match.group(1)), 95.0)
    return _empty_field()


def _extract_gender(text):
    text_l = text.lower()
    if "female" in text_l or "महिला" in text_l:
        return _empty_field("Female", 96.0)
    if "male" in text_l or "पुरुष" in text_l:
        return _empty_field("Male", 96.0)
    if "transgender" in text_l or "third gender" in text_l:
        return _empty_field("Transgender", 96.0)
    return _empty_field()


def _extract_number(text, doc_type):
    patterns = {
        "pan": [r"\b([A-Z]{5}\d{4}[A-Z])\b"],
        "passport": [r"\b([A-Z]\d{7})\b"],
        "driving_license": [r"\b([A-Z]{2}[-\s]?\d{2}[-\s]?\d{11,13})\b", r"\b([A-Z]{2}\d{2}\d{11,13})\b"],
        "voter_id": [r"\b([A-Z]{3}\d{7})\b", r"\b([A-Z]{2,3}\d{6,9})\b"],
        "certificate_number": [r"\b([A-Z0-9][A-Z0-9/\-]{5,})\b"],
    }
    for pattern in patterns.get(doc_type, []):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _empty_field(match.group(1).upper(), 92.0)
    return _empty_field()


def _extract_income(text):
    patterns = [
        r"\b(?:annual income|income)\s*[:\-]?\s*[₹Rs\.]*\s*([\d,]+(?:\.\d+)?)",
        r"\b₹\s*([\d,]+(?:\.\d+)?)",
    ]
    match = _first_match(patterns, text)
    if match:
        return _empty_field(match.group(1).replace(",", ""), 92.0)
    return _empty_field()


def _extract_address(text):
    labels = ["address", "residence", "house", "home address"]
    field = _field_from_label(text, labels, confidence=92.0)
    if str(field["value"]).strip():
        return field
    chunks = []
    for key in ["house", "street", "village", "taluk", "district", "state", "pincode", "country"]:
        match = re.search(rf"\b{key}\s*[:\-]\s*([A-Za-z0-9\s,./-]+)", text, re.IGNORECASE)
        if match:
            chunks.append(VaultUtils.clean_extracted_text(match.group(1)))
    if chunks:
        return _empty_field(", ".join(chunks), 84.0)
    return _empty_field()


def _extract_parents(text):
    parent = _field_from_label(text, ["father", "father's name", "mother", "mother's name", "guardian", "guardian name"], confidence=92.0)
    if str(parent["value"]).strip():
        return parent
    return _empty_field()


def _extract_certificate_specific(text, document_type):
    fields = OrderedDict()
    if document_type == "income_certificate":
        fields["income"] = _extract_income(text)
        fields["certificate_number"] = _extract_number(text, "certificate_number")
        fields["issuing_authority"] = _field_from_label(text, ["issuing authority", "authority", "office"], 90.0)
    elif document_type == "caste_certificate":
        fields["caste"] = _field_from_label(text, ["caste"], 90.0)
        fields["category"] = _field_from_label(text, ["category", "community"], 90.0)
        fields["certificate_number"] = _extract_number(text, "certificate_number")
        fields["issuing_authority"] = _field_from_label(text, ["issuing authority", "authority", "office"], 90.0)
    elif document_type == "disability_certificate":
        percent_match = re.search(r"\b(\d{1,3})\s*%\b", text)
        fields["disability_percent"] = _empty_field(percent_match.group(1) if percent_match else "", 90.0 if percent_match else 0.0)
        fields["disability_type"] = _field_from_label(text, ["disability type", "type of disability"], 90.0)
        fields["certificate_number"] = _extract_number(text, "certificate_number")
    elif document_type == "birth_certificate":
        fields["parents"] = _extract_parents(text)
        fields["certificate_number"] = _extract_number(text, "certificate_number")
    elif document_type == "marriage_certificate":
        fields["bride"] = _field_from_label(text, ["bride", "wife"], 90.0)
        fields["groom"] = _field_from_label(text, ["groom", "husband"], 90.0)
        fields["marriage_date"] = _extract_dob(text)
    elif document_type == "ration_card":
        family_block = _field_from_label(text, ["family members", "members", "family"], 90.0)
        fields["family_members"] = family_block
    return fields


def _extract_generic_fields(document_type, text, user_name=None):
    lines = _normalize_lines(text)
    fields = OrderedDict()
    fields["name"] = _extract_name(lines, text, user_name=user_name)
    fields["dob"] = _extract_dob(text)
    fields["gender"] = _extract_gender(text)
    fields["identity_number"] = _extract_number(text, document_type)
    fields["masked_aadhaar"] = _empty_field(VaultUtils.mask_aadhaar(text), 60.0 if "aadhaar" in document_type else 0.0)
    fields["address"] = _extract_address(text)
    fields["parents"] = _extract_parents(text)
    fields.update(_extract_certificate_specific(text, document_type))

    if document_type == "aadhaar_ocr":
        fields["masked_aadhaar"] = _empty_field(_extract_masked_aadhaar(text), 96.0)
        fields["aadhaar_reference_id"] = _extract_aadhaar_reference(text)
    if document_type == "passport":
        fields["identity_number"] = _extract_number(text, "passport")
    if document_type == "pan":
        fields["identity_number"] = _extract_number(text, "pan")
    if document_type == "driving_license":
        fields["identity_number"] = _extract_number(text, "driving_license")

    return fields


def _extract_masked_aadhaar(text):
    patterns = [
        r"[Xx\*]{4}\s?[Xx\*]{4}\s?(\d{4})",
        r"\b(\d{4})\s(\d{4})\s(\d{4})\b",
    ]
    match = _first_match(patterns, text)
    if match:
        return f"XXXX-XXXX-{match.group(1) if len(match.groups()) == 1 else match.group(3)}"
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 12:
        return f"XXXX-XXXX-{digits[-4:]}"
    return "XXXX-XXXX-XXXX"


def _extract_aadhaar_reference(text):
    patterns = [
        r"\b(?:reference id|aadhaar reference id|vid)\s*[:\-]?\s*([A-Z0-9]{8,32})",
        r"\b([A-Z0-9]{28})\b",
    ]
    match = _first_match(patterns, text, flags=re.IGNORECASE)
    if match:
        return _empty_field(match.group(1).strip(), 94.0)
    return _empty_field()


def _extract_zip_aadhaar_fields(file_path, share_code):
    extracted = OrderedDict()
    raw_xml = ""
    with zipfile.ZipFile(file_path, "r") as zip_ref:
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

    extracted["name"] = _empty_field(VaultUtils.canonicalize_name(poi.get("name", "")), 98.0)
    extracted["dob"] = _empty_field(VaultUtils.normalize_date(poi.get("dob", "")), 98.0)
    extracted["gender"] = _empty_field(VaultUtils.normalize_gender(poi.get("gender", "")), 98.0)
    extracted["masked_aadhaar"] = _empty_field(VaultUtils.mask_aadhaar(root.get("referenceId", "")), 95.0)
    extracted["aadhaar_reference_id"] = _empty_field(root.get("referenceId", ""), 95.0)
    address = ""
    if poa is not None:
        address = ", ".join(
            part
            for part in [
                poa.get("house", ""),
                poa.get("street", ""),
                poa.get("loc", ""),
                poa.get("vtc", ""),
                poa.get("dist", ""),
                poa.get("state", ""),
                poa.get("pc", ""),
            ]
            if part
        )
    extracted["address"] = _empty_field(address, 92.0 if address else 0.0)
    extracted["raw_xml"] = raw_xml
    return extracted


def _detect_fraud(text, quality_result, extracted_fields, qr_result):
    findings = []
    probability = 0.0

    quality_issues = quality_result.get("issues", [])
    probability += min(30.0, len(quality_issues) * 6.0)
    findings.extend(quality_issues)

    text_l = (text or "").lower()
    suspicious_terms = ["fake", "forged", "tampered", "edited", "photoshop", "manipulated", "counterfeit", "replaced photograph"]
    for term in suspicious_terms:
        if term in text_l:
            probability += 20.0
            findings.append(f"Suspicious keyword detected: {term}")

    if qr_result.get("available") and not qr_result.get("passed", True):
        probability += 40.0
        findings.append("QR mismatch detected")

    for key, value in extracted_fields.items():
        if isinstance(value, dict):
            confidence = float(value.get("confidence", 0))
            if value.get("value") and confidence < 60:
                probability += 4.0
                findings.append(f"Low confidence for field: {key}")

    probability = max(0.0, min(100.0, probability))
    return {
        "fraud_probability": round(probability, 2),
        "findings": findings,
        "passed": probability < 70.0,
    }


def _build_search_index(document_type, extracted_fields):
    pieces = [document_type]
    for value in extracted_fields.values():
        if isinstance(value, dict):
            raw_value = str(value.get("value", "")).strip()
            if raw_value:
                pieces.append(raw_value)
    return " ".join(pieces).lower()


def _map_force_engine(force_engine):
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
        return None
    return {
        "document_type": forced_type,
        "document_label": SUPPORTED_DOCUMENT_TYPES.get(forced_type, {}).get("label", forced_type),
        "confidence": 100.0,
        "verification_engine": force_engine,
        "requires_share_code": forced_type == "aadhaar_ekyc",
        "supported": True,
        "reason": "Forced by request",
    }


def _document_requirements(document_type):
    return SUPPORTED_DOCUMENT_TYPES.get(document_type, {})


class VerificationOrchestrator:
    def __init__(self):
        self.classifier = DocumentClassifier()

    def _get_identity_state(self, user_id):
        db = get_db()
        if db is None:
            return None, False, {}
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None, False, {}
        return user, bool(user.get("identity_locked", False)), user.get("identity_profile", {}) or {}

    def _load_cached_duplicate(self, user_id, doc_hash):
        try:
            return DocumentVault.get_user_vault(user_id, query=doc_hash)
        except Exception:
            return []

    def _collect_ocr_text(self, file_path, hint_language="eng"):
        try:
            hint_text = quick_document_hint(file_path)
            ocr_result = ocr_document(file_path, lang_hints=[hint_language, "eng", "en"])
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
            if best and best.confidence < LOW_CONFIDENCE_THRESHOLD:
                fallback = ocr_image(file_path, lang="eng")
                if len(fallback.strip()) > len(raw_text.strip()):
                    raw_text = fallback
            if not candidates:
                candidates = multi_ocr_candidates(file_path)
            combined_text = " ".join(part for part in [hint_text, raw_text] if part).strip()
            return combined_text or raw_text, candidates, hint_text
        except Exception:
            candidates = multi_ocr_candidates(file_path)
            best = candidates[0] if candidates else {"text": "", "confidence": 0.0}
            return best.get("text", ""), candidates, ""

    def _extract_document_data(self, document_type, file_path, raw_text, user_id=None, share_code=None, hint_text="", qr_result=None):
        user = None
        user_name = None
        if user_id:
            db = get_db()
            if db is not None:
                user = db.users.find_one({"_id": ObjectId(user_id)})
                if user:
                    user_name = user.get("name", "")

        qr_result = qr_result or decode_qr_and_barcode(file_path)
        qr_blob = qr_result.get("qr_data", [None])[0] if qr_result.get("qr_data") else ""
        structured = extract_structured_document_fields(
            file_path,
            document_type=document_type,
            user_name=user_name,
            share_code=share_code,
            hint_text=hint_text or raw_text,
            qr_payload=qr_blob,
        )
        if document_type in {"aadhaar_ocr", "aadhaar_ekyc"}:
            extracted = structured.get("fields", OrderedDict())
        else:
            extracted = _extract_generic_fields(document_type, raw_text, user_name=user_name)
        raw_text = structured.get("raw_text", raw_text)
        best_text = structured.get("best_text", "")
        best_confidence = float(structured.get("best_confidence", 0.0) or 0.0)
        if "document_type" not in extracted and document_type in {"aadhaar_ocr", "aadhaar_ekyc"}:
            extracted["document_type"] = _empty_field(
                "Aadhaar Offline e-KYC" if document_type == "aadhaar_ekyc" else "Aadhaar Card",
                99.0,
            )
        if qr_blob:
            extracted["qr_code_data"] = _empty_field(qr_blob, 99.0)
        if qr_result.get("qr_data"):
            extracted["qr_code_data"] = _empty_field(qr_result["qr_data"][0], 99.0)
        if qr_result.get("barcode_data"):
            extracted["barcode_data"] = _empty_field(qr_result["barcode_data"][0], 99.0)

        signature_field = extracted.get("digital_signature", _empty_field())
        signature_text = str(signature_field.get("value", "")).strip().lower()
        if not signature_text and raw_text:
            lowered = raw_text.lower()
            if any(token in lowered for token in ["digitally signed", "digital signature", "signature verified", "signed by"]):
                extracted["digital_signature"] = _empty_field("Present", 80.0)
        extracted["seal"] = extracted.get("seal", _empty_field())
        extracted["stamp"] = extracted.get("stamp", _empty_field())
        extracted["watermark"] = extracted.get("watermark", _empty_field())
        extracted["__best_ocr_confidence"] = _empty_field("", best_confidence)
        return extracted, qr_result

    def extract_document_fields(self, user_id, file_path, original_filename, share_code=None, force_engine=None):
        if not os.path.exists(file_path):
            return {"status": VerificationStatus.FAILED, "error": "File not found"}

        quality_result = QualityDetector.analyze(file_path)
        qr_result = decode_qr_and_barcode(file_path)
        qr_blob = " ".join(qr_result.get("qr_data", []) + qr_result.get("barcode_data", []))
        preflight_hint = quick_document_hint(file_path)
        classification = DocumentClassifier.classify(
            file_path,
            original_filename,
            hint_text=" ".join(part for part in [preflight_hint, qr_blob] if part),
        )

        if force_engine:
            forced = _map_force_engine(force_engine)
            if forced:
                classification = forced

        if not classification.get("supported"):
            classification = {
                "document_type": "government_certificate",
                "document_label": SUPPORTED_DOCUMENT_TYPES.get("government_certificate", {}).get("label", "Government-issued Certificate"),
                "confidence": classification.get("confidence", 0.0),
                "verification_engine": classification.get("verification_engine", "generic_document"),
                "supported": False,
                "reason": classification.get("reason", "Unsupported document detected."),
            }

        raw_text, ocr_candidates, hint_text = self._collect_ocr_text(file_path)
        document_type = classification.get("document_type", "government_certificate")
        extracted_data, qr_result = self._extract_document_data(
            document_type,
            file_path,
            raw_text,
            user_id=user_id,
            share_code=share_code,
            hint_text=hint_text,
            qr_result=qr_result,
        )

        sanitized_fields = sanitize_for_json({k: v for k, v in extracted_data.items() if not k.startswith("__")})
        required_fields = _document_requirements(document_type).get("required_fields", [])
        missing_fields = [
            field for field in required_fields
            if not str(extracted_data.get(field, {}).get("value", "")).strip()
        ]

        return {
            "status": "EXTRACTED",
            "message": "Field extraction complete",
            "classification": classification,
            "quality": quality_result,
            "fields": sanitized_fields,
            "raw_text": raw_text,
            "ocr_candidates": ocr_candidates,
            "qr": qr_result,
            "missing_fields": missing_fields,
            "validation": {
                "required_fields": required_fields,
                "document_type": document_type,
            },
        }

    def process_document(self, user_id, file_path, original_filename, **kwargs):
        if not os.path.exists(file_path):
            return {"status": VerificationStatus.FAILED, "error": "File not found"}

        quality_result = QualityDetector.analyze(file_path)
        if not quality_result.get("passed", True) and quality_result.get("quality_score", 0) < MIN_ACCEPTABLE_QUALITY:
            return {
                "status": VerificationStatus.REJECTED,
                "verificationStatus": "Rejected",
                "reason": "Document Quality Failed",
                "message": "The uploaded document is unusable due to blur, low resolution, or cropping.",
                "quality": quality_result,
            }

        doc_hash = SecurityManager.generate_file_hash(file_path)
        if doc_hash:
            db = get_db()
            if db is not None:
                existing_doc = db.vault_documents.find_one({
                    "user_id": str(user_id),
                    "document_hash": doc_hash,
                    "verification_status": {"$in": [VerificationStatus.VERIFIED, VerificationStatus.OCR_VERIFIED]},
                })
                if existing_doc:
                    existing_doc["_id"] = str(existing_doc["_id"])
                    return {
                        "status": VerificationStatus.VERIFIED,
                        "message": "Document already verified.",
                        "document": sanitize_for_json(existing_doc),
                        "classification": {
                            "document_type": existing_doc.get("document_type"),
                            "document_label": existing_doc.get("document_label"),
                            "confidence": existing_doc.get("confidence", 0),
                            "verification_engine": existing_doc.get("verification_method"),
                            "supported": True,
                        },
                    }

        qr_result = decode_qr_and_barcode(file_path)
        qr_blob = " ".join(qr_result.get("qr_data", []) + qr_result.get("barcode_data", []))
        preflight_hint = quick_document_hint(file_path)
        classification = DocumentClassifier.classify(file_path, original_filename, hint_text=" ".join(part for part in [preflight_hint, qr_blob] if part))
        force_engine = kwargs.get("force_engine")
        if force_engine:
            forced = _map_force_engine(force_engine)
            if forced:
                classification = forced

        if not classification.get("supported") and not kwargs.get("force_type"):
            return {
                "status": VerificationStatus.REJECTED,
                "verificationStatus": "Rejected",
                "reason": "Unsupported Document",
                "message": classification.get("reason") or "Unsupported document detected. Please upload a valid Aadhaar Card or supported government document.",
                "classification": classification,
                "quality": quality_result,
            }

        raw_text, ocr_candidates, hint_text = self._collect_ocr_text(file_path)
        classification = DocumentClassifier.classify(file_path, original_filename, hint_text=" ".join(part for part in [preflight_hint, hint_text, raw_text, qr_blob] if part))

        if classification["confidence"] < 60.0 and not kwargs.get("force_type"):
            return {
                "status": VerificationStatus.CLASSIFYING,
                "message": "Could not classify document. Please rename the file with a recognizable document type.",
                "classification": classification,
                "quality": quality_result,
            }

        user, identity_locked, identity_profile = self._get_identity_state(user_id)
        if user is None:
            return {"status": VerificationStatus.FAILED, "error": "User not found"}

        document_type = classification.get("document_type", "unknown")
        if not identity_locked and document_type not in {"aadhaar_ekyc", "aadhaar_ocr"}:
            return {
                "status": VerificationStatus.REJECTED,
                "verificationStatus": "Rejected",
                "reason": "Identity Verification Required",
                "message": "Please verify your Aadhaar first to create your Identity Lock.",
                "quality": quality_result,
                "classification": classification,
            }

        share_code = kwargs.get("share_code")
        extracted_data, qr_result = self._extract_document_data(
            document_type,
            file_path,
            raw_text,
            user_id=user_id,
            share_code=share_code,
            hint_text=hint_text,
            qr_result=qr_result,
        )

        fraud_result = _detect_fraud(raw_text, quality_result, extracted_data, qr_result)
        if not fraud_result["passed"]:
            AuditLogger.record("vault_fraud_rejected", user_id, {
                "document_type": document_type,
                "fraud_probability": fraud_result["fraud_probability"],
                "findings": fraud_result["findings"],
            })
            return {
                "status": VerificationStatus.REJECTED,
                "verificationStatus": "Rejected",
                "reason": "Fraud Detected",
                "message": "The uploaded document appears to be forged, tampered with, or otherwise unsafe to store.",
                "fraud": fraud_result,
                "classification": classification,
            }

        if qr_result.get("qr_data"):
            qr_blob = qr_result["qr_data"][0]
            qr_fields = _normalize_lines(qr_blob)
            extracted_text_blob = " ".join(
                str(field.get("value", ""))
                for key, field in extracted_data.items()
                if isinstance(field, dict) and not key.startswith("__")
            )
            if extracted_text_blob and VaultUtils.similarity(qr_blob, extracted_text_blob) < 35:
                return {
                    "status": VerificationStatus.REJECTED,
                    "verificationStatus": "Rejected",
                    "reason": "QR Validation Failed",
                    "message": "The QR data does not match the extracted document data.",
                    "classification": classification,
                    "fraud": fraud_result,
                    "qr": {
                        "available": True,
                        "passed": False,
                        "data": qr_blob,
                    },
                }

        qr_validation = {
            "available": bool(qr_result.get("qr_data") or qr_result.get("barcode_data")),
            "passed": True,
            "data": qr_result.get("qr_data", [None])[0] if qr_result.get("qr_data") else None,
            "barcode": qr_result.get("barcode_data", [None])[0] if qr_result.get("barcode_data") else None,
        }

        signature_validation = {
            "available": bool(str(extracted_data.get("digital_signature", {}).get("value", "")).strip()),
            "passed": True,
            "reason": "Signature heuristic passed" if str(extracted_data.get("digital_signature", {}).get("value", "")).strip() else "No signature present",
        }

        identity_ok, identity_score, needs_confirm, match_msg, updated_identity_profile = evaluate_identity_match(
            user_id,
            document_type,
            extracted_data,
        )

        user_confirmed = str(kwargs.get("confirm_match", "")).lower() == "true"
        if not identity_ok:
            return {
                "status": VerificationStatus.REJECTED,
                "verificationStatus": "Rejected",
                "reason": "Identity Mismatch",
                "message": match_msg or MISMATCH_RESPONSE["message"],
                "identityMatchScore": round(identity_score, 2),
                "classification": classification,
            }
        if needs_confirm and not user_confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "verificationStatus": "ConfirmationRequired",
                "reason": "Fuzzy Match Required",
                "message": match_msg,
                "identityMatchScore": round(identity_score, 2),
                "classification": classification,
                "quality": quality_result,
                "extracted": sanitize_for_json(extracted_data),
            }

        doc_rule = _document_requirements(document_type)
        required_fields = doc_rule.get("required_fields", [])
        missing_fields = [field for field in required_fields if not str(extracted_data.get(field, {}).get("value", "")).strip()]

        confidence_values = [
            float(field.get("confidence", 0))
            for key, field in extracted_data.items()
            if isinstance(field, dict)
            and not key.startswith("__")
            and key not in {"seal", "stamp", "watermark", "document_language", "qr_code_data", "barcode_data"}
            and str(field.get("value", "")).strip()
            and float(field.get("confidence", 0) or 0) > 0
        ]
        document_confidence = round(sum(confidence_values) / max(len(confidence_values), 1), 2)
        best_ocr_confidence = float(extracted_data.get("__best_ocr_confidence", {}).get("confidence", 0) or 0)
        if max(document_confidence, best_ocr_confidence) < LOW_CONFIDENCE_THRESHOLD and not user_confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "verificationStatus": "ConfirmationRequired",
                "reason": "Low Confidence",
                "message": "We need your confirmation because one or more extracted fields are below confidence threshold.",
                "documentConfidence": document_confidence,
                "identityMatchScore": round(identity_score, 2),
                "classification": classification,
                "missingFields": missing_fields,
                "quality": quality_result,
                "extracted": sanitize_for_json({k: v for k, v in extracted_data.items() if not k.startswith("__")}),
            }

        if missing_fields and document_type not in {"education_certificate", "government_certificate"}:
            low_risk_missing = len(missing_fields) <= 2 and document_confidence >= CONFIRM_SCORE
            if not low_risk_missing and document_type != "ration_card":
                return {
                    "status": VerificationStatus.REJECTED,
                    "verificationStatus": "Rejected",
                    "reason": "Missing Required Fields",
                    "message": "The uploaded document is missing mandatory fields for verification.",
                    "missingFields": missing_fields,
                    "classification": classification,
                }

        if not identity_locked and document_type in {"aadhaar_ekyc", "aadhaar_ocr"}:
            locked, lock_profile, message = lock_identity_if_needed(
                user_id,
                extracted_data,
                verification_context={
                    "document_type": classification.get("document_label", document_type),
                    "verification_method": classification.get("verification_engine", "ocr"),
                    "confidence": document_confidence,
                },
            )
            if not locked:
                return {
                    "status": VerificationStatus.REJECTED,
                    "verificationStatus": "Rejected",
                    "reason": "Identity Verification Failed",
                    "message": message,
                    "classification": classification,
                }
            updated_identity_profile = lock_profile

        summary = VaultUtils.document_summary(document_type, extracted_data, quality_result, fraud_result, identity_score)
        search_index = _build_search_index(document_type, extracted_data)

        verification_logs = [
            {"step": "quality", "result": sanitize_for_json(quality_result)},
            {"step": "classification", "result": sanitize_for_json(classification)},
            {"step": "ocr", "result": sanitize_for_json(ocr_candidates)},
            {"step": "fraud", "result": sanitize_for_json(fraud_result)},
            {"step": "identity", "result": {"score": identity_score, "message": match_msg}},
            {"step": "qr", "result": sanitize_for_json(qr_validation)},
            {"step": "signature", "result": sanitize_for_json(signature_validation)},
        ]

        final_status = VerificationStatus.VERIFIED
        metadata = {
            "user_id": user_id,
            "document_hash": doc_hash,
            "document_type": document_type,
            "document_label": classification.get("document_label", document_type),
            "verification_status": final_status,
            "verification_method": classification.get("verification_engine", "generic_document"),
            "verified_fields": sanitize_for_json(extracted_data),
            "confidence": document_confidence,
            "quality_score": quality_result.get("quality_score", 0),
            "identity_match_score": round(identity_score, 2),
            "identity_match_breakdown": updated_identity_profile if isinstance(updated_identity_profile, dict) else {},
            "fraud_probability": fraud_result["fraud_probability"],
            "fraud_findings": fraud_result["findings"],
            "quality_findings": quality_result.get("issues", []),
            "qr_validation": qr_validation,
            "signature_validation": signature_validation,
            "document_summary": summary,
            "missing_fields": missing_fields,
            "verification_logs": verification_logs,
            "search_index": search_index,
            "expiry_date": None,
            "created_at": datetime.datetime.utcnow(),
            "sealed_payload": {
                "raw_text": raw_text,
                "ocr_candidates": ocr_candidates,
                "quality": quality_result,
                "classification": classification,
                "extracted": sanitize_for_json(extracted_data),
                "fraud": fraud_result,
                "qr": qr_result,
            },
        }

        metadata = sanitize_for_json(metadata)
        try:
            doc_id = DocumentVault.save_verification_metadata(metadata)
            stored = DocumentVault.get_document_by_id(doc_id, user_id=user_id)
            if stored:
                stored["identity_profile"] = updated_identity_profile
            AuditLogger.record("vault_document_verified", user_id, {
                "document_id": doc_id,
                "document_type": document_type,
                "identity_match_score": round(identity_score, 2),
            })
            return {
                "status": final_status,
                "verificationStatus": final_status,
                "message": "Verification complete",
                "document": sanitize_for_json(stored or metadata),
                "classification": classification,
                "quality": quality_result,
                "ocr": ocr_candidates,
                "identityMatchScore": round(identity_score, 2),
            }
        except Exception as e:
            return sanitize_for_json({"status": VerificationStatus.FAILED, "error": f"Database error: {e}"})
