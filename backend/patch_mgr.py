import sys

file_path = r'd:\MAJOR PROJECT(SATYA) (Final) (curr)\backend\vault\document_manager.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            # ── Stage 3: PDF/Image Conversion ────────────────────────────────────
            t0 = time.time()
            if ext == ".pdf":
                image_paths = self._convert_pdf_to_images(temp_path)
            else:
                image_paths = [temp_path]
            timings["conversion"] = round(time.time() - t0, 3)

            # ── Stage 4: Preprocessing ───────────────────────────────────────────
            t0 = time.time()
            for page_image in image_paths:
                processed = self._preprocess_image(page_image)
                processed_paths.append(processed or page_image)
            timings["preprocessing"] = round(time.time() - t0, 3)

            if not processed_paths:
                eid = _make_error_id(f"Preprocessing produced no output for {filename}")
                return {"status": "FAILED", "message": "Image could not be processed.", "error_code": eid}

            primary_path = processed_paths[0]

            # ── Stage 5: OCR ─────────────────────────────────────────────────────
            t0 = time.time()
            hint_text = quick_document_hint(primary_path)
            raw_text, ocr_candidates, ocr_confidence = self._run_ocr(processed_paths)
            timings["ocr"] = round(time.time() - t0, 3)
            ocr_engine = ocr_candidates[0].get("engine", "unknown") if ocr_candidates else "none"
            logger.info("[STAGE:OCR] END %.3fs engine=%s confidence=%.1f%%", timings["ocr"], ocr_engine, ocr_confidence)'''

replacement = '''            # ── Stage 3: PDF/Image Conversion ────────────────────────────────────
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
                logger.info("[STAGE:OCR] END %.3fs engine=%s confidence=%.1f%%", timings["ocr"], ocr_engine, ocr_confidence)'''
                
if target.replace('\r', '') in text.replace('\r', ''):
    new_text = text.replace('\r', '').replace(target.replace('\r', ''), replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('SUCCESS: Substring replaced.')
else:
    print('ERROR: Target substring not found in the file.')
