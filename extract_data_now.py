#!/usr/bin/env python3
"""
Quick data extraction from handwritten document
"""
import sys
from PIL import Image
import pytesseract
import re
import json

def extract_with_tesseract(image_path):
    """Extract data using Tesseract"""
    print("📄 Loading image...")
    image = Image.open(image_path)
    
    print("🔍 Extracting text with Tesseract...")
    text = pytesseract.image_to_string(image)
    
    print("\n" + "="*70)
    print("EXTRACTED TEXT")
    print("="*70)
    print(text)
    print("="*70)
    
    # Extract structured fields
    fields = {}
    
    # Member ID
    id_match = re.search(r'ID[:\s]+([A-Z0-9\-]+)', text, re.IGNORECASE)
    if id_match:
        fields['member_id'] = id_match.group(1)
    
    # Plan
    plan_match = re.search(r'Plan[:\s]+([A-Z0-9\s]+)', text, re.IGNORECASE)
    if plan_match:
        fields['plan'] = plan_match.group(1).strip()
    
    # Copay amounts
    copay_matches = re.findall(r'\$(\d+)', text)
    if copay_matches:
        fields['amounts'] = [f"${amt}" for amt in copay_matches]
    
    # Numbers
    numbers = re.findall(r'\d{4,}', text)
    if numbers:
        fields['numbers_found'] = numbers
    
    print("\n" + "="*70)
    print("STRUCTURED FIELDS")
    print("="*70)
    print(json.dumps(fields, indent=2))
    print("="*70)
    
    return text, fields

if __name__ == "__main__":
    image_path = "data/samples/payer-sample.jpg"
    
    print("="*70)
    print("HANDWRITTEN DATA EXTRACTION")
    print("="*70)
    print(f"Image: {image_path}\n")
    
    try:
        text, fields = extract_with_tesseract(image_path)
        
        print("\n✅ Extraction complete!")
        print(f"\nFound {len(fields)} structured fields")
        
        # Save results
        result = {
            'text': text,
            'fields': fields,
            'confidence': 'medium',
            'method': 'tesseract'
        }
        
        with open('extracted_data.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print("💾 Results saved to: extracted_data.json")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
