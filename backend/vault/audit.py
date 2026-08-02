"""
Audit logging for the SATYA Document Vault.

Every important event (upload, OCR, review, correction, acceptance,
rejection, eligibility check, download, delete) is persisted to
the ``vault_audit_logs`` MongoDB collection with full context.
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from database import get_db

logger = logging.getLogger(__name__)


class AuditLogger:
    """Immutable, append-only audit log for document vault events."""

    @staticmethod
    def _collection():
        db = get_db()
        if db is None:
            return None
        return db.vault_audit_logs

    # ── Generic event recorder ────────────────────────────────────────────

    @staticmethod
    def record(
        action: str,
        user_id: Optional[str],
        payload: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> Optional[str]:
        """Insert a single audit event. Returns the inserted event ID."""
        collection = AuditLogger._collection()
        if collection is None:
            logger.warning("[AUDIT] MongoDB unavailable – event '%s' dropped", action)
            return None

        event = {
            "action": action,
            "user_id": str(user_id) if user_id is not None else None,
            "document_id": str(document_id) if document_id else None,
            "timestamp": datetime.datetime.utcnow(),
            "payload": payload or {},
        }
        try:
            result = collection.insert_one(event)
            return str(result.inserted_id)
        except Exception as exc:
            logger.error("[AUDIT] Failed to write event '%s': %s", action, exc)
            return None

    # ── Specialised helpers ───────────────────────────────────────────────

    @staticmethod
    def record_correction(
        user_id: str,
        document_id: str,
        field_name: str,
        ocr_value: str,
        corrected_value: str,
        reason: str = "",
    ) -> Optional[str]:
        """Record a single field correction made during user review."""
        return AuditLogger.record(
            action="field_correction",
            user_id=user_id,
            document_id=document_id,
            payload={
                "field": field_name,
                "ocr_value": ocr_value,
                "corrected_value": corrected_value,
                "reason": reason,
                "edited_at": datetime.datetime.utcnow().isoformat(),
            },
        )

    @staticmethod
    def record_review(
        user_id: str,
        document_id: str,
        decision: str,
        corrections: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """Record the user's review decision (confirm / edit / re-upload)."""
        return AuditLogger.record(
            action="user_review",
            user_id=user_id,
            document_id=document_id,
            payload={
                "decision": decision,
                "corrections": corrections or [],
                "reviewed_at": datetime.datetime.utcnow().isoformat(),
            },
        )

    @staticmethod
    def get_document_history(document_id: str) -> List[Dict[str, Any]]:
        """Retrieve the full audit trail for a specific document."""
        collection = AuditLogger._collection()
        if collection is None:
            return []
        try:
            events = list(
                collection.find({"document_id": str(document_id)})
                .sort("timestamp", 1)
            )
            for event in events:
                event["_id"] = str(event["_id"])
                if event.get("timestamp"):
                    event["timestamp"] = event["timestamp"].isoformat()
            return events
        except Exception as exc:
            logger.error("[AUDIT] Failed to retrieve history for %s: %s", document_id, exc)
            return []
