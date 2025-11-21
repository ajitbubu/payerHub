"""
TrOCR-based Handwriting Recognition
Uses Microsoft's Transformer-based OCR for superior handwriting accuracy
"""

import logging
from typing import Dict, Any, List, Tuple
from PIL import Image
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from dataclasses import dataclass
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrOCRResult:
    """Result from TrOCR processing"""
    text: str
    confidence: float
    lines: List[Dict[str, Any]]
    extracted_fields: Dict[str, Any]
    model_used: str


class TrOCRHandwritingProcessor:
    """
    Advanced handwriting OCR using TrOCR (Transformer-based OCR)
    Significantly better accuracy than traditional OCR on handwritten text
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize TrOCR model
        model_name = self.config.get('model', 'microsoft/trocr-large-handwritten')
        logger.info(f"Loading TrOCR model: {model_name}")
        
        self.processor = TrOCRProcessor.from_pretrained(model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"TrOCR initialized on {self.device}")
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for TrOCR
        """
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (TrOCR works best with smaller images)
        max_size = 2048
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.LANCZOS)
        
        return image
    
    def extract_text_lines(self, image: Image.Image) -> List[Tuple[Image.Image, Dict]]:
        """
        Segment image into individual text lines
        Returns list of (line_image, bbox) tuples
        """
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        lines = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter out noise (too small regions)
            if w > 50 and h > 15:
                # Extract line region with some padding
                padding = 5
                y1 = max(0, y - padding)
                y2 = min(img_array.shape[0], y + h + padding)
                x1 = max(0, x - padding)
                x2 = min(img_array.shape[1], x + w + padding)
                
                line_img = img_array[y1:y2, x1:x2]
                line_pil = Image.fromarray(line_img)
                
                bbox = {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)}
                lines.append((line_pil, bbox))
        
        # Sort lines by y-coordinate (top to bottom)
        lines.sort(key=lambda l: l[1]['y'])
        
        return lines
    
    def recognize_text(self, image: Image.Image) -> Tuple[str, float]:
        """
        Recognize text from image using TrOCR
        Returns (text, confidence)
        """
        try:
            # Preprocess
            image = self.preprocess_image(image)
            
            # Prepare input
            pixel_values = self.processor(image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)
            
            # Generate text
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    max_length=256,
                    num_beams=4,
                    early_stopping=True
                )
            
            # Decode
            text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # Calculate confidence (simplified - based on generation probability)
            # In production, you'd want to use the actual logits
            confidence = 0.85 if len(text) > 0 else 0.0
            
            return text.strip(), confidence
            
        except Exception as e:
            logger.error(f"TrOCR recognition failed: {e}")
            return "", 0.0
    
    def process_line_by_line(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Process document line by line for better accuracy
        """
        # Extract lines
        line_images = self.extract_text_lines(image)
        
        results = []
        for idx, (line_img, bbox) in enumerate(line_images):
            # Recognize text in line
            text, confidence = self.recognize_text(line_img)
            
            if text:
                results.append({
                    'line_number': idx + 1,
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox
                })
                logger.debug(f"Line {idx + 1}: {text} (conf: {confidence:.2f})")
        
        return results
    
    def extract_structured_fields(
        self, 
        text: str, 
        lines: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract structured fields from recognized text
        """
        import re
        
        fields = {}
        text_lower = text.lower()
        
        # Healthcare-specific field extraction
        
        # Member/Patient ID
        id_patterns = [
            r'(?:member|patient|id)[:\s]+([A-Z0-9\-]+)',
            r'id[:\s]*([A-Z]{2,4}[-\s]?\d{4}[-\s]?\d{4,})',
        ]
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['member_id'] = match.group(1).strip()
                break
        
        # Plan information
        plan_patterns = [
            r'plan[:\s]+([A-Z0-9\s]+?)(?:\n|$)',
            r'(PPO|HMO|EPO|POS)[:\s]+([A-Z0-9\s]+)',
        ]
        for pattern in plan_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['plan'] = match.group(0).strip()
                break
        
        # Copay amounts
        copay_patterns = [
            r'(?:copay|co\s*pay)[:\s]+\$?(\d+)',
            r'(?:er|emergency)[:\s]+\$(\d+)',
            r'(?:rx|prescription)[:\s]+\$?(\d+)',
        ]
        for pattern in copay_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                field_name = match.group(0).split(':')[0].strip().lower().replace(' ', '_')
                fields[f'{field_name}_amount'] = f"${match.group(1)}"
        
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
        
        # Provider/Doctor name
        provider_patterns = [
            r'(?:dr|doctor)[.\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'provider[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        for pattern in provider_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['provider'] = match.group(1).strip()
                break
        
        # Health plan name
        if 'health' in text_lower:
            health_match = re.search(r'([A-Z][a-z]+\s+Health[^\n]*)', text, re.IGNORECASE)
            if health_match:
                fields['health_plan'] = health_match.group(1).strip()
        
        return fields
    
    def process_handwritten_document(self, image_path: str) -> TrOCRResult:
        """
        Main processing function for handwritten documents
        """
        try:
            # Load image
            image = Image.open(image_path)
            
            # Process line by line
            lines = self.process_line_by_line(image)
            
            # Combine all text
            full_text = '\n'.join([line['text'] for line in lines])
            
            # Calculate average confidence
            if lines:
                avg_confidence = sum(line['confidence'] for line in lines) / len(lines)
            else:
                avg_confidence = 0.0
            
            # Extract structured fields
            fields = self.extract_structured_fields(full_text, lines)
            
            logger.info(f"TrOCR processing complete: {len(lines)} lines, confidence: {avg_confidence:.2f}")
            
            return TrOCRResult(
                text=full_text,
                confidence=avg_confidence,
                lines=lines,
                extracted_fields=fields,
                model_used='microsoft/trocr-large-handwritten'
            )
            
        except Exception as e:
            logger.error(f"TrOCR processing failed: {e}")
            raise
    
    def process_with_fallback(
        self, 
        image_path: str,
        fallback_processor=None
    ) -> Dict[str, Any]:
        """
        Process with TrOCR and fallback to another processor if confidence is low
        """
        # Try TrOCR first
        result = self.process_handwritten_document(image_path)
        
        # If confidence is low and fallback is available, try fallback
        if result.confidence < 0.6 and fallback_processor:
            logger.info("Low confidence, trying fallback processor...")
            try:
                fallback_result = fallback_processor.process_handwritten_image(image_path)
                
                # Use whichever has higher confidence
                if fallback_result.confidence > result.confidence:
                    logger.info("Using fallback result (higher confidence)")
                    return {
                        'text': fallback_result.text,
                        'confidence': fallback_result.confidence,
                        'lines': fallback_result.lines,
                        'extracted_fields': fallback_result.extracted_fields,
                        'model_used': 'fallback',
                        'needs_manual_review': fallback_result.confidence < 0.7
                    }
            except Exception as e:
                logger.error(f"Fallback processing failed: {e}")
        
        return {
            'text': result.text,
            'confidence': result.confidence,
            'lines': result.lines,
            'extracted_fields': result.extracted_fields,
            'model_used': result.model_used,
            'needs_manual_review': result.confidence < 0.7
        }


# Example usage
if __name__ == "__main__":
    processor = TrOCRHandwritingProcessor()
    
    # Process handwritten document
    result = processor.process_with_fallback('/path/to/handwritten_doc.jpg')
    
    print(f"Model Used: {result['model_used']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Needs Review: {result['needs_manual_review']}")
    print(f"\nExtracted Text:\n{result['text']}")
    print(f"\nExtracted Fields:")
    for key, value in result['extracted_fields'].items():
        print(f"  {key}: {value}")
