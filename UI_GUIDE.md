# PayerHub Web UI Guide

## 🎨 User Interface Overview

A modern, user-friendly web interface has been created for testing the PayerHub Integration Platform. The UI allows you to upload documents and see the AI/ML processing pipeline in action.

## 🌐 Accessing the UI

**URL**: http://localhost:8000

The web interface is now running and accessible in your browser!

## ✨ Features

### 1. **Document Upload**
- **Drag & Drop**: Simply drag files into the upload area
- **Click to Browse**: Click the upload area to select files
- **Supported Formats**:
  - PDF documents
  - Images (JPG, JPEG, PNG, TIFF)
  - Text files (TXT)
  - Screenshots

### 2. **Document Type Selection**
Choose from various healthcare document types:
- Prior Authorization
- Eligibility Verification
- Explanation of Benefits (EOB)
- Appeal Letter
- Financial Assistance
- Claim Document
- Unknown/Other

### 3. **Patient & Organization Info**
- Patient ID field (pre-filled with example: PAT123456)
- Organization ID field (pre-filled with example: ORG789)
- Easily customizable for your test cases

### 4. **Real-Time Processing**
Watch the document processing pipeline in action:
- **OCR Processing** - Text extraction from documents
- **Entity Extraction** - AI-powered data extraction
- **Anomaly Detection** - Data quality validation
- **FHIR Conversion** - Healthcare standard conversion
- **Privacy Check** - Consent and access validation
- **Hub Integration** - CRM system update

### 5. **Results Display**
- Processing status indicator
- Step-by-step pipeline progress
- Extracted patient information
- Extracted insurance information
- Document confidence scores
- Raw JSON response viewer

### 6. **Recent Uploads**
- View history of recent uploads
- Quick status overview
- Timestamp tracking

## 🚀 How to Use

### Step 1: Open the UI
```bash
# Open in your default browser
open http://localhost:8000

# Or visit manually
# Navigate to: http://localhost:8000
```

### Step 2: Prepare Your Document
You can test with:
- Sample PDF documents
- Screenshots of insurance cards
- Photos of medical documents
- Text files with patient information
- Scanned documents

### Step 3: Upload Document
1. Select document type from dropdown
2. Verify/update Patient ID and Organization ID
3. Either:
   - Drag and drop your file into the upload area
   - Click the upload area to browse and select a file

### Step 4: Process Document
1. Click "Upload & Process" button
2. Watch the progress bar as the document is processed
3. View real-time updates of each pipeline step

### Step 5: Review Results
- Check the processing status (Success/Processing/Error)
- Review extracted information:
  - Patient details
  - Insurance information
  - Clinical data
- Examine each pipeline step's results
- View raw JSON response for debugging

## 📊 UI Components

### Header
- **PayerHub Logo**: Branding
- **API Status Badge**: Shows if API is online/offline
  - 🟢 Green = API Online
  - 🔴 Red = API Offline

### Upload Section
- **Document Type Selector**: Choose document category
- **Patient/Organization Fields**: Enter identifiers
- **Upload Area**: Drag & drop or click to upload
- **File Preview**: Shows selected file details
- **Upload Button**: Initiates processing

### Results Section
- **Progress Bar**: Visual processing indicator
- **Status Badge**: Success/Processing/Error state
- **Document ID**: Unique identifier for tracking
- **Pipeline Steps**: Each processing stage with status
- **Extracted Data**: Organized display of extracted information
- **Raw Response**: Expandable JSON viewer

### Recent Uploads
- **Upload History**: Last 10 uploads
- **Quick Status**: At-a-glance status indicators
- **Timestamps**: When each document was processed

## 🎯 Testing Scenarios

### Test 1: PDF Document
```
1. Select "Prior Authorization" as document type
2. Upload a PDF file
3. Watch OCR extract text
4. Review extracted entities
```

### Test 2: Image/Screenshot
```
1. Select "Eligibility Verification"
2. Upload a screenshot of an insurance card
3. See image processing in action
4. Check extracted insurance details
```

### Test 3: Text Document
```
1. Select "Unknown/Other"
2. Upload a text file with patient info
3. Observe entity extraction
4. Verify data quality checks
```

## 🎨 UI Design Features

### Modern Design
- Clean, professional interface
- Gradient background
- Card-based layout
- Smooth animations

### Responsive
- Works on desktop, tablet, and mobile
- Adaptive layouts
- Touch-friendly controls

### User-Friendly
- Clear visual feedback
- Intuitive drag & drop
- Progress indicators
- Error messages

### Accessible
- High contrast colors
- Clear typography
- Keyboard navigation
- Screen reader friendly

## 🔧 Technical Details

### Frontend Stack
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with CSS Grid and Flexbox
- **Vanilla JavaScript**: No framework dependencies
- **LocalStorage**: Recent uploads persistence

### API Integration
- RESTful API calls
- JWT authentication
- FormData for file uploads
- JSON response handling

### File Handling
- Client-side validation
- File type checking
- Size limit enforcement (50MB)
- Preview generation

## 🐛 Troubleshooting

### UI Not Loading
```bash
# Check if API is running
curl http://localhost:8000/health

# Restart API if needed
python3 run_api.py
```

### Upload Fails
- Check file size (max 50MB)
- Verify file type is supported
- Check API status badge
- Review browser console for errors

### No Results Displayed
- Ensure API is running
- Check network tab in browser dev tools
- Verify authentication token is generated
- Review API logs

## 📱 Browser Compatibility

Tested and working on:
- ✅ Chrome/Chromium (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)

## 🔗 Quick Links

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **API Root**: http://localhost:8000/api

## 📸 Screenshots

### Main Upload Screen
- Clean interface with drag & drop
- Document type selection
- Patient/Organization fields

### Processing View
- Animated progress bar
- Real-time status updates
- Pipeline step indicators

### Results Display
- Success/error status
- Extracted data cards
- Pipeline step details
- Raw JSON viewer

## 💡 Tips

1. **Test with Real Documents**: Use actual healthcare documents for realistic testing
2. **Try Different Types**: Test various document types to see different extraction patterns
3. **Check Recent Uploads**: Use the history to compare results
4. **View Raw Response**: Helpful for debugging and understanding the API
5. **Monitor API Status**: Keep an eye on the status badge

## 🎉 Next Steps

1. **Upload Your First Document**: Try the drag & drop feature
2. **Explore Different Document Types**: Test various healthcare documents
3. **Review Extracted Data**: See the AI/ML pipeline in action
4. **Check API Documentation**: Visit /docs for detailed API info
5. **Customize for Your Needs**: Modify patient IDs and organization IDs

---

**Enjoy testing the PayerHub Integration Platform!** 🚀

The UI provides a visual, interactive way to test document processing without writing any code.
