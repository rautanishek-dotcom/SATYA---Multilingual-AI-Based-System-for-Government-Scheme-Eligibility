from typing import Dict, List

SUPPORTED_LANGUAGES: List[str] = [
    "en", "hi", "mr", "gu", "bn", "ta", "te", "kn", "ml", "pa", "or"
]

CANONICAL_FIELD_KEYS: List[str] = [
    "full_name",
    "dob",
    "gender",
    "address",
    "aadhaar_number",
    "pan_number",
    "issue_date",
    "expiry_date",
    "district",
    "state",
    "pin_code",
    "certificate_number",
    "issuing_authority",
    "income",
    "category",
    "disability_percent",
    "disability_type",
    "family_members",
    "document_number",
    "qr_code_data",
    "barcode_data",
]

SUPPORTED_DOCUMENT_TYPES: Dict[str, Dict[str, object]] = {
    "aadhaar_front": {
        "label": "Aadhaar Card (Front)",
        "required_fields": ["full_name", "dob", "gender", "aadhaar_number", "address"],
        "aliases": ["Aadhaar Card", "aadhaar front", "aadhaar"]
    },
    "aadhaar_back": {
        "label": "Aadhaar Card (Back)",
        "required_fields": ["address", "pin_code", "state", "district"],
        "aliases": ["Aadhaar back", "aadhaar back"]
    },
    "aadhaar_offline_ekyc": {
        "label": "Aadhaar Offline eKYC XML",
        "required_fields": ["full_name", "dob", "gender", "aadhaar_number"],
        "aliases": ["aadhaar eKYC", "offline ekyc"]
    },
    "pan": {
        "label": "PAN Card",
        "required_fields": ["full_name", "dob", "pan_number"],
        "aliases": ["PAN", "pan card"]
    },
    "passport": {
        "label": "Passport",
        "required_fields": ["full_name", "dob", "gender", "expiry_date"],
        "aliases": ["passport"]
    },
    "driving_license": {
        "label": "Driving Licence",
        "required_fields": ["full_name", "dob", "expiry_date", "document_number"],
        "aliases": ["driving licence", "driving license", "dl"]
    },
    "voter_id": {
        "label": "Voter ID",
        "required_fields": ["full_name", "dob", "document_number"],
        "aliases": ["voter id", "elector card"]
    },
    "birth_certificate": {
        "label": "Birth Certificate",
        "required_fields": ["full_name", "dob", "district", "state"],
        "aliases": ["birth certificate"]
    },
    "income_certificate": {
        "label": "Income Certificate",
        "required_fields": ["full_name", "dob", "income", "issuing_authority"],
        "aliases": ["income certificate"]
    },
    "caste_certificate": {
        "label": "Caste Certificate",
        "required_fields": ["full_name", "dob", "category", "certificate_number"],
        "aliases": ["caste certificate"]
    },
    "residence_certificate": {
        "label": "Residence Certificate",
        "required_fields": ["full_name", "dob", "address", "pin_code"],
        "aliases": ["residence certificate"]
    },
    "disability_certificate": {
        "label": "Disability Certificate",
        "required_fields": ["full_name", "dob", "disability_percent", "disability_type"],
        "aliases": ["disability certificate"]
    },
    "ration_card": {
        "label": "Ration Card",
        "required_fields": ["full_name", "address", "family_members"],
        "aliases": ["ration card"]
    },
}

DOCUMENT_CLASSIFICATION_LABELS: List[str] = [
    "Aadhaar Front",
    "Aadhaar Back",
    "PAN",
    "Passport",
    "Driving Licence",
    "Voter ID",
    "Income Certificate",
    "Birth Certificate",
    "Caste Certificate",
    "Residence Certificate",
    "Disability Certificate",
    "Ration Card",
]

CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.95

AUGMENTATION_PIPELINE: List[str] = [
    "blur",
    "motion_blur",
    "shadow",
    "fold",
    "torn_paper",
    "perspective",
    "skew",
    "rotation",
    "brightness",
    "low_light",
    "reflection",
    "compression",
    "photocopy",
    "screenshot",
    "watermark",
    "dirty_background",
]

LAYOUT_BLOCK_TYPES: List[str] = [
    "government_logo",
    "qr_code",
    "photograph",
    "header",
    "footer",
    "name_block",
    "address_block",
    "dob_block",
    "gender_block",
    "document_number",
    "signature",
    "barcode",
]
