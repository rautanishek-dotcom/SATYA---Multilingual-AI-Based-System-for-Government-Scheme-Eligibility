from vault.verifiers.base_verifier import BaseVerifier
from vault.verification_status import VerificationStatus, DocumentTypes

class DetectOnlyVerifier(BaseVerifier):
    def __init__(self, doc_type):
        self.doc_type = doc_type
        
    def detect(self, file_path):
        return True

    def verify(self, file_path, **kwargs):
        # Stub for detect only
        return {"status": VerificationStatus.VERIFYING, "raw_text": "Detected"}

    def extract(self, file_path, **kwargs):
        return {}

    def validate(self, extracted_data):
        return True, VerificationStatus.OCR_VERIFIED, 60.0

    def save(self, metadata, user_id):
        metadata['document_type'] = self.doc_type
        metadata['verification_method'] = "DETECT_ONLY"
        return metadata

class PassportVerifier(DetectOnlyVerifier):
    def __init__(self):
        super().__init__(DocumentTypes.PASSPORT)

class PanVerifier(DetectOnlyVerifier):
    def __init__(self):
        super().__init__(DocumentTypes.PAN)

class DrivingLicenseVerifier(DetectOnlyVerifier):
    def __init__(self):
        super().__init__(DocumentTypes.DRIVING_LICENSE)
