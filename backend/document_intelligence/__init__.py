"""Document intelligence package for SATYA."""
from .config import SUPPORTED_DOCUMENT_TYPES, SUPPORTED_LANGUAGES, CANONICAL_FIELD_KEYS
from .classification import DocumentClassifier
from .layout import LayoutDetector
from .ocr_pipeline import OCRPipeline
from .orchestrator import DocumentIntelligenceOrchestrator
from .augmentation import apply_augmentation
from .correction import normalize_fields, normalize_field
from .field_mapping import map_to_canonical_fields, required_fields_for_document
from .qr import QREngine
