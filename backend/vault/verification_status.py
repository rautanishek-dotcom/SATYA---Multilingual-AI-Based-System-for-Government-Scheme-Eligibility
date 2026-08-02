"""
Canonical document lifecycle statuses and type constants for the SATYA Document Vault.

Lifecycle:  Uploaded → Processing → Awaiting Review → Accepted / Rejected
"""


class DocumentStatus:
    """Tracks the document's processing lifecycle."""
    UPLOADED = "Uploaded"
    PROCESSING = "Processing"
    AWAITING_REVIEW = "Awaiting Review"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"

    ALL = {UPLOADED, PROCESSING, AWAITING_REVIEW, ACCEPTED, REJECTED}


class IdentityStatus:
    """Tracks whether the document owner's identity has been verified."""
    UNVERIFIED = "Unverified"
    VERIFIED = "Verified"
    FAILED = "Failed"

    ALL = {UNVERIFIED, VERIFIED, FAILED}


class ConfidenceTier:
    """Maps OCR confidence percentage to a human-readable tier."""
    EXCELLENT = "Excellent"   # >= 95
    GOOD = "Good"             # 80 – 94
    POOR = "Poor"             # < 80

    @staticmethod
    def from_score(score: float) -> str:
        if score >= 95.0:
            return ConfidenceTier.EXCELLENT
        if score >= 80.0:
            return ConfidenceTier.GOOD
        return ConfidenceTier.POOR


class DocumentHealth:
    EXCELLENT = "Excellent"
    GOOD = "Good"
    AVERAGE = "Average"
    POOR = "Poor"


class DocumentTypes:
    AADHAAR_OFFLINE_ZIP = "Offline Aadhaar e-KYC ZIP"
    AADHAAR_CARD = "Aadhaar Card"
    INCOME_CERTIFICATE = "Income Certificate"
    CASTE_CERTIFICATE = "Caste Certificate"
    RATION_CARD = "Ration Card"
    DISABILITY_CERTIFICATE = "Disability Certificate"
    PASSPORT = "Passport"
    PAN = "PAN"
    DRIVING_LICENSE = "Driving Licence"
    VOTER_ID = "Voter ID"
    BIRTH_CERTIFICATE = "Birth Certificate"
    UNKNOWN = "Unknown Document"


# ── Backward-compatible alias ─────────────────────────────────────────────
# Legacy code imports ``VerificationStatus`` – keep this alias so that
# verification_orchestrator.py and the verifier modules continue to work.
class VerificationStatus:
    UPLOADED = DocumentStatus.UPLOADED
    VALIDATING = DocumentStatus.PROCESSING
    CLASSIFYING = DocumentStatus.PROCESSING
    VERIFYING = DocumentStatus.PROCESSING
    EXTRACTING = DocumentStatus.PROCESSING
    SAVING = DocumentStatus.PROCESSING
    VERIFIED = DocumentStatus.ACCEPTED
    OCR_VERIFIED = DocumentStatus.ACCEPTED
    FAILED = DocumentStatus.REJECTED
    REJECTED = DocumentStatus.REJECTED

