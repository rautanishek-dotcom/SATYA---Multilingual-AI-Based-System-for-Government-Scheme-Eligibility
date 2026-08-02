"""
Duplicate detection and document versioning for the SATYA Document Vault.

Detection strategy (in priority order):
1. Exact SHA-256 hash match  (same file re-uploaded)
2. user_id + document_type + document_number match
3. Fuzzy match on user_id + document_type + name + dob

When a duplicate is found the caller can choose to:
- Create a new *version* of the existing document
- Replace the old version
- Cancel the upload
"""

import logging
from typing import Any, Dict, Optional, Tuple

from database import get_db
from vault.utils import VaultUtils

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detects duplicate documents and manages document versions."""

    @staticmethod
    def check(
        user_id: str,
        document_hash: str,
        document_type: str = "",
        document_number: str = "",
        owner_name: str = "",
        dob: str = "",
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Returns ``(is_duplicate, existing_doc, match_reason)``.

        ``match_reason`` is one of:
        ``"hash"``, ``"type_number"``, ``"fuzzy"``, or ``""`` (no match).
        """
        db = get_db()
        if db is None:
            return False, None, ""

        collection = db.vault_documents

        # 1. Exact hash match
        if document_hash:
            existing = collection.find_one({
                "user_id": str(user_id),
                "document_hash": document_hash,
            })
            if existing:
                existing["_id"] = str(existing["_id"])
                return True, existing, "hash"

        # 2. user_id + document_type + document_number
        if document_type and document_number:
            existing = collection.find_one({
                "user_id": str(user_id),
                "document_type": document_type,
                "metadata.document_number": document_number,
            })
            if existing:
                existing["_id"] = str(existing["_id"])
                return True, existing, "type_number"

        # 3. Fuzzy match: user_id + document_type + (name OR dob)
        if document_type and (owner_name or dob):
            candidates = list(collection.find({
                "user_id": str(user_id),
                "document_type": document_type,
            }).sort("created_at", -1).limit(5))

            for candidate in candidates:
                meta = candidate.get("metadata", {})
                # Verified data takes precedence over raw OCR metadata
                vdata = candidate.get("verified_data", meta)
                c_name = vdata.get("owner_name", "")
                c_dob = vdata.get("dob", "")

                name_sim = VaultUtils.similarity(owner_name, c_name) if owner_name and c_name else 0.0
                dob_match = (
                    VaultUtils.normalize_date(dob) == VaultUtils.normalize_date(c_dob)
                    if dob and c_dob else False
                )

                if name_sim >= 85.0 or dob_match:
                    candidate["_id"] = str(candidate["_id"])
                    return True, candidate, "fuzzy"

        return False, None, ""

    @staticmethod
    def get_version_count(user_id: str, document_type: str) -> int:
        """Count how many versions of a given document type the user has."""
        db = get_db()
        if db is None:
            return 0
        return db.vault_documents.count_documents({
            "user_id": str(user_id),
            "document_type": document_type,
        })

    @staticmethod
    def deactivate_previous_versions(user_id: str, document_type: str) -> int:
        """Mark all previous versions of the document type as inactive."""
        db = get_db()
        if db is None:
            return 0
        result = db.vault_documents.update_many(
            {"user_id": str(user_id), "document_type": document_type},
            {"$set": {"is_active": False}},
        )
        return result.modified_count
