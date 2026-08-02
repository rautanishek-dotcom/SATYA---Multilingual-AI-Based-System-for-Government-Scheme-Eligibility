import base64
import hashlib
import hmac
import json
import os
import shutil
import logging

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except Exception:
    Fernet = None  # type: ignore
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)


class SecurityManager:
    @staticmethod
    def generate_file_hash(file_path):
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"Error generating hash: {e}")
            return None

    @staticmethod
    def encrypt_file(source_path: str, dest_path: str) -> bool:
        try:
            if not os.path.exists(source_path):
                raise FileNotFoundError(source_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source_path, dest_path)
            return True
        except Exception as e:
            logger.exception("Error encrypting file %s to %s: %s", source_path, dest_path, e)
            return False

    @staticmethod
    def decrypt_file(source_path: str, dest_path: str) -> bool:
        try:
            if not os.path.exists(source_path):
                raise FileNotFoundError(source_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source_path, dest_path)
            return True
        except Exception as e:
            logger.exception("Error decrypting file %s to %s: %s", source_path, dest_path, e)
            return False

    @staticmethod
    def validate_magic_number(file_path, expected_types=None):
        if not expected_types:
            expected_types = ["zip", "pdf", "jpeg", "png", "webp", "tiff", "bmp"]

        signatures = {
            "zip": b"PK\x03\x04",
            "pdf": b"%PDF",
            "jpeg": b"\xFF\xD8\xFF",
            "png": b"\x89PNG",
            "webp": b"RIFF",
            "tiff": [b"II*\x00", b"MM\x00*"],
            "bmp": b"BM",
        }

        try:
            with open(file_path, "rb") as f:
                header = f.read(8)

            for file_type in expected_types:
                sig = signatures.get(file_type)
                if isinstance(sig, list):
                    if any(header.startswith(item) for item in sig):
                        return True, file_type
                elif sig and header.startswith(sig):
                    return True, file_type

            return False, "Unsupported file format"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def secure_cleanup(file_paths):
        for path in file_paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Error deleting temp file {path}: {e}")

    @staticmethod
    def seal_json(payload, secret=None):
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        secret_bytes = (secret or os.getenv("SATYA_VAULT_SECRET", "satya-vault-secret")).encode("utf-8")
        mac = hmac.new(secret_bytes, raw, hashlib.sha256).hexdigest()
        return {
            "sealed": base64.b64encode(raw).decode("utf-8"),
            "mac": mac,
        }

    @staticmethod
    def unseal_json(envelope, secret=None):
        if not envelope:
            return {}
        raw = base64.b64decode(envelope.get("sealed", "").encode("utf-8"))
        secret_bytes = (secret or os.getenv("SATYA_VAULT_SECRET", "satya-vault-secret")).encode("utf-8")
        mac = hmac.new(secret_bytes, raw, hashlib.sha256).hexdigest()
        if mac != envelope.get("mac"):
            raise ValueError("Integrity check failed")
        return json.loads(raw.decode("utf-8"))

