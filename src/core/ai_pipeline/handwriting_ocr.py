"""
Enhanced OCR Processor for Handwritten Documents
Uses advanced preprocessing and multiple OCR engines for better accuracy
"""

import logging
from typing import Dict, Any, Tuple, List
from PIL import Image
import cv2
import numpy as np
import pytesseract
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HandwritingOCRResult:
    """Result from handwriting OCR"""
    text: str
    confidence: float
    lines: List[Dict[str, Any]]
    extracted_fields: Dict[str, Any]
    preprocessing_applied: List[str]


class HandwritingOCRProcessor:
    """
    Specialized OCR processor for handwritten documents
    Applies multiple preprocessing techniques and uses ensemble methods
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        logger.info("Handwriting OCR Processor initialized")
    
    def preprocess_handwriting(self, image: Image.Image) -> List[Tuple[Image.Image, str]]:
        """
        Apply multiple preprocessing techniques for handwritten text
        Returns list of (preprocessed_image, technique_name) tuples
        """
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        preprocessed_images = []
        
        # Technique 1: Adaptive Thresholding
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        preprocessed_images.append((Image.fromarray(adaptive_thresh), "adaptive_threshold"))
        
        # Technique 2: Otsu's Thresholding
        _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_images.append((Image.fromarray(otsu_thresh), "otsu_threshold"))
        
        # Technique 3: Denoising + Thresholding
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        _, denoised_thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_images.append((Image.fromarray(denoised_thresh), "denoised_otsu"))
        
        # Technique 4: Morphological operations
        kernel = np.ones((2, 2), np.uint8)
        morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        _, morph_thresh = cv2.threshold(morph, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_images.append((Image.fromarray(morph_thresh), "morphological"))
        
        # Technique 5: Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, enhanced_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_images.append((Image.fromarray(enhanced_thresh), "contrast_enhanced"))
        
        # Technique 6: Original with slight blur
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, blur_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_images.append((Image.fromarray(blur_thresh), "gaussian_blur"))
        
        return preprocessed_images
    
    def extract_text_ensemble(
        self, 
        preprocessed_images: List[Tuple[Image.Image, str]]
    ) -> Tuple[str, float, List[str]]:
        """
        Use ensemble approach: try multiple preprocessing techniques
        and combine results for best accuracy
        """
        results = []
        techniques_used = []
        
        # Try different Tesseract configurations for handwriting
        configs = [
            '--psm 6',  # Assume uniform text block
            '--psm 4',  # Assume single column of text
            '--psm 11', # Sparse text
            '--psm 12', # Sparse text with OSD
        ]
        
        for image, technique in preprocessed_images:
            for config in configs:
                try:
                    # Extract text with confidence
                    data = pytesseract.image_to_data(
                        image,
                        output_type=pytesseract.Output.DICT,
                        config=config
                    )
                    
                    text_parts = []
                    confidences = []
                    
                    for i, conf in enumerate(data['conf']):
                        if conf > 30:  # Lower threshold for handwriting
                            text = data['text'][i].strip()
                            if text:
                                text_parts.append(text)
                                confidences.append(conf)
                    
                    if text_parts:
                        full_text = ' '.join(text_parts)
                        avg_conf = np.mean(confidences) if confidences else 0
                        results.append((full_text, avg_conf, technique, config))
                        
                except Exception as e:
                    logger.debug(f"OCR failed for {technique} with {config}: {e}")
                    continue
        
        if not results:
            return "", 0.0, []
        
        # Sort by confidence and get best result
        results.sort(key=lambda x: x[1], reverse=True)
        best_text, best_conf, best_technique, best_config = results[0]
        
        techniques_used.append(f"{best_technique}_{best_config}")
        
        return best_text, best_conf / 100.0, techniques_used
    
    def extract_lines(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Extract individual lines from the document
        Useful for line-by-line processing
        """
        img_array = np.array(image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours (lines)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        lines = []
        for i, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter out noise (too small regions)
            if w > 50 and h > 10:
                # Extract line region
                line_img = gray[y:y+h, x:x+w]
                line_pil = Image.fromarray(line_img)
                
                # OCR on individual line
                try:
                    line_text = pytesseract.image_to_string(
                        line_pil,
                        config='--psm 7'  # Single line
                    ).strip()
                    
                    if line_text:
                        lines.append({
                            'line_number': i + 1,
                            'text': line_text,
                            'bbox': {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)}
                        })
                except Exception as e:
                    logger.debug(f"Line OCR failed: {e}")
        
        # Sort lines by y-coordinate (top to bottom)
        lines.sort(key=lambda l: l['bbox']['y'])
        
        return lines
    
    def extract_structured_fields(
        self, 
        text: str, 
        lines: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract structured fields from handwritten document
        Uses pattern matching and heuristics
        """
        import re
        
        fields = {}
        text_lower = text.lower()
        
        # Extract common healthcare fields
        
        # Patient/Member ID
        id_patterns = [
            r'id[:\s]+([A-Z0-9\-]+)',
            r'member[:\s]+([A-Z0-9\-]+)',
            r'patient\s*id[:\s]+([A-Z0-9\-]+)',
        ]
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['member_id'] = match.group(1)
                break
        
        # Plan information
        plan_patterns = [
            r'plan[:\s]+([A-Z0-9\s]+)',
            r'ppo[:\s]+([A-Z0-9\s]+)',
            r'hmo[:\s]+([A-Z0-9\s]+)',
        ]
        for pattern in plan_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['plan'] = match.group(1).strip()
                break
        
        # Copay/Cost information
        cost_patterns = [
            r'copay[:\s]+\$?(\d+)',
            r'co\s*pay[:\s]+\$?(\d+)',
            r'\$(\d+)',
        ]
        costs = []
        for pattern in cost_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            costs.extend(matches)
        if costs:
            fields['copay'] = f"${costs[0]}"
        
        # Dates
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                fields['date'] = match.group(1)
                break
        
        # Provider/Doctor
        if 'dr.' in text_lower or 'doctor' in text_lower:
            provider_match = re.search(r'dr\.?\s+([A-Za-z\s]+)', text, re.IGNORECASE)
            if provider_match:
                fields['provider'] = provider_match.group(1).strip()
        
        # Extract from individual lines for better accuracy
        for line in lines:
            line_text = line['text'].lower()
            
            if 'health' in line_text:
                fields['health_plan'] = line['text']
            elif 'rx' in line_text or 'prescription' in line_text:
                fields['prescription_info'] = line['text']
            elif 'er' in line_text and '$' in line['text']:
                er_match = re.search(r'\$(\d+)', line['text'])
                if er_match:
                    fields['er_copay'] = f"${er_match.group(1)}"
        
        return fields
    
    def process_handwritten_image(self, image_path: str) -> HandwritingOCRResult:
        """
        Main processing function for handwritten documents
        """
        try:
            # Load image
            image = Image.open(image_path)
            
            # Apply multiple preprocessing techniques
            preprocessed_images = self.preprocess_handwriting(image)
            
            # Extract text using ensemble approach
            text, confidence, techniques = self.extract_text_ensemble(preprocessed_images)
            
            # Extract individual lines
            lines = self.extract_lines(image)
            
            # Extract structured fields
            fields = self.extract_structured_fields(text, lines)
            
            logger.info(f"Handwriting OCR completed with confidence: {confidence:.2f}")
            logger.info(f"Extracted {len(lines)} lines")
            logger.info(f"Extracted fields: {list(fields.keys())}")
            
            return HandwritingOCRResult(
                text=text,
                confidence=confidence,
                lines=lines,
                extracted_fields=fields,
                preprocessing_applied=techniques
            )
            
        except Exception as e:
            logger.error(f"Handwriting OCR failed: {e}")
            raise
    
    def process_with_manual_review(
        self, 
        image_path: str
    ) -> Dict[str, Any]:
        """
        Process handwritten document and flag for manual review if confidence is low
        """
        result = self.process_handwritten_image(image_path)
        
        # Flag for manual review if confidence is low
        needs_review = result.confidence < 0.6
        
        return {
            'text': result.text,
            'confidence': result.confidence,
            'lines': result.lines,
            'extracted_fields': result.extracted_fields,
            'needs_manual_review': needs_review,
            'review_reason': 'Low confidence score' if needs_review else None,
            'preprocessing_used': result.preprocessing_applied
        }


# Example usage
if __name__ == "__main__":
    processor = HandwritingOCRProcessor()
    
    # Process handwritten document
    result = processor.process_with_manual_review('/path/to/handwritten_doc.jpg')
    
    print(f"Extracted Text: {result['text']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Needs Review: {result['needs_manual_review']}")
    print(f"\nExtracted Fields:")
    for key, value in result['extracted_fields'].items():
        print(f"  {key}: {value}")
    print(f"\nLines Detected: {len(result['lines'])}")
    for line in result['lines']:
        print(f"  Line {line['line_number']}: {line['text']}")
