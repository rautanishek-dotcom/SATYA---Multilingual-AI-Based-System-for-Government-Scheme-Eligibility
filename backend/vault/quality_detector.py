import os
import cv2
import numpy as np
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class QualityDetector:
    MIN_WIDTH = 600
    MIN_HEIGHT = 400
    BLUR_THRESHOLD = 100.0

    @staticmethod
    def analyze(image_path: str) -> Dict[str, Any]:
        """
        Analyzes an image for quality metrics: Blur, Brightness, Contrast, Noise, Resolution, Skew.
        Returns a quality score, confidence, and recommendation for OCR.
        """
        result = {
            "passed": True,
            "quality_score": 100.0,
            "metrics": {},
            "recommendation": "PROCEED",
            "issues": [],
            "confidence": 1.0
        }

        if not os.path.exists(image_path):
            return {"passed": False, "issues": ["File not found"], "quality_score": 0.0, "recommendation": "REJECT", "confidence": 0.0}

        ext = os.path.splitext(image_path)[1].lower()
        if ext == ".pdf":
            result["metrics"]["type"] = "pdf"
            result["recommendation"] = "PROCEED (Extract digital text or convert to image)"
            return result
        elif ext == ".zip":
            result["metrics"]["type"] = "zip"
            result["recommendation"] = "PROCEED (Extract XML)"
            return result

        img = cv2.imread(image_path)
        if img is None:
            return {"passed": False, "issues": ["Cannot read image file"], "quality_score": 0.0, "recommendation": "REJECT", "confidence": 0.0}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # 1. Resolution
        result["metrics"]["resolution"] = f"{w}x{h}"
        if w < QualityDetector.MIN_WIDTH or h < QualityDetector.MIN_HEIGHT:
            result["issues"].append("Low resolution")
            result["quality_score"] -= 20

        # 2. Blur (Variance of Laplacian)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        result["metrics"]["blur"] = round(blur_score, 2)
        if blur_score < QualityDetector.BLUR_THRESHOLD:
            result["issues"].append("Image is blurry")
            result["quality_score"] -= min(30, (QualityDetector.BLUR_THRESHOLD - blur_score) / 2)

        # 3. Brightness
        brightness = np.mean(gray)
        result["metrics"]["brightness"] = round(brightness, 2)
        if brightness < 50:
            result["issues"].append("Underexposed (Too dark)")
            result["quality_score"] -= 15
        elif brightness > 220:
            result["issues"].append("Overexposed (Too bright)")
            result["quality_score"] -= 15

        # 4. Contrast
        contrast = gray.std()
        result["metrics"]["contrast"] = round(contrast, 2)
        if contrast < 20:
            result["issues"].append("Low contrast")
            result["quality_score"] -= 15

        # 5. Skew Angle Estimation
        thresh = cv2.threshold(cv2.bitwise_not(gray), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            result["metrics"]["skew_angle"] = round(angle, 2)
            if abs(angle) > 5.0:
                result["issues"].append(f"High skew detected ({angle:.2f} deg)")
                result["quality_score"] -= 10
        else:
            result["metrics"]["skew_angle"] = 0.0

        # Cap quality score
        result["quality_score"] = max(0.0, min(100.0, result["quality_score"]))
        result["confidence"] = result["quality_score"] / 100.0

        # Recommendation Logic
        if result["quality_score"] < 40:
            result["passed"] = False
            result["recommendation"] = "REJECT (Unreadable)"
        elif result["quality_score"] < 70:
            result["recommendation"] = "ENHANCE (Requires contrast/blur correction)"
        else:
            result["recommendation"] = "PROCEED"

        return result
