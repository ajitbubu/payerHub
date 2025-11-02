#!/bin/bash

# PayerHub API Test Script
# Simple script to test the API endpoints

echo "=========================================="
echo "PayerHub API Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000"

# Test 1: Root endpoint
echo -e "${YELLOW}Test 1: Root Endpoint${NC}"
echo "GET $API_URL/"
response=$(curl -s $API_URL/)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Success${NC}"
    echo "$response" | python3 -m json.tool
else
    echo -e "${RED}✗ Failed${NC}"
fi
echo ""

# Test 2: Health check
echo -e "${YELLOW}Test 2: Health Check${NC}"
echo "GET $API_URL/health"
response=$(curl -s $API_URL/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Success${NC}"
    echo "$response" | python3 -m json.tool
else
    echo -e "${RED}✗ Failed${NC}"
fi
echo ""

# Test 3: Get authentication token
echo -e "${YELLOW}Test 3: Authentication Token${NC}"
echo "POST $API_URL/api/v1/auth/token"
response=$(curl -s -X POST "$API_URL/api/v1/auth/token?user_id=USER001&organization_id=ORG789")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Success${NC}"
    echo "$response" | python3 -m json.tool
    
    # Extract token for next tests
    TOKEN=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null)
    if [ ! -z "$TOKEN" ]; then
        echo -e "${GREEN}Token extracted successfully${NC}"
    fi
else
    echo -e "${RED}✗ Failed${NC}"
fi
echo ""

# Test 4: API Documentation
echo -e "${YELLOW}Test 4: API Documentation${NC}"
echo "GET $API_URL/docs"
response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/docs)
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ Success - Documentation available at $API_URL/docs${NC}"
else
    echo -e "${RED}✗ Failed - HTTP Status: $response${NC}"
fi
echo ""

echo "=========================================="
echo "Test Suite Complete"
echo "=========================================="
echo ""
echo "API is running at: $API_URL"
echo "Interactive docs: $API_URL/docs"
echo ""
