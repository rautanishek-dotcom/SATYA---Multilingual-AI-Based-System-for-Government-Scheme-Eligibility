import os
import sys
import unittest
from unittest.mock import patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from vault.verifiers.caste_certificate import CasteCertificateVerifier, normalize_caste_category


class CasteCertificateExtractionTests(unittest.TestCase):
    def setUp(self):
        self.verifier = CasteCertificateVerifier()

    def test_normalizes_only_supported_categories(self):
        expected = {
            "General Category": "General",
            "OBC": "OBC",
            "Other Backward Class": "OBC",
            "Other Backward Classes": "OBC",
            "Scheduled Caste": "SC",
            "Scheduled Castes": "SC",
            "Scheduled Tribe": "ST",
            "Scheduled Tribes": "ST",
            "O.B.C.": "OBC",
            "0BC": "OBC",
            "S. C.": "SC",
            "S T": "ST",
            "Unreserved Category": "General",
        }
        for source, category in expected.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_caste_category(source), category)

    def test_uses_category_context_not_community_name(self):
        extracted = self.verifier.extract("", raw_text="Community: XYZ\nCategory: Other Backward Class\nCertificate No: OBC/2026/1234")
        self.assertEqual(extracted["category"], "OBC")
        self.assertGreaterEqual(extracted["confidence"], 70.0)

    def test_unknown_community_and_false_positive_words_stay_unverified(self):
        for source in ("Community: XYZ", "School State Student Section", "SC/ST coaching section"):
            with self.subTest(source=source):
                extracted = self.verifier.extract("", raw_text=source)
                self.assertIsNone(extracted["category"])
                self.assertEqual(extracted["confidence"], 0.0)

    def test_detects_ocr_variants_when_they_are_in_a_category_field(self):
        samples = {
            "Caste Category: O.B.C.": "OBC",
            "Social Category - 0BC": "OBC",
            "Class: S. C.": "SC",
            "Reservation Category: S T": "ST",
            "Category: Unreserved": "General",
            "Category: General": "General",
            "Category: GEN": "General",
            "Belongs to Scheduled Caste": "SC",
            "Belongs to Scheduled Tribe": "ST",
            "Belongs to Other Backward Class": "OBC",
            "Class: Social and Educationally Backward Class": "OBC",
            "Caste: SEBC": "OBC",
        }
        for source, category in samples.items():
            with self.subTest(source=source):
                extracted = self.verifier.extract("", raw_text=source)
                self.assertEqual(extracted["category"], category)
                self.assertGreaterEqual(extracted["confidence"], 70.0)

    def test_reprocesses_the_original_certificate_when_saved_ocr_is_empty(self):
        with patch("vault.verifiers.caste_certificate._caste_ocr_from_file", return_value="Caste Category: Scheduled Tribe"):
            extracted = self.verifier.extract("original-certificate.png", raw_text="")
        self.assertEqual(extracted["category"], "ST")
        self.assertGreaterEqual(extracted["confidence"], 70.0)


if __name__ == "__main__":
    unittest.main()
