import unittest

from vault.utils import VaultUtils


class TestVaultUtilsImport(unittest.TestCase):
    def test_vault_utils_import(self):
        self.assertIsNotNone(VaultUtils)
        self.assertTrue(hasattr(VaultUtils, 'normalize_text'))
        self.assertTrue(hasattr(VaultUtils, 'mask_aadhaar'))
        self.assertTrue(hasattr(VaultUtils, 'validate_file'))


if __name__ == '__main__':
    unittest.main()
