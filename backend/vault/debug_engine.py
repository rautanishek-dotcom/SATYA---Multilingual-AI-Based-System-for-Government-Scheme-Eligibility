import os
import json
import cv2
import uuid
from datetime import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DebugEngine:
    DEBUG_DIR = "uploads/debug"
    
    @staticmethod
    def _ensure_dir():
        os.makedirs(DebugEngine.DEBUG_DIR, exist_ok=True)
        
    @staticmethod
    def draw_bounding_boxes(image_path: str, ocr_result: Dict[str, Any], output_path: str):
        """Draws bounding boxes on the image for debugging."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return
                
            for word in ocr_result.get("words", []):
                box = word["box"]
                text = word["text"]
                # Box is a list of 4 points [[x,y], [x,y], [x,y], [x,y]]
                pts = np.array(box, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], True, (0, 255, 0), 2)
                
            cv2.imwrite(output_path, img)
        except Exception as e:
            logger.error(f"Failed to draw bounding boxes: {e}")

    @staticmethod
    def log_execution(original_path: str, preprocessed_path: str, ocr_result: Dict[str, Any], extracted_fields: Dict[str, Any], failure_reason: str = ""):
        """
        Saves all artifacts associated with an OCR run.
        """
        DebugEngine._ensure_dir()
        session_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().isoformat()
        
        base_path = os.path.join(DebugEngine.DEBUG_DIR, f"{timestamp.replace(':', '-')}_{session_id}")
        
        # 1. Overlay bounding boxes
        if os.path.exists(original_path):
            overlay_path = f"{base_path}_bboxes.jpg"
            import numpy as np # Import locally for safety
            DebugEngine.draw_bounding_boxes(original_path, ocr_result, overlay_path)
            
        # 2. Save structured JSON
        json_path = f"{base_path}_log.json"
        
        log_data = {
            "session_id": session_id,
            "timestamp": timestamp,
            "failure_reason": failure_reason,
            "ocr_metrics": {
                "engine": ocr_result.get("engine"),
                "processing_time_ms": ocr_result.get("processing_time_ms"),
                "average_confidence": ocr_result.get("average_confidence"),
            },
            "extracted_data": extracted_fields,
            "raw_text": ocr_result.get("full_text", "")
        }
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Debug artifacts saved for session {session_id}")
