#!/usr/bin/env python3
"""
Test script for handwriting OCR
Usage: python scripts/test_handwriting_ocr.py <image_path>
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.ai_pipeline.handwriting_ocr import HandwritingOCRProcessor
import json


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_handwriting_ocr.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    print("=" * 70)
    print("HANDWRITING OCR TEST")
    print("=" * 70)
    print(f"Processing: {image_path}\n")
    
    # Initialize processor
    processor = HandwritingOCRProcessor()
    
    # Process image
    result = processor.process_with_manual_review(image_path)
    
    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print(f"\n📊 Confidence Score: {result['confidence']:.1%}")
    print(f"⚠️  Needs Manual Review: {'YES' if result['needs_manual_review'] else 'NO'}")
    
    if result['needs_manual_review']:
        print(f"   Reason: {result['review_reason']}")
    
    print(f"\n🔧 Preprocessing Used: {', '.join(result['preprocessing_used'])}")
    
    print(f"\n📝 Extracted Text:")
    print("-" * 70)
    print(result['text'])
    print("-" * 70)
    
    print(f"\n📋 Extracted Fields:")
    if result['extracted_fields']:
        for key, value in result['extracted_fields'].items():
            print(f"   • {key.replace('_', ' ').title()}: {value}")
    else:
        print("   (No structured fields extracted)")
    
    print(f"\n📄 Lines Detected: {len(result['lines'])}")
    if result['lines']:
        print("-" * 70)
        for line in result['lines']:
            print(f"   Line {line['line_number']:2d}: {line['text']}")
        print("-" * 70)
    
    # Save detailed results to JSON
    output_file = image_path.rsplit('.', 1)[0] + '_ocr_result.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    if result['confidence'] < 0.4:
        print("⚠️  Very low confidence. Consider:")
        print("   • Rescanning the document at higher resolution")
        print("   • Ensuring better lighting and contrast")
        print("   • Using a flatbed scanner instead of camera")
        print("   • Manual data entry may be more accurate")
    elif result['confidence'] < 0.6:
        print("⚠️  Low confidence. Recommendations:")
        print("   • Review extracted data carefully")
        print("   • Verify critical fields manually")
        print("   • Consider rescanning if possible")
    else:
        print("✅ Good confidence. Still recommend:")
        print("   • Spot-check critical fields")
        print("   • Verify numerical values")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
