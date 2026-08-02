import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Singletons for models
_PADDLEOCR_INSTANCE = None
_PADDLEOCR_AVAILABLE = False
_TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    _PADDLEOCR_AVAILABLE = True
except ImportError:
    pass

try:
    import pytesseract
    pytesseract.get_tesseract_version()
    _TESSERACT_AVAILABLE = True
except Exception:
    pass


class OCREngine:
    @staticmethod
    def get_paddle_instance():
        global _PADDLEOCR_INSTANCE
        if not _PADDLEOCR_AVAILABLE:
            return None
            
        if _PADDLEOCR_INSTANCE is None:
            logger.info("Initializing PaddleOCR Singleton (This should only happen once)")
            import logging as _logging
            _logging.getLogger("ppocr").setLevel(_logging.ERROR)
            # Use use_angle_cls=True but disable tensorrt/gpu for local compat
            _PADDLEOCR_INSTANCE = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False, use_tensorrt=False)
        return _PADDLEOCR_INSTANCE

    @staticmethod
    def extract(image_path: str, use_fallback: bool = True) -> Dict[str, Any]:
        """
        Extracts text and bounding boxes using PaddleOCR (primary) or Tesseract (fallback).
        Returns a structured dictionary with words, boxes, confidences, and processing time.
        """
        t0 = time.time()
        result = {
            "engine": "none",
            "words": [],
            "full_text": "",
            "average_confidence": 0.0,
            "processing_time_ms": 0,
            "raw_json": []
        }

        paddle = OCREngine.get_paddle_instance()
        if paddle:
            try:
                # Paddle OCR returns: [[[[x,y], [x,y], [x,y], [x,y]], ('text', confidence)], ...]
                raw_result = paddle.ocr(image_path, cls=True)
                if raw_result and raw_result[0]:
                    words = []
                    total_conf = 0.0
                    
                    for line in raw_result[0]:
                        if not line or len(line) < 2:
                            continue
                        box = line[0]  # List of 4 points
                        text = str(line[1][0]).strip()
                        conf = float(line[1][1]) * 100.0  # Scale 0-100
                        
                        if text:
                            # Calculate center
                            x_coords = [p[0] for p in box]
                            y_coords = [p[1] for p in box]
                            center_x = sum(x_coords) / 4.0
                            center_y = sum(y_coords) / 4.0
                            
                            words.append({
                                "text": text,
                                "box": box,
                                "center": (center_x, center_y),
                                "confidence": round(conf, 2)
                            })
                            total_conf += conf
                            
                    if words:
                        result["engine"] = "paddleocr"
                        result["words"] = words
                        result["full_text"] = " ".join([w["text"] for w in words])
                        result["average_confidence"] = round(total_conf / len(words), 2)
                        result["raw_json"] = raw_result
                        result["processing_time_ms"] = int((time.time() - t0) * 1000)
                        return result
            except Exception as e:
                logger.error(f"PaddleOCR extraction failed: {e}")

        # Fallback to Tesseract
        if use_fallback and _TESSERACT_AVAILABLE:
            try:
                import cv2
                img = cv2.imread(image_path)
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                
                words = []
                total_conf = 0.0
                
                n_boxes = len(data['text'])
                for i in range(n_boxes):
                    text = str(data['text'][i]).strip()
                    conf = float(data['conf'][i])
                    
                    if text and conf > 0:
                        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        box = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                        center = (x + w/2, y + h/2)
                        
                        words.append({
                            "text": text,
                            "box": box,
                            "center": center,
                            "confidence": round(conf, 2)
                        })
                        total_conf += conf

                if words:
                    result["engine"] = "tesseract"
                    result["words"] = words
                    result["full_text"] = " ".join([w["text"] for w in words])
                    result["average_confidence"] = round(total_conf / len(words), 2)
                    result["raw_json"] = data
            except Exception as e:
                logger.error(f"Tesseract extraction failed: {e}")

        result["processing_time_ms"] = int((time.time() - t0) * 1000)
        return result
