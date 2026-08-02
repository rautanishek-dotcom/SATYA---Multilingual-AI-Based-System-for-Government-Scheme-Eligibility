"""Central policy definitions for the SATYA vault."""

SUPPORTED_DOCUMENT_TYPES = {
    "aadhaar_ekyc": {
        "label": "Aadhaar Offline e-KYC",
        "requires_identity_lock": False,
        "is_identity_document": True,
        "required_fields": ["name", "dob", "gender", "masked_aadhaar"],
    },
    "aadhaar_ocr": {
        "label": "Aadhaar Card",
        "requires_identity_lock": False,
        "is_identity_document": True,
        "required_fields": ["name", "dob", "gender", "masked_aadhaar"],
    },
    "pan": {
        "label": "PAN Card",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "identity_number"],
    },
    "passport": {
        "label": "Passport",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "identity_number"],
    },
    "driving_license": {
        "label": "Driving Licence",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "identity_number"],
    },
    "voter_id": {
        "label": "Voter ID",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob"],
    },
    "ration_card": {
        "label": "Ration Card",
        "requires_identity_lock": True,
        "required_fields": ["family_members"],
        "family_member_rule": True,
    },
    "income_certificate": {
        "label": "Income Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "income", "certificate_number", "issuing_authority"],
    },
    "caste_certificate": {
        "label": "Caste Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "caste", "category", "certificate_number"],
    },
    "domicile_certificate": {
        "label": "Domicile Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "certificate_number"],
    },
    "disability_certificate": {
        "label": "Disability Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "disability_percent", "disability_type"],
    },
    "birth_certificate": {
        "label": "Birth Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "parents"],
    },
    "death_certificate": {
        "label": "Death Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob"],
    },
    "marriage_certificate": {
        "label": "Marriage Certificate",
        "requires_identity_lock": True,
        "required_fields": ["bride", "groom", "marriage_date"],
    },
    "residence_certificate": {
        "label": "Residence Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob", "address"],
    },
    "character_certificate": {
        "label": "Character Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob"],
    },
    "education_certificate": {
        "label": "Education Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name"],
    },
    "land_records": {
        "label": "Land Records",
        "requires_identity_lock": True,
        "required_fields": ["name", "address"],
    },
    "pension_document": {
        "label": "Pension Document",
        "requires_identity_lock": True,
        "required_fields": ["name", "dob"],
    },
    "government_certificate": {
        "label": "Government-issued Certificate",
        "requires_identity_lock": True,
        "required_fields": ["name"],
    },
    "resume": {
        "label": "Resume",
        "requires_identity_lock": False,
        "required_fields": [],
    },
    "other_document": {
        "label": "Other Document",
        "requires_identity_lock": False,
        "required_fields": [],
    },
}

SUPPORTED_DOCUMENT_LABELS = {
    key: value["label"] for key, value in SUPPORTED_DOCUMENT_TYPES.items()
}

MISMATCH_RESPONSE = {
    "verificationStatus": "Rejected",
    "reason": "Identity Mismatch",
    "message": "The uploaded document belongs to another individual and cannot be added to your SATYA Vault.",
}

RESET_COOLDOWN_HOURS = 24
ACCEPT_SCORE = 90
CONFIRM_SCORE = 70
LOW_CONFIDENCE_THRESHOLD = 90
MAX_UPLOAD_MB = 20
MIN_ACCEPTABLE_QUALITY = 45
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
SUPPORTED_DOCUMENT_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf", ".zip"}
