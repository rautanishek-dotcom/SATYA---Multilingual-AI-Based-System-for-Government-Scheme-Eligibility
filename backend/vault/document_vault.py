import datetime

from bson import ObjectId

from database import get_db
from vault.audit import AuditLogger
from vault.security import SecurityManager
from vault.utils import VaultUtils


class DocumentVault:
    @staticmethod
    def _collection():
        db = get_db()
        if db is None:
            raise Exception("Database not initialized")
        return db.vault_documents

    @staticmethod
    def save_document_record(record):
        collection = DocumentVault._collection()
        now = datetime.datetime.utcnow()
        safe_record = {
            "user_id": str(record.get("user_id", "")),
            "document_name": record.get("document_name", ""),
            "document_type": record.get("document_type", ""),
            "document_label": record.get("document_label", ""),
            "file_type": record.get("file_type", ""),
            "file_size": int(record.get("file_size", 0) or 0),
            "storage_path": record.get("storage_path", ""),
            "thumbnail_path": record.get("thumbnail_path", ""),
            "document_hash": record.get("document_hash", ""),
            "version": int(record.get("version", 1)),
            "is_active": bool(record.get("is_active", True)),
            "is_expired": bool(record.get("is_expired", False)),

            # Separated statuses
            "document_status": record.get("document_status", "Awaiting Review"),
            "identity_status": record.get("identity_status", "Unverified"),
            "verification_status": record.get("verification_status", "Awaiting Review"),

            # Immutable OCR data
            "ocr_text": record.get("ocr_text", ""),
            "ocr_engine": record.get("ocr_engine", ""),
            "ocr_data": VaultUtils.to_serializable(record.get("ocr_data", {})),

            # User-correctable verified data
            "verified_data": VaultUtils.to_serializable(record.get("verified_data", {})),
            "metadata": VaultUtils.to_serializable(record.get("metadata", {})),

            # Confidence
            "confidence": float(record.get("confidence", 0) or 0),
            "confidence_tier": record.get("confidence_tier", ""),
            "field_confidence": VaultUtils.to_serializable(record.get("field_confidence", {})),

            # Processing metrics
            "processing_time": float(record.get("processing_time", 0) or 0),
            "stage_timings": VaultUtils.to_serializable(record.get("stage_timings", {})),

            # Supplementary
            "quality": VaultUtils.to_serializable(record.get("quality", {})),
            "quality_score": float(record.get("quality_score", 0) or 0),
            "qr": VaultUtils.to_serializable(record.get("qr", {})),
            "classification": VaultUtils.to_serializable(record.get("classification", {})),
            "search_index": record.get("search_index", ""),
            "masked_fields": VaultUtils.to_serializable(record.get("masked_fields", {})),
            "sealed_payload": SecurityManager.seal_json(record.get("sealed_payload", {})),

            # Timestamps
            "created_at": record.get("uploaded_at", now),
            "updated_at": record.get("updated_at", now),
            "review_timestamp": record.get("review_timestamp"),
            "verification_timestamp": record.get("verification_timestamp"),
            "audit_history": record.get("audit_history", []),
            "stored_encrypted": True,
        }
        result = collection.insert_one(safe_record)
        AuditLogger.record(
            "vault_document_saved",
            record.get("user_id"),
            {
                "document_id": str(result.inserted_id),
                "document_type": safe_record["document_type"],
                "document_name": safe_record["document_name"],
            },
        )
        return str(result.inserted_id)

    @staticmethod
    def save_verification_metadata(metadata):
        collection = DocumentVault._collection()
        document_id = str(metadata.get("verification_id") or ObjectId())
        safe_record = {
            "user_id": str(metadata.get("user_id")),
            "verification_id": document_id,
            "document_hash": metadata.get("document_hash"),
            "document_type": metadata.get("document_type"),
            "document_label": metadata.get("document_label"),
            "verification_method": metadata.get("verification_method"),
            "verification_status": metadata.get("verification_status"),
            "verified_fields": VaultUtils.to_serializable(metadata.get("verified_fields", {})),
            "confidence": float(metadata.get("confidence", 0)),
            "quality_score": float(metadata.get("quality_score", 0)),
            "identity_match_score": float(metadata.get("identity_match_score", 0)),
            "identity_match_breakdown": VaultUtils.to_serializable(metadata.get("identity_match_breakdown", {})),
            "fraud_probability": float(metadata.get("fraud_probability", 0)),
            "fraud_findings": VaultUtils.to_serializable(metadata.get("fraud_findings", [])),
            "quality_findings": VaultUtils.to_serializable(metadata.get("quality_findings", [])),
            "qr_validation": VaultUtils.to_serializable(metadata.get("qr_validation", {})),
            "signature_validation": VaultUtils.to_serializable(metadata.get("signature_validation", {})),
            "document_summary": VaultUtils.to_serializable(metadata.get("document_summary", {})),
            "missing_fields": VaultUtils.to_serializable(metadata.get("missing_fields", [])),
            "verification_logs": VaultUtils.to_serializable(metadata.get("verification_logs", [])),
            "search_index": metadata.get("search_index", ""),
            "hash": metadata.get("document_hash"),
            "expiry_date": metadata.get("expiry_date"),
            "created_at": metadata.get("created_at", datetime.datetime.utcnow()),
            "updated_at": datetime.datetime.utcnow(),
            "stored_encrypted": True,
            "sealed_payload": SecurityManager.seal_json(metadata.get("sealed_payload", {})),
        }
        result = collection.insert_one(safe_record)
        AuditLogger.record(
            "vault_document_saved",
            metadata.get("user_id"),
            {
                "document_id": str(result.inserted_id),
                "document_type": safe_record["document_type"],
                "verification_status": safe_record["verification_status"],
            },
        )
        return str(result.inserted_id)

    @staticmethod
    def update_verification_status(doc_id, status, additional_data=None):
        collection = DocumentVault._collection()
        update_fields = {
            "verification_status": status,
            "updated_at": datetime.datetime.utcnow(),
        }
        if additional_data:
            update_fields.update(additional_data)
        collection.update_one({"_id": ObjectId(doc_id)}, {"$set": update_fields})

    @staticmethod
    def get_user_vault(user_id, query=None):
        collection = DocumentVault._collection()
        filter_query = {"user_id": str(user_id)}
        if query:
            filter_query["$or"] = [
                {"search_index": {"$regex": query, "$options": "i"}},
                {"document_label": {"$regex": query, "$options": "i"}},
            ]
        docs = list(collection.find(filter_query).sort("created_at", -1))
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            doc["created_at"] = doc.get("created_at").isoformat() if doc.get("created_at") else None
            doc["updated_at"] = doc.get("updated_at").isoformat() if doc.get("updated_at") else None
            if doc.get("expiry_date") and hasattr(doc["expiry_date"], "isoformat"):
                doc["expiry_date"] = doc["expiry_date"].isoformat()
            doc.pop("sealed_payload", None)
        return docs

    @staticmethod
    def get_document_by_id(document_id, user_id=None):
        collection = DocumentVault._collection()
        query = {"_id": ObjectId(document_id)}
        if user_id is not None:
            query["user_id"] = str(user_id)
        doc = collection.find_one(query)
        if doc:
            doc["_id"] = str(doc["_id"])
            doc["created_at"] = doc.get("created_at").isoformat() if doc.get("created_at") else None
            doc["updated_at"] = doc.get("updated_at").isoformat() if doc.get("updated_at") else None
            if doc.get("expiry_date") and hasattr(doc["expiry_date"], "isoformat"):
                doc["expiry_date"] = doc["expiry_date"].isoformat()
            doc.pop("sealed_payload", None)
        return doc

    @staticmethod
    def delete_document(user_id, document_id):
        import os
        collection = DocumentVault._collection()
        doc = collection.find_one({"_id": ObjectId(document_id), "user_id": str(user_id)})
        if not doc:
            return False
            
        try:
            if doc.get("storage_path") and os.path.exists(doc["storage_path"]):
                os.remove(doc["storage_path"])
            if doc.get("thumbnail_path") and os.path.exists(doc["thumbnail_path"]):
                os.remove(doc["thumbnail_path"])
        except Exception:
            pass

        result = collection.delete_one({"_id": ObjectId(document_id), "user_id": str(user_id)})
        if result.deleted_count:
            AuditLogger.record("vault_document_deleted", user_id, {"document_id": str(document_id)})
        return result.deleted_count > 0

    @staticmethod
    def get_dashboard_stats(user_id):
        collection = DocumentVault._collection()
        pipeline = [
            {"$match": {"user_id": str(user_id)}},
            {"$group": {
                "_id": None,
                "total_documents": {"$sum": 1},
                "accepted": {"$sum": {"$cond": [{"$eq": ["$document_status", "Accepted"]}, 1, 0]}},
                "awaiting_review": {"$sum": {"$cond": [{"$eq": ["$document_status", "Awaiting Review"]}, 1, 0]}},
                "rejected": {"$sum": {"$cond": [{"$eq": ["$document_status", "Rejected"]}, 1, 0]}},
                "avg_conf": {"$avg": "$confidence"},
                "avg_processing_time": {"$avg": "$processing_time"},
            }}
        ]
        results = list(collection.aggregate(pipeline))
        if results:
            stats = results[0]
            return {
                "accepted": stats.get("accepted", 0),
                "awaiting_review": stats.get("awaiting_review", 0),
                "rejected": stats.get("rejected", 0),
                "average_confidence": round(stats.get("avg_conf", 0) or 0, 2),
                "average_processing_time": round(stats.get("avg_processing_time", 0) or 0, 2),
                "total_documents": stats.get("total_documents", 0),
                # Legacy compat
                "pending": stats.get("awaiting_review", 0),
            }
        return {
            "accepted": 0,
            "awaiting_review": 0,
            "rejected": 0,
            "average_confidence": 0,
            "average_processing_time": 0,
            "total_documents": 0,
            "pending": 0,
        }

    @staticmethod
    def purge_user_vault(user_id):
        collection = DocumentVault._collection()
        result = collection.delete_many({"user_id": str(user_id)})
        AuditLogger.record("vault_user_purged", user_id, {"deleted_count": result.deleted_count})
        return result.deleted_count

    @staticmethod
    def search_documents(user_id, query):
        return DocumentVault.get_user_vault(user_id, query=query or "")

