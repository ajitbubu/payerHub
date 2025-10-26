"""
OCR Processor for extracting text from unstructured documents
Supports PDF, TIFF, images, and scanned documents
Uses Tesseract OCR and LayoutLM for advanced document understanding
"""

import os
import io
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

import pytesseract
from PIL import Image
import pdf2image
import cv2
import numpy as np
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import torch
from dataclasses import dataclass
import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR extraction result"""
    text: str
    confidence: float
    structured_fields: Dict[str, Any]
    document_type: str
    metadata: Dict[str, Any]
    processing_time: float


class OCRProcessor:
    """
    Advanced OCR processor for healthcare documents
    Combines Tesseract OCR with LayoutLM for document understanding
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get('layoutlm_model', 'microsoft/layoutlmv3-base')
        self.use_gpu = config.get('use_gpu', torch.cuda.is_available())
        
        # Initialize LayoutLM
        self.device = torch.device('cuda' if self.use_gpu else 'cpu')
        self.processor = LayoutLMv3Processor.from_pretrained(self.model_name)
        self.model = LayoutLMv3ForTokenClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        
        # S3 client for document storage
        self.s3_client = boto3.client('s3') if config.get('use_s3') else None
        self.s3_bucket = config.get('s3_bucket')
        
        logger.info(f"OCR Processor initialized with model: {self.model_name}")
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results
        - Convert to grayscale
        - Apply adaptive thresholding
        - Denoise
        """
        # Convert PIL Image to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Convert back to PIL Image
        return Image.fromarray(thresh)
    
    def extract_text_tesseract(self, image: Image.Image) -> Tuple[str, float]:
        """
        Extract text using Tesseract OCR
        Returns text and confidence score
        """
        try:
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                image, 
                output_type=pytesseract.Output.DICT,
                config='--psm 6'  # Assume uniform text block
            )
            
            # Extract text and calculate average confidence
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(data['conf']):
                if conf > 0:  # Valid confidence
                    text_parts.append(data['text'][i])
                    confidences.append(conf)
            
            full_text = ' '.join(text_parts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            return full_text, avg_confidence / 100.0  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return "", 0.0
    
    def extract_structured_fields_layoutlm(
        self, 
        image: Image.Image, 
        text: str
    ) -> Dict[str, Any]:
        """
        Use LayoutLM to extract structured fields from document
        Identifies key-value pairs like patient name, insurance ID, dates, etc.
        """
        try:
            # Prepare inputs for LayoutLM
            encoding = self.processor(
                image, 
                return_tensors="pt",
                padding="max_length",
                truncation=True
            )
            
            # Move to device
            encoding = {k: v.to(self.device) for k, v in encoding.items()}
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**encoding)
                predictions = outputs.logits.argmax(-1).squeeze().tolist()
            
            # Map predictions to field names
            # This would be customized based on your fine-tuned model
            structured_fields = self._map_predictions_to_fields(predictions, text)
            
            return structured_fields
            
        except Exception as e:
            logger.error(f"LayoutLM extraction failed: {e}")
            return {}
    
    def _map_predictions_to_fields(
        self, 
        predictions: List[int], 
        text: str
    ) -> Dict[str, Any]:
        """
        Map LayoutLM predictions to healthcare document fields
        """
        # Label mapping (customize based on your fine-tuned model)
        label_map = {
            0: 'O',  # Outside
            1: 'PATIENT_NAME',
            2: 'PATIENT_ID',
            3: 'DATE_OF_BIRTH',
            4: 'INSURANCE_ID',
            5: 'PAYER_NAME',
            6: 'AUTH_NUMBER',
            7: 'DIAGNOSIS_CODE',
            8: 'PROCEDURE_CODE',
            9: 'APPROVAL_DATE',
            10: 'EXPIRY_DATE',
            11: 'STATUS'
        }
        
        fields = {}
        current_label = None
        current_text = []
        
        # Simple extraction logic (enhance based on your needs)
        tokens = text.split()
        for idx, pred in enumerate(predictions[:len(tokens)]):
            label = label_map.get(pred, 'O')
            
            if label != 'O':
                if label != current_label:
                    if current_label and current_text:
                        fields[current_label] = ' '.join(current_text)
                    current_label = label
                    current_text = [tokens[idx]]
                else:
                    current_text.append(tokens[idx])
        
        # Add last field
        if current_label and current_text:
            fields[current_label] = ' '.join(current_text)
        
        return fields
    
    def detect_document_type(self, text: str) -> str:
        """
        Detect document type based on content
        """
        text_lower = text.lower()
        
        if 'prior authorization' in text_lower or 'pa request' in text_lower:
            return 'PRIOR_AUTHORIZATION'
        elif 'eligibility' in text_lower or 'coverage' in text_lower:
            return 'ELIGIBILITY_VERIFICATION'
        elif 'claim' in text_lower and 'eob' in text_lower:
            return 'EXPLANATION_OF_BENEFITS'
        elif 'appeal' in text_lower:
            return 'APPEAL_LETTER'
        elif 'financial assistance' in text_lower or 'copay' in text_lower:
            return 'FINANCIAL_ASSISTANCE'
        else:
            return 'UNKNOWN'
    
    def process_pdf(self, pdf_path: str) -> OCRResult:
        """
        Process PDF document through OCR pipeline
        """
        start_time = datetime.now()
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(pdf_path, dpi=300)
            
            all_text = []
            all_fields = {}
            total_confidence = 0.0
            
            for idx, image in enumerate(images):
                logger.info(f"Processing page {idx + 1}/{len(images)}")
                
                # Preprocess
                preprocessed = self.preprocess_image(image)
                
                # Extract text
                text, confidence = self.extract_text_tesseract(preprocessed)
                all_text.append(text)
                total_confidence += confidence
                
                # Extract structured fields (only from first page typically)
                if idx == 0:
                    fields = self.extract_structured_fields_layoutlm(preprocessed, text)
                    all_fields.update(fields)
            
            # Combine results
            full_text = '\n\n'.join(all_text)
            avg_confidence = total_confidence / len(images)
            
            # Detect document type
            doc_type = self.detect_document_type(full_text)
            
            # Store in S3 if configured
            if self.s3_client and self.s3_bucket:
                self._store_in_s3(pdf_path, full_text, all_fields)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                text=full_text,
                confidence=avg_confidence,
                structured_fields=all_fields,
                document_type=doc_type,
                metadata={
                    'num_pages': len(images),
                    'source_file': pdf_path,
                    'processed_at': datetime.now().isoformat()
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise
    
    def process_image(self, image_path: str) -> OCRResult:
        """
        Process image file through OCR pipeline
        """
        start_time = datetime.now()
        
        try:
            # Load image
            image = Image.open(image_path)
            
            # Preprocess
            preprocessed = self.preprocess_image(image)
            
            # Extract text
            text, confidence = self.extract_text_tesseract(preprocessed)
            
            # Extract structured fields
            fields = self.extract_structured_fields_layoutlm(preprocessed, text)
            
            # Detect document type
            doc_type = self.detect_document_type(text)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                text=text,
                confidence=confidence,
                structured_fields=fields,
                document_type=doc_type,
                metadata={
                    'source_file': image_path,
                    'processed_at': datetime.now().isoformat()
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise
    
    def _store_in_s3(
        self, 
        file_path: str, 
        extracted_text: str, 
        fields: Dict[str, Any]
    ):
        """Store extracted data in S3"""
        try:
            file_name = Path(file_path).name
            s3_key = f"processed/{datetime.now().strftime('%Y/%m/%d')}/{file_name}.txt"
            
            # Upload extracted text
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=extracted_text.encode('utf-8'),
                Metadata={
                    'extracted_fields': str(fields),
                    'processed_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Stored OCR result in S3: {s3_key}")
            
        except Exception as e:
            logger.error(f"S3 storage failed: {e}")


# Example usage
if __name__ == "__main__":
    config = {
        'layoutlm_model': 'microsoft/layoutlmv3-base',
        'use_gpu': True,
        'use_s3': False,
        's3_bucket': 'payerhub-documents'
    }
    
    processor = OCRProcessor(config)
    
    # Process a sample document
    # result = processor.process_pdf('/path/to/prior_auth.pdf')
    # print(f"Extracted text: {result.text[:500]}...")
    # print(f"Confidence: {result.confidence}")
    # print(f"Document type: {result.document_type}")
    # print(f"Structured fields: {result.structured_fields}")
