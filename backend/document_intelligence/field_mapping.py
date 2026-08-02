CANONICAL_FIELD_KEYS = {
    "full_name": "name",
    "name": "name",
    "dob": "dob",
    "date_of_birth": "dob",
    "gender": "gender",
    "father_name": "father_name",
    "mother_name": "mother_name",
    "address": "address",
    "aadhaar_number": "aadhaar_number",
    "aadhaar_reference_id": "aadhaar_reference_id",
    "masked_aadhaar": "masked_aadhaar",
    "document_number": "document_number",
    "ration_card_number": "ration_card_number",
    "document_type": "document_type",
    "district": "district",
    "village": "village",
}

REQUIRED_FIELDS_BY_DOCUMENT = {
    "aadhaar_ocr": ["name", "dob", "gender", "masked_aadhaar"],
    "aadhaar_ekyc": ["name", "dob", "gender", "aadhaar_reference_id"],
    "ration_card": ["name", "dob", "address", "ration_card_number"],
    "income_certificate": ["name", "dob", "address", "document_number"],
    "disability_certificate": ["name", "dob", "gender", "document_number"],
}


def map_to_canonical_fields(raw_fields):
    canonical = {}
    for key, value in (raw_fields or {}).items():
        mapped_key = CANONICAL_FIELD_KEYS.get(key.lower(), key.lower())
        canonical[mapped_key] = value
    return canonical


def required_fields_for_document(document_type):
    return REQUIRED_FIELDS_BY_DOCUMENT.get(document_type, [])
