import logging
import cv2
import re
from typing import Dict, Any, List, Optional
from vault.extractors.base_extractor import BaseDocumentExtractor
from vault.field_extractor import FieldExtractor
from vault.utils import VaultUtils

logger = logging.getLogger(__name__)

class AadhaarExtractor(BaseDocumentExtractor):
    def __init__(self, debug_mode=True):
        super().__init__(debug_mode)
        
    def extract(self, image_path: str, hint_text: str = "", qr_payload: str = "") -> Dict[str, Any]:
        """Aadhaar specific Region-Based Extraction Pipeline."""
        img = self._normalize_image_for_ocr(image_path)
        if img is None:
            return {}

        # STEP 1: Full Document Baseline Words Extraction
        words = self._get_ocr_words(image_path)
        merged_words = self._merge_text_boxes(words)
        
        # STEP 2: Find Anchors (DOB, Gender)
        dob_box = self._find_dob_anchor(merged_words)
        gender_box = self._find_gender_anchor(merged_words)
        
        # Determine candidate region bounds geometrically
        h, w = img.shape[:2]
        regions = self._generate_name_candidate_regions(dob_box, gender_box, h, w)
        
        candidates = []
        best_overall = None
        
        # STEP 3: Multi-configuration Region OCR
        for region_idx, region_rect in enumerate(regions):
            rx, ry, rw, rh = region_rect
            # Safety bounds
            rx, ry = max(0, rx), max(0, ry)
            rw, rh = min(w - rx, rw), min(h - ry, rh)
            if rw <= 10 or rh <= 10:
                continue
                
            crop = img[ry:ry+rh, rx:rx+rw]
            self._save_debug_image(crop, f"aadhaar_debug_region_{region_idx}.png")
            
            variants = self._generate_preprocessing_variants(crop)
            for var_name, var_img in variants.items():
                # Write to temp for OCR Engine
                tmp_path = f"backend/temp_uploads/debug/tmp_{var_name}_{region_idx}.png"
                cv2.imwrite(tmp_path, var_img)
                
                # Extract and merge crop words
                crop_words = self._merge_text_boxes(self._get_ocr_words(tmp_path))
                
                for word_entry in crop_words:
                    cand_text = self._correct_common_ocr_errors(word_entry["text"])
                    cand_text = re.sub(r'[^a-zA-Z\s\.]', '', cand_text).strip()
                    if self._is_valid_aadhaar_name(cand_text):
                        # Layout Distance Score
                        dist_score = 0
                        if dob_box:
                            # Distance from DOB Y
                            y_dist = dob_box[0][1] - (ry + word_entry["center"][1])
                            if 0 < y_dist < 150:
                                dist_score += 15 # Bonus for being directly above DOB
                        
                        score = word_entry["confidence"] * 0.4 + dist_score + len(cand_text.split()) * 5
                        candidates.append({
                            "text": cand_text,
                            "confidence": min(100.0, score),
                            "source": f"region_crop_{region_idx}_{var_name}"
                        })

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        final_name = candidates[0] if candidates else None

        # Return standardized payload compatible with extraction_orchestrator
        fields = {}
        if final_name and final_name["confidence"] > 60:
            # Map EXACTLY to "full_name" to respect UI requirements
            fields["full_name"] = {
                "value": final_name["text"],
                "confidence": final_name["confidence"],
                "strategy": "layout_anchor_region"
            }
            # Fallback legacy alias for UI parity just in case
            fields["name"] = fields["full_name"]
            
        return {
            "fields": fields,
            "name_candidates": candidates
        }

    def _find_dob_anchor(self, words: List[Dict[str, Any]]) -> Optional[List[List[float]]]:
        for w in words:
            if re.search(r'\b\d{2,4}[/\-]\d{2}[/\-]\d{2,4}\b', w["text"]):
                return w["box"]
        return None

    def _find_gender_anchor(self, words: List[Dict[str, Any]]) -> Optional[List[List[float]]]:
        for w in words:
            if re.search(r'\b(male|female|transgender)\b', w["text"], re.IGNORECASE):
                return w["box"]
        return None

    def _generate_name_candidate_regions(self, dob_box, gender_box, h, w):
        """Generates dynamic bounding boxes proportional to known anchors."""
        regions = []
        if dob_box:
            dy = int(dob_box[0][1])
            dx = int(dob_box[0][0])
            # Region 1: Directly above DOB
            regions.append((max(0, dx - 100), max(0, dy - 150), 400, 150))
            # Region 2: Wider band above DOB
            regions.append((max(0, dx - 200), max(0, dy - 250), 600, 250))
        elif gender_box:
            gy = int(gender_box[0][1])
            gx = int(gender_box[0][0])
            regions.append((max(0, gx - 100), max(0, gy - 200), 400, 200))
        else:
            # Fallback typical Aadhaar proportions if anchors fail
            regions.append((int(w*0.1), int(h*0.15), int(w*0.8), int(h*0.3)))
        return regions

    def _is_valid_aadhaar_name(self, text: str) -> bool:
        c = text.lower().strip()
        if len(c) < 3 or len(c) > 50: return False
        if bool(re.search(r'\d', c)): return False
        forbidden = {'dob', 'date of birth', 'gender', 'male', 'female', 'aadhaar', 'uidai', 'address', 'phone', 'pan', 'government'}
        tokens = c.split()
        if any(t in forbidden for t in tokens): return False
        return True
