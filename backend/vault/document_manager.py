import datetime
import io
import os
import re
import shutil
import tempfile
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from vault.audit import AuditLogger
from vault.document_classifier import DocumentClassifier
from vault.document_vault import DocumentVault
from vault.ocr_utils import (
    decode_qr_and_barcode,
    extract_structured_document_fields,
    multi_ocr_candidates,
    ocr_document,
    quick_document_hint,
)
from vault.quality_detector import QualityDetector
from vault.security import SecurityManager
from vault.utils import VaultUtils
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

# Store for safe error IDs (cleared periodically in production)
_ERROR_STORE: Dict[str, str] = {}

def _make_error_id(detail: str) -> str:
    """Stores full error detail keyed by a short ID. Returns the ID for the frontend."""
    eid = "ERR-" + uuid.uuid4().hex[:8].upper()
    _ERROR_STORE[eid] = detail
    logger.error("[%s] %s", eid, detail)
    return eid

def _stage(name: str):
    """Context manager that logs stage timing and success/failure."""
    import contextlib
    @contextlib.contextmanager
    def _ctx():
        t0 = time.time()
        logger.info("[STAGE:%s] START", name)
        try:
            yield
            logger.info("[STAGE:%s] END  OK - %.3fs", name, time.time() - t0)
        except Exception as exc:
            logger.error("[STAGE:%s] END  FAIL - %.3fs - %s", name, time.time() - t0, exc)
            raise
    return _ctx()


try:
    import fitz
    PYMUPDF_AVAILABLE = True
except Exception:
    fitz = None  # type: ignore
    PYMUPDF_AVAILABLE = False

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
EXTENSION_TO_MAGIC_TYPE = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".pdf": "pdf",
}
MAX_UPLOAD_MB = 20
MAX_PDF_PAGES = 20
STORAGE_ROOT = "vault_storage"
THUMBNAIL_ROOT = "vault_thumbnails"
TEMP_ROOT = "temp_uploads"


class DocumentManager:
    def __init__(self):
        os.makedirs(STORAGE_ROOT, exist_ok=True)
        os.makedirs(THUMBNAIL_ROOT, exist_ok=True)
        os.makedirs(TEMP_ROOT, exist_ok=True)
        self.classifier = DocumentClassifier()

    def _validate_upload(self, file_storage: Any) -> Tuple[bool, str, Optional[str], Optional[int]]:
        if not file_storage:
            logger.warning("Upload validation failed: no file_storage received")
            return False, "No file was received.", None, None

        filename = getattr(file_storage, "filename", "") or ""
        ext = os.path.splitext(filename.lower())[1]
        content_type = getattr(file_storage, "content_type", None) or getattr(file_storage, "mimetype", None)
        normalized_content_type = None
        if content_type:
            normalized_content_type = content_type.lower()
            if normalized_content_type == "image/jpg":
                normalized_content_type = "image/jpeg"

        logger.info(
            "Validating upload: filename=%s, extension=%s, content_type=%s",
            filename,
            ext,
            normalized_content_type,
        )

        if ext not in SUPPORTED_EXTENSIONS:
            logger.warning("Upload validation failed: unsupported extension %s", ext)
            return False, f"Unsupported extension: {ext}", ext, None

        file_storage.seek(0, os.SEEK_END)
        size_bytes = file_storage.tell()
        file_storage.seek(0)
        if size_bytes == 0:
            logger.warning("Upload validation failed: empty uploaded file %s", filename)
            return False, "Empty uploaded file", ext, 0
        if size_bytes > MAX_UPLOAD_MB * 1024 * 1024:
            logger.warning("Upload validation failed: file too large %s (%d bytes)", filename, size_bytes)
            return False, f"File exceeds the maximum allowed size of {MAX_UPLOAD_MB} MB.", ext, size_bytes

        if normalized_content_type and normalized_content_type not in SUPPORTED_MIME_TYPES:
            logger.warning("Upload validation failed: unsupported MIME type %s for %s", normalized_content_type, filename)
            return False, f"Unsupported MIME type: {normalized_content_type}", ext, size_bytes

        temp_path = self._save_temp_file(file_storage, filename)
        try:
            actual_size = os.path.getsize(temp_path)
            if actual_size == 0:
                logger.warning("Upload validation failed: empty temp file %s", temp_path)
                return False, "Empty uploaded file", ext, 0

            expected_magic_types = [EXTENSION_TO_MAGIC_TYPE.get(ext, ext.strip("."))]
            valid_magic, magic_type = SecurityManager.validate_magic_number(temp_path, expected_types=expected_magic_types)
            if not valid_magic:
                logger.warning(
                    "Upload validation failed: unsupported file signature for %s. expected=%s, detected=%s",
                    filename,
                    expected_magic_types,
                    magic_type,
                )
                return False, f"Unsupported MIME type: {content_type or magic_type}", ext, size_bytes

            if ext == ".pdf":
                if not PYMUPDF_AVAILABLE:
                    logger.warning("Upload validation failed: PyMuPDF unavailable for PDF processing")
                    return False, "PDF processing is not available because PyMuPDF is not installed.", ext, size_bytes
                page_count = self._count_pdf_pages(temp_path)
                if page_count is None:
                    logger.warning("Upload validation failed: corrupted PDF %s", filename)
                    return False, "Corrupted PDF", ext, size_bytes
                if page_count > MAX_PDF_PAGES:
                    logger.warning("Upload validation failed: PDF page count too high %s (%d pages)", filename, page_count)
                    return False, f"PDF exceeds the maximum allowed page limit of {MAX_PDF_PAGES}.", ext, size_bytes
            else:
                page_count = 1

            logger.info("Upload validation succeeded: %s, mime=%s, size=%d", filename, content_type, size_bytes)
            return True, "OK", ext, page_count
        finally:
            SecurityManager.secure_cleanup([temp_path])

    def _save_temp_file(self, file_storage: Any, filename: str) -> str:
        temp_name = f"upload_{uuid.uuid4().hex}_{Path(filename).name}"
        temp_path = os.path.join(TEMP_ROOT, temp_name)
        with open(temp_path, "wb") as dest:
            file_storage.seek(0)
            shutil.copyfileobj(file_storage, dest)
        try:
            file_storage.seek(0)
        except Exception:
            pass
        return temp_path

    def _count_pdf_pages(self, file_path: str) -> Optional[int]:
        if not PYMUPDF_AVAILABLE:
            return None
        try:
            doc = fitz.open(file_path)
            page_count = doc.page_count
            doc.close()
            return page_count
        except Exception:
            return None

    def _convert_pdf_to_images(self, file_path: str) -> List[str]:
        if not PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF is required to convert PDF pages to images.")

        images: List[str] = []
        doc = fitz.open(file_path)
        try:
            for page_index in range(min(doc.page_count, MAX_PDF_PAGES)):
                page = doc[page_index]
                pix = page.get_pixmap(dpi=300)
                image_name = f"pdf_page_{page_index + 1}_{uuid.uuid4().hex}.png"
                image_path = os.path.join(TEMP_ROOT, image_name)
                pix.save(image_path)
                images.append(image_path)
        finally:
            doc.close()
        return images

    def _preprocess_image(self, image_path: str) -> Optional[str]:
        image = cv2.imread(image_path)
        if image is None:
            return None
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
            gray = cv2.medianBlur(gray, 3)
            gray = cv2.equalizeHist(gray)

            processed_path = os.path.join(TEMP_ROOT, f"preprocessed_{uuid.uuid4().hex}.png")
            cv2.imwrite(processed_path, gray)
            return processed_path
        except Exception:
            return image_path

    def _generate_thumbnail(self, source_path: str) -> str:
        image = cv2.imread(source_path)
        if image is None:
            return ""
        try:
            h, w = image.shape[:2]
            scale = min(250 / max(w, 1), 250 / max(h, 1), 1.0)
            thumbnail = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            thumb_path = os.path.join(THUMBNAIL_ROOT, f"thumb_{uuid.uuid4().hex}.png")
            cv2.imwrite(thumb_path, thumbnail)
            return thumb_path
        except Exception:
            return ""

    def _run_ocr(self, image_paths: List[str]) -> Tuple[str, List[Dict[str, Any]], float]:
        text_parts = []
        candidates: List[Dict[str, Any]] = []
        confidences: List[float] = []

        for image_path in image_paths:
            ocr_result = ocr_document(image_path, lang_hints=["eng"])
            if not ocr_result:
                continue
            candidate = ocr_result.get("best")
            if candidate and candidate.text:
                text_parts.append(candidate.text)
                confidences.append(float(candidate.confidence or 0.0))
            for item in ocr_result.get("candidates", []):
                if getattr(item, "text", ""):
                    text_parts.append(item.text)
            candidates.extend([
                {
                    "engine": item.engine,
                    "lang": item.lang,
                    "text": item.text,
                    "confidence": item.confidence,
                }
                for item in ocr_result.get("candidates", [])
            ])

        if not text_parts and not candidates:
            candidates = multi_ocr_candidates(image_paths[0]) if image_paths else []

        full_text = "\n".join([text for text in text_parts if text]).strip()
        average_confidence = float(sum(confidences) / max(len(confidences), 1)) if confidences else 0.0
        return full_text, candidates, average_confidence

    def _format_document_name(self, original_filename: str, classification: Dict[str, Any]) -> str:
        if original_filename:
            return original_filename
        return classification.get("document_label", "Vault Document")

    def _mask_sensitive_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        masked = {}
        for key, value in fields.items():
            if not isinstance(value, dict):
                masked[key] = value
                continue
            raw = str(value.get("value", ""))
            if key in {"masked_aadhaar", "aadhaar_number", "identity_number"}:
                masked[key] = {**value, "value": VaultUtils.mask_aadhaar(raw)}
            elif key == "pan_number":
                masked[key] = {**value, "value": VaultUtils.mask_number(raw, visible=4)}
            elif key == "passport_number":
                masked[key] = {**value, "value": VaultUtils.mask_number(raw, visible=4)}
            else:
                masked[key] = value
        return masked

    def _build_search_index(self, metadata: Dict[str, Any], ocr_text: str) -> str:
        parts = [
            str(metadata.get("document_name", "")),
            str(metadata.get("document_type", "")),
            str(metadata.get("document_label", "")),
            str(metadata.get("metadata", {}).get("owner_name", "")),
            str(metadata.get("metadata", {}).get("document_number", "")),
            str(metadata.get("metadata", {}).get("dob", "")),
            ocr_text,
        ]
        return VaultUtils.normalize_text(" ".join(parts))

    def process_upload(self, user_id: str, file_storage: Any) -> Dict[str, Any]:
        upload_start = time.time()
        filename = getattr(file_storage, "filename", "") or ""
        logger.info("[UPLOAD] START user_id=%s filename=%s", user_id, filename)
        timings: Dict[str, float] = {}

        if not user_id or not filename:
            return {"status": "FAILED", "error": "Missing required upload parameters.", "error_code": "ERR-MISSING-PARAMS"}

        # ── Stage 1: Validation ──────────────────────────────────────────────────
        t0 = time.time()
        logger.info("[STAGE:VALIDATION] START")
        valid, message, ext, page_count = self._validate_upload(file_storage)
        timings["validation"] = round(time.time() - t0, 3)
        logger.info("[STAGE:VALIDATION] END %.3fs valid=%s", timings["validation"], valid)
        if not valid:
            AuditLogger.record("vault_upload_validation_failed", user_id, {"filename": filename, "reason": message})
            return {"status": "FAILED", "message": message, "error": message}

        # ── Stage 2: Save temp file ──────────────────────────────────────────────
        t0 = time.time()
        temp_path = self._save_temp_file(file_storage, filename)
        timings["storage"] = round(time.time() - t0, 3)

        # ── Stage 2b: SHA-256 Hash ───────────────────────────────────────────────
        document_hash = SecurityManager.generate_file_hash(temp_path)

        image_paths: List[str] = []
        processed_paths: List[str] = []
        try:
            # ── Stage 3: PDF/Image Conversion ────────────────────────────────────
            t0 = time.time()
            is_digital_pdf = False
            raw_text = ""
            ocr_candidates = []
            ocr_confidence = 0.0
            hint_text = ""
            ocr_engine = "none"

            if ext == ".pdf":
                # Try getting text directly first
                pdf_text = ""
                try:
                    from vault.ocr_utils import _extract_pdf_text
                    pdf_text = _extract_pdf_text(temp_path)
                except Exception:
                    pass
                
                if pdf_text and len(pdf_text.strip()) > 20:
                    is_digital_pdf = True
                    raw_text = pdf_text
                    ocr_candidates = [{"engine": "pdf-text", "lang": "text", "text": pdf_text, "confidence": 96.0}]
                    ocr_confidence = 96.0
                    ocr_engine = "pdf-text"
                    hint_text = quick_document_hint(temp_path)
                    
                    # Convert only the first page for thumbnail/preview if it's a digital PDF
                    image_paths = self._convert_pdf_to_images(temp_path)
                    processed_paths = [image_paths[0]] if image_paths else [temp_path]
                else:
                    image_paths = self._convert_pdf_to_images(temp_path)
            else:
                image_paths = [temp_path]
            timings["conversion"] = round(time.time() - t0, 3)

            # ── Stage 4: Preprocessing (Skip if Digital PDF) ────────────────────
            t0 = time.time()
            if not is_digital_pdf:
                for page_image in image_paths:
                    processed = self._preprocess_image(page_image)
                    processed_paths.append(processed or page_image)
            timings["preprocessing"] = round(time.time() - t0, 3)

            if not processed_paths:
                eid = _make_error_id(f"Preprocessing produced no output for {filename}")
                return {"status": "FAILED", "message": "Image could not be processed.", "error_code": eid}

            primary_path = processed_paths[0]

            # ── Stage 5: OCR (Skip if Digital PDF) ───────────────────────────────
            if not is_digital_pdf:
                t0 = time.time()
                hint_text = quick_document_hint(primary_path)
                raw_text, ocr_candidates, ocr_confidence = self._run_ocr(processed_paths)
                timings["ocr"] = round(time.time() - t0, 3)
                ocr_engine = ocr_candidates[0].get("engine", "unknown") if ocr_candidates else "none"
                logger.info("[STAGE:OCR] END %.3fs engine=%s confidence=%.1f%%", timings["ocr"], ocr_engine, ocr_confidence)

            # ── Stage 6: QR Decode ───────────────────────────────────────────────
            t0 = time.time()
            qr_result = decode_qr_and_barcode(primary_path)
            qr_payload = " ".join(qr_result.get("qr_data", []) + qr_result.get("barcode_data", []))
            timings["qr"] = round(time.time() - t0, 3)

            # ── Stage 7: Classification ──────────────────────────────────────────
            t0 = time.time()
            classification = self.classifier.classify(filename, hint_text=f"{hint_text} {raw_text}")
            timings["classification"] = round(time.time() - t0, 3)

            if not classification.get("supported"):
                classification["document_type"] = classification.get("document_type", "other_document")
                classification["document_label"] = classification.get("document_label", "Other Document")

            # ── Stage 8: Metadata Extraction ─────────────────────────────────────
            t0 = time.time()
            extracted = extract_structured_document_fields(
                primary_path,
                document_type=classification.get("document_type"),
                user_name=None,
                hint_text=hint_text,
                qr_payload=qr_payload,
            )
            structured_fields = extracted.get("fields", {})
            # Normalize: ensure every value is a dict with value/confidence
            structured_fields = {
                k: v if isinstance(v, dict) else {"value": str(v), "confidence": 0.0, "source": "raw"}
                for k, v in structured_fields.items()
            }
            timings["metadata"] = round(time.time() - t0, 3)

            # ── Build per-field confidence map ───────────────────────────────────
            field_confidence = {}
            for field_key, field_val in structured_fields.items():
                if isinstance(field_val, dict) and field_val.get("value"):
                    field_confidence[field_key] = round(float(field_val.get("confidence", 0.0)), 1)

            # ── Calculate VERIFICATION confidence from identity fields only ──────
            name_conf = field_confidence.get("name", 0.0)
            dob_conf = field_confidence.get("dob", 0.0)
            gender_conf = field_confidence.get("gender", 0.0)
            # Weighted: name 40%, dob 35%, gender 25%
            verification_confidence = round(
                name_conf * 0.40 + dob_conf * 0.35 + gender_conf * 0.25, 2
            )
            # Map to frontend-friendly keys
            field_confidence["owner_name"] = name_conf
            field_confidence["verification"] = verification_confidence

            # ── Build ocr_data (immutable) ───────────────────────────────────────
            ocr_data = {
                # Name: Aadhaar stores as "name", generic/PAN also "name"
                "owner_name": (
                    structured_fields.get("name", {}).get("value", "")
                    or structured_fields.get("owner_name", {}).get("value", "")
                    or structured_fields.get("full_name", {}).get("value", "")
                ),
                # Document number: Aadhaar uses "document_number", generic uses "identity_number"
                "document_number": (
                    structured_fields.get("document_number", {}).get("value", "")
                    or structured_fields.get("identity_number", {}).get("value", "")
                    or structured_fields.get("masked_aadhaar", {}).get("value", "")
                    or structured_fields.get("aadhaar_reference_id", {}).get("value", "")
                ),
                "dob": (
                    structured_fields.get("dob", {}).get("value", "")
                    or structured_fields.get("date_of_birth", {}).get("value", "")
                ),
                "gender": structured_fields.get("gender", {}).get("value", ""),
                "issue_date": structured_fields.get("issue_date", {}).get("value", ""),
                "expiry_date": structured_fields.get("expiry_date", {}).get("value", ""),
                "address": structured_fields.get("address", {}).get("value", ""),
                "state": structured_fields.get("state", {}).get("value", ""),
                "district": structured_fields.get("district", {}).get("value", ""),
                "pin_code": structured_fields.get("pin_code", {}).get("value", ""),
            }

            # Mirror to verified_data (user can correct later)
            verified_data = dict(ocr_data)

            # ── Stage 9: Expiry Detection ────────────────────────────────────────
            is_expired = self._check_expiry(ocr_data.get("expiry_date", ""))

            # ── Stage 10: Thumbnail ──────────────────────────────────────────────
            t0 = time.time()
            thumbnail_path = self._generate_thumbnail(primary_path)
            timings["thumbnail"] = round(time.time() - t0, 3)

            # ── Stage 11: Duplicate Detection & Versioning ───────────────────────
            t0 = time.time()
            from vault.duplicate_detector import DuplicateDetector
            document_type = classification.get("document_type", "other_document")

            is_dup, existing_doc, dup_reason = DuplicateDetector.check(
                user_id=user_id,
                document_hash=document_hash,
                document_type=document_type,
                document_number=ocr_data.get("document_number", ""),
                owner_name=ocr_data.get("owner_name", ""),
                dob=ocr_data.get("dob", ""),
            )

            version = 1
            if is_dup and existing_doc:
                version = DuplicateDetector.get_version_count(user_id, document_type) + 1
                DuplicateDetector.deactivate_previous_versions(user_id, document_type)
            timings["duplicate_check"] = round(time.time() - t0, 3)

            # ── Stage 12: Encrypt & Store ────────────────────────────────────────
            masked_fields = self._mask_sensitive_fields(structured_fields)
            document_name = self._format_document_name(filename, classification)
            document_label = classification.get("document_label", "Other Document")
            file_size = os.path.getsize(temp_path)
            file_type = ext.lstrip(".")
            storage_filename = f"vault_{uuid.uuid4().hex}{ext}"
            storage_path = os.path.join(STORAGE_ROOT, storage_filename)
            SecurityManager.encrypt_file(temp_path, storage_path)

            # ── Determine initial document_status ────────────────────────────────
            from vault.verification_status import DocumentStatus, ConfidenceTier
            # Use VERIFICATION confidence (from identity fields), NOT raw OCR confidence
            confidence_tier = ConfidenceTier.from_score(verification_confidence)

            if verification_confidence >= 90:
                document_status = DocumentStatus.ACCEPTED
            elif verification_confidence >= 75:
                document_status = DocumentStatus.AWAITING_REVIEW
            else:
                document_status = DocumentStatus.AWAITING_REVIEW

            quality_data = QualityDetector.analyze(primary_path)

            # ── Build the full MongoDB record ────────────────────────────────────
            now = datetime.datetime.utcnow()
            metadata_record = {
                "user_id": str(user_id),
                "document_name": document_name,
                "document_type": document_type,
                "document_label": document_label,
                "file_type": file_type,
                "file_size": file_size,
                "storage_path": storage_path,
                "thumbnail_path": thumbnail_path,
                "document_hash": document_hash,
                "version": version,
                "is_active": True,
                "is_expired": is_expired,

                # Status fields (separated per architecture)
                "document_status": document_status,
                "identity_status": "Unverified",
                "verification_status": document_status,  # Legacy compat

                # OCR results (immutable)
                "ocr_text": raw_text,
                "ocr_engine": ocr_engine,
                "ocr_data": ocr_data,

                # User-correctable data (initially mirrors ocr_data)
                "verified_data": verified_data,
                "metadata": ocr_data,  # Legacy compat

                # Confidence — use VERIFICATION confidence, not raw OCR
                "confidence": round(verification_confidence, 2),
                "raw_ocr_confidence": round(ocr_confidence, 2),
                "confidence_tier": confidence_tier,
                "field_confidence": field_confidence,
                "identity_match_score": None,  # null when no reference data available

                # Processing metrics
                "processing_time": round(time.time() - upload_start, 3),
                "stage_timings": timings,

                # Supplementary
                "quality": quality_data,
                "quality_score": quality_data.get("quality_score", 0.0),
                "qr": qr_result,
                "classification": classification,
                "search_index": self._build_search_index({
                    "document_name": document_name,
                    "document_type": document_type,
                    "document_label": document_label,
                    "metadata": ocr_data,
                }, raw_text),
                "masked_fields": {
                    "aadhaar_number": VaultUtils.mask_aadhaar(
                        structured_fields.get("masked_aadhaar", {}).get("value", "")
                    ),
                },
                "sealed_payload": {
                    "ocr_text": raw_text,
                    "ocr_candidates": ocr_candidates,
                    "fields": structured_fields,
                    "classification": classification,
                    "qr": qr_result,
                },

                "uploaded_at": now,
                "created_at": now,
                "updated_at": now,
                "review_timestamp": None,
                "verification_timestamp": None,
                "audit_history": [],
            }

            # ── Stage 13: MongoDB Insert ─────────────────────────────────────────
            t0 = time.time()
            try:
                document_id = DocumentVault.save_document_record(metadata_record)
            except Exception as db_exc:
                eid = _make_error_id(f"MongoDB insert failed: {db_exc}\n{traceback.format_exc()}")
                return {"status": "FAILED", "message": "Failed to save document. Please try again.", "error_code": eid}
            timings["mongodb_insert"] = round(time.time() - t0, 3)

            AuditLogger.record("vault_document_stored", user_id, {
                "document_id": document_id,
                "document_type": document_type,
                "document_name": document_name,
                "version": version,
                "is_duplicate": is_dup,
                "duplicate_reason": dup_reason,
            }, document_id=document_id)

            total_time = round(time.time() - upload_start, 3)
            timings["total"] = total_time
            logger.info(
                "[UPLOAD] COMPLETE document_id=%s total_time=%.3fs engine=%s confidence=%.1f%% status=%s version=%d",
                document_id, total_time, ocr_engine, ocr_confidence, document_status, version,
            )

            # Return full context for the frontend review modal
            stored = DocumentVault.get_document_by_id(document_id, user_id=user_id)
            return {
                "status": "AWAITING_REVIEW",
                "message": "Document processed successfully. Please review the extracted information.",
                "document_id": document_id,
                "document": stored,
                "ocr_data": ocr_data,
                "verified_data": verified_data,
                "field_confidence": field_confidence,
                "confidence": round(ocr_confidence, 2),
                "confidence_tier": confidence_tier,
                "ocr_engine": ocr_engine,
                "processing_time": total_time,
                "stage_timings": timings,
                "is_duplicate": is_dup,
                "duplicate_reason": dup_reason,
                "is_expired": is_expired,
                "version": version,
            }

        except Exception as exc:
            tb = traceback.format_exc()
            eid = _make_error_id(f"Upload pipeline exception for {filename}: {exc}\n{tb}")
            return {
                "status": "FAILED",
                "message": "An internal error occurred. Please try again.",
                "error_code": eid,
            }
        finally:
            SecurityManager.secure_cleanup(image_paths + [temp_path])

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _check_expiry(expiry_date_str: str) -> bool:
        """Return True if the document has expired based on its expiry_date."""
        if not expiry_date_str:
            return False
        normalized = VaultUtils.normalize_date(expiry_date_str)
        if not normalized or len(normalized) < 10:
            return False
        try:
            expiry = datetime.datetime.strptime(normalized[:10], "%Y-%m-%d")
            return expiry < datetime.datetime.utcnow()
        except (ValueError, TypeError):
            return False


