import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app


class TestVaultUploadRoute(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_upload_missing_user_id_returns_400(self):
        response = self.client.post(
            "/api/vault/upload",
            content_type="multipart/form-data",
            data={}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json().get("error"), "Missing file or user_id")

    def test_documents_list_missing_user_id_returns_400(self):
        response = self.client.get("/api/vault/documents")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json().get("error"), "user_id required")


if __name__ == "__main__":
    unittest.main()
