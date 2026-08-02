from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class FieldAnnotation:
    field_name: str
    value: str
    normalized_value: str = ""
    confidence: float = 0.0
    bbox: List[float] = field(default_factory=list)
    source: str = ""
    page_number: int = 1
    field_type: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "normalized_value": self.normalized_value,
            "confidence": round(float(self.confidence), 2),
            "bbox": self.bbox,
            "source": self.source,
            "page_number": self.page_number,
            "field_type": self.field_type,
            "notes": self.notes,
        }


@dataclass
class LayoutBlock:
    block_id: str
    label: str
    bbox: List[float]
    text: str = ""
    confidence: float = 0.0
    page_number: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "label": self.label,
            "bbox": self.bbox,
            "text": self.text,
            "confidence": round(float(self.confidence), 2),
            "page_number": self.page_number,
        }


@dataclass
class PageSample:
    page_number: int
    image_path: str
    width: int
    height: int
    raw_text: str
    layout_blocks: List[LayoutBlock] = field(default_factory=list)
    ocr_candidates: List[Dict[str, Any]] = field(default_factory=list)
    qr_data: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "image_path": self.image_path,
            "width": self.width,
            "height": self.height,
            "raw_text": self.raw_text,
            "layout_blocks": [block.to_dict() for block in self.layout_blocks],
            "ocr_candidates": self.ocr_candidates,
            "qr_data": self.qr_data,
        }


@dataclass
class DocumentSample:
    document_type: str
    language: str
    image_path: str
    bounding_boxes: List[List[float]]
    fields: Dict[str, FieldAnnotation]
    pages: List[PageSample] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type,
            "language": self.language,
            "image_path": self.image_path,
            "bounding_boxes": self.bounding_boxes,
            "fields": {name: field.to_dict() for name, field in self.fields.items()},
            "pages": [page.to_dict() for page in self.pages],
            "metadata": self.metadata,
        }


def annotation_spec() -> Dict[str, Any]:
    return {
        "document_type": "string",
        "language": "string",
        "image_path": "string",
        "bounding_boxes": "array of [x0, y0, x1, y1]",
        "fields": {
            "full_name": {"value": "string", "confidence": "float", "bbox": "[x0, y0, x1, y1]", "source": "string"},
            "dob": {"value": "string", "confidence": "float"},
            "gender": {"value": "string", "confidence": "float"},
            "address": {"value": "string", "confidence": "float"},
            "aadhaar_number": {"value": "string", "confidence": "float"},
            "pan_number": {"value": "string", "confidence": "float"},
            "issue_date": {"value": "string", "confidence": "float"},
            "expiry_date": {"value": "string", "confidence": "float"},
            "district": {"value": "string", "confidence": "float"},
            "state": {"value": "string", "confidence": "float"},
            "pin_code": {"value": "string", "confidence": "float"},
        },
    }
