#!/usr/bin/env python3
"""
Generate sample PDF and image documents for testing PayerHub
"""

import os
from datetime import datetime

def create_sample_pdf():
    """Create a simple PDF using reportlab if available, otherwise create HTML"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        
        # Create insurance card PDF
        pdf_path = "sample_documents/insurance_card.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1*inch, 10*inch, "HEALTH INSURANCE CARD")
        
        # Card details
        c.setFont("Helvetica", 12)
        y = 9*inch
        
        card_info = [
            ("Member Name:", "JENNIFER DAVIS"),
            ("Member ID:", "UHC-2024-998877"),
            ("Group Number:", "GRP-445566"),
            ("Plan:", "PPO Select Plus"),
            ("Effective Date:", "01/01/2024"),
            ("", ""),
            ("COPAYS:", ""),
            ("Primary Care:", "$20"),
            ("Specialist:", "$40"),
            ("Emergency Room:", "$200"),
            ("", ""),
            ("RX BIN:", "610020"),
            ("RX PCN:", "MEDDADV"),
            ("RX Group:", "MEDRX01"),
            ("", ""),
            ("Customer Service:", "1-800-555-UHC1"),
            ("Website:", "www.myuhc.com"),
        ]
        
        for label, value in card_info:
            c.drawString(1*inch, y, f"{label} {value}")
            y -= 0.3*inch
        
        c.save()
        print(f"✅ Created: {pdf_path}")
        return True
        
    except ImportError:
        print("⚠️  reportlab not installed. Install with: pip install reportlab")
        return False

def create_html_documents():
    """Create HTML versions that can be converted to PDF"""
    
    # Insurance Card HTML
    insurance_card_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Insurance Card</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; }
        .card { border: 3px solid #0066cc; padding: 30px; max-width: 600px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; border-radius: 15px; }
        .title { font-size: 24px; font-weight: bold; margin-bottom: 20px; }
        .section { margin: 15px 0; }
        .label { font-weight: bold; }
        .value { margin-left: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="title">HEALTH INSURANCE CARD</div>
        <div class="section">
            <span class="label">Member Name:</span>
            <span class="value">JENNIFER DAVIS</span>
        </div>
        <div class="section">
            <span class="label">Member ID:</span>
            <span class="value">UHC-2024-998877</span>
        </div>
        <div class="section">
            <span class="label">Group Number:</span>
            <span class="value">GRP-445566</span>
        </div>
        <div class="section">
            <span class="label">Plan:</span>
            <span class="value">PPO Select Plus</span>
        </div>
        <div class="section">
            <span class="label">Effective Date:</span>
            <span class="value">01/01/2024</span>
        </div>
        <hr style="margin: 20px 0; border-color: rgba(255,255,255,0.3);">
        <div class="section">
            <div class="label">COPAYS:</div>
            <div>Primary Care: $20</div>
            <div>Specialist: $40</div>
            <div>Emergency Room: $200</div>
        </div>
        <hr style="margin: 20px 0; border-color: rgba(255,255,255,0.3);">
        <div class="section">
            <div>RX BIN: 610020</div>
            <div>RX PCN: MEDDADV</div>
            <div>RX Group: MEDRX01</div>
        </div>
        <hr style="margin: 20px 0; border-color: rgba(255,255,255,0.3);">
        <div class="section">
            <div>Customer Service: 1-800-555-UHC1</div>
            <div>Website: www.myuhc.com</div>
        </div>
    </div>
</body>
</html>
"""
    
    html_path = "sample_documents/insurance_card.html"
    with open(html_path, 'w') as f:
        f.write(insurance_card_html)
    print(f"✅ Created: {html_path}")
    print("   💡 Open this in a browser and use 'Print to PDF' to create a PDF")

def create_sample_image():
    """Create a sample image using PIL if available"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple insurance card image
        img = Image.new('RGB', (800, 500), color=(102, 126, 234))
        draw = ImageDraw.Draw(img)
        
        # Try to use a default font
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw card content
        y = 30
        draw.text((30, y), "HEALTH INSURANCE CARD", fill='white', font=font_large)
        
        y += 60
        card_info = [
            "Member: JENNIFER DAVIS",
            "ID: UHC-2024-998877",
            "Group: GRP-445566",
            "Plan: PPO Select Plus",
            "",
            "COPAYS:",
            "Primary Care: $20",
            "Specialist: $40",
            "ER: $200",
            "",
            "RX BIN: 610020",
            "Customer Service: 1-800-555-UHC1"
        ]
        
        for line in card_info:
            if line == "COPAYS:":
                draw.text((30, y), line, fill='white', font=font_medium)
            else:
                draw.text((30, y), line, fill='white', font=font_small)
            y += 30
        
        img_path = "sample_documents/insurance_card.png"
        img.save(img_path)
        print(f"✅ Created: {img_path}")
        return True
        
    except ImportError:
        print("⚠️  Pillow not installed. Install with: pip install Pillow")
        return False

def create_screenshot_simulation():
    """Create a text file that simulates a screenshot"""
    screenshot_text = """
╔══════════════════════════════════════════════════════════════╗
║                    INSURANCE PORTAL SCREENSHOT                ║
║                      www.myinsurance.com                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Welcome back, DAVID WILSON                                  ║
║                                                               ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │ Your Coverage Summary                                │    ║
║  ├─────────────────────────────────────────────────────┤    ║
║  │ Member ID: BCBS-2024-334455                         │    ║
║  │ Plan: Blue Cross Blue Shield PPO                    │    ║
║  │ Status: ✓ Active                                    │    ║
║  │                                                      │    ║
║  │ Deductible Progress:                                │    ║
║  │ [████████████░░░░░░░░] $1,200 / $1,500             │    ║
║  │                                                      │    ║
║  │ Out-of-Pocket Progress:                             │    ║
║  │ [██████░░░░░░░░░░░░░░] $1,800 / $5,000             │    ║
║  └─────────────────────────────────────────────────────┘    ║
║                                                               ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │ Recent Claims                                        │    ║
║  ├─────────────────────────────────────────────────────┤    ║
║  │ 10/15/2024 - Dr. Smith Office Visit    $150.00     │    ║
║  │              Status: Processed                       │    ║
║  │                                                      │    ║
║  │ 10/01/2024 - Lab Work                  $280.00     │    ║
║  │              Status: Paid                            │    ║
║  │                                                      │    ║
║  │ 09/20/2024 - Prescription Refill       $45.00      │    ║
║  │              Status: Paid                            │    ║
║  └─────────────────────────────────────────────────────┘    ║
║                                                               ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │ Quick Actions                                        │    ║
║  ├─────────────────────────────────────────────────────┤    ║
║  │ [Find a Doctor]  [View ID Card]  [File a Claim]    │    ║
║  └─────────────────────────────────────────────────────┘    ║
║                                                               ║
║  Contact Us: 1-800-555-BCBS                                  ║
║  Available 24/7                                              ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝

Screenshot captured: October 26, 2024 at 2:30 PM
Browser: Chrome 118.0
Device: MacBook Pro
"""
    
    screenshot_path = "sample_documents/portal_screenshot.txt"
    with open(screenshot_path, 'w') as f:
        f.write(screenshot_text)
    print(f"✅ Created: {screenshot_path}")

def main():
    """Generate all sample documents"""
    print("=" * 60)
    print("PayerHub Sample Document Generator")
    print("=" * 60)
    print()
    
    # Create directory if it doesn't exist
    os.makedirs("sample_documents", exist_ok=True)
    
    print("Generating sample documents...")
    print()
    
    # Try to create PDF
    pdf_created = create_sample_pdf()
    
    # Create HTML version
    create_html_documents()
    
    # Try to create image
    image_created = create_sample_image()
    
    # Create screenshot simulation
    create_screenshot_simulation()
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    # List all files in sample_documents
    files = os.listdir("sample_documents")
    print(f"\n📁 Total files created: {len(files)}")
    print("\nAvailable test documents:")
    for f in sorted(files):
        size = os.path.getsize(f"sample_documents/{f}")
        print(f"  • {f} ({size:,} bytes)")
    
    print()
    print("=" * 60)
    print("Next Steps")
    print("=" * 60)
    print()
    print("1. Open the web UI: http://localhost:8000")
    print("2. Try uploading different document types:")
    print("   - Text files (.txt)")
    print("   - PDF files (.pdf) - if reportlab installed")
    print("   - Image files (.png) - if Pillow installed")
    print("   - HTML files (.html) - can be converted to PDF in browser")
    print()
    print("3. Test different document types:")
    print("   - Prior Authorization")
    print("   - Eligibility Verification")
    print("   - Explanation of Benefits")
    print("   - Appeal Letter")
    print("   - Claim Document")
    print()
    
    if not pdf_created:
        print("💡 To create PDFs, install reportlab:")
        print("   pip install reportlab")
        print()
    
    if not image_created:
        print("💡 To create images, install Pillow:")
        print("   pip install Pillow")
        print()

if __name__ == "__main__":
    main()
