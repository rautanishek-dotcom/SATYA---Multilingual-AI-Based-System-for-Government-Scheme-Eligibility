import os
import unittest

from vault.document_classifier import DocumentClassifier
from vault.field_extractor import FieldExtractor


class OCRClassificationExtractionTests(unittest.TestCase):
    def _read_diag(self, name):
        base = os.path.dirname(__file__)
        path = os.path.join(base, "..", "temp_uploads", "ocr_diagnostics", name)
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read().strip()

    def test_pan_classification_from_ocr_text(self):
        text = self._read_diag("diag_ed7770f3_ocr_text.txt")
        result = DocumentClassifier.classify_by_text(text)
        self.assertEqual(result["document_type"], "pan")
        self.assertTrue(result["supported"])
        self.assertGreaterEqual(result["confidence"], 0.7)

    def test_passport_classification_from_ocr_text(self):
        text = self._read_diag("diag_e25ce35d_ocr_text.txt")
        result = DocumentClassifier.classify_by_text(text)
        self.assertEqual(result["document_type"], "passport")
        self.assertTrue(result["supported"])
        self.assertGreaterEqual(result["confidence"], 0.7)

    def test_field_extractor_recovers_pan_number_and_name(self):
        text = self._read_diag("diag_ed7770f3_ocr_text.txt")
        result = FieldExtractor.extract_fields({"full_text": text, "words": []})
        self.assertEqual(result["document_type"], "pan")
        self.assertEqual(result["fields"]["document_number"]["value"], "ABCDE1234F")
        self.assertIn("ABHISHEK", result["fields"]["name"]["value"].upper())


if __name__ == "__main__":
    unittest.main()
