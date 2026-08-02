import io
import os
import unittest

from vault.document_manager import DocumentManager


class DummyFileStorage:
    def __init__(self, filename, content, content_type=None):
        self.filename = filename
        self._content = content
        self.content_type = content_type
        self.mimetype = content_type
        self._position = 0

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self._position = offset
        elif whence == os.SEEK_CUR:
            self._position += offset
        elif whence == os.SEEK_END:
            self._position = len(self._content) + offset
        return self._position

    def tell(self):
        return self._position

    def read(self, size=-1):
        if size < 0:
            size = len(self._content) - self._position
        data = self._content[self._position:self._position + size]
        self._position += len(data)
        return data

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self._content)


class TestDocumentUploadValidation(unittest.TestCase):
    def setUp(self):
        self.manager = DocumentManager()

    def test_validate_jpeg_mime_alias(self):
        file_storage = DummyFileStorage('test.jpg', b'\xFF\xD8\xFF\xE0', content_type='image/jpg')
        valid, message, ext, pages = self.manager._validate_upload(file_storage)
        self.assertTrue(valid)
        self.assertEqual(message, 'OK')
        self.assertEqual(ext, '.jpg')

    def test_validate_png(self):
        file_storage = DummyFileStorage('test.png', b'\x89PNG\r\n\x1a\n', content_type='image/png')
        valid, message, ext, pages = self.manager._validate_upload(file_storage)
        self.assertTrue(valid)
        self.assertEqual(message, 'OK')
        self.assertEqual(ext, '.png')

    def test_validate_pdf(self):
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Hello) Tj\nET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000061 00000 n \n0000000115 00000 n \n0000000249 00000 n \n0000000323 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n383\n%%EOF\n"
        file_storage = DummyFileStorage('test.pdf', pdf_bytes, content_type='application/pdf')
        valid, message, ext, pages = self.manager._validate_upload(file_storage)
        self.assertTrue(valid)
        self.assertEqual(message, 'OK')
        self.assertEqual(ext, '.pdf')

    def test_fail_unsupported_extension(self):
        file_storage = DummyFileStorage('test.exe', b'MZ', content_type='application/x-msdownload')
        valid, message, ext, pages = self.manager._validate_upload(file_storage)
        self.assertFalse(valid)
        self.assertEqual(message, 'Unsupported extension: .exe')

    def test_fail_unsupported_mime(self):
        file_storage = DummyFileStorage('test.jpg', b'\xFF\xD8\xFF\xE0', content_type='application/octet-stream')
        valid, message, ext, pages = self.manager._validate_upload(file_storage)
        self.assertFalse(valid)
        self.assertEqual(message, 'Unsupported MIME type: application/octet-stream')

    def test_fail_empty_file(self):
        file_storage = DummyFileStorage('test.jpg', b'', content_type='image/jpeg')
        valid, message, ext, pages = self.manager._validate_upload(file_storage)
        self.assertFalse(valid)
        self.assertEqual(message, 'Empty uploaded file')


if __name__ == '__main__':
    unittest.main()
