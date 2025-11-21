#!/usr/bin/env python3
"""
Compare different OCR models on handwritten documents
Usage: python scripts/compare_ocr_models.py <image_path>
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.ai_pipeline.handwriting_ocr import HandwritingOCRProcessor
try:
    from src.core.ai_pipeline.trocr_handwriting import TrOCRHandwritingProcessor
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False
    print("⚠️  TrOCR not available. Install with: pip install transformers torch")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/compare_ocr_models.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    print("=" * 80)
    print("OCR MODELS COMPARISON")
    print("=" * 80)
    print(f"Image: {image_path}\n")
    
    results = {}
    
    # Test 1: Tesseract-based (current)
    print("🔍 Testing Tesseract-based OCR...")
    print("-" * 80)
    tesseract_processor = HandwritingOCRProcessor()
    start_time = time.time()
    tesseract_result = tesseract_processor.process_with_manual_review(image_path)
    tesseract_time = time.time() - start_time
    
    results['tesseract'] = {
        'text': tesseract_result['text'],
        'confidence': tesseract_result['confidence'],
        'fields': tesseract_result['extracted_fields'],
        'time': tesseract_time,
        'lines': len(tesseract_result['lines'])
    }
    
    print(f"✓ Completed in {tesseract_time:.2f}s")
    print(f"  Confidence: {tesseract_result['confidence']:.1%}")
    print(f"  Lines detected: {len(tesseract_result['lines'])}")
    print(f"  Fields extracted: {len(tesseract_result['extracted_fields'])}")
    print()
    
    # Test 2: TrOCR (if available)
    if TROCR_AVAILABLE:
        print("🔍 Testing TrOCR (Transformer-based)...")
        print("-" * 80)
        try:
            trocr_processor = TrOCRHandwritingProcessor()
            start_time = time.time()
            trocr_result = trocr_processor.process_with_fallback(image_path)
            trocr_time = time.time() - start_time
            
            results['trocr'] = {
                'text': trocr_result['text'],
                'confidence': trocr_result['confidence'],
                'fields': trocr_result['extracted_fields'],
                'time': trocr_time,
                'lines': len(trocr_result['lines'])
            }
            
            print(f"✓ Completed in {trocr_time:.2f}s")
            print(f"  Confidence: {trocr_result['confidence']:.1%}")
            print(f"  Lines detected: {len(trocr_result['lines'])}")
            print(f"  Fields extracted: {len(trocr_result['extracted_fields'])}")
            print()
        except Exception as e:
            print(f"✗ TrOCR failed: {e}\n")
    
    # Comparison
    print("=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    
    print("\n📊 Performance Metrics:")
    print("-" * 80)
    print(f"{'Model':<20} {'Confidence':<15} {'Time':<10} {'Lines':<10} {'Fields':<10}")
    print("-" * 80)
    
    for model_name, result in results.items():
        print(f"{model_name.upper():<20} {result['confidence']:.1%}{'':>9} "
              f"{result['time']:.2f}s{'':>4} {result['lines']:<10} {result['fields']:<10}")
    
    print()
    
    # Text comparison
    print("\n📝 Extracted Text Comparison:")
    print("-" * 80)
    
    for model_name, result in results.items():
        print(f"\n{model_name.upper()}:")
        print(result['text'][:500] if result['text'] else "(No text extracted)")
        if len(result['text']) > 500:
            print("... (truncated)")
    
    print()
    
    # Fields comparison
    print("\n📋 Extracted Fields Comparison:")
    print("-" * 80)
    
    all_fields = set()
    for result in results.values():
        all_fields.update(result['fields'].keys())
    
    if all_fields:
        for field in sorted(all_fields):
            print(f"\n{field.replace('_', ' ').title()}:")
            for model_name, result in results.items():
                value = result['fields'].get(field, '(not found)')
                print(f"  {model_name.upper():<15}: {value}")
    else:
        print("(No structured fields extracted by any model)")
    
    print()
    
    # Recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    
    if TROCR_AVAILABLE and 'trocr' in results:
        tesseract_conf = results['tesseract']['confidence']
        trocr_conf = results['trocr']['confidence']
        
        if trocr_conf > tesseract_conf + 0.1:
            print("✅ TrOCR shows significantly better confidence")
            print(f"   Improvement: {(trocr_conf - tesseract_conf) * 100:.1f} percentage points")
            print("\n   Recommended: Use TrOCR for production")
        elif trocr_conf > tesseract_conf:
            print("✅ TrOCR shows slightly better confidence")
            print("\n   Recommended: Use TrOCR for better accuracy")
        else:
            print("⚠️  Tesseract performed better on this image")
            print("\n   Recommended: Use hybrid approach with both models")
    else:
        print("ℹ️  Only Tesseract tested")
        print("\n   To test TrOCR, install: pip install transformers torch")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
