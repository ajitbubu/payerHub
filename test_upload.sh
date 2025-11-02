#!/bin/bash

# Test the upload endpoint

echo "Testing PayerHub Upload Endpoint"
echo "================================="
echo ""

# Get auth token
echo "1. Getting authentication token..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token?user_id=USER001&organization_id=ORG789")
TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token"
    exit 1
fi

echo "✅ Token obtained"
echo ""

# Upload file
echo "2. Uploading test document..."
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/sample_prior_auth.txt" \
  -F "document_type=PRIOR_AUTHORIZATION" \
  -F "patient_id=PAT123456" \
  -F "organization_id=ORG789")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool

if echo "$UPLOAD_RESPONSE" | grep -q "success"; then
    echo ""
    echo "✅ Upload successful!"
else
    echo ""
    echo "❌ Upload failed"
fi
