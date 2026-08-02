import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vault.document_classifier import DocumentClassifier
from vault.field_extractor import FieldExtractor


def validate_document(path: Path):
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        text = handle.read().strip()

    classification = DocumentClassifier.classify_by_text(text)
    extraction = FieldExtractor.extract_fields({"full_text": text, "words": []})
    doc_type = extraction["document_type"]

    fields = extraction.get("fields", {})
    print(f"FILE: {path.name}")
    print(f"  detected_type={doc_type}")
    print(f"  confidence={classification['confidence']:.3f}")
    print("  fields:")
    for field_name, payload in fields.items():
        if field_name == "document_type":
            continue
        print(f"    - {field_name}: {payload.get('value', '')} [{payload.get('strategy', '')}]")
    print()


if __name__ == "__main__":
    diagnostics_dir = ROOT / "temp_uploads" / "ocr_diagnostics"
    if not diagnostics_dir.exists():
        raise SystemExit(f"Diagnostics directory not found: {diagnostics_dir}")

    for path in sorted(diagnostics_dir.glob("*.txt")):
        validate_document(path)
