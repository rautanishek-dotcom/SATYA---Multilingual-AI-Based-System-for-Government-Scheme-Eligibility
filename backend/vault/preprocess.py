import cv2
import numpy as np
from PIL import Image, ExifTags
import logging

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    @staticmethod
    def fix_exif_orientation(image_path: str) -> np.ndarray:
        """Reads image with PIL to fix EXIF orientation, converts to cv2 format."""
        try:
            image = Image.open(image_path)
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            
            exif = image._getexif()
            if exif is not None and orientation in exif:
                if exif[orientation] == 3:
                    image = image.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    image = image.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    image = image.rotate(90, expand=True)
                    
            # Convert to OpenCV BGR
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            return cv_image
        except Exception as e:
            logger.warning(f"EXIF orientation fix failed or not applicable: {e}")
            return cv2.imread(image_path)

    @staticmethod
    def deskew_image(image: np.ndarray) -> np.ndarray:
        """Calculates skew angle and deskews the image using probabilistic Hough transform."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        # Ignore tiny skews
        if abs(angle) < 0.5:
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        logger.debug(f"Deskewed image by {angle:.2f} degrees")
        return rotated

    @staticmethod
    def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
        """Applies CLAHE and noise removal for optimal OCR."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Denoising
        denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10, searchWindowSize=21, templateWindowSize=7)
        
        # Adaptive Thresholding for sharp binarization (better for OCR)
        binary = cv2.adaptiveThreshold(
            denoised, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 31, 11
        )
        
        # Convert back to 3-channel for PaddleOCR compatibility
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def process(image_path: str) -> np.ndarray:
        """Runs the full preprocessing pipeline."""
        img = ImagePreprocessor.fix_exif_orientation(image_path)
        img = ImagePreprocessor.deskew_image(img)
        return img
