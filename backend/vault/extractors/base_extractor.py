import cv2
import numpy as np
import logging
import os
import re
from typing import Dict, Any, List, Optional
from vault.ocr_engine import OCREngine

logger = logging.getLogger(__name__)

class BaseDocumentExtractor:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self.debug_dir = "backend/temp_uploads/debug"
        if self.debug_mode:
            os.makedirs(self.debug_dir, exist_ok=True)

    def extract(self, image_path: str, hint_text: str = "", qr_payload: str = "") -> Dict[str, Any]:
        """Override this in specific document extractors."""
        raise NotImplementedError

    def _save_debug_image(self, image, filename: str):
        if self.debug_mode and image is not None:
            path = os.path.join(self.debug_dir, filename)
            cv2.imwrite(path, image)

    def _normalize_image_for_ocr(self, image_path: str):
        """Grayscale, contrast enhancement, resizing."""
        img = cv2.imread(image_path)
        if img is None:
            return None
        return img

    def _get_ocr_words(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract words and bounding boxes using OCREngine."""
        result = OCREngine.extract(image_path, use_fallback=True)
        return result.get("words", [])

    def _generate_preprocessing_variants(self, img) -> Dict[str, Any]:
        """Provides different preprocessed variants of an image crop."""
        variants = {"original": img}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        variants["grayscale"] = gray
        # Adaptive Threshold
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
        variants["adaptive_thresh"] = thresh
        # Upscaled
        upscaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        variants["upscaled_2x"] = upscaled
        return variants

    def _merge_text_boxes(self, words: List[Dict[str, Any]], vertical_tolerance: float = 15.0, horizontal_tolerance: float = 25.0) -> List[Dict[str, Any]]:
        """
        Merges broken OCR text if boxes belong to the same line.
        """
        if not words:
            return []
            
        words.sort(key=lambda w: (w["center"][1], w["center"][0]))
        merged = []
        current_line = [words[0]]
        
        for i in range(1, len(words)):
            w = words[i]
            prev = current_line[-1]
            
            y_diff = abs(w["center"][1] - prev["center"][1])
            x_diff = w["box"][0][0] - prev["box"][1][0] # prev right to current left
            
            # Same line heuristic
            if y_diff < vertical_tolerance and x_diff < horizontal_tolerance and x_diff > -10:
                current_line.append(w)
            else:
                # Merge current line
                merged.append(self._compress_line(current_line))
                current_line = [w]
                
        if current_line:
            merged.append(self._compress_line(current_line))
            
        return merged

    def _compress_line(self, line_words: List[Dict[str, Any]]) -> Dict[str, Any]:
        box_pts = []
        for w in line_words:
            box_pts.extend(w["box"])
        xs = [p[0] for p in box_pts]
        ys = [p[1] for p in box_pts]
        merged_box = [[min(xs), min(ys)], [max(xs), min(ys)], [max(xs), max(ys)], [min(xs), max(ys)]]
        center = ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2)
        text = " ".join([w["text"] for w in line_words])
        avg_conf = sum(w["confidence"] for w in line_words) / len(line_words)
        return {"text": text, "box": merged_box, "center": center, "confidence": avg_conf}

    def _correct_common_ocr_errors(self, name_cand: str) -> str:
        """Conservative correction rules specifically for Names."""
        tokens = name_cand.split()
        corrected = []
        for t in tokens:
            if re.match(r'^[A-Z]*[O0I1l58S]+[A-Z]*$', t, re.IGNORECASE):
                t = t.replace('0', 'O').replace('1', 'I').replace('5', 'S').replace('8', 'B')
            corrected.append(t)
        return " ".join(corrected)
