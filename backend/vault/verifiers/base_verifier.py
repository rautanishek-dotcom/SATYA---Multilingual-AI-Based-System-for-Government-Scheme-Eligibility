from abc import ABC, abstractmethod

class BaseVerifier(ABC):
    """
    Base class for all document verifiers.
    All verifiers MUST inherit from this and implement its methods.
    """
    
    @abstractmethod
    def detect(self, file_path):
        """Detect document boundaries and relevance."""
        pass

    @abstractmethod
    def verify(self, file_path, **kwargs):
        """Core verification logic (e.g., XML signature, OCR checks)."""
        pass

    @abstractmethod
    def extract(self, file_path, **kwargs):
        """Extract verified information into a standard dictionary."""
        pass

    @abstractmethod
    def validate(self, extracted_data):
        """Validate the extracted data for completeness and correctness."""
        pass

    @abstractmethod
    def save(self, metadata, user_id):
        """Prepares the metadata for Vault DB saving."""
        pass
