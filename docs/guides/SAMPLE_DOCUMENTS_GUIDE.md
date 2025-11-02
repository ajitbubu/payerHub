# 📄 Sample Documents Guide

## Overview

Your PayerHub installation now includes 10 sample documents for testing! These cover various healthcare document types in multiple formats.

---

## 📁 Available Documents

### Text Files (.txt)

#### 1. **sample_prior_auth.txt** (1.6 KB)
- **Type**: Prior Authorization Request
- **Content**: Complete PA request with patient, insurance, provider, and clinical information
- **Use Case**: Test OCR and entity extraction for authorization workflows
- **Key Data**: 
  - Patient: John Smith (PAT123456)
  - Insurance: Blue Cross Blue Shield
  - Procedure: MRI Brain with Contrast

#### 2. **eligibility_verification.txt** (2.2 KB)
- **Type**: Eligibility Verification Response
- **Content**: Detailed insurance coverage verification
- **Use Case**: Test benefit extraction and coverage analysis
- **Key Data**:
  - Patient: Sarah Martinez (MEM456789)
  - Insurance: Aetna Health Insurance
  - Deductible: $1,500 (56.7% met)

#### 3. **explanation_of_benefits.txt** (4.8 KB)
- **Type**: EOB (Explanation of Benefits)
- **Content**: Detailed claim processing results with payment breakdown
- **Use Case**: Test claim data extraction and financial calculations
- **Key Data**:
  - Patient: Robert Johnson
  - Insurance: UnitedHealthcare
  - Total Billed: $580.00, Patient Owes: $180.00

#### 4. **appeal_letter.txt** (5.5 KB)
- **Type**: Insurance Appeal Letter
- **Content**: Formal appeal of denied prior authorization
- **Use Case**: Test clinical documentation and appeal reasoning extraction
- **Key Data**:
  - Patient: Emily Thompson
  - Insurance: Blue Cross Blue Shield
  - Reason: MRI denial appeal with extensive clinical justification

#### 5. **claim_document.txt** (6.8 KB)
- **Type**: CMS-1500 Claim Form
- **Content**: Standard medical claim form with all fields
- **Use Case**: Test structured form data extraction
- **Key Data**:
  - Patient: Michael Anderson
  - Insurance: Blue Cross Blue Shield
  - Services: Office visit, spirometry, chest X-ray

#### 6. **portal_screenshot.txt** (4.6 KB)
- **Type**: Insurance Portal Screenshot (ASCII art)
- **Content**: Simulated insurance portal interface
- **Use Case**: Test unstructured data extraction from screenshots
- **Key Data**:
  - Member: David Wilson
  - Deductible progress, recent claims, quick actions

### PDF Files (.pdf)

#### 7. **insurance_card.pdf** (2.0 KB)
- **Type**: Insurance ID Card
- **Content**: Member insurance card with all key information
- **Use Case**: Test PDF OCR and card data extraction
- **Key Data**:
  - Member: Jennifer Davis
  - ID: UHC-2024-998877
  - Copays, RX information, contact details

### Image Files (.png)

#### 8. **insurance_card.png** (30.4 KB)
- **Type**: Insurance ID Card Image
- **Content**: Visual representation of insurance card
- **Use Case**: Test image OCR and visual data extraction
- **Key Data**: Same as PDF version

#### 9. **Patient Authorization Data.png** (1.8 MB)
- **Type**: Patient Authorization Document
- **Content**: Pre-existing patient authorization image
- **Use Case**: Test large image file handling

### HTML Files (.html)

#### 10. **insurance_card.html** (2.2 KB)
- **Type**: Insurance Card (HTML format)
- **Content**: Styled HTML version of insurance card
- **Use Case**: Can be converted to PDF in browser for testing
- **Key Data**: Same as PDF/PNG versions

---

## 🎯 Testing Scenarios

### Scenario 1: Prior Authorization Workflow
```
File: sample_prior_auth.txt
Document Type: Prior Authorization
Expected Extraction:
- Patient Name: John Smith
- Patient ID: PAT123456
- Insurance: Blue Cross Blue Shield
- Procedure: MRI Brain with Contrast
- Diagnosis: Migraine (G43.909)
```

### Scenario 2: Eligibility Check
```
File: eligibility_verification.txt
Document Type: Eligibility Verification
Expected Extraction:
- Member: Sarah Martinez
- Member ID: MEM456789
- Deductible: $1,500 (56.7% met)
- Coverage Status: ACTIVE
- Copays: PCP $25, Specialist $50
```

### Scenario 3: Claims Processing
```
File: explanation_of_benefits.txt
Document Type: Explanation of Benefits
Expected Extraction:
- Patient: Robert Johnson
- Total Billed: $580.00
- Allowed Amount: $400.00
- Patient Responsibility: $180.00
- Services: Office visit, X-ray, injection
```

### Scenario 4: Appeal Documentation
```
File: appeal_letter.txt
Document Type: Appeal Letter
Expected Extraction:
- Patient: Emily Thompson
- Denial Reason: Not medically necessary
- Conservative Treatment: 8 months documented
- Clinical Justification: Progressive symptoms
```

### Scenario 5: Claim Form
```
File: claim_document.txt
Document Type: Claim Document
Expected Extraction:
- Patient: Michael Anderson
- Provider: Boston Medical Associates
- Diagnosis: Acute bronchitis (J20.9)
- Total Charges: $485.00
```

### Scenario 6: Insurance Card (Multiple Formats)
```
Files: insurance_card.pdf, insurance_card.png, insurance_card.html
Document Type: Unknown/Other
Expected Extraction:
- Member: Jennifer Davis
- Member ID: UHC-2024-998877
- Copays: PCP $20, Specialist $40, ER $200
- RX Information: BIN, PCN, Group
```

---

## 🚀 How to Test

### Method 1: Web UI (Recommended)
1. Open http://localhost:8000
2. Select document type from dropdown
3. Drag and drop any sample file
4. Click "Upload & Process"
5. Review extracted data

### Method 2: Command Line
```bash
# Test with curl
./test_upload.sh

# Or manually
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token?user_id=USER001&organization_id=ORG789" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['token'])")

curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/sample_prior_auth.txt" \
  -F "document_type=PRIOR_AUTHORIZATION" \
  -F "patient_id=PAT123456" \
  -F "organization_id=ORG789"
```

### Method 3: API Documentation
1. Open http://localhost:8000/docs
2. Navigate to POST /api/v1/documents/upload
3. Click "Try it out"
4. Upload file and fill parameters
5. Execute and view response

---

## 📊 Expected Results

For each document, you should see:

### Pipeline Steps
- ✓ OCR Processing (confidence ~95%)
- ✓ Entity Extraction (10-15 entities)
- ✓ Anomaly Detection (no issues)
- ✓ FHIR Conversion (valid resource)
- ✓ Privacy Check (access granted)
- ✓ Hub Integration (record created)

### Extracted Data
**Patient Information:**
- Patient Name
- Patient ID
- Date of Birth
- Contact Information

**Insurance Information:**
- Insurance Company
- Policy/Member Number
- Group Number
- Coverage Details

---

## 🎨 Document Formats

### Text Files (.txt)
- ✅ Easy to read and edit
- ✅ Fast processing
- ✅ Good for testing entity extraction
- ✅ Can simulate various document types

### PDF Files (.pdf)
- ✅ Real-world format
- ✅ Tests OCR capabilities
- ✅ Preserves formatting
- ✅ Industry standard

### Image Files (.png, .jpg)
- ✅ Tests image OCR
- ✅ Simulates scanned documents
- ✅ Tests visual data extraction
- ✅ Common for insurance cards

### HTML Files (.html)
- ✅ Can be converted to PDF
- ✅ Styled content
- ✅ Easy to customize
- ✅ Browser-based testing

---

## 💡 Tips for Testing

### 1. Test Different File Types
- Start with text files (fastest)
- Move to PDFs (realistic)
- Try images (challenging)
- Test HTML (versatile)

### 2. Test Different Document Types
- Change the document type dropdown
- See how classification works
- Compare extraction results

### 3. Test File Sizes
- Small files: < 10 KB (fast)
- Medium files: 10-100 KB (normal)
- Large files: > 1 MB (stress test)

### 4. Test Edge Cases
- Empty files
- Corrupted files
- Wrong file types
- Very large files

### 5. Monitor Results
- Check extraction accuracy
- Review confidence scores
- Verify all pipeline steps
- Examine raw JSON response

---

## 🔧 Customization

### Create Your Own Test Documents

#### Text File
```bash
cat > sample_documents/my_test.txt << 'EOF'
Patient Name: Your Name
Patient ID: TEST123
Insurance: Test Insurance Co.
Policy: TEST-2024-001
EOF
```

#### Using the Generator
```bash
# Edit generate_sample_documents.py
# Add your custom document generation
python3 generate_sample_documents.py
```

---

## 📈 Performance Benchmarks

| File Type | Size | Processing Time | Accuracy |
|-----------|------|----------------|----------|
| Text | < 10 KB | < 1 second | 95-98% |
| PDF | < 100 KB | 1-3 seconds | 90-95% |
| Image | < 1 MB | 2-5 seconds | 85-92% |
| Large Image | > 1 MB | 5-10 seconds | 85-92% |

*Note: These are estimates. Actual performance depends on system resources.*

---

## 🐛 Troubleshooting

### File Won't Upload
- Check file size (max 50 MB)
- Verify file type is supported
- Ensure file isn't corrupted
- Try a different file

### Low Confidence Scores
- Normal for complex documents
- Images may have lower scores
- Handwritten text is challenging
- Try clearer/higher quality files

### Missing Extracted Data
- Some documents may not have all fields
- Mock data returns realistic examples
- Real OCR would extract actual content
- Check raw JSON for all data

---

## 📚 Next Steps

1. **Test All Documents**: Upload each sample file
2. **Compare Results**: See how different formats perform
3. **Create Custom Documents**: Make your own test files
4. **Review Extraction**: Check accuracy of extracted data
5. **Test Edge Cases**: Try unusual or problematic files

---

## 🎉 Summary

You now have:
- ✅ 10 sample documents
- ✅ 5 different document types
- ✅ 4 file formats (TXT, PDF, PNG, HTML)
- ✅ Realistic healthcare data
- ✅ Complete testing scenarios

**Start testing**: http://localhost:8000

Happy testing! 🚀
